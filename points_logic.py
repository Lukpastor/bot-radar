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
1. "is_os": true se for um relatório de serviço válido, false caso contrário.
2. "cliente": O nome do cliente extraído do texto (se não achar, retorne "NÃO INFORMADO").
3. "servicos": Uma lista contendo EXATAMENTE UM nome exato de serviço, baseando-se estritamente na lista de permitidos.
4. "pontos": A pontuação do único serviço escolhido.

Lista de serviços permitidos e seus pontos:
{json.dumps(pontos_os, ensure_ascii=False, indent=2)}

Sinônimos e termos equivalentes para te ajudar a identificar os serviços:
{json.dumps(sinonimos, ensure_ascii=False, indent=2)}

🚨 REGRAS CRÍTICAS DE PONTUAÇÃO (PROIBIDO MISTURAR QUALQUER SERVIÇO):
- A O.S. DEVE TER APENAS UM ÚNICO SERVIÇO PRINCIPAL REGISTRADO. NUNCA retorne mais de um serviço na lista "servicos".
- É TERMINANTEMENTE PROIBIDO acumular, somar ou misturar QUALQUER tipo de serviço. 
- Se o texto do técnico mencionar várias palavras-chave diferentes (ex: reparo, mudança, instalação, visita, retirada), ESCOLHA APENAS O SERVIÇO MAIS IMPORTANTE/DE MAIOR VALOR e ignore completamente todos os outros.

=== GABARITO (EXEMPLOS DE COMO VOCÊ DEVE RESPONDER) ===

Exemplo 1 (Retirada de equipamento):
Texto: "...Foi realizado a retirada completa dos equipamentos em comodato. O conector foi retirado da caixa."
Sua Resposta: {{"is_os": true, "cliente": "Nome do Cliente", "servicos": ["retirada"], "pontos": 1.0}}

Exemplo 2 (Visita Improdutiva):
Texto: "...Visita improdutiva. Cabos estavam mal encaixados... O problema foi solucionado e o cliente orientado..."
Sua Resposta: {{"is_os": true, "cliente": "Nome do Cliente", "servicos": ["visita improdutiva"], "pontos": 1.0}}

Exemplo 3 (Reparo):
Texto: "...Conector estava danificado e foi realizado a troca. Potência de RX..."
Sua Resposta: {{"is_os": true, "cliente": "Nome do Cliente", "servicos": ["reparo"], "pontos": 1.0}}

Exemplo 4 (Mudança de Endereço sem sucesso / Retirada):
Texto: "...Não foi possível realizar a mudança de endereço por inviabilidade técnica... Foi retirado conector rápido da caixa."
Sua Resposta: {{"is_os": true, "cliente": "Nome do Cliente", "servicos": ["retirada"], "pontos": 1.0}}

Exemplo 5 (Instalação):
Texto: "...Instalação de fibra óptica realizada. Potência de RX: - 20 dbm..."
Sua Resposta: {{"is_os": true, "cliente": "Nome do Cliente", "servicos": ["instalacao"], "pontos": 2.0}}

Regras de formatação finais:
- Retorne APENAS um objeto JSON válido.

Texto da O.S. para analisar:
""" + texto_os

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        texto_resposta = response.text.strip()
        logger.info(f"Resposta bruta da IA: {texto_resposta}")
        
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
        logger.error(f"Erro ao processar JSON ou na nuvem do Gemini: {e}")
        return {"is_os": False}
