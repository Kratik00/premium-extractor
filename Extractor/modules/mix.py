import asyncio
import aiohttp
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
import base64
import time
import os

from Extractor import app
from config import PREMIUM_LOGS

log_channel = PREMIUM_LOGS


# ===================== DECRYPT HELPERS =====================

def decrypt(enc):
    if not enc:
        return ""
    enc = b64decode(enc.split(':')[0])
    key = b'638udh3829162018'
    iv = b'fedcba9876543210'
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(enc), AES.block_size)
    return plaintext.decode('utf-8')


def decode_base64(encoded_str):
    try:
        return base64.b64decode(encoded_str).decode("utf-8")
    except Exception:
        return ""


# ===================== VIDEO FETCH =====================

async def fetch_item_details(session, api_base, course_id, item, headers, userid, app_name, path):
    fi = item.get("id")
    outputs = []

    try:
        async with session.get(
            f"{api_base}/get/fetchVideoDetailsById"
            f"?course_id={course_id}&video_id={fi}"
            f"&folder_wise_course=1&ytflag=0",
            headers=headers
        ) as response:

            if not response.headers.get("Content-Type", "").startswith("application/json"):
                return []

            r4 = await response.json()
            data = r4.get("data", {})
            if not data:
                return []

            vt = data.get("Title", "Untitled")

            # 🎥 YouTube
            fl = data.get("video_id")
            if fl:
                outputs.append(f"🗂️{vt}:https://youtu.be/{decrypt(fl)}")

            # 📹 Direct link
            vl = data.get("download_link")
            if vl:
                dvl = decrypt(vl)
                if ".pdf" not in dvl:
                    outputs.append(f"{vt}:https://appxapi.co/{app_name}/{course_id}/{fi}/{userid}.m3u8")

            # 🔐 ALL encrypted links
            for link in data.get("encrypted_links", []):
                a = link.get("path")
                k = link.get("key")
                if a and k:
                    outputs.append(f"{vt}:https://appxapi.co/{app_name}/{course_id}/{fi}/{userid}.m3u8")
                elif a:
                    outputs.append(f"{vt}:https://appxapi.co/{app_name}/{course_id}/{fi}/{userid}.m3u8")

            # 📄 PDFs (VIDEO + PDF)
            if data.get("material_type") in ("PDF", "VIDEO"):
                for p, k in [
                    (data.get("pdf_link"), data.get("pdf_encryption_key")),
                    (data.get("pdf_link2"), data.get("pdf2_encryption_key")),
                ]:
                    if p and k:
                        dp = decrypt(p)
                        dk = decrypt(k)
                        if dk == "abcdefg":
                            outputs.append(f"{vt}:https://appxapi.co/{app_name}/{course_id}/{fi}/{userid}.pdf")
                        else:
                            outputs.append(f"{vt}:https://appxapi.co/{app_name}/{course_id}/{fi}/{userid}.pdf")

    except Exception as e:
        print(f"💣 Video error {fi}: {e}")

    return outputs


# ===================== FOLDER RECURSION =====================

async def fetch_folder_contents(session, api_base, course_id, folder_id, headers, userid, app_name, path="Home"):
    outputs = []

    try:
        async with session.get(
            f"{api_base}/get/folder_contentsv3"
            f"?course_id={course_id}&parent_id={folder_id}"
            f"&windowsapp=false&start=0",
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

                # 📁 Folder → recurse
                if mtype == "FOLDER":
                    sub = await fetch_folder_contents(
                        session, api_base, course_id,
                        item["id"], headers, userid, app_name, current_path
                    )
                    outputs.extend(sub)

                # 🎥 Video / PDF
                else:
                    vids = await fetch_item_details(
                            session, api_base, course_id,
                            item, headers, userid, app_name, current_path
                        )
                    outputs.extend(vids)

    except Exception as e:
        print(f"💣 Folder error {folder_id}: {e}")

    return outputs


# ===================== MAIN ENTRY =====================

async def v2_new(
    app, message, token, userid, hdr1,
    app_name, raw_text2, api_base,
    sanitized_course_name, start_time,
    start, end, pricing, input2, m1, m2
):
    async with aiohttp.ClientSession() as session:

        # 🔁 SINGLE ENTRY POINT (IMPORTANT)
        all_outputs = await fetch_folder_contents(
                session,
                api_base,
                raw_text2,
                folder_id=-1,
                headers=hdr1,
                userid=userid,
                app_name=app_name,
                path="Home"
            )

        if not all_outputs:
            return await message.reply_text("No content found.")

        filename = f"{sanitized_course_name}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            for line in all_outputs:
                f.write(line + "\n")

        elapsed = time.time() - start_time

        caption = (
            f"╭━━━━━━━『 <b>🚀 COURSE INFO</b> 』━━━━━━━╮\n"
            f"📦 <b>App Name:</b> <code>{app_name}</code>\n"
            f"🎓 <b>Batch Name:</b> <code>{sanitized_course_name}</code>\n"
            f"🕒 <b>Validity:</b> <code>{start}</code> ➜ <code>{end}</code>\n"
            f"💰 <b>Price:</b> <code>{pricing}</code>\n"
            f"⏱️ <b>Extracted In:</b> <code>{elapsed:.1f}s</code>\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"👑 <b>Admin:</b> <a href='https://t.me/NOOBHUSIR'>LUCIFER ⚡</a>\n"
            f"⚙️ <b>Extractor:</b> <code>LUCIFER EXTRACTOR ⚡</code>"
        )

        await input2.delete(True)
        await m1.delete(True)
        await m2.delete(True)

        await app.send_document(message.chat.id, filename, caption=caption)
        await app.send_document(log_channel, filename, caption=caption)

        os.remove(filename)
        await message.reply_text("Done✅")
