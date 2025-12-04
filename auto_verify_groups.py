from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon.errors import SessionPasswordNeededError
import asyncio
import re
import requests
import datetime

# === YOUR CONFIG ===
api_id = 12345678        # Your API ID
api_hash = 'your_api_hash_here'
phone = '+2519xxxxxxxx'   # One of your 10 accounts

# Your website API to update task status
WEB_API = "https://buytgold.visionexcellencecenter.com/api/update_task.php"

# Accounts list (you can run 10 instances or use multiple sessions)
accounts = [
    {'phone': '+2519xxx1', 'session': 'account1'},
    {'phone': '+2519xxx2', 'session': 'account2'},
    # add up to 10
]

client = TelegramClient('verifier', api_id, api_hash)

async def check_group_age(chat):
    try:
        full_chat = await client.get_entity(chat)
        if hasattr(full_chat, 'migrated_to'):
            return None
        created = full_chat.date
        year = created.year
        return year
    except:
        return None

async def leave_and_reject(chat, task_id, reason):
    await client.send_message(chat, "Invalid group detected. Leaving.")
    await client(LeaveChannelRequest(chat))
    requests.post(WEB_API, data={
        'task_id': task_id,
        'status': 'Rejected',
        'reason': reason
    })

@client.on(events.NewMessage(pattern='/start_verify'))
async def handler(event):
    if event.is_private:
        link = event.message.text.split(maxsplit=1)[1] if len(event.message.text.split()) > 1 else None
        task_id = event.sender_id  # or extract from message

        if not link:
            return

        # Extract invite link
        match = re.search(r'(https?://t\.me/\+?[a-zA-Z0-9]+)', link)
        if not match:
            return
        invite_link = match.group(0)

        try:
            # Join group
            result = await client(ImportChatInviteRequest(invite_link.split('/')[-1]))
            chat = result.chats[0]

            await event.reply(f"Joined: {chat.title}")

            # Check creation year
            year = await check_group_age(chat)
            expected_year = 2022  # or extract from task name

            if not year or year > 2023:
                await leave_and_reject(chat, task_id, f"Group created in {year}, expected 2022 or older")
                await event.reply(f"Rejected - Group is from {year}")
                return

            await event.reply(f"Valid old group ({year}) - Waiting for ownership...")

            # Wait for ownership transfer
            @client.on(events.ChatAction(func=lambda e: e.user_added and e.new_admin))
            async def ownership_handler(e):
                if e.user_id == (await client.get_me()).id:
                    await event.reply("Ownership received! Task approved.")
                    requests.post(WEB_API, data={
                        'task_id': task_id,
                        'status': 'Approved',
                        'revenue': 15.00  # auto calculate based on year
                    })
                    await asyncio.sleep(5)
                    await client(LeaveChannelRequest(chat))

            # Keep alive for 48 hours max
            await asyncio.sleep(48 * 3600)
            await client(LeaveChannelRequest(chat))

        except Exception as e:
            await event.reply(f"Error: {str(e)}")

print("Bot is running... Waiting for /start_verify + link")
client.start()
client.run_until_disconnected()
