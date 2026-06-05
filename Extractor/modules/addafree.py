import asyncio
import io
import os
import re
import aiohttp
import pytz
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import MessageNotModified
from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

# ===================== CONFIG & STATE ===================== #
MY_LOGO_URL = "https://i.ibb.co/BHQ2HsW5/JPEG-20260125-141038-953649353278939736.jpg"
user_states = {}  # Stores {user_id: 'waiting_for_package_id'}

# ===================== HEADERS (No JWT Required) ===================== #
BASE_HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "cp-origin": "11",
    "dName": "Chrome on Linux Desktop",
    "Origin": "https://www.adda247.com",
    "Referer": "https://www.adda247.com/",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "X-Auth-Token": "fpoa43edty5"
}

def get_headers(host: str):
    h = BASE_HEADERS.copy()
    h["Host"] = host
    return h

# ===================== HELPERS ===================== #
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|₹]', "", name).strip() + ".txt"

async def fetch_json_async(session, url: str, headers: dict):
    try:
        async with session.get(url, headers=headers, timeout=20) as r:
            if r.status == 200:
                return await r.json()
            else:
                # FIX: Print actual error if API fails (e.g., 401, 403)
                error_text = await r.text()
                print(f"⚠️ API Error {r.status} for {url}: {error_text[:300]}")
                return None
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return None

