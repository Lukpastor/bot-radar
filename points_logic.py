import json
import re
import os
import warnings
import google.generativeai as genai
from config import logger, pontos_os, sinonimos, CATEGORIAS_ORDENADAS
from dotenv import load_dotenv

# Silencia o aviso chato (FutureWarning) do pacote google.generativeai
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

# Carrega a chave do Google e configura a API
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
else:
    logger.error("🚨 CHAVE DO GEMINI NÃO ENCONTRADA NO .ENV!")
    model = None

def extrair_cliente(texto: str) -> str:
    match = re.search(r'(?:nome do cliente|cliente):\s*([^\n\r]+)', texto, re.IGNORECASE)
    if match:
        return match.group(1).strip().upper()
    return "NÃO INFORMADO"

def processar_com_ia(texto: str) -> dict:
    texto_lower = texto.lower()
    cliente_extraido = extrair_cliente(texto)
    
    # ====================================================
    # PASSO 0: CAPTURA DE ATRIBUIÇÃO DIRETA (Ex: Serviço = 1)
    # ====================================================
    padrao_atribuicao = re.findall(r'([^\n=]+?)\s*=\s*([0-9]+(?:\.[0-9]+)?)', texto)
    
    if padrao_atribuicao:
        servicos_personalizados = []
        pontos_totais_personalizados = 0.0
        
        for desc, valor in padrao_atribuicao:
            desc_limpa = desc.strip().upper()
            if desc_limpa:
                servicos_personalizados.append(desc_limpa)
                pontos_totais_personalizados += float(valor)
        
        if servicos_personalizados:
            servico_final = " + ".join(servicos_personalizados)
            if re.search(r'\b(infra|rompimento|otdr|ce|cd|cto)\b', texto_lower):
                 cliente_definitivo = "INFRAESTRUTURA DE REDE"
            else:
                 cliente_definitivo = cliente_extraido
                 
            return {
                "is_os": True, "servicos": [servico_final], 
                "pontos": pontos_totais_personalizados, "cliente": cliente_definitivo, "resposta_chat": ""
            }

    # ====================================================
    # PASSO 0.5: PRIORIDADE ABSOLUTA PARA O TIPO INFORMADO NA OS
    # ====================================================
    match_tipo = re.search(r'tipo\s+e\s+suporte\s*:\s*(.+)', texto_lower)
    if match_tipo:
        tipo = match_tipo.group(1).strip()
        if tipo == "reparo" and "reparo" in pontos_os:
            return {
                "is_os": True,
                "servicos": ["reparo"],
                "pontos": pontos_os["reparo"],
                "cliente": cliente_extraido,
                "resposta_chat": ""
            }

    # ====================================================
    # PASSO 1: BUSCA DETERMINÍSTICA DIRETA (MÉTODO ULTRA-RÁPIDO)
    # ====================================================
    servicos_finais = []
    
    if re.search(r'\b(tvbox|tv box|netflix|assistência|funcionando normal|funcionando normalmente|tudo normal)\b', texto_lower):
        servicos_finais.append("visita improdutiva")
    
    for categoria in CATEGORIAS_ORDENADAS:
        if categoria in sinonimos:
            for frase in sinonimos[categoria]:
                if frase.lower() in texto_lower:
                    if categoria not in servicos_finais:
                        servicos_finais.append(categoria)
                    break 

    if servicos_finais:
        infra_validada = []
        for s in servicos_finais:
            if "infra" in s and not re.search(r'\b(poste|rua|ceo|espinado|caixa de emenda|cd|ce|otdr|drop|rompimento|cto)\b', texto_lower):
                continue 
            infra_validada.append(s)
            
        if infra_validada:
            pontos_totais = sum(pontos_os[s] for s in infra_validada if s in pontos_os)
            return {
                "is_os": True, "servicos": infra_validada,
                "pontos": pontos_totais, "cliente": cliente_extraido,
                "resposta_chat": ""
            }

    # ====================================================
    # PASSO 2: GOOGLE GEMINI API (NUVEM)
    # ====================================================
    if not model:
        return {"is_os": True, "servicos": [], "pontos": 0.0, "cliente": cliente_extraido, "resposta_chat": ""}

    prompt = f"""
    Você é um extrator de dados estrito da Radar Internet. Sua ÚNICA função é analisar relatórios técnicos e extrair um JSON estruturado.

    MENSAGEM DO TÉCNICO: "{texto}"

    REGRAS DE OURO:
    1. Extraia o nome do cliente em MAIÚSCULAS. Se não houver clareza, retorne "NÃO INFORMADO".
    2. Se relatar problema em equipamento de terceiros (TVBox, roteador particular, celular) ou disser que a "internet já estava normal", classifique como "visita improdutiva".
    3. Se existir "Tipo e suporte: reparo", a categoria deve ser obrigatoriamente "reparo", mesmo que o texto mencione CTO, caixa de emenda ou infraestrutura.
    4. Somente classifique como "infra - reparo" quando o relatório for de uma OS da equipe de infraestrutura, e não apenas porque a infraestrutura foi acionada.
    5. Para outros casos, tente enquadrar o serviço descrito EXATAMENTE em UMA destas categorias: {list(pontos_os.keys())}.

    Obrigatório retornar APENAS o JSON no formato abaixo:
    {{
        "is_os": true,
        "servicos": ["NOME_DA_CATEGORIA"],
        "pontos": 0.0,
        "cliente": "NOME DO CLIENTE",
        "resposta_chat": ""
    }}
    """

    try:
        response = model.generate_content(prompt)
        dados_extraidos = json.loads(response.text)
        
        servicos_ia = []
        pontos_ia = 0.0
        
        if dados_extraidos.get('is_os') and 'servicos' in dados_extraidos:
            for s in dados_extraidos['servicos']:
                servico_limpo = s.lower().strip()
                
                if "infra" in servico_limpo and not re.search(r'\b(poste|rua|ceo|espinado|caixa de emenda|cd|ce|otdr|drop|rompimento|cto)\b', texto_lower):
                    if "retirada" in servico_limpo: servico_limpo = "retirada fibra"
                    elif "instalação" in servico_limpo: servico_limpo = "instalação fibra"
                    else: servico_limpo = "reparo"
                
                if servico_limpo in pontos_os:
                    if servico_limpo not in servicos_ia: 
                        servicos_ia.append(servico_limpo)
                        pontos_ia += pontos_os[servico_limpo]

        if servicos_ia:
            dados_extraidos['servicos'] = servicos_ia
            dados_extraidos['pontos'] = pontos_ia
        else:
             dados_extraidos['servicos'] = []
             dados_extraidos['pontos'] = 0.0
             
        dados_extraidos['cliente'] = cliente_extraido
        return dados_extraidos

    except Exception as e:
        logger.error(f"Erro na nuvem do Gemini: {e}")
        return {"is_os": True, "servicos": [], "pontos": 0.0, "cliente": cliente_extraido, "resposta_chat": ""}
