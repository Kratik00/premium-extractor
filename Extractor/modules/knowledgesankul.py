import requests
import os
import  asyncio
import json
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

LOG_CHANNEL = PREMIUM_LOGS


# ================= API SETTINGS =================

API_COURSES = "https://class.ingeniumedu.com/getRecentCourses"
API_DETAILS = "https://class.ingeniumedu.com/getCourseDetailsStudent"

HEADERS = {
    "Host": "class.ingeniumedu.com",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJfaWQiOjEwOTMxNTQsImlhdCI6MTc3MDg5Mzc5NX0.tC8_k6s_hx5wnnFEf0-qFip_xe_UpKD4NOLyzawt07E",
    "Seq-Auto-Fetch": "cors",
    "Origin": "https://knowledgesankul.ingeniumedu.com",
    "Connection": "keep-alive",
    "Referer": "https://knowledgesankul.ingeniumedu.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache"
}

PARAMS = {
    "client_id": "2001",
    "client_user_id": "1093154",
    "limit": "100"
}


# ================= GET COURSES =================

def get_courses():

    r = requests.get(API_COURSES, headers=HEADERS, params=PARAMS)
    if r.status_code != 200:
        return []
    
    data = r.json()


    courses = data.get("result", {}).get("assigned_courses", [])

    return [
        (c["course_id"], c["course_title"])
        for c in courses
    ]


# ================= EXTRACT LINKS =================

def extract_links(course_id):

    params = {
        "client_id": "2001",
        "course_id": course_id
    }

    r = requests.get(API_DETAILS, headers=HEADERS, params=params)
    data = r.json()

    sections = data.get("result", {}).get("section_array", [])

    lines = []

    for section in sections:

        subject = section.get("section_name", "Unknown")

        contents = sorted(
            section.get("content_array", []),
            key=lambda x: x.get("priority_order", 0)
        )

        for item in contents:

            topic = item.get("name", "No Title")
            url = None

            # Tests / PDFs
            if item.get("file_url"):
                url = item["file_url"]

            # Drive / External
            elif item.get("file_link", "").startswith("http"):
                url = item["file_link"]

            # YouTube
            elif item.get("file_type") == "youtube":
                url = f"https://youtu.be/{item['file_link']}"

            if url and url != "https":
                lines.append(f"[{subject}] {topic} : {url}")

    # Remove duplicates
    return list(dict.fromkeys(lines))


# ================= SAVE TXT =================

def save_txt(course_title, lines):

    safe_name = "".join(
        x for x in course_title if x.isalnum() or x in " -_"
    )

    file_name = f"{safe_name}.txt"

    with open(file_name, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return file_name


#================== PROCESS =====================

async def process_ingenium(app, message):
    """Show available courses as buttons"""

    await message.reply_text(
        "📡 <b>Fetching available courses...</b> Please wait ⚡"
    )

    courses = await asyncio.to_thread(get_courses)

    keyboard = [
        [InlineKeyboardButton(f"📘 {title}", callback_data=f"ingi_{cid}")]
        for cid, title in courses
    ]

    await message.reply_text(
        "💠 <b>Select a Course to Extract:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUTTON MENU =================

@app.on_callback_query(filters.regex("^ingenium_$"))
async def ingenium_callback(client, callback_query):
    """Triggered when user clicks Ingenium Extractor"""

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
            "⚙️ <b>Initializing Ingenium Extractor...</b>\n\n"
            "Please wait while I load available courses 💫"
        )

        await process_ingenium(client, callback_query.message)

        await processing.delete()

    except Exception as e:
        print(f"Error in ingenium_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)



# ================= EXTRACT CALLBACK =================

@app.on_callback_query(filters.regex("^ingi_"))
async def ingenium_batch_callback(app, callback_query):

    course_id = callback_query.data.replace("ingi_", "")

    await callback_query.answer("⏳ Extracting... please wait")

    try:

        courses = dict(get_courses())
        course_title = courses.get(int(course_id), "Course")

        subject_links = await asyncio.to_thread(extract_links, course_id)

        total_links = len(subject_links)

        file_name = save_txt(course_title, subject_links)

        if total_links == 0 or os.path.getsize(file_name) == 0:
            os.remove(file_name)

            await callback_query.message.edit_text(
                f"⚠️ <b>No links found for:</b> <code>{course_title}</code>"
            )
            return

        caption = (
            f"╭━━━『 💠 𝐋𝐔𝐂𝐈𝐅𝐄𝐑 𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐎𝐑 💠 』━━━╮\n"
            f"📦 <b>Platform:</b> Ingenium\n"
            f"📚 <b>Course:</b> <code>{course_title}</code>\n"
            f"🔗 <b>Total Links:</b> {total_links}\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"<b>👑 Maintained by:</b> <a href='https://t.me/URS_LUCIFER'>Lucifer</a>"
        )

        # Send to user
        await app.send_document(
            chat_id=callback_query.message.chat.id,
            document=file_name,
            caption=caption
        )

        # OPTIONAL → send to logs (same as CDS)
        try:
            await app.send_document(
                chat_id=LOG_CHANNEL,
                document=file_name,
                caption=f"📡 <b>Ingenium Extract</b>\n\n{caption}"
            )
        except Exception as e:
            print(f"Log send error: {e}")

        os.remove(file_name)
        await callback_query.message.delete()

    except Exception as e:
        print("Ingenium extraction error:", e)
        await callback_query.answer("Extraction failed!", show_alert=True)
