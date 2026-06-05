import requests
import os
import asyncio
import json
import aiohttp
import pytz
from datetime import datetime
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import MessageNotModified
from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

LOG_CHANNEL = PREMIUM_LOGS
MY_LOGO_URL = "https://i.ibb.co/BHQ2HsW5/JPEG-20260125-141038-953649353278939736.jpg"

# State management for pagination
user_courses = {}
user_pages = {}

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

# ================= GET COURSES (UNCHANGED) =================
def get_courses():
    r = requests.get(API_COURSES, headers=HEADERS, params=PARAMS)
    if r.status_code != 200:
        return []
    
    data = r.json()
    courses = data.get("result", {}).get("assigned_courses", [])
    return [(c["course_id"], c["course_title"]) for c in courses]

# ================= EXTRACT LINKS (UNCHANGED) =================
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
            if item.get("file_url"):
                url = item["file_url"]
            elif item.get("file_link", "").startswith("http"):
                url = item["file_link"]
            elif item.get("file_type") == "youtube":
                url = f"https://youtu.be/{item['file_link']}"
            if url and url != "https":
                lines.append(f"[{subject}] {topic} : {url}")
    return list(dict.fromkeys(lines))

# ================= SAVE TXT (UNCHANGED) =================
def save_txt(course_title, lines):
    safe_name = "".join(x for x in course_title if x.isalnum() or x in " -_")
    file_name = f"{safe_name}.txt"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return file_name

# ================= THUMBNAIL DOWNLOADER =================
async def download_thumbnail(logo_url: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(logo_url, timeout=15) as resp:
                if resp.status == 200:
                    thumb_path = f"thumb_ingenium_{datetime.now().timestamp()}.jpg"
                    with open(thumb_path, 'wb') as f:
                        f.write(await resp.read())
                    return thumb_path
    except Exception as e:
        print(f"⚠️ Failed to download thumbnail: {e}")
    return None

# ================= PAGINATION UI =================
async def show_courses_page(client, target, courses, page=0):
    is_callback = isinstance(target, CallbackQuery)
    # FIX: For Message objects, from_user is the bot. We must use chat.id to get the real user.
    user_id = target.from_user.id if is_callback else target.chat.id 
    
    total_courses = len(courses)
    courses_per_page = 5
    total_pages = (total_courses + courses_per_page - 1) // courses_per_page if total_courses else 1
    
    start_idx = page * courses_per_page
    end_idx = min(start_idx + courses_per_page, total_courses)
    page_courses = courses[start_idx:end_idx]
    
    keyboard = []
    for i, (cid, title) in enumerate(page_courses):
        display_title = title if len(title) <= 30 else title[:27] + "..."
        keyboard.append([InlineKeyboardButton(f"📘 {display_title}", callback_data=f"ingi_{cid}")])
        
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"ingipage_{page-1}"))
    
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="ingiinfo"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"ingipage_{page+1}"))
        
    keyboard.append(nav_row)
    
    text = (
        f"💠 <b>Select a Course to Extract:</b>\n\n"
        f"📂 <b>Showing:</b> {start_idx + 1}-{end_idx} of {total_courses}\n\n"
        f"Tap a course to extract immediately.\n"
        f"Use ◀️ ▶️ to navigate pages."
    )
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        try:
            await target.message.edit_text(text, reply_markup=reply_markup)
        except MessageNotModified:
            pass
    else:
        await target.reply_text(text, reply_markup=reply_markup)
    
    user_pages[user_id] = page

# ================= PROCESS =================
# FIX: Accept user_id explicitly to avoid saving under the Bot's ID
async def process_ingenium(app, message, user_id: int):
    msg = await message.reply_text("📡 <b>Fetching available courses...</b> Please wait ⚡")
    
    courses = await asyncio.to_thread(get_courses)
    
    if not courses:
        await msg.edit_text("😕 <b>No courses found.</b>")
        return
        
    user_courses[user_id] = courses # Now saves under the correct user ID
    await msg.delete()
    await show_courses_page(app, message, courses, page=0)

