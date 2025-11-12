
import requests 
import datetime, pytz, re, aiofiles, subprocess, os, base64, io, asyncio, time
import json, tqdm, urllib.parse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from base64 import b64decode
from pyrogram import filters
from Extractor import app
from config import PREMIUM_LOGS, THUMB_URL
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init
from termcolor import colored
from pyrogram.errors import FloodWait, RPCError
from pyrogram.session import Session
from contextlib import asynccontextmanager
import aiohttp
import logging
from datetime import timedelta

# Initialize colorama for Windows compatibility
init(autoreset=True)

appname = "Utkarsh"
txt_dump = PREMIUM_LOGS
MAX_CONCURRENT_REQUESTS = 1000  # Increased concurrency for faster processing
MAX_RETRIES = 15  # For request retry logic
TIMEOUT = 90  # Increased timeout for large batches
UPDATE_DELAY = 5  # Delay between message updates
SESSION_TIMEOUT = 200  # Session timeout in seconds
EDIT_LOCK = asyncio.Lock()
MAX_WORKERS = 5000  # Increased workers for better performance
UPDATE_INTERVAL = 15  # Update progress message every 15 seconds
CHECKPOINT_FILE = "batch_checkpoint.json"

class SessionManager:
    def __init__(self, app):
        self.app = app
        self.lock = asyncio.Lock()
        self._session = None
        self.last_used = 0
        
    async def get_session(self):
        async with self.lock:
            current_time = time.time()
            if self._session is None or (current_time - self.last_used) > SESSION_TIMEOUT:
                if self._session:
                    await self._session.stop()
                self._session = await self.app.storage.conn.get_session()
                self.last_used = current_time
            return self._session
            
    async def release(self):
        async with self.lock:
            if self._session:
                try:
                    await self._session.stop()
                except Exception:
                    pass
                finally:
                    self._session = None

@asynccontextmanager
async def managed_edit(message, session_manager):
    """Context manager for safe message editing with session management"""
    try:
        await session_manager.get_session()
        yield
    except FloodWait as e:
        print(colored(f"⚠️ FloodWait: Waiting for {e.value} seconds", "yellow"))
        await asyncio.sleep(e.value)
    except Exception as e:
        print(colored(f"❌ Error in message edit: {str(e)}", "red"))
    finally:
        await session_manager.release()

async def safe_edit_message(message, text):
    """Safely edit a message with retry logic and delay"""
    async with EDIT_LOCK:  # Use a lock to prevent concurrent edits
        for attempt in range(MAX_RETRIES):
            try:
                await asyncio.sleep(UPDATE_DELAY)  # Add delay between edits
                await message.edit(text)
                return True
            except FloodWait as e:
                print(colored(f"⚠️ FloodWait: Waiting for {e.value} seconds", "yellow"))
                await asyncio.sleep(e.value)
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    print(colored(f"❌ Failed to edit message after {MAX_RETRIES} attempts: {e}", "red"))
                    return False
                await asyncio.sleep(UPDATE_DELAY * 2)
        return False

def decrypt(enc):
    enc = b64decode(enc)
    Key = '%!$!%_$&!%F)&^!^'.encode('utf-8') 
    iv =  '#*y*#2yJ*#$wJv*v'.encode('utf-8') 
    cipher = AES.new(Key, AES.MODE_CBC, iv)
    plaintext =  unpad(cipher.decrypt(enc), AES.block_size)
    b = plaintext.decode('utf-8')
    return b

