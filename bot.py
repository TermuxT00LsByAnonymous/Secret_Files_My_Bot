# bot.py  
import logging  
import os  
import sys  
import uuid  
import asyncio  
import html  
  
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup  
# HTML parse mode ka istemaal karenge  
from telegram.constants import ParseMode  
from telegram.ext import (  
    Application,  
    CommandHandler,  
    MessageHandler,  
    CallbackQueryHandler,  
    ContextTypes,  
    filters,  
)  
  
# Configuration aur database functions ko import karein  
from config import BOT_TOKEN, ADMIN_ID, WEBHOOK_URL, WEBHOOK_PORT, STORAGE_CHANNEL_ID  
import database as db  
  
# Ek page par kitni files dikhani hain (admin panel ke liye)  
FILES_PER_PAGE = 5  # <--- YAHAN ZAROORI BADLAV KIYA GAYA HAI  
  
# Logging setup  
logging.basicConfig(  
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO  
)  
logger = logging.getLogger(__name__)  
  
# --- Helper Functions ---  
def is_admin(user_id: int) -> bool:  
    """Check karta hai ki user admin hai ya nahi."""  
    return user_id == ADMIN_ID  
  
async def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:  
    """Bot ka username laata hai."""  
    bot_user = await context.bot.get_me()  
    return bot_user.username  
  
# --- Command Handlers ---  
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  
    """/start command ko handle karta hai."""  
    args = context.args  
    user = update.effective_user  
  
    if args:  
        link_id = args[0]  
        # MongoDB se file data laayein  
        file_data = db.get_file_data(link_id)  
        if file_data:  
            try:  
                await context.bot.copy_message(  
                    chat_id=user.id,  
                    from_chat_id=STORAGE_CHANNEL_ID,  
                    message_id=file_data["permanent_file_id"]  
                )  
            except Exception as e:  
                logger.error(f"Error sending file with link_id {link_id} to {user.id}: {e}")  
                await update.message.reply_text("Sorry, is file ko bhejte samay ek error aa gaya.")  
        else:  
            await update.message.reply_text("Maaf kijiye, ye file nahi mili ya delete kar di gayi hai.")  
    else:  
        await update.message.reply_text(  
            "File Sharing Bot mein aapka swagat hai!\n\n"  
            "File upload karne ke liye, bas mujhe koi document, photo, ya video bhejein.\n"  
            "Apni saari files dekhne ke liye /myfiles command ka istemaal karein."  
        )  
  
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  
    """File uploads (documents, photos, videos) ko handle karta hai."""  
    user = update.effective_user  
    message = update.message  
      
    if not STORAGE_CHANNEL_ID:  
        await update.message.reply_text("Error: Storage channel configure nahi kiya gaya hai.")  
        return  
  
    try:  
        forwarded_message = await message.forward(chat_id=STORAGE_CHANNEL_ID)  
        permanent_file_id = forwarded_message.message_id  
        link_id = str(uuid.uuid4().hex)[:8]  
          
        file_name = "Unknown File"  
        if message.document:  
            file_name = message.document.file_name  
        elif message.video:  
            file_name = message.video.file_name or f"video_{message.video.file_unique_id}.mp4"  
        elif message.photo:  
            file_name = f"photo_{message.photo[-1].file_unique_id}.jpg"  
  
        # File ka record MongoDB mein save karein  
        db.add_file(link_id, user.id, file_name, permanent_file_id)  
  
        bot_username = await get_bot_username(context)  
        share_link = f"https://t.me/{bot_username}?start={link_id}"  
  
        # HTML parse mode ka istemaal karein, jo special characters ke liye zyada surakshit hai  
        await update.message.reply_text(  
            f"File safaltapoorvak upload ho gayi!\n\n"  
            f"File Name: <code>{html.escape(file_name)}</code>\n"  
            f"Shareable Link: <code>{share_link}</code>",  
            parse_mode=ParseMode.HTML  
        )  
    except Exception as e:  
        logger.exception(f"File handle karte samay error aaya (user: {user.id}):")  
        await update.message.reply_text("Aapki file process karte samay ek error aa gaya. Kripya dobara koshish karein.")  
  
