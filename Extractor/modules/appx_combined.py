import asyncio
import aiohttp
import requests
import json
import os
import time
import base64
import jwt
import cloudscraper
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
from pyrogram import filters
from concurrent.futures import ThreadPoolExecutor
from Extractor import app
from config import PREMIUM_LOGS
from Extractor.modules.db import save_user_token

log_channel = PREMIUM_LOGS
MY_LOGO_URL = "https://i.ibb.co/BHQ2HsW5/JPEG-20260125-141038-953649353278939736.jpg"

india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d %b %Y, %I:%M %p")

# ===================== DECRYPT HELPERS =====================
def decrypt(enc):
    """Decrypt AES encrypted string"""
    if not enc:
        return ""
    try:
        enc = b64decode(enc.split(':')[0])
        key = b'638udh3829162018'
        iv = b'fedcba9876543210'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(enc), AES.block_size)
        return plaintext.decode('utf-8')
    except Exception as e:
        print(f"Decryption error: {e}")
        return ""

def download_thumbnail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            thumb_path = "thumb_temp.jpg"
            with open(thumb_path, "wb") as f:
                f.write(response.content)
            return thumb_path
        return None
    except Exception:
        return None

def decode_base64(encoded_str):
    """Decode base64 string"""
    try:
        return base64.b64decode(encoded_str).decode("utf-8")
    except Exception:
        return ""

# ===================== FETCH HELPERS =====================
async def fetch(session, url, headers):
    """Fetch and parse JSON response"""
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"Error fetching {url}: {response.status}")
                return {}
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            return json.loads(str(soup))
    except Exception as e:
        print(f"An error occurred while fetching {url}: {str(e)}")
        return {}

# ===================== VIDEO/PDF EXTRACTION =====================
async def fetch_item_details(session, api_base, course_id, item, headers, userid, app_name, path="Home", stats=None):
    """Extract video/PDF details from item"""
    vid_id = item.get("id")
    lines = []
    try:
        async with session.get(
            f"{api_base}/get/fetchVideoDetailsById?course_id={course_id}&video_id={vid_id}&folder_wise_course=1&ytflag=0",
            headers=headers
        ) as response:
            if not response.headers.get("Content-Type", "").startswith("application/json"):
                return []

            r4 = await response.json()
            data = r4.get("data", {})
            if not data:
                return []

            file_title = data.get("Title", "Untitled")
            prefix = ""
            if path:
                last_folder = path.split("<")[-1].strip()
                if last_folder != "Home":
                    prefix = f"[{last_folder}]"

            # YouTube video
            yt_id = data.get("video_id")
            if yt_id:
                lines.append(f"{prefix}{file_title}:https://youtu.be/{decrypt(yt_id)}\n")
                stats["youtube"] += 1
            # Direct download link
            file_link = data.get("download_link")
            if file_link:
                dec_link = decrypt(file_link)
                lines.append(f"{prefix}{file_title}:{dec_link}\n")
                stats["regular"] += 1

            # Encrypted links
            for link in data.get("encrypted_links", []):
                path1 = link.get("path")
                key1 = link.get("key")
                if path1 and key1:
                    dec_key1 = decrypt(key1)
                    decode_key1 = decode_base64(dec_key1)
                    dec_path1 = decode(path1)
                    lines.append(f"{prefix}{file_title}:{dec_path1}*{decode_key1}\n")
                    stats["regular"] += 1
                    break
                elif path1:
                    dec_path1 = decode(path1)
                    lines.append(f"{prefix}{file_title}:{dec_path1}\n")
                    stats["regular"] += 1
                    break

            # PDF files
            if data.get("material_type") in ("PDF", "VIDEO"):
                pdf1 = data.get("pdf_link", "")
                key1 = data.get("pdf_encryption_key", "")
                pdf2 = data.get("pdf_link2", "")
                key2 = data.get("pdf2_encryption_key", "")
                if pdf1:
                    dec_pdf1 = decrypt(pdf1)
                    dec_key1 = decrypt(key1)
                    lines.append(f"{prefix}{file_title}:{dec_pdf1}*{dec_key1}\n")
                    stats["pdf"] += 1
                if pdf2:
                    dec_pdf2 = decrypt(pdf2)
                    dec_key2 = decrypt(key2)
                    lines.append(f"{prefix}{file_title}:{dec_pdf2}*{dec_key2}")
                    stats["pdf"] += 1

    except Exception as e:
        print(f"💣 Video error {vid_id}: {e}")

    return lines

