import os
import re
import aiohttp
import json
from datetime import datetime
from typing import List, Tuple, Any, Optional, Dict

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from Extractor import app
from Extractor.core.func import chk_user
from config import PREMIUM_LOGS

LOG_CHANNEL = PREMIUM_LOGS

# -------------------------------------------------------------------
# Config: category ids you mentioned
CATEGORY_COMPLETE_TRAINING = "658d20bd26cab6711f5a4897"   # Complete Training Course category id
CATEGORY_INDIVIDUAL = "6527e5146ee29110fa5df078"          # Individual category id

# If you want static mapping for some complete-training course ids -> _next/data urls,
# put them here (optional). You already supplied several — keep as examples.
NEXT_DATA_MAP = {
    "652e437e47fad6d3441c0c7e": "https://civilguruji.com/_next/data/kdtZjEnRVjOuVcq0KFlTh/package/bim-professional-course/652e437e47fad6d3441c0c7e.json?id=652e437e47fad6d3441c0c7e&url=bim-professional-course",
    "6533a1865506cc759b0f0cce": "https://civilguruji.com/_next/data/kdtZjEnRVjOuVcq0KFlTh/package/highway-engineering/6533a1865506cc759b0f0cce.json?id=6533a1865506cc759b0f0cce&url=highway-engineering",
    "660fc509dc19bb67499197f6": "https://civilguruji.com/_next/data/kdtZjEnRVjOuVcq0KFlTh/package/bridge-construction-course/660fc509dc19bb67499197f6.json?id=660fc509dc19bb67499197f6&url=bridge-construction-course",
    "652e789247fad6d3441ced2b": "https://civilguruji.com/_next/data/kdtZjEnRVjOuVcq0KFlTh/package/construction-management/652e789247fad6d3441ced2b.json?url=construction-management&id=652e789247fad6d3441ced2b",
    "66617162dde5e1934e395961": "https://civilguruji.com/_next/data/kdtZjEnRVjOuVcq0KFlTh/package/advanced-building-construction-training/66617162dde5e1934e395961.json?url=advanced-building-construction-training&id=66617162dde5e1934e395961",
    "652e7a9747fad6d3441d0666": "https://civilguruji.com/_next/data/kdtZjEnRVjOuVcq0KFlTh/package/geotechnical-engineering-course/652e7a9747fad6d3441d0666.json?url=geotechnical-engineering-course&id=652e7a9747fad6d3441d0666",
}


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://civilguruji.com/"
}

def extract_clean_iframe_url(video_url):
    if not video_url:
        return None

    s = video_url.replace("\n", " ").replace("\r", " ").strip()

    s = re.sub(r"</iframe.*$", "", s, flags=re.IGNORECASE)

    m = re.search(r'src=["\']([^"\']+)["\']', s, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()

    m = re.search(r'(https?://[a-zA-Z0-9./?_=-]+)', s)
    if m:
        return m.group(1).strip()

    return None



# ------------------ Helpers ------------------
async def fetch_json(session: aiohttp.ClientSession, url: str, **kwargs) -> Any:
    async with session.get(url, headers=HEADERS, **kwargs) as resp:
        resp.raise_for_status()
        return await resp.json()

def find_first_list_of_dicts_with_keys(obj: Any, required_keys: List[str]) -> Optional[List[Dict]]:
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict) and all(k in obj[0] for k in required_keys):
            return obj
        for item in obj:
            res = find_first_list_of_dicts_with_keys(item, required_keys)
            if res:
                return res
    elif isinstance(obj, dict):
        for v in obj.values():
            res = find_first_list_of_dicts_with_keys(v, required_keys)
            if res:
                return res
    return None
