import asyncio
import io
import os
import re
import aiohttp
import pytz
from datetime import datetime
from urllib.parse import quote
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import MessageNotModified
from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d %b %Y, %I:%M %p")

# ===================== CONFIG & STATE ===================== #
# Study IQ Public Course List Source (No Login)
IQ_COURSES_URL = "https://raw.githubusercontent.com/dev-raj009/Vipiq/refs/heads/main/valid_courses.json"

MY_LOGO_URL = "https://i.ibb.co/BHQ2HsW5/JPEG-20260125-141038-953649353278939736.jpg"

user_batches = {}
user_pages = {}  # Track current page for each user

# ===================== HELPERS ===================== #
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|₹]', "", name).strip() + ".txt"

def encode_url(url: str) -> str:
    if not url:
        return url
    parts = url.split('/', 3)
    if len(parts) < 4:
        return url
    return parts[0] + '//' + parts[2] + '/' + quote(parts[3])

async def fetch_json_async(session, url: str):
    try:
        async with session.get(url, timeout=20) as r:
            if r.status == 200:
                return await r.json()
            return None
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return None

async def download_thumbnail(logo_url: str) -> str:
    """Download logo image to use as thumbnail"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(logo_url, timeout=15) as resp:
                if resp.status == 200:
                    thumb_path = f"thumb_{datetime.now().timestamp()}.jpg"
                    with open(thumb_path, 'wb') as f:
                        f.write(await resp.read())
                    return thumb_path
    except Exception as e:
        print(f"⚠️ Failed to download thumbnail: {e}")
    return None

# ===================== STUDY IQ EXTRACTION LOGIC ===================== #
async def scrape_batch_iq(course_id: str):
    all_results = {} 
    video_count = 0
    pdf_count = 0
    youtube_count = 0

    async with aiohttp.ClientSession() as session:
        # 1. Fetch Master Details
        url_master = f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={course_id}&languageId="
        master_data = await fetch_json_async(session, url_master)
        
        if not master_data or "data" not in master_data:
            return all_results, video_count, pdf_count, youtube_count

        topics = master_data["data"]
        
        # Helper to process items (videos and pdfs)
        async def process_items(items, label):
            nonlocal video_count, pdf_count, youtube_count
            lines = []
            for item in items:
                title = item.get("name", "Untitled").strip()
                video_url = item.get("videoUrl")
                cid = item.get("contentId")
                
                if video_url:
                    lines.append(f"[{label}] Video | {title} : {video_url}")
                    video_count += 1
                    if "youtube.com" in video_url or "youtu.be" in video_url:
                        youtube_count += 1
                
                # Fetch PDFs via Lesson API
                if cid:
                    try:
                        url_lesson = f"https://backend.studyiq.net/app-content-ws/api/lesson/data?lesson_id={cid}&courseId={course_id}"
                        nresp = await fetch_json_async(session, url_lesson)
                        if nresp and nresp.get("options"):
                            for opt in nresp["options"]:
                                for ud in (opt.get("urls") or []):
                                    n_name = ud.get("name", "")
                                    n_url = ud.get("url", "")
                                    if n_name and n_url:
                                        n_url = encode_url(n_url)
                                        lines.append(f"[{label}] PDF | {n_name} : {n_url}")
                                        pdf_count += 1
                    except Exception as e:
                        print(f"⚠️ Error fetching lesson {cid}: {e}")
            return lines

        # 2. Iterate Topics
        for topic in topics:
            t_id = topic.get("contentId")
            topic_name = topic.get("name", "Unknown Topic")
            
            if not t_id:
                continue
                
            url_parent = f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={course_id}&languageId=&parentId={t_id}"
            parent_data = await fetch_json_async(session, url_parent)
            
            if not parent_data or "data" not in parent_data:
                continue
                
            sub_items = parent_data["data"]
            has_subtopic = any(x.get("subFolderOrderId") is not None for x in sub_items)
            
            if topic_name not in all_results:
                all_results[topic_name] = {}
                
            if not has_subtopic:
                if "General" not in all_results[topic_name]:
                    all_results[topic_name]["General"] = []
                lines = await process_items(sub_items, topic_name)
                all_results[topic_name]["General"].extend(lines)
            else:
                for sub in sub_items:
                    p_id = sub.get("contentId")
                    sub_name = sub.get("name", topic_name)
                    label = f"{topic_name} > {sub_name}"
                    
                    if not p_id:
                        continue
                        
                    url_sub = f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={course_id}&languageId=&parentId={t_id}/{p_id}"
                    video_data = await fetch_json_async(session, url_sub)
                    
                    if video_data and "data" in video_data:
                        if sub_name not in all_results[topic_name]:
                            all_results[topic_name][sub_name] = []
                        lines = await process_items(video_data["data"], label)
                        all_results[topic_name][sub_name].extend(lines)

    return all_results, video_count, pdf_count, youtube_count

# ===================== PAGINATION UI ===================== #
async def show_batches_page(client, target, batches, page=0):
    is_callback = isinstance(target, CallbackQuery)
    user_id = target.from_user.id if is_callback else target.from_user.id
    
    total_batches = len(batches)
    batches_per_page = 10
    total_pages = (total_batches + batches_per_page - 1) // batches_per_page if total_batches else 1
    
    start_idx = page * batches_per_page
    end_idx = min(start_idx + batches_per_page, total_batches)
    page_batches = batches[start_idx:end_idx]
    
    keyboard = []
    for i, batch in enumerate(page_batches):
        actual_index = start_idx + i + 1
        title = batch.get('title', 'Unknown')
        if len(title) > 30:
            title = title[:27] + "..."
        keyboard.append([InlineKeyboardButton(f"{actual_index}. {title}", callback_data=f"iq_batch_{batch['id']}")])
    
    # Navigation buttons with page info
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"iq_page_{page-1}"))
    
    # Show current page indicator
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="iq_page_info"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"iq_page_{page+1}"))
    
    keyboard.append(nav_row)
    
    # Show range of batches displayed
    display_info = ""
    if total_batches > 0:
        display_info = f"📂 <b>Showing:</b> {start_idx + 1}-{end_idx} of {total_batches}\n\n"
    
    text = (
        f"📘 <b>Select a Study IQ Batch to Extract:</b>\n\n"
        f"{display_info}"
        f"Tap a batch number to extract immediately.\n"
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
    
    # Save current page
    user_pages[user_id] = page

# ===================== MAIN CALLBACK ===================== #
@app.on_callback_query(filters.regex("^studyiq_$"))
async def studyiq_callback(client, callback_query):
    lol = await chk_user(callback_query, callback_query.from_user.id)
    if lol == 1:
        await callback_query.message.reply_text(
            "🔒 <b>Premium Feature Locked!</b>\n\n"
            "You don't have access to use this feature yet.\n"
            "💎 <b>Contact:</b> <a href='https://t.me/URS_LUCIFER'>LUCIFER</a> to upgrade.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💬 Contact Admin", url="https://t.me/noobhusir")]]
            )
        )
        return

    try:
        processing_msg = await callback_query.message.reply_text(
            "⚙️ <b>Initializing Study IQ Extractor...</b>\n\n"
            "Fetching available batches 💫"
        )
        
        user_id = callback_query.from_user.id
        await process_studyiq(client, callback_query.message, user_id)
        await processing_msg.delete()
        
    except Exception as e:
        print(f"Error in studyiq_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

# ===================== FETCH BATCH LIST ===================== #
async def process_studyiq(app: Client, message, user_id: int):
    waiting_msg = await message.reply_text("📡 <b>Fetching Study IQ batches...</b> Please wait ⚡")

    async with aiohttp.ClientSession() as session:
        batches = await fetch_json_async(session, IQ_COURSES_URL)
    
    if not batches or not isinstance(batches, list):
        await waiting_msg.edit_text("😕 <b>No batches found.</b>")
        return

    user_batches[user_id] = batches
    user_pages[user_id] = 0
    
    await waiting_msg.delete()
    await show_batches_page(app, message, batches, page=0)

# ===================== PAGE NAVIGATION ===================== #
@app.on_callback_query(filters.regex("^iq_page_(\d+)$"))
async def iq_page_callback(client, callback_query):
    page = int(callback_query.data.split("_")[2])
    user_id = callback_query.from_user.id
    batches = user_batches.get(user_id, [])
    
    if not batches:
        await callback_query.answer("Session expired. Restart.", show_alert=True)
        return
    
    await callback_query.answer()
    await show_batches_page(client, callback_query, batches, page)

@app.on_callback_query(filters.regex("^iq_page_info$"))
async def iq_page_info_callback(client, callback_query):
    await callback_query.answer("Use ◀️ ▶️ buttons to change pages", show_alert=False)

# ===================== EXTRACT BATCH ===================== #
@app.on_callback_query(filters.regex("^iq_batch_"))
async def studyiq_batch_callback(app: Client, callback_query):
    await callback_query.answer("⏳ Extracting... please wait")
    batch_id = callback_query.data.replace("iq_batch_", "")
    chat_id = callback_query.message.chat.id
    
    try:
        await extract_and_send_batch_iq(app, chat_id, batch_id, callback_query.from_user)
    except Exception as e:
        print(f"❌ Extraction Error: {e}")
        await callback_query.message.reply_text(f"❌ <b>Error:</b>\n<code>{str(e)}</code>")
    
    try:
        await callback_query.message.delete()
    except:
        pass

async def extract_and_send_batch_iq(app: Client, chat_id: int, batch_id: str, user):
    # Fetch batch details from cached list
    batches = user_batches.get(user.id, [])
    batch_data = next((b for b in batches if str(b.get("id")) == str(batch_id)), {})
    
    batch_name = batch_data.get("title", "Unknown Batch")
    thumbnail_url = ""  # Study IQ JSON doesn't contain banner URLs
    price = batch_data.get("price", "N/A")
    if price and price != "N/A":
        price = f"₹{price}"
    else:
        price = "Free"

    processing_msg = await app.send_message(chat_id, "⏳ <b>Extracting content...</b>")
    
    try:
        all_results, video_count, pdf_count, youtube_count = await scrape_batch_iq(batch_id)

        if not all_results:
            await processing_msg.edit_text("😕 <b>No content found in this batch.</b>")
            return

        # Build output file
        file_content = ""
        if thumbnail_url:
            file_content += f"{batch_name}[Batch Thumbnail]: {thumbnail_url}\n\n"
            
        for topic_name, sections in all_results.items():
            for section_name, links in sections.items():
                for link in links:
                    file_content += f"{link}\n"
            
        file_bytes = io.BytesIO(file_content.encode("utf-8"))
        file_bytes.name = sanitize_filename(batch_name)

        # Download thumbnail
        thumb_path = await download_thumbnail(MY_LOGO_URL)

        mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
        total_links = video_count + pdf_count
        regular_count = video_count - youtube_count
        caption = (
            f"<blockquote>📚 App: Study IQ</blockquote>\n\n"
            f"═══════ BATCH DETAILS ═══════\n"
            f"<blockquote>🌟 Batch Name: {batch_name}\n"
            f"🆔 Batch ID: {batch_id}\n"
            f"💸 Price : {price}</blockquote>\n\n"
            f"═══════ LINK SUMMARY ═══════\n"
            f"<blockquote>🔢 Total Links: {total_links}\n"
            f"┠🎥 Videos : {video_count}\n"
            f"  ┠📺 Regular : {regular_count}\n"
            f"  ┠📻 YouTube : {youtube_count}\n"
            f"┠📁 Documents: {pdf_count}</blockquote>\n\n"
            f"👤 Generated By: {mention}\n"
            f"📅 Generated On: {time_new} IST"
        )

        # Send document with thumbnail
        await app.send_document(
            chat_id=chat_id, 
            document=file_bytes, 
            caption=caption,
            thumb=thumb_path
        )

        # Send to log channel
        try:
            file_bytes.seek(0)
            await app.send_document(
                chat_id=PREMIUM_LOGS,
                document=file_bytes,
                caption=caption,
                thumb=thumb_path
            )
        except Exception as e:
            print(f"⚠️ Error sending to log: {e}")

        await processing_msg.delete()
        
    finally:
        # Clean up thumbnail file
        if os.path.exists(thumb_path if 'thumb_path' in locals() else ""):
            try:
                os.remove(thumb_path)
            except:
                pass