# ===================== FOLDER RECURSION =====================
async def fetch_folder_contents(session, api_base, course_id, folder_id, headers, userid, app_name, path="Home", stats=None):
    """Recursively fetch folder contents"""
    outputs = []
    
    try:
        async with session.get(
            f"{api_base}/get/folder_contentsv3?course_id={course_id}&parent_id={folder_id}&windowsapp=false&start=0",
            headers=headers
        ) as response:
            if response.status != 200:
                return []

            j = await response.json()
            data = j.get("data", [])
            if not data:
                return []

            for item in data:
                title = item.get("Title", "Untitled").strip()
                mtype = item.get("material_type")
                current_path = f"{path} < {title}"

                if mtype == "FOLDER":
                    sub = await fetch_folder_contents(
                        session, api_base, course_id,
                        item["id"], headers, userid, app_name, current_path, stats
                    )
                    outputs.extend(sub)
                else:
                    vids = await fetch_item_details(
                        session, api_base, course_id,
                        item, headers, userid, app_name, current_path, stats
                    )
                    outputs.extend(vids)

    except Exception as e:
        print(f"💣 Folder error {folder_id}: {e}")

    return outputs

# ===================== FOLDER-BASED EXTRACTION =====================
async def v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, 
                 sanitized_course_name, start_time, start, end, pricing, input2, msg, stats):
    """Extract course using folder-based method"""
    async with aiohttp.ClientSession() as session:
        all_outputs = await fetch_folder_contents(
            session, api_base, raw_text2, folder_id=-1,
            headers=hdr1, userid=userid, app_name=app_name, path="Home", stats=stats
        )

        if not all_outputs:
            return await message.reply_text("No content found.")

        filename = f"{sanitized_course_name}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            for line in all_outputs:
                f.write(line)

        elapsed = time.time() - start_time
        regular_count = stats["regular"]
        youtube_count = stats["youtube"]
        pdf_count = stats["pdf"]

        video_count = regular_count + youtube_count
        total_links = video_count + pdf_count

        mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
        caption = generate_caption(
            app_name,
            sanitized_course_name,
            raw_text2,
            pricing,
            total_links,
            video_count,
            regular_count,
            youtube_count,
            pdf_count,
            mention,
            time_new
        )
        await input2.delete(True)
        await msg.delete(True)
        thumb_path = await download_thumbnail(MY_LOGO_URL)

        await app.send_document(message.chat.id, filename, caption=caption, thumb=thumb_path)
        await app.send_document(log_channel, filename, caption=caption, thumb=thumb_path)

        os.remove(filename)
        await message.reply_text("Done✅")

# ===================== SUBJECT/TOPIC EXTRACTION =====================
async def process_video(session, api_base, course_id, sub_id, sub_name, top_id, top_name, video, hdr1, userid, app_name, stats):
    """Process individual video"""
    vid_id = video.get("id")
    vid_name = video.get("Title")
    lines = []
    
    try:
        r4 = await fetch(session, f"{api_base}/get/fetchVideoDetailsById?course_id={course_id}&video_id={vid_id}&ytflag=0&folder_wise_course=0", hdr1)
        
        if not r4 or not r4.get("data"):
            return None

        file_title = r4.get("data", {}).get("Title", "")
        file_link = r4.get("data", {}).get("download_link", "")
        yt_id = r4.get("data", {}).get("video_id", "")
        prefix = f"[{top_name}]"
        
        if yt_id:
            lines.append(f"{prefix}{file_title}:https://youtu.be/{decrypt(yt_id)}\n")
            stats["youtube"] += 1

        if file_link:
            dec_link = decrypt(file_link)
            lines.append(f"{prefix}{file_title}:{dec_link}\n")
            stats["regular"] += 1

        else:
            encrypted_links = r4.get("data", {}).get("encrypted_links", [])
            for link in encrypted_links:
                path1 = link.get("path")
                key1 = link.get("key")
                
                if path1 and key1:
                    dec_key1 = decrypt(key1)
                    decode_key1 = decode_base64(dec_key1)
                    dec_path1 = decrypt(path1) # Using decrypt for consistency with path encryption
                    lines.append(f"{prefix}{file_title}:{dec_path1}*{decode_key1}\n")
                    stats["regular"] += 1
                    break
                elif path1:
                    dec_path1 = decrypt(path1)
                    lines.append(f"{prefix}{file_title}:{dec_path1}\n")
                    stats["regular"] += 1
                    break
        if "material_type" in r4.get("data", {}):
            mt = r4["data"]["material_type"]
            if mt in ("PDF", "VIDEO"):
                pdf1 = r4["data"].get("pdf_link", "")
                key1 = r4["data"].get("pdf_encryption_key", "")
                pdf2 = r4["data"].get("pdf_link2", "")
                key2 = r4["data"].get("pdf2_encryption_key", "")
                
                if pdf1 and key1:
                    dec_pdf1 = decrypt(pdf1)
                    dec_key1 = decrypt(key1)
                    lines.append(f"{prefix}{file_title}:{dec_pdf1}*{dec_key1}\n")
                    stats["pdf"] += 1
                if pdf2 and key2:
                    dec_pdf2 = decrypt(pdf2)
                    dec_key2 = decrypt(key2)
                    lines.append(f"{prefix}{file_title}:{dec_pdf2}*{dec_key2}\n")
                    stats["pdf"] += 1
        
        return lines

    except Exception as e:
        print(f"An error occurred while processing video ID {vid_id}: {str(e)}")
        return None

