import io
import os
import re
import aiohttp
import pytz
import uuid
import asyncio
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import MessageNotModified

from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

# ===================== CONFIG & STATE ===================== #
MY_LOGO_URL = "https://i.ibb.co/BHQ2HsW5/JPEG-20260125-141038-953649353278939736.jpg"
user_states = {}  # Stores {user_id: {'state': 'waiting', 'session': 'uuid'}}

# ===================== HEADERS ===================== #
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
    "X-Auth-Token": "fpoa43edty5",
    "x-jwt-token": "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJzdW9vaGFpbEBnbWFpbC5jb20iLCJhdWQiOiI3NTAzNTk3IiwiaWF0IjoxNzgwNjU4NDc0LCJpc3MiOiJhZGRhMjQ3LmNvbSIsIm5hbWUiOiJqYWNrIG9mIGFsbCBUcmFkZXMiLCJlbWFpbCI6InN1b29oYWlsQGdtYWlsLmNvbSIsInBob25lIjoiNzUwMTM0NDU2NyIsInVzZXJJZCI6ImFkZGEudjEuNDNhOGIzNDRkZmE1MzYxODFiYTY1MTU5N2RkMGIzZGQiLCJsb2dpbkFwaVZlcnNpb24iOjJ9.xejdMXXfdtNrzQkCVwQ7Ra7oj15dewxoLweFS82fq8KVspMv4a8tbQfdGvJUIe34qsWjJDJFMQwoe7fvkAdiaA",
    "LOGIN_TOKEN": "3d23790f-855c-4e5a-9f7e-934c378ec4c6",
    "LOGIN_TYPE": "1"
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
                    with open(thumb_path, "wb") as f:
                        f.write(await resp.read())
                    return thumb_path
    except Exception as e:
        print(f"⚠️ Failed to download thumbnail: {e}")
    return None

