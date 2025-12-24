from os import environ
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ChatJoinRequest, BotCommand, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
UPDATE_CH = environ.get("UPDATE_CH", "https://t.me/Mo_Tech_YT") 
WELCOME_PIC = environ.get("WELCOME_PIC", "")
MASTER_CHANNEL_ID = int(environ.get("MASTER_CHANNEL_ID", "0"))

scheduler = AsyncIOScheduler()

# --- HELPERS (Database & Buttons) ---
async def add_user(user_id):
    if not await users_db.find_one({"user_id": user_id}):
        await users_db.insert_one({"user_id": user_id})

async def get_buttons():
    btns = await settings_db.find_one({"id": "start_buttons"})
    if not btns:
        return [
            {"n1": "🎥 Bot Updates Channel 🎥", "u1": UPDATE_CH},
            {"n2": "🎬 Latest Releases 🎬", "u2": "https://t.me/Mo_Tech_YT", "n3": "Channel Manager 🎥", "u3": "https://t.me/Mo_Tech_YT"}
        ]
    return btns["data"]

# --- WELCOME MESSAGE WITH MEDIA (Exactly as before) ---
async def send_msg_with_media(client, chat_id, mention, title):
    caption_text = TEXT.format(mention=mention, title=title)
    btns_data = await get_buttons()
    def check_url(url):
        return url if (url and url.startswith("http")) else "https://t.me/telegram"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btns_data[0]['n1'], url=check_url(btns_data[0]['u1']))],
        [InlineKeyboardButton(btns_data[1]['n2'], url=check_url(btns_data[1]['u2'])),
         InlineKeyboardButton(btns_data[1]['n3'], url=check_url(btns_data[1]['u3']))],
        [InlineKeyboardButton("Add to Group ➕", url=f"http://t.me/{client.me.username}?startgroup=botstart")],
        [InlineKeyboardButton("Close ❌", callback_data="close_msg")]
    ])
    try:
        if WELCOME_PIC: await client.send_photo(chat_id, photo=WELCOME_PIC, caption=caption_text, reply_markup=keyboard)
        else: await client.send_message(chat_id, text=caption_text, reply_markup=keyboard)
    except: pass

# --- AUTO-POST ENGINE ---
async def auto_post_job():
    all_ch = await channels_db.find().to_list(length=None)
    all_pst = await posts_db.find().to_list(length=None)
    if not all_ch or not all_pst: return
    
    data = await settings_db.find_one({"id": "post_index"})
    idx = data["index"] if data else 0

    for _ in range(15): # Ek bar mein 15 post uthayega
        if idx >= len(all_pst): idx = 0
        p = all_pst[idx]
        for c in all_ch:
            try:
                await pr0fess0r_99.copy_message(chat_id=c["chat_id"], from_chat_id=MASTER_CHANNEL_ID, message_id=p["msg_id"])
                await asyncio.sleep(1)
            except: pass
        idx += 1
    await settings_db.update_one({"id": "post_index"}, {"$set": {"index": idx}}, upsert=True)

# --- COMMANDS & HANDLERS ---

@pr0fess0r_99.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await add_user(message.from_user.id)
    btns_data = await get_buttons()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btns_data[0]['n1'], url=btns_data[0]['u1'])],
        [InlineKeyboardButton(btns_data[1]['n2'], url=btns_data[1]['u2']),
         InlineKeyboardButton(btns_data[1]['n3'], url=btns_data[1]['u3'])]
    ])
    await message.reply_text(f"Hi {message.from_user.mention}!\n\nMain aapki join requests auto-accept karta hoon aur aapke movies channel ko manage karta hoon.", reply_markup=keyboard)

@pr0fess0r_99.on_message(filters.command("status") & filters.user(ADMINS))
async def stats(client, message):
    u = await users_db.count_documents({})
    c = await channels_db.count_documents({})
    p = await posts_db.count_documents({})
    await message.reply_text(f"📊 Status:\n- Users: {u}\n- Target Channels: {c}\n- Master Posts: {p}")

@pr0fess0r_99.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def bcast(client, message):
    m = await message.reply_text("Broadcasting...")
    count = 0
    async for user in users_db.find({}):
        try:
            await message.reply_to_message.copy(user["user_id"])
            count += 1
            await asyncio.sleep(0.1)
        except: pass
    await m.edit(f"✅ Sent to {count} users.")

@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    try:
        await client.approve_chat_join_request(message.chat.id, message.from_user.id)
        await channels_db.update_one({"chat_id": message.chat.id}, {"$set": {"chat_id": message.chat.id}}, upsert=True)
        await add_user(message.from_user.id)
        await send_msg_with_media(client, message.from_user.id, message.from_user.mention, message.chat.title)
    except: pass

@pr0fess0r_99.on_message(filters.chat(MASTER_CHANNEL_ID))
async def save_pst(client, message):
    if not await posts_db.find_one({"msg_id": message.id}):
        await posts_db.insert_one({"msg_id": message.id})

@pr0fess0r_99.on_message(filters.command("settime") & filters.user(ADMINS))
async def set_t(client, message):
    args = message.text.split()
    if len(args) < 2: return await message.reply_text("Usage: `/settime 14:00 22:00`")
    scheduler.remove_all_jobs()
    for t in args[1:]:
        try:
            h, m = t.split(':')
            scheduler.add_job(auto_post_job, "cron", hour=int(h), minute=int(m))
        except: continue
    await settings_db.update_one({"id": "sch_t"}, {"$set": {"times": args[1:]}}, upsert=True)
    await message.reply_text(f"✅ Time Set: {', '.join(args[1:])}")

@pr0fess0r_99.on_callback_query(filters.regex("close_msg"))
async def close(client, query): await query.message.delete()

# --- STARTUP ---
async def start_bot():
    await pr0fess0r_99.start()
    saved = await settings_db.find_one({"id": "sch_t"})
    if saved:
        for t in saved['times']:
            h, m = t.split(':')
            scheduler.add_job(auto_post_job, "cron", hour=int(h), minute=int(m))
    scheduler.start()
    await pr0fess0r_99.set_bot_commands([
        BotCommand("start", "Start Bot"),
        BotCommand("status", "Check Stats"),
        BotCommand("settime", "Set Timings"),
        BotCommand("broadcast", "Send to Users")
    ])
    print("🔥 ALL FEATURES ACTIVE!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_bot())
