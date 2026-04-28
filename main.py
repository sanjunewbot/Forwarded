from alphagram import Client, filters
from alphagram.types import InlineKeyboardButton, InlineKeyboardMarkup
from alphagram.errors import FloodWait
from config import BOT_TOKEN, SUDO_USERS
import asyncio
import traceback
import os
import threading
from flask import Flask

# ===== FLASK HEALTH SERVER =====
web = Flask(__name__)

@web.route('/')
def home():
    return "Bot is running"

def run_web():
    web.run(host='0.0.0.0', port=8000)

threading.Thread(target=run_web, daemon=True).start()


# ===== BOT INIT =====
app = Client("FORWARDER", use_default_api=True, bot_token=BOT_TOKEN)

logs = []
task = None
s, f = 0, 0
caption = ''

FAST_DELAY = 0.2
SLOW_DELAY = 1.5
current_delay = FAST_DELAY

WORKERS = 4
BATCH_SIZE = 15

LOG_LIMIT = 1000

markup = InlineKeyboardMarkup(
    [[InlineKeyboardButton("Progress", callback_data='progress')]]
)

def chunkify(start, end, size):
    return [list(range(i, min(i + size, end + 1))) for i in range(start, end + 1, size)]

async def worker(chat_id, fwd_id, ids):
    global s, f, current_delay

    for msg_id in ids:
        try:
            await app.copy_message(fwd_id, chat_id, msg_id, caption=caption or None)
            s += 1
            current_delay = max(FAST_DELAY, current_delay - 0.03)
            await asyncio.sleep(current_delay)

        except FloodWait as e:
            wait_time = int(getattr(e, "value", 30))
            current_delay = min(SLOW_DELAY, current_delay + 0.3)
            await asyncio.sleep(wait_time)

        except Exception:
            f += 1

async def forward(chat_id, fwd_id, st, en):
    chunks = chunkify(st, en, BATCH_SIZE)
    sem = asyncio.Semaphore(WORKERS)

    async def limited_worker(ids):
        async with sem:
            await worker(chat_id, fwd_id, ids)

    await asyncio.gather(*[limited_worker(ch) for ch in chunks])


@app.on_message(filters.command("f") & filters.user(SUDO_USERS))
async def f_handler(_, m):
    global task, s, f, current_delay

    if task and not task.done():
        return await m.reply("Already running")

    try:
        spl = m.text.split()
        fwd_id = int(spl[1])
        chat_id, st_id = spl[2].split('/')[-2:]
        en_id = spl[3].split('/')[-1]

        st_id, en_id = int(st_id), int(en_id)
        chat_id = int("-100" + chat_id)

    except:
        return await m.reply("Usage:\n/f dest start_link end_link")

    s, f = 0, 0
    current_delay = FAST_DELAY

    await m.reply("🚀 Started")

    task = asyncio.create_task(forward(chat_id, fwd_id, st_id, en_id))


# ===== START =====
async def main():
    await app.start()
    print("🚀 Bot Started Successfully")

    # KEEP ALIVE (important)
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
