import io
import os
import re
import aiohttp
import pytz
import asyncio
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import MessageNotModified

from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

# ===================== CONFIG ===================== #
MY_LOGO_URL = "https://i.ibb.co/BHQ2HsW5/JPEG-20260125-141038-953649353278939736.jpg"

# ===================== HELPERS ===================== #
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|₹]', "", name).strip() + ".txt"

async def fetch_json_async(session, url: str, headers: dict = None):
    try:
        req_headers = headers or {}
        async with session.get(url, headers=req_headers, timeout=20) as r:
            if r.status == 200:
                return await r.json()
            else:
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

# ===================== EXTRACTION LOGIC ===================== #
async def extract_adda247_package(app: Client, chat_id: int, package_id: str, user, msg):
    thumb_path = None
    try:
        await msg.edit_text("⏳ <b>Fetching all subjects...</b> Please wait ⚡")
        
        # 1. Fetch Main Data (NO HEADERS REQUIRED)
        url_topics = f"https://adda-livid.vercel.app/api/topics?packageId={package_id}"
        async with aiohttp.ClientSession() as session:
            data_topics = await fetch_json_async(session, url_topics, headers={})

        if not data_topics:
            await msg.edit_text("😕 <b>Failed to fetch subjects.</b> API returned empty.")
            return

        subjects_list = data_topics.get("data", [])
        tests_list = data_topics.get("tests", [])

        if not subjects_list and not tests_list:
            await msg.edit_text("😕 <b>No subjects or tests found for this Package ID.</b>")
            return

        all_results = {}
        total_videos = 0
        total_pdfs = 0
        youtube_count = 0
        regular_count = 0
        total_tests = 0

        async with aiohttp.ClientSession() as session:
            # 2. Process Subjects, Chapters, and Media
            for i, subject in enumerate(subjects_list):
                subject_name = subject.get("subjectName", "Unknown Subject")
                chapters = subject.get("chapters", [])
                
                all_results[subject_name] = []
                
                for chapter in chapters:
                    chapter_name = chapter.get("chapterName", "Unknown Chapter")
                    media_list = chapter.get("media", [])
                    
                    for media in media_list:
                        # Check if tImg or pdfFileName exists
                        has_timg = bool(media.get("tImg"))
                        has_pdf = bool(media.get("pdfFileName"))
                        
                        # 🚨 FIX: If BOTH are missing, SKIP this media item entirely
                        if not has_timg and not has_pdf:
                            continue
                        
                        title = media.get("name", "No Title").strip()
                        
                        # --- Extract Video URL (if tImg exists) ---
                        if has_timg:
                            tImg = media.get("tImg", "")
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
                            
                            if video_url:
                                all_results[subject_name].append(f"[{chapter_name}] [VIDEO] {title}: {video_url}")
                                total_videos += 1
                                if "youtube.com" in video_url or "youtu.be" in video_url:
                                    youtube_count += 1
                                else:
                                    regular_count += 1

                        # --- Extract PDF URL (if pdfFileName exists) ---
                        if has_pdf:
                            pdf_filename = media.get("pdfFileName")
                            pdf_url = f"https://store.adda247.com/{pdf_filename}"
                            all_results[subject_name].append(f"[{chapter_name}] [PDF] {title}: {pdf_url}")
                            total_pdfs += 1
                
                # Update Progress
                try:
                    await msg.edit_text(
                        f"⏳ <b>Extracting Content...</b> Please wait ⚡\n\n"
                        f"📖 <b>Subject:</b> <code>{subject_name}</code>\n"
                        f"📊 <b>Progress:</b> {i+1}/{len(subjects_list)}\n"
                        f"🎥 <b>Videos found:</b> {total_videos}\n"
                        f"📄 <b>PDFs found:</b> {total_pdfs}\n"
                        f"📝 <b>Tests found:</b> {total_tests}"
                    )
                except MessageNotModified:
                    pass

            # 3. Process Mock Tests (NO FETCHING, JUST FRAME URL DIRECTLY)
            if tests_list:
                all_results["MOCK TESTS"] = []
                for test in tests_list:
                    mock_id = test.get("mockTestId")
                    test_title = test.get("title", "Unknown Test")
                    test_topic = test.get("topic", "General")
                    
                    # Frame the URL directly without fetching
                    test_url = f"https://ts-storetest.adda247.com/{mock_id}.json"
                    all_results["MOCK TESTS"].append(f"[{test_topic}] [TEST] {test_title}: {test_url}")
                    total_tests += 1
                        
                # Update Progress for Tests
                try:
                    await msg.edit_text(
                        f"⏳ <b>Extracting Tests...</b> Please wait ⚡\n\n"
                        f"📝 <b>Total Tests:</b> {len(tests_list)}\n"
                        f"🎥 <b>Videos found:</b> {total_videos}\n"
                        f"📄 <b>PDFs found:</b> {total_pdfs}\n"
                        f"📝 <b>Tests found:</b> {total_tests}"
                    )
                except MessageNotModified:
                    pass

        if total_videos == 0 and total_pdfs == 0 and total_tests == 0:
            await msg.edit_text("😕 <b>No content found in this package.</b>")
            return

        await msg.edit_text("⏳ <b>Generating file...</b> Almost done! ⚡")

        # 4. Build Output File
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

        # 5. Build Caption
        india_timezone = pytz.timezone("Asia/Kolkata")
        current_time = datetime.now(india_timezone)
        time_new = current_time.strftime("%d %b %Y, %I:%M %p")

        total_links = total_videos + total_pdfs + total_tests
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
            f"  ┠📻 YouTube : {youtube_count}\n"
            f"┠📝 Mock Tests : {total_tests}</blockquote>\n\n"
            f"👤 Generated By: {mention}\n"
            f"📅 Generated On: {time_new} IST"
        ).rstrip()

        # 6. Send Document
        await app.send_document(chat_id=chat_id, document=file_bytes, caption=caption, thumb=thumb_path, parse_mode="HTML")

        # 7. Log to Channel
        try:
            file_bytes.seek(0)
            await app.send_document(chat_id=PREMIUM_LOGS, document=file_bytes, caption=f"📡 <b>Adda247 Extract</b>\n\n{caption}", thumb=thumb_path, parse_mode="HTML")
        except Exception as e:
            print(f"⚠️ Error sending to log: {e}")

    except Exception as e:
        print(f"❌ CRITICAL ERROR IN EXTRACTION: {e}")
        await msg.edit_text(f"❌ <b>Bot crashed during extraction:</b>\n<code>{str(e)}</code>")
    finally:
        if thumb_path and os.path.exists(thumb_path):
            try: os.remove(thumb_path)
            except: pass

