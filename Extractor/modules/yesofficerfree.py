import requests
import threading
import json
import cloudscraper
from pyrogram import filters
from Extractor import app
import os
import io
import asyncio
import aiohttp
import base64
from Crypto.Cipher import AES
from Extractor.modules.mix import v2_new
from Crypto.Util.Padding import unpad
from base64 import b64decode
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import time
from config import PREMIUM_LOGS
from Extractor.core.func import chk_user

log_channel = PREMIUM_LOGS
log_channel2 = PREMIUM_LOGS

# STATIC API + TOKEN
API_BASE = "https://yesofficerapi.classx.co.in"
TOKEN = (
"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9."
"eyJpZCI6IjY2MTYxIiwiZW1haWwiOiJzdWJoYXNpc2dhcmFpOTlAZ21haWwuY29tIiwidGltZXN0YW1wIjoxNzYwMTkyNzc1LCJ0ZW5hbnRUeXBlIjoidXNlciIsInRlbmFudE5hbWUiOiJ5ZXNvZmZpY2VyX2RiIiwidGVuYW50SWQiOiIiLCJkaXNwb3NhYmxlIjpmYWxzZX0.P6xupnCewq3YgVBxkT_h5y5JoAMr3HLQZGIdjtHl-Jo"
)

STATIC_HDR = {
    "Client-Service": "Appx",
    "source": "website",
    "Auth-Key": "appxapi",
    "Authorization": TOKEN,
    "User-ID": "-2"
}

# SAME DECRYPT FUNCTION
def decrypt(enc):
    enc = b64decode(enc.split(':')[0])
    key = '638udh3829162018'.encode('utf-8')
    iv = 'fedcba9876543210'.encode('utf-8')
    if len(enc) == 0:
        return ""
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(enc), AES.block_size)
    return plaintext.decode('utf-8')


def decode_base64(encoded_str):
    try:
        return base64.b64decode(encoded_str).decode('utf-8')
    except:
        return encoded_str


# SAME FETCH
async def fetch(session, url, headers):
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return {}
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            return json.loads(str(soup))
    except:
        return {}


# SAME PROCESSING
async def handle_course(session, api_base, bi, si, sn, topic, hdr1):
    ti = topic.get("topicid")
    url = f"{api_base}/get/livecourseclassbycoursesubtopconceptapiv3?courseid={bi}&subjectid={si}&topicid={ti}&conceptid=&start=-1"
    r3 = await fetch(session, url, hdr1)
    videos = sorted(r3.get("data", []), key=lambda x: x.get("id"))

    tasks = [
        process_video(session, api_base, bi, si, sn, ti, topic.get("topic_name"), v, hdr1)
        for v in videos
    ]
    results = await asyncio.gather(*tasks)
    return [x for block in results if block for x in block]


async def process_video(session, api_base, bi, si, sn, ti, tn, video, hdr1):
    vi = video.get("id")
    lines = []
    try:
        r4 = await fetch(
            session,
            f"{api_base}/get/fetchVideoDetailsById?course_id={bi}&video_id={vi}&ytflag=0&folder_wise_course=0",
            hdr1
        )

        if not r4.get("data"):
            return None

        d = r4["data"]
        title = d.get("Title", "")

        # direct download
        if d.get("download_link"):
            dec = decrypt(d["download_link"])
            lines.append(f"{title}:{dec}\n")

        # encrypted video_id → YouTube
        if d.get("video_id"):
            yid = decrypt(d["video_id"])
            lines.append(f"{title}:https://youtu.be/{yid}\n")

        # encrypted links fallback
        enc = d.get("encrypted_links", [])
        if enc:
            a = enc[0].get("path")
            k = enc[0].get("key")
            if a:
                da = decrypt(a)
                dk = decrypt(k) if k else ""
                dk2 = decode_base64(dk)
                if dk2:
                    lines.append(f"{title}:{da}*{dk2}\n")
                else:
                    lines.append(f"{title}:{da}\n")

        # PDF handling
        for p, pk in [
            (d.get("pdf_link"), d.get("pdf_encryption_key")),
            (d.get("pdf_link2"), d.get("pdf2_encryption_key"))
        ]:
            if p:
                dp = decrypt(p)
                dk = decrypt(pk) if pk else ""
                if dk and dk != "abcdefg":
                    lines.append(f"{title}:{dp}*{dk}\n")
                else:
                    lines.append(f"{title}:{dp}\n")

        return lines

    except Exception:
        return None


