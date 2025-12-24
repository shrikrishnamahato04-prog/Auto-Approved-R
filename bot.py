from os import environ
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ChatJoinRequest, BotCommand
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
settings_db = db.settings

# --- CONFIG VARS ---
ADMINS = [int(admin) for admin in environ.get("ADMINS", "").split()]
TEXT = environ.get("APPROVED_WELCOME_TEXT", "Hello {mention}\nWelcome To {title}!")
UPDATE_CH = environ.get("UPDATE_CH", "https://t.me/Mo_Tech_YT") 
WELCOME_PIC = environ.get("WELCOME_PIC", "")

# --- HELPERS ---
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

# --- SEND MEDIA FUNCTION ---
async def send_msg_with_media(client, chat_id, mention, title):
    caption_text = TEXT.format(mention=mention, title=title)
    btns_data = await get_buttons()
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btns_data[0]['n1'], url=btns_data[0]['u1'])],
        [
            InlineKeyboardButton(btns_data[1]['n2'], url=btns_data[1]['u2']),
            InlineKeyboardButton(btns_data[1]['n3'], url=btns_data[1]['u3'])
        ],
        [
            InlineKeyboardButton("Add to Group ➕", url=f"http://t.me/{client.me.username}?startgroup=botstart"),
            InlineKeyboardButton("Add to Channel 📢", url=f"http://t.me/{client.me.username}?startchannel=botstart")
        ]
    ])

    try:
        if WELCOME_PIC:
            await client.send_photo(chat_id, photo=WELCOME_PIC, caption=caption_text, reply_markup=keyboard)
        else:
            await client.send_message(chat_id, text=caption_text, reply_markup=keyboard)
    except Exception as e:
        print(f"Error: {e}")

# --- HANDLERS ---

@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    try:
        await client.approve_chat_join_request(message.chat.id, message.from_user.id)
        await add_user(message.from_user.id)
        await send_msg_with_media(client, message.from_user.id, message.from_user.mention, message.chat.title)
    except: pass

@pr0fess0r_99.on_message(filters.private & filters.command("start"))
async def start(client, message: Message):
    await add_user(message.from_user.id)
    await send_msg_with_media(client, message.chat.id, message.from_user.mention, "Our Service")

@pr0fess0r_99.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_handler(client, message):
    count = await users_db.count_documents({})
    await message.reply_text(f"📊 **Total Users:** `{count}`")

@pr0fess0r_99.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_handler(client, message):
    all_users = users_db.find({})
    msg = await message.reply_text("🚀 Broadcast In Progress...")
    count, deleted = 0, 0
    async for user in all_users:
        try:
            await message.reply_to_message.copy(chat_id=user["user_id"])
            count += 1
            await asyncio.sleep(0.3)
        except:
            await users_db.delete_one({"user_id": user["user_id"]})
            deleted += 1
    await msg.edit(f"✅ Sent: `{count}` | Deleted: `{deleted}`")

@pr0fess0r_99.on_message(filters.command("edit") & filters.user(ADMINS))
async def edit_buttons(client, message: Message):
    args = message.text.split(None, 3)
    if len(args) < 4:
        return await message.reply_text("Usage: `/edit 1 Name Link` (_ for space)")
    num, name, link = args[1], args[2], args[3]
    current = await get_buttons()
    if num == "1": current[0]['n1'], current[0]['u1'] = name.replace("_", " "), link
    elif num == "2": current[1]['n2'], current[1]['u2'] = name.replace("_", " "), link
    elif num == "3": current[1]['n3'], current[1]['u3'] = name.replace("_", " "), link
    await settings_db.update_one({"id": "start_buttons"}, {"$set": {"data": current}}, upsert=True)
    await message.reply_text(f"✅ Button {num} Updated!")

# --- START BOT ---
async def start_bot():
    await pr0fess0r_99.start()
    await pr0fess0r_99.set_bot_commands([
        BotCommand("start", "🚀 Start Bot"),
        BotCommand("stats", "📊 Check Stats"),
        BotCommand("broadcast", "📢 Broadcast"),
        BotCommand("edit", "🛠️ Edit Buttons")
    ])
    print("🔥 BOT IS LIVE!")
    await idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
