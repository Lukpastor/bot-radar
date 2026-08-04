import os
import json
from dotenv import load_dotenv
from config import pontos_os, sinonimos, CATEGORIAS_ORDENADAS, logger

# NOVO PACOTE DA GOOGLE
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    client = None
    logger.error("GEMINI_API_KEY não configurada no arquivo .env!")

def processar_com_ia(texto_os: str) -> dict:
    """
    Usa a IA do Gemini para analisar o texto da O.S. e extrair cliente e serviço.
    Versão Otimizada com a nova biblioteca google.genai e modelos fallback.
    """
    if not client:
        return {"is_os": False}

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
        # Modelos atualizados e à prova de falhas para testar
        modelos_para_testar = [
            'gemini-3.5-flash',
            'gemini-1.5-flash', # Excelente plano B (muito rápido e estável)
            'gemini-1.5-pro'    # Plano C (mais robusto, caso tudo falhe)
        ]
        
        response = None
        modelo_usado = None
        
        for nome_modelo in modelos_para_testar:
            try:
                # NOVA FORMA DE CHAMAR A GOOGLE
                response = client.models.generate_content(
                    model=nome_modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json"
                    )
                )
                modelo_usado = nome_modelo
                break  # Funcionou! Sai do loop.
            except Exception as e:
                logger.warning(f"Erro no modelo {nome_modelo}, ignorando... ({e})")
                continue
        
        if not response:
            logger.error("Nenhum modelo estático respondeu a tempo ou foi aceito.")
            return {"is_os": False}
            
        texto_resposta = response.text.strip()
        logger.info(f"Sucesso! IA processou usando [{modelo_usado}]. Resposta bruta: {texto_resposta}")
        
        # ==========================================
        # EXTRAÇÃO E VALIDAÇÃO ESTRUTURAL DE JSON
        # ==========================================
        texto_limpo = texto_resposta.replace('```json', '').replace('```', '').strip()
        
        try:
            start_idx = texto_limpo.find('{')
            if start_idx == -1:
                return {"is_os": False}
                
            texto_para_parse = texto_limpo[start_idx:]
            
            decoder = json.JSONDecoder()
            dados, _ = decoder.raw_decode(texto_para_parse)
            
            if not isinstance(dados, dict):
                return {"is_os": False}
                
            chaves_esperadas = ["is_os", "cliente", "servicos"]
            if not all(chave in dados for chave in chaves_esperadas):
                return {"is_os": False}
                
        except Exception as e:
            logger.error(f"Falha na validação do JSON: {e}")
            return {"is_os": False}

        # ==========================================
        # CÁLCULO DE PONTOS DETERMINÍSTICO (PYTHON)
        # ==========================================
        if dados.get("is_os") and dados.get("servicos"):
            # AQUI ESTÁ A CORREÇÃO (.lower()) PARA NÃO RECUSAR LETRAS MAIÚSCULAS
            nome_servico = dados["servicos"][0].strip().lower()

            if nome_servico not in pontos_os:
                logger.warning(f"Serviço inválido retornado pela IA: {nome_servico}")
                return {"is_os": False}

            dados["pontos"] = pontos_os[nome_servico]
        else:
            dados["pontos"] = 0.0
            
        return dados

    except Exception as e:
        logger.error(f"Erro geral no processamento: {e}")
        return {"is_os": False}
