import re
import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from Extractor import app
from config import PREMIUM_LOGS

LOG_CHANNEL = PREMIUM_LOGS
BASE = "https://www.cdsjourney.com"

# ---------------- SESSION ----------------
def create_session():
    s = requests.Session()
    s.headers.update({
        "user-agent": "Mozilla/5.0"
    })
    return s


# ---------------- CSRF ----------------
def get_csrf(session):
    session.get(BASE)
    return session.cookies.get("csrftoken")


# ---------------- LOGIN ----------------
def send_otp(session, email, csrf):
    url = f"{BASE}/login-or-register/"
    data = {
        "csrfmiddlewaretoken": csrf,
        "loginEmail": email
    }
    headers = {
        "x-requested-with": "XMLHttpRequest",
        "referer": BASE
    }
    session.post(url, data=data, headers=headers)


def verify_otp(session, email, otp, csrf):
    url = f"{BASE}/verify-quiz-otp/"
    data = {
        "csrfmiddlewaretoken": csrf,
        "loginPhone2": email,
        "sent-OTP": otp,
        "first-name": "",
        "mobile": ""
    }
    headers = {
        "x-requested-with": "XMLHttpRequest",
        "referer": BASE
    }
    session.post(url, data=data, headers=headers)
    return "sessionid" in session.cookies.get_dict()


# ---------------- VALIDATION ----------------
def is_logged_in(session):
    try:
        r = session.get(f"{BASE}/student-dashboard/home/")
        return "Logout" in r.text
    except:
        return False


# ---------------- FETCH BATCHES ----------------
def get_batches(session):
    html = session.get(f"{BASE}/student-dashboard/home/").text
    soup = BeautifulSoup(html, "html.parser")

    batches = []

    for card in soup.find_all("div", class_="card-content"):
        try:
            title = card.find("h4").text.strip()

            batch_link = card.find("a", href=True)
            join_btn = card.find("a", class_="join-now-link")

            if not batch_link or not join_btn:
                continue

            href = batch_link["href"]
            join_href = join_btn.get("href", "")

            if "/batch/" not in href:
                continue

            batch_id = href.split("/batch/")[1].split("/")[0]

            if (
                "/student-dashboard/batch/" in join_href
                or "/zoom-index/" in join_href
            ):
                batches.append((batch_id, title))

        except:
            continue

    return batches


# ---------------- SUBJECTS ----------------
def get_subjects(session, batch_id):
    html = session.get(f"{BASE}/student-dashboard/batch/{batch_id}/subjects/").text
    soup = BeautifulSoup(html, "html.parser")

    # ✅ extract batch name
    try:
        batch_name = soup.find("h1").text.strip()
    except:
        batch_name = f"batch_{batch_id}"

    subjects = []
    for a in soup.find_all("a", href=True):
        if "/subject/" in a["href"]:
            try:
                sid = a["href"].split("/subject/")[1].split("/")[0]
                img = a.find("img")
                name = img.get("alt", f"Subject {sid}") if img else f"Subject {sid}"
                subjects.append((sid, name))
            except:
                continue

    return subjects, batch_name


# ---------------- VIDEOS ----------------
def get_videos(session, subject_id):
    html = session.get(f"{BASE}/student-dashboard/subject/{subject_id}/").text
    soup = BeautifulSoup(html, "html.parser")

    videos = []

    for card in soup.find_all("div", class_="card"):
        try:
            title = card.find("p").text.strip()
            btn = card.find("span", onclick=True)

            if not btn:
                continue

            vid = re.search(r"loadVideo\('(\d+)'\)", btn["onclick"])
            if vid:
                videos.append((title, vid.group(1)))
        except:
            continue

    return videos


# ---------------- VIDEO URL ----------------
def get_video_url(session, vid):
    try:
        r1 = session.get(f"{BASE}/get-recording-url/{vid}/").json()
        proxy = BASE + r1["url"]

        r2 = session.get(proxy).json()
        return r2.get("url")
    except:
        return None


# ---------------- START CALLBACK ----------------
@app.on_callback_query(filters.regex("^cds$"))
async def cds_start(app, callback_query):

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Session Login", callback_data="cds_login_session")],
        [InlineKeyboardButton("📧 Email Login (OTP)", callback_data="cds_login_email")]
    ])

    await callback_query.message.reply_text(
        "🔑 <b>Select Login Method</b>",
        reply_markup=buttons
    )


# ---------------- SESSION LOGIN ----------------
@app.on_callback_query(filters.regex("^cds_login_session$"))
async def cds_session_login(app, callback_query):

    await callback_query.answer()
    chat_id = callback_query.message.chat.id

    # 🔥 remove old button msg
    try:
        await callback_query.message.delete()
    except:
        pass

    # 🔑 ask session id
    ask_msg = await app.send_message(chat_id, "🔑 <b>Send SessionID:</b>")
    inp = await app.listen(chat_id)

    sessionid = inp.text.strip()

    try:
        await inp.delete()
    except:
        pass

    # 🔥 create session
    session = create_session()
    session.cookies.set("sessionid", sessionid)

    # ❌ invalid
    if not is_logged_in(session):
        return await ask_msg.edit_text("❌ <b>Invalid SessionID</b>")

    # ✅ reuse SAME message (clean UI)
    await ask_msg.edit_text("✅ <b>Login Successful!</b>\n\nFetching batches...")

    # 🔥 pass same msg
    await show_batches(app, chat_id, session, sessionid, ask_msg)

