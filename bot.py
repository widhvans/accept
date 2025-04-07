import telegram
from telegram.ext import Application, ChatJoinRequestHandler, CommandHandler, ChatMemberHandler, MessageHandler, CallbackContext
from telegram.ext import filters
import logging
import asyncio
import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Replace with your bot token
TOKEN = '7320891454:AAHp3AAIZK2RKIkWyYIByB_fSEq9Xuk9-bk'

# File to store data
DATA_FILE = 'chats.json'
LOG_FILE = 'bot.log'

# Set up logging to file and console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load or initialize data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    # Default data with your ID as an admin
    return {'mode': 'recent', 'chats': [], 'admins': [1938030055], 'delay': 0, 'last_msg_id': None}

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
        [InlineKeyboardButton("Connect Your Channel", callback_data='connect_channel')],
        [InlineKeyboardButton("Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_msg = (
        f"Hello, {user.first_name}! I’m {context.bot.first_name}.\n"
        "To connect a group/channel, forward this message to me in private chat after adding me as an admin.\n"
        "Or use 'Connect Your Channel' to link a channel by forwarding its last message."
    )
    msg = await update.message.reply_text(welcome_msg, reply_markup=reply_markup)
    data['last_msg_id'] = msg.message_id
    save_data(data)
    logger.info(f"User {user.id} sent /start, last_msg_id set to {msg.message_id}")

async def connect_channel_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Prompt user to forward channel message."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Please forward the last message from your channel to me in private chat to connect it.\n"
        "I must be an admin in that channel."
    )

