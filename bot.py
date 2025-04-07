import telegram
from telegram.ext import Application, ChatJoinRequestHandler, CommandHandler, ChatMemberHandler, MessageHandler, CallbackContext
from telegram.ext import filters
import logging
import asyncio
import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Dict

# Replace with your bot token
TOKEN = '7320891454:AAHp3AAIZK2RKIkWyYIByB_fSEq9Xuk9-bk'

# File to store data
DATA_FILE = 'chats.json'
LOG_FILE = 'bot.log'

# Set up logging to file and console with DEBUG level
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global state
stop_processing: Dict[int, bool] = {}  # Per-chat stop flag
pending_counts: Dict[int, int] = {}    # Simulated pending counts per chat

# Load or initialize data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            logger.debug(f"Loaded data from {DATA_FILE}: {data}")
            return data
    default_data = {'mode': None, 'chats': [], 'admins': [1938030055], 'delay': 0, 'last_msg_id': None}
    logger.debug(f"Initialized default data: {default_data}")
    return default_data

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)
    logger.debug(f"Saved data to {DATA_FILE}: {data}")

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
        f"🌟 Welcome, {user.first_name}, to the realm of {context.bot.first_name}!\n"
        "Unleash my powers by forwarding this message in private to bind a chat,\n"
        "or tap 'Connect Your Channel' to summon its essence!"
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
        "🔮 Weave your spell! Forward the last message from your channel to me in private.\n"
        "I must wield admin powers there!"
    )
    logger.debug(f"User {query.from_user.id} triggered connect_channel_callback")

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
        "✨ Enchanted Commands:\n"
        "/setmode <pending|recent> - Shape your fate\n"
        "/setdelay <seconds> - Twist time’s thread\n"
        "/status - Peer into the arcane"
    )
    await query.edit_message_text(help_msg, reply_markup=reply_markup)
    logger.debug(f"User {query.from_user.id} triggered help_callback")

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
        f"🌌 Back again, seeker? I’m {context.bot.first_name}.\n"
        "Forward this in private to bind a chat,\n"
        "or summon a channel with 'Connect Your Channel'!"
    )
    await query.edit_message_text(welcome_msg, reply_markup=reply_markup)
    logger.debug(f"User {query.from_user.id} triggered start_callback")

async def mode_selection(update: telegram.Update, context: CallbackContext, chat_id: int) -> None:
    """Show mode selection after connecting a chat."""
    keyboard = [
        [InlineKeyboardButton("Pending Mode", callback_data=f'mode_pending_{chat_id}')],
        [InlineKeyboardButton("Recent Mode", callback_data=f'mode_recent_{chat_id}')],
        [InlineKeyboardButton("Magic Wand", callback_data=f'wand_{chat_id}')],
        [InlineKeyboardButton("Retry Magic", callback_data=f'retry_{chat_id}')]  # Magical fallback
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🌠 Chat {chat_id} bound to my will!\n"
        "Choose your path:\n"
        "- Pending Mode: Unveil and approve lost souls\n"
        "- Recent Mode: Greet new spirits instantly\n"
        "- Magic Wand: Toggle modes with a flick!\n"
        "- Retry Magic: Recast if the spell falters!",
        reply_markup=reply_markup
    )
    logger.debug(f"Sent mode selection for chat {chat_id} to user {update.message.from_user.id}, callback_data: {[[btn.callback_data for btn in row] for row in keyboard]}")

async def mode_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Handle mode selection."""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Received mode callback from user {query.from_user.id}: {query.data}")
    try:
        mode, chat_id = query.data.split('_')[1], int(query.data.split('_')[2])
        data['mode'] = mode
        save_data(data)
        await query.edit_message_text(
            f"✨ {mode.capitalize()} Mode conjured for chat {chat_id}!\n"
            f"{'The past awakens...' if mode == 'pending' else 'The present ignites!'}"
        )
        logger.info(f"User {query.from_user.id} set mode to {mode} for chat {chat_id}")
        if mode == 'pending':
            await check_pending_requests(context, chat_id, query.from_user.id)
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing mode callback data {query.data}: {e}")
        await query.edit_message_text("💥 The spell misfired! Try 'Retry Magic'.")

async def wand_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Toggle mode with a magic wand."""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Received wand callback from user {query.from_user.id}: {query.data}")
    try:
        chat_id = int(query.data.split('_')[1])
        data['mode'] = 'recent' if data['mode'] == 'pending' else 'pending'
        save_data(data)
        await query.edit_message_text(f"🪄 Wand waved! Mode switched to {data['mode']} for {chat_id}!")
        
   
logger.info(f"User {query.from_user.id} toggled mode to {data['mode']} for chat {chat_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing wand callback data {query.data}: {e}")
        await query.edit_message_text("💥 Wand malfunction! Try 'Retry Magic'.")

