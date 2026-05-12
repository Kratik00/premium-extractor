import re
import requests
import json
import os
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

# ---------------- GLOBAL SETTINGS ----------------
LOG_CHANNEL = PREMIUM_LOGS
HEADERS = {
    "accept": "application/json",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,hi;q=0.6,pt;q=0.5,mr;q=0.4",
    
    "authorization": "Bearer YOUR_TOKEN",

    "cache-control": "max-age=0",

    "cookie": "_ga_66NQGZ7KP9=GS2.1.s1774946517$o6$g1$t1774951029$j46$l0$h0; _ga_8ZGD76QEP3=GS2.1.s1774946517$o6$g1$t1774951031$j44$l0$h0; _ga=GA1.1.143849368.1758642086; _ga_M6LMHSSMSF=GS2.1.s1774966216$o5$g1$t1774966216$j60$l0$h0; _ga_FQXYQFWSCS=GS2.1.s1774966216$o5$g1$t1774966216$j60$l0$h0; csrftoken=Qq2SCtr4bqPmTu8PzfzpZGvhxA5C4hpqYg9L2bUVysacNjeK0OI6Ynn2erAYYTh3; sessionid=51r64ellnbub4tp0ynt5suhd3401zp2c; AWSALB=6pABHq1w4jKW/gDwrObgEtecjZ1xHF+i1ZG0tqpMCm2NtiHdgnfuMi/0QXaFguuecNu91G+n9+oTQoBc/E4yrz0Of0CAUdtmk4siVM/beE/Qvn4wAMwUCIgNEGYB",

    "priority": "u=0, i",

    "referer": "https://www.cdsjourney.com/",

    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',

    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",

    "upgrade-insecure-requests": "1",

    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
}

COURSES = {
    "course1": ("Bravo GAT batch (NDA 1 2026)", 45),
    "course2": ("Bravo MATH batch (NDA 1 2026)", 46),
}

# ---------------- SCRAPING UTILS ----------------
def get_subjects(batch_id):
    """Fetch subjects using API"""

    url = f"https://www.cdsjourney.com/api/batch-subject/{batch_id}/"

    r = requests.get(url, headers=HEADERS)

    if r.status_code != 200:
        return []

    data = r.json()

    return data.get("list", [])

def get_recordings(subject_id):
    """Fetch recordings using API"""

    url = f"https://www.cdsjourney.com/api/recordings/{subject_id}/"

    r = requests.get(url, headers=HEADERS)

    if r.status_code != 200:
        return []

    data = r.json()

    return data.get("recordings", [])

# ---------------- CALLBACKS ----------------
@app.on_callback_query(filters.regex("^cdsjourney_$"))
async def cdsjourney_callback(client, callback_query):
    """Triggered when user clicks CDS Journey"""
    lol = await chk_user(callback_query, callback_query.from_user.id)
    if lol == 1:
        await callback_query.message.reply_text(
            "🔒 <b>Premium Feature Locked!</b>\n\n"
            "You don’t have access to use this feature yet.\n"
            "💎 <b>Contact:</b> <a href='https://t.me/URS_LUCIFER'>LUCIFER</a> to upgrade your plan.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💬 Contact Admin", url="https://t.me/noobhusir")]]
            )
        )
        return

    try:
        processing = await callback_query.message.reply_text(
            "⚙️ <b>Initializing CDS Journey Extractor...</b>\n\nPlease wait while I load available batches 💫"
        )

        await process_cdsjourney(client, callback_query.message)
        await processing.delete()

    except Exception as e:
        print(f"Error in cdsjourney_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)


async def process_cdsjourney(app: Client, message):
    """Show available courses as buttons"""
    await message.reply_text("📡 <b>Fetching available courses...</b> Please wait ⚡")

    keyboard = [
        [InlineKeyboardButton(f"📘 {name}", callback_data=f"cds_batch_{cid}")]
        for cid, (name, _) in COURSES.items()
    ]

    await message.reply_text(
        "💠 <b>Select a Course to Extract:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_callback_query(filters.regex("^cds_batch_"))
async def cdsjourney_batch_callback(app: Client, callback_query):
    data = callback_query.data.replace("cds_batch_", "")
    if data not in COURSES:
        await callback_query.answer("❌ Invalid course!", show_alert=True)
        return

    course_title, batch_id = COURSES[data]
    await callback_query.answer("⏳ Extracting... please wait")

    # Scrape the course
    subjects = get_subjects(batch_id)
    total_links = 0
    file_name = f"{course_title}.txt"

    with open(file_name, "w", encoding="utf-8") as f:
        for subject_data in subjects:

            subject_id = subject_data["id"]
            subject_name = subject_data["subject"]["name"]

            recordings = get_recordings(subject_id)
            for rec in recordings:

                title = rec.get("title", "Untitled")
                link = rec.get("file_url", "NO LINK")

                f.write(f"{title}: {link}\n")

                total_links += 1
    if total_links == 0 or os.path.getsize(file_name) == 0:
        os.remove(file_name)
        await callback_query.message.edit_text(
            f"⚠️ <b>No links found for:</b> <code>{course_title}</code>"
        )
        return

    caption = (
        f"╭━━━『 💠 𝐋𝐔𝐂𝐈𝐅𝐄𝐑 𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐎𝐑 💠 』━━━╮\n"
        f"📦 <b>Platform:</b> CDS Journey\n"
        f"📚 <b>Course:</b> <code>{course_title}</code>\n"
        f"🔗 <b>Total Links:</b> {total_links}\n"
        f"🕒 <b>Extracted:</b> {datetime.now().strftime('%d-%m-%Y %I:%M %p')}\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"<b>👑 Maintained by:</b> <a href='https://t.me/URS_LUCIFER'>Lucifer</a>"
    )

    # Send file to user
    await app.send_document(
        chat_id=callback_query.message.chat.id,
        document=file_name,
        caption=caption
    )

    # Send file to log channel
    try:
        await app.send_document(
            chat_id=LOG_CHANNEL,
            document=file_name,
            caption=f"📡 <b>CDS Journey Extract</b>\n\n{caption}"
        )
    except Exception as e:
        print(f"⚠️ Error sending to log channel: {e}")

    os.remove(file_name)
    await callback_query.message.delete()
