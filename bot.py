import asyncio
import traceback
import os
import threading
import time
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN

# ---------------- WEB SERVER ----------------
web = Flask(__name__)

@web.route("/")
def home():
    return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", 8000))
    web.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

# ---------------- BOT ----------------
app = Client("forwarder-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

ADMINS = [123456789]  # 👈 apna user id dalna

task = None
success = 0
failed = 0
logs = []
speed = 2

filters_state = {
    "text": True,
    "photo": True,
    "video": True,
    "audio": True,
    "document": True,
    "voice": True,
    "animation": True
}

# ---------------- ADMIN CHECK ----------------
def is_admin(user_id):
    return user_id in ADMINS

# ---------------- FILTER UI ----------------
def build_buttons():
    btns = []
    for k, v in filters_state.items():
        status = "✅" if v else "❌"
        btns.append([InlineKeyboardButton(f"{k.upper()} {status}", callback_data=f"toggle_{k}")])
    return InlineKeyboardMarkup(btns)

@app.on_message(filters.command("filter"))
async def filter_menu(_, m):
    if not is_admin(m.from_user.id): return
    await m.reply("📁 Media Filter:", reply_markup=build_buttons())

@app.on_callback_query(filters.regex("toggle_"))
async def toggle_filter(_, q):
    if not is_admin(q.from_user.id): return
    key = q.data.split("_")[1]
    filters_state[key] = not filters_state[key]
    await q.message.edit_reply_markup(build_buttons())
    await q.answer(f"{key} {'Enabled' if filters_state[key] else 'Disabled'}")

# ---------------- SPEED ----------------
@app.on_message(filters.command("speed"))
async def set_speed(_, m):
    global speed
    if not is_admin(m.from_user.id): return
    try:
        val = int(m.text.split()[1])
        if val < 1 or val > 5:
            return await m.reply("Use 1-5")
        speed = {1: 0.5, 2: 1, 3: 2, 4: 3, 5: 4}[val]
        await m.reply(f"⚡ Speed set to {val}")
    except:
        await m.reply("Usage: /speed 1-5")

# ---------------- PROGRESS BAR ----------------
def progress_bar(percent):
    bars = int(percent // 5)
    return "█" * bars + "░" * (20 - bars)

# ---------------- LINK PARSER ----------------
def extract(link):
    link = link.split("?")[0]
    parts = link.strip().split("/")
    chat = int("-100" + parts[-2])
    msg_id = int(parts[-1])
    return chat, msg_id

# ---------------- FORWARD ----------------
async def forward_messages(src, dest, start, end, status_msg, user_caption):
    global success, failed, speed

    total = end - start + 1
    processed = 0
    start_time = time.time()
    current = start

    while current <= end:
        try:
            batch_end = min(current + 50, end)
            msgs = await app.get_messages(src, list(range(current, batch_end + 1)))

            if not isinstance(msgs, list):
                msgs = [msgs]

            for msg in msgs:
                if not msg or msg.empty:
                    continue

                # FILTERS
                if msg.text and not filters_state["text"]: continue
                if msg.photo and not filters_state["photo"]: continue
                if msg.video and not filters_state["video"]: continue
                if msg.audio and not filters_state["audio"]: continue
                if msg.document and not filters_state["document"]: continue
                if msg.voice and not filters_state["voice"]: continue
                if msg.animation and not filters_state["animation"]: continue

                try:
                    final_caption = ""

                    if msg.caption:
                        final_caption += msg.caption + "\n\n"

                    if user_caption:
                        final_caption += user_caption

                    await msg.copy(dest, caption=final_caption or None)
                    success += 1
                except Exception as e:
                    failed += 1
                    logs.append(str(e))

                processed += 1

                # ETA
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                remaining = total - processed
                eta = int(remaining / rate) if rate > 0 else 0

                # PROGRESS UPDATE
                if processed % 10 == 0:
                    percent = (processed / total) * 100
                    bar = progress_bar(percent)

                    try:
                        await status_msg.edit(
                            f"📊 Progress\n\n"
                            f"[{bar}] {percent:.1f}%\n\n"
                            f"✔ {success} | ❌ {failed}\n"
                            f"{processed}/{total}\n\n"
                            f"⏱️ ETA: {eta}s\n"
                            f"⚡ Speed: {speed}s/msg"
                        )
                    except:
                        pass

                await asyncio.sleep(speed)

            current = batch_end + 1

        except FloodWait as e:
            wait = int(getattr(e, "value", 30))
            await asyncio.sleep(wait)

        except Exception:
            failed += 1
            logs.append(traceback.format_exc())

# ---------------- COMMAND ----------------
@app.on_message(filters.command("forward"))
async def forward_handler(_, m):
    global task, success, failed

    if not is_admin(m.from_user.id):
        return await m.reply("❌ Not allowed")

    if task and not task.done():
        return await m.reply("Task already running")

    try:
        parts = m.text.split("|", 1)
        main = parts[0].strip().split()
        caption_text = parts[1].strip() if len(parts) > 1 else ""

        _, dest, start_link, end_link = main

        dest = int(dest)
        src_chat, start_id = extract(start_link)
        src2, end_id = extract(end_link)

        if src_chat != src2:
            return await m.reply("Source mismatch")

        if start_id > end_id:
            start_id, end_id = end_id, start_id

    except:
        return await m.reply(
            "Usage:\n/forward dest start_link end_link | caption"
        )

    # access check
    test = await app.get_messages(src_chat, start_id)
    if not test or test.empty:
        return await m.reply("❌ Cannot access source chat")

    msg = await m.reply("🚀 Forwarding started...")
    success, failed = 0, 0

    task = asyncio.create_task(
        forward_messages(src_chat, dest, start_id, end_id, msg, caption_text)
    )

    try:
        await task
    finally:
        task = None
        await msg.edit(f"✅ Done\n\n✔ {success}\n❌ {failed}")

# ---------------- START ----------------
if __name__ == "__main__":
    print("Starting Bot...")
    app.start()
    print("Bot Started ✅")
    idle()
