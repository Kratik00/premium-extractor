import asyncio
import io
import re
import aiohttp
import requests
from datetime import datetime
from urllib.parse import quote
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

# ===================== CONFIG ===================== #
# Base URL for the API. 
# Note: If the classes endpoint is hosted on a different domain (e.g., node.topperswisdom.com), change this.
BASE_URL = "https://gdgoenkaratia.com"

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
    """Async helper to fetch JSON data"""
    try:
        async with session.get(url, timeout=15) as r:
            if r.status == 200:
                return await r.json()
            return None
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return None

async def scrape_batch(course_id: str):
    """Fetch video and PDF URLs + counts for a batch using the new API structure"""
    all_results = {}  # Will store {topic_name: [list of links]}
    video_count = 0
    pdf_count = 0

    async with aiohttp.ClientSession() as session:
        # --- 1. Fetch Topics ---
        url_topics = f"{BASE_URL}/api/topic-and-section?courseId={course_id}"
        data_topics = await fetch_json_async(session, url_topics)
        
        if not data_topics or "data" not in data_topics:
            return all_results, video_count, pdf_count

        topics = data_topics["data"].get("topics", [])
        
        # --- 2. Fetch Classes for each topic concurrently ---
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
        
        # Run all topic fetches at the same time
        results = await asyncio.gather(*tasks)
        
        # --- 3. Parse Videos and PDFs ---
        for topic_name, data in results:
            if not data or "data" not in data:
                continue
            
            classes = data["data"].get("classes", [])
            topic_links = []
            
            for cls in classes:
                title = cls.get("title", "No Title").strip()
                
                # --- Extract Video ---
                video_url = None
                if cls.get("mp4Recordings"):
                    recs = cls["mp4Recordings"]
                    if recs:
                        preferred = next((r for r in recs if r.get("quality") == "720p" and r.get("url")), None)
                        video_url = preferred["url"] if preferred else recs[0].get("url")
                    else:
                        video_url = cls.get("class_link") or cls.get("videoUrl") or cls.get("url")
                else:
                    video_url = cls.get("class_link") or cls.get("videoUrl") or cls.get("url")
                
                if title and video_url:
                    topic_links.append(f"[VIDEO] {title}: {video_url}")
                    video_count += 1
                
                # --- Extract PDFs ---
                pdf_items = []
                # Check common keys for PDFs/attachments in the class object
                for key in ["pdfs", "attachments", "notes", "documents", "studyMaterials"]:
                    if cls.get(key) and isinstance(cls.get(key), list):
                        pdf_items.extend(cls[key])
                
                for pdf in pdf_items:
                    pdf_title = pdf.get("title") or pdf.get("name") or "PDF"
                    pdf_url = pdf.get("url") or pdf.get("uploadPdf") or pdf.get("link")
                    if pdf_url:
                        pdf_url = encode_url(pdf_url)
                        topic_links.append(f"[PDF] {pdf_title}: {pdf_url}")
                        pdf_count += 1
            
            if topic_links:
                all_results[topic_name] = topic_links

    return all_results, video_count, pdf_count

# ===================== MAIN CALLBACK ===================== #
@app.on_callback_query(filters.regex("^selectionway_$"))
async def selectionway_callback(client, callback_query):
    """Triggered when user clicks SelectionWay"""
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
        processing_msg = await callback_query.message.reply_text(
            "⚙️ <b>Initializing SelectionWay Extractor...</b>\n\n"
            "Please wait while I fetch available batches 💫"
        )

        await process_selectionway(client, callback_query.message)
        await processing_msg.delete()

    except Exception as e:
        print(f"Error in selectionway_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

# ===================== FETCH BATCH LIST ===================== #
async def process_selectionway(app: Client, message):
    """Main button logic — fetch and display available batches"""
    waiting_msg = await message.reply_text("📡 <b>Fetching all available batches...</b> Please wait ⚡")

    url_info = f"{BASE_URL}/api/courses/active?userId=2054598"
    
    async with aiohttp.ClientSession() as session:
        data_info = await fetch_json_async(session, url_info)
    
    batches = data_info.get("data", []) if data_info else []

    if not batches:
        await waiting_msg.edit_text("😕 <b>No active batches found right now.</b>")
        return

    keyboard = [
        [InlineKeyboardButton(f"📘 {batch['title']}", callback_data=f"sw_batch_{batch['id']}")]
        for batch in batches
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await waiting_msg.edit_text(
        "💠 <b>Select a Batch to Extract:</b>\n\nEach button corresponds to a live course batch ⚡",
        reply_markup=reply_markup
    )

# ===================== EXTRACT BATCH ===================== #
@app.on_callback_query(filters.regex("^sw_batch_"))
async def selectionway_batch_callback(app: Client, callback_query):
    await callback_query.answer("⏳ Extracting... please wait")

    batch_id = callback_query.data.replace("sw_batch_", "")
    
    # Fetch batch info for caption and thumbnail
    url_info = f"{BASE_URL}/api/courses/active?userId=2054598"
    async with aiohttp.ClientSession() as session:
        data_info = await fetch_json_async(session, url_info)
    
    batch_data = next((b for b in (data_info.get("data", []) if data_info else []) if b["id"] == batch_id), {})
    batch_name = batch_data.get("title", "Unknown Batch")
    thumbnail_url = batch_data.get("banner") or batch_data.get("bannerSquare") or ""

    # Scrape batch content
    all_results, video_count, pdf_count = await scrape_batch(batch_id)

    if not all_results:
        await callback_query.message.edit_text("😕 <b>No content found in this batch.</b>")
        return

    # Build output file
    # 1. Attach thumbnail in the first line as requested
    file_content = f"Thumbnail: {thumbnail_url}\n\n"
    
    # 2. Group links by topic for better readability
    for topic_name, links in all_results.items():
        file_content += f"{'='*20} {topic_name} {'='*20}\n"
        for link in links:
            file_content += f"{link}\n"
        file_content += "\n"
        
    file_bytes = io.BytesIO(file_content.encode("utf-8"))
    file_bytes.name = sanitize_filename(batch_name)

    # Create better UI caption
    caption = (
        f"╭━━━『 💠 𝐋𝐔𝐂𝐈𝐅𝐄𝐑 𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐎𝐑 💠 』━━━╮\n"
        f"┃ 📦 <b>Platform:</b> SelectionWay\n"
        f"┃ 📚 <b>Course:</b> <code>{batch_name}</code>\n"
        f"┃ 🎬 <b>Total Videos:</b> {video_count}\n"
        f"┃ 📄 <b>Total PDFs:</b> {pdf_count}\n"
        f"┃ 🕒 <b>Time:</b> {datetime.now().strftime('%d-%m-%Y | %I:%M %p')}\n"
        f"╰━━━『 👑 Maintained by @URS_LUCIFER 』━━━╯"
    )

    # Send to user
    await app.send_document(
        chat_id=callback_query.message.chat.id,
        document=file_bytes,
        caption=caption
    )

    # Also log to channel
    try:
        file_bytes.seek(0)
        await app.send_document(
            chat_id=PREMIUM_LOGS,
            document=file_bytes,
            caption=f"📡 <b>SelectionWay Extract</b>\n\n{caption}"
        )
    except Exception as e:
        print(f"⚠️ Error sending to log channel: {e}")

    await callback_query.message.delete()
