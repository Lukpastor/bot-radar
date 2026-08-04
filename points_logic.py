import os
import re
import json
import unicodedata
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import (
    pontos_os,
    sinonimos,
    CATEGORIAS_ORDENADAS,
    logger,
)


# ==========================================
# CONFIGURAÇÃO
# ==========================================
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

# Você pode substituir no .env:
#
# GEMINI_MODELS=gemini-3.5-flash-lite,gemini-3.6-flash
#
MODELOS_ENV = os.getenv(
    "GEMINI_MODELS",
    "gemini-3.5-flash-lite,gemini-3.6-flash",
)

MODELOS_PREFERIDOS = [
    modelo.strip()
    for modelo in MODELOS_ENV.split(",")
    if modelo.strip()
]

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    client = None
    logger.error(
        "GEMINI_API_KEY não configurada no arquivo .env!"
    )


# ==========================================
# RESULTADO PADRÃO
# ==========================================
def criar_resultado_padrao(
    erro: str | None = None,
) -> dict[str, Any]:
    resultado = {
        "is_os": False,
        "cliente": "",
        "servicos": [],
        "pontos": 0.0,
    }

    if erro:
        resultado["erro"] = erro

    return resultado


# ==========================================
# NORMALIZAÇÃO DE TEXTO
# ==========================================
def normalizar_texto(texto: Any) -> str:
    """
    Normaliza textos para comparação:

    - converte para minúsculas;
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

    texto = re.sub(
        r"[^a-z0-9\s]",
        " ",
        texto,
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


# ==========================================
# VALIDAÇÃO DA CONFIGURAÇÃO
# ==========================================
def validar_configuracao_ia() -> None:
    """
    Confere se todas as categorias usadas nos sinônimos
    e na ordem existem em pontos_os.
    """
    categorias_pontos = set(pontos_os)
    categorias_sinonimos = set(sinonimos)
    categorias_ordenadas = set(CATEGORIAS_ORDENADAS)

    for categoria in sorted(
        categorias_sinonimos - categorias_pontos
    ):
        logger.warning(
            "Categoria existente em sinonimos, mas ausente "
            f"em pontos_os: {categoria!r}"
        )

    for categoria in sorted(
        categorias_ordenadas - categorias_pontos
    ):
        logger.warning(
            "Categoria existente em CATEGORIAS_ORDENADAS, "
            f"mas ausente em pontos_os: {categoria!r}"
        )


validar_configuracao_ia()


# ==========================================
# LOCALIZAÇÃO DO SERVIÇO OFICIAL
# ==========================================
def localizar_servico(
    servico_ia: Any,
) -> str | None:
    """
    Transforma o nome retornado pela IA em uma categoria
    oficial existente em pontos_os.
    """
    servico_normalizado = normalizar_texto(servico_ia)

    if not servico_normalizado:
        return None

    # Primeiro compara com os nomes oficiais.
    for categoria_oficial in pontos_os:
        if (
            normalizar_texto(categoria_oficial)
            == servico_normalizado
        ):
            return categoria_oficial

    # Depois compara com os sinônimos.
    for categoria_oficial, lista_sinonimos in sinonimos.items():
        if categoria_oficial not in pontos_os:
            continue

        if not isinstance(lista_sinonimos, list):
            continue

        for sinonimo in lista_sinonimos:
            if (
                normalizar_texto(sinonimo)
                == servico_normalizado
            ):
                return categoria_oficial

    return None


# ==========================================
# IDENTIFICAÇÃO LOCAL DE O.S.
# ==========================================
def texto_parece_os(texto_os: str) -> bool:
    """
    Verifica se o texto possui campos típicos de uma O.S.
    """
    texto = normalizar_texto(texto_os)

    indicadores = [
        "nome do cliente",
        "cliente",
        "modelo da ont",
        "modelo da onu",
        "mac",
        "numero da caixa",
        "caixa",
        "cto",
        "olt",
        "potencia de rx",
        "potencia rx",
        "teste de velocidade",
        "tipo e suporte",
        "servico realizado",
    ]

    quantidade = sum(
        1
        for indicador in indicadores
        if indicador in texto
    )

    # Dois indicadores já tornam o texto bastante provável
    # de ser uma O.S.
    return quantidade >= 2


# ==========================================
# EXTRAÇÃO LOCAL DO CLIENTE
# ==========================================
def limpar_nome_cliente(nome: str) -> str:
    """
    Limpa caracteres estranhos e limita o tamanho do nome.
    """
    nome = nome.strip()

    # Evita capturar campos colocados na mesma linha.
    separadores = [
        "|",
        ";",
        " user:",
        " usuário:",
        " usuario:",
        " senha:",
        " olt:",
        " rx:",
        " mac:",
    ]

    nome_minusculo = nome.lower()

    for separador in separadores:
        posicao = nome_minusculo.find(separador)

        if posicao != -1:
            nome = nome[:posicao].strip()
            nome_minusculo = nome.lower()

    nome = re.sub(
        r"\s+",
        " ",
        nome,
    ).strip()

    # Remove pontuação no começo ou final.
    nome = nome.strip(" :-–—.,;|")

    if len(nome) > 120:
        nome = nome[:120].strip()

    return nome.upper()


def extrair_cliente_localmente(
    texto_os: str,
) -> str:
    """
    Extrai o nome a partir dos campos mais comuns.
    """
    padroes = [
        r"^\s*nome\s+do\s+cliente\s*:\s*(.+?)\s*$",
        r"^\s*nome\s+cliente\s*:\s*(.+?)\s*$",
        r"^\s*cliente\s*:\s*(.+?)\s*$",
        r"^\s*assinante\s*:\s*(.+?)\s*$",
        r"^\s*nome\s*:\s*(.+?)\s*$",
    ]

    for linha in texto_os.splitlines():
        linha = linha.strip()

        if not linha:
            continue

        for padrao in padroes:
            correspondencia = re.match(
                padrao,
                linha,
                flags=re.IGNORECASE,
            )

            if not correspondencia:
                continue

            nome = limpar_nome_cliente(
                correspondencia.group(1)
            )

            if nome:
                return nome

    return "NÃO INFORMADO"


# ==========================================
# DETECÇÃO LOCAL DO SERVIÇO
# ==========================================
def obter_categorias_em_ordem() -> list[str]:
    """
    Retorna primeiro as categorias definidas em
    CATEGORIAS_ORDENADAS e depois quaisquer categorias
    restantes de pontos_os.
    """
    resultado: list[str] = []

    for categoria in CATEGORIAS_ORDENADAS:
        if (
            categoria in pontos_os
            and categoria not in resultado
        ):
            resultado.append(categoria)

    for categoria in pontos_os:
        if categoria not in resultado:
            resultado.append(categoria)

    return resultado


def detectar_servico_localmente(
    texto_os: str,
) -> str | None:
    """
    Procura categorias e sinônimos diretamente no texto.

    Os sinônimos maiores são testados primeiro para evitar
    que uma frase específica seja confundida com outra
    categoria mais genérica.
    """
    texto_normalizado = normalizar_texto(texto_os)

    if not texto_normalizado:
        return None

    categorias_ordenadas = obter_categorias_em_ordem()

    for categoria in categorias_ordenadas:
        expressoes: list[str] = []

        # Inclui o próprio nome oficial.
        expressoes.append(categoria)

        lista_sinonimos = sinonimos.get(
            categoria,
            [],
        )

        if isinstance(lista_sinonimos, list):
            expressoes.extend(lista_sinonimos)

        expressoes_normalizadas = {
            normalizar_texto(expressao)
            for expressao in expressoes
            if normalizar_texto(expressao)
        }

        # Testa frases maiores primeiro.
        expressoes_ordenadas = sorted(
            expressoes_normalizadas,
            key=len,
            reverse=True,
        )

        for expressao in expressoes_ordenadas:
            if expressao in texto_normalizado:
                logger.info(
                    "Serviço detectado localmente | "
                    f"CATEGORIA={categoria}"
                )

                return categoria

    return None


# ==========================================
# FALLBACK LOCAL
# ==========================================
def processar_localmente(
    texto_os: str,
    servico_local: str | None = None,
) -> dict[str, Any]:
    """
    Processa a O.S. sem depender do Gemini.
    """
    if not texto_parece_os(texto_os):
        return criar_resultado_padrao(
            "Texto não identificado como O.S."
        )

    if not servico_local:
        servico_local = detectar_servico_localmente(
            texto_os
        )

    if not servico_local:
        return criar_resultado_padrao(
            "Serviço não identificado localmente."
        )

    if servico_local not in pontos_os:
        logger.warning(
            "Serviço local ausente em pontos_os: "
            f"{servico_local!r}"
        )

        return criar_resultado_padrao(
            "Categoria sem pontuação configurada."
        )

    cliente = extrair_cliente_localmente(
        texto_os
    )

    resultado = {
        "is_os": True,
        "cliente": cliente,
        "servicos": [servico_local],
        "pontos": float(
            pontos_os[servico_local]
        ),
        "modelo": "fallback-local",
    }

    logger.info(
        "O.S. processada pelo fallback local | "
        f"CLIENTE={cliente} | "
        f"SERVIÇO={servico_local} | "
        f"PONTOS={resultado['pontos']}"
    )

    return resultado


# ==========================================
# CLASSIFICAÇÃO DOS ERROS DA API
# ==========================================
def identificar_tipo_erro(
    erro: Exception,
) -> str:
    mensagem = str(erro).upper()

    if (
        "404" in mensagem
        or "NOT_FOUND" in mensagem
    ):
        return "modelo_indisponivel"

    if (
        "429" in mensagem
        or "RESOURCE_EXHAUSTED" in mensagem
        or "RATE LIMIT" in mensagem
    ):
        return "limite"

    if (
        "503" in mensagem
        or "UNAVAILABLE" in mensagem
        or "HIGH DEMAND" in mensagem
    ):
        return "temporario"

    if (
        "401" in mensagem
        or "403" in mensagem
        or "UNAUTHENTICATED" in mensagem
        or "PERMISSION_DENIED" in mensagem
        or "API_KEY_INVALID" in mensagem
    ):
        return "autenticacao"

    return "desconhecido"


# ==========================================
# SCHEMA DA RESPOSTA
# ==========================================
def criar_schema_resposta(
    nomes_servicos_permitidos: list[str],
) -> dict[str, Any]:
    """
    Cria o JSON Schema usado pelo Gemini.
    """
    return {
        "type": "object",
        "properties": {
            "is_os": {
                "type": "boolean",
            },
            "cliente": {
                "type": "string",
            },
            "servicos": {
                "type": "array",
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
    }


# ==========================================
# CRIAÇÃO DO PROMPT
# ==========================================
def criar_prompt(
    texto_os: str,
    nomes_servicos_permitidos: list[str],
) -> str:
    return f"""