@app.on_message(filters.command(["utkarsh", "utk", "utk_dl"]))  # Added more handlers
async def handle_utk_logic(app, m):
    session_manager = SessionManager(app)
    start_time = time.time()
    editable = await m.reply_text(
        f"╭━━━━━━━『 <b>⚡ LUCIFER EXTRACTOR</b> 』━━━━━━━╮\n"
        f"👤 <b>Authentication Required</b>\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"🪄 <b>Send your credentials below:</b>\n"
        f"➡️ Format → <code>ID*Password</code>\n\n"
        f"💡 <i>Example:</i> <code>UTK12345*mysecurepass</code>"
    )

    
    input1 = await app.listen(chat_id=m.chat.id)
    raw_text = input1.text
    await input1.delete()
    
    print(colored("🔄 Attempting login to Utkarsh...", "cyan"))
    
    # Improved token fetch with retry logic
    for attempt in range(MAX_RETRIES):
        try:
            token_response = requests.get('https://online.utkarsh.com/web/home/get_states', timeout=TIMEOUT)
            token = token_response.json()["token"]
            print(colored(f"✅ Token obtained successfully", "green"))
            break
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2)
                continue
            else:
                print(colored(f"❌ Failed to get token: {e}", "red"))
                await safe_edit_message(editable, "❌ Failed to connect to Utkarsh servers. Please try again later.")
                return
    
    headers = {
            'accept':'application/json, text/javascript, */*; q=0.01',
            'content-type':'application/x-www-form-urlencoded; charset=UTF-8',
            'x-requested-with':'XMLHttpRequest',
            'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'origin':'https://online.utkarsh.com',
            'accept-encoding':'gzip, deflate, br, zstd',
            'accept-language':'en-US,en;q=0.9',
            'cookie':f'csrf_name={token}; ci_session=tb0uld02neaa4ujs1g4idb6l8bmql8jh'}
    
    if '*' in raw_text:
        ids, ps = raw_text.split("*")
        data = "csrf_name="+token+"&mobile="+ids+"&url=0&password="+ps+"&submit=LogIn&device_token=null"
        
        try:
            log_response = requests.post('https://online.utkarsh.com/web/Auth/login', headers=headers, data=data, timeout=TIMEOUT).json()["response"].replace('MDE2MTA4NjQxMDI3NDUxNQ==','==').replace(':', '==')
            dec_log = decrypt(log_response)
            dec_logs = json.loads(dec_log)
            error_message = dec_logs["message"]
            status = dec_logs['status']
            
            if status:
                await safe_edit_message(editable, "✅ <b>Login successful!</b>")
                print(colored("✅ Login successful!", "green"))
            else:
                await safe_edit_message(editable, f'❌ Login Failed - {error_message}')
                print(colored(f"❌ Login failed: {error_message}", "red"))
                return
        except Exception as e:
            await safe_edit_message(editable, f'❌ Error during login: {str(e)}')
            print(colored(f"❌ Exception during login: {e}", "red"))
            return
    else:
        await safe_edit_message(editable, "❌ <b>Invalid format!</b>\n\nPlease send ID and password in this format: <code>ID*Password</code>")
        return

    # Fetch course data with better error handling
    try:
        data2 = "type=Batch&csrf_name="+ token +"&sort=0"
        res2 = requests.post('https://online.utkarsh.com/web/Profile/my_course', headers=headers, data=data2, timeout=TIMEOUT).json()["response"].replace('MDE2MTA4NjQxMDI3NDUxNQ==','==').replace(':', '==')
        decrypted_res = decrypt(res2)
        dc = json.loads(decrypted_res)
        dataxxx = dc['data']
        bdetail = dataxxx.get("data", [])  
        
        if not bdetail:
            await safe_edit_message(editable, "❌ No courses found in your account.")
            print(colored("⚠️ No courses found in user account", "yellow"))
            return
            
        cool = ""
        FFF = "🔸 <b>BATCH INFORMATION</b> 🔸"
        Batch_ids = ''
        
        print(colored(f"📚 Found {len(bdetail)} courses:", "cyan"))
        for item in bdetail:
            id = item.get("id")
            batch = item.get("title")
            price = item.get("mrp")
            aa = f"<code>{id}</code> - <b>{batch}</b> 💰 ₹{price}\n\n"
            print(colored(f"  • {batch} (ID: {id}) - ₹{price}", "white"))
            if len(f'{cool}{aa}') > 4096:
                cool = ""
            cool += aa
            Batch_ids += str(id) + '&'
        Batch_ids = Batch_ids.rstrip('&')
        
        login_msg = f'<b>✅ {appname} Authentication Successful</b>\n'    
        login_msg += f'\n<b>🆔 Credentials:</b> <code>{raw_text}</code>\n\n'
        login_msg += f'\n\n<b>📚 Available Batches</b>\n\n{cool}'    
        
        # Send login info to log channel
        copiable = await app.send_message(txt_dump, login_msg)
        
        # Send formatted batch info to user
        await safe_edit_message(editable, f'{FFF}\n\n{cool}')
    
        # Ask for batch ID selection
        editable1 = await m.reply_text(
            f"<b>📥 Send the Batch ID to download</b>\n\n"
            f"<b>💡 For ALL batches:</b> <code>{Batch_ids}</code>\n\n"
            f"<i>Supports multiple IDs separated by '&'</i>"
        )
        
        user_id = int(m.chat.id)
        input2 = await app.listen(chat_id=m.chat.id)
        await input2.delete()
        await editable.delete()
        await editable1.delete()
        
        # Process batch ID selection
        if "&" in input2.text:
            batch_ids = input2.text.split('&')
        else:
            batch_ids = [input2.text]

        # Process each selected batch
        for batch_id in batch_ids:
            batch_id = batch_id.strip()  # Clean input
            start_time = datetime.datetime.now()
            progress_msg = await m.reply_text(f"⏳ <b>Processing batch ID:</b> <code>{batch_id}</code>...")
            
            # Get batch name
            bname = next((x['title'] for x in bdetail if str(x['id']) == batch_id), None)
            if not bname:
                await safe_edit_message(progress_msg, f"❌ Batch ID <code>{batch_id}</code> not found!")
                continue
                
            print(colored(f"\n📦 Processing batch: {bname} (ID: {batch_id})", "cyan"))
                
            # Fetch subject data
            try:
                data4 = {
                    'tile_input': f'{{"course_id": {batch_id},"revert_api":"1#0#0#1","parent_id":0,"tile_id":"0","layer":1,"type":"course_combo"}}',
                    'csrf_name': token
                }
                Key = '%!$!%_$&!%F)&^!^'.encode('utf-8') 
                iv = '#*y*#2yJ*#$wJv*v'.encode('utf-8')   
                cipher = AES.new(Key, AES.MODE_CBC, iv)
                padded_data = pad(data4['tile_input'].encode(), AES.block_size)
                encrypted_data = cipher.encrypt(padded_data)
                encoded_data = base64.b64encode(encrypted_data).decode()
                data4['tile_input'] = encoded_data
                
                res4 = requests.post("https://online.utkarsh.com/web/Course/tiles_data", headers=headers, data=data4, timeout=TIMEOUT).json()["response"].replace('MDE2MTA4NjQxMDI3NDUxNQ==','==').replace(':', '==')
                res4_dec = decrypt(res4)
                res4_json = json.loads(res4_dec)
                subject = res4_json.get("data", [])
                
                if not subject:
                    await safe_edit_message(progress_msg, f"❌ No subjects found in batch <code>{batch_id}</code>")
                    continue
                    
                subjID = "&".join([id["id"] for id in subject])
                print(colored(f"📚 Found {len(subject)} subjects", "cyan"))
                
                subject_ids = subjID.split('&')
                
                # Process subjects with new method
                all_urls = await process_batch_subjects(app, subject_ids, subject, batch_id, headers, token, progress_msg, bname)
                
                if all_urls:
                    print(colored(f"✅ Successfully extracted {len(all_urls)} URLs from batch {bname}", "green"))
                    await login(app, user_id, m, all_urls, start_time, bname, batch_id, progress_msg, app_name="Utkarsh")
                else:
                    await safe_edit_message(progress_msg, f"⚠️ No content URLs found in batch <code>{bname}</code>")
            except Exception as e:
                print(colored(f"❌ Error processing batch {batch_id}: {e}", "red"))
                await safe_edit_message(progress_msg, f"❌ Error processing batch: {str(e)}")
        
        # Logout after processing all batches
        try:
            logout = requests.get("https://online.utkarsh.com/web/Auth/logout", headers=headers, timeout=TIMEOUT)
            if logout.status_code == 200:
                print(colored("✅ Logout successful", "green"))
                execution_time = time.time() - start_time
                print(colored(f"⏱️ Total execution time: {execution_time:.2f} seconds", "cyan"))
        except Exception as e:
            print(colored("⚠️ Failed to logout properly", "yellow"))
            
    except Exception as e:
        print(colored(f"❌ Error fetching courses: {e}", "red"))
        await safe_edit_message(editable, f"❌ Error fetching your courses: {str(e)}")
        return
    finally:
        await session_manager.release()

