import asyncio
import aiohttp
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
from pyrogram import filters
import cloudscraper
from Extractor import app
from config import PREMIUM_LOGS 
import os
import base64
import time

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

async def fetch_item_details(session, api_base, course_id, item, headers):
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

                vt = data.get("Title", "")
                vl = data.get("download_link", "")

                if vl:
                    dvl = decrypt(vl)
                    outputs.append(f"{vt}:{dvl}")
                else:
                    encrypted_links = data.get("encrypted_links", [])
                    for link in encrypted_links:
                        a = link.get("path")
                        k = link.get("key")

                        if a and k:
                            k1 = decrypt(k)
                            k2 = decode_base64(k1)
                            da = decrypt(a)
                            outputs.append(f"{vt}:{da}*{k2}")
                            break
                        elif a:
                            da = decrypt(a)
                            outputs.append(f"{vt}:{da}")
                            break

                if "material_type" in data:
                    mt = data["material_type"]
                    if mt == "VIDEO":
                        p1 = data.get("pdf_link", "")
                        pk1 = data.get("pdf_encryption_key", "")
                        p2 = data.get("pdf_link2", "")
                        pk2 = data.get("pdf2_encryption_key", "")
                        if p1 and pk1:
                            dp1 = decrypt(p1)
                            depk1 = decrypt(pk1)
                            if depk1 == "abcdefg":
                                outputs.append(f"{vt}:{dp1}")
                            else:
                                outputs.append(f"{vt}:{dp1}*{depk1}")
                    
                        
                            
                        if p2 and pk2:
                            dp2 = decrypt(p2)
                            depk2 = decrypt(pk2)
                            if depk2 == "abcdefg":
                                outputs.append(f"{vt}:{dp2}")
                            else:
                                outputs.append(f"{vt}:{dp2}*{depk2}")
            else:
                error_page = await response.text()
                print(f"Error: Unexpected response for video ID {fi}:\n{error_page}")
                return []
    except Exception as e:
        print(f"An error occurred while fetching details for video ID {fi}: {str(e)}")
        return []

    return outputs
    
                    
        
async def fetch_folder_contents(session, api_base, course_id, folder_id, headers):
    outputs = []
    url = f"{api_base}/get/folder_contentsv3?course_id={course_id}&parent_id={folder_id}&windowsapp=false&start=0"

    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"⚠️ Folder {folder_id} failed ({response.status})")
                print(await response.text())
                return []

            j = await response.json()
            data = j.get("data", [])
            if not data:
                print(f"⚠️ Folder {folder_id} is empty")
                return []

            tasks = []

            for item in data:
                title = item.get("Title")
                mtype = item.get("material_type")

                if mtype == "FOLDER":
                    print(f"📂 Found folder → {title} ({item['id']})")
                    tasks.append(fetch_folder_contents(session, api_base, course_id, item["id"], headers))
                else:
                    print(f"📄 Found {mtype} → {title}")
                    tasks.append(fetch_item_details(session, api_base, course_id, item, headers))

            if tasks:
                results = await asyncio.gather(*tasks)
                for res in results:
                    if res:
                        outputs.extend(res)

    except Exception as e:
        print(f"💣 Error fetching folder {folder_id}: {e}")
        outputs.append(f"Error fetching folder {folder_id}: {e}")

    return outputs



async def v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, sanitized_course_name, start_time, start, end, pricing, input2, m1, m2):
  async with aiohttp.ClientSession() as session:
        
        async with session.get(f"{api_base}/get/folder_contentsv3?course_id={raw_text2}&parent_id=-1", headers=hdr1) as res2:
            j2 = await res2.json()
        if not j2.get("data"):
            return await message.reply_text("No data found in the response. Try switching to v3 and retry.")
        
        filename = f"{sanitized_course_name}.txt"
        all_outputs = []        
        tasks = []
        if "data" in j2:
            for item in j2["data"]:        
                tasks.append(fetch_item_details(session, api_base, raw_text2, item, hdr1))
                if item["material_type"] == "FOLDER":
                    tasks.append(fetch_folder_contents(session, api_base, raw_text2, item["id"], hdr1))
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
        c_text = (f"**AppName:** {app_name}\n"
                  f"**BatchName:** {sanitized_course_name}\n"
                  f"**Batch Start Date:** {start}\n"
                  f"**Validity Ends On:** {end}\n"
                  f"Elapsed time: {elapsed_time:.1f} seconds\n"
                  f"**Batch Purchase At:** {pricing}")

        await input2.delete(True)
        await m1.delete(True)
        await m2.delete(True)
        await app.send_document(message.chat.id, filename, caption=c_text)
        await app.send_document(log_channel, filename, caption = c_text)
        os.remove(filename)
        await message.reply_text("Done✅")
                              