async def handle_course(session, api_base, course_id, sub_id, sub_name, topic, headers, userid, app_name, stats):
    """Handle course with subjects/topics structure"""
    top_id = topic.get("topicid")
    top_name = topic.get("topic_name")

    print(f"\n\n➡ ENTER TOPIC: {sub_name} -> {top_name}")
    all_lines = []

    # Get concepts
    concept_url = f"{api_base}/get/allconceptfrmlivecourseclass?courseid={course_id}&subjectid={sub_id}&topicid={top_id}&start=-1"
    r_concept = await fetch(session, concept_url, headers)
    concepts = r_concept.get("data", []) or [{"conceptid": "", "concept_name": "All"}]

    for concept in concepts:
        con_id = concept.get("conceptid") or ""
        con_name = concept.get("concept_name", "Unknown")
        print(f"\n  ▶ ENTER CONCEPT: {con_name}")

        # Get videos for this concept
        list_url = f"{api_base}/get/livecourseclassbycoursesubtopconceptapiv3?courseid={course_id}&subjectid={sub_id}&topicid={top_id}&conceptid={con_id}&start=0"
        r_list = await fetch(session, list_url, headers)
        videos = sorted(r_list.get("data", []) or [], key=lambda x: int(x.get("id", 0)))

        print(f"    found {len(videos)} videos")

        # Process videos sequentially
        for idx, video in enumerate(videos, start=1):
            vid_id = video.get("id")
            print(f"      ▶ processing video [{idx}/{len(videos)}] ID={vid_id}")

            try:
                lines = await process_video(session, api_base, course_id, sub_id, sub_name, top_id, top_name, video, headers, userid, app_name, stats)
                if lines:
                    all_lines.extend(lines)
            except Exception as e:
                print(f"      💣 Video {vid_id} failed: {e}")

        print(f"  ✔ concept done: {con_name}")

    print(f"✔ topic complete: {top_name}\n")
    return all_lines

# ===================== CAPTION GENERATOR =====================
def generate_caption(app_name, txtn, raw_text2, pricing, total_links, video_count, regular_count, youtube_count, pdf_count, mention, time_new):
    """Generate formatted caption for documents"""
    return (
            f"<blockquote>📚 App: {app_name.upper()}</blockquote>\n\n"
            f"═══════ BATCH DETAILS ═══════\n"
            f"<blockquote>🌟 Batch Name: {txtn}\n"
            f"🆔 Batch ID: {raw_text2}\n"
            f"💸 Price : ₹{pricing}</blockquote>\n\n"
            f"═══════ LINK SUMMARY ═══════\n"
            f"<blockquote>🔢 Total Links: {total_links}\n"
            f"┠🎥 Videos : {video_count}\n"
            f"  ┠📺 Regular : {regular_count}\n"
            f"  ┠📻 YouTube : {youtube_count}\n"
            f"┠📁 Documents: {pdf_count}</blockquote>\n\n"
            f"👤 Generated By: {mention}\n"
            f"📅 Generated On: {time_new} IST"
        )

# ===================== MAIN HANDLERS =====================
@app.on_message(filters.command(["masterappx"]))
async def appex_v4_txt(app, message):
    """Main command handler"""
    api = await app.ask(message.chat.id, text="__Enter your AppX API Domain:__")
    api_txt = api.text
    name = api_txt.split('.')[0].replace("api", "") if api else api_txt.split('.')[0]
    
    if "api" in api_txt:
        await appex_v5_txt(app, message, api_txt, name)
    else:
        await app.send_message(message.chat.id, "__❌ Invalid API Format. Please check the example again.__")

