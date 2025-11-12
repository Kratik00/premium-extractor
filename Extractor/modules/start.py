import re
import json
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pyrogram import filters
from Extractor import app
from config import OWNER_ID
from Extractor.core import script
from Extractor.core.func import subscribe, chk_user
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from Extractor.modules.appex_v1 import api_v1
from Extractor.modules.appex_v2 import appex_v2_txt
from Extractor.modules.appex_v3 import appex_v3_txt
from Extractor.modules.appex_v4 import appex_v4_txt
from Extractor.modules.classplus import classplus_txt
from Extractor.modules.pw import pw_login
from Extractor.modules.exampur import exampur_txt
from Extractor.modules.careerwill import career_will
from Extractor.modules.utk import handle_utk_logic
from Extractor.modules.mypathshala import my_pathshala_login
from Extractor.modules.khan import khan_login
from Extractor.modules.kdlive import kdlive
from Extractor.modules.iq import handle_iq_logic
from Extractor.modules.getappxotp import send_otpp
from Extractor.modules.findapi import findapis_extract
from Extractor.modules.rg_vikramjeet import rgvikram_txt
from Extractor.modules.adda import adda_command_handler
        
from Extractor.modules.freecp import *
from Extractor.modules.cdsjourneyfree import *
from Extractor.modules.selectionwayfree import *
from Extractor.modules.freeappx import *
from Extractor.modules.freepw import *

from Extractor.core.mongo import plans_db
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import config

THREADPOOL = ThreadPoolExecutor(max_workers=2000)
TIMEOUT = 300  # 5 minutes timeout

# buttons = InlineKeyboardMarkup([
#                 [
#                   InlineKeyboardButton("📇Login/without login", callback_data="modes_")
#                 ],
#                 [
#                  # InlineKeyboardButton("🔍 Fɪɴᴅ Aᴘɪ", callback_data="findapi_"),
#                   #InlineKeyboardButton("📓 Aᴘᴘx Lɪsᴛ", callback_data="appxlist")
#                 #],
#                 #[
#                    InlineKeyboardButton("🚀help", callback_data="help_")
#                    InlineKeyboardButton("🚨Close", callback_data="close_")
#                    InlineKeyboardButton("💻Developer", url="https://t.me/urs_lucifer")
#                 ]
                
#                 ])

buttons = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📇 Login / Without Login", callback_data="modes_")
    ],
    [
        InlineKeyboardButton("🔍 Find API", callback_data="findapi_")
    ],
    [
        InlineKeyboardButton("🚀 Help", callback_data="help_"),
        InlineKeyboardButton("💻 Developer", url="https://t.me/URS_LUCIFER"),
        InlineKeyboardButton("🚨 Close", callback_data="close_data")
    ]
])
modes_button = [[
                  InlineKeyboardButton("🔏Without login", callback_data="custom_")
                ],[
                  InlineKeyboardButton("🔑Login", callback_data="manual_"),
                ],[
                  InlineKeyboardButton("Back", callback_data="home_")
                ]]


custom_button = [[
                  InlineKeyboardButton("🧩Physics Wallah", callback_data="pwwp"),
                  InlineKeyboardButton("🛰️APPX", callback_data="appxwp"),
                ],[
                  InlineKeyboardButton("🎯Classplus", callback_data="cpwp")
                ],[
                  InlineKeyboardButton("🪄 SelectionWay", callback_data="selectionway_")
                ],[
                  InlineKeyboardButton("🤖 CDS JOURNEY", callback_data="cdsjourney_")
                ],[
                  InlineKeyboardButton("👑 PREMIUM", callback_data="premium_")
                ],[
                  InlineKeyboardButton("🌪️Back", callback_data="modes_")
                ]]

button1 = [              
                [
                    InlineKeyboardButton(" 🕹️APPX", callback_data="appx_"),
                    InlineKeyboardButton(" 🕹️APPX OTP", callback_data="appxotp_")
                ],
                [
                    InlineKeyboardButton(" 🕹️CLASSPLUS", callback_data="classplus_"),
                    InlineKeyboardButton(" 🕹️UTKARSH", callback_data="utkarsh_")
                ],
                [
                    InlineKeyboardButton(" 🕹️KHAN GS", callback_data="khan_"),   
                    InlineKeyboardButton(" 🕹️PHYSICS WALLAH", callback_data="pw_")    
                ],
                # [
                #     InlineKeyboardButton("👑 Sᴛᴜᴅʏ IQ", callback_data="iq_"),
                #     InlineKeyboardButton("👑 Kᴅ Cᴀᴍᴘᴜs", callback_data="kdlive_")         
                # ],
                # [
                #     InlineKeyboardButton("👑 Cᴀʀᴇᴇʀᴡɪʟʟ", callback_data="cw_"),   
                #     InlineKeyboardButton("👑 Uᴛᴋᴀʀsʜ", callback_data="adda_")              
                # ],
                # [
                #    # InlineKeyboardButton("CʟᴀssPʟᴜs", callback_data="classplus_"),
                #     InlineKeyboardButton("👑 Mʏ Pᴀᴛʜsʜᴀʟᴀ", callback_data="my_pathshala_") ,
                #     InlineKeyboardButton("👑 ExamPur", callback_data="exampur_txt") 


                # ],
                [
                  #  InlineKeyboardButton("﹤", callback_data="next_4"),
                    InlineKeyboardButton("🌪️Back", callback_data="modes_"),
                  #  InlineKeyboardButton("﹥", callback_data="next_1")
                ]
                ]


