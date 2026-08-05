import aiosqlite
import sqlite3
import json
import datetime
import hashlib
import re
from config import logger

DB_NAME = "pontos_v2.db"
FUSO_BRASIL = datetime.timezone(datetime.timedelta(hours=-3))

# Cache de usuários com TTL (expiração de 5 minutos / 300 segundos)
usuarios_cache = {}  # Formato: {user_id: {"cargo": str, "exp": datetime.datetime}}
TTL_CACHE_SEGUNDOS = 300

def get_agora_brasil():
    return datetime.datetime.now(FUSO_BRASIL).strftime('%Y-%m-%d %H:%M:%S')

def normalizar_texto(texto: str) -> str:
    """Normalização agressiva para impedir que alterações mínimas burlem o hash."""
    if not texto:
        return ""
    # Remove caracteres especiais e espaços excessivos, mantendo letras e números
    texto_limpo = re.sub(r'[^\w\s]', '', texto)
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
    return texto_limpo.strip().upper()

def extrair_rx(texto: str) -> str:
    match = re.search(r'RX[:\s-]*(-?\d+(?:\.\d+)?)', texto, re.IGNORECASE)
    return match.group(1) if match else ""

def extrair_serial(texto: str) -> str:
    match = re.search(r'(?:serial|sn|s/n)[:\s]*([A-Z0-9]+)', texto, re.IGNORECASE)
    return match.group(1).upper() if match else ""

def extrair_mac(texto: str) -> str:
    match = re.search(r'([0-9A-F]{2}(?::[0-9A-F]{2}){5}|[0-9A-F]{12})', texto, re.IGNORECASE)
    if match:
        return match.group(1).replace(":", "").upper()
    return ""

def extrair_pon(texto: str) -> str:
    match = re.search(r'pon[:\s]*([A-Z0-9\-/]+)', texto, re.IGNORECASE)
    return match.group(1).upper() if match else ""

def extrair_onu(texto: str) -> str:
    match = re.search(r'(?:onu|ont|modelo)[:\s]*([A-Z0-9\-_]+)', texto, re.IGNORECASE)
    return match.group(1).upper() if match else ""

def gerar_hash_relevante(cliente: str, servico: str, descricao: str, protocolo: str = "") -> str:
    """Gera um hash SHA-256 inteligente combinando Cliente, Serviço, Protocolo e parâmetros técnicos."""
    cliente_norm = normalizar_texto(cliente)
    servico_norm = normalizar_texto(servico)
    protocolo_norm = protocolo.strip().upper() if protocolo else "NÃO INFORMADO"

    rx = extrair_rx(descricao)
    serial = extrair_serial(descricao)
    mac = extrair_mac(descricao)
    pon = extrair_pon(descricao)
    onu = extrair_onu(descricao)

    if protocolo_norm and protocolo_norm != "NÃO INFORMADO":
        assinatura = f"{cliente_norm}|{servico_norm}|{protocolo_norm}"
    else:
        assinatura = f"{cliente_norm}|{servico_norm}|{rx}|{serial}|{mac}|{pon}|{onu}"

    return hashlib.sha256(assinatura.encode("utf-8")).hexdigest()

