from os import environ
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ChatJoinRequest
from motor.motor_asyncio import AsyncIOMotorClient

# Bot Client Setup
pr0fess0r_99 = Client(
    "Auto Approved Bot",
    bot_token = environ["BOT_TOKEN"],
    api_id = int(environ["API_ID"]),
    api_hash = environ["API_HASH"],
    session_string = environ.get("SESSION_STRING")
)

# Database Setup (MongoDB)
# Heroku mein MONGO_URL naam ka variable zaroor dalein
mongo_url = environ.get("MONGO_URL")
if mongo_url:
    db_client = AsyncIOMotorClient(mongo_url)
    db = db_client.AutoApproveBot
    users_db = db.users
else:
    users_db = None

# Admin IDs (Heroku mein ADMINS variable dalein, space dekar IDs likhein)
ADMINS = [int(admin) for admin in environ.get("ADMINS", "").split()]
TEXT = environ.get("APPROVED_WELCOME_TEXT", "Hello {mention}\nWelcome To {title}\n\nYour Request has been Auto Approved!")
APPROVED = environ.get("APPROVED_WELCOME", "on").lower()

# User ID Save karne ka function
async def add_user(user_id):
    if users_db is not None:
        if not await users_db.find_one({"user_id": user_id}):
            await users_db.insert_one({"user_id": user_id})

@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    chat = message.chat
    user = message.from_user
    
    # User ko DB mein save karein broadcast ke liye
    await add_user(user.id)
    
    try:
        # 1. Request Approve karein
        await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        
        # 2. User ko Inbox (Private) mein message bhejein
        if APPROVED == "on":
            try:
                await client.send_message(chat_id=user.id, text=TEXT.format(mention=user.mention, title=chat.title))
            except Exception:
                pass 
        print(f"Approved: {user.first_name}")
    except Exception as e:
        print(f"Error: {e}")

@pr0fess0r_99.on_message(filters.private & filters.command(["start"]))
async def start(client, message: Message):
    # Start karne par bhi user save hoga
    await add_user(message.from_user.id)
    
    approvedbot = await client.get_me() 
    button = [[ 
        InlineKeyboardButton("Updates 📢", url="t.me/Mo_Tech_YT") 
    ], [ 
        InlineKeyboardButton("➕️ Add Me To Your Chat ➕️", url=f"http://t.me/{approvedbot.username}?startgroup=botstart") 
    ]]
    await client.send_message(
        chat_id=message.chat.id, 
        text=f"**Hello {message.from_user.mention}! I am Auto Approver Bot.**", 
        reply_markup=InlineKeyboardMarkup(button)
    )

# Broadcast Command (Sirf Admins ke liye)
@pr0fess0r_99.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_handler(client, message):
    if users_db is None:
        return await message.reply_text("MONGO_URL missing hai!")

    all_users = users_db.find({})
    msg = await message.reply_text("Broadcast chalu hai...")
    count = 0
    
    async for user in all_users:
        try:
            await message.reply_to_message.copy(chat_id=user["user_id"])
            count += 1
            await asyncio.sleep(0.3) # Flood se bachne ke liye
        except:
            pass
            
    await msg.edit(f"✅ Broadcast Khatam!\nTotal Users: {count}")

print("Bot with Broadcast & MongoDB is LIVE!")
pr0fess0r_99.run()
