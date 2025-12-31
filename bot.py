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

# --- LOGGING SETUP (Taki error dikhe agar aaye to) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- BOT CONFIGURATION ---
pr0fess0r_99 = Client(
    "Auto Approved Bot",
    bot_token=environ["BOT_TOKEN"],
    api_id=int(environ["API_ID"]),
    api_hash=environ["API_HASH"]
)

# --- DATABASE CONNECTION ---
mongo_url = environ["MONGO_URL"]
db_client = AsyncIOMotorClient(mongo_url)
db = db_client.AutoApproveBot
users_db = db.users
settings_db = db.settings
channels_db = db.channels
posts_db = db.posts

# --- VARIABLES ---
ADMINS = [int(admin) for admin in environ.get("ADMINS", "").split()]
TEXT = environ.get("APPROVED_WELCOME_TEXT", "Hello {mention}\nWelcome To {title}!")
UPDATE_CH = environ.get("UPDATE_CH", "https://t.me/Mo_Tech_YT")
WELCOME_PIC = environ.get("WELCOME_PIC", "")
MASTER_CHANNEL_ID = int(environ.get("MASTER_CHANNEL_ID", "0"))

scheduler = AsyncIOScheduler()

# ==========================================
#  ⬇️ CORE LOGIC: INSTAGRAM DOWNLOADER ⬇️
# ==========================================

def download_insta_sync(url, unique_id):
    """
    Ye function background mein chalega taki bot ruke nahi.
    Unique ID ka use karega taki files mix na ho.
    """
    filename = f"reels_{unique_id}.mp4"
    ydl_opts = {
        'format': 'best',
        'outtmpl': filename,
        'quiet': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            description = info.get('description', '')
            
            # Hashtags nikalna (safely)
            hashtags = re.findall(r"#\w+", description) if description else []
            hashtag_str = " ".join(hashtags)
            
            return filename, hashtag_str
    except Exception as e:
        logger.error(f"DL Error: {e}")
        return None, None

@pr0fess0r_99.on_message(filters.regex(r"https?://.*instagram[^\s]+") & filters.private)
async def insta_handler(client, message):
    # 1. Processing Message
    status = await message.reply_text("🔎 **Link check kar raha hoon...**", quote=True)
    
    try:
        # Unique ID generation (Time + UserID)
        uid = f"{message.from_user.id}_{int(time.time())}"
        
        await status.edit("📥 **Downloading Video...**\n(Please wait...)")
        
        # 2. Download in Background (Non-Blocking)
        loop = asyncio.get_event_loop()
        video_path, tags = await loop.run_in_executor(None, download_insta_sync, message.text, uid)
        
        if not video_path or not os.path.exists(video_path):
            await status.edit("❌ **Error:** Video download nahi ho payi. Link private ho sakta hai.")
            return

        # 3. Uploading
        await status.edit("📤 **Uploading to Telegram...**")
        
        caption_text = f"✅ **Downloaded Successfully**\n\n**Tags:**\n`{tags}`\n\nby {client.me.mention}"
        
        await message.reply_video(
            video=video_path,
            caption=caption_text,
            quote=True
        )
        await status.delete()
        
    except Exception as e:
        logger.error(f"Handler Error: {e}")
        await status.edit("❌ **Error:** Kuch technical issue hai.")
        
    finally:
        # 4. Cleanup (File Delete karna zaruri hai)
        if video_path and os.path.exists(video_path):
            os.remove(video_path)

# ==========================================
#  ⬇️ CORE LOGIC: AUTO ACCEPT & POSTS ⬇️
# ==========================================

@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    """Ye hai apka Main Auto-Accept Feature"""
    try:
        # Request Accept
        await client.approve_chat_join_request(message.chat.id, message.from_user.id)
        
        # Database Update
        await channels_db.update_one({"chat_id": message.chat.id}, {"$set": {"chat_id": message.chat.id}}, upsert=True)
        await add_user(message.from_user.id)
        
        # Welcome Message Send
        await send_msg_with_media(client, message.from_user.id, message.from_user.mention, message.chat.title)
    except Exception as e:
        logger.error(f"AutoApprove Error: {e}")

# --- HELPERS (User & Buttons) ---
async def add_user(user_id):
    if not await users_db.find_one({"user_id": user_id}):
        await users_db.insert_one({"user_id": user_id})

async def get_buttons():
    btns = await settings_db.find_one({"id": "start_buttons"})
    if not btns:
        return [
            {"n1": "🎥 Updates Channel", "u1": UPDATE_CH},
            {"n2": "🎬 Support Group", "u2": UPDATE_CH, "n3": "More Bots", "u3": UPDATE_CH}
        ]
    return btns["data"]

async def send_msg_with_media(client, chat_id, mention, title):
    caption_text = TEXT.format(mention=mention, title=title)
    btns_data = await get_buttons()
    
    # URL Checker (Safety)
    def check(url): return url if url and url.startswith("http") else "https://t.me/telegram"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btns_data[0]['n1'], url=check(btns_data[0]['u1']))],
        [InlineKeyboardButton(btns_data[1]['n2'], url=check(btns_data[1]['u2'])),
         InlineKeyboardButton(btns_data[1]['n3'], url=check(btns_data[1]['u3']))],
        [InlineKeyboardButton("Add Me to Group ➕", url=f"http://t.me/{client.me.username}?startgroup=botstart")]
    ])
    try:
        if WELCOME_PIC: 
            await client.send_photo(chat_id, photo=WELCOME_PIC, caption=caption_text, reply_markup=keyboard)
        else: 
            await client.send_message(chat_id, text=caption_text, reply_markup=keyboard)
    except: pass

