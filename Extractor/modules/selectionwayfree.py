import asyncio
import io
import re
import aiohttp
from datetime import datetime
from urllib.parse import quote
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import MessageNotModified
from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

# ===================== CONFIG & STATE ===================== #
BASE_URL = "https://gdgoenkaratia.com"

# 👇👇👇 CHANGE THIS URL TO YOUR OWN LOGO/THUMBNAIL 👇👇👇
MY_LOGO_URL = "https://telegra.ph/file/your-custom-logo.jpg" 
# 👆👆👆 PASTE YOUR LOGO URL HERE 👆👆👆

user_batches = {}  # Stores {user_id: [list_of_batches]}
user_states = {}   # Stores {user_id: 'waiting_for_index'}

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
        async with session.get(url, timeout=20) as r:
            if r.status == 200:
                return await r.json()
            return None
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return None

async def scrape_batch(course_id: str):
    """Fetch video and PDF URLs + counts for a batch using the new API structure"""
    all_results = {} 
    video_count = 0
    pdf_count = 0

    async with aiohttp.ClientSession() as session:
        url_topics = f"{BASE_URL}/api/topic-and-section?courseId={course_id}"
        data_topics = await fetch_json_async(session, url_topics)
        
        if not data_topics or "data" not in data_topics:
            return all_results, video_count, pdf_count

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
                if cls.get("mp4Recordings") and isinstance(cls["mp4Recordings"], list) and len(cls["mp4Recordings"]) > 0:
                    recs = cls["mp4Recordings"]
                    preferred = next((r for r in recs if r.get("quality") == "720p" and r.get("url")), None)
                    video_url = preferred["url"] if preferred else recs[0].get("url")
                else:
                    video_url = cls.get("class_link") or cls.get("videoUrl") or cls.get("url")
                
                if title and video_url:
                    all_results[topic_name][section_name].append(f"[VIDEO] {title}: {video_url}")
                    video_count += 1
                
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
                        all_results[topic_name][section_name].append(f"[PDF] {pdf_title}: {pdf_url}")
                        pdf_count += 1

    return all_results, video_count, pdf_count

