import asyncio
import io
import os
import re
import json
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
BASE_URL = "https://gdgoenkaratia.com"
EXTRA_JSON_FILE = "Extractor/modules/extra_batches.json"

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

# ===================== BATCH MERGING LOGIC ===================== #
def normalize_batch(b: dict) -> dict:
    """
    Normalizes keys from the external JSON to match the API format 
    expected by the rest of your code (title, banner, discountPrice).
    """
    return {
        "id": b.get("id"),
        "title": b.get("title") or b.get("name", "Unknown Batch"),
        "banner": b.get("banner") or b.get("banner_url", ""),
        "bannerSquare": b.get("bannerSquare", ""),
        "discountPrice": b.get("discountPrice") or b.get("discounted_price"),
        "price": b.get("price")
    }

async def get_all_batches():
    """
    Fetches batches from the live API and merges them with the external JSON file.
    Prevents duplicates by prioritizing the live API data.
    """
    api_batches = []
    async with aiohttp.ClientSession() as session:
        data_info = await fetch_json_async(session, f"{BASE_URL}/api/courses/active?userId=2054598")
        if data_info and "data" in data_info:
            api_batches = [normalize_batch(b) for b in data_info["data"] if b.get("id")]
    
    extra_batches = []
    try:
        # Read the external JSON file
        with open(EXTRA_JSON_FILE, "r", encoding="utf-8") as f:
            extra_data = json.load(f)
            if "batches" in extra_data:
                extra_batches = [normalize_batch(b) for b in extra_data["batches"] if b.get("id")]
    except FileNotFoundError:
        print(f"⚠️ {EXTRA_JSON_FILE} not found. Using API data only.")
    except Exception as e:
        print(f"⚠️ Error reading {EXTRA_JSON_FILE}: {e}")

    # Merge dictionaries to avoid duplicate IDs (API takes priority)
    merged_dict = {}
    for b in api_batches:
        merged_dict[b["id"]] = b
    for b in extra_batches:
        if b["id"] not in merged_dict:
            merged_dict[b["id"]] = b
            
    return list(merged_dict.values())