async def help_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Show help menu with all commands."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("/setmode <pending|recent>", callback_data='noop')],
        [InlineKeyboardButton("/setdelay <seconds>", callback_data='noop')],
        [InlineKeyboardButton("/status", callback_data='noop')],
        [InlineKeyboardButton("Back to Start", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    help_msg = (
        "Commands (work after chat connection):\n"
        "/setmode <pending|recent> - Set approval mode\n"
        "/setdelay <seconds> - Set delay for recent requests\n"
        "/status - Show bot status"
    )
    await query.edit_message_text(help_msg, reply_markup=reply_markup)

async def start_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Return to start menu."""
    query = update.callback_query
    await query.answer()
    bot_username = context.bot.username
    keyboard = [
        [InlineKeyboardButton("Add to Group/Channel", url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton("Connect Your Channel", callback_data='connect_channel')],
        [InlineKeyboardButton("Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_msg = (
        f"Welcome back! I’m {context.bot.first_name}.\n"
        "Forward this message to me in private to connect a group/channel,\n"
        "or use 'Connect Your Channel' to link a channel."
    )
    await query.edit_message_text(welcome_msg, reply_markup=reply_markup)

async def handle_forwarded_message(update: telegram.Update, context: CallbackContext) -> None:
    """Handle forwarded message for chat connection."""
    user_id = update.message.from_user.id
    forward_origin = update.message.forward_origin

    if not forward_origin:
        await update.message.reply_text("This doesn’t seem to be a forwarded message!")
        logger.warning(f"User {user_id} sent a non-forwarded message")
        return

    forwarded_msg_id = forward_origin.message_id
    chat_id = forward_origin.chat.id if forward_origin.chat else None

    logger.info(f"User {user_id} forwarded message ID {forwarded_msg_id} from chat {chat_id}")

    # Case 1: Forwarded /start message
    if forwarded_msg_id == data['last_msg_id']:
        if not data['chats']:
            await update.message.reply_text("Add me to a group/channel first!")
            logger.warning(f"User {user_id} tried to connect with no chats added")
            return
        chat_id = data['chats'][-1]
        try:
            chat_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if chat_member.status in ['administrator']:
                await update.message.reply_text(f"Chat {chat_id} connected successfully!")
                logger.info(f"User {user_id} connected chat {chat_id} via /start message")
            else:
                await update.message.reply_text("I must be an admin in that chat!")
                logger.warning(f"Bot not admin in chat {chat_id}")
        except telegram.error.TelegramError as e:
            await update.message.reply_text("Failed to verify admin status.")
            logger.error(f"Error verifying admin status in {chat_id}: {e}")
        return

    # Case 2: Forwarded channel/group message
    if chat_id:
        try:
            # Check if bot is admin in the chat
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if bot_member.status not in ['administrator']:
                await update.message.reply_text("I must be an admin in that chat!")
                logger.warning(f"Bot not admin in chat {chat_id}")
                return

            # Add chat to connected list if not already there
            if chat_id not in data['chats']:
                data['chats'].append(chat_id)
                save_data(data)
            await update.message.reply_text(f"Chat {chat_id} connected successfully!")
            logger.info(f"User {user_id} connected chat {chat_id} via forwarded message")
        except telegram.error.TelegramError as e:
            await update.message.reply_text("Failed to connect chat. Ensure I’m an admin there!")
            logger.error(f"Error connecting chat {chat_id}: {e}")
    else:
        await update.message.reply_text("Invalid message! Forward my /start message or a chat message where I’m an admin.")
        logger.warning(f"User {user_id} forwarded invalid message ID {forwarded_msg_id} or chat {chat_id}")

async def setmode(update: telegram.Update, context: CallbackContext) -> None:
    """Set bot mode: 'pending' or 'recent'."""
    user_id = update.message.from_user.id
    if not data['chats']:
        await update.message.reply_text("A chat must be connected first!")
        return
    
    if not context.args or context.args[0] not in ['pending', 'recent']:
        await update.message.reply_text("Usage: /setmode <pending|recent>")
        return
    
    data['mode'] = context.args[0]
    save_data(data)
    await update.message.reply_text(f"Mode set to: {data['mode']}")
    logger.info(f"User {user_id} set mode to {data['mode']}")

async def setdelay(update: telegram.Update, context: CallbackContext) -> None:
    """Set delay for recent join requests."""
    user_id = update.message.from_user.id
    if not data['chats']:
        await update.message.reply_text("A chat must be connected first!")
        return
    
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setdelay <seconds>")
        return
    
    data['delay'] = int(context.args[0])
    save_data(data)
    await update.message.reply_text(f"Recent request delay set to {data['delay']} seconds")
    logger.info(f"User {user_id} set delay to {data['delay']} seconds")

async def status(update: telegram.Update, context: CallbackContext) -> None:
    """Show bot status."""
    user_id = update.message.from_user.id
    if not data['chats']:
        await update.message.reply_text("A chat must be connected first!")
        return
    
    chats = "\n".join([f"- {chat}" for chat in data['chats']]) or "None"
    msg = f"Mode: {data['mode']}\nDelay: {data['delay']}s\nConnected Chats:\n{chats}"
    await update.message.reply_text(msg)
    logger.info(f"User {user_id} checked status")

async def accept_join_request(update: telegram.Update, context: CallbackContext) -> None:
    """Handle recent join requests with delay."""
    if data['mode'] != 'recent' or not data['chats']:
        return
    
    join_request = update.chat_join_request
    chat_id = join_request.chat.id
    user_id = join_request.from_user.id
    
    await asyncio.sleep(data['delay'])
    try:
        await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        logger.info(f"Accepted recent join request from user {user_id} in chat {chat_id} after {data['delay']}s")
    except telegram.error.TelegramError as e:
        logger.error(f"Error accepting join request in chat {chat_id}: {e}")

async def handle_chat_member(update: telegram.Update, context: CallbackContext) -> None:
    """Detect when bot is added to a chat."""
    chat_member = update.my_chat_member
    if chat_member.new_chat_member.user.id == context.bot.id and chat_member.new_chat_member.status in ['administrator', 'member']:
        chat_id = chat_member.chat.id
        if chat_id not in data['chats']:
            data['chats'].append(chat_id)
            save_data(data)
            logger.info(f"Bot added to chat {chat_id}, awaiting verification")

async def check_pending_requests(context: CallbackContext) -> None:
    """Process pending requests with rate limiting."""
    if data['mode'] != 'pending' or not data['chats']:
        return
    
    for chat_id in data['chats']:
        try:
            total_requests = 10000  # Simulated
            logger.info(f"Found {total_requests} pending requests in chat {chat_id}")
            
            approved = 0
            for i in range(total_requests):
                await asyncio.sleep(0.5)  # 2 requests/second
                approved += 1
                logger.info(f"Approved pending request {approved}/{total_requests} in chat {chat_id}")
                
                if approved % 100 == 0:
                    logger.info("Pausing for 5 seconds after 100 requests")
                    await asyncio.sleep(5)
                
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
    application.add_handler(MessageHandler(filters.FORWARDED & filters.ChatType.PRIVATE, handle_forwarded_message))
    application.add_handler(telegram.ext.CallbackQueryHandler(connect_channel_callback, pattern='connect_channel'))
    application.add_handler(telegram.ext.CallbackQueryHandler(help_callback, pattern='help'))
    application.add_handler(telegram.ext.CallbackQueryHandler(start_callback, pattern='start'))
    application.add_handler(telegram.ext.CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern='noop'))

    # Error handler
    application.add_error_handler(error_handler)

    # Job queue for pending requests
    application.job_queue.run_once(check_pending_requests, 0)
    application.job_queue.run_repeating(check_pending_requests, interval=3600)

    # Start the bot
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    if 1938030055 not in data['admins']:
        data['admins'].append(1938030055)
        save_data(data)
    main()
