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
    Usa a IA do Gemini para analisar o texto da O.S. e extrair cliente e serviço.
    Versão Otimizada: Sem chamadas extras de lista para evitar Timeout no Telegram.
    """
    if not API_KEY:
        logger.error("GEMINI_API_KEY não configurada.")
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
        # === MODO TURBO ATIVADO ===
        # Removemos a busca demorada (list_models).
        # Vamos direto para os modelos que sabemos que funcionam na sua chave, na ordem de velocidade.
        modelos_para_testar = [
            'gemini-3.5-flash',
            'gemini-flash-latest',
            'gemini-pro-latest'
        ]
        
        response = None
        modelo_usado = None
        
        # Testa a lista estática diretamente
        for nome_modelo in modelos_para_testar:
            try:
                model = genai.GenerativeModel(nome_modelo)
                
                # Força a entrega de JSON puro e zera a temperatura
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
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
            nome_servico = dados["servicos"][0].strip()

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