# ================= BUTTON MENU =================
@app.on_callback_query(filters.regex("^ingenium_$"))
async def ingenium_callback(client, callback_query):
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
            "⚙️ <b>Initializing KNOWLEDGE SANKUL Extractor...</b>\n\n"
            "Please wait while I load available courses 💫"
        )
        
        # FIX: Get actual user ID from the callback
        user_id = callback_query.from_user.id 
        await process_ingenium(client, callback_query.message, user_id)
        await processing.delete()
    except Exception as e:
        print(f"Error in ingenium_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

# ================= PAGINATION CALLBACKS =================
@app.on_callback_query(filters.regex("^ingipage_"))
async def ingenium_page_callback(client, callback_query):
    page = int(callback_query.data.replace("ingipage_", ""))
    user_id = callback_query.from_user.id
    courses = user_courses.get(user_id, [])
    if not courses:
        await callback_query.answer("Session expired.", show_alert=True)
        return
    await callback_query.answer()
    await show_courses_page(client, callback_query, courses, page)

@app.on_callback_query(filters.regex("^ingiinfo$"))
async def ingenium_info_callback(client, callback_query):
    await callback_query.answer("Use ◀️ ▶️ buttons to change pages", show_alert=False)

# ================= EXTRACT CALLBACK =================
@app.on_callback_query(filters.regex("^ingi_"))
async def ingenium_batch_callback(app, callback_query):
    course_id = callback_query.data.replace("ingi_", "")
    await callback_query.answer("⏳ Extracting... please wait")

    try:
        courses_dict = dict(user_courses.get(callback_query.from_user.id, []))
        if not courses_dict:
            courses_list = await asyncio.to_thread(get_courses)
            courses_dict = dict(courses_list)
            
        course_title = courses_dict.get(int(course_id), "Course")

        subject_links = await asyncio.to_thread(extract_links, course_id)
        total_links = len(subject_links)

        # Smart counting for caption
        youtube_count = 0
        regular_count = 0
        pdf_count = 0
        for line in subject_links:
            url = line.split(" : ")[-1].strip()
            if "youtu.be" in url or "youtube.com" in url:
                youtube_count += 1
            elif url.lower().endswith(('.pdf', '.doc', '.docx')):
                pdf_count += 1
            else:
                regular_count += 1

        file_name = save_txt(course_title, subject_links)

        if total_links == 0 or os.path.getsize(file_name) == 0:
            os.remove(file_name)
            await callback_query.message.edit_text(f"⚠️ <b>No links found for:</b> <code>{course_title}</code>")
            return

        # Download thumbnail
        thumb_path = await download_thumbnail(MY_LOGO_URL)

        # Time & Caption logic
        india_timezone = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(india_timezone)
        time_new = current_time.strftime("%d %b %Y, %I:%M %p")
        
        mention = f"<a href='tg://user?id={callback_query.from_user.id}'>{callback_query.from_user.first_name}</a>"

        caption = (
            f"<blockquote>📚 App: Knowledge Sankul</blockquote>\n\n"
            f"═══════ BATCH DETAILS ═══════\n"
            f"<blockquote>🌟 Batch Name: {course_title}\n"
            f"🆔 Course ID: {course_id}\n"
            f"💸 Price : ₹N/A</blockquote>\n\n"
            f"═══════ LINK SUMMARY ═══════\n"
            f"<blockquote>🔢 Total Links: {total_links}\n"
            f"┠🎥 Videos : {youtube_count + regular_count}\n"
            f"  ┠📺 Regular : {regular_count}\n"
            f"  ┠📻 YouTube : {youtube_count}\n"
            f"┠📁 Documents: {pdf_count}</blockquote>\n\n"
            f"👤 Generated By: {mention}\n"
            f"📅 Generated On: {time_new} IST"
        )  # Ensures zero trailing spaces

        # FIX: Send to user with thumbnail fallback (If Telegram rejects the image size, it sends without it)
        try:
            await app.send_document(
                chat_id=callback_query.message.chat.id,
                document=file_name,
                caption=caption,
                thumb=thumb_path
            )
        except Exception as e:
            print(f"⚠️ Thumbnail failed ({e}), sending without thumbnail...")
            await app.send_document(
                chat_id=callback_query.message.chat.id,
                document=file_name,
                caption=caption
            )

        # Send to logs with same fallback
        try:
            try:
                await app.send_document(
                    chat_id=LOG_CHANNEL,
                    document=file_name,
                    caption=caption,
                    thumb=thumb_path
                )
            except:
                await app.send_document(
                    chat_id=LOG_CHANNEL,
                    document=file_name,
                    caption=fcaption
                )
        except Exception as e:
            print(f"Log send error: {e}")

        # Cleanup files
        os.remove(file_name)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
            
        try:
            await callback_query.message.delete()
        except:
            pass

    except Exception as e:
        print("Ingenium extraction error:", e)
        await callback_query.answer("Extraction failed!", show_alert=True)