# ===================== EXTRACTION LOGIC (UNCHANGED) ===================== #
async def extract_adda247_package(app: Client, chat_id: int, package_id: str, user):
    processing_msg = await app.send_message(chat_id, "⏳ <b>Fetching all subjects...</b> Please wait ⚡")
    thumb_path = None
    try:
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

        all_results = {}
        total_videos = 0
        total_pdfs = 0
        youtube_count = 0
        regular_count = 0

        async with aiohttp.ClientSession() as session:
            for i, subj in enumerate(syllabus):
                subject_id = subj.get("id")
                subject_name = subj.get("tags", [{}])[0].get("name", "Unknown Subject")

                try:
                    await processing_msg.edit_text(
                        f"⏳ <b>Extracting Content...</b> Please wait ⚡\n\n"
                        f"📖 <b>Subject:</b> <code>{subject_name}</code>\n"
                        f"📊 <b>Progress:</b> {i+1}/{len(syllabus)}\n"
                        f"🎥 <b>Videos found:</b> {total_videos}\n"
                        f"📄 <b>PDFs found:</b> {total_pdfs}"
                    )
                except MessageNotModified:
                    pass

                all_results[subject_name] = []
                page = 0
                page_size = 50 
                found_level = None

                for level_type in ["TOPIC", "CHAPTER", "SUBJECT"]:
                    test_url = f"https://liveclasses.adda247.com/api/v1/pdp/OLC/content?contentType=ONLINE_LIVE_CLASSES&packageId={package_id}&level={level_type}&syllabusId={subject_id}&pageNo=0&pageSize={page_size}&src=aweb"
                    test_data = await fetch_json_async(session, test_url, get_headers("liveclasses.adda247.com"))
                    if test_data and test_data.get("success"):
                        test_content = test_data.get("data", {}).get("content", [])
                        if test_content:
                            found_level = level_type
                            break
                
                if not found_level:
                    continue

                while True:
                    url_classes = f"https://liveclasses.adda247.com/api/v1/pdp/OLC/content?contentType=ONLINE_LIVE_CLASSES&packageId={package_id}&level={found_level}&syllabusId={subject_id}&pageNo={page}&pageSize={page_size}&src=aweb"
                    data_classes = await fetch_json_async(session, url_classes, get_headers("liveclasses.adda247.com"))

                    if not data_classes or not data_classes.get("success"):
                        break
                        
                    content = data_classes.get("data", {}).get("content", [])
                    if not content:
                        break
                        
                    for cls in content:
                        title = cls.get("name", "No Title").strip()
                        tImg = cls.get("tImg", "")
                        video_url = None
                        
                        if "/ivs/" in tImg:
                            try:
                                ivs_part = tImg.split("/ivs/")[1]
                                parts = ivs_part.split("/")
                                if len(parts) >= 3:
                                    video_url = f"https://video-streaming-source.s3.ap-south-1.amazonaws.com//ivs/{parts[0]}/{parts[1]}.mp4"
                                elif len(parts) == 2:
                                    video_url = f"https://video-streaming-source.s3.ap-south-1.amazonaws.com//ivs/{parts[0]}.mp4"
                                elif len(parts) == 1:
                                    video_id = parts[0].split('.')[0]
                                    video_url = f"https://video-streaming-source.s3.ap-south-1.amazonaws.com//ivs/{video_id}.mp4"
                            except Exception:
                                pass
                        
                        if not video_url and cls.get("externalScheduleId"):
                            video_url = f"https://video-streaming-source.s3.ap-south-1.amazonaws.com//ivs/{cls['externalScheduleId']}.mp4"

                        if title and video_url:
                            all_results[subject_name].append(f"[VIDEO] {title}: {video_url}")
                            total_videos += 1
                            if "youtube.com" in video_url or "youtu.be" in video_url:
                                youtube_count += 1
                            else:
                                regular_count += 1

                        pdf_filename = cls.get("pdfFileName")
                        if pdf_filename:
                            pdf_url = f"https://store.adda247.com/{pdf_filename}"
                            all_results[subject_name].append(f"[PDF] {pdf_filename}: {pdf_url}")
                            total_pdfs += 1

                    if len(content) < page_size:
                        break
                    page += 1

        if total_videos == 0 and total_pdfs == 0:
            await processing_msg.edit_text("😕 <b>No content found in this package.</b>")
            return

        await processing_msg.edit_text("⏳ <b>Generating file...</b> Almost done! ⚡")

        file_content = f"{MY_LOGO_URL}\n\n"
        for subj_name, links in all_results.items():
            if links:
                file_content += f"{'='*20} {subj_name} {'='*20}\n"
                for link in links:
                    file_content += f"{link}\n"
                file_content += "\n\n"

        file_bytes = io.BytesIO(file_content.encode("utf-8"))
        file_bytes.name = sanitize_filename(f"Adda247_{package_id}")
        thumb_path = await download_thumbnail(MY_LOGO_URL)

        india_timezone = pytz.timezone("Asia/Kolkata")
        current_time = datetime.now(india_timezone)
        time_new = current_time.strftime("%d %b %Y, %I:%M %p")

        total_links = total_videos + total_pdfs
        price = "N/A"
        mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

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
        ).rstrip()

        await processing_msg.delete()

        await app.send_document(chat_id=chat_id, document=file_bytes, caption=caption, thumb=thumb_path, parse_mode="HTML")

        try:
            file_bytes.seek(0)
            await app.send_document(chat_id=PREMIUM_LOGS, document=file_bytes, caption=f"📡 <b>Adda247 Extract</b>\n\n{caption}", thumb=thumb_path, parse_mode="HTML")
        except Exception as e:
            print(f"⚠️ Error sending to log: {e}")

    finally:
        if thumb_path and os.path.exists(thumb_path):
            try: os.remove(thumb_path)
            except: pass

