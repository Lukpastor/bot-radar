import os
import logging
from dotenv import load_dotenv


# ==========================================
# VARIÁVEIS DE AMBIENTE
# ==========================================

# Localmente, lê o arquivo .env.
# No Railway, as variáveis são carregadas
# automaticamente pelo painel Variables.
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN não encontrado nas variáveis de ambiente."
    )

if not GEMINI_API_KEY:
    logging.warning(
        "GEMINI_API_KEY não encontrada nas variáveis de ambiente."
    )


# ==========================================
# CONFIGURAÇÃO DE LOGS
# ==========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# Reduz logs repetitivos do Telegram/httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ==========================================
# SEGURANÇA: ID DO DONO
# ==========================================
MASTER_ID = 1379071981

META_MENSAL = 160


# ==========================================
# REGRAS DE NEGÓCIO E PONTUAÇÕES
# ==========================================
pontos_os = {
    # Infraestrutura
    "infra - instalação": 4,
    "infra - reparo": 2,
    "infra - retirada": 2,
    "infra - troca": 2,
    "infra - verificação": 1,
    "infra - deslocamento": 1,

    # Atendimento ao cliente
    "instalação fibra": 2.5,
    "instalação wireless": 2,
    "instalação de cabo de rede": 2,

    "reativação": 2,
    "reparo": 1,
    "troca de drop": 1,
    "troca de ont/onu/roteador": 0.0,

    "retirada fibra": 1,
    "retirada wireless": 1,
    "retirada": 1,

    "visita improdutiva": 1,
    "configuração": 1,
    "renovação": 1,

    "mudança de titularidade": 2.5,
    "mudança de endereço": 2.5,

    "suporte extra": 0.0,
    "migração de torre": 1,
    "periódico": 1,
}


