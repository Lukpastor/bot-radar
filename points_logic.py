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
    Usa a IA do Gemini para analisar o texto da O.S. e extrair cliente e serviço.
    A pontuação é calculada de forma determinística pelo Python.
    """
    if not API_KEY:
        logger.error("GEMINI_API_KEY não configurada.")
        return {"is_os": False}

    # Passamos apenas as chaves (nomes dos serviços) para a IA, sem os valores
    nomes_servicos_permitidos = list(pontos_os.keys())

    prompt = f"""
Você é um sistema de computador. Retorne APENAS um objeto JSON válido.
Sua tarefa é analisar o texto enviado pelo técnico e retornar o JSON estrito contendo:
1. "is_os": true se for um relatório de serviço válido.
2. "cliente": O nome do cliente extraído do texto.
3. "servicos": Uma lista contendo EXATAMENTE UM nome exato de serviço.

Lista de serviços permitidos que você pode escolher:
{json.dumps(nomes_servicos_permitidos, ensure_ascii=False, indent=2)}

Sinônimos para ajudar a identificar os serviços:
{json.dumps(sinonimos, ensure_ascii=False, indent=2)}

🚨 REGRAS CRÍTICAS:
1. IDENTIFICAÇÃO DE O.S.: Se tiver dados como Nome, RX, Teste de velocidade ou OLT, É UMA O.S. VÁLIDA ("is_os": true).
2. RESOLUÇÃO DE CONFLITOS: A descrição da O.S. sempre vence o cabeçalho se houver divergência de serviços.

=== GABARITO (EXEMPLOS DE RESPOSTA) ===
Exemplo: {{"is_os": true, "cliente": "Nome do Cliente", "servicos": ["visita improdutiva"]}}

Texto da O.S. para analisar:
""" + texto_os

    try:
        modelos_google = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelos_google.append(m.name.replace('models/', ''))
        
        modelos_prioridade = [
            'gemini-3.5-flash',
            'gemini-flash-latest',
            'gemini-pro-latest',
            'gemini-3.1-flash-lite'
        ]
        
        modelos_para_testar = []
        
        for p in modelos_prioridade:
            if p in modelos_google:
                modelos_para_testar.append(p)
                
        for m in modelos_google:
            if m not in modelos_para_testar:
                if "vision" not in m and "embedding" not in m and "aqa" not in m and "gemma" not in m and "tts" not in m:
                    modelos_para_testar.append(m)
        
        response = None
        modelo_usado = None
        
        for nome_modelo in modelos_para_testar:
            try:
                model = genai.GenerativeModel(nome_modelo)
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.0,
                        response_mime_type="application/json"
                    )
                )
                modelo_usado = nome_modelo
                break
            except Exception as e:
                logger.warning(f"Erro no modelo {nome_modelo}, ignorando...")
                continue
        
        if not response:
            logger.error("Nenhum modelo compatível com JSON foi encontrado.")
            return {"is_os": False}
            
        texto_resposta = response.text.strip()
        logger.info(f"Sucesso! IA processou usando [{modelo_usado}]. Resposta bruta: {texto_resposta}")
        
        match = re.search(r'\{.*\}', texto_resposta, re.DOTALL)
        if match:
            dados = json.loads(match.group(0))
        else:
            dados = json.loads(texto_resposta)

        # ==========================================
        # CÁLCULO DE PONTOS DETERMINÍSTICO (PYTHON)
        # ==========================================
        if dados.get("is_os") and dados.get("servicos"):
            nome_servico = dados["servicos"][0]
            # Busca o valor real no dicionário do config.py (se não achar, dá 0.0)
            pontos_calculados = pontos_os.get(nome_servico, 0.0)
            dados["pontos"] = pontos_calculados
        else:
            dados["pontos"] = 0.0
            
        return dados

    except Exception as e:
        logger.error(f"Erro geral no processamento: {e}")
        return {"is_os": False}
