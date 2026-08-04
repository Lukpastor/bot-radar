import os
import re
import json
import unicodedata
from dotenv import load_dotenv

from config import pontos_os, sinonimos, CATEGORIAS_ORDENADAS, logger

from google import genai
from google.genai import types


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    client = None
    logger.error("GEMINI_API_KEY não configurada no arquivo .env!")


def normalizar_texto(texto: str) -> str:
    """
    Padroniza texto para facilitar comparações:
    - coloca em minúsculas;
    - remove acentos;
    - remove pontuação;
    - remove espaços duplicados.
    """
    if not isinstance(texto, str):
        return ""

    texto = texto.strip().lower()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def localizar_servico(servico_ia: str) -> str | None:
    """
    Converte o serviço retornado pela IA para a chave oficial
    existente em pontos_os.
    """
    servico_normalizado = normalizar_texto(servico_ia)

    # 1. Procura diretamente nas categorias oficiais
    for categoria_oficial in pontos_os:
        if normalizar_texto(categoria_oficial) == servico_normalizado:
            return categoria_oficial

    # 2. Procura nos sinônimos
    for categoria_oficial, lista_sinonimos in sinonimos.items():
        if categoria_oficial not in pontos_os:
            logger.warning(
                f"Categoria de sinônimo não existe em pontos_os: "
                f"{categoria_oficial!r}"
            )
            continue

        for sinonimo in lista_sinonimos:
            if normalizar_texto(sinonimo) == servico_normalizado:
                return categoria_oficial

    return None


def detectar_servico_localmente(texto_os: str) -> str | None:
    """
    Detecta serviços muito claros antes de chamar a IA.

    Isso evita falhas para textos explícitos como:
    'Reativação de fibra óptica realizada'.
    """
    texto_normalizado = normalizar_texto(texto_os)

    expressoes_reativacao = [
        "reativacao de fibra optica realizada",
        "reativacao de fibra realizada",
        "fibra reativada",
        "cliente reativado",
        "servico reativado",
        "reativacao realizada",
    ]

    if any(
        expressao in texto_normalizado
        for expressao in expressoes_reativacao
    ):
        # Localiza automaticamente a categoria oficial correta
        candidatos = [
            "reativação fibra",
            "reativação",
            "reativacao fibra",
        ]

        for candidato in candidatos:
            servico = localizar_servico(candidato)

            if servico:
                return servico

    return None


