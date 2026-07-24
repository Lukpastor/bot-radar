import os
import time
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import database
import handlers
from config import logger

async def run_bot_async():
    load_dotenv() 
    
    # Inicializa o banco de dados de forma assíncrona
    await database.iniciar_banco()

    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("CRÍTICO: Token não encontrado no arquivo .env!")
        return 
    
    app = None
    for attempt in range(5):
        try:
            app = ApplicationBuilder().token(bot_token).build()
            break 
        except Exception: 
            await asyncio.sleep(5)

    if app is None: 
        return

    # Sistema
    app.add_handler(CommandHandler("start", handlers.ajuda))
    app.add_handler(CommandHandler("ajuda", handlers.ajuda))
    app.add_handler(CommandHandler("pontos", handlers.pontos))
    app.add_handler(CommandHandler("historico", handlers.historico))
    app.add_handler(CommandHandler("ranking", handlers.ranking))
    app.add_handler(CommandHandler("consultar_cliente", handlers.consultar_cliente))
    app.add_handler(CommandHandler("excluir_ultima", handlers.excluir_ultima))
    app.add_handler(CommandHandler("contar", handlers.contar))
    
    # Supervisor
    app.add_handler(CommandHandler("add", handlers.add_user))
    app.add_handler(CommandHandler("delet", handlers.delet_user))
    app.add_handler(CommandHandler("apagar_usuario", handlers.apagar_usuario))
    app.add_handler(CommandHandler("apagar_os", handlers.apagar_os))
    app.add_handler(CommandHandler("exportar", handlers.exportar))
    app.add_handler(CommandHandler("forcar_os", handlers.forcar_os))
    
    # Processamento
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    app.add_handler(CallbackQueryHandler(handlers.handle_callback))

    # Inicialização e execução nativa compatível com Python 3.13+
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    
    logger.info("Bot 2.0 Assíncrono Operante - Sistema de Metas e Consulta Online!")

    # Mantém o bot rodando indefinidamente na nuvem
    stop_signal = asyncio.get_running_loop().create_future()
    await stop_signal

def main() -> None:
    try:
        asyncio.run(run_bot_async())
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == '__main__':
    main()
