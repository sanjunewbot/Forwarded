from alphagram import Client, filters
from alphagram.types import InlineKeyboardButton, InlineKeyboardMarkup
from alphagram.errors import FloodWait
from config import BOT_TOKEN, SUDO_USERS
import asyncio
import traceback
import os
import threading
from flask import Flask

# ===== FLASK HEALTH SERVER (for Koyeb) =====
web = Flask(__name__)

@web.route('/')
def home():
    return "Bot is running"

def run_web():
    web.run(host='0.0.0.0', port=8000)

threading.Thread(target=run_web).start()


# ===== BOT INIT =====
app = Client("FORWARDER", use_default_api=True, bot_token=BOT_TOKEN)

logs = []
task = None
s, f = 0, 0
caption = ''

# ===== SPEED CONTROL =====
FAST_DELAY = 0.2
SLOW_DELAY = 1.5
current_delay = FAST_DELAY

# ===== MULTI WORKER =====
WORKERS = 4
BATCH_SIZE = 15

LOG_LIMIT = 1000

markup = InlineKeyboardMarkup(
    [[InlineKeyboardButton("Progress", callback_data='progress')]]
)


# ===== CHUNK =====
def chunkify(start, end, size):
    return [list(range(i, min(i + size, end + 1))) for i in range(start, end + 1, size)]


# ===== WORKER =====
async def worker(chat_id: int, fwd_id: int, ids):
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

            logs.append(f"FloodWait: {wait_time}s")
            if len(logs) > LOG_LIMIT:
                logs.pop(0)

            await asyncio.sleep(wait_time)

        except Exception as e:
            if "MESSAGE_ID_INVALID" in str(e):
                continue

            f += 1
            logs.append(traceback.format_exc())
            if len(logs) > LOG_LIMIT:
                logs.pop(0)


# ===== FORWARD =====
async def forward(chat_id: int, fwd_id: int, st: int, en: int):
    chunks = chunkify(st, en, BATCH_SIZE)

    sem = asyncio.Semaphore(WORKERS)

    async def limited_worker(ids):
        async with sem:
            await worker(chat_id, fwd_id, ids)

    tasks = [asyncio.create_task(limited_worker(ch)) for ch in chunks]
    await asyncio.gather(*tasks)


# ===== CAPTION =====
@app.on_message(filters.command("caption") & filters.user(SUDO_USERS))
async def caption_handler(_, m):
    global caption
    parts = m.text.split(maxsplit=1)

    if len(parts) > 1:
        caption = parts[1]
        return await m.reply(f"Caption set:\n{caption}")

    return await m.reply("No caption set." if not caption else f"Current:\n{caption}")


@app.on_message(filters.command("dcaption") & filters.user(SUDO_USERS))
async def dcaption_handler(_, m):
    global caption
    caption = ''
    await m.reply("Caption removed.")


# ===== LOGS =====
@app.on_message(filters.command("logs") & filters.user(SUDO_USERS))
async def logs_handler(_, m):
    if not logs:
        return await m.reply("No Logs Stored.")

    with open("logs.txt", "w") as f_:
        f_.write("\n\n".join(logs))

    await m.reply_document("logs.txt")
    os.remove("logs.txt")


# ===== CANCEL =====
@app.on_message(filters.command("cancel") & filters.user(SUDO_USERS))
async def cancel_handler(_, m):
    global task

    if task and not task.done():
        task.cancel()
        task = None
        return await m.reply("❌ Task cancelled.")

    await m.reply("No active task.")


# ===== PROGRESS BUTTON =====
@app.on_callback_query(filters.regex("progress"))
async def progress_cb(_, cq):
    total = s + f
    await cq.answer(f"✅ {s} | ❌ {f} | 📦 {total}", show_alert=True)


# ===== FORWARD COMMAND =====
@app.on_message(filters.command('f') & filters.user(SUDO_USERS))
async def f_handler(_, m):
    global task, s, f, current_delay

    if task and not task.done():
        return await m.reply("Already running. Use /cancel first.")

    try:
        spl = m.text.split()
        fwd_id = int(spl[1])

        chat_id, st_id = spl[2].split('/')[-2:]
        en_id = spl[3].split('/')[-1]

        st_id, en_id = int(st_id), int(en_id)

        try:
            int(chat_id)
            chat_id = int("-100" + chat_id)
        except:
            pass

    except:
        traceback.print_exc()
        return await m.reply('/f fwd_chat_id start_link end_link')

    # reset
    s, f = 0, 0
    current_delay = FAST_DELAY
    logs.clear()

    await m.reply("🚀 Ultra-fast forwarding started...", reply_markup=markup)

    task = asyncio.create_task(forward(chat_id, fwd_id, st_id, en_id))

    try:
        await task
    except:
        pass
    finally:
        task = None


# ===== START =====
app.start()
print("🚀 Bot Started Successfully")

# keep bot alive
import time
while True:
    time.sleep(10)