async def stop_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Stop request processing."""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Received stop callback from user {query.from_user.id}: {query.data}")
    chat_id_str = query.data.split('_')[1] if '_' in query.data else None
    try:
        chat_id = int(chat_id_str) if chat_id_str else None
        if chat_id:
            stop_processing[chat_id] = True
            await query.edit_message_text(f"🛑 The spell over {chat_id} has been broken!")
            logger.info(f"User {query.from_user.id} stopped processing for chat {chat_id}")
        else:
            await query.edit_message_text("🛑 No chat specified to stop!")
            logger.warning(f"User {query.from_user.id} triggered stop with no chat ID")
    except ValueError as e:
        logger.error(f"Error parsing stop callback data {query.data}: {e}")
        await query.edit_message_text("💥 Stop spell failed! Try again.")

async def retry_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Retry mode selection if buttons fail."""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Received retry callback from user {query.from_user.id}: {query.data}")
    try:
        chat_id = int(query.data.split('_')[1])
        await query.edit_message_text(f"🔄 Recasting the spell for {chat_id}...")
        await mode_selection(query.message, context, chat_id)
        logger.info(f"User {query.from_user.id} retried mode selection for chat {chat_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing retry callback data {query.data}: {e}")
        await query.edit_message_text("💥 Retry failed! Contact the wizard.")

async def handle_forwarded_message(update: telegram.Update, context: CallbackContext) -> None:
    """Handle forwarded message for chat connection."""
    user_id = update.message.from_user.id
    forward_origin = update.message.forward_origin

    if not forward_origin:
        await update.message.reply_text("🔍 No magic here, mortal! Forward a message!")
        logger.warning(f"User {user_id} sent a non-forwarded message")
        return

    forwarded_msg_id = forward_origin.message_id
    chat_id = forward_origin.chat.id if forward_origin.chat else None

    logger.info(f"User {user_id} forwarded message ID {forwarded_msg_id} from chat {chat_id}")

    if forwarded_msg_id == data['last_msg_id']:
        if not data['chats']:
            await update.message.reply_text("🌑 Summon a chat first!")
            logger.warning(f"User {user_id} tried to connect with no chats added")
            return
        chat_id = data['chats'][-1]
    if chat_id:
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if bot_member.status not in ['administrator']:
                await update.message.reply_text("⛔ I need admin powers in that realm!")
                logger.warning(f"Bot not admin in chat {chat_id}")
                return
            if chat_id not in data['chats']:
                data['chats'].append(chat_id)
                save_data(data)
            await mode_selection(update, context, chat_id)
            logger.info(f"User {user_id} connected chat {chat_id} via forwarded message")
        except telegram.error.TelegramError as e:
            await update.message.reply_text("💥 The spell failed! Ensure I’m an admin!")
            logger.error(f"Error connecting chat {chat_id}: {e}")
    else:
        await update.message.reply_text("❌ Invalid scroll! Forward my /start or a chat message!")
        logger.warning(f"User {user_id} forwarded invalid message ID {forwarded_msg_id} or chat {chat_id}")

async def setmode(update: telegram.Update, context: CallbackContext) -> None:
    """Set bot mode manually."""
    user_id = update.message.from_user.id
    if not data['chats']:
        await update.message.reply_text("🌑 Bind a chat first, seeker!")
        logger.warning(f"User {user_id} tried /setmode with no chats")
        return
    
    if not context.args or context.args[0] not in ['pending', 'recent']:
        await update.message.reply_text("✨ Whisper: /setmode <pending|recent>")
        logger.warning(f"User {user_id} used invalid /setmode syntax: {context.args}")
        return
    
    data['mode'] = context.args[0]
    save_data(data)
    await update.message.reply_text(f"🌟 Mode woven to: {data['mode']}")
    logger.info(f"User {user_id} set mode to {data['mode']}")

async def setdelay(update: telegram.Update, context: CallbackContext) -> None:
    """Set delay for recent join requests."""
    user_id = update.message.from_user.id
    if not data['chats']:
        await update.message.reply_text("🌑 Bind a chat first, seeker!")
        logger.warning(f"User {user_id} tried /setdelay with no chats")
        return
    
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("✨ Whisper: /setdelay <seconds>")
        logger.warning(f"User {user_id} used invalid /setdelay syntax: {context.args}")
        return
    
    data['delay'] = int(context.args[0])
    save_data(data)
    await update.message.reply_text(f"⏳ Time bent to {data['delay']} seconds")
    logger.info(f"User {user_id} set delay to {data['delay']} seconds")

async def status(update: telegram.Update, context: CallbackContext) -> None:
    """Show bot status with flair."""
    user_id = update.message.from_user.id
    if not data['chats']:
        await update.message.reply_text("🌑 No realms bound yet!")
        logger.warning(f"User {user_id} checked status with no chats")
        return
    
    chats = "\n".join([f"- {chat} ({pending_counts.get(chat, 0)} souls await)" for chat in data['chats']]) or "None"
    msg = f"🌌 The Oracle Speaks:\nMode: {data['mode'] or 'Unchosen'}\n⏳ Delay: {data['delay']}s\n✨ Realms:\n{chats}"
    await update.message.reply_text(msg)
    logger.info(f"User {user_id} checked status: {msg}")

