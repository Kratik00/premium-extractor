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
    "authority": "www.cdsjourney.com",
    "method": "GET",
    "scheme": "https",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "cookie": "_gid=GA1.2.980171571.1761951418; _ga=GA1.2.1653714809.1760266297; _ga_8ZGD76QEP3=GS2.1.s1761951417$o5$g1$t1761953478$j60$l0$h0; _ga_66NQGZ7KP9=GS2.1.s1761951417$o5$g1$t1761953478$j60$l0$h0; csrftoken=8BdZImygCi5IilEl1fl8gtHcaUNDV30NFeuy8i3PEfVyqHHNp5LIjSPOtD3VWi0R; sessionid=lw2ryog1sxywl86xx6gozazfm2nqggma; AWSALB=ja/SNHhZ5w9SSNad5typfLrUzVSM1c4IZ1SNXp2+4u/ifK+1jDoSMv2L7XMwmR/oL0dQvGjqcD75hHnaNsBTmc5XH62COgeoxKq5PbaEvt213X3uAlr6weFpi5N0",
    "priority": "u=0, i",
    "referer": "https://www.cdsjourney.com/",
    "sec-ch-ua": "\"Google Chrome\";v=\"141\", \"Not?A_Brand\";v=\"8\", \"Chromium\";v=\"141\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
}

COURSES = {
    "course1": ("Bravo GAT batch (NDA 1 2026)", "https://www.cdsjourney.com/course-detail/bravo-gat-batch-nda-1-2026/"),
    "course2": ("Bravo MATH batch (NDA 1 2026)", "https://www.cdsjourney.com/course-detail/bravo-math-batch-nda-1-2026/"),
    "course3": ("Charlie Batch (AFCAT 1 2026)", "https://www.cdsjourney.com/course-detail/charlie-batch-afcat-1-2026/"),
    "course4": ("CAPF Paper 1 + 2 Delta (2026)", "https://www.cdsjourney.com/course-detail/delta-capf-batch-capf-2026-paper-1-paper-2/"),
    "course5": ("CAPF Paper 2 Delta (2026)", "https://www.cdsjourney.com/course-detail/delta-capf-batch-capf-2026-paper-2-exclusive/"),
    "course6": ("Alpha OTA batch (CDS 1 2026)", "https://www.cdsjourney.com/course-detail/alpha-ota-batch-cds-1-2026/"),
    "course7": ("Alpha MATH batch (CDS 1 2026)", "https://www.cdsjourney.com/course-detail/alpha-math-batch-cds-1-2026/"),
    "course8": ("Echo Batch (AFCAT 2 2026)", "https://www.cdsjourney.com/course-detail/echo-batch-afcat-2-2026/"),
    "course9": ("Golf SSB Batch", "https://www.cdsjourney.com/course-detail/golf-ssb-batch/"),
    "coursea": ("YANKEE BATCH (AFCAT 2 2025)", "https://www.cdsjourney.com/course-detail/yankee-batch-afcat-2-2025/"),
    "courseb": (X-RAY BATCH (NDA 2 2025)", "https://www.cdsjourney.com/course-detail/xray-batch-nda-2-2025/"),
    "coursec": (ZULU BATCH (CDS 2 2025)", "https://www.cdsjourney.com/course-detail/zulu-ota-batch-cds-2-2025/")
}

# ---------------- SCRAPING UTILS ----------------
def get_subject_ids(url):
    """Extract subject IDs from a course page"""
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.content, "html.parser")
    ids = set()
    for a in soup.find_all("a", href=True):
        m = re.search(r"/student-dashboard/subject/(\d+)/", a["href"])
        if m:
            ids.add(m.group(1))
    return list(ids)

def scrape_subject(subject_id):
    """Extract lessons and links from a subject"""
    url = f"https://www.cdsjourney.com/student-dashboard/subject/{subject_id}/"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.content, "html.parser")

    subject_name = soup.select_one("h3.card-title")
    subject_name = subject_name.get_text(strip=True) if subject_name else f"Subject {subject_id}"

    titles = []
    for p in soup.select('.card-header p'):
        t = re.sub(r"^\d+\.\s*", "", p.get_text(strip=True))
        if t:
            titles.append(t)

    zoom_links = re.findall(r"if\s*\(videoId === '(\d+)'\).*?zoomLink\s*=\s*'(.*?)'", r.text, re.S)

    lessons = []
    for i, t in enumerate(titles, 1):
        link = next((l for vid, l in zoom_links if int(vid) == i), None)
        lessons.append((t, link))

    return subject_name, lessons

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

    course_title, course_url = COURSES[data]
    await callback_query.answer("⏳ Extracting... please wait")

    # Scrape the course
    subject_ids = get_subject_ids(course_url)
    total_links = 0
    file_name = f"{course_title}.txt"

    with open(file_name, "w", encoding="utf-8") as f:
        for sid in subject_ids:
            subject, lessons = scrape_subject(sid)
            for title, link in lessons:
                f.write(f"{title}: {link or 'NO LINK FOUND'}\n")
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
