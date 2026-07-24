import logging

# ==========================================
# CONFIGURAÇÃO DE LOGS
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# SEGURANÇA: ID DO DONO (MASTER)
# ==========================================
MASTER_ID = 1379071981

META_MENSAL = 160

# ==========================================
# REGRAS DE NEGÓCIO E PONTUAÇÕES
# ==========================================
pontos_os = {
    'infra - instalação': 4,
    'infra - reparo': 2,
    'infra - retirada': 2,
    'infra - troca': 2,
    'infra - verificação': 1,
    'infra - deslocamento': 1,
    'troca de ont/onu/roteador': 0.0,
    'reparo': 1,
    'visita improdutiva': 1,
    'configuração': 1,
    'renovação': 1,
    'reativação': 2,
    'instalação fibra': 2.5,
    'troca de drop': 1,
    'mudança de titularidade': 2.5,
    'mudança de endereço': 2.5,
    'suporte extra': 0.0,
    'migração de torre': 1,
    'instalação wireless': 2,
    'periódico': 1,
    'retirada wireless': 1,
    'retirada fibra': 1,
    'RETIRADA': 1,
    'retirada': 1,
    'instalação de cabo de rede': 2,
}

# ==========================================
# DICIONÁRIO DE SINÔNIMOS (O CÉREBRO DO BOT)
# ==========================================
sinonimos = {
    'instalação fibra': [
        'instalação de fibra', 'instalacao de fibra optica', 'fibra optica instalada', 
        'passagem de fibra', 'ponto fibra novo', 'instalacao de rede de fibra', 
        'instalação de fibra óptica realizada', 'instalação de fibra', 'instalacao fibra',
        'instalação de fibra óptica realizada.'
    ],
    'retirada fibra': [
        'remocao fibra', 'fibra optica retirada', 'cabo fibra retirado', 'desativacao fibra',
        'desconexao de fibra', 'retirada de fibra', 'retirada da ont em comodato',
        'retirada da onu/ont em comodato', 'retirada completa dos equipamentos em comodato',
        'o conector foi retirado da caixa', 'tipo e suporte:retirada', 'tipo e suporte: retirada'
    ],
    'reparo': [
        'tipo e suporte:reparo', 'tipo e suporte: fibra reparo', 'manutenção', 'conserto', 
        'restabelecimento', 'falha resolvida', 'problema corrigido', 'sinal reestabelecido',
        'reparo realizado', 'houve um rompimento de fibra local', 'cabos estavam invertidos',
        'cabos estavam mal encaixados', 'equipamentos estavam desligados',
        'equipamentos foram resetados pelo cliente', 'velocidade está conforme o contratado',
        'conector estava danificado', 'troca de conector', 'cabo de rede danificado',
        'equipamentos resetados por queda de energia', 'roteador do cliente com defeito',
        'reinstalação interna', 'reparo fibra',
        'roteador do cliente incompatível', 'rompimento de fibra local',
        'onu com defeito', 'plano incompatível com a utilização', 'não há problemas locais'
    ],
    'visita improdutiva': [
        'visita improdutiva', 'não foi encontrado nenhum problema', 
        'aparentemente o notebook/desktop do cliente está com problema',
        'aparentemente roteador está com mau funcionamento', 'tvbox', 'tv box', 
        'assistência técnica', 'funcionando normal', 'tudo normal', 'internet já estava normal',
        'nenhum problema encontrado'
    ],
    'reativação': [
        'reativação realizada', 'reativação de fibra óptica realizada', 
        'reativacao', 'reativacao de servico', 'reativação'
    ],
    'mudança de endereço': [
        'alteracao de endereco', 'mudanca de local', 'transferencia de ponto', 'relocacao',
        'mudança de endereço realizada', 'mudança de cômodo realizada',
        'mudanças de endereço', 'mudanca de endereco'
    ],
    'troca de ont/onu/roteador': [
        'substituicao de ont', 'ont trocada', 'onu trocada', 'troca de onu', 'roteador trocado',
        'substituicao de roteador', 'mudanca de equipamento', 'troca de aparelho', 'troca de modem',
        'troca de roteador realizada', 'tipo e suporte:troca de equipamento',
        'troca de onu realizada', 'onu está com defeito', 'roteador está com defeito',
        'roteador em comodato está com defeito apresentando quedas no tráfego e é necessário fazer a troca.',
        'é necessário fazer a troca', 'necessario fazer a troca', 'roteador em comodato está com defeito'
    ],
    'configuração': [
        'configuração de roteador efetuada', 'configuração realizada', 'config de roteador',
        'roteador configurado', 'ajuste de configuração', 'configuracao de rede', 'configuracao de wi-fi',
        'ajuste tecnico', 'ajuste no roteador', 'configurar internet',
        'instalação e alteração de login e senha realizada', 'configuração padrão dos equipamentos',
        'reconfiguração foi realizada', 'mudança de senha de roteador efetuada'
    ],
    'troca de drop': [
        'tipo e suporte:troca de drop', 'substituicao de drop', 'troca de cabo drop', 'drop substituido',
        'cabo drop trocado', 'mudanca de drop', 'substituicao de cabo'
    ],
    'renovação': [
        'tipo e suporte:renovação', 'contrato renovado', 'renovacao de contrato', 'renovacao de plano',
        'contrato expirado', 'renovação realizada', 'fibra renova'
    ],
    'mudança de titularidade': [
        'transferencia de titularidade', 'alteracao de titular', 'troca de nome', 'mudanca de cliente', 'alteracao de cpf'
    ],
    'migração de torre': [
        'mudança de torre', 'migracao de ap', 'troca de torre',
        'alteracao de torre', 'mudanca de equipamento de torre', 'migracao de torre'
    ],
    'instalação wireless': [
        'instalacao wi-fi', 'antena wireless instalada', 'ponto wireless novo', 'wi-fi instalado',
        'instalacao de radio', 'instalacao de cliente wireless', 'ponto de acesso novo'
    ],
    'periódico': [
        'manutencao periodica', 'verificacao programada', 'checagem de rotina', 'revisao',
        'visita periodica', 'vistoria', 'manutencao preventiva'
    ],
    'retirada wireless': [
        'remocao wireless', 'antena wireless retirada', 'desinstalacao wireless', 'desativacao de radio',
        'desconexao wireless', 'retirada de radio'
    ],
    'instalação de cabo de rede': [
        'instalação de cabo de rede efetuada', 'cabo de rede estava danificado e foi realizado a troca'
    ],
    'instalação': [
        'instalação realizada', 'reinstalação externa realizada', 'ponto novo',
        'instalacao efetuada', 'servico de instalacao', 'ativacao de servico',
        'nova instalacao', 'ativacao', 'cliente novo',
        'foi necessário refazer a instalação dos equipamentos',
        'refazer a instalação externa', 'instalação de onu em comodato realizada',
        'instalação de roteador em comodato realizada', 'instalação de roteador do cliente realizada'
    ],
    'retirada': [
        'equipamento retirado', 'desconexão', 'desativado', 'equipamento removido',
        'cabo retirado', 'desativacao de linha','retirada',
        'Foi realizado a retirada do roteador em comodato. O conector foi retirado da caixa.',
        'Foi realizado a retirada da ONU/ONT em comodato. O conector foi retirado da caixa.',
        'Foi realizado a retirada da ONT em comodato. O conector foi retirado da caixa.',
        'Foi realizado a retirada da ONU em comodato. O conector foi retirado da caixa.',
        'Foi realizado a retirada completa dos equipamentos em comodato. O conector foi retirado da caixa.'
    ],
    'troca': [
        'equipamento trocado', 'substituição de equipamento', 'troca de peça'
    ],
    'verificação': [
        'verificacao de sinal', 'checagem de rede', 'diagnostico', 'analise de rede', 'testar sinal'
    ],
    'deslocamento': [
        'visita tecnica', 'deslocamento para atendimento', 'ida ao local',
        'viagem tecnica', 'ida a campo', 'apenas deslocamento'
    ]
}

# ==========================================
# ORDEM DE LEITURA DO BOT
# ==========================================
CATEGORIAS_ORDENADAS = [
    'instalação fibra', 'retirada fibra', 'retirada wireless', 'instalação wireless',
    'troca de drop', 'troca de ont/onu/roteador', 'instalação de cabo de rede',
    'infra - instalação', 'infra - reparo', 'infra - retirada', 'infra - troca',
    'infra - verificação', 'infra - deslocamento', 'reparo', 'visita improdutiva', 
    'configuração', 'renovação', 'reativação', 'mudança de titularidade', 
    'mudança de endereço', 'suporte extra', 'migração de torre', 'periódico', 
    'instalação', 'retirada', 'troca', 'verificação', 'deslocamento'
]
