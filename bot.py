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

# 👇 यहाँ अपना REAL Telegram ID डालना है
ADMINS = [123456789]

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
    return user_id and user_id in ADMINS

# ---------------- GET ID ----------------
@app.on_message(filters.command("id"))
async def get_id(_, m):
    await m.reply(f"🆔 Your ID: `{m.from_user.id}`")

# ---------------- FILTER UI ----------------
def build_buttons():
    btns = []
    for k, v in filters_state.items():
        status = "✅" if v else "❌"
        btns.append([InlineKeyboardButton(f"{k.upper()} {status}", callback_data=f"toggle_{k}")])
    return InlineKeyboardMarkup(btns)

@app.on_message(filters.command("filter"))
async def filter_menu(_, m):
    if not is_admin(m.from_user.id):
        return await m.reply("❌ Not allowed")
    await m.reply("📁 Media Filter:", reply_markup=build_buttons())

@app.on_callback_query(filters.regex("toggle_"))
async def toggle_filter(_, q):
    if not is_admin(q.from_user.id):
        return await q.answer("Not allowed", show_alert=True)
    key = q.data.split("_")[1]
    filters_state[key] = not filters_state[key]
    await q.message.edit_reply_markup(build_buttons())
    await q.answer(f"{key} {'Enabled' if filters_state[key] else 'Disabled'}")

# ---------------- SPEED ----------------
@app.on_message(filters.command("speed"))
async def set_speed(_, m):
    global speed
    if not is_admin(m.from_user.id):
        return await m.reply("❌ Not allowed")
    try:
        val = int(m.text.split()[1])
        speed = {1:0.5,2:1,3:2,4:3,5:4}[val]
        await m.reply(f"⚡ Speed set to {val}")
    except:
        await m.reply("Usage: /speed 1-5")

# ---------------- PROGRESS BAR ----------------
def progress_bar(percent):
    bars = int(percent // 5)
    return "█"*bars + "░"*(20-bars)

# ---------------- LINK PARSER ----------------
def extract(link):
    link = link.split("?")[0]
    parts = link.strip().split("/")
    return int("-100"+parts[-2]), int(parts[-1])

# ---------------- FORWARD ----------------
async def forward_messages(src, dest, start, end, status_msg, user_caption):
    global success, failed, speed

    total = end - start + 1
    processed = 0
    start_time = time.time()
    current = start

    while current <= end:
        try:
            msgs = await app.get_messages(src, list(range(current, min(current+50,end)+1)))
            if not isinstance(msgs, list):
                msgs = [msgs]

            for msg in msgs:
                if not msg or msg.empty:
                    continue

                try:
                    final_caption = (msg.caption or "")
                    if user_caption:
                        final_caption += "\n\n" + user_caption

                    await msg.copy(dest, caption=final_caption or None)
                    success += 1
                except Exception as e:
                    failed += 1
                    logs.append(str(e))

                processed += 1

                if processed % 10 == 0:
                    percent = (processed/total)*100
                    bar = progress_bar(percent)
                    elapsed = time.time()-start_time
                    eta = int((total-processed)/(processed/elapsed)) if processed else 0

                    await status_msg.edit(
                        f"📊 Progress\n\n[{bar}] {percent:.1f}%\n"
                        f"{processed}/{total}\n"
                        f"✔ {success} ❌ {failed}\n\n"
                        f"⏱️ ETA: {eta}s\n⚡ {speed}s/msg"
                    )

                await asyncio.sleep(speed)

            current += 50

        except FloodWait as e:
            await asyncio.sleep(int(getattr(e,"value",30)))

# ---------------- COMMAND ----------------
@app.on_message(filters.command("forward"))
async def forward_handler(_, m):
    global task, success, failed

    if not is_admin(m.from_user.id):
        return await m.reply("❌ Not allowed")

    try:
        parts = m.text.split("|",1)
        main = parts[0].split()
        caption = parts[1].strip() if len(parts)>1 else ""

        _, dest, s_link, e_link = main
        dest = int(dest)

        src, start = extract(s_link)
        _, end = extract(e_link)

    except:
        return await m.reply("Usage:\n/forward dest start end | caption")

    msg = await m.reply("🚀 Started...")
    success = failed = 0

    await forward_messages(src,dest,start,end,msg,caption)

    await msg.edit(f"✅ Done\n✔ {success}\n❌ {failed}")

# ---------------- START ----------------
if __name__ == "__main__":
    print("Starting Bot...")
    app.start()
    print("Bot Started ✅")
    idle()