def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "course"
# ------------------ Function: fetch category courses ------------------
async def fetch_category_courses(session: aiohttp.ClientSession, category_id: str) -> Tuple[str, List[Tuple[str,str]]]:
    url = f"https://civilguruji.com/api/course/category-wise-list/{category_id}"
    j = await fetch_json(session, url)
    # try direct courses key
    courses = None
    if isinstance(j, dict):
        courses = j.get("courses") or find_first_list_of_dicts_with_keys(j, ["_id", "name"])
    if not courses:
        courses = find_first_list_of_dicts_with_keys(j, ["_id", "name"])
    lines = []
    pairs = []
    if isinstance(courses, list):
        for c in courses:
            if not isinstance(c, dict):
                continue
            cid = c.get("_id") or c.get("id") or None
            name = c.get("name") or c.get("title") or None
            # some responses embed course inside 'course' object
            if (not cid or not name) and isinstance(c.get("course"), dict):
                nested = c["course"]
                cid = cid or nested.get("_id") or nested.get("id")
                name = name or nested.get("name") or nested.get("title")
            if cid and name:
                pairs.append((name, cid))
                lines.append(f"{name} : {cid}")
    if not lines:
        lines.append("No courses found or unexpected response.")
    return ("\n".join(lines), pairs)

# ------------------ Function: fetch pre-fetched course data (videos) ------------------
async def fetch_prefetched_course_data(session: aiohttp.ClientSession, course_id: str) -> str:
    url = f"https://civilguruji.com/api/course/getPreFetchedCourseData/{course_id}"
    j = await fetch_json(session, url)
    # Locate 'courseContents' (common shapes)
    course_contents = None
    if isinstance(j, dict):
        course_contents = j.get("courseContents") or j.get("courseDetail", {}).get("courseContents")
    if not course_contents:
        course_contents = find_first_list_of_dicts_with_keys(j, ["courseContentName", "courseSubContents"]) or find_first_list_of_dicts_with_keys(j, ["courseContentName"])
    out_lines = []
    if isinstance(course_contents, list):
        for block in course_contents:
            if not isinstance(block, dict):
                continue
            block_name = block.get("courseContentName") or block.get("courseContent") or block.get("title") or "NO_BLOCK_NAME"
            subs = block.get("courseSubContents") or block.get("courseSubContentsList") or block.get("courseSubContent") or []
            if isinstance(subs, list) and subs:
                for s in subs:
                    if not isinstance(s, dict):
                        continue
                    sub_name = s.get("name") or s.get("title") or "NO_NAME"
                    raw = (
                        s.get("videoUrl")
                        or s.get("videoURL")
                        or s.get("url")
                        or s.get("mediaUrl")
                        or (s.get("video", {}).get("url") if isinstance(s.get("video"), dict) else None)
                        or (s.get("Video", {}).get("videoUrl") if isinstance(s.get("Video"), dict) else None)
                        or ""
                    )
                    video_url = extract_clean_iframe_url(raw)
                    out_lines.append(f"[{block_name}]{sub_name}: {video_url}")

            else:
                # maybe block itself has name and video
                sub_name = block.get("name") or block.get("title")
                raw_block = block.get("videoUrl") or ""
                if sub_name and raw_block:
                    video_url = extract_clean_iframe_url(raw_block)
                    out_lines.append(f"[{block_name}]{sub_name}: {video_url}")

    if not out_lines:
        out_lines.append("No course contents/videos found or unexpected JSON structure.")
    return "\n".join(out_lines)

