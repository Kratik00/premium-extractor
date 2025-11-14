import os
import re
import html
from config import PREMIUM_LOGS
from pyrogram import Client, filters

HTML_LOG_CHANNEL = PREMIUM_LOGS       # Channel to receive HTML files
STATIC_THEME_COLOR = "#ff76c8"        # 💖 Pink theme


def txt_to_html(txt_path, html_path):

    # Read TXT file
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    file_name = os.path.basename(txt_path).replace(".txt", "")

    # Categories
    sections = {
        "video": {"items": []},
        "pdf": {"items": []},
        "other": {"items": []},
    }

    # Categorizer
    def categorize(name, url):
        if (
            re.search(r"\.(mp4|mkv|avi|mov|flv|wmv|m3u8)$", url, re.IGNORECASE)
            or "youtube.com" in url
            or "youtu.be" in url
        ):
            return "video"
        if url.lower().endswith(".pdf"):
            return "pdf"
        return "other"

    # Extract name + URL per line
    for line in lines:
        line = line.strip()
        match = re.match(r"^(.*?)(https?://\S+)$", line)
        if match:
            name, url = match.groups()
            cat = categorize(name, url)
            sections[cat]["items"].append((name.strip(), url.strip()))

    # Build HTML block content
    html_blocks = ""
    theme = STATIC_THEME_COLOR

    for key in ["video", "pdf", "other"]:
        links = []
        for name, url in sections[key]["items"]:
            safe_name = html.escape(name)

            if key == "video":
                links.append(
                    f"<div class='video' onclick=\"playVideo('{url}', '{safe_name}')\">{safe_name}</div>"
                )
            else:
                links.append(
                    f"<a href='{url}' target='_blank'><div class='video'>{safe_name}</div></a>"
                )

        content = "\n".join(links) if links else "<p>No content</p>"

        html_blocks += f"""
        <div class='tab-content' id='{key}' style='display:none;'>
            {content}
        </div>
        """

    # Final HTML
    html_content = f"""<!DOCTYPE html><html><head>
<meta charset='utf-8'>
<title>{html.escape(file_name)}</title>
<meta name='viewport' content='width=device-width, initial-scale=1.0' />

<style>
  body {{
    background:#0a0a0a;
    color:#ffe3ec;
    font-family:'Segoe UI', sans-serif;
    margin:0; padding:20px;
  }}

  .player-box {{ max-width:900px; margin:auto; text-align:center; }}
  video {{ width:100%; border-radius:12px; box-shadow:0 0 15px {theme}; }}
  #videoTitle {{ font-size:20px; font-weight:bold; color:{theme}; margin:10px 0 30px; }}

  .tabs {{
    display:flex; justify-content:center; gap:10px;
    flex-wrap:wrap; margin-bottom:20px;
  }}

  .tab-button {{
    padding:12px 20px; font-size:16px;
    background:rgba(255,255,255,0.05);
    color:#fff; border:1px solid #444;
    border-radius:8px; cursor:pointer;
    font-weight:bold; transition:all 0.3s;
  }}

  .tab-button:hover {{ background:{theme}; color:#000; }}
  .tab-button.active {{
    background:linear-gradient(135deg,{theme}, #ff9fdc);
    color:#000; box-shadow:0 0 12px {theme};
  }}

  .video {{
    background:#1c1c1c; padding:14px 18px;
    border-radius:10px; font-size:15px;
    font-weight:500; transition:0.3s ease;
    border-left:4px solid {theme}; margin-bottom:12px;
  }}

  .video:hover {{
    transform:translateX(6px);
    background:#2a2a2a;
    box-shadow:0 0 10px {theme};
  }}

  a {{ color:{theme}; text-decoration:none; font-weight:500; }}
  a:hover {{ color:#ff9fdc; text-decoration:underline; }}

  .float-name {{
    position:fixed; font-size:40px;
    color:{theme}; border:2px solid #ff9fdc;
    padding:5px 10px; z-index:9999;
    background:rgba(0,0,0,0.6);
    border-radius:10px; animation:floatName 10s ease-in-out infinite alternate;
  }}

  @keyframes floatName {{
    0% {{ top:5%; left:5%; }}
    50% {{ top:90%; left:90%; }}
    100% {{ top:5%; left:5%; }}
  }}

  .footer {{
    text-align:center; margin-top:40px;
    font-size:14px; color:#777;
  }}
</style>

</head><body>

<div class="float-name">✦ LUCIFER ✦</div>

<div class="player-box">
  <video id="player" controls autoplay playsinline>
    <source src="" type="application/x-mpegURL" />
    Your browser does not support the video tag.
  </video>
  <div id="videoTitle"></div>
</div>

<div class="tabs">
  <button class="tab-button" onclick="showTab('video')">🎥 Videos</button>
  <button class="tab-button" onclick="showTab('pdf')">📜 PDF</button>
  <button class="tab-button" onclick="showTab('other')">☠ Other</button>
</div>

{html_blocks}

<div class="footer">
  Developed by <a href="https://t.me/URS_LUCIFER">♞ King Lucifer ♞</a>
</div>

<script>
function playVideo(url, title) {{
  const p = document.getElementById('player');
  p.src = url;
  document.getElementById('videoTitle').textContent = title;
  window.scrollTo({{ top:0, behavior:'smooth' }});
  p.play();
}}

function showTab(id) {{
  document.querySelectorAll('.tab-content').forEach(t => t.style.display='none');
  document.getElementById(id).style.display='block';
  document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
}}

document.addEventListener("DOMContentLoaded", () => showTab('video'));
</script>

</body></html>
"""

    # Write HTML file
    with open(html_path, "w", encoding="utf-8") as f:
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

    # Download file (unicode-safe)
    downloaded = await client.download_media(message.document)

    base = os.path.splitext(os.path.basename(downloaded))[0]
    safe = re.sub(r"[^A-Za-z0-9_]", "_", base)

    txt_path = downloaded
    html_path = f"{safe}.html"

    video, pdf, other = txt_to_html(txt_path, html_path)

    caption = (
        f"🌸 **HTML Conversion Complete!**\n\n"
        f"🎥 Videos: `{video}`\n"
        f"📜 PDFs: `{pdf}`\n"
        f"📁 Other: `{other}`\n\n"
        f"💖 Theme: Pink"
    )

    # Send to user
    await client.send_document(message.chat.id, html_path, caption=caption)

    # Send to channel log
    try:
        await client.send_document(
            HTML_LOG_CHANNEL,
            html_path,
            caption=f"📤 New HTML Upload\n👤 User: {message.from_user.mention}"
        )
    except Exception as e:
        print("Channel Upload Error:", e)

    try:
        await wait_msg.delete()
    except:
        pass

    os.remove(txt_path)
    os.remove(html_path)
