import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv
from config import pontos_os, sinonimos, CATEGORIAS_ORDENADAS, logger

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)

def processar_com_ia(texto_os: str) -> dict:
    """
    Usa a IA do Gemini para analisar o texto da O.S., extrair cliente,
    serviços executados e calcular os pontos com base nas regras do config.py.
    """
    if not API_KEY:
        logger.error("GEMINI_API_KEY não configurada.")
        return {"is_os": False}

    prompt = f"""
Você é um assistente especialista em análise de Ordens de Serviço (O.S.) de provedores de internet.
Sua tarefa é analisar o texto enviado pelo técnico e retornar um JSON estrito contendo:
1. "is_os": true se for um relatório de serviço válido.
2. "cliente": O nome do cliente extraído do texto (se não achar, retorne "NÃO INFORMADO").
3. "servicos": Uma lista contendo EXATAMENTE UM nome exato de serviço, baseando-se estritamente na lista de permitidos.
4. "pontos": A pontuação do único serviço escolhido.

Lista de serviços permitidos e seus pontos:
{json.dumps(pontos_os, ensure_ascii=False, indent=2)}

Sinônimos e termos equivalentes para te ajudar a identificar os serviços:
{json.dumps(sinonimos, ensure_ascii=False, indent=2)}

🚨 REGRAS CRÍTICAS DE ANÁLISE:
1. IDENTIFICAÇÃO DE O.S.: Se o texto tiver dados como Nome do cliente, Potência de RX, Teste de velocidade ou OLT, É UMA O.S. VÁLIDA. Sempre retorne "is_os": true nestes casos, MESMO QUE O TEXTO ESTEJA CONFUSO.
2. APENAS UM SERVIÇO: É proibido retornar mais de um serviço. Escolha apenas o serviço final real que o técnico executou.
3. RESOLUÇÃO DE CONFLITOS: Se o técnico preencher "Tipo e suporte: Reparo", mas na descrição colocar "Visita improdutiva" ou "Não foi encontrado problema", A DESCRIÇÃO É A QUE VALE. O serviço final será "visita improdutiva". Se o suporte diz "Reparo" mas a descrição diz "Reinstalação externa realizada", o serviço final é "reinstalacao externa".

=== GABARITO (EXEMPLOS DE COMO VOCÊ DEVE RESPONDER) ===

Exemplo 1 (Contradição comum):
Texto: "...Tipo e suporte: Reparo Fibra... Visita improdutiva. Não foi encontrado nenhum problema..."
Sua Resposta: {{"is_os": true, "cliente": "Nome do Cliente", "servicos": ["visita improdutiva"], "pontos": 1.0}}

Exemplo 2 (Contradição de Reparo e Reinstalação):
Texto: "...Tipo e suporte: reparo... Reinstalação externa realizada. Potência de RX..."
Sua Resposta: {{"is_os": true, "cliente": "Nome do Cliente", "servicos": ["reinstalacao externa"], "pontos": 2.0}}

Exemplo 3 (Retirada):
Texto: "...Foi realizado a retirada completa dos equipamentos em comodato..."
Sua Resposta: {{"is_os": true, "cliente": "Nome do Cliente", "servicos": ["retirada"], "pontos": 1.0}}

Regras de formatação finais:
- Retorne APENAS um objeto JSON válido.

Texto da O.S. para analisar:
""" + texto_os

    try:
        # === ESCADA DE TENTATIVAS ===
        # Lista dos modelos mais estáveis, ignorando o 2.5 que está bloqueado para sua conta
        modelos_seguros = [
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-1.0-pro'
        ]
        
        response = None
        modelo_usado = None
        
        for nome_modelo in modelos_seguros:
            try:
                logger.info(f"Tentando usar o modelo: {nome_modelo}")
                model = genai.GenerativeModel(nome_modelo)
                response = model.generate_content(prompt)
                modelo_usado = nome_modelo
                break  # Se deu certo e não deu erro 404, para o loop!
            except Exception as e:
                logger.warning(f"Erro no modelo {nome_modelo}, tentando o próximo... ({e})")
                continue  # Tenta o próximo da lista
        
        if not response:
            logger.error("Todos os modelos seguros falharam. Verifique sua chave de API.")
            return {"is_os": False}
            
        texto_resposta = response.text.strip()
        logger.info(f"Sucesso! IA processou usando [{modelo_usado}]. Resposta bruta: {texto_resposta}")
        
        # Limpeza robusta (remove formatações Markdown, se houver)
        texto_limpo = texto_resposta.replace('```json', '').replace('```', '').strip()
        
        # Busca apenas a parte que é o JSON usando Expressão Regular
        match = re.search(r'\{.*\}', texto_limpo, re.DOTALL)
        if match:
            dados = json.loads(match.group(0))
            return dados
        else:
            logger.error("A IA não retornou um bloco de chaves JSON.")
            return {"is_os": False}

    except Exception as e:
        logger.error(f"Erro geral no processamento da nuvem do Gemini: {e}")
        return {"is_os": False}
