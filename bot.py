from os import environ
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ChatJoinRequest
from motor.motor_asyncio import AsyncIOMotorClient

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

# --- CONFIG VARS ---
ADMINS = [int(admin) for admin in environ.get("ADMINS", "").split()]
TEXT = environ.get("APPROVED_WELCOME_TEXT", "Hello {mention}\nWelcome To {title}!")
UPDATE_CH = environ.get("UPDATE_CH", "https://t.me/Mo_Tech_YT") 
WELCOME_PIC = environ.get("WELCOME_PIC", "") 

async def add_user(user_id):
    if not await users_db.find_one({"user_id": user_id}):
        await users_db.insert_one({"user_id": user_id})

# --- SMART MEDIA SEND FUNCTION ---
async def send_msg_with_media(client, chat_id, mention, title, reply_markup=None):
    caption_text = TEXT.format(mention=mention, title=title)
    try:
        if WELCOME_PIC:
            # Agar GIF hai
            if WELCOME_PIC.endswith((".gif", ".mp4")):
                await client.send_video(chat_id, video=WELCOME_PIC, caption=caption_text, reply_markup=reply_markup)
            # Agar Image (PNG/JPG) hai
            else:
                await client.send_photo(chat_id, photo=WELCOME_PIC, caption=caption_text, reply_markup=reply_markup)
        else:
            await client.send_message(chat_id, text=caption_text, reply_markup=reply_markup)
    except Exception as e:
        print(f"Error: {e}")
        await client.send_message(chat_id, text=caption_text, reply_markup=reply_markup)

# --- HANDLERS ---

@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    chat = message.chat
    user = message.from_user
    try:
        await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        await add_user(user.id)
        # Instant welcome in inbox
        await send_msg_with_media(client, user.id, user.mention, chat.title)
    except:
        pass

@pr0fess0r_99.on_message(filters.private & filters.command(["start"]))
async def start(client, message: Message):
    await add_user(message.from_user.id)
    button = [
        [InlineKeyboardButton("Updates Channel 📢", url=UPDATE_CH)],
        [InlineKeyboardButton("➕ Add Me To Your Chat", url=f"http://t.me/{client.me.username}?startgroup=botstart")]
    ]
    # Yahan photo support add kar diya gaya hai
    await send_msg_with_media(client, message.chat.id, message.from_user.mention, "Our Service", reply_markup=InlineKeyboardMarkup(button))

@pr0fess0r_99.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_handler(client, message):
    count = await users_db.count_documents({})
    await message.reply_text(f"📊 **Total Users:** `{count}`")

@pr0fess0r_99.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_handler(client, message):
    all_users = users_db.find({})
    msg = await message.reply_text("🚀 Broadcast started...")
    count, deleted = 0, 0
    async for user in all_users:
        try:
            await message.reply_to_message.copy(chat_id=user["user_id"])
            count += 1
            await asyncio.sleep(0.3)
        except:
            await users_db.delete_one({"user_id": user["user_id"]})
            deleted += 1
    await msg.edit(f"✅ Sent: `{count}` | Blocked: `{deleted}`")

print("🔥 Bot Repaired & Running!")
pr0fess0r_99.run()
