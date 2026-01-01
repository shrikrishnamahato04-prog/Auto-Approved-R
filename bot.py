import asyncio
import os
import re
import time
import logging
from os import environ
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest, BotCommand
from motor.motor_asyncio import AsyncIOMotorClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import yt_dlp

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- BOT SETUP ---
pr0fess0r_99 = Client(
    "Auto Approved Bot",
    bot_token = environ["BOT_TOKEN"],
    api_id = int(environ["API_ID"]),
    api_hash = environ["API_HASH"]
)

# --- DATABASE ---
mongo_url = environ["MONGO_URL"]
db_client = AsyncIOMotorClient(mongo_url)
db = db_client.AutoApproveBot
users_db = db.users
settings_db = db.settings
channels_db = db.channels

# --- CONFIG ---
ADMINS = [int(admin) for admin in environ.get("ADMINS", "").split()]
TEXT = environ.get("APPROVED_WELCOME_TEXT", "Hello {mention}\nWelcome To {title}!")
DEF_UPDATE_CH = environ.get("UPDATE_CH", "https://t.me/Mo_Tech_YT") 
WELCOME_PIC = environ.get("WELCOME_PIC", "")

# --- DOWNLOADER (HD + PRIVATE + HASHTAGS) ---
def download_insta_pro(url, unique_id):
    filename = f"video_{unique_id}.mp4"
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best', # Highest Quality
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt', # Private video ke liye zaruri hai
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            desc = info.get('description') or info.get('title') or ""
            tags = re.findall(r"#\w+", desc)
            unique_tags = " ".join(list(set(tags))) if tags else "No Hashtags"
            return filename, unique_tags
    except Exception as e:
        logger.error(f"Error: {e}")
        return None, None

# --- HANDLERS ---

@pr0fess0r_99.on_message(filters.regex(r"https?://.*instagram[^\s]+") & filters.private)
async def handle_insta(client, message):
    m = await message.reply_text("🔎 **Fetching HD Video & Tags...**", quote=True)
    uid = f"{message.from_user.id}_{int(time.time())}"
    
    file, hashtags = await asyncio.get_event_loop().run_in_executor(None, download_insta_pro, message.text, uid)
    
    if file and os.path.exists(file):
        await m.edit("📤 **Uploading High Quality...**")
        await message.reply_video(
            video=file,
            caption=f"✅ **Downloaded Successfully**\n\n**Hashtags:**\n`{hashtags}`",
            quote=True
        )
        os.remove(file)
        await m.delete()
    else:
        await m.edit("❌ **Error:** Instagram block ya link private hai. Cookies check karein.")

@pr0fess0r_99.on_message(filters.command("start") & filters.private)
async def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 Bot Updates Channel 🎥", url=DEF_UPDATE_CH)],
        [InlineKeyboardButton("🎬 Latest Releases 🎬", url=DEF_UPDATE_CH),
         InlineKeyboardButton("Channel Manager 🎥", url=DEF_UPDATE_CH)]
    ])
    await message.reply_text(f"Hi {message.from_user.mention}!\nAuto-Accept aur HD Downloader ready hai.", reply_markup=keyboard)

@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    try:
        await client.approve_chat_join_request(message.chat.id, message.from_user.id)
    except: pass

# --- STARTUP ---
async def start_bot():
    await pr0fess0r_99.start()
    await pr0fess0r_99.set_bot_commands([
        BotCommand("start", "Start Bot"),
        BotCommand("status", "Check Stats"),
        BotCommand("setupdate", "Change Update Link"),
        BotCommand("broadcast", "Send to Users")
    ])
    print("🔥 PROFESSIONAL BOT READY!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_bot())