# ---------------- EMAIL LOGIN ----------------
@app.on_callback_query(filters.regex("^cds_login_email$"))
async def cds_email_login(app, callback_query):

    await callback_query.answer()

    chat_id = callback_query.message.chat.id

    # 🔥 edit instead of delete
    main_msg = callback_query.message
    await main_msg.edit_text("📧 <b>Send Email:</b>")

    session = create_session()

    # 📧 email input
    email_msg = await app.listen(chat_id)
    email = email_msg.text.strip()

    try:
        await email_msg.delete()
    except:
        pass

    # 🔑 csrf
    csrf = get_csrf(session)

    await main_msg.edit_text("📨 <b>Sending OTP...</b>")
    send_otp(session, email, csrf)

    # 🔢 OTP step
    await main_msg.edit_text("🔢 <b>Enter OTP:</b>")

    otp_msg = await app.listen(chat_id)
    otp = otp_msg.text.strip()

    try:
        await otp_msg.delete()
    except:
        pass

    csrf = session.cookies.get("csrftoken")

    # ❌ fail
    if not verify_otp(session, email, otp, csrf):
        return await main_msg.edit_text("❌ <b>OTP Failed</b>")

    sessionid = session.cookies.get("sessionid")

    await main_msg.edit_text("✅ <b>Login Successful!</b>\n\nFetching batches...")

    # 🔥 pass message for editing further
    await show_batches(app, chat_id, session, sessionid, main_msg)

# ---------------- SHOW BATCHES ----------------
async def show_batches(app, chat_id, session, sessionid, msg):

    batches = get_batches(session)

    if not batches:
        return await msg.edit_text("__❌ No enrolled batches found__")

    text = "📚 <b>Your Batches</b>\n\n"

    for bid, title in batches:
        text += f"• <code>{bid}</code> - {title}\n"

    text += "\n\n📝 <b>Send Batch ID to continue:</b>"

    await msg.edit_text(text)

    # 👇 wait for user input
    user_msg = await app.listen(chat_id)
    batch_id = user_msg.text.strip()

    try:
        await user_msg.delete()
    except:
        pass

    # 🔥 validate batch id
    valid_ids = [b[0] for b in batches]

    if batch_id not in valid_ids:
        return await msg.edit_text("❌ Invalid Batch ID. Restart again.")

    await msg.edit_text(f"⏳ Processing Batch <code>{batch_id}</code>...")

    # 👉 next step call (subjects / videos)
    await process_batch(app, chat_id, session, batch_id, msg)


# ---------------- BATCH CALLBACK ----------------
@app.on_callback_query(filters.regex("^cds_run_"))
async def cds_batch_callback(app: Client, callback_query):

    await callback_query.answer()

    data = callback_query.data.replace("cds_run_", "")
    batch_id, sessionid = data.split("|")

    chat_id = callback_query.message.chat.id

    # 🔥 delete old UI
    try:
        await callback_query.message.delete()
    except:
        pass

    # 🔥 session setup
    session = create_session()
    session.cookies.set("sessionid", sessionid)

    # 🔥 single progress message
    msg = await app.send_message(chat_id, "⏳ Starting...")

    # 🔥 delegate ALL work
    await process_batch(app, chat_id, session, batch_id, msg)

async def process_batch(app, chat_id, session, batch_id, msg):

    try:
        import asyncio
        import re

        subjects, batch_name = get_subjects(session, batch_id)

        if not subjects:
            return await msg.edit_text("❌ No subjects found")

        result = []
        total = 0

        for sid, sname in subjects:

            # 🔥 clean UI
            await msg.edit_text(f"📚 <b>{sname}</b>")

            videos = get_videos(session, sid)

            for title, vid in videos:
                url = get_video_url(session, vid)

                if url:
                    result.append(f"({sname}) {title}: {url}")
                    total += 1

            await asyncio.sleep(0.4)

        if total == 0:
            return await msg.edit_text("❌ No videos found")

        # 🔥 safe filename
        safe_name = re.sub(r'[\\/*?:"<>|]', "", batch_name)
        file_name = f"{safe_name}.txt"

        with open(file_name, "w", encoding="utf-8") as f:
            f.write("\n".join(result))

        await msg.edit_text("📤 Uploading...")

        caption = (
            f"╭━━━『 💠 CDS EXTRACTOR 💠 』━━━╮\n"
            f"📚 Batch: <code>{batch_name}</code>\n"
            f"🔗 Total Links: {total}\n"
            f"🕒 {datetime.now().strftime('%d-%m-%Y %I:%M %p')}\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━╯"
        )

        await app.send_document(chat_id, file_name, caption=caption)

        try:
            await app.send_document(
                LOG_CHANNEL,
                file_name,
                caption=f"📡 CDS Extract\n\n{caption}"
            )
        except:
            pass

        os.remove(file_name)

        # 🔥 clean UI
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")
        