# ===================== NEW CALLBACK HANDLER (ASK LISTEN LOGIC) ===================== #
@app.on_callback_query(filters.regex("^adda247_"))
async def adda247_callback(client, callback_query):
    lol = await chk_user(callback_query, callback_query.from_user.id)
    if lol == 1:
        await callback_query.message.reply_text(
            "🔒 <b>Premium Feature Locked!</b>\n\n"
            "You don't have access to use this feature yet.\n"
            "💎 <b>Contact:</b> <a href='https://t.me/URS_LUCIFER'>LUCIFER</a> to upgrade.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Contact Admin", url="https://t.me/noobhusir")]])
        )
        return

    try:
        chat_id = callback_query.message.chat.id
        user_id = callback_query.from_user.id
        
        # 1. Send a NEW message with a Cancel button (Fixes MessageNotModified)
        prompt_text = (
            "📦 <b>Adda247 Extractor</b>\n\n"
            "Please send the <b>Package ID</b> to extract all subjects.\n\n"
            "⏱️ <i>You have 2 minutes to respond.</i>"
        )
        cancel_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="adda_cancel")]
        ])
        
        await callback_query.message.reply_text(prompt_text, reply_markup=cancel_markup)
        await callback_query.answer()
        
        # 2. Set state with a unique session ID and listen for input
        session_id = str(uuid.uuid4())
        user_states[user_id] = {'state': 'waiting', 'session': session_id}
        
        try:
            # Listen for the next text message from this specific user (Pinnacle logic)
            msg = await client.ask(
                chat_id=chat_id,
                filters=filters.text & filters.user(user_id),
                timeout=120  # 2 minutes timeout
            )
            
            # Check if session is still valid (they didn't cancel or restart)
            current_session = user_states.get(user_id, {})
            if current_session.get('session') != session_id:
                return  # Session expired or cancelled, ignore this message
            
            del user_states[user_id]
            text = msg.text.strip()
            
            if text.lower() == '/cancel':
                await msg.reply_text("❌ Process cancelled.")
                return
                
            if not text.isdigit():
                await msg.reply_text("❌ Please send a valid numeric Package ID.")
                return
                
            # Start extraction
            await extract_adda247_package(client, chat_id, text, callback_query.from_user)
            
        except asyncio.TimeoutError:
            if user_id in user_states:
                del user_states[user_id]
            await client.send_message(chat_id, "⏱️ <b>Time's up!</b> You took too long to respond. Process cancelled.")
            
    except Exception as e:
        print(f"Error in adda247_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

# ===================== CANCEL BUTTON HANDLER ===================== #
@app.on_callback_query(filters.regex("^adda_cancel$"))
async def adda_cancel_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in user_states and user_states[user_id].get('state') == 'waiting':
        del user_states[user_id]  # Delete state to invalidate the session
        await callback_query.message.edit_text("❌ <b>Process Cancelled.</b>")
        await callback_query.answer("Cancelled", show_alert=False)
    else:
        await callback_query.answer("Nothing to cancel.", show_alert=True)

# ===================== COMMAND HANDLER (UNCHANGED) ===================== #
@app.on_message(filters.command("addafree"))
async def adda_command_handler(client, m):
    try:
        pkg_msg = await client.ask(
            m.chat.id,
            "📦 <b>Adda247 Extractor</b>\n\nSend the <b>Package ID</b>.\n\n❌ Send <code>/cancel</code> to abort.",
            filters=filters.text,
            timeout=120
        )

        text = pkg_msg.text.strip()
        if text.lower() == "/cancel":
            return await m.reply_text("❌ Process cancelled.")
        if not text.isdigit():
            return await m.reply_text("❌ Please send a valid numeric Package ID.")

        await extract_adda247_package(client, m.chat.id, text, m.from_user)

    except asyncio.TimeoutError:
        await m.reply_text("⏱️ <b>Time's up!</b> Process cancelled.")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        await m.reply_text(f"❌ <b>Error:</b>\n<code>{e}</code>")
