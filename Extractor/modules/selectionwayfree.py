import asyncio  
import io  
import re 
import json
import aiohttp
from urllib.parse import quote  
from datetime import datetime  
import requests  
from config import PREMIUM_LOGS 
from Extractor.core.func import subscribe, chk_user
from pyrogram import Client  
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup  

# ---------------- LOG CHANNEL -----------------  
LOG_CHANNEL = PREMIUM_LOGS # 👈 replace with your real log channel id

# ---------------- TRACKED MESSAGES -----------------  
user_messages = {}  # chat_id: list of dicts {id, type}  

# ---------------- HELPERS -----------------  
def sanitize_filename(name: str) -> str:  
    return re.sub(r'[\\/*?:"<>|₹]', "", name).strip() + ".txt"  

def encode_url(url: str) -> str:  
    if not url:  
        return url  
    parts = url.split('/', 3)  
    if len(parts) < 4:  
        return url  
    return parts[0] + '//' + parts[2] + '/' + quote(parts[3])  

def fetch_json(url: str):  
    try:  
        r = requests.get(url, timeout=15)  
        r.raise_for_status()  
        return r.json()  
    except Exception as e:  
        print(f"⚠️ Failed to fetch {url}: {e}")  
        return None  

async def scrape_batch(batch_id: str):
    """Fetch video and PDF URLs + counts for a batch"""
    all_results = []
    video_count = 0
    pdf_count = 0

    # --- Videos ---
    url_videos = f"https://backend.multistreaming.site/api/courses/{batch_id}/classes?populate=full"
    data_videos = fetch_json(url_videos)
    if data_videos:
        classes_data = data_videos.get("data", {}).get("classes", [])
        for topic in classes_data:
            for cls in topic.get("classes", []):
                title = cls.get("title", "No Title").strip()
                url = None
                if cls.get("mp4Recordings"):
                    recs = cls["mp4Recordings"]
                    preferred = next((r for r in recs if r.get("quality")=="720p" and r.get("url")), None)
                    url = preferred["url"] if preferred else recs[0].get("url")
                else:
                    url = cls.get("class_link")
                if title and url:
                    all_results.append(f"{title}: {url}")
                    video_count += 1

    # --- PDFs ---
    url_pdfs = f"https://backend.multistreaming.site/api/courses/{batch_id}/pdfs?groupBy=topic"
    data_pdfs = fetch_json(url_pdfs)
    if data_pdfs:
        topics = data_pdfs.get("data", {}).get("topics", [])
        for topic in topics:
            pdfs = topic.get("pdfs", [])
            for pdf in pdfs:
                title = pdf.get("title", "No Title").strip()
                link = encode_url(pdf.get("uploadPdf"))
                if title and link:
                    all_results.append(f"{title}: {link}")
                    pdf_count += 1

    return all_results, video_count, pdf_count

async def track_message(chat_id: int, message_id: int, msg_type="generic"):  
    if chat_id not in user_messages:  
        user_messages[chat_id] = []  
    user_messages[chat_id].append({"id": message_id, "type": msg_type})  

async def delete_tracked_messages(client: Client, chat_id: int, exclude_types=["persistent"]):  
    if chat_id in user_messages:  
        remaining = []  
        for msg in user_messages[chat_id]:  
            if msg["type"] in exclude_types:  
                remaining.append(msg)  
                continue  
            try:  
                await client.delete_messages(chat_id, msg["id"])  
            except:  
                pass  
        user_messages[chat_id] = remaining  

# ===== Helper to fetch thumbnail =====
async def fetch_thumbnail(url):
    if not url:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    thumb_file = io.BytesIO(data)
                    thumb_file.name = "thumb.jpg"
                    return thumb_file
    except Exception as e:
        print(f"⚠️ Failed to fetch thumbnail: {e}")
        return None


async def selectionway_callback(client, callback_query):
    """Triggered when user clicks SelectionWay"""
    lol = await chk_user(callback_query, callback_query.from_user.id)
    if lol == 1:
        await callback_query.message.reply_text(
            "🔒 <b>Premium Feature Locked!</b>\n\n"
            "You don’t have access to use this feature yet.\n"
            "💎 <b>Contact:</b> <a href='https://t.me/URS_LUCIFER'>LUCIFER</a> to upgrade your plan.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("💬 Contact Admin", url="https://t.me/noobhusir")]
                ]
            )
        )
        return

    try:
        processing_msg = await callback_query.message.reply_text(
            "**⚙️ Fetching available batches... please wait 💫**"
        )

        await process_selectionway(client, callback_query.message, callback_query.from_user.id)
        await processing_msg.delete()

    except Exception as e:
        print(f"Error in selectionway_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

# ===== CALLBACK ENTRY POINT =====
async def process_selectionway(app: Client, message, user_id: int):
    """Main button logic — fetch and display available batches"""
    await message.reply_text("📡 Fetching all available batches... please wait")
    
    url_info = "https://backend.multistreaming.site/api/courses/active?userId=2054598"
    data_info = fetch_json(url_info)
    batches = data_info.get("data", []) if data_info else []

    if not batches:
        await message.reply_text("😕 No active batches found right now.")
        return

    keyboard = [
        [InlineKeyboardButton(batch["title"], callback_data=f"sw_batch_{batch['id']}")]
        for batch in batches
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        "💠 <b>Select a Batch to Extract:</b>",
        reply_markup=reply_markup
    )


# ===== CALLBACK FOR BATCH SELECTION =====
async def selectionway_batch_callback(app: Client, callback_query):
    await callback_query.answer("⏳ Extracting... please wait")
    batch_id = callback_query.data.replace("sw_batch_", "")

    all_results, video_count, pdf_count = await scrape_batch(batch_id)

    # Fetch batch info
    url_info = "https://backend.multistreaming.site/api/courses/active?userId=2054598"
    data_info = fetch_json(url_info)
    batch_data = next((b for b in (data_info.get("data", []) if data_info else []) if b["id"] == batch_id), {})
    batch_name = batch_data.get("title", "Unknown Batch")
    thumbnail_url = batch_data.get("banner") or batch_data.get("bannerSquare") or ""

    if not all_results:
        await callback_query.message.edit_text("😕 No content found in this batch.")
        return

    file_content = "\n".join(all_results)
    file_bytes = io.BytesIO(file_content.encode("utf-8"))
    file_bytes.name = sanitize_filename(batch_name)

    caption = (
        f"╭━━━『 💠 𝐋𝐔𝐂𝐈𝐅𝐄𝐑 𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐎𝐑 💠 』━━━╮\n"
        f"📦 <b>Platform:</b> SelectionWay\n"
        f"📚 <b>Batch:</b> <code>{batch_name}</code>\n"
        f"🎬 <b>Videos:</b> {video_count}\n"
        f"📄 <b>PDFs:</b> {pdf_count}\n"
        f"🕒 <b>Extracted:</b> {datetime.now().strftime('%d-%m-%Y %I:%M %p')}\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"<code>💫 Extracted by Lucifer Extractor</code>"
    )

    # send to user
    await app.send_document(
        chat_id=callback_query.message.chat.id,
        document=file_bytes,
        caption=caption
    )

    # send to channel too 🔥
    try:
        await app.send_document(
            chat_id=LOG_CHANNEL,
            document=file_bytes,
            caption=f"📡 <b>SelectionWay Extract</b>\n\n{caption}"
        )
    except Exception as e:
        print(f"⚠️ Error sending to log channel: {e}")

    await callback_query.message.delete()