# ------------------ Function: fetch _next/data page and parse similar content ------------------
async def fetch_next_data_and_parse(session: aiohttp.ClientSession, next_data_url: str) -> str:
    j = await fetch_json(session, next_data_url)

    # candidate roots
    root_candidates = []
    if isinstance(j, dict):
        for candidate_key in ("pageProps", "props", "data"):
            if candidate_key in j:
                root_candidates.append(j[candidate_key])
        root_candidates.append(j)

    out_lines = []

    # -------- helper to extract nested path ----------
    def get_path(o, path):
        for key in path:
            if isinstance(o, dict) and key in o:
                o = o[key]
            else:
                return None
        return o

    # -------- parse list of courseContents ----------
    def parse_contents_list(cc):
        lines = []
        for block in cc:
            if not isinstance(block, dict):
                continue

            block_name = (
                block.get("courseContentName")
                or block.get("courseContent")
                or block.get("title")
                or "NO_BLOCK_NAME"
            )

            subs = (
                block.get("courseSubContents")
                or block.get("courseSubContentsList")
                or block.get("courseSubContent")
                or []
            )

            # children
            if isinstance(subs, list) and subs:
                for s in subs:
                    if not isinstance(s, dict):
                        continue

                    sub_name = s.get("name") or s.get("title") or "NO_NAME"

                    raw = (
                        s.get("videoUrl")
                        or s.get("videoURL")
                        or s.get("url")
                        or s.get("mediaUrl")
                        or (s.get("video", {}).get("url") if isinstance(s.get("video"), dict) else None)
                        or (s.get("Video", {}).get("videoUrl") if isinstance(s.get("Video"), dict) else None)
                        or ""
                    )

                    cleaned = extract_clean_iframe_url(raw)
                    lines.append(f"[{block_name}]{sub_name}: {cleaned}")

            else:
                # block-level
                sub_name = block.get("name") or block.get("title")
                raw = block.get("videoUrl") or ""
                if sub_name and raw:
                    cleaned = extract_clean_iframe_url(raw)
                    lines.append(f"[{block_name}]{sub_name}: {cleaned}")

        return lines

    # -------- main extractor ----------
    def extract_from_obj(obj):
        collected = []

        # 1️⃣ Direct courseContents locations
        direct_paths = [
            ["course", "courseDetail", "courseContents"],
            ["courseDetail", "courseContents"],
            ["data", "course", "courseDetail", "courseContents"],
            ["props", "pageProps", "data", "course", "courseDetail", "courseContents"],
        ]

        for path in direct_paths:
            maybe = get_path(obj, path)
            if isinstance(maybe, list):
                collected.extend(parse_contents_list(maybe))

        # 2️⃣ Complete training → packageDataz structure
        pkg_courses = (
            get_path(obj, ["packageDataz", "packageData", "courses"])
            or get_path(obj, ["pageProps", "packageDataz", "packageData", "courses"])
            or get_path(obj, ["props", "pageProps", "packageDataz", "packageData", "courses"])
        )

        if isinstance(pkg_courses, list):
            for course_wrapper in pkg_courses:
                course = course_wrapper.get("course")
                if not isinstance(course, dict):
                    continue

                detail = course.get("courseDetail", {})
                cc = detail.get("courseContents")

                if isinstance(cc, list):
                    collected.extend(parse_contents_list(cc))

        # 3️⃣ Deep fallback search
        if not collected:
            cc = find_first_list_of_dicts_with_keys(
                obj, ["courseContentName", "courseSubContents"]
            )
            if isinstance(cc, list):
                collected.extend(parse_contents_list(cc))

        return collected

    # PROCESS candidates
    for root in root_candidates:
        if not root:
            continue
        found = extract_from_obj(root)
        if found:
            out_lines.extend(found)

    # Final fallback
    if not out_lines:
        out_lines.append("No course contents found in _next data or unexpected structure.")

    # remove duplicates but keep order
    final_list = list(dict.fromkeys(out_lines))

    return "\n".join(final_list)




# ------------------ UI / Callbacks ------------------
# Entry button (user clicks "Civil Guruji")
@app.on_callback_query(filters.regex("^civilguruji_$"))
async def civilguruji_entry(client, callback_query):
    uid = callback_query.from_user.id
    ok = await chk_user(callback_query, uid)
    if ok == 1:
        await callback_query.message.reply_text(
            "🔒 <b>Premium Feature Locked!</b>\n\nContact admin to upgrade.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Contact Admin", url="https://t.me/noobhusir")]])
        )
        return

    # Ask which course type
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Complete Training Course", callback_data=f"civil_type_complete")],
        [InlineKeyboardButton("🔹 Individual Courses", callback_data=f"civil_type_individual")],
    ])
    await callback_query.message.reply_text("💠 <b>Select Course Type:</b>", reply_markup=kb)
    await callback_query.answer()

