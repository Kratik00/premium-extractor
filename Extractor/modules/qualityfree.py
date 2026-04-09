import re
import requests
import os
import asyncio
from datetime import datetime
from pyrogram import filters
from Extractor import app
from config import PREMIUM_LOGS, THUMB_URL

LOG_CHANNEL = PREMIUM_LOGS

HEADERS = {
    "Host": "test.qualityeducation.in",
    "accept-encoding": "gzip",
    "user-agent": "okhttp/3.14.7"
}


# ---------------- THUMB ----------------
def download_thumbnail(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            path = "thumb_temp.jpg"
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except:
        return None


# ---------------- GET CATEGORIES ----------------
def get_categories():
    url = "https://test.qualityeducation.in/api/video-category-get"
    res = requests.get(url, headers=HEADERS).json()
    return [(str(c["id"]), c["category_name"]) for c in res.get("data", [])]


# ---------------- GET COMBO ----------------
def get_combo(batch_id):
    url = f"https://test.qualityeducation.in/api/combo-get/318096/{batch_id}"
    return requests.get(url, headers=HEADERS).json()


# ---------------- GET SUBJECTS ----------------
def get_subjects(video_id):
    url = f"https://test.qualityeducation.in/api/subject-get/{video_id}"
    return requests.get(url, headers=HEADERS).json()


# ---------------- GET CONTENT ----------------
def get_content(video_id, subject_id):
    url = f"https://test.qualityeducation.in/api/subject-get/{video_id}/{subject_id}"
    return requests.get(url, headers=HEADERS).json()


# ---------------- MAIN COMMAND ----------------
@app.on_callback_query(filters.regex("^qualitytext$"))
async def quality_text_handler(app, callback_query):

    await callback_query.answer()
    chat_id = callback_query.message.chat.id

    main_msg = await app.send_message(chat_id, "📂 <b>Fetching QE Categories...</b>")

    categories = get_categories()

    text = "📚 <b>Available QE Batches</b>\n\n"
    for cid, name in categories:
        text += f"🪪 <code>{cid}</code> - {name}\n"

    text += "\n\n📝 <b>Send Batch ID:</b>"
    await main_msg.edit_text(text)

    # 👇 input
    user_msg = await app.listen(chat_id)
    batch_id = user_msg.text.strip()

    try:
        await user_msg.delete()
    except:
        pass

    await main_msg.edit_text("⏳ <b>Processing...</b>")

    await process_qe(app, callback_query.from_user, chat_id, batch_id, main_msg)


# ---------------- PROCESS ----------------
async def process_qe(app, user, chat_id, batch_id, msg):

    data = get_combo(batch_id)

    if not data or not data.get("data") or not data["data"].get("video"):
        return await msg.edit_text("❌ Invalid Batch ID or No data found")

    videos = data["data"]["video"]
    batch_name = videos[0].get("title", "Batch")

    result = []
    video_count = 0
    pdf_count = 0

    for video in videos:

        vid = video.get("id")

        subjects = get_subjects(vid)

        for sub in subjects.get("data", []):
            sid = sub.get("id")

            contents = get_content(vid, sid)

            for item in contents.get("data", []):

                topic = item.get("topic_name", "Untitled")

                pdf = item.get("pdf_link")
                video_links = [
                    item.get("quality_1080"),
                    item.get("quality_720"),
                    item.get("quality_480"),
                    item.get("quality_360"),
                    item.get("video_link")
                ]

                vid_link = next((v for v in video_links if v), None)

                if pdf:
                    result.append(f"{topic}: {pdf}")
                    pdf_count += 1

                if vid_link:
                    result.append(f"{topic}: {vid_link}")
                    video_count += 1

        await msg.edit_text(f"📦 Processing: <b>{batch_name}</b>")

        await asyncio.sleep(0.2)

    total = video_count + pdf_count

    if total == 0:
        return await msg.edit_text("❌ No content found")

    # ---------------- FILE ----------------
    safe_name = re.sub(r'[\\/*?:_"<>|]', " ", batch_name)
    file_name = f"{safe_name}.txt"

    with open(file_name, "w", encoding="utf-8") as f:
        f.write("\n".join(result))

    thumb_path = download_thumbnail(THUMB_URL)

    me = await app.get_me()
    mention = f"<a href='tg://user?id={me.id}'>{me.first_name}</a>"

    mention1 = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>" if user else "User"

    caption = (
        "🎯 <b>QUALITY   EDUCATION</b>\n\n"

        "──────── <b>BATCH DETAILS</b> ────────\n"
        "<blockquote>"
        f"📚 <b>Batch :</b> {batch_name}\n"
        f"🪪 <b>ID :</b> <code>{batch_id}</code>\n"
        "</blockquote>\n\n"

        "──────── <b>CONTENT SUMMARY</b> ────────\n"
        "<blockquote>"
        f"🔗 <b>Total :</b> {total}\n"
        f"🎬 <b>Videos :</b> {video_count}\n"
        f"📄 <b>PDFs :</b> {pdf_count}\n"
        "</blockquote>\n\n"

        f"⏰ <b>Generated :</b> {datetime.now().strftime('%d-%m-%Y %I:%M:%S %p')}\n"
        f"🪪 <b>User :</b> {mention1}\n"

        "➖➖➖➖➖➖➖\n"
        f"✳️ <b>Extractor :</b> {mention}"
    )

    await msg.edit_text("📤 Uploading...")

    await app.send_document(
        chat_id,
        file_name,
        caption=caption,
        thumb=thumb_path if thumb_path else None
    )

    # ---------------- LOG ----------------
    try:
        await app.send_document(
            LOG_CHANNEL,
            file_name,
            caption=caption,
            thumb=thumb_path if thumb_path else None
        )
    except:
        pass

    # ---------------- CLEANUP ----------------
    os.remove(file_name)

    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)

    await msg.delete()