# ===================== SCRAPING LOGIC ===================== #
async def scrape_batch(course_id: str):
    all_results = {} 
    video_count = 0
    pdf_count = 0
    youtube_count = 0

    async with aiohttp.ClientSession() as session:
        url_topics = f"{BASE_URL}/api/topic-and-section?courseId={course_id}"
        data_topics = await fetch_json_async(session, url_topics)
        
        if not data_topics or "data" not in data_topics:
            return all_results, video_count, pdf_count, youtube_count

        topics = data_topics["data"].get("topics", [])
        
        async def fetch_topic_classes(topic_name, topic_id):
            url_classes = f"{BASE_URL}/api/topics/{topic_id}/classes?courseId={course_id}"
            try:
                data = await fetch_json_async(session, url_classes)
                return topic_name, data
            except Exception as e:
                print(f"⚠️ Error fetching classes for {topic_name}: {e}")
                return topic_name, None

        tasks = [
            fetch_topic_classes(topic.get("topicName", "Unknown Topic"), topic.get("topicId"))
            for topic in topics if topic.get("topicId")
        ]
        
        results = await asyncio.gather(*tasks)
        
        for topic_name, data in results:
            if not data or "data" not in data:
                continue
            
            classes = data["data"].get("classes", [])
            
            for cls in classes:
                title = cls.get("title", "No Title").strip()
                
                section_name = "General"
                if cls.get("internalSection") and cls["internalSection"].get("sectionName"):
                    section_name = cls["internalSection"]["sectionName"].strip()
                
                if topic_name not in all_results:
                    all_results[topic_name] = {}
                if section_name not in all_results[topic_name]:
                    all_results[topic_name][section_name] = []
                
                # --- Extract Video ---
                video_url = None
                if cls.get("class_link"):
                    video_url = cls.get("class_link")
                else:
                    recs = cls.get("mp4Recordings", [])
                    if recs:
                        preferred = next((r for r in recs if r.get("quality") == "720p" and r.get("url")), None)
                        video_url = preferred["url"] if preferred else recs[0].get("url")
                
                if title and video_url:
                    all_results[topic_name][section_name].append(f"({topic_name}) {title}: {video_url}")
                    video_count += 1
                    if "youtube.com" in video_url or "youtu.be" in video_url:
                        youtube_count += 1
                
                # --- Extract PDFs ---
                pdf_items = cls.get("classPdf", [])
                if not pdf_items:
                    for key in ["pdfs", "attachments", "notes", "documents", "studyMaterials"]:
                        if cls.get(key) and isinstance(cls.get(key), list):
                            pdf_items.extend(cls[key])
                
                for pdf in pdf_items:
                    pdf_title = pdf.get("name") or pdf.get("title") or "PDF"
                    pdf_url = pdf.get("url") or pdf.get("uploadPdf") or pdf.get("link")
                    if pdf_url:
                        pdf_url = encode_url(pdf_url)
                        all_results[topic_name][section_name].append(f"({topic_name}) {pdf_title}: {pdf_url}")
                        pdf_count += 1

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
        keyboard.append([InlineKeyboardButton(f"{actual_index}. {title}", callback_data=f"sw_batch_{batch['id']}")])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"sw_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="sw_page_info"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"sw_page_{page+1}"))
    keyboard.append(nav_row)
    
    display_info = ""
    if total_batches > 0:
        display_info = f"📂 <b>Showing:</b> {start_idx + 1}-{end_idx} of {total_batches}\n\n"
    
    text = (
        f"💠 <b>Select a Batch to Extract:</b>\n\n"
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
    
    user_pages[user_id] = page

# ===================== MAIN CALLBACK ===================== #
@app.on_callback_query(filters.regex("^selectionway_$"))
async def selectionway_callback(client, callback_query):
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
            "⚙️ <b>Initializing SelectionWay Extractor...</b>\n\n"
            "Fetching available batches 💫"
        )
        
        user_id = callback_query.from_user.id
        await process_selectionway(client, callback_query.message, user_id)
        await processing_msg.delete()
        
    except Exception as e:
        print(f"Error in selectionway_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

# ===================== FETCH BATCH LIST ===================== #
async def process_selectionway(app: Client, message, user_id: int):
    waiting_msg = await message.reply_text("📡 <b>Fetching all batches...</b> Please wait ⚡")

    # Fetch merged batches (API + External JSON)
    batches = await get_all_batches()

    if not batches:
        await waiting_msg.edit_text("😕 <b>No active batches found.</b>")
        return

    user_batches[user_id] = batches
    user_pages[user_id] = 0
    
    await waiting_msg.delete()
    await show_batches_page(app, message, batches, page=0)

# ===================== PAGE NAVIGATION ===================== #
@app.on_callback_query(filters.regex("^sw_page_(\d+)$"))
async def sw_page_callback(client, callback_query):
    page = int(callback_query.data.split("_")[2])
    user_id = callback_query.from_user.id
    batches = user_batches.get(user_id, [])
    
    if not batches:
        await callback_query.answer("Session expired. Restart.", show_alert=True)
        return
    
    await callback_query.answer()
    await show_batches_page(client, callback_query, batches, page)

@app.on_callback_query(filters.regex("^sw_page_info$"))
async def sw_page_info_callback(client, callback_query):
    await callback_query.answer("Use ◀️ ▶️ buttons to change pages", show_alert=False)

# ===================== EXTRACT BATCH ===================== #
@app.on_callback_query(filters.regex("^sw_batch_"))
async def selectionway_batch_callback(app: Client, callback_query):
    await callback_query.answer("⏳ Extracting... please wait")
    batch_id = callback_query.data.replace("sw_batch_", "")
    chat_id = callback_query.message.chat.id
    
    try:
        await extract_and_send_batch(app, chat_id, batch_id, callback_query.from_user)
    except Exception as e:
        print(f"❌ Extraction Error: {e}")
        await callback_query.message.reply_text(f"❌ <b>Error:</b>\n<code>{str(e)}</code>")
    
    try:
        await callback_query.message.delete()
    except:
        pass

async def extract_and_send_batch(app: Client, chat_id: int, batch_id: str, user):
    # Fetch merged batches to find the specific batch details
    all_batches = await get_all_batches()
    batch_data = next((b for b in all_batches if b.get("id") == batch_id), {})
    
    batch_name = batch_data.get("title", "Unknown Batch")
    thumbnail_url = batch_data.get("banner") or batch_data.get("bannerSquare") or ""
    price = batch_data.get("discountPrice") or batch_data.get("price", "N/A")
    if price and price != "N/A":
        price = f"{price}"
    else:
        price = "N/A"

    processing_msg = await app.send_message(chat_id, "⏳ <b>Extracting content...</b>")
    
    try:
        all_results, video_count, pdf_count, youtube_count = await scrape_batch(batch_id)

        if not all_results:
            await processing_msg.edit_text("😕 <b>No content found in this batch.</b>")
            return

        file_content = f"{batch_name}[Batch Thumbnail]: {thumbnail_url}\n\n"
        for topic_name, sections in all_results.items():
            for section_name, links in sections.items():
                for link in links:
                    file_content += f"{link}\n"
            
        file_bytes = io.BytesIO(file_content.encode("utf-8"))
        file_bytes.name = sanitize_filename(batch_name)

        thumb_path = await download_thumbnail(MY_LOGO_URL)

        mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
        total_links = video_count + pdf_count
        regular_count = video_count - youtube_count
        caption = (
            f"<blockquote>📚 App: Selection Way</blockquote>\n\n"
            f"═══════ BATCH DETAILS ═══════\n"
            f"<blockquote>🌟 Batch Name: {batch_name}\n"
            f"🆔 Batch ID: {batch_id}\n"
            f"💸 Price : ₹{price}</blockquote>\n\n"
            f"═══════ LINK SUMMARY ═══════\n"
            f"<blockquote>🔢 Total Links: {total_links}\n"
            f"┠🎥 Videos : {video_count}\n"
            f"  ┠📺 Regular : {regular_count}\n"
            f"  ┠📻 YouTube : {youtube_count}\n"
            f"┠📁 Documents: {pdf_count}</blockquote>\n\n"
            f"👤 Generated By: {mention}\n"
            f"📅 Generated On: {time_new} IST"
        )

        await app.send_document(
            chat_id=chat_id, 
            document=file_bytes, 
            caption=caption,
            thumb=thumb_path
        )

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
        if os.path.exists(thumb_path if 'thumb_path' in locals() else ""):
            try:
                os.remove(thumb_path)
            except:
                passs