# ======================================
# MAIN CALLBACK — CALL FROM start.py
# ======================================
async def yesofficer_callback(client, callback_query):

    lol = await chk_user(callback_query, callback_query.from_user.id)
    if lol == 1:
        return

    await callback_query.message.reply_text("📡 Fetching YesOfficer batches...")

    scraper = cloudscraper.create_scraper()
    mc = scraper.get(f"{API_BASE}/get/mycoursev2?userid=-2", headers=STATIC_HDR).json()

    data = mc.get("data", [])
    if not data:
        return await callback_query.message.reply_text("❌ No batches found.")

    # MAKE TXT LIST
    txt = "𝗕𝗔𝗧𝗖𝗛 𝗜𝗗 ➤ 𝗕𝗔𝗧𝗖𝗛 𝗡𝗔𝗠𝗘\n\n"
    valid_ids = []

    for c in data:
        cid = str(c["id"])
        cn = c["course_name"]
        txt += f"`{cid}` — `{cn}`\n"
        valid_ids.append(cid)

    buf = io.BytesIO(txt.encode())
    buf.name = "yesofficer_batches.txt"

    await callback_query.message.reply_document(
        buf,
        caption="📦 All YesOfficer batches fetched.\n➡ Send ONE Batch ID to extract."
    )

    # ASK ONE BATCH
    ask = await app.ask(callback_query.message.chat.id, "📥 Send Batch ID:")

    bid = ask.text.strip()
    if bid not in valid_ids:
        return await callback_query.message.reply_text("❌ Invalid batch id.")

    await extract_yesofficer_batch(app, callback_query.message, bid)


# =================================================
# FINAL EXTRACTION (ONE BATCH) — SAME AS YOUR CODE
# =================================================
async def extract_yesofficer_batch(app, message, batch_id):

    m1 = await message.reply_text(f"⏳ Extracting `{batch_id}`...")

    filename = f"yesofficer_{batch_id}.txt"

    async with aiohttp.ClientSession() as session:
        with open(filename, "w", encoding="utf-8") as f:

            sub = await fetch(session, f"{API_BASE}/get/allsubjectfrmlivecourseclass?courseid={batch_id}&start=-1", STATIC_HDR)
            subjects = sub.get("data", [])

            for s in subjects:
                si = s["subjectid"]
                sn = s["subject_name"]

                top = await fetch(session, f"{API_BASE}/get/alltopicfrmlivecourseclass?courseid={batch_id}&subjectid={si}&start=-1", STATIC_HDR)
                topics = sorted(top.get("data", []), key=lambda x: x["topicid"])

                tasks = [handle_course(session, API_BASE, batch_id, si, sn, t, STATIC_HDR) for t in topics]
                results = await asyncio.gather(*tasks)

                for block in results:
                    if block:
                        f.writelines(block)

    caption = (
        f"╭━━━『 💠 𝐘𝐞𝐬𝐎𝐟𝐟𝐢𝐜𝐞𝐫 💠 』━━━╮\n"
        f"📚 Batch ID: `{batch_id}`\n"
        f"⚙️ Extractor: LUCIFER EXTRACTOR\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━╯"
    )

    await app.send_document(message.chat.id, filename, caption=caption)
    await app.send_document(log_channel, filename, caption=caption)

    await m1.delete()
    os.remove(filename)
