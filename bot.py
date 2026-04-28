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

# 🔥 100% FIX ADMIN SYSTEM
# पहले ENV से लेगा, नहीं तो fallback use करेगा
ADMIN_ENV = os.getenv("ADMINS", "")
ADMINS = list(map(int, ADMIN_ENV.split())) if ADMIN_ENV else [123456789]  # 👈 replace fallback

task = None
success = 0
failed = 0
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

# ---------------- DEBUG COMMAND ----------------
@app.on_message(filters.command("check"))
async def check(_, m):
    await m.reply(f"Your ID: {m.from_user.id}\nAdmins: {ADMINS}")

# ---------------- FILTER UI ----------------
def build_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{k.upper()} {'✅' if v else '❌'}", callback_data=f"t_{k}")]
        for k, v in filters_state.items()
    ])

@app.on_message(filters.command("filter"))
async def filter_menu(_, m):
    if not is_admin(m.from_user.id):
        return await m.reply("❌ Not allowed")
    await m.reply("📁 Media Filter:", reply_markup=build_buttons())

@app.on_callback_query(filters.regex("^t_"))
async def toggle(_, q):
    if not is_admin(q.from_user.id):
        return await q.answer("Not allowed", show_alert=True)
    key = q.data.split("_")[1]
    filters_state[key] = not filters_state[key]
    await q.message.edit_reply_markup(build_buttons())

# ---------------- SPEED ----------------
@app.on_message(filters.command("speed"))
async def set_speed(_, m):
    global speed
    if not is_admin(m.from_user.id):
        return await m.reply("❌ Not allowed")
    try:
        val = int(m.text.split()[1])
        speed = {1:0.5,2:1,3:2,4:3,5:4}[val]
        await m.reply(f"⚡ Speed {val}")
    except:
        await m.reply("Usage: /speed 1-5")

# ---------------- LINK PARSER ----------------
def extract(link):
    link = link.split("?")[0]
    parts = link.strip().split("/")
    return int("-100"+parts[-2]), int(parts[-1])

# ---------------- PROGRESS BAR ----------------
def bar(p):
    return "█"*int(p//5)+"░"*(20-int(p//5))

# ---------------- FORWARD ----------------
async def forward_messages(src, dest, start, end, msg, cap):
    global success, failed

    total = end - start + 1
    done = 0
    start_time = time.time()

    for i in range(start, end+1):
        try:
            m = await app.get_messages(src, i)
            if not m or m.empty:
                continue

            if m.text and not filters_state["text"]: continue
            if m.photo and not filters_state["photo"]: continue
            if m.video and not filters_state["video"]: continue
            if m.audio and not filters_state["audio"]: continue
            if m.document and not filters_state["document"]: continue
            if m.voice and not filters_state["voice"]: continue
            if m.animation and not filters_state["animation"]: continue

            final = (m.caption or "")
            if cap:
                final += "\n\n"+cap

            await m.copy(dest, caption=final or None)
            success += 1

        except Exception:
            failed += 1

        done += 1

        if done % 10 == 0:
            p = (done/total)*100
            eta = int((total-done)/((done)/(time.time()-start_time))) if done else 0
            await msg.edit(
                f"📊 [{bar(p)}] {p:.1f}%\n"
                f"{done}/{total}\n✔ {success} ❌ {failed}\n"
                f"⏱️ {eta}s"
            )

        await asyncio.sleep(speed)

# ---------------- COMMAND ----------------
@app.on_message(filters.command("forward"))
async def forward(_, m):
    global success, failed

    if not is_admin(m.from_user.id):
        return await m.reply("❌ Not allowed")

    try:
        parts = m.text.split("|",1)
        main = parts[0].split()
        cap = parts[1].strip() if len(parts)>1 else ""

        _, dest, l1, l2 = main
        dest = int(dest)

        src, s = extract(l1)
        _, e = extract(l2)

    except:
        return await m.reply("Usage:\n/forward dest link link | caption")

    msg = await m.reply("🚀 Started")
    success = failed = 0

    await forward_messages(src, dest, s, e, msg, cap)

    await msg.edit(f"✅ Done\n✔ {success}\n❌ {failed}")

# ---------------- START ----------------
if __name__ == "__main__":
    print("Bot Started")
    app.start()
    idle()