Você é um classificador de ordens de serviço de um provedor de internet.

Analise o relatório e retorne somente o objeto JSON solicitado.

TAREFAS:

1. Defina "is_os" como true quando o texto for um relatório de serviço.
2. Extraia somente o nome completo do cliente.
3. Escolha exatamente UM serviço da lista permitida.
4. Copie o nome do serviço exatamente como aparece na lista.
5. Nunca invente categorias.
6. Nunca calcule pontos.

SERVIÇOS PERMITIDOS:

{json.dumps(
    nomes_servicos_permitidos,
    ensure_ascii=False,
    indent=2,
)}

SINÔNIMOS:

{json.dumps(
    sinonimos,
    ensure_ascii=False,
    indent=2,
)}

REGRAS IMPORTANTES:

- Nome, cliente, ONT, ONU, MAC, caixa, CTO, OLT, RX ou
  teste de velocidade são indicadores de uma O.S.
- A descrição do trabalho realizado vence um cabeçalho conflitante.
- "Reativação de fibra óptica realizada" corresponde a "reativação".
- Uma O.S. válida deve possuir exatamente um serviço.
- Uma mensagem que não for O.S. pode retornar uma lista vazia.
- Não inclua senhas, usuário PPPoE, MAC, RX, OLT ou outros dados
  dentro do campo "cliente".
