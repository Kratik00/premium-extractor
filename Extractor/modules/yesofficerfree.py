import io
import json
import asyncio
import aiohttp
from pyromod import listen   
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from Extractor import app
from config import PREMIUM_LOGS
from Extractor.core.func import chk_user

# ---------------- STATIC CONFIG ----------------
API_BASE = "https://yesofficerapi.classx.co.in"
TOKEN = (
"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9."
"eyJpZCI6IjY2MTYxIiwiZW1haWwiOiJzdWJoYXNp"
"c2dhcmFpOTlAZ21haWwuY29tIiwidGltZXN0YW1w"
"IjoxNzYwMTkyNzc1LCJ0ZW5hbnRUeXBlIjoidXNl"
"ciIsInRlbmFudE5hbWUiOiJ5ZXNvZmZpY2VyX2Ri"
"IiwidGVuYW50SWQiOiIiLCJkaXNwb3NhYmxlIjpm"
"YWxzZX0.P6xupnCewq3YgVBxkT_h5y5JoAMr3HLQZGIdjtHl-Jo"
)

HDR = {
    "Auth-Key": "appxapi",
    "Client-Service": "Appx",
    "Authorization": TOKEN,
    "User-ID": "-2"
}

LOG = PREMIUM_LOGS

# ---------------------------------------------------
# BUTTON ENTRY (call from start.py)
# ---------------------------------------------------
async def yesofficer_callback(client, callback_query):

    # premium check
    lol = await chk_user(callback_query, callback_query.from_user.id)
    if lol == 1:
        return

    chat_id = callback_query.message.chat.id

    # separate new message (don't reply to callback)
    msg = await client.send_message(chat_id, "⏳ Fetching YesOfficer batches...")

    async with aiohttp.ClientSession() as ses:
        async with ses.get(f"{API_BASE}/get/mycoursev2?userid=-2", headers=HDR) as r:
            js = await r.json()

    data = js.get("data", [])

    if not data:
        return await client.send_message(chat_id, "❌ No batches found.")

    # ---------- CREATE BATCH LIST TEXT ----------
    txt = "📚 YESOFFICER — ALL BATCHES\n\n"
    valid_ids = []

    for c in data:
        cid = c["id"]
        name = c["course_name"]
        txt += f"{cid} — {name}\n"
        valid_ids.append(str(cid))

    # prepare file
    file_bytes = io.BytesIO(txt.encode())
    file_bytes.name = "yesofficer_batches.txt"

    # send file
    await client.send_document(
        chat_id=chat_id,
        document=file_bytes,
        caption=(
            "📦 **All batches fetched!**\n"
            "➡️ Now send the Batch ID you want to extract.\n"
            f"`Example: {valid_ids[0]}`"
        )
    )

    # ask for batch ID (pyromod)
    ask = await client.ask(
        chat_id,
        "📥 **Send any 1 Batch ID to extract:**"
    )

    bid = ask.text.strip()

    if bid not in valid_ids:
        return await client.send_message(chat_id, "❌ Invalid batch ID.")

    await extract_yesofficer_batch(client, msg, bid)



# ---------------------------------------------------
# EXTRACTION FUNCTION
# ---------------------------------------------------
async def extract_yesofficer_batch(app, message, batch_id):

    await app.send_message(message.chat.id, f"⏳ Extracting batch `{batch_id}`...")

    async with aiohttp.ClientSession() as ses:
        # subjects
        async with ses.get(
            f"{API_BASE}/get/allsubjectfrmlivecourseclass?courseid={batch_id}&start=-1",
            headers=HDR
        ) as r:
            s_json = await r.json()

        subjects = s_json.get("data", [])

        if not subjects:
            return await app.send_message(message.chat.id, "❌ No subjects found in this batch.")

        final_lines = []

        # LOOP SUBJECTS
        for sub in subjects:
            sid = sub["subjectid"]

            # fetch topics
            async with ses.get(
                f"{API_BASE}/get/alltopicfrmlivecourseclass?courseid={batch_id}&subjectid={sid}&start=-1",
                headers=HDR
            ) as r2:
                t_json = await r2.json()

            topics = t_json.get("data", [])

            # LOOP TOPICS
            for t in topics:
                tid = t["topicid"]

                # classes
                async with ses.get(
                    f"{API_BASE}/get/livecourseclassbycoursesubtopconceptapiv3?"
                    f"courseid={batch_id}&subjectid={sid}&topicid={tid}&conceptid=&start=-1",
                    headers=HDR
                ) as r3:
                    vc_json = await r3.json()

                classes = vc_json.get("data", [])
                for cls in classes:
                    title = cls.get("Title", "Untitled")
                    cid = cls.get("id")

                    # video details
                    async with ses.get(
                        f"{API_BASE}/get/fetchVideoDetailsById?course_id={batch_id}&video_id={cid}&ytflag=0",
                        headers=HDR
                    ) as r4:
                        vd = await r4.json()

                    if not vd.get("data"):
                        continue

                    link = vd["data"].get("download_link")
                    if link:
                        final_lines.append(f"{title}: {link}\n")

    # WRITE FILE
    out = "".join(final_lines)
    buf = io.BytesIO(out.encode())
    buf.name = f"yesofficer_{batch_id}.txt"

    caption = (
        f"╭━━━━━━━『 <b>🚀 COURSE INFO</b> 』━━━━━━━╮\n"
        f"📱 <b>App Name:</b> <code>YES OFFICER</code>\n"
        f"🎓 <b>Batch Name:</b> <code>{batch_name}</code>\n"
        f"🕒 <b>Validity:</b> <code>{start}</code> ➜ <code>{end}</code>\n"
        f"💰 <b>Price:</b> <code>{pricing}</code>\n"
        f"⏱️ <b>Extracted In:</b> <code>{elapsed_time:.1f}s</code>\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
  
        f"╭━━━━━━━『 <b>💾 DOWNLOAD INFO</b> 』━━━━━━━╮\n"
        f"🖼️ <b>Thumbnail:</b> <a href='{thumbnail_url}'>Click Here</a>\n"
        f"⚡ <b>Extractor:</b> <code>LUCIFER EXTRACTOR</code>\n"
        f"👑 <b>Admin:</b> <a href='https://t.me/URS_LUCIFER'>LUCIFER</a>\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    )

    # send to user
    await app.send_document(
        chat_id=message.chat.id,
        document=buf,
        caption=caption
    )

    # send to log
    await app.send_document(
        LOG,
        document=buf,
        caption=f"📡 YesOfficer Extract Log\n\n{caption}"
    )

    await app.send_message(message.chat.id, "✅ Extraction complete!")