# When user selects course type
@app.on_callback_query(filters.regex("^civil_type_"))
async def civil_type_select(client, callback_query):
    typ = callback_query.data.replace("civil_type_", "")
    await callback_query.answer()
    async with aiohttp.ClientSession() as session:
        if typ == "complete":
            # fetch category courses for complete training
            text, pairs = await fetch_category_courses(session, CATEGORY_COMPLETE_TRAINING)
            # build keyboard of pairs
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(name, callback_data=f"civil_course_complete|{cid}")] for name, cid in pairs])
            await callback_query.message.reply_text(f"<pre>{text}</pre>", reply_markup=kb)
        else:
            text, pairs = await fetch_category_courses(session, CATEGORY_INDIVIDUAL)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(name, callback_data=f"civil_course_individual|{cid}")] for name, cid in pairs])
            await callback_query.message.reply_text(f"<pre>{text}</pre>", reply_markup=kb)

# When user clicks a course from keyboard
@app.on_callback_query(filters.regex(r"^civil_course_(complete|individual)\|"))
async def civil_course_selected(client, callback_query):
    data = callback_query.data
    m = re.match(r"^civil_course_(complete|individual)\|(.+)$", data)
    if not m:
        await callback_query.answer("Invalid selection", show_alert=True)
        return

    kind, course_id = m.groups()
    await callback_query.answer("⏳ Extracting... please wait")

    async with aiohttp.ClientSession() as session:
        try:
            # ------------------ extract text ------------------
            if kind == "individual":
                txt = await fetch_prefetched_course_data(session, course_id)

            else:
                next_url = NEXT_DATA_MAP.get(course_id)
                if next_url:
                    txt = await fetch_next_data_and_parse(session, next_url)
                else:
                    try:
                        txt = await fetch_prefetched_course_data(session, course_id)
                        if "No course contents" in txt:
                            raise Exception("empty prefetched")
                    except:
                        txt = "Unable to find course content via API. Add mapping in NEXT_DATA_MAP."

            # ------------------ find course name for filename ------------------
            async with aiohttp.ClientSession() as sfind:
                complete_list = (await fetch_category_courses(sfind, CATEGORY_COMPLETE_TRAINING))[1]
                individual_list = (await fetch_category_courses(sfind, CATEGORY_INDIVIDUAL))[1]

            course_name = None
            for name, cid in complete_list + individual_list:
                if cid == course_id:
                    course_name = name
                    break

            if not course_name:
                course_name = f"course-{course_id}"

            slug = slugify(course_name)
            fname = f"{slug}.txt"

            # ------------------ save & send ------------------
            with open(fname, "w", encoding="utf-8") as fh:
                fh.write(txt)

            caption = (
                f"╭━━『 💠 CivilGuruji Extractor 』━━╮\n"
                f"📚 <b>Course:</b> <code>{course_name}</code>\n"
                f"🔗 <b>Type:</b> {kind}\n"
                f"🕒 <b>Extracted:</b> {datetime.now().strftime('%d-%m-%Y %I:%M %p')}\n"
                f"╰━━━━━━━━━━━━━━━━━━━━━━╯"
            )

            await app.send_document(
                chat_id=callback_query.message.chat.id,
                document=fname,
                caption=caption
            )

            # log channel
            try:
                await app.send_document(
                    chat_id=LOG_CHANNEL,
                    document=fname,
                    caption=f"📡 CivilGuruji extract\n\n{caption}"
                )
            except:
                pass
            finally:
                os.remove(fname)
                await callback_query.message.delete()

        except Exception as e:
            print("Error extracting course:", e)
            await callback_query.message.edit_text(f"⚠️ Error extracting course: kya hi ukhad lega reson jaan ke tu")

# ------------------ end module ------------------