async def iniciar_banco():
    """Inicializa o banco de dados, tabelas, restrições UNIQUE e índices compostos de alta performance."""
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute('PRAGMA journal_mode=WAL;')
            await conn.execute('PRAGMA synchronous=NORMAL;')
            
            # Tabela de Usuários
            await conn.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                user_id INTEGER PRIMARY KEY, 
                cargo TEXT DEFAULT 'tecnico', 
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            try: await conn.execute("ALTER TABLE usuarios ADD COLUMN nome TEXT DEFAULT 'Desconhecido'")
            except sqlite3.OperationalError: pass 
                
            # Tabela principal de Histórico de O.S.
            await conn.execute('''CREATE TABLE IF NOT EXISTS historico_os (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER, 
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                descricao_os TEXT, 
                tipos_identificados TEXT, 
                pontos_ganhos REAL, 
                cliente TEXT DEFAULT 'Não informado', 
                protocolo TEXT DEFAULT 'NÃO INFORMADO',
                hash_os TEXT,
                FOREIGN KEY(user_id) REFERENCES usuarios(user_id)
            )''')

            # Tabela de Auditoria de Tentativas Duplicadas
            await conn.execute('''CREATE TABLE IF NOT EXISTS historico_duplicidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                protocolo TEXT,
                descricao TEXT,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            
            # Garantia de compatibilidade de colunas
            for coluna, tipo in [("cliente", "TEXT DEFAULT 'Não informado'"), 
                                 ("protocolo", "TEXT DEFAULT 'NÃO INFORMADO'"), 
                                 ("hash_os", "TEXT")]:
                try:
                    await conn.execute(f"ALTER TABLE historico_os ADD COLUMN {coluna} {tipo}")
                except sqlite3.OperationalError:
                    pass

            # Índices Individuais e Compostos para máxima performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_protocolo ON historico_os(protocolo);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_hash ON historico_os(hash_os);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_user_data ON historico_os(user_id, data_hora);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_dup_user_data ON historico_duplicidades(user_id, data_hora);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_dup_protocolo ON historico_duplicidades(protocolo);")

            # Restrições UNIQUE no nível de banco de dados
            await conn.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_protocolo 
                ON historico_os(protocolo) 
                WHERE protocolo IS NOT NULL AND protocolo != '' AND protocolo != 'NÃO INFORMADO'
            ''')
            await conn.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_hash_os 
                ON historico_os(hash_os) 
                WHERE hash_os IS NOT NULL AND hash_os != ''
            ''')
            
            # Tabelas auxiliares
            await conn.execute('''CREATE TABLE IF NOT EXISTS user_states (user_id INTEGER PRIMARY KEY, state TEXT)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS pending_os (user_id INTEGER PRIMARY KEY, texto TEXT, cliente TEXT, tipos TEXT, pontos_totais REAL)''')
            
            await conn.commit()
    except Exception as e: 
        logger.error(f"Erro ao inicializar banco: {e}")

async def registrar_tentativa_duplicada(user_id: int, protocolo: str, descricao: str):
    """Registra auditoria de tentativa duplicada."""
    agora = get_agora_brasil()
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute(
                "INSERT INTO historico_duplicidades (user_id, protocolo, descricao, data_hora) VALUES (?, ?, ?, ?)",
                (user_id, protocolo, descricao, agora)
            )
            await conn.commit()
    except Exception as e:
        logger.error(f"Erro ao registrar tentativa duplicada: {e}")

async def contar_tentativas_10_min(user_id: int) -> int:
    """Sistema Anti-Flood: conta tentativas nos últimos 10 minutos (imune ao fuso do servidor)."""
    agora = get_datetime_brasil()
    limite_tempo = (agora - datetime.timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')

    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute(
                """
                SELECT COUNT(*)
                FROM historico_duplicidades
                WHERE user_id = ?
                AND data_hora >= ?
                """,
                (user_id, limite_tempo)
            ) as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0
    except Exception as e:
        logger.error(f"Erro ao contar tentativas de flood: {e}")
        return 0
async def verificar_por_protocolo_conn(conn, protocolo: str):
    if not protocolo or protocolo in ["NÃO INFORMADO", ""]:
        return False
    async with conn.execute(
        """
        SELECT h.id, h.cliente, h.tipos_identificados, h.data_hora, h.protocolo, h.pontos_ganhos, 
               COALESCE(u.nome, 'Téc ' || h.user_id) as tecnico_nome
        FROM historico_os h
        LEFT JOIN usuarios u ON h.user_id = u.user_id
        WHERE h.protocolo = ?
        """, 
        (protocolo,)
    ) as cursor:
        res = await cursor.fetchone()
        if res:
            return {
                "id": res[0], "cliente": res[1], "servico": res[2],
                "data_hora": res[3], "protocolo": res[4], "pontos": res[5], "tecnico": res[6]
            }
    return False

async def verificar_por_protocolo(protocolo: str):
    """Método público para buscar O.S. estritamente pelo número do protocolo."""
    if not protocolo or protocolo in ["NÃO INFORMADO", ""]:
        return False
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            return await verificar_por_protocolo_conn(conn, protocolo)
    except Exception as e:
        logger.error(f"Erro ao verificar por protocolo: {e}")
        return False

async def verificar_duplicidade_interna(conn, protocolo: str, cliente: str, servico: str, descricao_os: str):
    """Verificação interna reutilizando a conexão ativa para evitar race conditions."""
    if protocolo and protocolo not in ["NÃO INFORMADO", ""]:
        proto_res = await verificar_por_protocolo_conn(conn, protocolo)
        if proto_res:
            return proto_res

    hash_atual = gerar_hash_relevante(cliente, servico, descricao_os, protocolo)
    async with conn.execute(
        """
        SELECT h.id, h.cliente, h.tipos_identificados, h.data_hora, h.protocolo, h.pontos_ganhos, 
               COALESCE(u.nome, 'Téc ' || h.user_id) as tecnico_nome
        FROM historico_os h
        LEFT JOIN usuarios u ON h.user_id = u.user_id
        WHERE h.hash_os = ?
        """,
        (hash_atual,)
    ) as cursor:
        res = await cursor.fetchone()
        if res:
            return {
                "id": res[0], "cliente": res[1], "servico": res[2],
                "data_hora": res[3], "protocolo": res[4], "pontos": res[5], "tecnico": res[6]
            }
    return False

async def verificar_duplicidade(protocolo: str, cliente: str, servico: str, descricao_os: str):
    """Método público para checagem rápida de duplicidade."""
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            return await verificar_duplicidade_interna(conn, protocolo, cliente, servico, descricao_os)
    except Exception as e:
        logger.error(f"Erro ao verificar duplicidade: {e}")
        return False

async def registrar_os(user_id: int, descricao: str, tipos: str, pontos: float, cliente: str = 'Não informado', protocolo: str = 'NÃO INFORMADO') -> bool:
    """Registra a O.S. com transação atômica imediata (BEGIN IMMEDIATE), rollback automático e logs completos."""
    agora = get_agora_brasil()
    hash_atual = gerar_hash_relevante(cliente, tipos, descricao, protocolo)
    
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            # Proteção contra race condition com bloqueio de escrita imediato
            await conn.execute("BEGIN IMMEDIATE")
            try:
                duplicada = await verificar_duplicidade_interna(conn, protocolo, cliente, tipos, descricao)
                if duplicada:
                    logger.warning(f"OS DUPLICADA | USER={user_id} | CLIENTE={cliente} | PROTOCOLO={protocolo}")
                    await conn.rollback()
                    return False

                await conn.execute(
                    """
                    INSERT INTO historico_os 
                    (user_id, data_hora, descricao_os, tipos_identificados, pontos_ganhos, cliente, protocolo, hash_os) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, 
                    (user_id, agora, descricao, tipos, pontos, cliente, protocolo, hash_atual)
                )
                await conn.commit()
                logger.info(f"OS REGISTRADA | USER={user_id} | CLIENTE={cliente} | SERVIÇO={tipos} | PONTOS={pontos} | PROTOCOLO={protocolo}")
                return True
            except Exception as inner_e:
                await conn.rollback()
                logger.error(f"Erro transacional interno, rollback executado: {inner_e}")
                return False
    except sqlite3.IntegrityError:
        logger.warning(f"OS DUPLICADA (IntegrityError) | USER={user_id} | CLIENTE={cliente} | PROTOCOLO={protocolo}")
        return False
    except Exception as e: 
        logger.error(f"Erro ao registrar OS: {e}")
        return False

async def obter_resumo_mes(user_id: int, ano: str, mes: str) -> dict:
    """Consulta unificada otimizada para pontos e quantidade de O.S. no mês."""
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute(
                """
                SELECT COALESCE(SUM(pontos_ganhos), 0.0), COUNT(id) 
                FROM historico_os 
                WHERE user_id = ? AND strftime('%Y', data_hora) = ? AND strftime('%m', data_hora) = ?
                """, 
                (user_id, ano, mes)
            ) as cursor:
                res = await cursor.fetchone()
                if res:
                    return {"pontos": res[0], "os": res[1]}
        return {"pontos": 0.0, "os": 0}
    except Exception as e:
        logger.error(f"Erro ao obter resumo do mês: {e}")
        return {"pontos": 0.0, "os": 0}

async def obter_pontos_mes(user_id: int, ano: str, mes: str) -> float:
    """Função de compatibilidade retroativa usando a consulta unificada."""
    resumo = await obter_resumo_mes(user_id, ano, mes)
    return resumo["pontos"]

async def contar_os_mes(user_id: int, ano: str, mes: str) -> int:
    """Função de compatibilidade retroativa usando a consulta unificada."""
    resumo = await obter_resumo_mes(user_id, ano, mes)
    return resumo["os"]

async def verificar_usuario(user_id: int):
    """Verifica cargo do usuário utilizando Cache em Memória com expiração (TTL)."""
    agora_dt = datetime.datetime.now()
    if user_id in usuarios_cache:
        cached = usuarios_cache[user_id]
        if cached["exp"] > agora_dt:
            return cached["cargo"]

    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute("SELECT cargo FROM usuarios WHERE user_id = ?", (user_id,)) as cursor:
                res = await cursor.fetchone()
                cargo = res[0] if res else None
                if cargo:
                    usuarios_cache[user_id] = {
                        "cargo": cargo,
                        "exp": agora_dt + datetime.timedelta(seconds=TTL_CACHE_SEGUNDOS)
                    }
                return cargo
    except Exception as e:
        logger.error(f"Erro ao verificar usuário: {e}")
        return None

# --- Funções auxiliares mantidas para compatibilidade ---
async def set_user_state(user_id: int, state: str):
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("INSERT OR REPLACE INTO user_states (user_id, state) VALUES (?, ?)", (user_id, state))
            await conn.commit()
    except Exception: pass

async def get_user_state(user_id: int):
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute("SELECT state FROM user_states WHERE user_id = ?", (user_id,)) as cursor:
                res = await cursor.fetchone()
                return res[0] if res else None
    except Exception: return None

async def clear_user_state(user_id: int):
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
            await conn.commit()
    except Exception: pass

async def save_pending_os(user_id: int, texto: str, cliente: str, tipos: list, pontos_totais: float):
    tipos_str = json.dumps(tipos)
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("INSERT OR REPLACE INTO pending_os (user_id, texto, cliente, tipos, pontos_totais) VALUES (?, ?, ?, ?, ?)", (user_id, texto, cliente, tipos_str, pontos_totais))
            await conn.commit()
    except Exception: pass

async def get_pending_os(user_id: int):
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute("SELECT texto, cliente, tipos, pontos_totais FROM pending_os WHERE user_id = ?", (user_id,)) as cursor:
                res = await cursor.fetchone()
                if res: return {'texto': res[0], 'cliente': res[1], 'tipos': json.loads(res[2]), 'pontos_totais': res[3]}
                return None
    except Exception: return None

async def clear_pending_os(user_id: int):
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("DELETE FROM pending_os WHERE user_id = ?", (user_id,))
            await conn.commit()
    except Exception: pass

async def adicionar_usuario(user_id: int, cargo: str = 'tecnico') -> bool:
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("INSERT OR REPLACE INTO usuarios (user_id, cargo) VALUES (?, ?)", (user_id, cargo))
            await conn.commit()
            usuarios_cache[user_id] = {
                "cargo": cargo,
                "exp": datetime.datetime.now() + datetime.timedelta(seconds=TTL_CACHE_SEGUNDOS)
            }
            return True
    except Exception: return False

async def remover_usuario(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("DELETE FROM usuarios WHERE user_id = ?", (user_id,))
            await conn.commit()
            usuarios_cache.pop(user_id, None)
            return True
    except Exception: return False

async def apagar_usuario_completo(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("DELETE FROM historico_os WHERE user_id = ?", (user_id,))
            await conn.execute("DELETE FROM usuarios WHERE user_id = ?", (user_id,))
            await conn.commit()
            usuarios_cache.pop(user_id, None)
            return True
    except Exception: return False

async def atualizar_nome_usuario(user_id: int, nome: str):
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("UPDATE usuarios SET nome = ? WHERE user_id = ?", (nome, user_id))
            await conn.commit()
    except Exception: pass

async def obter_historico_usuario(user_id: int, limite: int = 15):
    """Obtém o histórico do próprio usuário com a data já formatada para o Brasil."""
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute("""
                SELECT 
                    id, 
                    strftime('%d/%m/%Y %H:%M', data_hora) as data_formatada, 
                    tipos_identificados, 
                    pontos_ganhos, 
                    cliente 
                FROM historico_os 
                WHERE user_id = ? 
                ORDER BY data_hora DESC 
                LIMIT ?
            """, (user_id, limite)) as cursor:
                return await cursor.fetchall()
    except Exception as e: 
        logger.error(f"Erro ao obter histórico do usuário: {e}")
        return []

async def excluir_ultima_os(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("DELETE FROM historico_os WHERE id = (SELECT MAX(id) FROM historico_os WHERE user_id = ?)", (user_id,))
            await conn.commit()
            return True
    except Exception: return False

async def obter_todos_dados_mes(ano: str, mes: str):
    """Gera o relatório mensal exportando o NOME do técnico em vez do ID numérico."""
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute("""
                SELECT 
                    h.id, 
                    COALESCE(u.nome, 'Téc ' || h.user_id) as tecnico_nome, 
                    strftime('%d/%m/%Y %H:%M', h.data_hora) as data_formatada, 
                    h.tipos_identificados, 
                    h.pontos_ganhos, 
                    h.descricao_os,
                    h.cliente
                FROM historico_os h
                LEFT JOIN usuarios u ON h.user_id = u.user_id
                WHERE strftime('%Y', h.data_hora) = ? AND strftime('%m', h.data_hora) = ? 
                ORDER BY h.data_hora DESC
            """, (ano, mes)) as cursor:
                return await cursor.fetchall()
    except Exception as e: 
        logger.error(f"Erro ao obter dados do mês: {e}")
        return []

async def consultar_cliente(termo_busca: str):
    """Busca o histórico do cliente com o NOME do técnico e a data formatada para o Brasil."""
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute("""
                SELECT 
                    strftime('%d/%m/%Y %H:%M', h.data_hora) as data_formatada,
                    COALESCE(u.nome, 'Téc ' || h.user_id) as tecnico_nome,
                    h.tipos_identificados, 
                    h.pontos_ganhos, 
                    h.cliente 
                FROM historico_os h
                LEFT JOIN usuarios u ON h.user_id = u.user_id
                WHERE h.cliente LIKE ? 
                ORDER BY h.data_hora DESC 
                LIMIT 15
            """, (f'%{termo_busca}%',)) as cursor:
                return await cursor.fetchall()
    except Exception as e: 
        logger.error(f"Erro ao consultar cliente: {e}")
        return []

async def apagar_os_especifica(os_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            cursor = await conn.execute("DELETE FROM historico_os WHERE id = ?", (os_id,))
            await conn.commit()
            return cursor.rowcount > 0 
    except Exception: return False
async def obter_ranking_mes(ano: str, mes: str):
    """Consulta os dados para montar o placar/ranking dos técnicos no mês."""
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute("""
                SELECT h.user_id, COALESCE(u.nome, 'Téc ' || h.user_id), SUM(h.pontos_ganhos) as total 
                FROM historico_os h 
                LEFT JOIN usuarios u ON h.user_id = u.user_id 
                WHERE strftime('%Y', h.data_hora) = ? AND strftime('%m', h.data_hora) = ? 
                GROUP BY h.user_id 
                ORDER BY total DESC
            """, (ano, mes)) as cursor:
                return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao obter ranking do mês: {e}")
        return []
