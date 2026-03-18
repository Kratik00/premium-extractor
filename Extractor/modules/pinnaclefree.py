import re
import requests
import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from Extractor import app
from config import PREMIUM_LOGS, THUMB_URL
from urllib.parse import quote

LOG_CHANNEL = PREMIUM_LOGS
BASE = "https://auth.ssccglpinnacle.com"


# ---------------- HEADERS ----------------
def get_headers():
    return {
        "origin": "https://videos.ssccglpinnacle.com",
        "referer": "https://videos.ssccglpinnacle.com/",
        "user-agent": "Mozilla/5.0"
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
    except Exception:
        return None


# ---------------- CATEGORIES ----------------
def get_categories():
    url = f"{BASE}/categories"
    res = requests.get(url, headers=get_headers()).json()
    return [(c["_id"], c["categoryTitle"]) for c in res]


# ---------------- COURSES ----------------
def get_courses(category):
    url = f"{BASE}/rc/courses?category={quote(category)}"
    res = requests.get(url, headers=get_headers()).json()

    courses = []
    for c in res:
        courses.append({
            "id": c["_id"],
            "title": c["courseTitle"],
            "price": c.get("price", 0),
            "mrp": c.get("mrp", 0),
            "instructor": c.get("instructorName", "Unknown"),
            "category": c.get("category", "Unknown")
        })
    return courses


# ---------------- CHAPTERS ----------------
def get_chapters(course_id):
    url = f"{BASE}/api/youtubeChapters/course/{course_id}"
    return requests.get(url, headers=get_headers()).json()


# ---------------- MAIN COMMAND ----------------
@app.on_message(filters.command("pinnacle") & filters.private)
async def pinnacle_handler(app, message):

    chat_id = message.chat.id
    main_msg = await message.reply("📂 <b>Fetching Categories...</b>")

    # 🔹 categories
    categories = get_categories()

    text = "📚 <b>Available Categories</b>\n\n"
    for cid, name in categories:
        text += f"• <code>{name.strip()}</code>\n"

    text += "\n📝 <b>Send Category Name:</b>"
    await main_msg.edit_text(text)

    cat_msg = await app.listen(chat_id)
    category = cat_msg.text.strip()

    try:
        await cat_msg.delete()
    except:
        pass

    # 🔹 courses
    courses = get_courses(category)

    if not courses:
        return await main_msg.edit_text("__❌ Invalid Category or No courses__")

    text = "🎯 <b>Available Courses</b>\n\n"
    for c in courses:
        text += f"🪪 <code>{c['id']}</code> - 📚 {c['title']}\n"

    text += "\n📝 <b>Send Course ID:</b>"
    await main_msg.edit_text(text)

    course_msg = await app.listen(chat_id)
    course_id = course_msg.text.strip()

    try:
        await course_msg.delete()
    except:
        pass

    selected = next((c for c in courses if c["id"] == course_id), None)

    if not selected:
        return await main_msg.edit_text("❌ Invalid Course ID")

    await main_msg.edit_text("⏳ <b>Processing...</b>")

    await process_pinnacle(app, message, chat_id, selected, main_msg)


# ---------------- PROCESS ----------------
async def process_pinnacle(app, message, chat_id, course, msg):

    course_id = course["id"]
    course_title = course["title"]
    price = course["price"]
    mrp = course["mrp"]
    instructor = course["instructor"]
    category = course["category"]

    chapters = get_chapters(course_id)

    if not chapters:
        return await msg.edit_text("❌ No content found")

    result = []
    total = 0

    for ch in chapters:

        cname = ch["chapterTitle"]
        await msg.edit_text(f"📚 <b>{cname}</b>")

        for topic in ch["topics"]:
            title = topic["videoTitle"]
            url = topic["videoYoutubeLink"]

            result.append(f"({cname}) {title}: {url}")
            total += 1

        await asyncio.sleep(0.3)

    if total == 0:
        return await msg.edit_text("❌ No videos found")

    # 🔹 file
    safe_name = re.sub(r'[\\/*?:_"<>|]', " ", course_title)
    file_name = f"{safe_name}.txt"

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(
            f"{course_title}\n"
            f"{'='*50}\n\n"
        )
        f.write("\n".join(result))

    thumb_path = download_thumbnail(THUMB_URL)

    me = await app.get_me()
    mention = f"<a href='tg://user?id={me.id}'>{me.first_name}</a>"

    user = message.from_user
    mention1 = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

    course_name = re.sub(r"[_]+", " ", course_title).strip()

    caption = (
        "🎯 <b>PINNACLE PRO</b>\n\n"

        "──────── <b>COURSE DETAILS</b> ────────\n"
        "<blockquote>"
        f"📚 <b>Course :</b> {course_name}\n"
        f"🪪 <b>ID :</b> <code>{course_id}</code>\n"
        f"📂 <b>Category :</b> {category}\n"
        f"👨‍🏫 <b>Instructor :</b> {instructor}\n"
        f"💰 <b>Price :</b> ₹{price} (MRP: ₹{mrp})\n"
        "</blockquote>\n\n"

        "──────── <b>LINK SUMMARY</b> ────────\n"
        "<blockquote>"
        f"🔗 <b>Total Links :</b> {total}\n"
        f"🎬 <b>Videos :</b> {total}\n"
        "📄 <b>PDFs :</b> Excluded\n"
        "</blockquote>\n\n"

        f"⏰ <b>Generated On :</b> {datetime.now().strftime('%d-%m-%Y %I:%M:%S %p')}\n"
        f"🪪 <b>EXTRACTED BY :</b> {mention1}\n"

        "➖➖➖➖➖➖➖\n"
        f"✳️ <b>TXT EXTRACTOR :</b> {mention}"
    )

    await msg.edit_text("📤 Uploading...")

    await app.send_document(
        chat_id,
        file_name,
        caption=caption,
        thumb=thumb_path if thumb_path else None
    )

    # 🔹 logs
    try:
        await app.send_document(
            LOG_CHANNEL,
            file_name,
            caption=caption,
            thumb=thumb_path if thumb_path else None
        )
    except:
        pass

    # 🔹 cleanup
    os.remove(file_name)

    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)

    await msg.delete()
