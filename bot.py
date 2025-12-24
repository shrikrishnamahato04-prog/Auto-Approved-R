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
async def send_msg_with_media(client, chat_id, mention, title, reply_markup=None):
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
    except:
        pass

# --- HANDLERS ---

@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    await client.approve_chat_join_request(message.chat.id, message.from_user.id)
    await add_user(message.from_user.id)
    await send_msg_with_media(client, message.from_user.id, message.from_user.mention, message.chat.title)

@pr0fess0r_99.on_message(filters.private & filters.command("start"))
async def start(client, message: Message):
    await add_user(message.from_user.id)
    await send_msg_with_media(client, message.chat.id, message.from_user.mention, "Our Service")

@pr0fess0r_99.on_message(filters.command("edit") & filters.user(ADMINS))
async def edit_buttons(client, message: Message):
    args = message.text.split(None, 3)
    if len(args) < 4:
        return await message.reply_text("Usage: `/edit 1 Name Link` (Use _ for spaces)")
    
    num, name, link = args[1], args[2], args[3]
    current = await get_buttons()
    if num == "1": current[0]['n1'], current[0]['u1'] = name.replace("_", " "), link
    elif num == "2": current[1]['n2'], current[1]['u2'] = name.replace("_", " "), link
    elif num == "3": current[1]['n3'], current[1]['u3'] = name.replace("_", " "), link
    
    await settings_db.update_one({"id": "start_buttons"}, {"$set": {"data": current}}, upsert=True)
    await message.reply_text("✅ Updated!")

# --- MENU COMMAND SETTINGS ---
async def set_menu_commands(client):
    await client.set_bot_commands([
        BotCommand("start", "Start the bot 🚀"),
        BotCommand("stats", "Bot Statistics 📊"),
        BotCommand("broadcast", "Send Broadcast 📢"),
        BotCommand("edit", "Edit Buttons 🛠️")
    ])

# --- BOT RUN LOGIC ---
async def main():
    await pr0fess0r_99.start()
    await set_menu_commands(pr0fess0r_99)
    print("🔥 Bot is Online with Menu Button!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