async def update_progress_safely(progress_msg, text, last_update_time, min_interval=UPDATE_INTERVAL):
    """Update progress message with rate limiting"""
    current_time = time.time()
    if current_time - last_update_time >= min_interval:
        try:
            await progress_msg.edit(text)
            return current_time
        except Exception as e:
            print(colored(f"Progress update skipped: {e}", "yellow"))
    return last_update_time

async def process_single_subject(app, subject_id, subject_list, batch_id, headers, token, progress_msg, current_subject, total_subjects):
    """Process a single subject with stable progress updates"""
    topicName = next((x['title'] for x in subject_list if str(x['id']) == subject_id), "Unknown Topic")
    start_time = time.time()
    last_update_time = 0
    
    # Initial progress update
    progress_text = (
        f"╭━━━━━━━『 ⚙️ <b>LUCIFER EXTRACTOR</b> 』━━━━━━━╮\n"
        f"🔄 <b>Processing Large Batch...</b>\n"
        f"📚 <b>Subject:</b> <code>{current_subject}/{total_subjects}</code>\n"
        f"🧩 <b>Now Extracting:</b> <code>{topicName}</code>\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    )

    last_update_time = await update_progress_safely(progress_msg, progress_text, last_update_time, 5)
    
    try:
        # Save checkpoint
        checkpoint_data = {
            "subject_id": subject_id,
            "current_subject": current_subject,
            "total_subjects": total_subjects,
            "batch_id": batch_id,
            "subject_name": topicName
        }
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint_data, f)
        
        # Get topics list
        data5 = {
            'tile_input': f'{{"course_id":{subject_id},"layer":1,"page":1,"parent_id":{batch_id},"revert_api":"1#0#0#1","tile_id":"0","type":"content"}}',
            'csrf_name': token
        }
        Key = '%!$!%_$&!%F)&^!^'.encode('utf-8') 
        iv = '#*y*#2yJ*#$wJv*v'.encode('utf-8')   
        cipher = AES.new(Key, AES.MODE_CBC, iv)
        padded_data = pad(data5['tile_input'].encode(), AES.block_size)
        encrypted_data = cipher.encrypt(padded_data)
        encoded_data = base64.b64encode(encrypted_data).decode()
        data5['tile_input'] = encoded_data

        res5 = requests.post(
            "https://online.utkarsh.com/web/Course/tiles_data", 
            headers=headers, 
            data=data5, 
            timeout=TIMEOUT
        ).json()["response"].replace('MDE2MTA4NjQxMDI3NDUxNQ==','==').replace(':', '==')
        
        decres5 = decrypt(res5)
        res5l = json.loads(decres5)
        resp5 = res5l.get("data", {})

        if not resp5:
            return []
        
        res5list = resp5.get("list", [])
        topic_ids = [str(id["id"]) for id in res5list]
        
        all_topic_urls = []
        total_topics = len(topic_ids)
        processed_topics = 0
        last_update_time = time.time()
        
        # Process topics with improved concurrency
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Process topics in smaller chunks to prevent overload
            chunk_size = 5
            for i in range(0, len(topic_ids), chunk_size):
                chunk = topic_ids[i:i + chunk_size]
                futures = []
                
                for t in chunk:
                    future = executor.submit(
                        process_topic, 
                        subject_id, 
                        t, 
                        batch_id, 
                        headers, 
                        token, 
                        Key, 
                        iv
                    )
                    futures.append(future)
                
                # Process chunk results
                for future in as_completed(futures):
                    try:
                        topic_urls = future.result()
                        if topic_urls:
                            all_topic_urls.extend(topic_urls)
                        
                        processed_topics += 1
                        current_time = time.time()
                        
                        # Update progress less frequently
                        if current_time - last_update_time >= UPDATE_INTERVAL:
                            elapsed = current_time - start_time
                            eta = (elapsed / processed_topics) * (total_topics - processed_topics) if processed_topics > 0 else 0
                            
                            progress_text = (
                                f"🔄 <b>Processing Large Batch</b>\n"
                                f"├─ Subject: {current_subject}/{total_subjects}\n"
                                f"├─ Name: <code>{topicName}</code>\n"
                                f"├─ Topics: {processed_topics}/{total_topics}\n"
                                f"├─ Links: {len(all_topic_urls)}\n"
                                f"├─ Time: {str(timedelta(seconds=int(elapsed)))}\n"
                                f"└─ ETA: {str(timedelta(seconds=int(eta)))}"
                            )
                            last_update_time = await update_progress_safely(progress_msg, progress_text, last_update_time)
                            
                    except Exception as e:
                        print(colored(f"  ⚠️ Error processing topic: {e}", "yellow"))
                        continue
                
                # Small delay between chunks
                await asyncio.sleep(1)
        
        # Clean up checkpoint after successful processing
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            
        return all_topic_urls
        
    except Exception as e:
        print(colored(f"  ❌ Error processing subject {topicName}: {e}", "red"))
        return []

