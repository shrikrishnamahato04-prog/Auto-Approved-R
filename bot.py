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
    api_hash = environ["API_HASH"],
    session_string = environ.get("SESSION_STRING")
)

# --- DATABASE (Hamesha ke liye Safe) ---
mongo_url = environ["MONGO_URL"]
db_client = AsyncIOMotorClient(mongo_url)
db = db_client.AutoApproveBot
users_db = db.users

# --- CONFIG VARS (Heroku Settings se control karein) ---
ADMINS = [int(admin) for admin in environ.get("ADMINS", "").split()]
TEXT = environ.get("APPROVED_WELCOME_TEXT", "Hello {mention}\nWelcome To {title}!")
UPDATE_CH = environ.get("UPDATE_CH", "https://t.me/Mo_Tech_YT") 
WELCOME_PIC = environ.get("WELCOME_PIC", "") # Photo link (optional)

# Database mein user save karne ka function
async def add_user(user_id):
    if not await users_db.find_one({"user_id": user_id}):
        await users_db.insert_one({"user_id": user_id})

# --- FEATURES ---

# 1. Sabse Fast Auto-Approval Logic
@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    chat = message.chat
    user = message.from_user
    
    # Priority 1: Instant Approval
    try:
        await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
    except Exception as e:
        print(f"Error: {e}")
        return

    # Priority 2: Save ID for Broadcast
    await add_user(user.id)
    
    # Priority 3: Welcome Message (Inbox)
    try:
        if WELCOME_PIC:
            await client.send_photo(
                chat_id=user.id, 
                photo=WELCOME_PIC, 
                caption=TEXT.format(mention=user.mention, title=chat.title)
            )
        else:
            await client.send_message(
                chat_id=user.id, 
                text=TEXT.format(mention=user.mention, title=chat.title)
            )
    except:
        pass # User blocked bot

# 2. Start Command with Dynamic Link
@pr0fess0r_99.on_message(filters.private & filters.command(["start"]))
async def start(client, message: Message):
    await add_user(message.from_user.id)
    button = [
        [InlineKeyboardButton("Updates Channel 📢", url=UPDATE_CH)],
        [InlineKeyboardButton("➕ Add Me To Your Chat", url=f"http://t.me/{client.me.username}?startgroup=botstart")]
    ]
    await message.reply_text(
        text=f"**Hello {message.from_user.mention}!**\n\nI am the most advanced Auto-Approver Bot with Database support.", 
        reply_markup=InlineKeyboardMarkup(button)
    )

# 3. Stats Feature (Admin Only)
@pr0fess0r_99.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_handler(client, message):
    count = await users_db.count_documents({})
    await message.reply_text(f"📊 **Bot Statistics**\n\n👥 Total Workers/Users: `{count}`\n📡 Database: `MongoDB Cloud`")

# 4. Smart Broadcast (With Auto-Clean)
@pr0fess0r_99.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_handler(client, message):
    all_users = users_db.find({})
    msg = await message.reply_text("🚀 Broadcast started...")
    count, deleted = 0, 0
    
    async for user in all_users:
        try:
            await message.reply_to_message.copy(chat_id=user["user_id"])
            count += 1
            await asyncio.sleep(0.3) # Avoid FloodWait
        except:
            await users_db.delete_one({"user_id": user["user_id"]})
            deleted += 1
            
    await msg.edit(f"✅ **Broadcast Completed**\n\n📩 Sent: `{count}`\n🗑 Removed (Blocked Users): `{deleted}`")

print("🔥 All-In-One Pro Bot is LIVE!")
pr0fess0r_99.run()