- Retorne apenas JSON.

TEXTO DA O.S.:

{texto_os}
""".strip()


# ==========================================
# LEITURA SEGURA DA RESPOSTA
# ==========================================
def extrair_json_resposta(
    texto_resposta: str,
) -> dict[str, Any] | None:
    """
    Lê JSON puro ou remove blocos Markdown caso o modelo
    ainda retorne ```json.
    """
    if not isinstance(texto_resposta, str):
        return None

    texto_limpo = texto_resposta.strip()

    texto_limpo = texto_limpo.replace(
        "```json",
        "",
    ).replace(
        "```JSON",
        "",
    ).replace(
        "```",
        "",
    ).strip()

    try:
        dados = json.loads(texto_limpo)

        if isinstance(dados, dict):
            return dados

    except json.JSONDecodeError:
        pass

    # Segunda tentativa: busca o primeiro objeto JSON.
    inicio = texto_limpo.find("{")

    if inicio == -1:
        return None

    try:
        decoder = json.JSONDecoder()

        dados, _ = decoder.raw_decode(
            texto_limpo[inicio:]
        )

        if isinstance(dados, dict):
            return dados

    except json.JSONDecodeError:
        return None

    return None


# ==========================================
# VALIDAÇÃO DA RESPOSTA DA IA
# ==========================================
def validar_resposta_ia(
    dados: dict[str, Any],
    texto_os: str,
    modelo_usado: str,
    servico_local: str | None,
) -> dict[str, Any]:
    """
    Valida os dados retornados pela IA e calcula os pontos.
    """
    is_os = dados.get("is_os") is True

    cliente = str(
        dados.get("cliente", "")
    ).strip()

    servicos_retornados = dados.get(
        "servicos",
        [],
    )

    if not is_os:
        # Se a IA disser que não é O.S., mas o texto possui
        # indicadores e serviço claro, usa o fallback.
        if (
            servico_local
            and texto_parece_os(texto_os)
        ):
            logger.warning(
                "IA marcou como não O.S., mas o fallback "
                "local encontrou um serviço."
            )

            return processar_localmente(
                texto_os,
                servico_local,
            )

        return {
            "is_os": False,
            "cliente": cliente,
            "servicos": [],
            "pontos": 0.0,
            "modelo": modelo_usado,
        }

    if not isinstance(servicos_retornados, list):
        logger.warning(
            "Campo 'servicos' não é uma lista: "
            f"{servicos_retornados!r}"
        )

        if servico_local:
            return processar_localmente(
                texto_os,
                servico_local,
            )

        return criar_resultado_padrao(
            "Formato de serviços inválido."
        )

    if len(servicos_retornados) != 1:
        logger.warning(
            "Quantidade inválida de serviços: "
            f"{servicos_retornados!r}"
        )

        if servico_local:
            return processar_localmente(
                texto_os,
                servico_local,
            )

        return criar_resultado_padrao(
            "Quantidade de serviços inválida."
        )

    servico_retornado = servicos_retornados[0]

    servico_oficial = localizar_servico(
        servico_retornado
    )

    if not servico_oficial and servico_local:
        logger.info(
            "Serviço da IA corrigido pelo detector local | "
            f"IA={servico_retornado!r} | "
            f"LOCAL={servico_local!r}"
        )

        servico_oficial = servico_local

    if not servico_oficial:
        logger.warning(
            "Serviço não reconhecido: "
            f"{servico_retornado!r}"
        )

        return criar_resultado_padrao(
            "Serviço não reconhecido."
        )

    if servico_oficial not in pontos_os:
        logger.error(
            "Serviço reconhecido, mas ausente em pontos_os: "
            f"{servico_oficial!r}"
        )

        return criar_resultado_padrao(
            "Serviço sem pontuação configurada."
        )

    # Caso o cliente venha vazio, tenta extrair localmente.
    if not cliente:
        cliente = extrair_cliente_localmente(
            texto_os
        )
    else:
        cliente = limpar_nome_cliente(
            cliente
        )

    pontos_calculados = float(
        pontos_os[servico_oficial]
    )

    resultado = {
        "is_os": True,
        "cliente": cliente,
        "servicos": [servico_oficial],
        "pontos": pontos_calculados,
        "modelo": modelo_usado,
    }

    logger.info(
        "O.S. processada com sucesso | "
        f"MODELO={modelo_usado} | "
        f"CLIENTE={cliente} | "
        f"SERVIÇO={servico_oficial} | "
        f"PONTOS={pontos_calculados}"
    )

    return resultado