def process_topic(subject_id, topic_id, batch_id, headers, token, Key, iv):
    """Process a single topic (runs in thread)"""
    try:
        data5 = {
            'tile_input': f'{{"course_id":{subject_id},"parent_id":{batch_id},"layer":2,"page":1,"revert_api":"1#0#0#1","subject_id":{topic_id},"tile_id":0,"topic_id":{topic_id},"type":"content"}}',
            'csrf_name': token
        }
        
        cipher = AES.new(Key, AES.MODE_CBC, iv)
        padded_data = pad(data5['tile_input'].encode(), AES.block_size)
        encrypted_data = cipher.encrypt(padded_data)
        encoded_data = base64.b64encode(encrypted_data).decode()
        data5['tile_input'] = encoded_data
        
        res6 = requests.post(
            "https://online.utkarsh.com/web/Course/tiles_data", 
            headers=headers, 
            data=data5, 
            timeout=TIMEOUT
        ).json()["response"].replace('MDE2MTA4NjQxMDI3NDUxNQ==','==').replace(':', '==')
        
        decres6 = decrypt(res6)
        res6l = json.loads(decres6)
        resp5 = res6l.get("data", {})
        
        if not resp5:
            return []
        
        res6list = resp5.get("list", [])
        topic_idss = [str(id["id"]) for id in res6list]
        
        topic_urls = []
        for tt in topic_idss:
            try:
                data6 = {
                    'layer_two_input_data': f'{{"course_id":{subject_id},"parent_id":{batch_id},"layer":3,"page":1,"revert_api":"1#0#0#1","subject_id":{topic_id},"tile_id":0,"topic_id":{tt},"type":"content"}}',
                    'content': 'content',
                    'csrf_name': token
                }
                encoded_data = base64.b64encode(data6['layer_two_input_data'].encode()).decode()
                data6['layer_two_input_data'] = encoded_data
                
                res6 = requests.post(
                    "https://online.utkarsh.com/web/Course/get_layer_two_data", 
                    headers=headers, 
                    data=data6, 
                    timeout=TIMEOUT
                ).json()["response"].replace('MDE2MTA4NjQxMDI3NDUxNQ==','==').replace(':', '==')
                
                decres6 = decrypt(res6)
                res6_json = json.loads(decres6)
                res6data = res6_json.get('data', {})
                
                if not res6data:
                    continue
                
                res6_list = res6data.get('list', [])
                for item in res6_list:
                    title = item.get("title", "").replace("||", "-").replace(":", "-")
                    bitrate_urls = item.get("bitrate_urls", [])
                    url = None
                    
                    for url_data in bitrate_urls:
                        if url_data.get("title") == "720p":
                            url = url_data.get("url")
                            break
                        elif url_data.get("name") == "720x1280.mp4":
                            url = url_data.get("link") + ".mp4"
                            url = url.replace("/enc/", "/plain/")
                        
                    if url is None:
                        url = item.get("file_url")
                    
                    if url and not url.endswith('.ws'):
                        if url.endswith(("_0_0", "_0")):
                            url = "https://apps-s3-jw-prod.utkarshapp.com/admin_v1/file_library/videos/enc_plain_mp4/{}/plain/720x1280.mp4".format(url.split("_")[0])
                        elif not url.startswith("https://") and not url.startswith("http://"):
                            url = f"https://youtu.be/{url}"
                        cc = f'{title}: {url}'
                        topic_urls.append(cc)
                        
            except Exception as e:
                print(colored(f"  ⚠️ Error processing subtopic {tt}: {e}", "yellow"))
                continue
                
        return topic_urls
        
    except Exception as e:
        print(colored(f"  ⚠️ Error processing topic {topic_id}: {e}", "yellow"))
        return []

