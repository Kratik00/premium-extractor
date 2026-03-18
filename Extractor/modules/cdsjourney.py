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
            link = card.find("a", href=True)["href"]

            if "/batch/" in link:
                bid = link.split("/batch/")[1].split("/")[0]
                batches.append((bid, title))
        except:
            continue

    return batches


# ---------------- SUBJECTS ----------------
def get_subjects(session, batch_id):
    html = session.get(f"{BASE}/student-dashboard/batch/{batch_id}/subjects/").text
    soup = BeautifulSoup(html, "html.parser")

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

    return subjects


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

    inp = await app.ask(callback_query.message.chat.id, "🔑 Send SessionID:")
    sessionid = inp.text.strip()

    session = create_session()
    session.cookies.set("sessionid", sessionid)

    if not is_logged_in(session):
        return await callback_query.message.reply("❌ Invalid SessionID")

    await show_batches(app, callback_query.message, session, sessionid)


# ---------------- EMAIL LOGIN ----------------
@app.on_callback_query(filters.regex("^cds_login_email$"))
async def cds_email_login(app, callback_query):

    session = create_session()

    email_msg = await app.ask(callback_query.message.chat.id, "📧 Send Email:")
    email = email_msg.text.strip()

    csrf = get_csrf(session)

    await callback_query.message.reply("📨 Sending OTP...")
    send_otp(session, email, csrf)

    otp_msg = await app.ask(callback_query.message.chat.id, "🔢 Enter OTP:")
    otp = otp_msg.text.strip()

    if not verify_otp(session, email, otp, csrf):
        return await callback_query.message.reply("❌ OTP Failed")

    sessionid = session.cookies.get("sessionid")

    await show_batches(app, callback_query.message, session, sessionid)


# ---------------- SHOW BATCHES ----------------
async def show_batches(app, message, session, sessionid):

    msg = await message.reply("🔄 Fetching batches...")

    batches = get_batches(session)

    if not batches:
        return await msg.edit_text("❌ No batches found")

    keyboard = []
    for bid, title in batches:
        keyboard.append([
            InlineKeyboardButton(title, callback_data=f"cds_run_{bid}|{sessionid}")
        ])

    await msg.edit_text(
        "📚 <b>Select Batch:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- BATCH CALLBACK ----------------
@app.on_callback_query(filters.regex("^cds_run_"))
async def cds_batch_callback(app: Client, callback_query):

    data = callback_query.data.replace("cds_run_", "")
    batch_id, sessionid = data.split("|")

    session = create_session()
    session.cookies.set("sessionid", sessionid)

    await callback_query.answer("⏳ Extracting...")

    msg = await callback_query.message.reply_text("🔄 Processing...")

    try:
        subjects = get_subjects(session, batch_id)

        if not subjects:
            return await msg.edit_text("❌ No subjects found")

        result = []
        total = 0

        for sid, sname in subjects:
            videos = get_videos(session, sid)

            for title, vid in videos:
                url = get_video_url(session, vid)

                if url:
                    result.append(f"({sname}) {title}: {url}")
                    total += 1

        if total == 0:
            return await msg.edit_text("❌ No videos found")

        file_name = f"CDS_{batch_id}.txt"

        with open(file_name, "w", encoding="utf-8") as f:
            f.write("\n".join(result))

        caption = (
            f"╭━━━『 💠 CDS EXTRACTOR 💠 』━━━╮\n"
            f"📚 Batch ID: <code>{batch_id}</code>\n"
            f"🔗 Total Links: {total}\n"
            f"🕒 {datetime.now().strftime('%d-%m-%Y %I:%M %p')}\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━╯"
        )

        await app.send_document(
            callback_query.message.chat.id,
            file_name,
            caption=caption
        )

        try:
            await app.send_document(
                LOG_CHANNEL,
                file_name,
                caption=f"📡 CDS Extract\n\n{caption}"
            )
        except:
            pass

        os.remove(file_name)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")