# ==========================================
# DICIONÁRIO DE SINÔNIMOS
# ==========================================
sinonimos = {
    # ======================================
    # INSTALAÇÃO DE FIBRA
    # ======================================
    "instalação fibra": [
        "instalação de fibra",
        "instalacao de fibra",
        "instalação fibra",
        "instalacao fibra",
        "instalação de fibra óptica",
        "instalacao de fibra optica",
        "instalação de fibra óptica realizada",
        "instalacao de fibra optica realizada",
        "fibra óptica instalada",
        "fibra optica instalada",
        "passagem de fibra",
        "ponto fibra novo",
        "instalação de rede de fibra",
        "instalacao de rede de fibra",
        "instalação realizada",
        "instalacao realizada",
        "ponto novo",
        "cliente novo",
        "ativação de cliente",
        "ativacao de cliente",
        "ativação de serviço",
        "ativacao de servico",
        "nova instalação",
        "nova instalacao",
        "instalação de onu em comodato realizada",
        "instalacao de onu em comodato realizada",
        "instalação de ont em comodato realizada",
        "instalacao de ont em comodato realizada",
        "instalação de roteador em comodato realizada",
        "instalacao de roteador em comodato realizada",
        "instalação de roteador do cliente realizada",
        "instalacao de roteador do cliente realizada",
        "foi necessário refazer a instalação dos equipamentos",
        "foi necessario refazer a instalacao dos equipamentos",
        "reinstalação externa realizada",
        "reinstalacao externa realizada",
        "refazer a instalação externa",
        "refazer a instalacao externa",
    ],

    # ======================================
    # RETIRADA DE FIBRA
    # ======================================
    "retirada fibra": [
        "remoção de fibra",
        "remocao de fibra",
        "fibra óptica retirada",
        "fibra optica retirada",
        "cabo de fibra retirado",
        "desativação de fibra",
        "desativacao de fibra",
        "desconexão de fibra",
        "desconexao de fibra",
        "retirada de fibra",
        "retirada da ont em comodato",
        "retirada da onu em comodato",
        "retirada da onu/ont em comodato",
        "retirada da ont/onu em comodato",
        "retirada completa dos equipamentos em comodato",
        "o conector foi retirado da caixa",
        "tipo e suporte: retirada",
        "tipo e suporte:retirada",
        "retirada de fibra óptica",
        "retirada de fibra optica",
    ],

    # ======================================
    # REPARO
    # ======================================
    "reparo": [
        "tipo e suporte: reparo",
        "tipo e suporte:reparo",
        "tipo e suporte: fibra reparo",
        "tipo e suporte:fibra reparo",
        "manutenção",
        "manutencao",
        "conserto",
        "restabelecimento",
        "falha resolvida",
        "problema corrigido",
        "sinal restabelecido",
        "sinal reestabelecido",
        "reparo realizado",
        "reparo de fibra",
        "reparo fibra",
        "rompimento de fibra local",
        "houve um rompimento de fibra local",
        "cabos estavam invertidos",
        "cabos estavam mal encaixados",
        "equipamentos estavam desligados",
        "equipamentos foram resetados pelo cliente",
        "equipamentos resetados por queda de energia",
        "velocidade está conforme o contratado",
        "velocidade esta conforme o contratado",
        "conector estava danificado",
        "troca de conector",
        "cabo de rede danificado",
        "roteador do cliente com defeito",
        "reinstalação interna",
        "reinstalacao interna",
        "roteador do cliente incompatível",
        "roteador do cliente incompativel",
        "onu com defeito",
        "ont com defeito",
        "plano incompatível com a utilização",
        "plano incompativel com a utilizacao",
        "não há problemas locais",
        "nao ha problemas locais",
        "internet restabelecida",
        "conexão restabelecida",
        "conexao restabelecida",
    ],

    # ======================================
    # VISITA IMPRODUTIVA
    # ======================================
    "visita improdutiva": [
        "visita improdutiva",
        "não foi encontrado nenhum problema",
        "nao foi encontrado nenhum problema",
        "nenhum problema encontrado",
        "internet já estava normal",
        "internet ja estava normal",
        "funcionando normal",
        "tudo normal",
        "aparentemente o notebook do cliente está com problema",
        "aparentemente o notebook do cliente esta com problema",
        "aparentemente o desktop do cliente está com problema",
        "aparentemente o desktop do cliente esta com problema",
        "aparentemente o notebook/desktop do cliente está com problema",
        "aparentemente o notebook/desktop do cliente esta com problema",
        "aparentemente roteador está com mau funcionamento",
        "aparentemente roteador esta com mau funcionamento",
        "problema no equipamento do cliente",
        "tvbox",
        "tv box",
        "assistência técnica",
        "assistencia tecnica",
    ],

    # ======================================
    # REATIVAÇÃO
    # ======================================
    "reativação": [
        "reativação",
        "reativacao",
        "reativação realizada",
        "reativacao realizada",
        "reativação de fibra",
        "reativacao de fibra",
        "reativação de fibra óptica",
        "reativacao de fibra optica",
        "reativação de fibra óptica realizada",
        "reativacao de fibra optica realizada",
        "reativação de serviço",
        "reativacao de servico",
        "cliente reativado",
        "serviço reativado",
        "servico reativado",
        "fibra reativada",
    ],
        # ======================================
    # MUDANÇA DE ENDEREÇO
    # ======================================
    "mudança de endereço": [
        "alteração de endereço",
        "alteracao de endereco",
        "mudança de endereço",
        "mudanca de endereco",
        "mudança de local",
        "mudanca de local",
        "transferência de ponto",
        "transferencia de ponto",
        "relocação",
        "relocacao",
        "mudança de endereço realizada",
        "mudanca de endereco realizada",
        "mudança de cômodo realizada",
        "mudanca de comodo realizada",
        "mudanças de endereço",
        "mudancas de endereco",
    ],

    # ======================================
    # TROCA DE ONT, ONU OU ROTEADOR
    # ======================================
    "troca de ont/onu/roteador": [
        "substituição de ont",
        "substituicao de ont",
        "substituição de onu",
        "substituicao de onu",
        "ont trocada",
        "onu trocada",
        "troca de ont",
        "troca de onu",
        "roteador trocado",
        "troca de roteador",
        "substituição de roteador",
        "substituicao de roteador",
        "mudança de equipamento",
        "mudanca de equipamento",
        "troca de equipamento",
        "troca de aparelho",
        "troca de modem",
        "troca de roteador realizada",
        "troca de ont realizada",
        "troca de onu realizada",
        "tipo e suporte: troca de equipamento",
        "tipo e suporte:troca de equipamento",
        "onu está com defeito",
        "onu esta com defeito",
        "ont está com defeito",
        "ont esta com defeito",
        "roteador está com defeito",
        "roteador esta com defeito",
        "roteador em comodato está com defeito",
        "roteador em comodato esta com defeito",
        "roteador em comodato está com defeito apresentando quedas no tráfego",
        "roteador em comodato esta com defeito apresentando quedas no trafego",
        "é necessário fazer a troca",
        "e necessario fazer a troca",
        "necessário fazer a troca",
        "necessario fazer a troca",
    ],

    # ======================================
    # CONFIGURAÇÃO
    # ======================================
    "configuração": [
        "configuração",
        "configuracao",
        "configuração de roteador efetuada",
        "configuracao de roteador efetuada",
        "configuração realizada",
        "configuracao realizada",
        "config de roteador",
        "roteador configurado",
        "ajuste de configuração",
        "ajuste de configuracao",
        "configuração de rede",
        "configuracao de rede",
        "configuração de wi-fi",
        "configuracao de wi-fi",
        "configuração de wifi",
        "configuracao de wifi",
        "ajuste técnico",
        "ajuste tecnico",
        "ajuste no roteador",
        "configurar internet",
        "instalação e alteração de login e senha realizada",
        "instalacao e alteracao de login e senha realizada",
        "configuração padrão dos equipamentos",
        "configuracao padrao dos equipamentos",
        "reconfiguração foi realizada",
        "reconfiguracao foi realizada",
        "mudança de senha de roteador efetuada",
        "mudanca de senha de roteador efetuada",
        "alteração de senha do wi-fi",
        "alteracao de senha do wi-fi",
        "alteração de senha do wifi",
        "alteracao de senha do wifi",
    ],

    # ======================================
    # TROCA DE DROP
    # ======================================
    "troca de drop": [
        "tipo e suporte: troca de drop",
        "tipo e suporte:troca de drop",
        "substituição de drop",
        "substituicao de drop",
        "troca de cabo drop",
        "drop substituído",
        "drop substituido",
        "cabo drop trocado",
        "mudança de drop",
        "mudanca de drop",
        "substituição de cabo drop",
        "substituicao de cabo drop",
        "troca do drop",
        "drop danificado",
        "drop rompido",
    ],

    # ======================================
    # RENOVAÇÃO
    # ======================================
    "renovação": [
        "renovação",
        "renovacao",
        "tipo e suporte: renovação",
        "tipo e suporte:renovação",
        "tipo e suporte: renovacao",
        "tipo e suporte:renovacao",
        "contrato renovado",
        "renovação de contrato",
        "renovacao de contrato",
        "renovação de plano",
        "renovacao de plano",
        "contrato expirado",
        "renovação realizada",
        "renovacao realizada",
        "fibra renova",
    ],

    # ======================================
    # MUDANÇA DE TITULARIDADE
    # ======================================
    "mudança de titularidade": [
        "transferência de titularidade",
        "transferencia de titularidade",
        "alteração de titular",
        "alteracao de titular",
        "troca de nome",
        "mudança de cliente",
        "mudanca de cliente",
        "alteração de cpf",
        "alteracao de cpf",
        "mudança de titularidade realizada",
        "mudanca de titularidade realizada",
    ],

    # ======================================
    # MIGRAÇÃO DE TORRE
    # ======================================
    "migração de torre": [
        "migração de torre",
        "migracao de torre",
        "mudança de torre",
        "mudanca de torre",
        "migração de ap",
        "migracao de ap",
        "troca de torre",
        "alteração de torre",
        "alteracao de torre",
        "mudança de equipamento de torre",
        "mudanca de equipamento de torre",
    ],

    # ======================================
    # INSTALAÇÃO WIRELESS
    # ======================================
    "instalação wireless": [
        "instalação wireless",
        "instalacao wireless",
        "instalação wi-fi",
        "instalacao wi-fi",
        "instalação wifi",
        "instalacao wifi",
        "antena wireless instalada",
        "ponto wireless novo",
        "wi-fi instalado",
        "wifi instalado",
        "instalação de rádio",
        "instalacao de radio",
        "instalação de cliente wireless",
        "instalacao de cliente wireless",
        "ponto de acesso novo",
        "rádio instalado",
        "radio instalado",
    ],

    # ======================================
    # PERIÓDICO / PREVENTIVO
    # ======================================
    "periódico": [
        "periódico",
        "periodico",
        "manutenção periódica",
        "manutencao periodica",
        "verificação programada",
        "verificacao programada",
        "checagem de rotina",
        "revisão",
        "revisao",
        "visita periódica",
        "visita periodica",
        "vistoria",
        "manutenção preventiva",
        "manutencao preventiva",
        "preventivo",
    ],

    # ======================================
    # RETIRADA WIRELESS
    # ======================================
    "retirada wireless": [
        "retirada wireless",
        "remoção wireless",
        "remocao wireless",
        "antena wireless retirada",
        "desinstalação wireless",
        "desinstalacao wireless",
        "desativação de rádio",
        "desativacao de radio",
        "desconexão wireless",
        "desconexao wireless",
        "retirada de rádio",
        "retirada de radio",
        "rádio retirado",
        "radio retirado",
    ],

    # ======================================
    # INSTALAÇÃO DE CABO DE REDE
    # ======================================
    "instalação de cabo de rede": [
        "instalação de cabo de rede",
        "instalacao de cabo de rede",
        "instalação de cabo de rede efetuada",
        "instalacao de cabo de rede efetuada",
        "passagem de cabo de rede",
        "cabo de rede instalado",
        "cabo de rede estava danificado e foi realizada a troca",
        "cabo de rede estava danificado e foi realizado a troca",
        "troca de cabo de rede",
    ],

    # ======================================
    # RETIRADA GENÉRICA
    # ======================================
    "retirada": [
        "retirada",
        "equipamento retirado",
        "equipamentos retirados",
        "desconexão",
        "desconexao",
        "desativado",
        "equipamento removido",
        "equipamentos removidos",
        "cabo retirado",
        "desativação de linha",
        "desativacao de linha",
        "foi realizada a retirada do roteador em comodato",
        "foi realizado a retirada do roteador em comodato",
        "foi realizada a retirada da onu em comodato",
        "foi realizado a retirada da onu em comodato",
        "foi realizada a retirada da ont em comodato",
        "foi realizado a retirada da ont em comodato",
        "foi realizada a retirada da onu/ont em comodato",
        "foi realizado a retirada da onu/ont em comodato",
        "foi realizada a retirada completa dos equipamentos em comodato",
        "foi realizado a retirada completa dos equipamentos em comodato",
    ],

    # ======================================
    # SUPORTE EXTRA
    # ======================================
    "suporte extra": [
        "suporte extra",
        "atendimento extra",
        "apoio adicional",
        "serviço adicional",
        "servico adicional",
        "suporte adicional",
    ],
        # ======================================
    # INFRA - INSTALAÇÃO
    # ======================================
    "infra - instalação": [
        "instalação de infraestrutura",
        "instalacao de infraestrutura",
        "montagem de infraestrutura",
        "instalação de cto",
        "instalacao de cto",
        "montagem de cto",
        "instalação de caixa",
        "instalacao de caixa",
        "montagem de caixa",
        "instalação de cd",
        "instalacao de cd",
        "montagem de cd",
        "instalação de ce",
        "instalacao de ce",
        "montagem de ce",
        "instalação de rack",
        "instalacao de rack",
        "fixação de rack",
        "fixacao de rack",
        "instalação de splitter",
        "instalacao de splitter",
        "lançamento de cabo",
        "lancamento de cabo",
        "lançamento de cabo backbone",
        "lancamento de cabo backbone",
        "ancoragem de cabo",
        "passagem de eletroduto",
        "instalação de eletroduto",
        "instalacao de eletroduto",
    ],

    # ======================================
    # INFRA - REPARO
    # ======================================
    "infra - reparo": [
        "reparo de infraestrutura",
        "manutenção de infraestrutura",
        "manutencao de infraestrutura",
        "reparo de cto",
        "reparo de caixa",
        "reparo de cd",
        "reparo de ce",
        "refazer fusão",
        "refazer fusao",
        "fusão refeita",
        "fusao refeita",
        "correção de fusão",
        "correcao de fusao",
        "reparo em backbone",
        "correção de rompimento de backbone",
        "correcao de rompimento de backbone",
        "reancoragem de cabo",
        "reequipar cabo",
        "reparo de rack",
        "reparo de splitter",
    ],

    # ======================================
    # INFRA - RETIRADA
    # ======================================
    "infra - retirada": [
        "retirada de infraestrutura",
        "remoção de infraestrutura",
        "remocao de infraestrutura",
        "retirada de cto",
        "retirada de caixa",
        "retirada de cd",
        "retirada de ce",
        "retirada de rack",
        "retirada de splitter",
        "retirada de cabo backbone",
        "remoção de cabo backbone",
        "remocao de cabo backbone",
        "desmontagem de infraestrutura",
    ],

    # ======================================
    # INFRA - TROCA
    # ======================================
    "infra - troca": [
        "troca de infraestrutura",
        "substituição de infraestrutura",
        "substituicao de infraestrutura",
        "troca de cto",
        "troca de caixa",
        "troca de cd",
        "troca de ce",
        "troca de rack",
        "troca de splitter",
        "substituição de splitter",
        "substituicao de splitter",
        "troca de peça de infraestrutura",
        "troca de peca de infraestrutura",
        "equipamento de infraestrutura trocado",
    ],

    # ======================================
    # INFRA - VERIFICAÇÃO
    # ======================================
    "infra - verificação": [
        "verificação de infraestrutura",
        "verificacao de infraestrutura",
        "verificação de cto",
        "verificacao de cto",
        "verificação de caixa",
        "verificacao de caixa",
        "verificação de cd",
        "verificacao de cd",
        "verificação de ce",
        "verificacao de ce",
        "verificação de sinal da caixa",
        "verificacao de sinal da caixa",
        "checagem de infraestrutura",
        "diagnóstico de infraestrutura",
        "diagnostico de infraestrutura",
        "análise de infraestrutura",
        "analise de infraestrutura",
        "teste de sinal na caixa",
        "testar sinal da caixa",
        "vistoria de infraestrutura",
    ],

    # ======================================
    # INFRA - DESLOCAMENTO
    # ======================================
    "infra - deslocamento": [
        "deslocamento de infraestrutura",
        "deslocamento para infraestrutura",
        "deslocamento para atendimento de infraestrutura",
        "visita técnica de infraestrutura",
        "visita tecnica de infraestrutura",
        "ida ao local da infraestrutura",
        "ida a campo para infraestrutura",
        "viagem técnica de infraestrutura",
        "viagem tecnica de infraestrutura",
        "apenas deslocamento de infraestrutura",
    ],
}
# ==========================================
# ORDEM DE PRIORIDADE PARA CLASSIFICAÇÃO
# ==========================================
CATEGORIAS_ORDENADAS = [
    # Serviços específicos primeiro
    "instalação de cabo de rede",
    "troca de ont/onu/roteador",
    "troca de drop",

    "retirada fibra",
    "retirada wireless",
    "instalação fibra",
    "instalação wireless",

    "mudança de titularidade",
    "mudança de endereço",
    "migração de torre",

    "reativação",
    "renovação",
    "configuração",
    "visita improdutiva",
    "periódico",
    "reparo",

    # Infraestrutura
    "infra - instalação",
    "infra - reparo",
    "infra - retirada",
    "infra - troca",
    "infra - verificação",
    "infra - deslocamento",

    # Categorias genéricas por último
    "retirada",
    "suporte extra",
]