async def my_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  
    """User ko uski upload ki gayi files dikhata hai."""  
    user_id = update.effective_user.id  
    user_files = db.get_user_files(user_id)  
  
    if not user_files:  
        await update.message.reply_text("Aapne abhi tak koi file upload nahi ki hai.")  
        return  
  
    bot_username = await get_bot_username(context)  
    message_text = "Yahan aapki upload ki gayi files hain:\n\n"  
    for f in user_files:  
        # MongoDB se link_id field '._id' ke roop mein aayega  
        share_link = f"https://t.me/{bot_username}?start={f['_id']}"  
        message_text += f"📄 <b>{html.escape(f['file_name'])}</b>\n   <a href=\"{share_link}\">Share Link</a>\n\n"  
      
    await update.message.reply_text(message_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)  
  
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  
    """Admin panel dikhata hai."""  
    if not is_admin(update.effective_user.id):  
        await update.message.reply_text("Aap is command ka istemaal nahi kar sakte.")  
        return  
  
    keyboard = [  
        [InlineKeyboardButton("📊 Saari Files Dekhein", callback_data="admin_view_files_0")],  
        [InlineKeyboardButton("🗑️ Ek File Delete Karein", callback_data="admin_delete_start")],  
        [InlineKeyboardButton("🔥 Sabhi Files Clear Karein", callback_data="admin_clear_all_confirm")],  
    ]  
    reply_markup = InlineKeyboardMarkup(keyboard)  
    await update.message.reply_text("Admin Panel:", reply_markup=reply_markup)  
  
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  
    """Sabhi inline button presses ko handle karta hai."""  
    query = update.callback_query  
    await query.answer()  
    data = query.data  
    user_id = query.from_user.id  
  
    if not is_admin(user_id):  
        await query.answer("Ye ek admin function hai.", show_alert=True)  
        return  
  
    if data.startswith("admin_view_files_"):  
        page = int(data.split("_")[-1])  
        all_files = db.get_all_files()  
          
        if not all_files:  
            await query.edit_message_text("Bot mein koi file upload nahi hui hai.")  
            return  
  
        start_index = page * FILES_PER_PAGE  
        end_index = start_index + FILES_PER_PAGE  
        files_on_page = all_files[start_index:end_index]  
  
        message_text = "Sabhi Uploaded Files:\n\n"  
        for f in files_on_page:  
            message_text += (  
                f"👤 User: <code>{f['user_id']}</code>\n"  
                f"📄 File: <code>{html.escape(f['file_name'])}</code>\n"  
                f"🆔 Link ID: <code>{f['_id']}</code>\n\n"  
            )  
  
        keyboard = []  
        row = []  
        if page > 0:  
            row.append(InlineKeyboardButton("⬅️ Pichla", callback_data=f"admin_view_files_{page-1}"))  
        if end_index < len(all_files):  
            row.append(InlineKeyboardButton("Agla ➡️", callback_data=f"admin_view_files_{page+1}"))  
        if row:  
            keyboard.append(row)  
        keyboard.append([InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_back")])  
          
        await query.edit_message_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)  
  
    elif data == "admin_delete_start":  
        all_files = db.get_all_files()  
        if not all_files:  
            await query.edit_message_text("Delete karne ke liye koi file nahi hai.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Wapas", callback_data="admin_back")]]))  
            return  
          
        keyboard = []  
        for f in all_files:  
            button_text = f"📄 {f['file_name'][:20]} (by {f['user_id']})"  
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_delete_confirm_{f['_id']}")])  
        keyboard.append([InlineKeyboardButton("⬅️ Wapas", callback_data="admin_back")])  
        await query.edit_message_text("Delete karne ke liye file chunein:", reply_markup=InlineKeyboardMarkup(keyboard))  
  
    elif data.startswith("admin_delete_confirm_"):  
        link_id = data.replace("admin_delete_confirm_", "")  
        keyboard = [  
            [InlineKeyboardButton("✅ Haan, Delete Karein", callback_data=f"admin_delete_execute_{link_id}")],  
            [InlineKeyboardButton("❌ Nahi, Cancel Karein", callback_data="admin_delete_start")]  
        ]  
        await query.edit_message_text(f"Kya aap sach mein Link ID <code>{link_id}</code> ko delete karna chahte hain?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)  
  
    elif data.startswith("admin_delete_execute_"):  
        link_id = data.replace("admin_delete_execute_", "")  
        db.delete_file(link_id)  
        await query.edit_message_text(f"Link ID <code>{link_id}</code> ka record delete kar diya gaya hai.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Delete Menu", callback_data="admin_delete_start")]]), parse_mode=ParseMode.HTML)  
  
    elif data == "admin_clear_all_confirm":  
        keyboard = [  
            [InlineKeyboardButton("🔥 HAAN, SAB KUCH DELETE KAREIN", callback_data="admin_clear_all_execute")],  
            [InlineKeyboardButton("❌ Cancel", callback_data="admin_back")]  
        ]  
        await query.edit_message_text(  
            "<b>⚠️ DANGER ZONE ⚠️</b>\n\nKya aap sach mein database se saare file records delete karna chahte hain? Ye action undo nahi kiya ja sakta.",  
            reply_markup=InlineKeyboardMarkup(keyboard),  
            parse_mode=ParseMode.HTML  
        )  
  
    elif data == "admin_clear_all_execute":  
        db.clear_all_files()  
        await query.edit_message_text("Saare file records database se clear kar diye gaye hain.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_back")]]))  
  
    elif data == "admin_back":  
        keyboard = [  
            [InlineKeyboardButton("📊 Saari Files Dekhein", callback_data="admin_view_files_0")],  
            [InlineKeyboardButton("🗑️ Ek File Delete Karein", callback_data="admin_delete_start")],  
            [InlineKeyboardButton("🔥 Sabhi Files Clear Karein", callback_data="admin_clear_all_confirm")],  
        ]  
        await query.edit_message_text("Admin Panel:", reply_markup=InlineKeyboardMarkup(keyboard))  
  
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:  
    """Errors ko log karta hai."""  
    logger.warning('Update "%s" caused error "%s"', update, context.error)  
  
