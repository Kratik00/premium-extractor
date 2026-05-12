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
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgzNzkzODEyLCJpYXQiOjE3Nzg2MDk4MTIsImp0aSI6IjczY2E0MDUzMzM3YzQ3Y2E5MzE4NjdmYzQwMjQ5MjFlIiwidXNlcl9pZCI6NDg4MzU2fQ.osCffVxx2sQA8seyRaIu8I4cH4Llxo1mHTTpLt5l5Tw",
    "cookie": "_gid=GA1.2.980171571.1761951418; _ga=GA1.2.1653714809.1760266297; _ga_8ZGD76QEP3=GS2.1.s1761951417$o5$g1$t1761953478$j60$l0$h0; _ga_66NQGZ7KP9=GS2.1.s1761951417$o5$g1$t1761953478$j60$l0$h0; csrftoken=8BdZImygCi5IilEl1fl8gtHcaUNDV30NFeuy8i3PEfVyqHHNp5LIjSPOtD3VWi0R; sessionid=lw2ryog1sxywl86xx6gozazfm2nqggma; AWSALB=ja/SNHhZ5w9SSNad5typfLrUzVSM1c4IZ1SNXp2+4u/ifK+1jDoSMv2L7XMwmR/oL0dQvGjqcD75hHnaNsBTmc5XH62COgeoxKq5PbaEvt213X3uAlr6weFpi5N0",
    "host": "www.cdsjourney.com",
    "priority": "u=0, i",
    "referer": "https://www.cdsjourney.com/",
    "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
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

# ================= SESSION =================

def create_session():

    session = requests.Session()

    session.headers.update(HEADERS)

    return session

# ================= GET SUBJECTS =================

def get_subjects(session, batch_id):

    try:

        url = f"https://www.cdsjourney.com/api/batch-subject/{batch_id}/"

        r = session.get(url, timeout=20)

        print("\n[+] SUBJECT STATUS:", r.status_code)
        print("\n[+] SUBJECT RESPONSE:")
        print(r.text)

        if r.status_code != 200:
            return []

        data = r.json()

        return data.get("list", [])

    except Exception as e:

        print(f"SUBJECT API ERROR: {e}")

        return []

# ================= GET RECORDINGS =================

def get_recordings(session, subject_id):

    try:

        url = f"https://www.cdsjourney.com/api/recordings/{subject_id}/"

        r = session.get(url, timeout=20)

        print("\n[+] RECORDING STATUS:", r.status_code)
        print("\n[+] RECORDING RESPONSE:")
        print(r.text)

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

    await callback_query.answer(
        "⏳ Extracting... please wait"
    )

    session = create_session()

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
                    f"[{subject_name}]{title}: {link}\n"
                )

                total_links += 1

    # ================= EMPTY CHECK =================

    if total_links == 0 or os.path.getsize(file_name) == 0:

        os.remove(file_name)

        await callback_query.message.reply_text(
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
        f"╰━━━━━━━━━━━━━━━━━━━━━━╯"
    )

    # ================= SEND USER =================

    await app.send_document(
        chat_id=callback_query.message.chat.id,
        document=file_name,
        caption=caption
    )

    # ================= SEND LOG =================

    try:

        await app.send_document(
            chat_id=LOG_CHANNEL,
            document=file_name,
            caption=f"📡 CDS Journey Extract\n\n{caption}"
        )

    except Exception as e:

        print(f"LOG ERROR: {e}")

    # ================= CLEANUP =================

    session.close()

    os.remove(file_name)

    await callback_query.message.delete()
