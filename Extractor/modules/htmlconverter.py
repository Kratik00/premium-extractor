import os
import re
import html
from config import PREMIUM_LOGS
from pyrogram import Client, filters

HTML_LOG_CHANNEL = PREMIUM_LOGS   # <-- change if needed

STATIC_THEME_COLOR = "#ff76c8"  # 💖 PINK THEME


def txt_to_html(txt_path, html_path):
    # Read file
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    file_name = os.path.basename(txt_path).replace('.txt', '')

    # Categories
    sections = {
        'video': {"items": []},
        'pdf': {"items": []},
        'other': {"items": []}
    }

    # Categorize links
    def categorize(name, url):
        if (
            re.search(r'\.(mp4|mkv|avi|mov|flv|wmv|m3u8)$', url, re.IGNORECASE)
            or 'youtube.com' in url
            or 'youtu.be' in url
        ):
            return "video"
        elif url.lower().endswith('.pdf'):
            return "pdf"
        return "other"

    for line in lines:
        match = re.match(r'^(.*?)(https?://\S+)$', line.strip())
        if match:
            name, url = match.groups()
            cat = categorize(name, url)
            sections[cat]["items"].append((name.strip(), url.strip()))

    # Build HTML blocks
    html_blocks = ""
    for key in ['video', 'pdf', 'other']:
        items = sections[key]["items"]
        links = [
            f"<a href='{url}' target='_blank'><div class='video'>{html.escape(name)}</div></a>"
            for name, url in items
        ]

        html_blocks += f"""
        <div class='tab-content' id='{key}' style='display:none;'>
            {"".join(links) if links else "<p>No content</p>"}
        </div>
        """

    # Static pink theme applied everywhere 💖
    theme = STATIC_THEME_COLOR

    html_content = f"""
<!DOCTYPE html><html><head>
<meta charset='utf-8'>
<title>{html.escape(file_name)}</title>

<style>
body {{
    background:#0a0a0a;
    color:#fff;
    font-family:'Segoe UI';
    padding:20px;
}}
.video {{
    padding:12px;
    margin-bottom:10px;
    border-left:4px solid {theme};
    background:#1c1c1c;
    border-radius:10px;
}}
.video:hover {{
    background:#2a2a2a;
}}
.tab-button {{
    padding:10px;
    margin:5px;
    background:#222;
    color:#fff;
    border-radius:8px;
    cursor:pointer;
}}
.tab-button.active {{
    background:{theme};
    color:#000;
}}
</style>

</head><body>

<div class="tabs">
    <button class="tab-button" onclick="showTab('video')">🎥 Videos</button>
    <button class="tab-button" onclick="showTab('pdf')">📜 PDFs</button>
    <button class="tab-button" onclick="showTab('other')">☠ Other</button>
</div>

{html_blocks}

<script>
function showTab(id) {{
    document.querySelectorAll('.tab-content').forEach(e => e.style.display = 'none');
    document.getElementById(id).style.display = 'block';
}}
document.addEventListener("DOMContentLoaded", () => showTab('video'));
</script>

</body></html>
"""

    # Write HTML file
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return (
        len(sections["video"]["items"]),
        len(sections["pdf"]["items"]),
        len(sections["other"]["items"]),
    )


async def html_converter_callback(client, message):
    if not message.document or not message.document.file_name.endswith(".txt"):
        return await message.reply_text("⚠️ Please send a valid .txt file.")

    wait_msg = await message.reply_text("🕙 Converting TXT ➜ HTML... Please wait...")

    # SAFE DOWNLOAD path (handles Unicode)
    downloaded_path = await client.download_media(message.document)

    base = os.path.splitext(os.path.basename(downloaded_path))[0]
    safe_base = re.sub(r"[^A-Za-z0-9_]", "_", base)

    txt_path = downloaded_path
    html_path = f"{safe_base}.html"

    # Convert with static pink theme
    video, pdf, other = txt_to_html(txt_path, html_path)

    caption = (
        f"🌸 **HTML Conversion Completed!**\n\n"
        f"🎥 Videos: `{video}`\n"
        f"📜 PDFs: `{pdf}`\n"
        f"📁 Other: `{other}`\n\n"
        f"💖 Theme: Pink (`{STATIC_THEME_COLOR}`)"
    )

    # Send to user
    await client.send_document(message.chat.id, html_path, caption=caption)

    # Auto send to channel
    try:
        await client.send_document(
            HTML_LOG_CHANNEL,
            html_path,
            caption=f"📤 New HTML upload\n👤 User: {message.from_user.mention}"
        )
    except Exception as e:
        print("Channel send error:", e)

    try:
        await wait_msg.delete()
    except:
        pass

    os.remove(txt_path)
    os.remove(html_path)