# ==========================================
# VALIDAÇÃO AUTOMÁTICA DA CONFIGURAÇÃO
# ==========================================
def validar_configuracao() -> None:
    """
    Verifica inconsistências entre:
    - pontos_os
    - sinonimos
    - CATEGORIAS_ORDENADAS
    """

    categorias_pontos = set(pontos_os.keys())
    categorias_sinonimos = set(sinonimos.keys())
    categorias_ordenadas = set(CATEGORIAS_ORDENADAS)

    erros_encontrados = False

    # --------------------------------------
    # SINÔNIMOS SEM PONTUAÇÃO
    # --------------------------------------
    sinonimos_sem_pontuacao = (
        categorias_sinonimos - categorias_pontos
    )

    for categoria in sorted(sinonimos_sem_pontuacao):
        logger.warning(
            "Categoria de sinônimo não existe em pontos_os: "
            f"{categoria!r}"
        )
        erros_encontrados = True

    # --------------------------------------
    # CATEGORIAS ORDENADAS SEM PONTUAÇÃO
    # --------------------------------------
    ordenadas_sem_pontuacao = (
        categorias_ordenadas - categorias_pontos
    )

    for categoria in sorted(ordenadas_sem_pontuacao):
        logger.warning(
            "Categoria de CATEGORIAS_ORDENADAS não existe "
            f"em pontos_os: {categoria!r}"
        )
        erros_encontrados = True

    # --------------------------------------
    # PONTUAÇÕES SEM SINÔNIMOS
    # --------------------------------------
    categorias_sem_sinonimos = (
        categorias_pontos - categorias_sinonimos
    )

    for categoria in sorted(categorias_sem_sinonimos):
        logger.info(
            "Categoria de pontos sem lista de sinônimos: "
            f"{categoria!r}"
        )

    # --------------------------------------
    # PONTUAÇÕES FORA DA ORDEM
    # --------------------------------------
    categorias_fora_da_ordem = (
        categorias_pontos - categorias_ordenadas
    )

    for categoria in sorted(categorias_fora_da_ordem):
        logger.info(
            "Categoria de pontos não incluída em "
            f"CATEGORIAS_ORDENADAS: {categoria!r}"
        )

    # --------------------------------------
    # VALIDAÇÃO DAS LISTAS DE SINÔNIMOS
    # --------------------------------------
    for categoria, lista_sinonimos in sinonimos.items():
        if not isinstance(lista_sinonimos, list):
            logger.warning(
                f"Os sinônimos de {categoria!r} não são uma lista."
            )
            erros_encontrados = True
            continue

        if not lista_sinonimos:
            logger.warning(
                f"A categoria {categoria!r} possui lista vazia."
            )

        sinonimos_normalizados = [
            str(item).strip().lower()
            for item in lista_sinonimos
            if str(item).strip()
        ]

        duplicados = {
            item
            for item in sinonimos_normalizados
            if sinonimos_normalizados.count(item) > 1
        }

        if duplicados:
            logger.info(
                f"Sinônimos duplicados em {categoria!r}: "
                f"{sorted(duplicados)!r}"
            )

    if erros_encontrados:
        logger.warning(
            "A configuração possui inconsistências. "
            "Verifique os avisos acima."
        )
    else:
        logger.info(
            "Configuração de pontos e sinônimos "
            "validada com sucesso."
        )


# Executa a validação quando o config.py for importado
validar_configuracao()