def main() -> None:  
    """Bot ko webhooks ke saath start karta hai (Render/Production ke liye)."""  
    if not BOT_TOKEN:  
        logger.error("FATAL: BOT_TOKEN config mein set nahi hai.")  
        sys.exit(1)  
    if not ADMIN_ID:  
        logger.error("FATAL: ADMIN_ID config mein set nahi hai.")  
        sys.exit(1)  
    if not STORAGE_CHANNEL_ID:  
        logger.error("FATAL: STORAGE_CHANNEL_ID config mein set nahi hai.")  
        sys.exit(1)  
    if not WEBHOOK_URL:  
        logger.error("FATAL: WEBHOOK_URL environment variable set nahi hai. Bot start nahi ho sakta.")  
        sys.exit(1)  
  
    application = Application.builder().token(BOT_TOKEN).build()  
  
    application.add_handler(CommandHandler("start", start))  
    application.add_handler(CommandHandler("myfiles", my_files))  
    application.add_handler(CommandHandler("admin", admin))  
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_file))  
    application.add_handler(CallbackQueryHandler(button_callback_handler))  
    application.add_error_handler(error_handler)  
  
    logger.info(f"Webhook ko port {WEBHOOK_PORT} par start kar raha hai")  
    application.run_webhook(  
        listen="0.0.0.0",  
        port=WEBHOOK_PORT,  
        url_path=BOT_TOKEN, # Security measure  
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"  
    )  
  
if __name__ == "__main__":  
    main()  