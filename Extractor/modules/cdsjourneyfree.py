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

HEADERS = {
    "accept": "application/json",
    "accept-encoding": "gzip",
    "user-agent": "Dart/3.10 (dart:io)"
}

COURSES = {
    "course1": ("GOLF OTA BATCH (CDS-2 2026)", 44),
    "course2": ("GOLF MATH BATCH (CDS-2 2026)", 46),
    "course3": ("HOTEL BATCH (NDA-2 2026)", 45),
    "course4": ("FOXTROT BATCH (AFCAT 2 2026)", 47),
    "course5": ("ECHO BATCH (AFCAT 2 2026)", 43),
    "course6": ("CAPF Paper 1 + Paper 2 Delta batch (CAPF 2026)", 39),
    "course7": ("CAPF Paper 2 Delta batch (CAPF 2026)", 40),
}

LOGIN_SESSIONS = {}

# ================= SESSION =================

def create_session():

    session = requests.Session()

    session.headers.update(HEADERS)

    return session

# ================= LOGIN =================

def send_otp(session, email):

    try:

        url = "https://www.cdsjourney.com/api/login_or_register/"

        payload = {
            "email": email
        }

        headers = {
            "content-type": "application/x-www-form-urlencoded; charset=utf-8",
            "user-agent": "Dart/3.10 (dart:io)",
            "accept-encoding": "gzip"
        }

        r = session.post(
            url,
            data=payload,
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

        url = "https://www.cdsjourney.com/api/verify_otp/"

        payload = {
            "email": email,
            "otp": otp,
            "first-name": "User",
            "mobile": "9999999999"
        }

        headers = {
            "content-type": "application/x-www-form-urlencoded; charset=utf-8",
            "user-agent": "Dart/3.10 (dart:io)",
            "accept-encoding": "gzip"
        }

        r = session.post(
            url,
            data=payload,
            headers=headers,
            timeout=20
        )

        print("\n[+] VERIFY STATUS:", r.status_code)
        print("[+] VERIFY RESPONSE:", r.text)

        if r.status_code != 200:
            return False

        data = r.json()

        access_token = data.get("access_token")

        if not access_token:
            return False

        session.headers.update({
            "authorization": f"Bearer {access_token}"
        })

        print("\n[+] JWT TOKEN LOADED")

        return True

    except Exception as e:

        print(f"VERIFY ERROR: {e}")

        return False

# ================= API =================

def get_subjects(session, batch_id):

    try:

        url = f"https://www.cdsjourney.com/api/batch-subject/{batch_id}/"

        r = session.get(url, timeout=20)

        print("\n[+] SUBJECT STATUS:", r.status_code)

        if r.status_code != 200:
            return []

        data = r.json()

        return data.get("list", [])

    except Exception as e:

        print(f"SUBJECT API ERROR: {e}")

        return []


def get_recordings(session, subject_id):

    try:

        url = f"https://www.cdsjourney.com/api/recordings/{subject_id}/"

        r = session.get(url, timeout=20)

        print("\n[+] RECORDING STATUS:", r.status_code)

        if r.status_code != 200:
            return []

        data = r.json()

        return data.get("recordings", [])

    except Exception as e:

        print(f"RECORDING API ERROR: {e}")

        return []

# ================= SHOW COURSES =================

async def show_courses(message):

    text = "📚 <b>CDS Journey Courses</b>\n\n"

    for i, (_, data) in enumerate(COURSES.items(), start=1):

        text += f"<b>{i}.</b> {data[0]}\n"

    text += (
        "\n━━━━━━━━━━━━━━\n"
        "📥 Send indexes separated with <code>&</code>\n\n"
        "Example:\n"
        "<code>1&3&5</code>"
    )

    await message.reply_text(text)

# ================= MAIN BUTTON =================

@app.on_callback_query(filters.regex("^cdsjourney_$"))
async def cdsjourney_callback(client, callback_query):

    user_id = callback_query.from_user.id

    lol = await chk_user(
        callback_query,
        user_id
    )

    if lol == 1:

        await callback_query.message.reply_text(
            "🔒 <b>Premium Feature Locked!</b>\n\n"
            "💎 Contact Admin to upgrade.",
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

    if user_id in LOGIN_SESSIONS and LOGIN_SESSIONS[user_id].get("logged_in"):

        await show_courses(callback_query.message)

        return

    LOGIN_SESSIONS[user_id] = {
        "step": "email"
    }

    await callback_query.message.reply_text(
        "📧 Send your CDS Journey email:"
    )

# ================= LOGIN FLOW =================

@app.on_message(filters.text & filters.private & ~filters.regex("^/"))
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

        verified = verify_otp(
            session,
            data["email"],
            otp
        )

        if not verified:

            await message.reply_text(
                "❌ Invalid OTP"
            )

            return

        LOGIN_SESSIONS[user_id]["logged_in"] = True
        LOGIN_SESSIONS[user_id]["step"] = "select"

        await message.reply_text(
            "✅ Login successful"
        )

        await show_courses(message)

        return

    # ================= COURSE SELECT =================

    if data["step"] == "select":

        raw = message.text.strip()

        if "&" not in raw and not raw.isdigit():
            return

        processing = await message.reply_text(
            "⚡ Processing your request..."
        )

        indexes = raw.split("&")

        session = data["session"]

        selected = []

        for x in indexes:

            try:

                idx = int(x.strip())

                key = list(COURSES.keys())[idx - 1]

                selected.append(COURSES[key])

            except:
                pass

        if not selected:

            await processing.edit_text(
                "❌ Invalid indexes"
            )

            return

        for course_title, batch_id in selected:

            try:

                subjects = get_subjects(
                    session,
                    batch_id
                )

                total_links = 0
                subject_count = 0

                safe_name = course_title.replace("/", "_")

                file_name = f"{safe_name}.txt"

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
                                f"[{subject_name}] {title}: {link}\n"
                            )

                            total_links += 1

                if total_links == 0:

                    if os.path.exists(file_name):
                        os.remove(file_name)

                    continue

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
                    f"╰━━━━━━━━━━━━━━━━━━━━━━╯"
                )

                await client.send_document(
                    chat_id=message.chat.id,
                    document=file_name,
                    caption=caption
                )

                try:

                    await client.send_document(
                        chat_id=LOG_CHANNEL,
                        document=file_name,
                        caption=f"📡 CDS Journey Extract\n\n{caption}"
                    )

                except Exception as e:

                    print(f"LOG ERROR: {e}")

                os.remove(file_name)

            except Exception as e:

                print(f"EXTRACTION ERROR: {e}")

                await message.reply_text(
                    f"❌ Failed extracting:\n"
                    f"<code>{course_title}</code>"
                )

        session.close()

        del LOGIN_SESSIONS[user_id]

        await processing.delete()

        try:
            await message.delete()
        except:
            pass
