import asyncio
import os
import re
import time
import logging
from os import environ
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest, BotCommand, Message
from motor.motor_asyncio import AsyncIOMotorClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import yt_dlp

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- BOT SETUP ---
pr0fess0r_99 = Client(
    "Auto Approved Bot",
    bot_token = environ["BOT_TOKEN"],
    api_id = int(environ["API_ID"]),
    api_hash = environ["API_HASH"]
)

# --- DATABASE (MongoDB) ---
mongo_url = environ["MONGO_URL"]
db_client = AsyncIOMotorClient(mongo_url)
db = db_client.AutoApproveBot
users_db = db.users
settings_db = db.settings
channels_db = db.channels
posts_db = db.posts 

# --- CONFIG VARS ---
ADMINS = [int(admin) for admin in environ.get("ADMINS", "").split()]
TEXT = environ.get("APPROVED_WELCOME_TEXT", "Hello {mention}\nWelcome To {title}!")
DEF_UPDATE_CH = environ.get("UPDATE_CH", "https://t.me/Mo_Tech_YT") 
WELCOME_PIC = environ.get("WELCOME_PIC", "")
MASTER_CHANNEL_ID = int(environ.get("MASTER_CHANNEL_ID", "0"))

scheduler = AsyncIOScheduler()

# --- DYNAMIC UPDATE LINK HELPER ---
async def get_update_ch():
    data = await settings_db.find_one({"id": "update_link"})
    return data["link"] if data else DEF_UPDATE_CH

# --- PRO HASHTAG & VIDEO DOWNLOADER ---
def download_insta_reel(url, unique_id):
    filename = f"video_{unique_id}.mp4"
    ydl_opts = {
        'format': 'best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Deep Scan for Hashtags in description and title
            full_text = f"{info.get('description', '')} {info.get('title', '')}"
            hashtags = re.findall(r"#\w+", full_text)
            unique_tags = list(set(hashtags))
            return filename, " ".join(unique_tags) if unique_tags else "No Hashtags Found"
    except Exception as e:
        logger.error(f"DL Error: {e}")
        return None, None

# --- DYNAMIC BUTTONS (Original Look) ---
async def get_buttons():
    up_link = await get_update_ch()
    return [
        {"n1": "🎥 Bot Updates Channel 🎥", "u1": up_link},
        {"n2": "🎬 Latest Releases 🎬", "u2": up_link, "n3": "Channel Manager 🎥", "u3": up_link}
    ]

# --- WELCOME MESSAGE ---
async def send_msg_with_media(client, chat_id, mention, title):
    caption_text = TEXT.format(mention=mention, title=title)
    btns_data = await get_buttons()
    up_link = await get_update_ch()
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btns_data[0]['n1'], url=up_link)],
        [InlineKeyboardButton(btns_data[1]['n2'], url=up_link),
         InlineKeyboardButton(btns_data[1]['n3'], url=up_link)],
        [InlineKeyboardButton("Add to Group ➕", url=f"http://t.me/{client.me.username}?startgroup=botstart")],
        [InlineKeyboardButton("Close ❌", callback_data="close_msg")]
    ])
    try:
        if WELCOME_PIC: await client.send_photo(chat_id, photo=WELCOME_PIC, caption=caption_text, reply_markup=keyboard)
        else: await client.send_message(chat_id, text=caption_text, reply_markup=keyboard)
    except: pass

# --- HANDLERS ---

@pr0fess0r_99.on_message(filters.regex(r"https?://.*instagram[^\s]+") & filters.private)
async def handle_insta(client, message):
    m = await message.reply_text("📥 **Fetching Reel + Hashtags...**", quote=True)
    uid = f"{message.from_user.id}_{int(time.time())}"
    file, tags = await asyncio.get_event_loop().run_in_executor(None, download_insta_reel, message.text, uid)
    if file:
        await message.reply_video(video=file, caption=f"✅ **Downloaded Successfully**\n\n**Hashtags:**\n`{tags}`", quote=True)
        os.remove(file)
        await m.delete()
    else: await m.edit("❌ Failed to download. Link private ho sakta hai.")

@pr0fess0r_99.on_message(filters.command("setupdate") & filters.user(ADMINS))
async def set_update_link(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/setupdate https://t.me/YourChannel`")
    new_link = message.command[1]
    await settings_db.update_one({"id": "update_link"}, {"$set": {"link": new_link}}, upsert=True)
    await message.reply_text(f"✅ **Update Channel Link Changed!**\nNaya Link: {new_link}")

@pr0fess0r_99.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await add_user(message.from_user.id)
    up_link = await get_update_ch()
    btns_data = await get_buttons()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btns_data[0]['n1'], url=up_link)],
        [InlineKeyboardButton(btns_data[1]['n2'], url=up_link),
         InlineKeyboardButton(btns_data[1]['n3'], url=up_link)]
    ])
    await message.reply_text(f"Hi {message.from_user.mention}!\n\nMain aapki join requests auto-accept karta hoon aur Reels download karta hoon!", reply_markup=keyboard)

@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    try:
        await client.approve_chat_join_request(message.chat.id, message.from_user.id)
        await channels_db.update_one({"chat_id": message.chat.id}, {"$set": {"chat_id": message.chat.id}}, upsert=True)
        await add_user(message.from_user.id)
        await send_msg_with_media(client, message.from_user.id, message.from_user.mention, message.chat.title)
    except: pass

@pr0fess0r_99.on_message(filters.command("status") & filters.user(ADMINS))
async def stats(client, message):
    u = await users_db.count_documents({}); c = await channels_db.count_documents({})
    await message.reply_text(f"📊 Status:\n- Users: {u}\n- Channels: {c}")

@pr0fess0r_99.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def bcast(client, message):
    m = await message.reply_text("Broadcasting..."); count = 0
    async for user in users_db.find({}):
        try: await message.reply_to_message.copy(user["user_id"]); count += 1; await asyncio.sleep(0.1)
        except: pass
    await m.edit(f"✅ Sent to {count} users.")

async def add_user(user_id):
    if not await users_db.find_one({"user_id": user_id}): await users_db.insert_one({"user_id": user_id})

@pr0fess0r_99.on_callback_query(filters.regex("close_msg"))
async def close(client, query): await query.message.delete()

# --- STARTUP ---
async def start_bot():
    await pr0fess0r_99.start()
    scheduler.start()
    # Restore Original Menu Buttons with setupdate
    await pr0fess0r_99.set_bot_commands([
        BotCommand("start", "Start Bot"),
        BotCommand("status", "Check Stats"),
        BotCommand("setupdate", "Change Update Link"),
        BotCommand("broadcast", "Send to Users")
    ])
    print("🔥 CORE PROFESSIONAL BOT READY!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_bot())
