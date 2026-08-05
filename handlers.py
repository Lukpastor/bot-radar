import asyncio
import re
import datetime
import csv
import io
from telegram import Update
from telegram.ext import ContextTypes
from config import logger, MASTER_ID, META_MENSAL
from points_logic import processar_com_ia
from database import (
    verificar_usuario,
    verificar_por_protocolo,
    verificar_duplicidade,
    registrar_os,
    registrar_tentativa_duplicada,
    obter_resumo_mes,
    obter_historico_usuario,
    obter_ranking_mes,
    consultar_cliente as db_consultar_cliente,
    excluir_ultima_os,
    adicionar_usuario,
    remover_usuario,
    apagar_usuario_completo,
    apagar_os_especifica,
    obter_todos_dados_mes
)

# ==========================================
# FUNÇÃO AUXILIAR: BARRA DE PROGRESSO
# ==========================================
def gerar_barra_progresso(pontos_atuais: float, meta: int) -> str:
    """Gera a barra visual de progresso da meta mensal."""
    if meta <= 0: return ""
    
    percentual = (pontos_atuais / meta) * 100
    percentual_limitado = min(percentual, 100) # Trava em 100% para não quebrar a barra visual
    
    blocos_preenchidos = int(percentual_limitado // 10)
    blocos_vazios = 10 - blocos_preenchidos
    
    barra = "█" * blocos_preenchidos + "░" * blocos_vazios
    
    msg_meta = "\n🎉 <b>Meta Atingida! Parabéns!</b>" if percentual >= 100 else ""
    
    return (
        f"\n\n📈 <b>Progresso da Meta ({meta} pts):</b>\n"
        f"[{barra}] {percentual:.1f}%{msg_meta}"
    )

# ==========================================
# FUNÇÃO AUXILIAR DE PERMISSÃO
# ==========================================
async def is_supervisor(user_id: int) -> bool:
    """Verifica se o usuário tem permissão de supervisor/admin ou é o MASTER_ID."""
    if user_id == MASTER_ID:
        return True
    
    cargo = await verificar_usuario(user_id)
    return cargo in ['supervisor', 'admin', 'dono']

# ==========================================
# COMANDOS GERAIS (TÉCNICOS E SUPERVISORES)
# ==========================================
async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandos /start e /ajuda com menu dinâmico completo."""
    user = update.effective_user
    user_id = user.id
    cargo = await verificar_usuario(user_id)
    
    # O dono (MASTER) sempre tem acesso, mesmo se não estiver no banco ainda.
    if not cargo and user_id != MASTER_ID:
        await update.message.reply_text("❌ Você não está cadastrado. Solicite acesso ao supervisor.")
        return

    # Mensagem base para todos os usuários (Técnicos)
    mensagem = (
        f"👋 <b>Olá, {user.first_name}!</b>\n\n"
        f"🤖 <b>BOT DE PONTUAÇÃO</b>\n"
        f"<i>Gerenciamento automático de Ordens de Serviço.</i>\n\n"

        f"📌 <b>Como Funciona?</b>\n"
        f"Basta enviar o texto do seu relatório de <b>O.S.</b> aqui no chat. O bot lerá os dados, calculará os pontos e fará o registro sozinho! ⚡\n\n"

        f"👨‍🔧 <b>PAINEL DO TÉCNICO</b>\n"
        f"🔹 /pontos — Seu saldo e quantidade de O.S.\n"
        f"🔹 /historico — Suas últimas 10 O.S. registradas\n"
        f"🔹 /ranking — Placar dos técnicos no mês\n"
        f"🔹 /excluir_ultima — Desfaz o último registro\n"
        f"🔹 /ajuda — Exibe este menu principal\n"
    )

    if await is_supervisor(user_id):
        mensagem += (
            f"\n🛡️ <b>PAINEL DA SUPERVISÃO</b>\n"
            f"🔸 /consultar_cliente <code>nome</code> — Histórico do cliente\n"
            f"🔸 /exportar — Planilha Excel do mês\n"
            f"🔸 /add <code>ID</code> <code>cargo</code> — Novo acesso (Ex: /add 123 admin)\n"
            f"🔸 /delet <code>ID</code> — Remove acesso de um usuário\n"
            f"🔸 /apagar_usuario <code>ID</code> — Deleta usuário e seu histórico\n"
            f"🔸 /apagar_os <code>ID_OS</code> — Exclui um registro específico\n"
            f"🔸 /forcar_os <code>pts</code> <code>serviço</code> — (Responda à O.S. com este comando)\n"
        )

    mensagem += (
        f"\n💡 <i>Dica: Apenas envie sua O.S. e deixe o trabalho pesado comigo!</i>"
    )
    
    await update.message.reply_text(mensagem, parse_mode='HTML')

async def pontos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cargo = await verificar_usuario(user_id)
    if not cargo: return

    agora = datetime.datetime.now()
    resumo_mes = await obter_resumo_mes(user_id, agora.strftime('%Y'), agora.strftime('%m'))
    
    total_pontos = resumo_mes['pontos']
    barra = gerar_barra_progresso(total_pontos, META_MENSAL)
    
    await update.message.reply_text(
        f"📊 <b>Seu Resumo ({agora.strftime('%m/%Y')})</b>\n\n"
        f"✅ <b>O.S. Registradas:</b> {resumo_mes['os']}\n"
        f"🏆 <b>Pontuação Total:</b> {total_pontos:.1f} pts"
        f"{barra}",
        parse_mode='HTML'
    )

async def historico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await verificar_usuario(user_id): return

    registros = await obter_historico_usuario(user_id, limite=10)
    if not registros:
        await update.message.reply_text("📭 Nenhuma O.S. encontrada.")
        return

    msg = "📋 <b>Suas Últimas 10 O.S.:</b>\n\n"
    for os_id, data_formatada, tipos, pts, cliente in registros:
        msg += f"🔹 <b>ID {os_id}</b> | 📅 {data_formatada} | {pts} pts\n👤 {cliente}\n\n"

    await update.message.reply_text(msg, parse_mode='HTML')

async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_usuario(update.effective_user.id): return
    
    agora = datetime.datetime.now()
    rank = await obter_ranking_mes(agora.strftime('%Y'), agora.strftime('%m'))
    
    if not rank:
        await update.message.reply_text("📭 Nenhum ponto registrado neste mês ainda.")
        return

    msg = f"🏆 <b>Ranking do Mês ({agora.strftime('%m/%Y')})</b>\n\n"
    for i, (u_id, nome, total) in enumerate(rank, 1):
        medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}º"
        msg += f"{medalha} <b>{nome}</b>: {total:.1f} pts\n"

    await update.message.reply_text(msg, parse_mode='HTML')

async def excluir_ultima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await verificar_usuario(user_id): return
    
    sucesso = await excluir_ultima_os(user_id)
    if sucesso:
        await update.message.reply_text("✅ Sua última O.S. foi excluída com sucesso.")
    else:
        await update.message.reply_text("❌ Nenhuma O.S. encontrada para excluir.")

async def contar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias rápido para os pontos."""
    await pontos(update, context)

# ==========================================
# COMANDOS ADMINISTRATIVOS (SUPERVISOR)
# ==========================================
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_supervisor(update.effective_user.id): return
    
    if not context.args:
        await update.message.reply_text("⚠️ Uso correto: /add <code>ID_DO_USUARIO</code> [cargo]", parse_mode='HTML')
        return
        
    user_alvo = int(context.args[0])
    cargo_alvo = context.args[1].lower() if len(context.args) > 1 else 'tecnico'
    
    if await adicionar_usuario(user_alvo, cargo_alvo):
        await update.message.reply_text(f"✅ Usuário {user_alvo} adicionado como {cargo_alvo}.")
    else:
        await update.message.reply_text("❌ Erro ao adicionar usuário.")

async def delet_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_supervisor(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("⚠️ Uso: /delet <code>ID</code>", parse_mode='HTML')
    
    if await remover_usuario(int(context.args[0])):
        await update.message.reply_text("✅ Permissão do usuário removida.")

async def apagar_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_supervisor(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("⚠️ Uso: /apagar_usuario <code>ID</code>", parse_mode='HTML')
    
    if await apagar_usuario_completo(int(context.args[0])):
        await update.message.reply_text("✅ Usuário e todo seu histórico apagados.")

async def apagar_os(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_supervisor(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("⚠️ Uso: /apagar_os <code>ID_DA_OS</code>", parse_mode='HTML')
    
    if await apagar_os_especifica(int(context.args[0])):
        await update.message.reply_text("✅ O.S. apagada com sucesso.")
    else:
        await update.message.reply_text("❌ O.S. não encontrada.")

async def consultar_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_supervisor(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("⚠️ Uso: /consultar_cliente <code>nome</code>", parse_mode='HTML')
    
    termo = " ".join(context.args)
    resultados = await db_consultar_cliente(termo)
    
    if not resultados:
        return await update.message.reply_text("📭 Nenhum cliente encontrado com esse termo.")
        
    msg = f"🔎 <b>Resultados para '{termo}':</b>\n\n"
    for data_formatada, tecnico_nome, tipos, pts, cli in resultados:
        msg += f"👤 <b>{cli}</b>\n📅 {data_formatada} | 👨‍🔧 {tecnico_nome} | 🛠️ {tipos.upper()}\n\n"
    await update.message.reply_text(msg, parse_mode='HTML')

async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_supervisor(update.effective_user.id): return
    
    agora = datetime.datetime.now()
    ano = agora.strftime('%Y')
    mes = agora.strftime('%m')
    
    dados = await obter_todos_dados_mes(ano, mes)
    if not dados:
        return await update.message.reply_text("📭 Sem dados neste mês para exportar.")
        
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['ID_OS', 'NOME_TECNICO', 'DATA_HORA', 'SERVICOS', 'PONTOS', 'CLIENTE', 'DESCRICAO'])
    
    for row in dados:
        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[6], row[5]])
        
    output.seek(0)
    bytes_io = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    
    await update.message.reply_document(
        document=bytes_io, 
        filename=f"relatorio_os_{mes}_{ano}.csv",
        caption="📊 Relatório mensal gerado."
    )

async def forcar_os(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_supervisor(update.effective_user.id): return
    
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Você deve responder a uma mensagem de O.S. usando:\n/forcar_os <code>pontos</code> <code>servico</code>", parse_mode='HTML')
    
    if len(context.args) < 2:
        return await update.message.reply_text("⚠️ Uso: /forcar_os <code>1.5</code> <code>Instalacao</code>", parse_mode='HTML')
        
    pontos = float(context.args[0].replace(',', '.'))
    servico = " ".join(context.args[1:])
    texto_original = update.message.reply_to_message.text
    tecnico_id = update.message.reply_to_message.from_user.id
    
    sucesso = await registrar_os(tecnico_id, texto_original, servico, pontos, "FORÇADO PELO SUPERVISOR", "FORCADO")
    if sucesso:
        await update.message.reply_text(f"✅ O.S. forçada com sucesso no nome do técnico!\nServiço: {servico} | Pontos: {pontos}")
    else:
        await update.message.reply_text("❌ Erro ao forçar O.S. (Pode já estar duplicada).")

# ==========================================
# PROCESSAMENTO DE CALLBACKS (BOTÕES INLINE)
# ==========================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa botões clicáveis, caso você adicione no futuro."""
    query = update.callback_query
    await query.answer("Ação recebida!", show_alert=False)

# ==========================================
# HANDLER PRINCIPAL (PROCESSA TEXTO DA O.S.)
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_id = update.effective_user.id
    if not await verificar_usuario(user_id): return
    texto_mensagem = update.message.text

    # ==========================================
    # PORTEIRO (GATEKEEPER) - IGNORA BATE-PAPO
    # ==========================================
    texto_lower = texto_mensagem.lower()
    palavras_chave_os = ['cliente', 'os', 'olt', 'mac', 'rx', 'potência', 'velocidade', 'sinal']
    
    if len(texto_mensagem) < 30 and not any(palavra in texto_lower for palavra in palavras_chave_os):
        return
    # ==========================================

    msg_espera = await update.message.reply_text("⏳ <i>Processando O.S...</i>", parse_mode='HTML')

    try:
        # Extrai Protocolo
        match_proto = re.search(r'(?:protocolo(?:\s+do\s+bot)?|protocolo)[:\s]*([0-9]+)', texto_mensagem, re.IGNORECASE)
        protocolo_extraido = match_proto.group(1).strip().replace(" ", "").upper() if match_proto else "NÃO INFORMADO"

        # Verificação Prévia por Protocolo
        if protocolo_extraido != "NÃO INFORMADO":
            duplicada_proto = await verificar_por_protocolo(protocolo_extraido)
            if duplicada_proto:
                await registrar_tentativa_duplicada(user_id, protocolo_extraido, texto_mensagem)
                try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_espera.message_id)
                except Exception: pass

                await update.message.reply_text(
                    f"⚠️ <b>O.S. duplicada detectada (Protocolo)</b>\n\n"
                    f"• <b>Cliente:</b> {duplicada_proto['cliente']}\n"
                    f"• <b>Serviço:</b> {duplicada_proto['servico'].upper()}\n"
                    f"• <b>Registrada por:</b> {duplicada_proto['tecnico']}\n"
                    f"• <b>Protocolo:</b> {duplicada_proto['protocolo']}\n\n"
                    f"Nenhum ponto adicionado.", parse_mode='HTML'
                )
                return

        # IA Gemini em SEGUNDO PLANO com Timeout ampliado (Cronômetro de 45s)
        try:
            resultado = await asyncio.wait_for(
                asyncio.to_thread(processar_com_ia, texto_mensagem),
                timeout=45.0
            )
        except asyncio.TimeoutError:
            try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_espera.message_id)
            except Exception: pass
            await update.message.reply_text("⏳ A comunicação com o servidor da IA demorou muito (Timeout). Por favor, reenvie a O.S.")
            return
        
        if not resultado.get("is_os", False) or not resultado.get("servicos"):
            try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_espera.message_id)
            except Exception: pass
            await update.message.reply_text("⚠️ Nenhuma OS pontuável identificada.")
            return

        cliente = resultado.get("cliente", "NÃO INFORMADO")
        servico_str = " + ".join(resultado.get("servicos", [])).lower()
        pontos_os = resultado.get("pontos", 0.0)

        # Verificação Secundária por Hash
        duplicada_info = await verificar_duplicidade(protocolo_extraido, cliente, servico_str, texto_mensagem)
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_espera.message_id)
        except Exception: pass

        if duplicada_info:
            await registrar_tentativa_duplicada(user_id, protocolo_extraido, texto_mensagem)
            await update.message.reply_text(
                f"⚠️ <b>O.S. duplicada detectada (Conteúdo/Hash)</b>\n\n"
                f"• <b>Cliente:</b> {duplicada_info['cliente']}\n"
                f"• <b>Serviço:</b> {duplicada_info['servico'].upper()}\n"
                f"• <b>Registrada por:</b> {duplicada_info['tecnico']}\n\n"
                f"Nenhum ponto adicionado.", parse_mode='HTML'
            )
            return

        # Registro Seguro
        sucesso = await registrar_os(user_id, texto_mensagem, servico_str, pontos_os, cliente, protocolo_extraido)
        if not sucesso:
            await registrar_tentativa_duplicada(user_id, protocolo_extraido, texto_mensagem)
            await update.message.reply_text("⚠️ <b>O.S. duplicada detectada.</b> Nenhum ponto adicionado.", parse_mode='HTML')
            return

        # Resumo Mês e Barra de Progresso
        agora = datetime.datetime.now()
        resumo_mes = await obter_resumo_mes(user_id, agora.strftime('%Y'), agora.strftime('%m'))
        
        total_mes = resumo_mes['pontos']
        barra = gerar_barra_progresso(total_mes, META_MENSAL)

        await update.message.reply_text(
            f"✅ <b>OS registrada com sucesso!</b>\n"
            f"• Tipo: {servico_str.upper()}\n"
            f"• Pontos: {pontos_os:.1f}\n"
            f"• Cliente: {cliente}\n"
            f"📊 <b>Total Mês:</b> {total_mes:.1f} pts ({resumo_mes['os']} O.S.)"
            f"{barra}",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Erro crítico: {e}")
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_espera.message_id)
        except Exception: pass
        await update.message.reply_text("❌ Ocorreu um erro ao processar este relatório.")