async def accept_join_request(update: telegram.Update, context: CallbackContext) -> None:
    """Handle recent join requests with stop button."""
    if data['mode'] != 'recent' or not data['chats']:
        logger.debug(f"Recent mode not active or no chats: mode={data['mode']}, chats={data['chats']}")
        return
    
    join_request = update.chat_join_request
    chat_id = join_request.chat.id
    user_id = join_request.from_user.id
    
    stop_processing[chat_id] = False
    keyboard = [[InlineKeyboardButton("Stop", callback_data=f'stop_{chat_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    status_msg = await context.bot.send_message(chat_id=user_id, text=f"🌟 Opening the gates to {chat_id}...", reply_markup=reply_markup)
    logger.debug(f"Sent approval message to {user_id} for chat {chat_id}")
    
    await asyncio.sleep(data['delay'])
    if stop_processing.get(chat_id, False):
        await status_msg.edit_text("🛑 Gates sealed by your command!")
        stop_processing[chat_id] = False
        logger.info(f"Approval stopped for user {user_id} in chat {chat_id}")
        return
    
    try:
        await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        await status_msg.edit_text(f"✨ {user_id}, you’ve crossed into {chat_id}!")
        logger.info(f"Accepted recent join request from user {user_id} in chat {chat_id} after {data['delay']}s")
    except telegram.error.TelegramError as e:
        await status_msg.edit_text("💥 The gates resisted!")
        logger.error(f"Error accepting join request in chat {chat_id}: {e}")

async def handle_chat_member(update: telegram.Update, context: CallbackContext) -> None:
    """Detect when bot is added to a chat."""
    chat_member = update.my_chat_member
    if chat_member.new_chat_member.user.id == context.bot.id and chat_member.new_chat_member.status in ['administrator', 'member']:
        chat_id = chat_member.chat.id
        if chat_id not in data['chats']:
            data['chats'].append(chat_id)
            save_data(data)
            logger.info(f"Bot added to chat {chat_id}, awaiting binding")

async def check_pending_requests(context: CallbackContext, chat_id: int, admin_chat_id: int) -> None:
    """Process pending requests with stop button and real count placeholder."""
    if data['mode'] != 'pending' or chat_id not in data['chats']:
        logger.debug(f"Pending mode not active or chat not bound: mode={data['mode']}, chat={chat_id}")
        return
    
    # Simulate pending count (replace with real API call when available)
    pending_count = pending_counts.get(chat_id, 0)
    logger.info(f"🔍 Detected {pending_count} pending requests in chat {chat_id} (simulated)")
    
    if pending_count == 0:
        await context.bot.send_message(chat_id=admin_chat_id, text=f"🌑 No souls await in {chat_id}!")
        logger.info(f"No pending requests in chat {chat_id}")
        return
    
    stop_processing[chat_id] = False
    keyboard = [[InlineKeyboardButton("Stop", callback_data=f'stop_{chat_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    status_msg = await context.bot.send_message(chat_id=admin_chat_id, text=f"🌠 Unveiling {pending_count} souls in {chat_id}...", reply_markup=reply_markup)
    logger.debug(f"Started pending request processing for chat {chat_id}")
    
    approved = 0
    for i in range(pending_count):
        if stop_processing.get(chat_id, False):
            await status_msg.edit_text(f"🛑 Paused at {approved}/{pending_count} souls in {chat_id}!")
            stop_processing[chat_id] = False
            logger.info(f"Pending request processing stopped at {approved}/{pending_count} for chat {chat_id}")
            return
        await asyncio.sleep(0.5)
        approved += 1
        await status_msg.edit_text(f"🌠 Unveiling souls in {chat_id}: {approved}/{pending_count}")
        logger.info(f"Approved pending request {approved}/{pending_count} in chat {chat_id}")
        
        if approved % 10 == 0:
            await asyncio.sleep(2)
    
    await status_msg.edit_text(f"✨ All {approved} souls unveiled in {chat_id}!")
    logger.info(f"Finished approving {approved} pending requests in chat {chat_id}")

async def debug_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Catch-all callback handler for debugging."""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Caught unhandled callback from user {query.from_user.id}: {query.data}")
    await query.edit_message_text(f"🔍 Uncharted magic detected: {query.data}\nTry 'Retry Magic' or contact the wizard!")

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
    application.add_handler(telegram.ext.CallbackQueryHandler(mode_callback, pattern=r'mode_(pending|recent)_\d+'))
    application.add_handler(telegram.ext.CallbackQueryHandler(wand_callback, pattern=r'wand_\d+'))
    application.add_handler(telegram.ext.CallbackQueryHandler(stop_callback, pattern=r'stop(_\d+)?'))
    application.add_handler(telegram.ext.CallbackQueryHandler(retry_callback, pattern=r'retry_\d+'))
    application.add_handler(telegram.ext.CallbackQueryHandler(debug_callback))  # Catch-all for unhandled callbacks

    # Error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("✨ The arcane awakens...")
    application.run_polling()

if __name__ == '__main__':
    if 1938030055 not in data['admins']:
        data['admins'].append(1938030055)
        save_data(data)
    main()