# ===================== PAGINATION UI ===================== #
async def show_batches_page(client, target, batches, page=0):
    """Renders the paginated batch selection UI"""
    is_callback = isinstance(target, CallbackQuery)
    
    total_batches = len(batches)
    batches_per_page = 10
    total_pages = (total_batches + batches_per_page - 1) // batches_per_page
    
    start_idx = page * batches_per_page
    end_idx = min(start_idx + batches_per_page, total_batches)
    page_batches = batches[start_idx:end_idx]
    
    keyboard = []
    for i, batch in enumerate(page_batches):
        title = batch.get('title', 'Unknown')
        if len(title) > 35:
            title = title[:32] + "..."
        keyboard.append([InlineKeyboardButton(f"📘 {title}", callback_data=f"sw_batch_{batch['id']}")])
        
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"sw_page_{page-1}"))
    
    nav_row.append(InlineKeyboardButton("🔍 Enter Index", callback_data="sw_enter_index"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"sw_page_{page+1}"))
        
    keyboard.append(nav_row)
    
    text = (
        f"💠 <b>Select a Batch to Extract:</b>\n\n"
        f"📄 <b>Page:</b> {page + 1} / {total_pages}\n"
        f"📦 <b>Total Batches:</b> {total_batches}\n\n"
        f"Choose a batch from the buttons below or use <b>🔍 Enter Index</b>."
    )
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        try:
            await target.message.edit_text(text, reply_markup=reply_markup)
        except MessageNotModified:
            pass
    else:
        await target.reply_text(text, reply_markup=reply_markup)

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
        
        user_id = callback_query.from_user.id
        await process_selectionway(client, callback_query.message, user_id)
        await processing_msg.delete()
        
    except Exception as e:
        print(f"Error in selectionway_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

# ===================== FETCH BATCH LIST ===================== #
async def process_selectionway(app: Client, message, user_id: int):
    """Fetches batches and shows the first page"""
    waiting_msg = await message.reply_text("📡 <b>Fetching all available batches...</b> Please wait ⚡")

    url_info = f"{BASE_URL}/api/courses/active?userId=2054598"
    async with aiohttp.ClientSession() as session:
        data_info = await fetch_json_async(session, url_info)
    
    batches = data_info.get("data", []) if data_info else []

    if not batches:
        await waiting_msg.edit_text("😕 <b>No active batches found right now.</b>")
        return

    user_batches[user_id] = batches
    
    await waiting_msg.delete()
    await show_batches_page(app, message, batches, page=0)

# ===================== PAGE NAVIGATION ===================== #
@app.on_callback_query(filters.regex("^sw_page_"))
async def sw_page_callback(client, callback_query):
    page = int(callback_query.data.replace("sw_page_", ""))
    user_id = callback_query.from_user.id
    batches = user_batches.get(user_id, [])
    
    if not batches:
        await callback_query.answer("Session expired. Please start over.", show_alert=True)
        return
    
    await callback_query.answer()
    await show_batches_page(client, callback_query, batches, page)

# ===================== ENTER INDEX BUTTON ===================== #
@app.on_callback_query(filters.regex("^sw_enter_index$"))
async def sw_enter_index_callback(client, callback_query):
    user_id = callback_query.from_user.id
    batches = user_batches.get(user_id, [])
    
    if not batches:
        await callback_query.answer("Session expired.", show_alert=True)
        return
        
    await callback_query.answer("Sending batch list...")
    
    # Create txt file with numbered list
    file_content = "📋 AVAILABLE BATCHES LIST 📋\n\n"
    for i, batch in enumerate(batches):
        file_content += f"{i+1}. {batch.get('title', 'Unknown Batch')}\n"
        
    file_bytes = io.BytesIO(file_content.encode("utf-8"))
    file_bytes.name = "Batch_List.txt"
    
    await callback_query.message.reply_document(
        document=file_bytes,
        caption="📤 Here is the list of all available batches."
    )
    
    # Update state to wait for user input
    user_states[user_id] = 'waiting_for_index'
    
    # Edit the original message: remove the keyboard and ask for the index
    try:
        await callback_query.message.edit_text(
            "✅ <b>Batch list sent above!</b>\n\n"
            "Please reply with the <b>Index Number</b> (e.g., <code>1</code>, <code>2</code>, <code>3</code>) "
            "of the batch you want to extract.\n\n"
            "❌ <i>Reply /cancel to abort.</i>"
        )
    except MessageNotModified:
        pass

# ===================== HANDLE INDEX INPUT ===================== #
# FIX: Added group=-1 to force this to run BEFORE other global text handlers
@app.on_message(filters.text & ~filters.command(["start", "help"]), group=-1)
async def handle_index_input(client, message):
    """Catches the index number when the user is in 'waiting_for_index' state"""
    user_id = message.from_user.id
    
    if user_id in user_states and user_states[user_id] == 'waiting_for_index':
        # Stop propagation so other handlers (like start.py) don't catch this message
        message.stop_propagation()
        
        text = message.text.strip()
        if text.lower() == '/cancel':
            del user_states[user_id]
            await message.reply_text("❌ Process cancelled.")
            return
            
        try:
            index = int(text) - 1
            batches = user_batches.get(user_id, [])
            
            if 0 <= index < len(batches):
                batch_id = batches[index]['id']
                del user_states[user_id]
                
                processing_msg = await message.reply_text("⏳ Extracting... please wait")
                
                # FIX: Added try/except to catch silent extraction failures
                try:
                    await extract_and_send_batch(client, message.chat.id, batch_id)
                except Exception as e:
                    print(f"❌ Extraction Error: {e}")
                    await processing_msg.edit_text(f"❌ <b>Error during extraction:</b>\n<code>{str(e)}</code>")
                    return
                    
                await processing_msg.delete()
            else:
                await message.reply_text(f"❌ Invalid index. Please enter a number between 1 and {len(batches)}.")
        except ValueError:
            await message.reply_text("❌ Please send a valid number.")
        return

# ===================== EXTRACT BATCH ===================== #
@app.on_callback_query(filters.regex("^sw_batch_"))
async def selectionway_batch_callback(app: Client, callback_query):
    await callback_query.answer("⏳ Extracting... please wait")
    batch_id = callback_query.data.replace("sw_batch_", "")
    chat_id = callback_query.message.chat.id
    
    await extract_and_send_batch(app, chat_id, batch_id)
    
    try:
        await callback_query.message.delete()
    except:
        pass

async def extract_and_send_batch(app: Client, chat_id: int, batch_id: str):
    """Core extraction logic separated for reusability"""
    url_info = f"{BASE_URL}/api/courses/active?userId=2054598"
    async with aiohttp.ClientSession() as session:
        data_info = await fetch_json_async(session, url_info)
    
    batch_data = next((b for b in (data_info.get("data", []) if data_info else []) if b["id"] == batch_id), {})
    batch_name = batch_data.get("title", "Unknown Batch")

    all_results, video_count, pdf_count = await scrape_batch(batch_id)

    if not all_results:
        await app.send_message(chat_id, "😕 <b>No content found in this batch.</b>")
        return

    # Build output file
    file_content = f"{MY_LOGO_URL}\n\n"
    for topic_name, sections in all_results.items():
        file_content += f"{'='*20} {topic_name} {'='*20}\n"
        for section_name, links in sections.items():
            file_content += f"\n--- {section_name} ---\n"
            for link in links:
                file_content += f"{link}\n"
        file_content += "\n\n"
        
    file_bytes = io.BytesIO(file_content.encode("utf-8"))
    file_bytes.name = sanitize_filename(batch_name)

    caption = (
        f"╭━━━『 💠 𝐋𝐔𝐂𝐈𝐅𝐄𝐑 𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐎𝐑 💠 』━━━╮\n"
        f"┃ 📦 <b>Platform:</b> SelectionWay\n"
        f"┃ 📚 <b>Course:</b> <code>{batch_name}</code>\n"
        f"┃ 🎬 <b>Total Videos:</b> {video_count}\n"
        f"┃ 📄 <b>Total PDFs:</b> {pdf_count}\n"
        f"┃ 🕒 <b>Time:</b> {datetime.now().strftime('%d-%m-%Y | %I:%M %p')}\n"
        f"╰━━━『 👑 Maintained by @URS_LUCIFER 』━━━╯"
    )

    await app.send_document(chat_id=chat_id, document=file_bytes, caption=caption)

    try:
        file_bytes.seek(0)
        await app.send_document(
            chat_id=PREMIUM_LOGS,
            document=file_bytes,
            caption=f"📡 <b>SelectionWay Extract</b>\n\n{caption}"
        )
    except Exception as e:
        print(f"⚠️ Error sending to log channel: {e}")
