# MIT License
# Copyright (c) 2022 Muhammed

from os import environ
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ChatJoinRequest

# Bot Client Setup
pr0fess0r_99 = Client(
    "Auto Approved Bot",
    bot_token = environ["BOT_TOKEN"],
    api_id = int(environ["API_ID"]),
    api_hash = environ["API_HASH"],
    session_string = environ.get("SESSION_STRING")
)

# Config Variables
TEXT = environ.get("APPROVED_WELCOME_TEXT", "Hello {mention}\nWelcome To {title}\n\nYour Auto Approved")
APPROVED = environ.get("APPROVED_WELCOME", "on").lower()

@pr0fess0r_99.on_message(filters.private & filters.command(["start"]))
async def start(client, message: Message):
    approvedbot = await client.get_me() 
    button = [[ 
        InlineKeyboardButton("📦 Repo", url="https://github.com/PR0FESS0R-99/Auto-Approved-Bot"), 
        InlineKeyboardButton("Updates 📢", url="t.me/Mo_Tech_YT") 
    ], [ 
        InlineKeyboardButton("➕️ Add Me To Your Chat ➕️", url=f"http://t.me/{approvedbot.username}?startgroup=botstart") 
    ]]
    await client.send_message(
        chat_id=message.chat.id, 
        text=f"**__Hello {message.from_user.mention}! I am Auto Approver Bot. [Add Me To Your Group/Channel](http://t.me/{approvedbot.username}?startgroup=botstart) to start auto-approving members.__**", 
        reply_markup=InlineKeyboardMarkup(button), 
        disable_web_page_preview=True
    )

@pr0fess0r_99.on_chat_join_request()
async def autoapprove(client, message: ChatJoinRequest):
    chat = message.chat # Chat info
    user = message.from_user # User info
    print(f"New Request: {user.first_name} in {chat.title}") 
    
    try:
        # Har request ko approve karne ke liye
        await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        
        # Agar welcome message bhejna hai
        if APPROVED == "on":
            try:
                await client.send_message(chat_id=chat.id, text=TEXT.format(mention=user.mention, title=chat.title))
            except Exception:
                pass # Agar bot channel mein message nahi bhej pa raha toh skip kare
        print(f"Successfully Approved: {user.first_name}")
        
    except Exception as e:
        print(f"Approval Error: {e}")

print("Auto Approved Bot is LIVE!")
pr0fess0r_99.run()
