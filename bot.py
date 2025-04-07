import telegram
from telegram.ext import Updater, ChatJoinRequestHandler, CallbackContext
import logging

# Replace 'YOUR_BOT_TOKEN' with your bot token from BotFather
TOKEN = '7320891454:AAHp3AAIZK2RKIkWyYIByB_fSEq9Xuk9-bk'

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def accept_join_request(update: telegram.Update, context: CallbackContext) -> None:
    """Automatically accept join requests."""
    join_request = update.chat_join_request
    chat_id = join_request.chat.id
    user_id = join_request.from_user.id
    
    try:
        # Approve the join request
        context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        logger.info(f"Accepted join request from user {user_id} in chat {chat_id}")
    except telegram.error.TelegramError as e:
        logger.error(f"Error accepting join request: {e}")

def error_handler(update: telegram.Update, context: CallbackContext) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add handler for chat join requests
    dp.add_handler(ChatJoinRequestHandler(accept_join_request))

    # Log all errors
    dp.add_error_handler(error_handler)

    # Start the bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    logger.info("Bot is running...")
    updater.idle()

if __name__ == '__main__':
    main()