async def download_thumbnail(logo_url: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(logo_url, timeout=15) as resp:
                if resp.status == 200:
                    thumb_path = f"thumb_adda_{datetime.now().timestamp()}.jpg"
                    with open(thumb_path, 'wb') as f:
                        f.write(await resp.read())
                    return thumb_path
    except Exception as e:
        print(f"⚠️ Failed to download thumbnail: {e}")
    return None

# ===================== EXTRACTION LOGIC ===================== #
async def extract_adda247_package(app: Client, chat_id: int, package_id: str, user):
    processing_msg = await app.send_message(chat_id, "⏳ <b>Fetching all subjects...</b> Please wait ⚡")
    
    try:
        # 1. Fetch Subjects
        url_subjects = f"https://store.adda247.com/api/v1/syllabus/pdp/subjects?packageId={package_id}&contentType=ONLINE_LIVE_CLASSES&pageNo=0&src=aweb"
        async with aiohttp.ClientSession() as session:
            data_subjects = await fetch_json_async(session, url_subjects, get_headers("store.adda247.com"))
        
        if not data_subjects or not data_subjects.get("success"):
            error_info = data_subjects if data_subjects else "Connection failed or API returned empty."
            await processing_msg.edit_text(f"😕 <b>Failed to fetch subjects.</b>\n\n<code>{str(error_info)[:500]}</code>")
            return

        syllabus = data_subjects.get("data", {}).get("syllabus", [])
        if not syllabus:
            await processing_msg.edit_text("😕 <b>No subjects found for this Package ID.</b>")
            return

        # 2. Fetch Classes for each subject
        all_results = {}
        total_videos = 0
        total_pdfs = 0
        youtube_count = 0
        regular_count = 0

        async with aiohttp.ClientSession() as session:
            for subj in syllabus:
                subject_id = subj.get("id")
                subject_name = subj.get("tags", [{}])[0].get("name", "Unknown Subject")
                
                all_results[subject_name] = []
                page = 0
                
                while True:
                    url_classes = f"https://liveclasses.adda247.com/api/v1/pdp/OLC/content?contentType=ONLINE_LIVE_CLASSES&packageId={package_id}&level=CHAPTER&syllabusId={subject_id}&pageNo={page}&pageSize=20&src=aweb"
                    data_classes = await fetch_json_async(session, url_classes, get_headers("liveclasses.adda247.com"))
                    
                    if not data_classes or not data_classes.get("success"):
                        break
                        
                    content = data_classes.get("data", {}).get("content", [])
                    if not content:
                        break
                        
                    for cls in content:
                        title = cls.get("name", "No Title").strip()
                        
                        # --- Extract Video URL ---
                        tImg = cls.get("tImg", "")
                        video_url = None
                        if "/ivs/" in tImg:
                            try:
                                ivs_part = tImg.split("/ivs/")[1]
                                parts = ivs_part.split("/")
                                if len(parts) >= 2:
                                    video_url = f"https://video-streaming-source.s3.ap-south-1.amazonaws.com//ivs/{parts[0]}/{parts[1]}.mp4"
                            except:
                                pass
                        
                        if title and video_url:
                            all_results[subject_name].append(f"[VIDEO] {title}: {video_url}")
                            total_videos += 1
                            if "youtube.com" in video_url or "youtu.be" in video_url:
                                youtube_count += 1
                            else:
                                regular_count += 1
                        
                        # --- Extract PDF URL ---
                        pdf_filename = cls.get("pdfFileName")
                        if pdf_filename:
                            pdf_url = f"https://store.adda247.com/{pdf_filename}"
                            all_results[subject_name].append(f"[PDF] {pdf_filename}: {pdf_url}")
                            total_pdfs += 1
                    
                    if len(content) < 20:
                        break
                    page += 1

        # 3. Build Output File
        if total_videos == 0 and total_pdfs == 0:
            await processing_msg.edit_text("😕 <b>No content found in this package.</b>")
            return

        file_content = f"{MY_LOGO_URL}\n\n"
        for subj_name, links in all_results.items():
            if links:  # Only add subject if it has links
                file_content += f"{'='*20} {subj_name} {'='*20}\n"
                for link in links:
                    file_content += f"{link}\n"
                file_content += "\n\n"
                
        file_bytes = io.BytesIO(file_content.encode("utf-8"))
        file_bytes.name = sanitize_filename(f"Adda247_{package_id}")

        # 4. Download Thumbnail
        thumb_path = await download_thumbnail(MY_LOGO_URL)
        
        # 5. Build Caption
        india_timezone = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(india_timezone)
        time_new = current_time.strftime("%d %b %Y, %I:%M %p")
        
        total_links = total_videos + total_pdfs
        price = "N/A" 
        mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        file_name = file_bytes.name

        caption = (
            f"<blockquote>📚 App: Adda247</blockquote>\n\n"
            f"═══════ BATCH DETAILS ═══════\n"
            f"<blockquote>🌟 Batch Name: {package_id}\n"
            f"🆔 Package ID: {package_id}\n"
            f"💸 Price : ₹{price}</blockquote>\n\n"
            f"═══════ LINK SUMMARY ═══════\n"
            f"<blockquote>🔢 Total Links: {total_links}\n"
            f"📁 Documents: {total_pdfs}\n"
            f"┠🎥 Videos : {total_videos}\n"
            f"  ┠📺 Regular : {regular_count}\n"
            f"  ┠📻 YouTube : {youtube_count}</blockquote>\n\n"
            f"👤 Generated By: {mention}\n"
            f"📅 Generated On: {time_new} IST"
        ).rstrip()  # Ensures zero trailing spaces

        await processing_msg.delete()

        # 6. Send Document
        await app.send_document(
            chat_id=chat_id, 
            document=file_bytes, 
            caption=caption,
            thumb=thumb_path,
            parse_mode="HTML"
        )

        # 7. Log to Channel
        try:
            file_bytes.seek(0)
            await app.send_document(
                chat_id=PREMIUM_LOGS,
                document=file_bytes,
                caption=f"📡 <b>Adda247 Extract</b>\n\n{caption}",
                thumb=thumb_path,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"⚠️ Error sending to log: {e}")
            
    finally:
        if 'thumb_path' in locals() and thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except:
                pass

# ===================== MAIN CALLBACK ===================== #
@app.on_callback_query(filters.regex("^adda247_$"))
async def adda247_callback(client, callback_query):
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
        user_id = callback_query.from_user.id
        user_states[user_id] = 'waiting_for_package_id'
        
        try:
            await callback_query.message.edit_text(
                "📦 <b>Adda247 Extractor</b>\n\n"
                "Please send the <b>Package ID</b> to extract all subjects.\n\n"
                "❌ <i>Reply /cancel to abort.</i>"
            )
        except MessageNotModified:
            await callback_query.message.reply_text(
                "📦 <b>Adda247 Extractor</b>\n\n"
                "Please send the <b>Package ID</b> to extract all subjects.\n\n"
                "❌ <i>Reply /cancel to abort.</i>"
            )
        await callback_query.answer()
        
    except Exception as e:
        print(f"Error in adda247_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

# ===================== HANDLE PACKAGE ID INPUT ===================== #
# FIX: Changed group=-2 to group=-15 to ensure it runs BEFORE other text handlers in start.py
@app.on_message(filters.text & ~filters.command(["start", "help"]), group=-15)
async def handle_package_id_input(client, message):
    user_id = message.from_user.id
    
    if user_id in user_states and user_states[user_id] == 'waiting_for_package_id':
        message.stop_propagation()  # Stop other handlers from catching this
        
        text = message.text.strip()
        if text.lower() == '/cancel':
            del user_states[user_id]
            await message.reply_text("❌ Process cancelled.")
            return
            
        if text.isdigit():
            package_id = text
            del user_states[user_id]
            
            # FIX: Added try-except to catch silent crashes
            try:
                await extract_adda247_package(client, message.chat.id, package_id, message.from_user)
            except Exception as e:
                print(f"❌ CRITICAL ERROR IN EXTRACTION: {e}")
                await message.reply_text(f"❌ <b>Bot crashed during extraction:</b>\n<code>{str(e)}</code>")
        else:
            await message.reply_text("❌ Please send a valid numeric Package ID.")
        return
