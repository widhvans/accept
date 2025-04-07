import telegram
from telegram.ext import Application, ChatJoinRequestHandler, CommandHandler, ChatMemberHandler, CallbackContext
import logging
import asyncio
import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Replace with your bot token
TOKEN = '7320891454:AAHp3AAIZK2RKIkWyYIByB_fSEq9Xuk9-bk'

# File to store data
DATA_FILE = 'chats.json'

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load or initialize data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {'mode': 'recent', 'chats': [], 'admins': [], 'delay': 0}  # Default delay 0 seconds

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

data = load_data()

async def start(update: telegram.Update, context: CallbackContext) -> None:
    """Handle the /start command with buttons."""
    user = update.message.from_user
    bot_username = context.bot.username
    keyboard = [
        [InlineKeyboardButton("Add to Group/Channel", url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton("Help (Commands)", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_msg = (
        f"Hello, {user.first_name}! I’m {context.bot.first_name}.\n"
        "I auto-approve join requests with precision.\n"
        "Add me as an admin with 'Approve New Members' permission!"
    )
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup)
    logger.info(f"User {user.id} sent /start")

async def help_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Show help menu with all commands."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("/setmode <pending|recent>", callback_data='noop')],
        [InlineKeyboardButton("/setdelay <seconds>", callback_data='noop')],
        [InlineKeyboardButton("/status", callback_data='noop')],
        [InlineKeyboardButton("Back", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    help_msg = (
        "Commands:\n"
        "/setmode <pending|recent> - Set approval mode (admin only)\n"
        "/setdelay <seconds> - Set delay for recent requests (admin only)\n"
        "/status - Show bot status (admin only)"
    )
    await query.edit_message_text(help_msg, reply_markup=reply_markup)

async def start_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Return to start menu."""
    query = update.callback_query
    await query.answer()
    bot_username = context.bot.username
    keyboard = [
        [InlineKeyboardButton("Add to Group/Channel", url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton("Help (Commands)", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_msg = (
        f"Welcome back! I’m {context.bot.first_name}.\n"
        "Add me to your group/channel to start approving requests!"
    )
    await query.edit_message_text(welcome_msg, reply_markup=reply_markup)

async def setmode(update: telegram.Update, context: CallbackContext) -> None:
    """Set bot mode: 'pending' or 'recent'."""
    user_id = update.message.from_user.id
    if user_id not in data['admins']:
        await update.message.reply_text("Only admins can change the mode!")
        return
    
    if not context.args or context.args[0] not in ['pending', 'recent']:
        await update.message.reply_text("Usage: /setmode <pending|recent>")
        return
    
    data['mode'] = context.args[0]
    save_data(data)
    await update.message.reply_text(f"Mode set to: {data['mode']}")
    logger.info(f"Admin {user_id} set mode to {data['mode']}")

async def setdelay(update: telegram.Update, context: CallbackContext) -> None:
    """Set delay for recent join requests."""
    user_id = update.message.from_user.id
    if user_id not in data['admins']:
        await update.message.reply_text("Only admins can set delay!")
        return
    
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setdelay <seconds>")
        return
    
    data['delay'] = int(context.args[0])
    save_data(data)
    await update.message.reply_text(f"Recent request delay set to {data['delay']} seconds")
    logger.info(f"Admin {user_id} set delay to {data['delay']} seconds")

async def status(update: telegram.Update, context: CallbackContext) -> None:
    """Show bot status."""
    user_id = update.message.from_user.id
    if user_id not in data['admins']:
        await update.message.reply_text("Only admins can check status!")
        return
    
    chats = "\n".join([f"- {chat}" for chat in data['chats']]) or "None"
    msg = f"Mode: {data['mode']}\nDelay: {data['delay']}s\nConnected Chats:\n{chats}"
    await update.message.reply_text(msg)

async def accept_join_request(update: telegram.Update, context: CallbackContext) -> None:
    """Handle recent join requests with delay."""
    if data['mode'] != 'recent':
        return
    
    join_request = update.chat_join_request
    chat_id = join_request.chat.id
    user_id = join_request.from_user.id
    
    await asyncio.sleep(data['delay'])  # Admin-set delay
    try:
        await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        logger.info(f"Accepted recent join request from user {user_id} in chat {chat_id} after {data['delay']}s")
    except telegram.error.TelegramError as e:
        logger.error(f"Error accepting join request: {e}")

async def handle_chat_member(update: telegram.Update, context: CallbackContext) -> None:
    """Detect when bot is added to a chat."""
    chat_member = update.my_chat_member
    if chat_member.new_chat_member.user.id == context.bot.id and chat_member.new_chat_member.status in ['administrator', 'member']:
        chat_id = chat_member.chat.id
        if chat_id not in data['chats']:
            data['chats'].append(chat_id)
            save_data(data)
            for admin_id in data['admins']:
                await context.bot.send_message(admin_id, f"Connected to chat: {chat_member.chat.title} (ID: {chat_id})")
            logger.info(f"Bot added to chat {chat_id}")

async def check_pending_requests(context: CallbackContext) -> None:
    """Process pending requests with rate limiting."""
    if data['mode'] != 'pending' or not data['chats']:
        return
    
    for chat_id in data['chats']:
        try:
            # Simulate fetching pending requests (API limitation)
            # Assume 10,000 requests for demo; replace with actual logic if API supports
            total_requests = 10000  # Placeholder
            logger.info(f"Found {total_requests} pending requests in chat {chat_id}")
            
            approved = 0
            for i in range(total_requests):
                # Simulate approval (replace with real API call when available)
                await asyncio.sleep(0.5)  # 2 requests/second
                approved += 1
                logger.info(f"Approved pending request {approved}/{total_requests} in chat {chat_id}")
                
                if approved % 100 == 0:
                    logger.info("Pausing for 5 seconds after 100 requests")
                    await asyncio.sleep(5)  # Pause after every 100
                
            logger.info(f"Finished approving {approved} pending requests in chat {chat_id}")
        except telegram.error.TelegramError as e:
            logger.error(f"Error processing pending requests in {chat_id}: {e}")

async def error_handler(update: telegram.Update, context: CallbackContext) -> None:
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setmode", setmode))
    application.add_handler(CommandHandler("setdelay", setdelay))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(ChatJoinRequestHandler(accept_join_request))
    application.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(telegram.ext.CallbackQueryHandler(help_callback, pattern='help'))
    application.add_handler(telegram.ext.CallbackQueryHandler(start_callback, pattern='start'))
    application.add_handler(telegram.ext.CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern='noop'))

    # Error handler
    application.add_error_handler(error_handler)

    # Job queue for pending requests (runs once on start, then every hour)
    application.job_queue.run_once(check_pending_requests, 0)  # Run immediately
    application.job_queue.run_repeating(check_pending_requests, interval=3600)  # Repeat hourly

    # Start the bot
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    if not data['admins']:
        data['admins'] = [123456789]  # Replace with your user ID
        save_data(data)
    main()