button2 = [
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),   
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),              
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),   
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),       
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),       
                ],
                [
                    InlineKeyboardButton("﹤", callback_data="manual_"),
                    InlineKeyboardButton("ʙ ᴀ ᴄ ᴋ", callback_data="modes_"),
                    InlineKeyboardButton("﹥", callback_data="next_2")
                ]
                ]



button3 = [              
                [   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [              
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [
                    InlineKeyboardButton("﹤", callback_data="next_1"),
                    InlineKeyboardButton("ʙ ᴀ ᴄ ᴋ", callback_data="modes_"),
                    InlineKeyboardButton("﹥", callback_data="next_3")
                ]
                ]



button4 = [              
                [   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [              
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [
                    InlineKeyboardButton("﹤", callback_data="next_2"),
                    InlineKeyboardButton("ʙ ᴀ ᴄ ᴋ", callback_data="modes_"),
                    InlineKeyboardButton("﹥", callback_data="next_4")
                ]
                ]


button5 = [              
                [   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [   
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [              
                    InlineKeyboardButton("Soon", callback_data="maintainer_"),
                    InlineKeyboardButton("Soon", callback_data="maintainer_")
                ],
                [
                    InlineKeyboardButton("﹤", callback_data="next_3"),
                    InlineKeyboardButton("ʙ ᴀ ᴄ ᴋ", callback_data="modes_"),
                    InlineKeyboardButton("﹥", callback_data="manual_")
                ]
                ]
                
button6 = [        
                [
                    InlineKeyboardButton("Achievers Academy", callback_data="achievers_acc"),
                    InlineKeyboardButton("Adhyayan Mantra", callback_data="adhyan_mantra"),
                    InlineKeyboardButton("Aman Sir", callback_data="aman_sir"),
                ],
                [
                    InlineKeyboardButton("Anil Sir iti", callback_data="anilsir_iti"),
                    InlineKeyboardButton("App Exampur", callback_data="app_exampur"),
                    InlineKeyboardButton("Army Study", callback_data="army_study"),
                ],
                [
                    InlineKeyboardButton("Ashish Sing Lec", callback_data="Ashish_lec"),
                    InlineKeyboardButton("Bharti Sir", callback_data="bharti_sir"),
                    InlineKeyboardButton("Booster Academy", callback_data="booster_academy"),
                ],
                [
                    InlineKeyboardButton("Cadet Defence", callback_data="cadet_defence"),
                    InlineKeyboardButton("Cammando Academy", callback_data="commando_acc"),
                    InlineKeyboardButton("Christopher", callback_data="christopher_acc"),
                ],
                [
                    InlineKeyboardButton("Dhananjay IAS", callback_data="dhananjay_ias"),
                    InlineKeyboardButton("E1 Coaching", callback_data="e1_coaching"),
                    InlineKeyboardButton("Examo Academy", callback_data="examo_acc"),
                ],
                [
                    InlineKeyboardButton("Exampur", callback_data="exampur_"),
                    InlineKeyboardButton("Goal Yaan", callback_data="goal_yaan"),
                    InlineKeyboardButton("Gk Cafe", callback_data="gk_cafe"),
                ],
                [
                    InlineKeyboardButton("Grow Academy", callback_data="grow_acc"),
                    InlineKeyboardButton("Gyan Bindu", callback_data="gyan_bindu"),
                    InlineKeyboardButton("KTDT", callback_data="kt_dt"),
                ],
                [
                    InlineKeyboardButton("Md Classes", callback_data="md_classes"),
                    InlineKeyboardButton("Mg Concept", callback_data="mg_concept"),
                    InlineKeyboardButton("Mother's Live", callback_data="mothers_live"),
                ],
                [
                    InlineKeyboardButton("Neo Spark", callback_data="neo_spark"),
                    InlineKeyboardButton("Neon Classes", callback_data="neon_classes"),
                    InlineKeyboardButton("Neet Kakajee", callback_data="neet_kakajee"),
                ],
                [
                    InlineKeyboardButton("Ng Learners", callback_data="ng_learners"),
                    InlineKeyboardButton("Nidhi Academy", callback_data="nidhi_academy"),
                    InlineKeyboardButton("Nimisha Bansal", callback_data="nimisha_bansal"),
                ],
                [
                    InlineKeyboardButton("Nirman IAS", callback_data="nirman_ias"),
                    InlineKeyboardButton("Note Book", callback_data="note_book"),
                    InlineKeyboardButton("Ocean Gurukul", callback_data="ocean_gurukul"),
                ],
                [
                    InlineKeyboardButton("Officers Academy", callback_data="officers_acc"),
                    InlineKeyboardButton("Parmar Ssc", callback_data="permar_ssc"),
                    InlineKeyboardButton("Perfect Academy", callback_data="perfect_acc"),
                ],
                [
                    InlineKeyboardButton("PHYSICSASINGH", callback_data="physics_asingh"),
                    InlineKeyboardButton("Platform", callback_data="platform_"),
                    InlineKeyboardButton("RG Vikramjeet", callback_data="rg_vikramjeet"),
                ],
                [
                    InlineKeyboardButton("Rk Sir", callback_data="rk_sir"),
                    InlineKeyboardButton("Rwa", callback_data="rwa_"),
                    InlineKeyboardButton("Sachin Academy", callback_data="sachin_acc"),
                ],
                [
                    InlineKeyboardButton("Samyak", callback_data="samyak_ras"),
                    InlineKeyboardButton("Sankalp", callback_data="sankalp_"),
                    InlineKeyboardButton("Science Fun", callback_data="science_fun"),
                ],
                [
                    InlineKeyboardButton("Singhkori", callback_data="singhkori_education"),
                    InlineKeyboardButton("Space IAS", callback_data="space_ias"),
                    InlineKeyboardButton("Study Mantra", callback_data="study_mantra"),
                ],
                [
                    InlineKeyboardButton("Ssc Gurkul", callback_data="ssc_gurukul"),
                    InlineKeyboardButton("Ssc Maker", callback_data="ss_maker"),
                    InlineKeyboardButton("Target Plus", callback_data="target_plus"),
                ],
                [
                    InlineKeyboardButton("Target Upsc", callback_data="target_upsc"),
                    InlineKeyboardButton("TeachingPariksha", callback_data="teaching_"),
                    InlineKeyboardButton("Think Ssc", callback_data="think_ssc"),
                ],
                [
                    InlineKeyboardButton("Tutors Adda", callback_data="tutors_adda"),
                    InlineKeyboardButton("Uc Live", callback_data="uc_live"),
                    InlineKeyboardButton("Vasu Concept", callback_data="vasu_concept"),
                ],
                [
                    InlineKeyboardButton("Vidya Bihar", callback_data="vidya_bihar"),
                    InlineKeyboardButton("Vidya Education", callback_data="vidya_education"),
                    InlineKeyboardButton("Vj Education", callback_data="vj_education"),
                ],
                [
                    InlineKeyboardButton("Winners", callback_data="winners_"),
                    InlineKeyboardButton("Yodha", callback_data="yodha_"),
                ],
                [
                    InlineKeyboardButton("﹤", callback_data="prev"),
                    InlineKeyboardButton("𝙷𝙾𝙼𝙴", callback_data="home_"),
                    InlineKeyboardButton("﹥", callback_data="next"),
                ]
                ]




back_button  = [[
                    InlineKeyboardButton("🤍BACK", callback_data="modes_"),                    
                ]]



# ------------------------------------------------------------------------------- #

def photo():
    # Use THUMB_URL (correct case) from config
    return config.THUMB_URL

    # Keeping the old code as comment for reference
    """
    try:
        url = (
            f"https://api.unsplash.com/photos/random"
            f"?query={config.UNSPLASH_QUERY}&orientation=landscape&client_id={config.UNSPLASH_ACCESS_KEY}"
        )
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'urls' in data and 'regular' in data['urls']:
                return data['urls']['regular']
        
        return config.thumb_url
    except Exception as e:
        print(f"Error fetching photo: {e}")
        return config.thumb_url
    """

# @app.on_message(filters.command("start"))
# async def start(_, message):
#     await message.reply_photo(
#         photo="https://graph.org/file/0b988a4a0e9dd4647026b-ffabe40b6085866928.jpg",
#         caption="**Hey dear click /apps for more info **",
#         reply_markup=InlineKeyboardMarkup(
#             [
#                 [InlineKeyboardButton("📢CHANNEl", url="https://t.me/URS_LUCIFER")]
#             ]
#         )
#     )
                
@app.on_message(filters.command("start"))  # & filters.user(SUDO_USERS))
async def start(_, message):
    join = await subscribe(_, message)
    if join == 1:
        return
    try:
        await message.reply_photo(
            photo=random.choice(script.IMG),
            caption=script.START_TXT.format(message.from_user.mention),
            reply_markup=buttons
        )
    except Exception as e:
        print(f"Error in start command: {e}")
        # If photo fails, send message without photo
        await message.reply_text(
            script.START_TXT.format(message.from_user.mention),
            reply_markup=buttons
        )

@app.on_callback_query(filters.regex("^appxlist$"))
async def show_alphabet(client, query):
    keyboard = get_alphabet_keyboard()
    await query.message.edit_text("𝐒𝐞𝐥𝐞𝐜𝐭 𝐀 𝐋𝐞𝐭𝐭𝐞𝐫 𝐓𝐨 𝐕𝐢𝐞𝐰 𝐀𝐩𝐩𝐬 ✨", reply_markup=keyboard)

@app.on_callback_query(filters.regex("^alpha_"))
async def show_apps_for_letter(client, query):
    letter = query.data.split('_')[1]
    apps = get_apps_by_letter(letter)
    
    if not apps:
        await query.answer(f"No apps found starting with {letter}", show_alert=True)
        return
    
    keyboard, total_pages = create_app_keyboard(apps, page=0, letter=letter)
    # Create header with total apps count and page info
    text = f"📱 𝐀𝐩𝐩𝐬 𝐒𝐭𝐚𝐫𝐭𝐢𝐧𝐠 𝐖𝐢𝐭𝐡 '{letter}' ({len(apps)} apps)\n"
    text += f"𝐏𝐚𝐠𝐞: 1/{total_pages}\n"
    text += "═══════════════════"
    
    try:
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        print(f"Error showing apps: {e}")
        await query.answer("Error displaying apps. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("^page_"))
async def handle_pagination(client, query):
    try:
        # New format: page_LETTER_PAGENUMBER
        _, letter, page = query.data.split('_')
        page = int(page)
        
        apps = get_apps_by_letter(letter)
        if not apps:
            await query.answer("No apps found", show_alert=True)
            return
            
        keyboard, total_pages = create_app_keyboard(apps, page, letter)
        
        # Update header with new page number
        text = f"📱 𝐀𝐩𝐩𝐬 𝐒𝐭𝐚𝐫𝐭𝐢𝐧𝐠 𝐖𝐢𝐭𝐡 '{letter}' ({len(apps)} apps)\n"
        text += f"𝐏𝐚𝐠𝐞: {page + 1}/{total_pages}\n"
        text += "═══════════════════"
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        print(f"Pagination error: {e}")
        await query.answer("Error in pagination. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("^app_"))
async def handle_app_selection(client, query):
    app_name = query.data.split('_')[1]
    # Here you can implement what happens when an app is selected
    await query.answer(f"Selected app: {app_name}", show_alert=True)
    # Add your app handling logic here

async def process_with_timeout(func, client, message, user_id, timeout=60):
    try:
        return await asyncio.wait_for(func(client, message, user_id), timeout=timeout)
    except asyncio.TimeoutError:
        return "timeout"
    except Exception as e:
        print(f"Error in process_with_timeout: {e}")
        return f"error:{str(e)}"

@app.on_callback_query(filters.regex("^pwwp$"))
async def pwwp_callback(client, callback_query):
    try:
        # Send initial processing message
        processing_msg = await callback_query.message.reply_text(
            "ENTER YOUR TOKEN"
        )
        
        user_id = callback_query.from_user.id
        
        try:
            # Process with timeout
            result = await process_with_timeout(process_pwwp, client, callback_query.message, user_id)
            
            if result == "timeout":
                await processing_msg.edit_text(
                    "⚠️ Process timed out. Please try again.\n"
                    "Tip: Make sure to respond within 60 seconds when prompted."
                )
            elif result and result.startswith("error:"):
                await processing_msg.edit_text(
                    f"❌ An error occurred: {result[6:]}\n"
                    "Please try again."
                )
            else:
                await processing_msg.delete()
                
        except Exception as e:
            await processing_msg.edit_text(
                "❌ Process failed. Please try again.\n"
                f"Error: {str(e)}"
            )
            
    except Exception as e:
        print(f"Error in pwwp_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

@app.on_callback_query(filters.regex("^appxwp$"))
async def appxwp_callback(client, callback_query):
    try:
        # Send initial processing message
        processing_msg = await callback_query.message.reply_text(
            "⏳ Starting process... Please wait"
        )
        
        user_id = callback_query.from_user.id
        
        try:
            # Process with timeout
            result = await process_with_timeout(process_appxwp, client, callback_query.message, user_id)
            
            if result == "timeout":
                await processing_msg.edit_text(
                    "⚠️ Process timed out. Please try again.\n"
                    "Tip: Make sure to respond within 60 seconds when prompted."
                )
            elif result and result.startswith("error:"):
                await processing_msg.edit_text(
                    f"❌ An error occurred: {result[6:]}\n"
                    "Please try again."
                )
            else:
                await processing_msg.delete()
                
        except Exception as e:
            await processing_msg.edit_text(
                "❌ Process failed. Please try again.\n"
                f"Error: {str(e)}"
            )
            
    except Exception as e:
        print(f"Error in appxwp_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

@app.on_callback_query(filters.regex("^selectionway_$"))
async def selectionway_callback(client, callback_query):
    try:
        # Send processing message
        processing_msg = await callback_query.message.reply_text(
            "⚙️ <b>Handling SelectionWay Extractor...</b>\n\nPlease wait a few seconds 💫"
        )

        user_id = callback_query.from_user.id

        try:
            # Run the SelectionWay extractor process with timeout
            result = await process_with_timeout(process_selectionway, client, callback_query.message, user_id)

            if result == "timeout":
                await processing_msg.edit_text(
                    "⚠️ <b>Process timed out!</b>\n"
                    "Please try again.\n\n"
                    "💡 Tip: Respond within <b>60 seconds</b> when prompted."
                )
            elif result and result.startswith("error:"):
                await processing_msg.edit_text(
                    f"❌ <b>An error occurred:</b> {result[6:]}\n\nPlease try again."
                )
            else:
                await processing_msg.delete()

        except Exception as e:
            await processing_msg.edit_text(
                "❌ <b>Process failed.</b>\n\n"
                f"Error: <code>{str(e)}</code>\n"
                "Please retry after a moment."
            )

    except Exception as e:
        print(f"Error in selectionway_callback: {e}")
        await callback_query.answer("⚠️ An error occurred while handling SelectionWay.", show_alert=True)

@app.on_callback_query(filters.regex("^cpwp$"))
async def cpwp_callback(client, callback_query):
    lol = await chk_user(callback_query, callback_query.from_user.id)
    if lol == 1:
        await callback_query.message.reply_text(
            "🔒 <b>Premium Feature Locked!</b>\n\n"
            "You don’t have access to use this feature yet.\n"
            "💎 <b>Contact:</b> <a href='https://t.me/URS_LUCIFER'>LUCIFER</a> to upgrade your plan.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("💬 Contact Admin", url="https://t.me/noobhusir")]
                ]
            )
        )
        return

    try:
        # Send initial processing message
        processing_msg = await callback_query.message.reply_text(
            "**⚙️Handling classplus....... Please Wait💫**"
        )
        
        user_id = callback_query.from_user.id
        
        try:
            # Process with timeout
            result = await process_with_timeout(process_cpwp, client, callback_query.message, user_id)
            
            if result == "timeout":
                await processing_msg.edit_text(
                    "⚠️ Process timed out. Please try again.\n"
                    "Tip: Make sure to respond within 60 seconds when prompted."
                )
            elif result and result.startswith("error:"):
                await processing_msg.edit_text(
                    f"❌ An error occurred: {result[6:]}\n"
                    "Please try again."
                )
            else:
                await processing_msg.delete()
                
        except Exception as e:
            await processing_msg.edit_text(
                "❌ Process failed. Please try again.\n"
                f"Error: {str(e)}"
            )
            
    except Exception as e:
        print(f"Error in cpwp_callback: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

@app.on_callback_query(filters.regex("^selectionway_$"))
async def handle_selectionway(client, callback_query):
    await selectionway_callback(client, callback_query)

@app.on_callback_query(filters.regex("^sw_batch_"))
async def handle_sw_batch(client, callback_query):
    await selectionway_batch_callback(client, callback_query)

@app.on_callback_query(filters.regex("^cw$"))
async def career_will_callback(app: Client, callback_query: CallbackQuery):
    try:
        await callback_query.answer()
        processing_msg = await callback_query.message.reply_text("Starting CareerWill extractor...")
        await career_will(app, callback_query.message)
        try:
            await processing_msg.delete()
        except:
            pass
    except Exception as e:
        await callback_query.message.reply_text(f"Error: {str(e)}")

@app.on_callback_query()
async def handle_callback(client, query):  # <- client यहाँ होना चाहिए

    if query.data=="home_":        
        
        await query.message.edit_text(
              script.START_TXT.format(query.from_user.mention),
              reply_markup=buttons
            )
     
    elif query.data=="modes_":
      #  lol = await chk_user(query, query.from_user.id)
       # if lol == 1:
         # return
        reply_markup = InlineKeyboardMarkup(modes_button)
        await query.message.edit_text(
              script.MODES_TXT,
              reply_markup=reply_markup)
        
        
    elif query.data=="custom_":        
        reply_markup = InlineKeyboardMarkup(custom_button)
        await query.message.edit_text(
              script.CUSTOM_TXT,
              reply_markup=reply_markup
            )
        
     
    elif query.data=="manual_":        
        reply_markup = InlineKeyboardMarkup(button1)
        await query.message.edit_text(
              script.MANUAL_TXT,
              reply_markup=reply_markup
            )

    elif query.data == "v1_":
        
        user_id = query.from_user.id
        user = await client.get_users(user_id)
        await api_v1(app, query.message, user)
      
    elif query.data=="v4_":
        user_id = query.from_user.id
        user = await client.get_users(user_id)
        api = await app.ask(query.message.chat.id, text = "`>_` **Enter AppX API (skip https://)** → `tcsexamzoneapi.classx.co.in` ⚙️")
        api_txt = api.text
        name = api_txt.split('.')[0].replace("api", "") if api else api_txt.split('.')[0]
        await appex_v2_txt(app, query.message, api, name, user)
      
    elif query.data=="v2_": 
        api = await app.ask(query.message.chat.id, text = "`>_` **Enter AppX API (skip https://)** → `tcsexamzoneapi.classx.co.in` ⚙️")
        api_txt = api.text
        name = api_txt.split('.')[0].replace("api", "") if api else api_txt.split('.')[0]
        await appex_v2_txt(app, query.message, api_txt, name)

    elif query.data=="v3_": 
        api = await app.ask(query.message.chat.id, text = "`>_` **Enter AppX API (skip https://)** → `tcsexamzoneapi.classx.co.in` ⚙️")
        api_txt = api.text
        name = api_txt.split('.')[0].replace("api", "") if api else api_txt.split('.')[0]
        await appex_v3_txt(app, query.message, api_txt, name)
      
    #elif query.data=="next_1":        
        #reply_markup = InlineKeyboardMarkup(button2)
      #  await query.message.edit_text(
           #   script.MANUAL_TXT,
          #    reply_markup=reply_markup
          #  )
      
 #   elif query.data=="next_2":        
      #  reply_markup = InlineKeyboardMarkup(button3)
      #  await query.message.edit_text(
          #    script.MANUAL_TXT,
          #    reply_markup=reply_markup
         #   )
      
   # elif query.data=="next_3":        
       # reply_markup = InlineKeyboardMarkup(button4)
       # await query.message.edit_text(
           #   script.MANUAL_TXT,
            #  reply_markup=reply_markup
          #  )

  #  elif query.data=="next_4":        
      #  reply_markup = InlineKeyboardMarkup(button5)
      #  await query.message.edit_text(
          #    script.MANUAL_TXT,
          #    reply_markup=reply_markup
          #  )

          
    elif query.data=="cw_":
        try:
            await query.answer()
            processing_msg = await query.message.reply_text("Starting CareerWill extractor...")
            await career_will(app, query.message)
            try:
                await processing_msg.delete()
            except:
                pass
        except Exception as e:
            await query.message.reply_text(f"Error: {str(e)}")
        
    elif query.data=="utkarsh_":
        await handle_utk_logic(app, query.message)
        
    elif query.data=="my_pathshala_":
        await my_pathshala_login(app, query.message)
    
    elif query.data=="adda_":
        await adda_command_handler(app, query.message)

    elif query.data=="exampur_txt":
        await exampur_txt(app, query.message)

    elif query.data=="appxotp_":
        await send_otpp(app, query.message)
    
    elif query.data=="appx_":
        await appex_v4_txt(app, query.message)
        
    elif query.data=="findapi_":
        await findapis_extract(app, query.message)
        
    elif query.data=="kdlive_":
        await kdlive(app, query.message)
    
    elif query.data=="iq_":
        await handle_iq_logic(app, query.message)
   
   
    elif query.data == 'pw_':
        await pw_login(app, query.message)
        
    elif query.data=="khan_":
        await khan_login(app, query.message)

    elif query.data=="perfect_acc":     
        api = "perfectionacademyapi.appx.co.in"
        name = "Perfection Academy"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="e1_coaching":     
        api = "e1coachingcenterapi.classx.co.in"
        name = "e1 coaching"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="samyak_ras":     
        api = "samyakapi.classx.co.in"
        name = "Samyak"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="vj_education":     
        api = "vjeducationapi.appx.co.in"
        name = "VJ Education"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="gyan_bindu":     
        api = "gyanbinduapi.appx.co.in"
        name = "Gyan Bindu"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="dhananjay_ias":     
        api = "dhananjayiasacademyapi.classx.co.in"
        name = "Dhananjay IAS"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="think_ssc":     
        api = "thinksscapi.classx.co.in"
        name = "Think SSC"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="Ashish_lec":     
        api = "ashishsinghlecturesapi.classx.co.in"
        name = "Ashish Singh"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="tutors_adda":     
        api = "tutorsaddaapi.classx.co.in"
        name = "Tutors Adda"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="nimisha_bansal":     
        api = "nimishabansalapi.appx.co.in"
        name = "Nimisha Bansal"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="sachin_acc":     
        api = "sachinacademyapi.classx.co.in"
        name = "Sachin Academy"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="acharya_classes":     
        api = "acharyaclassesapi.classx.co.in"
        name = "Acharya Classes"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="target_plus":     
        api = "targetpluscoachingapi.classx.co.in"
        name = "Target Plus Coaching"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="rwa_":   
        api = "rozgarapinew.teachx.in"
        name = "Rojgar with Ankit"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="winners_":     
        api = "winnersinstituteapi.classx.co.in"
        name = "Winners"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="ocean_gurukul":     
        api = "oceangurukulsapi.classx.co.in"
        name = "Ocean Gurukul"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="mg_concept":     
        api = "mgconceptapi.classx.co.in"
        name = "MG Concept"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="yodha_":     
        api = "yodhaappapi.classx.co.in"
        name = "Yodha"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="note_book":     
        api = "notebookapi.classx.co.in"
        name = "Note Book"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="uc_live":     
        api = "ucliveapi.classx.co.in"
        name = "UC LIVE"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="space_ias":     
        api = "spaceiasapi.classx.co.in"
        name = "Space IAS"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="rg_vikramjeet":     
        api = "rgvikramjeetapi.classx.co.in"
        name = "RG Vikramjeet"
        await rgvikram_txt(app, query.message, api, name)
      
    elif query.data=="vidya_bihar":     
        api = "vidyabiharapi.teachx.in"
        name = "Vidya Vihar"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="aman_sir":     
        api = "amansirenglishapi.classx.co.in"
        name = "Aman Sir English"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="nirman_ias":     
        api = "nirmaniasapi.classx.co.in"
        name = "Nirman IAS"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="permar_ssc":     
        api = "parmaracademyapi.classx.co.in"
        name = "Parmar Academy"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="neo_spark":     
        api = "neosparkapi.classx.co.in"
        name = "Neo Spark"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="md_classes":     
        api = "mdclassesapi.classx.co.in"
        name = "MD Classes"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="ng_learners":     
        api = "nglearnersapi.classx.co.in"
        name = "NG Learners"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="ssc_gurukul":     
        api = "ssggurukulapi.appx.co.in"
        name = "SSC Gurukul"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="army_study":     
        api = "armystudyliveclassesapi.classx.co.in"
        name = "Army Study Live"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="sankalp_":     
        api = "sankalpclassesapi.classx.co.in"
        name = "Sankalp"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="target_upsc":     
        api = "targetupscapi.classx.co.in"
        name = "Target UPSC"
        await appex_v3_txt(app, query.message, api, name)
      
    elif query.data=="gk_cafe":     
        api = "gkcafeapi.classx.co.in"
        name = "GK Cafe"
        await appex_v3_txt(app, query.message, api, name)

    elif query.data == 'officers_acc':
        api = "theofficersacademyapi.classx.co.in"
        name = "Officers Academy"
        await appex_v3_txt(app, query.message, api, name)

    elif query.data == 'rk_sir':
        api = "rksirofficialapi.classx.co.in"
        name = "Rk Sir Official"
        await appex_v3_txt(app, query.message, api, name) 
      
    elif query.data == 'study_mantra':
        api = "studymantraapi.classx.co.in"
        name = "Study Mantra"
        await appex_v3_txt(app, query.message, api, name) 

    elif query.data == 'science_fun':
        api = "sciencefunapi.classx.co.in"
        name = "Science Fun"
        await appex_v3_txt(app, query.message, api, name) 

    elif query.data == 'grow_acc':
        api = "growacademyapi.classx.co.in"
        name = "Grow Academy"
        await appex_v3_txt(app, query.message, api, name) 

    elif query.data == 'goal_yaan':
        api = "goalyaanapi.appx.co.in"
        name = "Goal Yaan"
        await appex_v3_txt(app, query.message, api, name) 

    elif query.data == 'anilsir_iti':
        api = "anilsiritiapi.classx.co.in"
        name = "Anil Sir Iti"
        await appex_v3_txt(app, query.message, api, name) 

    elif query.data == 'education_adda':
        api = "educationaddaplusapi.classx.co.in"
        name = "Education Adda Plus"
        await appex_v3_txt(app, query.message, api, name) 

    elif query.data == 'achievers_acc':
        api = "achieversacademyapi.classx.co.in"
        name = "Achievers Academy"
        await appex_v3_txt(app, query.message, api, name) 

    elif query.data == 'commando_acc':
        api = "commandoacademyapi.appx.co.in"
        name = "Commando Academy"
        await appex_v3_txt(app, query.message, api, name) 



    elif query.data == 'neet_kakajee':
        api = "neetkakajeeapi.classx.co.in"
        name = "Neet Kaka JEE"
        await appex_v3_txt(app, query.message, api, name) 

    elif query.data == 'app_exampur':
        api = "exampurapi.classx.co.in"
        name = "App Exampur"
        await appex_v2_txt(app, query.message, api, name) 
  
    elif query.data=="classplus_":          
        await classplus_txt(app, query.message)
  
    elif query.data == 'pw2_':
        await query.message.reply_text(
            "**CHHOSE FROM BELOW **",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Mobile No.", callback_data='mobile_'),
                    InlineKeyboardButton("Token", callback_data='token_'),
                ]]))
    elif query.data == "help_":
        help_text = (
            "💡 <b>Help Menu</b>\n\n"
            "• Use <b>Login / Without Login</b> to access extraction modes.\n"
            "• Tap <b>Developer</b> to contact support.\n"
            "• Use <b>Close</b> to exit this menu.\n\n"
            "🚀 <i>Simple. Fast. Classy.</i>"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 Back", callback_data="modes_"),
                InlineKeyboardButton("🚨 Close", callback_data="close_data")
            ]
        ])
        await query.message.edit_text(help_text, reply_markup=keyboard)
    
    elif query.data == 'mobile_':
        await pw_mobile(app, query.message)

    elif query.data == 'token_':
        await pw_token(app, query.message)
        







  

                
  
    elif query.data == "premium_":
            button = [[
              InlineKeyboardButton(' ʙʀᴏɴᴢᴇ ', callback_data='bronze_'),
              InlineKeyboardButton(' ꜱɪʟᴠᴇʀ ', callback_data='silver_')
            ],[
              InlineKeyboardButton(' ɢᴏʟᴅ ', callback_data='gold_'),
              InlineKeyboardButton(' ᴏᴛʜᴇʀ ', callback_data='other_')
            ],[            
              InlineKeyboardButton(' ʙ ᴀ ᴄ ᴋ ', callback_data='home_')
            ]]
        
            reply_markup = InlineKeyboardMarkup(button)
            await query.message.edit_text(
             text=script.PLANS_TXT,
             reply_markup=reply_markup
            )
            
    
          
    elif query.data == "bronze_":
            button = [[
              InlineKeyboardButton('🔐 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ', callback_data='purchase_')
            ],[
              InlineKeyboardButton('⋞', callback_data='other_'),
              InlineKeyboardButton('ʙ ᴀ ᴄ ᴋ', callback_data='premium_'),
              InlineKeyboardButton('⋟', callback_data='silver_')
            ]]
      
            reply_markup = InlineKeyboardMarkup(button)
            await query.message.edit_text(
             text=script.BRONZE_TXT,
             reply_markup=reply_markup             
            )

    elif query.data == "silver_":
            button = [[
              InlineKeyboardButton('🔐 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ', callback_data='purchase_')
            ],[
              InlineKeyboardButton('⋞', callback_data='bronze_'),
              InlineKeyboardButton('ʙ ᴀ ᴄ ᴋ', callback_data='premium_'),
              InlineKeyboardButton('⋟', callback_data='gold_')
            ]]
      
            reply_markup = InlineKeyboardMarkup(button)
            await query.message.edit_text(
             text=script.SILVER_TXT,
             reply_markup=reply_markup             
            )
            
    elif query.data == "gold_":
            button = [[
              InlineKeyboardButton('🔐 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ', callback_data='purchase_')
            ],[
              InlineKeyboardButton('⋞', callback_data='silver_'),
              InlineKeyboardButton('ʙ ᴀ ᴄ ᴋ', callback_data='premium_'),
              InlineKeyboardButton('⋟', callback_data='other_')
            ]]
      
            reply_markup = InlineKeyboardMarkup(button)
            await query.message.edit_text(
             text=script.GOLD_TXT,
             reply_markup=reply_markup
            )
      
    elif query.data == "other_":
            button = [[
              InlineKeyboardButton('☎️ ᴄᴏɴᴛᴀᴄᴛ ', url="https://t.me/noobhusir")
            ],[
              InlineKeyboardButton('⋞', callback_data='gold_'),
              InlineKeyboardButton('ʙ ᴀ ᴄ ᴋ', callback_data='premium_'),
              InlineKeyboardButton('⋟', callback_data='bronze_')
            ]]
      
            reply_markup = InlineKeyboardMarkup(button)
            await query.message.edit_text(
             text=script.OTHER_TXT,
             reply_markup=reply_markup         
            )

    elif query.data == "purchase_":
            button = [[
                          InlineKeyboardButton('CONTACT ADMIN', url="https://t.me/noobhusir")

                      ],[
                          InlineKeyboardButton('𝐁 𝐀 𝐂 𝐊', callback_data='premium_')
                      ]]
          
            reply_markup = InlineKeyboardMarkup(button)
            await query.message.edit_text(
             text=script.PAYMENT_TXT,
             reply_markup=reply_markup,           
            )

  

  

    elif query.data=="close_data":
        await query.message.delete()
        await query.message.reply_to_message.delete()

def get_alphabet_keyboard():
    """Create a keyboard with A-Z buttons in a modern style"""
    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    keyboard = []
    row = []
    
    for letter in alphabet:
        row.append(InlineKeyboardButton(f"{letter}", callback_data=f"alpha_{letter}"))
        if len(row) == 7:  # 7 buttons per row for better layout
            keyboard.append(row)
            row = []
    
    if row:  # Add any remaining buttons
        keyboard.append(row)
    
    # Add back button
    keyboard.append([InlineKeyboardButton("𝐁 𝐀 𝐂 𝐊", callback_data="home_")])
    
    return InlineKeyboardMarkup(keyboard)

def get_apps_by_letter(letter):
    """Get apps starting with the given letter from appxapis.json"""
    try:
        with open('appxapis.json', 'r') as f:
            apps = json.load(f)
        
        # Filter apps starting with the letter
        filtered_apps = [app for app in apps if app['name'].upper().startswith(letter)]
        
        # Sort alphabetically
        filtered_apps.sort(key=lambda x: x['name'])
        
        return filtered_apps
    except Exception as e:
        print(f"Error reading appxapis.json: {e}")
        return []

def create_app_keyboard(apps, page=0, letter=None):
    """Create a keyboard with app buttons, 40 apps per page"""
    keyboard = []
    row = []
    
    # Calculate pagination
    items_per_page = 40
    total_pages = (len(apps) + items_per_page - 1) // items_per_page
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(apps))
    current_apps = apps[start_idx:end_idx]
    
    # Add app buttons
    for idx, app in enumerate(current_apps):
        name = app['name']
        # Clean up the name and ensure proper spacing
        styled_name = name.replace("api", "").replace("Api", "")  # Remove api/Api from name
        styled_name = ' '.join(word.capitalize() for word in styled_name.split())  # Proper capitalization
        
        # Create button with crown emoji and proper spacing
        button_text = f"💠 {styled_name}"
        button = InlineKeyboardButton(button_text, callback_data=f"app_{name}")
        row.append(button)
        
        # Always use 2 buttons per row
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    # Handle any remaining buttons in the last row
    if row:
        if len(row) == 1:
            row.append(InlineKeyboardButton(" ", callback_data="ignore"))
        keyboard.append(row)
    
    # Add navigation row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("« Prev", callback_data=f"page_{letter}_{page-1}"))
    nav_row.append(InlineKeyboardButton("« 𝐁𝐚𝐜𝐤 »", callback_data="appxlist"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next »", callback_data=f"page_{letter}_{page+1}"))
    keyboard.append(nav_row)
    
    return keyboard, total_pages

@app.on_callback_query(filters.regex("^ignore$"))
async def handle_ignore(client, query):
    await query.answer()