# ===================== CALLBACK HANDLER (LISTEN LOGIC) ===================== #
@app.on_callback_query(filters.regex("^adda247_"))
async def adda247_callback(app, callback_query):
    lol = await chk_user(callback_query, callback_query.from_user.id)
    if lol == 1:
        await callback_query.message.reply_text(
            "🔒 <b>Premium Feature Locked!</b>\n\n"
            "You don't have access to use this feature yet.\n"
            "💎 <b>Contact:</b> <a href='https://t.me/URS_LUCIFER'>LUCIFER</a> to upgrade.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Contact Admin", url="https://t.me/noobhusir")]])
        )
        return

    await callback_query.answer()
    chat_id = callback_query.message.chat.id
    
    # ✅ create ONE working message (don’t touch button msg)
    main_msg = await app.send_message(chat_id, "📦 <b>Adda247 Extractor</b>\n\n📝 <b>Send Package ID:</b>")
    
    try:
        # 👇 input using listen (Pinnacle logic)
        pkg_msg = await app.listen(chat_id)
        package_id = pkg_msg.text.strip()
        
        try:
            await pkg_msg.delete()
        except:
            pass
            
        if package_id.lower() == '/cancel':
            await main_msg.edit_text("❌ <b>Process Cancelled.</b>")
            await asyncio.sleep(2)
            await main_msg.delete()
            return
            
        if not package_id.isdigit():
            await main_msg.edit_text("❌ <b>Invalid Package ID.</b> Please send a numeric ID.")
            await asyncio.sleep(2)
            await main_msg.delete()
            return
            
        await main_msg.edit_text("⏳ <b>Processing...</b>")
        
        # Call extraction and pass main_msg for progress updates
        await extract_adda247_package(app, chat_id, package_id, callback_query.from_user, main_msg)
        
        # Delete the prompt message after success
        try:
            await main_msg.delete()
        except:
            pass
            
    except Exception as e:
        print(f"Error in adda247_callback listen: {e}")
        try:
            await main_msg.edit_text(f"❌ <b>Error:</b> {str(e)}")
        except:
            pass

# ===================== COMMAND HANDLER ===================== #
@app.on_message(filters.command("addafree"))
async def adda_command_handler(client, m):
    chat_id = m.chat.id
    main_msg = await client.send_message(chat_id, "📦 <b>Adda247 Extractor</b>\n\n📝 <b>Send Package ID:</b>")
    
    try:
        pkg_msg = await client.listen(chat_id)
        package_id = pkg_msg.text.strip()
        
        try:
            await pkg_msg.delete()
        except:
            pass
            
        if package_id.lower() == "/cancel":
            return await main_msg.edit_text("❌ <b>Process Cancelled.</b>")
            
        if not package_id.isdigit():
            return await main_msg.edit_text("❌ <b>Invalid Package ID.</b>")
            
        await main_msg.edit_text("⏳ <b>Processing...</b>")
        await extract_adda247_package(client, chat_id, package_id, m.from_user, main_msg)
        
        try:
            await main_msg.delete()
        except:
            pass
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        await main_msg.edit_text(f"❌ <b>Error:</b>\n<code>{e}</code>")
