import asyncio
import traceback
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN

app = Client(
    "forwarder-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

task = None
success = 0
failed = 0
logs = []
caption = ""


async def forward_messages(src, dest, start, end):
    global success, failed

    current = start
    while current <= end:
        try:
            batch_end = min(current + 99, end)

            msgs = await app.get_messages(src, list(range(current, batch_end + 1)))

            if not isinstance(msgs, list):
                msgs = [msgs]

            for msg in msgs:
                if not msg:
                    continue

                try:
                    await msg.copy(dest, caption=caption or None)
                    success += 1
                    await asyncio.sleep(1.5)
                except Exception:
                    failed += 1

            current = batch_end + 1

        except FloodWait as e:
            wait = int(e.value)
            logs.append(f"FloodWait {wait}s")
            await asyncio.sleep(wait)

        except Exception:
            logs.append(traceback.format_exc())
            failed += 1


@app.on_message(filters.command("start"))
async def start(_, m):
    await m.reply(
        "**Forwarder Bot Ready ✅**\n\n"
        "Use:\n`/f chat_id start end`\n\n"
        "Example:\n`/f -1001234567890 1 50`"
    )


@app.on_message(filters.command("f"))
async def forward_handler(_, m):
    global task, success, failed

    if task:
        return await m.reply("⚠️ Task already running.")

    try:
        _, chat_id, start, end = m.text.split()
        chat_id = int(chat_id)
        start = int(start)
        end = int(end)
    except:
        return await m.reply("❌ Usage:\n/f chat_id start end")

    msg = await m.reply("🚀 Forwarding started...")

    success, failed = 0, 0

    task = asyncio.create_task(
        forward_messages(chat_id, m.chat.id, start, end)
    )

    try:
        await task
    except:
        pass
    finally:
        task = None
        await msg.edit(f"✅ Done\n\n✔ Success: {success}\n❌ Failed: {failed}")


@app.on_message(filters.command("cancel"))
async def cancel(_, m):
    global task
    if not task:
        return await m.reply("No running task.")
    task.cancel()
    task = None
    await m.reply("❌ Cancelled.")


@app.on_message(filters.command("caption"))
async def set_caption(_, m):
    global caption
    parts = m.text.split(maxsplit=1)
    if len(parts) == 2:
        caption = parts[1]
        await m.reply(f"Caption set:\n{caption}")
    else:
        await m.reply("Usage:\n/caption your text")


@app.on_message(filters.command("dcaption"))
async def del_caption(_, m):
    global caption
    caption = ""
    await m.reply("Caption removed.")


@app.on_message(filters.command("logs"))
async def send_logs(_, m):
    if not logs:
        return await m.reply("No logs.")
    with open("logs.txt", "w") as f:
        f.write("\n\n".join(logs))
    await m.reply_document("logs.txt")

import asyncio
import traceback
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN

app = Client(
    "forwarder-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

task = None
success = 0
failed = 0
logs = []
caption = ""


async def forward_messages(src, dest, start, end):
    global success, failed

    current = start
    while current <= end:
        try:
            batch_end = min(current + 99, end)

            msgs = await app.get_messages(src, list(range(current, batch_end + 1)))

            if not isinstance(msgs, list):
                msgs = [msgs]

            for msg in msgs:
                if not msg:
                    continue

                try:
                    await msg.copy(dest, caption=caption or None)
                    success += 1
                    await asyncio.sleep(1.5)
                except Exception:
                    failed += 1

            current = batch_end + 1

        except FloodWait as e:
            wait = int(e.value)
            logs.append(f"FloodWait {wait}s")
            await asyncio.sleep(wait)

        except Exception:
            logs.append(traceback.format_exc())
            failed += 1


@app.on_message(filters.command("start"))
async def start(_, m):
    await m.reply(
        "**Forwarder Bot Ready ✅**\n\n"
        "Use:\n`/f chat_id start end`\n\n"
        "Example:\n`/f -1001234567890 1 50`"
    )


@app.on_message(filters.command("f"))
async def forward_handler(_, m):
    global task, success, failed

    if task:
        return await m.reply("⚠️ Task already running.")

    try:
        _, chat_id, start, end = m.text.split()
        chat_id = int(chat_id)
        start = int(start)
        end = int(end)
    except:
        return await m.reply("❌ Usage:\n/f chat_id start end")

    msg = await m.reply("🚀 Forwarding started...")

    success, failed = 0, 0

    task = asyncio.create_task(
        forward_messages(chat_id, m.chat.id, start, end)
    )

    try:
        await task
    except:
        pass
    finally:
        task = None
        await msg.edit(f"✅ Done\n\n✔ Success: {success}\n❌ Failed: {failed}")


@app.on_message(filters.command("cancel"))
async def cancel(_, m):
    global task
    if not task:
        return await m.reply("No running task.")
    task.cancel()
    task = None
    await m.reply("❌ Cancelled.")


@app.on_message(filters.command("caption"))
async def set_caption(_, m):
    global caption
    parts = m.text.split(maxsplit=1)
    if len(parts) == 2:
        caption = parts[1]
        await m.reply(f"Caption set:\n{caption}")
    else:
        await m.reply("Usage:\n/caption your text")


@app.on_message(filters.command("dcaption"))
async def del_caption(_, m):
    global caption
    caption = ""
    await m.reply("Caption removed.")


@app.on_message(filters.command("logs"))
async def send_logs(_, m):
    if not logs:
        return await m.reply("No logs.")
    with open("logs.txt", "w") as f:
        f.write("\n\n".join(logs))
    await m.reply_document("logs.txt")

from pyrogram import idle

if __name__ == "__main__":
    app.start()
    print("Bot Started ✅")
    idle()