# --- AUTO POST JOB ---
async def auto_post_job():
    all_ch = await channels_db.find().to_list(length=None)
    all_pst = await posts_db.find().to_list(length=None)
    if not all_ch or not all_pst: return
    
    data = await settings_db.find_one({"id": "post_index"})
    idx = data["index"] if data else 0

    for _ in range(15):
        if idx >= len(all_pst): idx = 0
        p = all_pst[idx]
        for c in all_ch:
            try:
                await pr0fess0r_99.copy_message(chat_id=c["chat_id"], from_chat_id=MASTER_CHANNEL_ID, message_id=p["msg_id"])
                await asyncio.sleep(1)
            except: pass
        idx += 1
    await settings_db.update_one({"id": "post_index"}, {"$set": {"index": idx}}, upsert=True)

# --- COMMANDS ---
@pr0fess0r_99.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await add_user(message.from_user.id)
    await message.reply_text(
        f"Hi {message.from_user.mention}!\n\n"
        "✅ **Auto-Accept:** Active\n"
        "📥 **Insta Downloader:** Link bhejo, video paao!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Updates Channel", url=UPDATE_CH)]])
    )

@pr0fess0r_99.on_message(filters.command("status") & filters.user(ADMINS))
async def stats(client, message):
    u = await users_db.count_documents({})
    c = await channels_db.count_documents({})
    await message.reply_text(f"📊 **Stats:**\nUsers: `{u}`\nChannels: `{c}`")

@pr0fess0r_99.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def bcast(client, message):
    m = await message.reply_text("Broadcasting...")
    c = 0
    async for user in users_db.find({}):
        try:
            await message.reply_to_message.copy(user["user_id"])
            c += 1
            await asyncio.sleep(0.1)
        except: pass
    await m.edit(f"✅ Sent to {c} users.")

@pr0fess0r_99.on_message(filters.chat(MASTER_CHANNEL_ID))
async def save_pst(client, message):
    if not await posts_db.find_one({"msg_id": message.id}):
        await posts_db.insert_one({"msg_id": message.id})

@pr0fess0r_99.on_message(filters.command("settime") & filters.user(ADMINS))
async def set_t(client, message):
    args = message.text.split()
    if len(args) < 2: return await message.reply_text("Use: /settime 14:00 22:00")
    scheduler.remove_all_jobs()
    for t in args[1:]:
        try:
            h, m = t.split(':')
            scheduler.add_job(auto_post_job, "cron", hour=int(h), minute=int(m))
        except: continue
    await settings_db.update_one({"id": "sch_t"}, {"$set": {"times": args[1:]}}, upsert=True)
    await message.reply_text(f"✅ Times Set: {args[1:]}")

# --- STARTUP ---
async def start_bot():
    print("🔄 Bot Starting...")
    await pr0fess0r_99.start()
    
    # Restore Schedule
    saved = await settings_db.find_one({"id": "sch_t"})
    if saved:
        for t in saved['times']:
            try:
                h, m = t.split(':')
                scheduler.add_job(auto_post_job, "cron", hour=int(h), minute=int(m))
            except: pass
    scheduler.start()
    
    await pr0fess0r_99.set_bot_commands([
        BotCommand("start", "Start Bot"),
        BotCommand("status", "Check Stats")
    ])
    print("🔥 BOT ONLINE: Auto-Accept + Insta DL Ready!")
    await idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