async def process_batch_subjects(app, subject_ids, subject_list, batch_id, headers, token, progress_msg, bname):
    """Process subjects with improved stability for large batches"""
    all_urls = []
    total_subjects = len(subject_ids)
    batch_start_time = time.time()
    last_update_time = 0
    
    # Check for existing checkpoint
    start_index = 0
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                checkpoint = json.load(f)
                if checkpoint.get("batch_id") == batch_id:
                    start_index = checkpoint.get("current_subject", 0) - 1
                    print(colored(f"📝 Resuming from checkpoint: Subject {start_index + 1}", "cyan"))
        except:
            pass
    
    for idx, subject_id in enumerate(subject_ids[start_index:], start_index + 1):
        try:
            # Process subject
            subject_urls = await process_single_subject(
                app, 
                subject_id, 
                subject_list, 
                batch_id, 
                headers, 
                token, 
                progress_msg,
                idx,
                total_subjects
            )
            
            if subject_urls:
                all_urls.extend(subject_urls)
            
            # Update batch progress less frequently
            current_time = time.time()
            if current_time - last_update_time >= UPDATE_INTERVAL:
                elapsed = current_time - batch_start_time
                eta = (elapsed / idx) * (total_subjects - idx) if idx > 0 else 0
                
                progress_text = (
                    f"╭━━━━━━━『 ⚡ <b>LUCIFER EXTRACTOR</b> 』━━━━━━━╮\n"
                    f"📦 <b>Batch Progress:</b>\n"
                    f"├─ ✅ <b>Completed:</b> <code>{idx}/{total_subjects}</code> subjects\n"
                    f"├─ 🔗 <b>Total Links:</b> <code>{len(all_urls)}</code>\n"
                    f"├─ ⏱️ <b>Elapsed:</b> <code>{str(timedelta(seconds=int(elapsed)))}</code>\n"
                    f"└─ 🕒 <b>ETA:</b> <code>{str(timedelta(seconds=int(eta)))}</code>\n"
                    f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
                )

                last_update_time = await update_progress_safely(progress_msg, progress_text, last_update_time)
            
            # Small delay between subjects
            await asyncio.sleep(1)
            
        except Exception as e:
            print(colored(f"❌ Error processing subject: {e}", "red"))
            continue
            
    return all_urls

