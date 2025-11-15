import requests, os, sys, re
import json, asyncio
import subprocess
import datetime
import time
import logging
from typing import List, Dict, Tuple, Any
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from Extractor import app
from config import PREMIUM_LOGS
import config
from pyrogram import Client, filters, idle
from pyrogram.types import Message
# from pyromod.listen import ListenerTimeout
# from pyrogram.errors import ListenerTimeout
from subprocess import getstatusoutput
from datetime import datetime
import pytz


join = config.join
india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d-%m-%Y %I:%M %p")

THREADPOOL = ThreadPoolExecutor(max_workers=5000)

async def download_thumbnail(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        # Create a temporary filename
        thumb_path = f"thumb_{int(time.time())}.jpg"
        
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                # Save the thumbnail
                with open(thumb_path, "wb") as f:
                    f.write(await response.read())
                return thumb_path
            return None
    except Exception as e:
        logging.error(f"Error downloading thumbnail: {e}")
        return None

def create_html_file(file_name, batch_name, contents):
    tbody = ''
    parts = contents.split('\n')
    for part in parts:
        split_part = [item.strip() for item in part.split(':', 1)]
    
        text = split_part[0] if split_part[0] else 'Untitled'
        url = split_part[1].strip() if len(split_part) > 1 and split_part[1].strip() else 'No URL'

        tbody += f'<tr><td>{text}</td><td><a href="{url}" target="_blank">{url}</a></td></tr>'

    with open('Extractor/core/template.html', 'r') as fp:
        file_content = fp.read()
    title = batch_name.strip()
    with open(file_name, 'w') as fp:
        fp.write(file_content.replace('{{tbody_content}}', tbody).replace('{{batch_name}}', title))
        



#======================================================================================================================





async def fetch_cpwp_signed_url(url_val: str, name: str, session: aiohttp.ClientSession, headers: Dict[str, str]) -> str | None:
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        params = {"url": url_val}
        try:
            async with session.get("https://api.classplusapp.com/cams/uploader/video/jw-signed-url", params=params, headers=headers) as response:
                response.raise_for_status()
                response_json = await response.json()
                signed_url = response_json.get("url") or response_json.get('drmUrls', {}).get('manifestUrl')
                return signed_url
                
        except Exception as e:
         #   logging.exception(f"Unexpected error fetching signed URL for {name}: {e}. Attempt {attempt + 1}/{MAX_RETRIES}")
            pass

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(2 ** attempt)

    logging.error(f"Failed to fetch signed URL for {name} after {MAX_RETRIES} attempts.")
    return None

async def process_cpwp_url(url_val: str, name: str, session: aiohttp.ClientSession, headers: Dict[str, str]) -> str | None:
    try:
        signed_url = await fetch_cpwp_signed_url(url_val, name, session, headers)
        # if not signed_url:
        #     logging.warning(f"Failed to obtain signed URL for {name}: {url_val}")
        #     return None

        if "testbook.com" in url_val or "classplusapp.com/drm" in url_val or "media-cdn.classplusapp.com/drm" in url_val or "media-cdn.classplusapp.com/" in url_val:
        #    logging.info(f"{name}:{url_val}")
            return f"{name}:{url_val}\n"

        async with session.get(signed_url) as response:
            response.raise_for_status()
       #     logging.info(f"{name}:{url_val}")
            return f"{name}:{url_val}\n"
            
    except Exception as e:
    #    logging.exception(f"Unexpected error processing {name}: {e}")
        pass
    return None



async def get_cpwp_course_content(session: aiohttp.ClientSession, headers: Dict[str, str], Batch_Token: str, folder_id: int = 0, limit: int = 9999999999, retry_count: int = 0) -> Tuple[List[str], int, int, int]:
    MAX_RETRIES = 3
    fetched_urls: set[str] = set()
    results: List[str] = []
    video_count = 0
    pdf_count = 0
    image_count = 0
    content_tasks: List[Tuple[int, asyncio.Task[str | None]]] = []
    folder_tasks: List[Tuple[int, asyncio.Task[List[str]]]] = []
     
    try:
        content_api = f'https://api.classplusapp.com/mm/v3/video/recordings/{Batch_Token}'
        #content_api = f'https://api.classplusapp.com/v2/course/preview/content/list/{Batch_Token}'
        params = {'folderId': folder_id, 'limit': limit}

        # Add timeout for content API request
        async with session.get(content_api, params=params, headers=headers, timeout=30) as res:
            res.raise_for_status()
            res_json = await res.json()
            contents: List[Dict[str, Any]] = res_json['data']

            for content in contents:
                if content['contentType'] == 1:
                    folder_task = asyncio.create_task(get_cpwp_course_content(session, headers, Batch_Token, content['id'], retry_count=0))
                    folder_tasks.append((content['id'], folder_task))

                else:
                    name: str = content['name']
                    url_val: str | None = content.get('url') or content.get('thumbnailUrl')

                    if not url_val:
                        logging.warning(f"No URL found for content: {name}")
                        continue
                        
                    if "media-cdn.classplusapp.com/tencent/" in url_val:
                        url_val = url_val.rsplit('/', 1)[0] + "/master.m3u8"
                    elif "media-cdn.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                        identifier = url_val.split('/')[-3]
                        url_val = f'https://media-cdn.classplusapp.com/alisg-cdn-a.classplusapp.com/{identifier}/master.m3u8'
                    elif "tencdn.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                        identifier = url_val.split('/')[-2]
                        url_val = f'https://media-cdn.classplusapp.com/tencent/{identifier}/master.m3u8'
                    elif "4b06bf8d61c41f8310af9b2624459378203740932b456b07fcf817b737fbae27" in url_val and url_val.endswith('.jpeg'):
                        video_id = url_val.split('/')[-1].split('.')[0]
                        url_val = f'https://media-cdn.classplusapp.com/alisg-cdn-a.classplusapp.com/b08bad9ff8d969639b2e43d5769342cc62b510c4345d2f7f153bec53be84fe35/{video_id}/master.m3u8'
                    elif "cpvideocdn.testbook.com" in url_val and url_val.endswith('.png'):
                        match = re.search(r'/streams/([a-f0-9]{24})/', url_val)
                        video_id = match.group(1) if match else url_val.split('/')[-2]
                        url_val = f'https://cpvod.testbook.com/{video_id}/playlist.m3u8'
                    elif "media-cdn.classplusapp.com/drm/" in url_val and url_val.endswith('.png'):
                        video_id = url_val.split('/')[-3]
                        url_val = f'https://media-cdn.classplusapp.com/drm/{video_id}/playlist.m3u8'
                    elif "https://media-cdn.classplusapp.com" in url_val and ("cc/" in url_val or "lc/" in url_val or "uc/" in url_val or "dy/" in url_val) and url_val.endswith('.png'):
                        url_val = url_val.replace('thumbnail.png', 'master.m3u8')
                    elif "https://tb-video.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                        video_id = url_val.split('/')[-1].split('.')[0]
                        url_val = f'https://tb-video.classplusapp.com/{video_id}/master.m3u8'

                    if url_val.endswith(("master.m3u8", "playlist.m3u8")) and url_val not in fetched_urls:
                        fetched_urls.add(url_val)
                        headers2 = { 'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9'}
                        task = asyncio.create_task(process_cpwp_url(url_val, name, session, headers2))
                        content_tasks.append((content['id'], task))
                        
                    else:
                        name: str = content['name']
                        url_val: str | None = content.get('url')
                        if url_val:
                            fetched_urls.add(url_val)
                            results.append(f"{name}:{url_val}\n")
                            if url_val.endswith('.pdf'):
                                pdf_count += 1
                            else:
                                image_count += 1
                                
    except asyncio.TimeoutError:
        logging.error(f"Timeout while fetching content list for folder {folder_id}")
        if retry_count < MAX_RETRIES:
            await asyncio.sleep(2 ** retry_count)
            return await get_cpwp_course_content(session, headers, Batch_Token, folder_id, limit, retry_count + 1)
        return [], 0, 0, 0
                                
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        if retry_count < MAX_RETRIES:
            logging.info(f"Retrying folder {folder_id} (Attempt {retry_count + 1}/{MAX_RETRIES})")
            await asyncio.sleep(2 ** retry_count)
            return await get_cpwp_course_content(session, headers, Batch_Token, folder_id, limit, retry_count + 1)
        else:
            logging.error(f"Failed to retrieve folder {folder_id} after {MAX_RETRIES} retries.")
            return [], 0, 0, 0
            
    # Add timeout for gathering tasks
    try:
        content_results = await asyncio.wait_for(
            asyncio.gather(*(task for _, task in content_tasks), return_exceptions=True),
            timeout=60  # 60 second timeout for content gathering
        )
        
        folder_results = await asyncio.wait_for(
            asyncio.gather(*(task for _, task in folder_tasks), return_exceptions=True),
            timeout=60  # 60 second timeout for folder gathering
        )
    except asyncio.TimeoutError:
        logging.error(f"Timeout while gathering results for folder {folder_id}")
        return results, video_count, pdf_count, image_count
    
    for (folder_id, result) in zip(content_tasks, content_results):
        if isinstance(result, Exception):
            logging.error(f"Task failed with exception: {result}")
        elif result:
            results.append(result)
            video_count += 1
            
    for folder_id, folder_result in folder_tasks:
        try:
            nested_results, nested_video_count, nested_pdf_count, nested_image_count = await folder_result
            if nested_results:
                results.extend(nested_results)
            video_count += nested_video_count
            pdf_count += nested_pdf_count
            image_count += nested_image_count
        except Exception as e:
            logging.error(f"Error processing folder {folder_id}: {e}")

    return results, video_count, pdf_count, image_count
    

    
async def process_cpwp(bot: Client, m: Message, user_id: int):
    # Add channel ID at the top
    CHANNEL_ID = -1002601604234
    
    headers = {
        'accept-encoding': 'gzip',
        'accept-language': 'EN',
        'api-version'    : '35',
        'app-version'    : '1.4.73.2',
        'build-number'   : '35',
        'connection'     : 'Keep-Alive',
        'content-type'   : 'application/json',
        'device-details' : 'Xiaomi_Redmi 7_SDK-32',
        'device-id'      : 'c28d3cb16bbdac01',
        'host'           : 'api.classplusapp.com',
        'region'         : 'IN',
        'user-agent'     : 'Mobile-Android',
        'webengage-luid' : '00000187-6fe4-5d41-a530-26186858be4c'
    }

    loop = asyncio.get_event_loop()
    CONNECTOR = aiohttp.TCPConnector(limit=1000, loop=loop)
    async with aiohttp.ClientSession(connector=CONNECTOR, loop=loop) as session:
        editable = None
        try:
            # Get user info at the start
            user = await bot.get_users(user_id)
            user_name = user.first_name
            if user.last_name:
                user_name += f" {user.last_name}"
            mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
            
            editable = await m.reply_text(
                "💬 <b>Just send me your <u>Organization Code</u></b>\n\n"
                "🛑 <b>Help:</b>\n"
                "<blockquote>Go to the <b>Play Store</b> and copy your app’s share link — it looks like:\n"
                "<code>https://play.google.com/store/apps/details?id=co.groot.bfwyu</code>\n\n"
                "The last part (e.g., <code>bfwyu</code>) is your <b>Organization Code</b>.\n\n"
                "Alternatively, open your app → tap the ☰ (three lines) in the top-left corner → find it there.</blockquote>"
            )

            
            try:
                input1 = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
                org_code = input1.text.lower()
                await input1.delete(True)
            except ListenerTimeout:
                await editable.edit("**Timeout! You took too long to respond**")
                return
            except Exception as e:
                logging.exception("Error during input1 listening:")
                try:
                    await editable.edit(f"**Error: {e}**")
                except:
                    logging.error(f"Failed to send error message to user: {e}")
                return

            hash_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://qsvfn.courses.store/?mainCategory=0&subCatList=[130504,62442]',
                'Sec-CH-UA': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
                'Sec-CH-UA-Mobile': '?0',
                'Sec-CH-UA-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
            }
            
            async with session.get(f"https://{org_code}.courses.store", headers=hash_headers) as response:
                html_text = await response.text()
                hash_match = re.search(r'"hash":"(.*?)"', html_text)

                if hash_match:
                    token = hash_match.group(1)
                    
                    async with session.get(f"https://api.classplusapp.com/v2/course/preview/similar/{token}?limit=100", headers=headers) as response:
                        if response.status == 200:
                            res_json = await response.json()
                            courses = res_json.get('data', {}).get('coursesData', [])
                            if courses:
                                filename = f"batches.txt"
                                all_indices = []
                                with open(filename, "w", encoding="utf-8") as f:
                                    f.write("『 ⚡ 𝗘𝗫𝗧𝗥𝗔𝗖𝗧𝗢𝗥 𝗟𝗨𝗖𝗜𝗙𝗘𝗥 ⚡ 』\n\n")
                                    for cnt, course in enumerate(courses):
                                        name = course['name']
                                        price = course['finalPrice']
                                        index = cnt + 1
                                        f.write(f"{index}. {name} 💵 ₹{price}\n")
                                        all_indices.append(str(index))
                                           # send the txt file instead of message
                                copy_paste_format = "&".join(all_indices)

                                await m.reply_document(
                                    document=filename,
                                    caption = (
                                        f"『 ⚡ 𝗔𝗹𝗹 𝗕𝗮𝘁𝗰𝗵𝗲𝘀 𝗳𝗿𝗼𝗺 <b>{org_code}</b> ⚡ 』\n\n"
                                        f"📋 <b>For Multiple Batches Copy This 👇</b>\n"
                                        f"<code>{copy_paste_format}</code>"
                                        ),
                                )
                                os.remove(filename)
                                 # then ask for input like before
                                await m.reply_text("⚡ Send the index number(s) for extraction:")

                                try:
                                    input2 = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
                                    raw_text2 = input2.text
                                    await input2.delete(True)
                                except asyncio.TimeoutError:  # ✅ replaces ListenerTimeout
                                    await editable.edit("⏳ <b>Timeout!</b> You took too long to respond.")
                                    return
                                except Exception as e:
                                    logging.exception("Error during input2 listening:")
                                    try:
                                        await editable.edit(f"**Error : {e}**")
                                    except:
                                        logging.error(f"Failed to send error message to user : {e}")
                                    return

                                # Handle multiple batch indices
                                batch_indices = raw_text2.split('&')
                                total_batches = len(batch_indices)
                                processed_batches = 0
                                thumb_path = "https://graph.org/file/499d881b10bfef5497dee-bd8dc33d7559107334.jpg"  # Reset thumbnail path for each batch
                                
                                # Process each batch separately
                                for batch_index in batch_indices:
                                    batch_index = batch_index.strip()
                                    start_time = time.time()  # Reset timer for each batch
                                    # Download thumbnail for this batch
                                    if config.THUMB_URL:
                                        thumb_path = await download_thumbnail(session, config.THUMB_URL)
                                    
                                    if batch_index.isdigit() and int(batch_index) <= len(courses):
                                        selected_course_index = int(batch_index)
                                        course = courses[selected_course_index - 1]
                                        selected_batch_id = course['id']
                                        selected_batch_name = course['name']
                                        price = course['finalPrice']
                                        clean_batch_name = selected_batch_name.replace("/", "-").replace("|", "-")
                                        
                                        status_msg = await m.reply_text(f"**📥 Extracting {processed_batches + 1}/{total_batches}\nBatch: {selected_batch_name}**")

                                        batch_headers = {
                                            'Accept': 'application/json, text/plain, */*',
                                            'region': 'IN',
                                            'accept-language': 'EN',
                                            'Api-Version': '22',
                                            'tutorWebsiteDomain': f'https://{org_code}.courses.store'
                                        }
                                            
                                        params = {
                                            'courseId': f'{selected_batch_id}',
                                        }

                                        try:
                                            async with session.get(f"https://api.classplusapp.com/v2/course/preview/org/info", params=params, headers=batch_headers) as response:
                                                if response.status == 200:
                                                    res_json = await response.json()
                                                    Batch_Token = res_json['data']['hash']
                                                    App_Name = res_json['data']['name']

                                                    course_content, video_count, pdf_count, image_count = await get_cpwp_course_content(session, headers, Batch_Token)
                                                    
                                                    if course_content:
                                                        # Create individual file for this batch
                                                        batch_filename = f"{clean_batch_name}_{batch_index}.txt"
                                                        
                                                        with open(batch_filename, 'w', encoding='utf-8') as f:
                                                            f.write(''.join(course_content))

                                                        end_time = time.time()
                                                        response_time = end_time - start_time
                                                        minutes = int(response_time // 60)
                                                        seconds = int(response_time % 60)

                                                        if minutes == 0:
                                                            if seconds < 1:
                                                                formatted_time = f"{response_time:.2f} seconds"
                                                            else:
                                                                formatted_time = f"{seconds} seconds"
                                                        else:
                                                            formatted_time = f"{minutes} minutes {seconds} seconds"

                                                        caption = (
                                                            f"『 ⚡ 𝗘𝗫𝗧𝗥𝗔𝗖𝗧𝗢𝗥 𝗟𝗨𝗖𝗜𝗙𝗘𝗥 ⚡ 』\n"
                                                            f"╭━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                                                            f"🌀 <b>App Name :</b> <code>{App_Name}</code>\n"
                                                            f"🔑 <b>Org Code :</b> <code>{org_code}</code>\n"
                                                            f"╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                                                            f"🏷️ <b>Batch Name :</b> <code>{clean_batch_name}</code>\n"
                                                            f"<blockquote>🎬 {video_count}  |  📁 {pdf_count}  |  🖼 {image_count}</blockquote>\n\n"
                                                            f"⏳ <b>Time Taken :</b> {formatted_time}\n"
                                                            f"📅 <b>Date :</b> {time_new}\n"
                                                            f"━━━━━━━━━━━━━━━━━━━━━━━"
                                                        )

                                                        try:
                                                            with open(batch_filename, 'rb') as f:
                                                                # Send to user
                                                                if thumb_path and os.path.exists(thumb_path):
                                                                    await m.reply_document(
                                                                        document=f, 
                                                                        caption=caption,
                                                                        thumb=thumb_path
                                                                    )
                                                                    # Send to channel directly
                                                                    try:
                                                                        await app.send_document(
                                                                            chat_id=PREMIUM_LOGS,
                                                                            document=f,
                                                                            caption=caption,
                                                                            thumb=thumb_path
                                                                        )
                                                                    except Exception as ce:
                                                                        print(f"Error sending to channel: {ce}")
                                                                else:
                                                                    # Send without thumbnail if download failed
                                                                    await m.reply_document(
                                                                        document=f, 
                                                                        caption=caption
                                                                    )
                                                                    await app.send_document(
                                                                        chat_id=PREMIUM_LOGS,
                                                                        document=f,
                                                                        caption=caption
                                                                    )
                                                        except Exception as e:
                                                            print(f"Error sending document: {e}")
                                                            await m.reply_text(f"**Error sending file for batch {selected_batch_name}: {str(e)}**")
                                                        finally:
                                                            try:
                                                                os.remove(batch_filename)
                                                                if thumb_path and os.path.exists(thumb_path):
                                                                    os.remove(thumb_path)
                                                            except:
                                                                pass
                                                    else:
                                                        await m.reply_text(
                                                            f"⚠️ <b>No content found in batch:</b> <code>{selected_batch_name}</code>"
                                                        )
                                                else:
                                                    await m.reply_text(
                                                        f"❌ <b>Error fetching batch:</b> <code>{selected_batch_name}</code>\n"
                                                        f"🪵 <b>Details:</b> <code>{response.status}</code>"
                                                    )
                                        except Exception as e:
                                            await m.reply_text(
                                                f"💥 <b>Error processing batch:</b> <code>{selected_batch_name}</code>\n"
                                                f"🧩 <b>Reason:</b> <code>{str(e)}</code>"
                                            )

                                        finally:
                                            processed_batches += 1
                                            try:
                                                await status_msg.delete()
                                            except:
                                                pass
                                    else:
                                        await m.reply_text(f"**Invalid Index Number: {batch_index}**")

                                await m.reply_text(
                                    f"╭━━━〔✅ 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞𝐝〕━━━╮\n"
                                    f"┣• **Batches Done:** `{processed_batches}/{total_batches}`\n"
                                    f"╰━━━━━━━━━━━━━━━━━━━╯"
                                )

                                
                                if editable:
                                    try:
                                        await editable.delete()
                                    except:
                                        pass
                            else:
                                raise Exception("NOTHING FOUND IN THIS COURSE")
                        else:
                            raise Exception(f"{response.text}")
                else:
                    raise Exception('WRONG INPUT')
                    
        except Exception as e:
            error_msg = f"**Error : {e}**"
            if editable:
                try:
                    await editable.edit(error_msg)
                except:
                    await m.reply_text(error_msg)
            else:
                await m.reply_text(error_msg)
            
        finally:
            await session.close()
            await CONNECTOR.close()
