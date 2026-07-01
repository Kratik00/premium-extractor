import re
import json
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pyrogram import filters
from Extractor import app
from config import OWNER_ID
from Extractor.core import script
from Extractor.core.mongo.plans_db import *
from Extractor.core.func import subscribe, chk_user
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
from Extractor.modules.qualityfree import *        
from Extractor.modules.freecp import *
from Extractor.modules.cdsjourney import *
from Extractor.modules.cdsjourneyfree import *
from Extractor.modules.selectionwayfree import *
from Extractor.modules.topperswisdomfree import *
from Extractor.modules.freepw import *
from Extractor.modules.civilgurujifree import *
from Extractor.modules.addafree import *
from Extractor.modules.htmlconverter import *
from Extractor.modules.knowledgesankul import *
from Extractor.modules.db import *
from Extractor.modules.apnacollege import *
from Extractor.modules.apnacollegefree import *
from Extractor.modules.iqfree import *
from Extractor.modules.pinnaclefree import *
from Extractor.modules.appx_combined import *

from Extractor.core.mongo import plans_db
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import config

THREADPOOL = ThreadPoolExecutor(max_workers=2000)
TIMEOUT = 300  # 5 minutes timeout

buttons = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📇 Login / Without Login", callback_data="modes_")
    ],
    [
        InlineKeyboardButton("🔍 Find API", callback_data="findapi_")
    ],
    [
        InlineKeyboardButton("📝 TXT ➜ HTML", callback_data="htmlconvert")
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
                  InlineKeyboardButton("🧩Physics Wallah", callback_data="pwwp")
                ],[
                  InlineKeyboardButton("🎯Classplus", callback_data="cpwp")
                ],[
                    InlineKeyboardButton("🪄 SelectionWay", callback_data="selectionway_"),
                    InlineKeyboardButton("🪄 Knowledge Sankul", callback_data="ingenium_")
                ],[
                    InlineKeyboardButton("🤖 CDS JOURNEY", callback_data="cdsjourney_"),
                    InlineKeyboardButton("🤖 CIVILGURUJI", callback_data="civilguruji_")
                ],[
                    InlineKeyboardButton("🚀 PINNACLE ", callback_data="pinnacle"),
                    InlineKeyboardButton("🚀 TopppersWisdom", callback_data="topperswisdom_")
                ],[
                  InlineKeyboardButton("🌸 ADDA 247", callback_data="adda247_"),
                  InlineKeyboardButton("♕ STUDY IQ", callback_data="studyiq_")
                ],[
                  InlineKeyboardButton("👑 PREMIUM", callback_data="premium_")
                ],[
                  InlineKeyboardButton("🌪️Back", callback_data="modes_")
                ]]

button1 = [              
                [
                    InlineKeyboardButton(" 🕹️APPX", callback_data="masterappx_"),
                    InlineKeyboardButton(" 🕹️APPX OTP", callback_data="appxotp_")
                ],
                [
                    InlineKeyboardButton(" 🕹️CLASSPLUS", callback_data="classplus_"),
                    InlineKeyboardButton(" 🕹️UTKARSH", callback_data="utkarsh_")
                ],
                [
                    InlineKeyboardButton(" 🕹️CDS JOURNEY", callback_data="cds"),   
                    InlineKeyboardButton(" 🕹️PHYSICS WALLAH", callback_data="pw_")    
                ],
                [
                    InlineKeyboardButton("👑 APNA COLLEGE", callback_data="apna_handler"),
                    InlineKeyboardButton("👑 Kᴅ Cᴀᴍᴘᴜs", callback_data="kdlive_")         
                ],
                [
                    InlineKeyboardButton("🌪️Back", callback_data="modes_"),
                ]
                ]




back_button  = [[
                    InlineKeyboardButton("🤍BACK", callback_data="modes_"),                    
                ]]

              
@app.on_message(filters.command("start"))
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

@app.on_callback_query(filters.regex("^cds$"))
async def cds_callback(app: Client, callback_query: CallbackQuery):
    try:
        await callback_query.answer()

        msg = await callback_query.message.reply_text("🔄 Starting CDS extractor...")

        # call your main function
        await cds_handler(app, callback_query.message)

        await msg.delete()

    except Exception as e:
        await callback_query.message.reply_text(f"❌ Error: {str(e)}")


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
@app.on_callback_query(filters.regex("^topperswisdom_$"))
async def topperswisdom_callback(client, callback_query):
    try:
        # Send processing message
        processing_msg = await callback_query.message.reply_text(
            "⚙️ <b>Handling ToppersWisdom Extractor...</b>\n\nPlease wait a few seconds 💫"
        )

        user_id = callback_query.from_user.id

        try:
            # Run the SelectionWay extractor process with timeout
            result = await process_with_timeout(process_topperswisdom, client, callback_query.message, user_id)

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
        print(f"Error in topperswisdom_callback: {e}")
        await callback_query.answer("⚠️ An error occurred while handling SelectionWay.", show_alert=True)

@app.on_message(filters.command("html"))
async def html_cmd(client, message):
    await message.reply_text("📄 Send the TXT file you want to convert.")

@app.on_message(filters.command("cleanpremium") & filters.user(OWNER_ID))
async def clean(_, msg):
    await clean_expired_premium()
    await msg.reply("✅ Expired premium deleted")

@app.on_message(filters.command("dumpdb") & filters.user(OWNER_ID))
async def dump_db_handler(client, message):
    try:
        await message.reply_text("📦 Dumping database... Please wait")

        filename = "db_dump.json"
        await dump_database_to_json(filename)

        await message.reply_document(filename)

        os.remove(filename)

    except Exception as e:
        await message.reply_text(f"❌ Error:\n<code>{str(e)}</code>")
        

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

html_waiting = set()   # to track which users clicked htmlconvert


@app.on_callback_query(filters.regex("^htmlconvert$"))
async def html_button(client, cq):
    uid = cq.from_user.id

    # mark user as waiting for txt
    html_waiting.add(uid)

    await cq.message.reply_text(
        "📄 <b>Send your TXT file now, I will convert it into HTML</b>",
    )


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
    
    elif query.data=="masterappx_":
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
    else:
        query.continue_propagation()


@app.on_callback_query(filters.regex("^ignore$"))
async def handle_ignore(client, query):
    await query.answer()