# ==========================================
# FUNÇÃO PRINCIPAL
# ==========================================
def processar_com_ia(
    texto_os: str,
) -> dict[str, Any]:
    """
    Processa uma O.S. usando Gemini e fallback local.

    Fluxo:

    1. Valida o texto.
    2. Detecta um possível serviço local.
    3. Tenta os modelos Gemini configurados.
    4. Valida o JSON.
    5. Calcula os pontos no Python.
    6. Se todos os modelos falharem, usa o fallback local.
    """
    if not isinstance(texto_os, str):
        return criar_resultado_padrao(
            "Texto recebido não é uma string."
        )

    texto_os = texto_os.strip()

    if not texto_os:
        return criar_resultado_padrao(
            "Texto da O.S. vazio."
        )

    servico_local = detectar_servico_localmente(
        texto_os
    )

    # Sem chave Gemini, ainda tenta processar localmente.
    if not client:
        logger.warning(
            "Gemini não configurado. Usando fallback local."
        )

        return processar_localmente(
            texto_os,
            servico_local,
        )

    nomes_servicos_permitidos = list(
        pontos_os.keys()
    )

    prompt = criar_prompt(
        texto_os,
        nomes_servicos_permitidos,
    )

    schema = criar_schema_resposta(
        nomes_servicos_permitidos
    )

    response = None
    modelo_usado = None

    for nome_modelo in MODELOS_PREFERIDOS:
        try:
            logger.info(
                f"Tentando modelo {nome_modelo}..."
            )

            resposta_modelo = (
                client.models.generate_content(
                    model=nome_modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type=(
                            "application/json"
                        ),
                        response_schema=schema,
                    ),
                )
            )

            if (
                resposta_modelo
                and resposta_modelo.text
                and resposta_modelo.text.strip()
            ):
                response = resposta_modelo
                modelo_usado = nome_modelo

                logger.info(
                    f"Modelo {nome_modelo} respondeu."
                )

                break

            logger.warning(
                f"Modelo {nome_modelo} respondeu sem texto."
            )

        except Exception as erro:
            tipo_erro = identificar_tipo_erro(
                erro
            )

            logger.warning(
                f"Erro no modelo {nome_modelo} | "
                f"TIPO={tipo_erro} | ERRO={erro}"
            )

            # Não aguarda: passa imediatamente ao próximo.
            continue

    # Todos os modelos falharam.
    if (
        not response
        or not response.text
        or not modelo_usado
    ):
        logger.error(
            "Todos os modelos Gemini falharam. "
            "Tentando fallback local."
        )

        return processar_localmente(
            texto_os,
            servico_local,
        )

    texto_resposta = response.text.strip()

    # Registra apenas a resposta estruturada da IA.
    # Não registra o texto original com senhas.
    logger.info(
        f"Resposta recebida de [{modelo_usado}]: "
        f"{texto_resposta}"
    )

    dados = extrair_json_resposta(
        texto_resposta
    )

    if not dados:
        logger.error(
            "Não foi possível extrair um JSON válido "
            "da resposta do Gemini."
        )

        return processar_localmente(
            texto_os,
            servico_local,
        )

    return validar_resposta_ia(
        dados=dados,
        texto_os=texto_os,
        modelo_usado=modelo_usado,
        servico_local=servico_local,
    )


# ==========================================
# TESTE MANUAL
# ==========================================
if __name__ == "__main__":
    texto_teste = """
Ont: Comodato
Modelo da ONT: Wifiber 1200R
MAC: 000000000000

Número da caixa: 05-041CER
Nome do cliente: JERBSON RODRIGUES COSTA
OLT: Carmo lojas

Reativação de fibra óptica realizada.
Potência de RX: -23 dBm.
Teste de velocidade: 789 Mbps.
"""

    resultado = processar_com_ia(
        texto_teste
    )

    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2,
        )
    )
