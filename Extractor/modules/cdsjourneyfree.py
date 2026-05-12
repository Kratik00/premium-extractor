import os
import time
import requests

from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

# ================= SETTINGS =================

LOG_CHANNEL = PREMIUM_LOGS

BASE = "https://www.cdsjourney.com"

HEADERS = {
    "accept": "application/json",
    "user-agent": "Mozilla/5.0"
}

COURSES = {
    "course1": ("Bravo GAT batch (NDA 1 2026)", 45),
    "course2": ("Bravo MATH batch (NDA 1 2026)", 46),
}

# ================= TEMP STORAGE =================

LOGIN_SESSIONS = {}

# ================= SESSION =================

def create_session():

    session = requests.Session()

    session.headers.update(HEADERS)

    session.get(BASE, timeout=20)

    return session

# ================= LOGIN =================

def send_otp(session, email):

    try:

        url = f"{BASE}/login-or-register/"

        csrf = session.cookies.get("csrftoken")

        data = {
            "csrfmiddlewaretoken": csrf,
            "loginEmail": email
        }

        headers = {
            "x-requested-with": "XMLHttpRequest",
            "referer": BASE + "/",
            "origin": BASE,
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0"
        }

        r = session.post(
            url,
            data=data,
            headers=headers,
            timeout=20
        )

        print("\n[+] OTP SEND STATUS:", r.status_code)
        print("[+] OTP RESPONSE:", r.text)

        return r.status_code == 200

    except Exception as e:

        print(f"OTP SEND ERROR: {e}")

        return False


def verify_otp(session, email, otp):

    try:

        url = f"{BASE}/verify-quiz-otp/"

        csrf = session.cookies.get("csrftoken")

        data = {
            "csrfmiddlewaretoken": csrf,
            "loginPhone2": email,
            "sent-OTP": otp,
            "first-name": "",
            "mobile": ""
        }

        headers = {
            "x-requested-with": "XMLHttpRequest",
            "referer": BASE + "/",
            "origin": BASE,
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0"
        }

        r = session.post(
            url,
            data=data,
            headers=headers,
            timeout=20
        )

        print("\n[+] VERIFY STATUS:", r.status_code)
        print("[+] VERIFY RESPONSE:", r.text)

        cookies = session.cookies.get_dict()

        return "sessionid" in cookies

    except Exception as e:

        print(f"OTP VERIFY ERROR: {e}")

        return False

# ================= API =================

def get_subjects(session, batch_id):

    try:

        url = f"{BASE}/api/batch-subject/{batch_id}/"

        r = session.get(url, timeout=20)

        if r.status_code != 200:
            return []

        data = r.json()

        return data.get("list", [])

    except Exception as e:

        print(f"SUBJECT API ERROR: {e}")

        return []


def get_recordings(session, subject_id):

    try:

        url = f"{BASE}/api/recordings/{subject_id}/"

        r = session.get(url, timeout=20)

        if r.status_code != 200:
            return []

        data = r.json()

        return data.get("recordings", [])

    except Exception as e:

        print(f"RECORDING API ERROR: {e}")

        return []

# ================= MAIN BUTTON =================

