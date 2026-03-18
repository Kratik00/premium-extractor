import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from Extractor import app
from config import CHANNEL_ID

BASE = "https://www.cdsjourney.com"

# ---------------- CORE CLASS ----------------
class CDSAsync:
    def __init__(self):
        self.session = None
        self.cookies = {}

    async def init(self):
        self.session = aiohttp.ClientSession()
        async with self.session.get(BASE) as res:
            self.cookies.update(res.cookies)

    async def login(self, sessionid):
        self.cookies["sessionid"] = sessionid

    async def get_html(self, url):
        async with self.session.get(url, cookies=self.cookies) as r:
            return await r.text()

    async def get_json(self, url):
        async with self.session.get(url, cookies=self.cookies) as r:
            return await r.json()

    async def get_batches(self):
        html = await self.get_html(f"{BASE}/student-dashboard/home/")
        soup = BeautifulSoup(html, "html.parser")

        data = []
        for c in soup.find_all("div", class_="card-content"):
            title = c.find("h4").text.strip()
            link = c.find("a", href=True)["href"]

            if "/batch/" in link:
                bid = link.split("/batch/")[1].split("/")[0]
                data.append((bid, title))
        return data

    async def get_subjects(self, batch_id):
        html = await self.get_html(f"{BASE}/student-dashboard/batch/{batch_id}/subjects/")
        soup = BeautifulSoup(html, "html.parser")

        subs = []
        for a in soup.find_all("a", href=True):
            if "/subject/" in a["href"]:
                img = a.find("img")
                if not img:
                    continue

                sid = a["href"].split("/subject/")[1].split("/")[0]
                name = img.get("alt", "")
                subs.append((sid, name))
        return subs

    async def get_videos(self, subject_id):
        html = await self.get_html(f"{BASE}/student-dashboard/subject/{subject_id}/")
        soup = BeautifulSoup(html, "html.parser")

        vids = []
        for c in soup.find_all("div", class_="card"):
            title = c.find("p").text.strip()
            btn = c.find("span", onclick=True)

            if not btn:
                continue

            vid = re.search(r"loadVideo\('(\d+)'\)", btn["onclick"])
            if vid:
                vids.append((title, vid.group(1)))
        return vids

    async def get_video_url(self, vid):
        try:
            d1 = await self.get_json(f"{BASE}/get-recording-url/{vid}/")
            proxy = BASE + d1["url"]
            d2 = await self.get_json(proxy)
            return d2.get("url")
        except:
            return None


# ---------------- HANDLER ----------------
@app.on_message(filters.command("cds") & filters.private)
async def cds_handler(app: Client, message: Message):

    inp = await app.ask(message.chat.id, "Send SessionID:")
    sessionid = inp.text.strip()

    cds = CDSAsync()
    await cds.init()
    await cds.login(sessionid)

    batches = await cds.get_batches()

    msg = "📚 <b>Batches</b>\n\n"
    for b in batches:
        msg += f"<code>{b[0]}</code> - {b[1]}\n"

    b_in = await app.ask(message.chat.id, msg + "\nSend Batch ID:")
    batch_id = b_in.text.strip()

    batch_name = next((b[1] for b in batches if b[0] == batch_id), "Batch")

    prog = await message.reply("🔄 Processing batch...")

    subjects = await cds.get_subjects(batch_id)

    result = []
    total = 0

    for sid, sname in subjects:
        vids = await cds.get_videos(sid)

        tasks = [cds.get_video_url(v[1]) for v in vids]
        urls = await asyncio.gather(*tasks)

        for (title, _), url in zip(vids, urls):
            if url:
                result.append(f"({sname}) {title}: {url}")
                total += 1

    # ---------------- SAVE ----------------
    file_name = f"{batch_name.replace('/', '')}.txt"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write("\n".join(result))

    # ---------------- CAPTION ----------------
    import datetime
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    caption = (
        "🎓 <b>CDS JOURNEY EXTRACTED</b> 🎓\n\n"
        f"📚 <b>BATCH:</b> {batch_name}\n"
        f"📅 <b>DATE:</b> {date} IST\n\n"
        "📊 <b>CONTENT STATS</b>\n"
        f"└─ 🔗 Total Links: {total}\n\n"
        f"🚀 <b>Extracted by:</b> @{(await app.get_me()).username}\n\n"
        f"<code>╾───•  •───╼</code>"
    )

    # ---------------- SEND ----------------
    await app.send_document(
        message.chat.id,
        file_name,
        caption=caption
    )

    await app.send_document(
        CHANNEL_ID,
        file_name,
        caption=caption,
    )

    await prog.delete()

    os.remove(file_name)
    if thumb and os.path.exists(thumb):
        os.remove(thumb)

    await cds.session.close()
