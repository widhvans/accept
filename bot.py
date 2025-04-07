import telegram
from telegram.ext import Application, ChatJoinRequestHandler, CommandHandler, ChatMemberHandler, MessageHandler, CallbackContext
from telegram.ext import filters
import logging
import asyncio
import json
import os
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Dict

# Replace with your bot token
TOKEN = '7320891454:AAHp3AAIZK2RKIkWyYIByB_fSEq9Xuk9-bk'

# File to store data
DATA_FILE = 'chats.json'
LOG_FILE = 'bot.log'

# Set up logging with DEBUG level
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
stop_processing: Dict[int, bool] = {}
pending_counts: Dict[int, int] = {}
dashboard_msg_ids: Dict[int, int] = {}  # Track dashboard message IDs per chat

# Load or initialize data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            logger.debug(f"Loaded data: {data}")
            return data
    default_data = {'mode': None, 'chats': [], 'admins': [1938030055], 'delay': 0, 'last_msg_id': None}
    logger.debug(f"Initialized default data: {default_data}")
    return default_data

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)
    logger.debug(f"Saved data: {data}")

data = load_data()

async def start(update: telegram.Update, context: CallbackContext) -> None:
    """Handle the /start command."""
    user = update.message.from_user
    bot_username = context.bot.username
    keyboard = [
        [InlineKeyboardButton("Add to Group/Channel", url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton("Connect Your Channel", callback_data='connect_channel')],
        [InlineKeyboardButton("Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_msg = (
        f"🌟 Welcome, {user.first_name}, to the cosmic realm of {context.bot.first_name}!\n"
        "Forward this in private to bind a chat, or summon a channel with 'Connect Your Channel'!"
    )
    msg = await update.message.reply_text(welcome_msg, reply_markup=reply_markup)
    data['last_msg_id'] = msg.message_id
    save_data(data)
    logger.info(f"User {user.id} started bot, last_msg_id: {msg.message_id}")

async def connect_channel_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Prompt user to forward channel message."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔮 Cast a spell! Forward a channel message to me in private. I must be an admin!")
    logger.debug(f"User {query.from_user.id} triggered connect_channel_callback")

async def help_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Show help menu."""
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
        "✨ Cosmic Commands:\n"
        "/setmode <pending|recent> - Bend fate\n"
        "/setdelay <seconds> - Warp time\n"
        "/status - Gaze into the void"
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
        f"🌌 Returned, seeker? I’m {context.bot.first_name}.\n"
        "Forward this to bind a chat, or summon a channel!"
    )
    await query.edit_message_text(welcome_msg, reply_markup=reply_markup)
    logger.debug(f"User {query.from_user.id} triggered start_callback")

async def update_dashboard(context: CallbackContext, chat_id: int, user_id: int, message_id: int = None) -> None:
    """Update the dynamic dashboard for a chat."""
    mode = data['mode'] or "Unchosen"
    pending_count = pending_counts.get(chat_id, 0)
    keyboard = [
        [InlineKeyboardButton(f"{'★ ' if mode == 'pending' else ''}Pending Mode", callback_data=f'mode_pending_{chat_id}')],
        [InlineKeyboardButton(f"{'★ ' if mode == 'recent' else ''}Recent Mode", callback_data=f'mode_recent_{chat_id}')],
        [InlineKeyboardButton("Magic Wand", callback_data=f'wand_{chat_id}'), InlineKeyboardButton("Chaos Mode", callback_data=f'chaos_{chat_id}')],
        [InlineKeyboardButton("Stop", callback_data=f'stop_{chat_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    dashboard_msg = (
        f"🌌 **Cosmic Dashboard for {chat_id}**\n"
        f"✨ Mode: {mode}\n"
        f"⏳ Delay: {data['delay']}s\n"
        f"🔍 Pending Souls: {pending_count}\n"
        f"🌠 Choose your destiny below!"
    )
    if message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=dashboard_msg,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            logger.debug(f"Updated dashboard for chat {chat_id}, message_id: {message_id}")
        except telegram.error.TelegramError as e:
            logger.error(f"Failed to update dashboard for {chat_id}: {e}")
    else:
        msg = await context.bot.send_message(
            chat_id=user_id,
            text=dashboard_msg,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        dashboard_msg_ids[chat_id] = msg.message_id
        logger.debug(f"Sent new dashboard for chat {chat_id}, message_id: {msg.message_id}")

async def mode_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Handle mode selection."""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Mode callback from user {query.from_user.id}: {query.data}")
    try:
        mode, chat_id = query.data.split('_')[1], int(query.data.split('_')[2])
        data['mode'] = mode
        save_data(data)
        await update_dashboard(context, chat_id, query.from_user.id, dashboard_msg_ids.get(chat_id))
        logger.info(f"User {query.from_user.id} set mode to {mode} for chat {chat_id}")
        if mode == 'pending':
            await check_pending_requests(context, chat_id, query.from_user.id)
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing mode callback {query.data}: {e}")
        await query.edit_message_text("💥 Spell misfired! Try again.")

async def wand_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Toggle mode with a magic wand."""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Wand callback from user {query.from_user.id}: {query.data}")
    try:
        chat_id = int(query.data.split('_')[1])
        data['mode'] = 'recent' if data['mode'] == 'pending' else 'pending'
        save_data(data)
        await update_dashboard(context, chat_id, query.from_user.id, dashboard_msg_ids.get(chat_id))
        logger.info(f"User {query.from_user.id} toggled mode to {data['mode']} for chat {chat_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing wand callback {query.data}: {e}")
        await query.edit_message_text("💥 Wand malfunction! Try again.")

async def chaos_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Randomly toggle modes for chaos!"""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Chaos callback from user {query.from_user.id}: {query.data}")
    try:
        chat_id = int(query.data.split('_')[1])
        data['mode'] = random.choice(['pending', 'recent'])
        save_data(data)
        await update_dashboard(context, chat_id, query.from_user.id, dashboard_msg_ids.get(chat_id))
        await query.message.reply_text(f"🌪 Chaos unleashed! Mode warped to {data['mode']} for {chat_id}!")
        logger.info(f"User {query.from_user.id} triggered chaos mode: {data['mode']} for chat {chat_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing chaos callback {query.data}: {e}")
        await query.edit_message_text("💥 Chaos misfired! Try again.")

async def stop_callback(update: telegram.Update, context: CallbackContext) -> None:
    """Stop request processing."""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Stop callback from user {query.from_user.id}: {query.data}")
    try:
        chat_id = int(query.data.split('_')[1])
        stop_processing[chat_id] = True
        await update_dashboard(context, chat_id, query.from_user.id, dashboard_msg_ids.get(chat_id))
        logger.info(f"User {query.from_user.id} stopped processing for chat {chat_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing stop callback {query.data}: {e}")
        await query.edit_message_text("💥 Stop failed! Try again.")

async def handle_forwarded_message(update: telegram.Update, context: CallbackContext) -> None:
    """Handle forwarded message for chat connection."""
    user_id = update.message.from_user.id
    forward_origin = update.message.forward_origin

    if not forward_origin:
        await update.message.reply_text("🔍 No magic here! Forward a message!")
        logger.warning(f"User {user_id} sent non-forwarded message")
        return

    forwarded_msg_id = forward_origin.message_id
    chat_id = forward_origin.chat.id if forward_origin.chat else None

    logger.info(f"User {user_id} forwarded message ID {forwarded_msg_id} from chat {chat_id}")

    if forwarded_msg_id == data['last_msg_id']:
        if not data['chats']:
            await update.message.reply_text("🌑 Summon a chat first!")
            logger.warning(f"User {user_id} tried to connect with no chats")
            return
        chat_id = data['chats'][-1]
    if chat_id:
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if bot_member.status not in ['administrator']:
                await update.message.reply_text("⛔ I need admin powers!")
                logger.warning(f"Bot not admin in chat {chat_id}")
                return
            if chat_id not in data['chats']:
                data['chats'].append(chat_id)
                save_data(data)
            await update_dashboard(context, chat_id, user_id)
            logger.info(f"User {user_id} connected chat {chat_id}")
        except telegram.error.TelegramError as e:
            logger.error(f"Error connecting chat {chat_id}: {e}")
            await update.message.reply_text("💥 Connection failed! Ensure I’m an admin!")
    else:
        await update.message.reply_text("❌ Invalid scroll! Forward my /start or a chat message!")
        logger.warning(f"User {user_id} forwarded invalid message ID {forwarded_msg_id} or chat {chat_id}")

async def setmode(update: telegram.Update, context: CallbackContext) -> None:
    """Set bot mode manually."""
    user_id = update.message.from_user.id
    if not data['chats']:
        await update.message.reply_text("🌑 Bind a chat first!")
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
        await update.message.reply_text("🌑 Bind a chat first!")
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
    """Show bot status."""
    user_id = update.message.from_user.id
    if not data['chats']:
        await update.message.reply_text("🌑 No realms bound yet!")
        logger.warning(f"User {user_id} checked status with no chats")
        return
    
    chats = "\n".join([f"- {chat} ({pending_counts.get(chat, 0)} souls)" for chat in data['chats']]) or "None"
    msg = f"🌌 Cosmic Status:\nMode: {data['mode'] or 'Unchosen'}\n⏳ Delay: {data['delay']}s\n✨ Realms:\n{chats}"
    await update.message.reply_text(msg)
    logger.info(f"User {user_id} checked status: {msg}")

async def accept_join_request(update: telegram.Update, context: CallbackContext) -> None:
    """Handle recent join requests."""
    if data['mode'] != 'recent' or not data['chats']:
        logger.debug(f"Recent mode not active or no chats: mode={data['mode']}, chats={data['chats']}")
        return
    
    join_request = update.chat_join_request
    chat_id = join_request.chat.id
    user_id = join_request.from_user.id
    
    stop_processing[chat_id] = False
    keyboard = [[InlineKeyboardButton("Stop", callback_data=f'stop_{chat_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    status_msg = await context.bot.send_message(chat_id=user_id, text=f"🌟 Opening gates to {chat_id}...", reply_markup=reply_markup)
    await asyncio.sleep(data['delay'])
    if stop_processing.get(chat_id, False):
        await status_msg.edit_text("🛑 Gates sealed!")
        stop_processing[chat_id] = False
        logger.info(f"Approval stopped for user {user_id} in chat {chat_id}")
        return
    
    try:
        await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        await status_msg.edit_text(f"✨ {user_id}, welcome to {chat_id}!")
        logger.info(f"Accepted join request from {user_id} in {chat_id}")
    except telegram.error.TelegramError as e:
        await status_msg.edit_text("💥 Gates resisted!")
        logger.error(f"Error accepting join request in {chat_id}: {e}")

async def handle_chat_member(update: telegram.Update, context: CallbackContext) -> None:
    """Detect when bot is added to a chat."""
    chat_member = update.my_chat_member
    if chat_member.new_chat_member.user.id == context.bot.id and chat_member.new_chat_member.status in ['administrator', 'member']:
        chat_id = chat_member.chat.id
        if chat_id not in data['chats']:
            data['chats'].append(chat_id)
            save_data(data)
            logger.info(f"Bot added to chat {chat_id}")

async def check_pending_requests(context: CallbackContext, chat_id: int, admin_chat_id: int) -> None:
    """Process pending requests."""
    if data['mode'] != 'pending' or chat_id not in data['chats']:
        logger.debug(f"Pending mode not active or chat not bound: mode={data['mode']}, chat={chat_id}")
        return
    
    pending_count = pending_counts.get(chat_id, 0)
    logger.info(f"🔍 Detected {pending_count} pending requests in {chat_id} (simulated)")
    
    if pending_count == 0:
        await context.bot.send_message(chat_id=admin_chat_id, text=f"🌑 No souls await in {chat_id}!")
        return
    
    stop_processing[chat_id] = False
    keyboard = [[InlineKeyboardButton("Stop", callback_data=f'stop_{chat_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    status_msg = await context.bot.send_message(chat_id=admin_chat_id, text=f"🌠 Unveiling {pending_count} souls in {chat_id}...", reply_markup=reply_markup)
    approved = 0
    for i in range(pending_count):
        if stop_processing.get(chat_id, False):
            await status_msg.edit_text(f"🛑 Paused at {approved}/{pending_count} souls!")
            stop_processing[chat_id] = False
            return
        await asyncio.sleep(0.5)
        approved += 1
        await status_msg.edit_text(f"🌠 Unveiling souls in {chat_id}: {approved}/{pending_count}")
        logger.info(f"Approved pending request {approved}/{pending_count} in {chat_id}")
    
    await status_msg.edit_text(f"✨ All {approved} souls unveiled in {chat_id}!")

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
    application.add_handler(telegram.ext.CallbackQueryHandler(chaos_callback, pattern=r'chaos_\d+'))
    application.add_handler(telegram.ext.CallbackQueryHandler(stop_callback, pattern=r'stop_\d+'))

    # Error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("✨ The cosmic realm awakens...")
    application.run_polling()

if __name__ == '__main__':
    if 1938030055 not in data['admins']:
        data['admins'].append(1938030055)
        save_data(data)
    main()