@app.on_callback_query(filters.regex("^cdsjourney_$"))
async def cdsjourney_callback(client, callback_query):

    lol = await chk_user(
        callback_query,
        callback_query.from_user.id
    )

    if lol == 1:

        await callback_query.message.reply_text(
            "🔒 <b>Premium Feature Locked!</b>\n\n"
            "You don’t have access to use this feature yet.\n"
            "💎 <b>Contact:</b> "
            "<a href='https://t.me/URS_LUCIFER'>LUCIFER</a>",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💬 Contact Admin",
                            url="https://t.me/noobhusir"
                        )
                    ]
                ]
            )
        )

        return

    keyboard = [
        [
            InlineKeyboardButton(
                f"📘 {name}",
                callback_data=f"cds_batch_{cid}"
            )
        ]
        for cid, (name, _) in COURSES.items()
    ]

    await callback_query.message.reply_text(
        "💠 <b>Select a Course:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= COURSE SELECT =================

@app.on_callback_query(filters.regex("^cds_batch_"))
async def cdsjourney_batch_callback(app: Client, callback_query):

    data = callback_query.data.replace("cds_batch_", "")

    if data not in COURSES:

        await callback_query.answer(
            "❌ Invalid course!",
            show_alert=True
        )

        return

    course_title, batch_id = COURSES[data]

    LOGIN_SESSIONS[callback_query.from_user.id] = {
        "course_title": course_title,
        "batch_id": batch_id,
        "step": "email"
    }

    await callback_query.message.reply_text(
        "📧 Send your CDS Journey email:"
    )

# ================= EMAIL HANDLER =================

@app.on_message(filters.text & filters.private)
async def login_handler(client, message):

    user_id = message.from_user.id

    if user_id not in LOGIN_SESSIONS:
        return

    data = LOGIN_SESSIONS[user_id]

    # ================= EMAIL STEP =================

    if data["step"] == "email":

        email = message.text.strip()

        session = create_session()

        ok = send_otp(session, email)

        if not ok:

            await message.reply_text(
                "❌ Failed to send OTP"
            )

            return

        LOGIN_SESSIONS[user_id]["email"] = email
        LOGIN_SESSIONS[user_id]["session"] = session
        LOGIN_SESSIONS[user_id]["step"] = "otp"

        await message.reply_text(
            "📩 OTP sent successfully.\n\n"
            "Now send the OTP:"
        )

        return

    # ================= OTP STEP =================

    if data["step"] == "otp":

        otp = message.text.strip()

        session = data["session"]
        email = data["email"]

        verified = verify_otp(
            session,
            email,
            otp
        )

        if not verified:

            await message.reply_text(
                "❌ Invalid OTP"
            )

            return

        await message.reply_text(
            "✅ Login successful\n\n"
            "⚡ Starting extraction..."
        )

        course_title = data["course_title"]
        batch_id = data["batch_id"]

        subjects = get_subjects(session, batch_id)

        total_links = 0
        subject_count = 0

        safe_name = course_title.replace("/", "_")

        file_name = f"{safe_name}_{user_id}.txt"

        with open(file_name, "w", encoding="utf-8") as f:

            for subject_data in subjects:

                time.sleep(1)

                subject_count += 1

                subject_id = subject_data["id"]

                subject_name = subject_data["subject"]["name"]

                recordings = get_recordings(
                    session,
                    subject_id
                )

                f.write(
                    f"\n========== {subject_name} ==========\n\n"
                )

                for rec in recordings:

                    title = rec.get(
                        "title",
                        "Untitled"
                    ).strip()

                    link = rec.get(
                        "file_url",
                        "NO LINK"
                    ).strip()

                    f.write(
                        f"{title} : {link}\n"
                    )

                    total_links += 1

        # ================= EMPTY CHECK =================

        if total_links == 0 or os.path.getsize(file_name) == 0:

            os.remove(file_name)

            await message.reply_text(
                f"⚠️ No links found for:\n"
                f"<code>{course_title}</code>"
            )

            return

        # ================= CAPTION =================

        caption = (
            f"╭━━━『 💠 𝐋𝐔𝐂𝐈𝐅𝐄𝐑 𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐎𝐑 💠 』━━━╮\n"
            f"📦 <b>Platform:</b> CDS Journey\n"
            f"📚 <b>Course:</b> "
            f"<code>{course_title}</code>\n"
            f"📖 <b>Total Subjects:</b> "
            f"{subject_count}\n"
            f"🔗 <b>Total Links:</b> "
            f"{total_links}\n"
            f"🕒 <b>Extracted:</b> "
            f"{datetime.now().strftime('%d-%m-%Y %I:%M %p')}\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"<b>👑 Maintained by:</b> "
            f"<a href='https://t.me/URS_LUCIFER'>Lucifer</a>"
        )

        # ================= SEND USER =================

        await client.send_document(
            chat_id=message.chat.id,
            document=file_name,
            caption=caption
        )

        # ================= SEND LOG =================

        try:

            await client.send_document(
                chat_id=LOG_CHANNEL,
                document=file_name,
                caption=f"📡 CDS Journey Extract\n\n{caption}"
            )

        except Exception as e:

            print(f"LOG ERROR: {e}")

        # ================= CLEANUP =================

        session.close()

        os.remove(file_name)

        del LOGIN_SESSIONS[user_id]