async def login(app, user_id, m, all_urls, start_time, bname, batch_id, progress_msg, app_name="Utkarsh", price=None, start_date=None, imageUrl=None):
    try:
        bname = await sanitize_bname(bname)
        file_path = f"{bname}.txt"
        
        await safe_edit_message(progress_msg, "💾 Creating file with extracted URLs...")
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.writelines([url + '\n' for url in all_urls])
            
        # Analyze content types
        all_text = "\n".join(all_urls)
        video_count = len([url for url in all_urls if any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.mpd', 'youtu.be', 'youtube.com'])])
        pdf_count = len([url for url in all_urls if '.pdf' in url.lower()])
        drm_count = len([url for url in all_urls if any(ext in url.lower() for ext in ['.mpd', '.m3u8', 'drm'])])
        image_count = len([url for url in all_urls if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif'])])
        doc_count = len([url for url in all_urls if any(ext in url.lower() for ext in ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'])])
        other_count = len(all_urls) - (video_count + pdf_count + image_count + doc_count)
        
        # Get user info
        user = await app.get_users(user_id)
        contact_link = f"[{user.first_name}](tg://openmessage?user_id={user_id})"
        
        # Prepare statistics
        local_time = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
        formatted_time = local_time.strftime("%d-%m-%Y %H:%M:%S")
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        minutes, seconds = divmod(duration.total_seconds(), 60)
        
        # Prepare modern caption with emojis and formatting
        caption = (
            f"╭━━━━━━━『 <b>⚡LUCIFER EXTRACTOR</b> 』━━━━━━━╮\n"
            f"📱 <b>App Name:</b> <code>{app_name}</code>\n"
            f"📚 <b>Batch:</b> <code>{bname}</code> | 🆔 <code>{batch_id}</code>\n"
            f"🕒 <b>Extraction Time:</b> <code>{int(minutes):02d}:{int(seconds):02d}</code>\n"
            f"📅 <b>Date:</b> <code>{formatted_time} IST</code>\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"╭━━━━━━━『 <b>📊 CONTENT STATS</b> 』━━━━━━━╮\n"
            f"📁 <b>Total Links:</b> <code>{len(all_urls)}</code>\n"
            f"🎬 <b>Videos:</b> <code>{video_count}</code>\n"
            f"📄 <b>PDFs:</b> <code>{pdf_count}</code>\n"
            f"🖼 <b>Images:</b> <code>{image_count}</code>\n"
            f"📑 <b>Documents:</b> <code>{doc_count}</code>\n"
            f"📦 <b>Others:</b> <code>{other_count}</code>\n"
            f"🔐 <b>Protected:</b> <code>{drm_count}</code>\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"⚙️ <b>Extractor:</b> <code>LUCIFER EXTRACTOR ⚡</code>\n"
            f"👑 <b>Admin:</b> <a href='https://t.me/NOOBHUSIR'>LUCIFER ⚡</a>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        
        # Send file with thumbnail
        await safe_edit_message(progress_msg, "📤 Uploading file with extracted links...")
        
        try:
            # Download thumbnail if available
            thumb_path = None
            if THUMB_URL:
                thumb_path = f"thumb_{bname}.jpg"
                async with aiofiles.open(thumb_path, 'wb') as f:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(THUMB_URL) as response:
                            await f.write(await response.read())
            
            # Send document
            if thumb_path and os.path.exists(thumb_path):
                copy = await m.reply_document(
                    document=file_path,
                    caption=caption,
                    thumb=thumb_path
                )
                await app.send_document(txt_dump, file_path, caption=caption, thumb=thumb_path)
                os.remove(thumb_path)
            else:
                copy = await m.reply_document(document=file_path, caption=caption)
                await app.send_document(txt_dump, file_path, caption=caption)
            
            os.remove(file_path)
            await progress_msg.delete()
            print(colored("✅ File sent successfully!", "green"))
            
            # Print summary in terminal
            print(colored("\n📊 EXTRACTION SUMMARY:", "cyan"))
            print(colored(f"📚 Batch: {bname}", "white"))
            print(colored(f"📁 Total Links: {len(all_urls)}", "white"))
            print(colored(f"🎬 Videos: {video_count}", "white"))
            print(colored(f"📄 PDFs: {pdf_count}", "white"))
            print(colored(f"🖼 Images: {image_count}", "white"))
            print(colored(f"📑 Documents: {doc_count}", "white"))
            print(colored(f"📦 Others: {other_count}", "white"))
            print(colored(f"🔐 Protected: {drm_count}", "white"))
            print(colored(f"⏱️ Process took: {int(minutes):02d}:{int(seconds):02d}", "white"))
            
        except Exception as e:
            await safe_edit_message(progress_msg, f"❌ Error sending file: {str(e)}")
            print(colored(f"❌ Error sending file: {e}", "red"))
            
    except Exception as e:
        print(colored(f"❌ Error in login function: {e}", "red"))
        await safe_edit_message(progress_msg, f"❌ Error: {str(e)}")

async def sanitize_bname(bname, max_length=50):
    """Clean batch name for safe file operations with advanced sanitization"""
    if not bname:
        return "Unknown_Batch"
        
    # Remove invalid filename characters
    bname = re.sub(r'[\\/:*?"<>|\t\n\r]+', '', bname).strip()
    
    # Replace spaces with underscores for better filenames
    bname = bname.replace(' ', '_')
    
    # Limit length
    if len(bname) > max_length:
        bname = bname[:max_length]
        
    # Ensure ASCII compatibility
    bname = ''.join(c for c in bname if ord(c) < 128)
    
    # If empty after sanitization, use default
    if not bname:
        bname = "Unknown_Batch"
        
    return bname
