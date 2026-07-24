import os
import json
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
1. "is_os": true se for um relatório de serviço válido, false caso contrário.
2. "cliente": O nome do cliente extraído do texto (se não achar, retorne "NÃO INFORMADO").
3. "servicos": Uma lista com os nomes exatos dos serviços encontrados, baseando-se estritamente na lista de serviços permitidos abaixo.
4. "pontos": A soma total dos pontos correspondentes aos serviços encontrados.

Lista de serviços permitidos e seus pontos:
{json.dumps(pontos_os, ensure_ascii=False, indent=2)}

Sinônimos e termos equivalentes para te ajudar a identificar os serviços:
{json.dumps(sinonimos, ensure_ascii=False, indent=2)}

Regras importantes:
- Retorne APENAS um objeto JSON válido, sem blocos de código em markdown (como ```json), sem texto antes e sem texto depois.
- Formato esperado de saída:
{{"is_os": true, "cliente": "Nome do Cliente", "servicos": ["reparo"], "pontos": 1.0}}

Texto da O.S. para analisar:
""" + texto_os

    try:
        # Atualizado para o modelo padrão atual da API do Google
        model = genai.GenerativeModel('gemini-3.5-flash')
        response = model.generate_content(prompt)
        
        texto_resposta = response.text.strip()
        
        # Remove eventuais marcações de markdown caso a IA coloque
        if texto_resposta.startswith("```json"):
            texto_resposta = texto_resposta[7:]
        if texto_resposta.endswith("```"):
            texto_resposta = texto_resposta[:-3]
            
        dados = json.loads(texto_resposta.strip())
        return dados

    except Exception as e:
        logger.error(f"Erro na nuvem do Gemini: {e}")
        return {"is_os": False}
