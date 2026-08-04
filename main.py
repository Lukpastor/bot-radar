from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, logger

import database
import handlers


# ==========================================
# INICIALIZAÇÃO DO BOT
# ==========================================
async def inicializar_bot(application: Application) -> None:
    """
    Executado automaticamente antes do polling começar.
    """
    logger.info("Inicializando banco de dados...")

    await database.iniciar_banco()

    logger.info("Banco de dados inicializado com sucesso.")


# ==========================================
# ENCERRAMENTO DO BOT
# ==========================================
async def encerrar_bot(application: Application) -> None:
    """
    Executado quando o bot estiver sendo desligado.
    """
    logger.info("Encerrando recursos do bot...")

    # Caso seu database.py possua uma função para fechar conexão,
    # você pode ativar este trecho:
    #
    # await database.fechar_banco()

    logger.info("Recursos encerrados com segurança.")


# ==========================================
# TRATAMENTO GLOBAL DE ERROS
# ==========================================
async def tratar_erro(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Captura erros não tratados nos handlers para impedir
    que uma falha isolada interrompa o bot.
    """
    logger.exception(
        "Erro não tratado durante o processamento de uma atualização:",
        exc_info=context.error,
    )

    if not isinstance(update, Update):
        return

    mensagem = update.effective_message

    if mensagem:
        try:
            await mensagem.reply_text(
                "❌ Ocorreu um erro ao processar sua solicitação.\n"
                "Tente novamente em alguns instantes."
            )
        except Exception as erro_resposta:
            logger.warning(
                "Não foi possível enviar a mensagem de erro: "
                f"{erro_resposta}"
            )


# ==========================================
# REGISTRO DOS HANDLERS
# ==========================================
def registrar_handlers(app: Application) -> None:
    """
    Registra todos os comandos, mensagens e callbacks.
    """

    # --------------------------------------
    # COMANDOS GERAIS
    # --------------------------------------
    app.add_handler(
        CommandHandler(
            "start",
            handlers.ajuda,
        )
    )

    app.add_handler(
        CommandHandler(
            "ajuda",
            handlers.ajuda,
        )
    )

    app.add_handler(
        CommandHandler(
            "pontos",
            handlers.pontos,
        )
    )

    app.add_handler(
        CommandHandler(
            "historico",
            handlers.historico,
        )
    )

    app.add_handler(
        CommandHandler(
            "ranking",
            handlers.ranking,
        )
    )

    app.add_handler(
        CommandHandler(
            "consultar_cliente",
            handlers.consultar_cliente,
        )
    )

    app.add_handler(
        CommandHandler(
            "excluir_ultima",
            handlers.excluir_ultima,
        )
    )

    app.add_handler(
        CommandHandler(
            "contar",
            handlers.contar,
        )
    )

    # --------------------------------------
    # COMANDOS DE SUPERVISOR
    # --------------------------------------
    app.add_handler(
        CommandHandler(
            "add",
            handlers.add_user,
        )
    )

    app.add_handler(
        CommandHandler(
            "delet",
            handlers.delet_user,
        )
    )

    app.add_handler(
        CommandHandler(
            "apagar_usuario",
            handlers.apagar_usuario,
        )
    )

    app.add_handler(
        CommandHandler(
            "apagar_os",
            handlers.apagar_os,
        )
    )

    app.add_handler(
        CommandHandler(
            "exportar",
            handlers.exportar,
        )
    )

    app.add_handler(
        CommandHandler(
            "forcar_os",
            handlers.forcar_os,
        )
    )

    # --------------------------------------
    # BOTÕES INLINE
    # --------------------------------------
    app.add_handler(
        CallbackQueryHandler(
            handlers.handle_callback,
        )
    )

    # --------------------------------------
    # MENSAGENS DE O.S.
    # --------------------------------------
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers.handle_message,
        )
    )

    # --------------------------------------
    # TRATAMENTO DE ERROS
    # --------------------------------------
    app.add_error_handler(
        tratar_erro
    )


# ==========================================
# FUNÇÃO PRINCIPAL
# ==========================================
def main() -> None:
    """
    Monta e inicia o bot.
    """

    if not BOT_TOKEN:
        logger.critical(
            "BOT_TOKEN não encontrado. "
            "Verifique o arquivo .env e o config.py."
        )
        return

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(inicializar_bot)
        .post_shutdown(encerrar_bot)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    registrar_handlers(app)

    logger.info(
        "Bot 2.0 operante — "
        "Sistema de Metas e Consulta Online."
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=True,
    )


# ==========================================
# EXECUÇÃO
# ==========================================
if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        logger.info(
            "Bot interrompido pelo usuário."
        )

    except SystemExit:
        logger.info(
            "Bot desligado pelo sistema."
        )

    except Exception:
        logger.exception(
            "Erro crítico durante a execução do bot."
        )