async def appex_v5_txt(app, message, api, name):
    """Handle login and course extraction"""
    api_base = api.replace("http://", "https://") if api.startswith(("http://", "https://")) else f"https://{api}"
    app_name = api_base.replace("http://", "").replace("https://", "").replace("api.classx.co.in", "").replace("api.akamai.net.in", "").replace("apinew.teachx.in", "").replace("api.cloudflare.net.in", "").replace("api.appx.co.in", "").replace("/", "")

    input1 = await app.ask(
        message.chat.id, 
        text=(
            f"🔐 **LOGIN TO {app_name.upper()}**\n\n"
            f"Please choose one method:\n\n"
            f"1️⃣ **ID & Password**\n"
            f"Format: `Mobile*Password`\n\n"
            f"2️⃣ **Direct Token**\n"
            f"Paste your long token directly.\n\n"
            f"👇 **Send Details Below:**"
        )
    )
    raw_text = input1.text.strip()
    token, userid = None, "-2"

    # Login handling
    if '*' in raw_text:
        email, password = raw_text.split("*")
        raw_url = f"{api_base}/post/userLogin"
        headers = {
            "Auth-Key": "appxapi",
            "User-Id": "-2",
            "Authorization": "",
            "User_app_category": "",
            "Language": "en",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "okhttp/4.9.1"
        }
        data = {"email": email, "password": password}
        
        try:
            response = requests.post(raw_url, data=data, headers=headers)

            print("=" * 50)
            print("Legacy Login")
            print("HTTP Status:", response.status_code)
            print("Response:")
            print(response.text)

            response = response.json()
            status = response.get("status")

            if status == 200:
                userid = response["data"]["userid"]
                token = response["data"]["token"]
                await save_user_token(userid, token, api_base)
            
            else:
                second_api_url = f"{api_base}/post/userLogin?extra_details=0"
                second_headers = {
                    "auth-key": "appxapi",
                    "client-service": "Appx",
                    "source": "website",
                    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
                    "accept": "*/*",
                    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8"
                }
                second_data = {
                    "source": "website",
                    "phone": email,
                    "email": email,
                    "password": password,
                    "extra_details": "1"
                }
                
                second_response = requests.post(
                    second_api_url,
                    headers=second_headers,
                    data=second_data
                )

                print("=" * 50)
                print("Website Login")
                print("HTTP Status:", second_response.status_code)
                print("Response:")
                print(second_response.text)

                second_response = second_response.json()  
                if second_response.get("status") == 200:
                    userid = second_response["data"]["userid"]
                    token = second_response["data"]["token"]
                    await save_user_token(userid, token, api_base)
                else:
                    return await message.reply_text("__Login Failed__")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return await message.reply_text("__Please try again later. Maybe Password Wrong__")

        hdr1 = {
            "Client-Service": "Appx",
            "source": "website",
            "Auth-Key": "appxapi",
            "Authorization": token,
            "User-ID": userid
        }
    else:
        token = raw_text
        userid = jwt.decode(token, options={"verify_signature": False}).get("id")
        hdr1 = {
            "Client-Service": "Appx",
            "source": "website",
            "Auth-Key": "appxapi",
            "Authorization": token,
            "User-ID": userid
        }
        await save_user_token(userid, token, api_base)
    
    # Fetch courses
    scraper = cloudscraper.create_scraper()
    try:
        main_data = scraper.get(f"{api_base}/get/mycourseweb?userid={userid}", headers=hdr1).json()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return await message.reply_text("An error occurred while fetching your courses. Please try again later.")

    FFF = (
        "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "┃      📚  **AVAILABLE BATCHES**  📚      ┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        "**ID ➤ NAME**\n\n"
    )
    valid_ids = []

    if "data" in main_data and main_data["data"]:
        for course_data in main_data["data"]:
            batch_id = course_data.get("id")
            batch_name = course_data.get("course_name")
            start = course_data.get("start_date")
            end = course_data.get("end_date")
            pricing = course_data.get("price")
            FFF += f"`{batch_id}`   -   **{batch_name}**\n\n"
            valid_ids.append(batch_id)
    else:
        return await message.reply_text("__No Batches Found__")

    
        # ===================== SEND COURSE LIST =====================
    dl = (
        f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        f"┃      ✅  **LOGIN SUCCESSFUL**  ✅      ┃\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"🔑 **App:** `{app_name}`\n"
        f"🧬 **API:** `{api_base}`\n"
        f"🎫 **Token:** `{token}...`\n\n"
        f"{FFF}"
    )

    if len(FFF) <= 4096:
        await app.send_message(log_channel, dl)
        editable1 = await message.reply_text(
            f"✅ **Login Successful!**\n\n"
            f"`{token}`\n\n{FFF}"
        )
    else:
        plain_FFF = FFF.replace("**", "").replace("`", "")
        file_path = f"{app_name}_batches.txt"
        
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(f"✅ Login Successful for {app_name}\n\nToken: {token}\n\n{plain_FFF}")

        await app.send_document(
            message.chat.id, 
            document=file_path, 
            caption="__Select Course ID from the attached file.__"
        )
        await app.send_document(
            log_channel, 
            document=file_path, 
            caption=f"📂 Batch List for `{app_name}`"
        )
        
        os.remove(file_path) 
        editable1 = None

    # Get batch selection
    input2 = await app.ask(
        message.chat.id, 
        text=(
            "🚀 __Select Batches to Extract__\n\n"
            "Send Course ID(s) below.\n"
            "Separate multiple IDs with `&`"
        )
    )   
    batch_ids = input2.text.strip().split("&")
    batch_ids = [batch.strip() for batch in batch_ids if batch.strip() in valid_ids]

    if not batch_ids:
        await message.reply_text("__Invalid Course ID(s).__")
        await input2.delete(True)
        if editable1:
            await editable1.delete(True)
        return

    # Process each batch
    for raw_text2 in batch_ids:
        msg = await message.reply_text(f"__Extracting batch `{raw_text2}`__")
        start_time = time.time()
        stats = {
            "regular": 0,
            "youtube": 0,
            "pdf": 0
        }
        
        try:
            r = scraper.get(f"{api_base}/get/course_by_id?id={raw_text2}", headers=hdr1).json()
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            await message.reply_text("__Error please try again later.__")
            continue

        if not r.get("data"):
            course_name = next((course_data.get("course_name") for course_data in main_data["data"] if course_data.get("id") == raw_text2), "Course")
            sanitized_course_name = course_name.replace(':', '_').replace('/', '_')
            await v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, 
                        sanitized_course_name, start_time, start, end, pricing, input2, msg, stats)
            continue

        # Subject/topic-based extraction
        for i in r.get("data", []):
            txtn = i.get("course_name")
            filename = f"{raw_text2}_{txtn.replace(':', '_').replace('/', '_')}.txt"

            async with aiohttp.ClientSession() as session:
                with open(filename, 'w') as f:
                    try:
                        r1 = await fetch(session, f"{api_base}/get/allsubjectfrmlivecourseclass?courseid={raw_text2}&start=-1", hdr1)
        
                        for subject in r1.get("data", []):
                            sub_id = subject.get("subjectid")
                            sub_name = subject.get("subject_name")

                            r2 = await fetch(session, f"{api_base}/get/alltopicfrmlivecourseclass?courseid={raw_text2}&subjectid={sub_id}&start=-1", hdr1)
                            topics = sorted(r2.get("data", []), key=lambda x: x.get("topicid"))

                            for topic in topics:
                                data = await handle_course(session, api_base, raw_text2, sub_id, sub_name, topic, hdr1, userid, app_name, stats)
                                if data:
                                    f.writelines(data)
                    except Exception as e:
                        print(f"An error occurred while processing the course: {str(e)}")
                        await message.reply_text("An error occurred while processing the course. Please try again later.")
                        continue
                
                end_time = time.time()
                elapsed_time = end_time - start_time
                mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
                regular_count = stats["regular"]
                youtube_count = stats["youtube"]
                pdf_count = stats["pdf"]

                video_count = regular_count + youtube_count
                total_links = video_count + pdf_count
                print(f"Elapsed time: {elapsed_time:.1f} seconds")
                thumb_path = await download_thumbnail(MY_LOGO_URL)

                c_text = generate_caption(app_name, txtn, raw_text2, pricing, total_links, video_count, regular_count, youtube_count, pdf_count, mention, time_new)

                try:
                    await input2.delete(True)
                    await msg.delete(True)
                    await app.send_document(message.chat.id, filename, caption=c_text, thumb=thumb_path)
                    await app.send_document(log_channel, filename, caption=c_text, thumb=thumb_path)
                except Exception as e:
                    print(f"__Error on sending file__: {str(e)}")
                    course_name = next((course_data.get("course_name") for course_data in main_data["data"] if course_data.get("id") == raw_text2), "Course")
                    sanitized_course_name = course_name.replace(':', '_').replace('/', '_')
                    await v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, 
                                sanitized_course_name, start_time, start, end, pricing, input2, msg, stats)
                finally:
                    if os.path.exists(filename):
                        os.remove(filename)
