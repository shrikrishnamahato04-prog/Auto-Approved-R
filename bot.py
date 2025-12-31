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
posts_db = db.posts 

# --- CONFIG ---
ADMINS = [int(admin) for admin in environ.get("ADMINS", "").split()]
TEXT = environ.get("APPROVED_WELCOME_TEXT", "Hello {mention}\nWelcome To {title}!")
DEF_UPDATE_CH = environ.get("UPDATE_CH", "https://t.me/Mo_Tech_YT") 
WELCOME_PIC = environ.get("WELCOME_PIC", "")
MASTER_CHANNEL_ID = int(environ.get("MASTER_CHANNEL_ID", "0"))

scheduler = AsyncIOScheduler()

async def get_update_ch():
    data = await settings_db.find_one({"id": "update_link"})
    return data["link"] if data else DEF_UPDATE_CH

# --- HIGH QUALITY DOWNLOADER WITH HASHTAG FIX ---
def download_insta_hd(url, unique_id):
    filename = f"hd_video_{unique_id}.mp4"
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best', # Force Highest Quality
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'nocheckcertificate': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Hashtags Extraction
            description = info.get('description') or info.get('title') or ""
            hashtags = re.findall(r"#\w+", description)
            unique_tags = " ".join(list(set(hashtags))) if hashtags else "No Hashtags"
            return filename, unique_tags
    except Exception as e:
        logger.error(f"Download Error: {e}")
        return None, None

# --- HANDLERS ---

@pr0fess0r_99.on_message(filters.regex(r"https?://.*instagram[^\s]+") & filters.private)
async def insta_hd_handler(client, message):
    status = await message.reply_text("🚀 **Processing HD Download...**", quote=True)
    uid = f"{message.from_user.id}_{int(time.time())}"
    
    file, tags = await asyncio.get_event_loop().run_in_executor(None, download_insta_hd, message.text, uid)
    
    if file and os.path.exists(file):
        await status.edit("📤 **Uploading High Quality Video...**")
        await message.reply_video(
            video=file,
            caption=f"✅ **HD Quality Downloaded**\n\n**Hashtags:**\n`{tags}`",
            quote=True
        )
        os.remove(file)
        await status.delete()
    else:
        await status.edit("❌ **Error:** Instagram ne block kiya ya link private hai. Thodi der baad try karein.")

# (Baaki ka Start, Auto-Accept aur Menu code waisa hi rahega jaisa pehle tha)
@pr0fess0r_99.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await add_user(message.from_user.id)
    up_link = await get_update_ch()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 Bot Updates Channel 🎥", url=up_link)],
        [InlineKeyboardButton("🎬 Latest Releases 🎬", url=up_link),
         InlineKeyboardButton("Channel Manager 🎥", url=up_link)]
    ])
    await message.reply_text(f"Hi {message.from_user.mention}!\nWelcome back.", reply_markup=keyboard)

@pr0fess0r_99.on_message(filters.command("setupdate") & filters.user(ADMINS))
async def set_update(client, message):
    if len(message.command) < 2: return
    new_link = message.command[1]
    await settings_db.update_one({"id": "update_link"}, {"$set": {"link": new_link}}, upsert=True)
    await message.reply_text(f"✅ Link Updated: {new_link}")

@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    try:
        await client.approve_chat_join_request(message.chat.id, message.from_user.id)
        await add_user(message.from_user.id)
    except: pass

async def add_user(user_id):
    if not await users_db.find_one({"user_id": user_id}): await users_db.insert_one({"user_id": user_id})

async def start_bot():
    await pr0fess0r_99.start()
    await pr0fess0r_99.set_bot_commands([
        BotCommand("start", "Start Bot"),
        BotCommand("status", "Check Stats"),
        BotCommand("setupdate", "Change Update Link"),
        BotCommand("broadcast", "Send to Users")
    ])
    print("🔥 FIXED HD BOT READY!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_bot())