def processar_com_ia(texto_os: str) -> dict:
    """
    Analisa a O.S., extrai o cliente, identifica um único serviço
    e calcula os pontos diretamente no Python.
    """
    resultado_padrao = {
        "is_os": False,
        "cliente": "",
        "servicos": [],
        "pontos": 0.0,
    }

    if not client:
        logger.error("Cliente Gemini não está configurado.")
        return resultado_padrao

    if not isinstance(texto_os, str) or not texto_os.strip():
        logger.warning("Texto da O.S. vazio ou inválido.")
        return resultado_padrao

    nomes_servicos_permitidos = list(pontos_os.keys())

    # Ajuda determinística para serviços muito explícitos
    servico_detectado_localmente = detectar_servico_localmente(texto_os)

    prompt = f"""
Você é um classificador de ordens de serviço de um provedor de internet.

Retorne somente o JSON solicitado.

Sua tarefa:

1. Definir "is_os" como true quando o texto for um relatório de serviço.
2. Extrair o nome completo do cliente.
3. Escolher exatamente UM serviço da lista permitida.
4. Nunca criar outro nome de serviço.

SERVIÇOS PERMITIDOS:

{json.dumps(
    nomes_servicos_permitidos,
    ensure_ascii=False,
    indent=2
)}

SINÔNIMOS:

{json.dumps(
    sinonimos,
    ensure_ascii=False,
    indent=2
)}

REGRAS CRÍTICAS:

- Se houver nome do cliente, ONT, MAC, caixa, OLT, RX,
  teste de velocidade ou descrição do serviço, considere uma O.S.
- A descrição do serviço executado vence cabeçalhos conflitantes.
- "Reativação de fibra óptica realizada" significa reativação.
- O campo "servicos" deve conter exatamente um item.
- O item deve ser copiado exatamente da lista permitida.

TEXTO DA O.S.:

{texto_os}
"""

    # Use somente identificadores realmente disponíveis na sua conta.
    modelos_para_testar = [
        "gemini-3.5-flash",
        "gemini-2.5-flash",
    ]

    response = None
    modelo_usado = None

    for nome_modelo in modelos_para_testar:
        try:
            resposta_modelo = client.models.generate_content(
                model=nome_modelo,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "is_os": {
                                "type": "boolean"
                            },
                            "cliente": {
                                "type": "string"
                            },
                            "servicos": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 1,
                                "items": {
                                    "type": "string",
                                    "enum": nomes_servicos_permitidos,
                                },
                            },
                        },
                        "required": [
                            "is_os",
                            "cliente",
                            "servicos",
                        ],
                        "additionalProperties": False,
                    },
                ),
            )

            # Não basta existir um objeto response.
            # É necessário ele possuir texto.
            if resposta_modelo and resposta_modelo.text:
                response = resposta_modelo
                modelo_usado = nome_modelo
                break

            logger.warning(
                f"Modelo {nome_modelo} respondeu sem conteúdo."
            )

        except Exception as erro_modelo:
            logger.warning(
                f"Erro no modelo {nome_modelo}: {erro_modelo}"
            )

    if not response or not response.text:
        logger.error("Nenhum modelo retornou uma resposta válida.")
        return resultado_padrao

    try:
        texto_resposta = response.text.strip()

        logger.info(
            f"IA processou usando [{modelo_usado}]. "
            f"Resposta bruta: {texto_resposta}"
        )

        dados = json.loads(texto_resposta)

    except json.JSONDecodeError as erro_json:
        logger.error(
            f"JSON inválido retornado pela IA: {erro_json}. "
            f"Conteúdo recebido: {response.text!r}"
        )
        return resultado_padrao

    except Exception as erro:
        logger.exception(
            f"Erro ao ler resposta da IA: {erro}"
        )
        return resultado_padrao

    if not isinstance(dados, dict):
        logger.warning("A resposta da IA não é um objeto JSON.")
        return resultado_padrao

    is_os = dados.get("is_os") is True
    cliente = str(dados.get("cliente", "")).strip()
    servicos_retornados = dados.get("servicos", [])

    if not is_os:
        return {
            "is_os": False,
            "cliente": cliente,
            "servicos": [],
            "pontos": 0.0,
        }

    if not isinstance(servicos_retornados, list):
        logger.warning(
            f"'servicos' não é uma lista: "
            f"{servicos_retornados!r}"
        )
        return resultado_padrao

    if len(servicos_retornados) != 1:
        logger.warning(
            f"A IA retornou quantidade inválida de serviços: "
            f"{servicos_retornados!r}"
        )
        return resultado_padrao

    servico_retornado = servicos_retornados[0]

    if not isinstance(servico_retornado, str):
        logger.warning(
            f"Nome do serviço não é uma string: "
            f"{servico_retornado!r}"
        )
        return resultado_padrao

    servico_oficial = localizar_servico(servico_retornado)

    # Se a IA falhar no nome, usa a detecção determinística
    if not servico_oficial and servico_detectado_localmente:
        servico_oficial = servico_detectado_localmente

        logger.info(
            f"Serviço corrigido pela detecção local: "
            f"{servico_oficial}"
        )

    if not servico_oficial:
        logger.warning(
            f"Serviço não reconhecido: {servico_retornado!r}"
        )
        return resultado_padrao

    pontos_calculados = float(
        pontos_os.get(servico_oficial, 0.0)
    )

    return {
        "is_os": True,
        "cliente": cliente,
        "servicos": [servico_oficial],
        "pontos": pontos_calculados,
        "modelo": modelo_usado,
    }
