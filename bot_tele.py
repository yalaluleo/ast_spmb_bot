"""
© 2025 Tiara Chantika. All rights reserved.
This script is not licensed for reuse or distribution without permission.
Enhanced for SPMB Banten 2026: MySQL, Admin Claim (Ambil Tugas), and Transparency.
"""
import sys
import os

# CEK VERSI PYTHON
print(f"🐍 Python version: {sys.version}")
if sys.version_info >= (3, 13):
    print("⚠️  WARNING: Python 3.13+ may have compatibility issues")
    print("⚠️  Recommended: Use Python 3.11 or 3.12")

import asyncio
import logging
from datetime import datetime
import mysql.connector
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ========== SETUP LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== KONFIGURASI ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_LINK = os.getenv("GROUP_LINK", 'https://t.me/+LR28DxO9IJU2Y2Vl')

# CEK ENVIRONMENT VARIABLE PENTING
required_vars = ["BOT_TOKEN", "MYSQLHOST", "MYSQLUSER", "MYSQLPASSWORD", "MYSQLDATABASE", "CHANNEL_ID"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# Konversi CHANNEL_ID ke integer
try:
    CHANNEL_ID = int(CHANNEL_ID)
except (ValueError, TypeError):
    logger.error(f"CHANNEL_ID must be an integer, got: {CHANNEL_ID}")
    sys.exit(1)

# ========== DATABASE FUNCTIONS ==========
def get_db():
    """Buat koneksi database baru"""
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQLHOST"),        
            user=os.getenv("MYSQLUSER"),        
            password=os.getenv("MYSQLPASSWORD"),
            database=os.getenv("MYSQLDATABASE"),
            port=int(os.getenv("MYSQLPORT") or 3306),
            connect_timeout=10
        )
        logger.info("Database connected successfully")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

# Global dictionaries
user_data = {}
message_to_user = {}
admin_replies = {}
pending_albums = {}

def save_to_mysql(user_id, username, full_name, msg_id, file_id=None):
    """Simpan data ke MySQL"""
    db = None
    try:
        db = get_db()
        if not db:
            logger.error("Failed to get database connection")
            return False
            
        cursor = db.cursor()
        sql = """INSERT INTO submissions (user_id, username, full_name, admin_msg_id, file_id, status, created_at) 
                 VALUES (%s, %s, %s, %s, %s, 'pending', NOW())"""
        cursor.execute(sql, (str(user_id), username or '', full_name or '', str(msg_id), file_id))
        db.commit()
        logger.info(f"Data saved to MySQL for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"MySQL Insert Error: {e}")
        return False
    finally:
        if db:
            db.close()

def update_admin_status(msg_id, status, admin_name):
    """Update status di database"""
    db = None
    try:
        db = get_db()
        if not db:
            return False
            
        cursor = db.cursor()
        sql = "UPDATE submissions SET status = %s, admin_handler = %s, updated_at = NOW() WHERE admin_msg_id = %s"
        cursor.execute(sql, (status, admin_name, str(msg_id)))
        db.commit()
        logger.info(f"Updated status for msg {msg_id} to {status} by {admin_name}")
        return True
    except Exception as e:
        logger.error(f"MySQL Update Error: {e}")
        return False
    finally:
        if db:
            db.close()

def get_admin_keyboard(user_id, status="pending"):
    if status == "pending":
        return InlineKeyboardMarkup([[InlineKeyboardButton("Ambil Tugas", callback_data=f"claim_{user_id}")]])
    elif status == "processing":
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Lengkap", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("Belum Lengkap", callback_data=f"reject_{user_id}"),
                InlineKeyboardButton("Reply", callback_data=f"reply_{user_id}")
            ]
        ])
    return None

def save_mapping(user_id, chat_id, group_msg_id):
    user_data[user_id] = {
        "chat_id": chat_id,
        "group_msg_id": group_msg_id,
        "status": "pending"
    }
    message_to_user[group_msg_id] = user_id

# ========== HANDLER FUNCTIONS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        await update.message.reply_text(
            f"Hai ASTers! {user.full_name} 👋\n\n"
            "Selamat datang di AST | SPMB Banten 2026\n\n"
            "Silakan kirim bukti persyaratan kamu di sini untuk dapat join di Grup Telegram kami, yang berupa:\n"
            "✅ Screenshot follow Instagram @anaksmatangerang\n"
            "✅ Screenshot repost postingan ke Instagram Story\n"
            "✅ Screenshot komentar yang berisi mention 5 teman di postingan alur join grup Telegram SPMB Banten 2026\n\n"
            "Link postingan: https://www.instagram.com/p/DYEK3nyCWcz/?igsh=MXZ6dXVwb295MndodQ==\n\n"
            "Kirimkan bukti dalam bentuk foto (maksimal 10 foto) atau PDF di chat ini. Terima kasih 😊"
        )
    except Exception as e:
        logger.error(f"Error in start: {e}")

async def handle_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    if not msg:
        return

    if msg.photo or msg.document:
        admin_msg = (
            f"Peserta Baru\n"
            f"User ID: {user.id}\n"
            f"Display name: {user.full_name}\n"
            f"Username: @{user.username if user.username else 'N/A'}\n\n"
            f"Pesan: {msg.text or msg.caption or '(tanpa teks)'}\n"
            f"Status: Menunggu Admin"
        )

        keyboard = get_admin_keyboard(user.id, "pending")

        try:
            if msg.media_group_id:
                # Handle album
                if msg.media_group_id not in pending_albums:
                    pending_albums[msg.media_group_id] = {
                        "messages": [],
                        "user_id": user.id,
                        "chat_id": msg.chat_id,
                        "username": user.username,
                        "full_name": user.full_name,
                        "admin_msg": admin_msg,
                        "keyboard": keyboard,
                    }
                
                pending_albums[msg.media_group_id]["messages"].append(msg)
                
                if len(pending_albums[msg.media_group_id]["messages"]) == 1:
                    asyncio.create_task(process_album_after_delay(context, msg.media_group_id))
                return
                
            elif msg.photo:
                file_id = msg.photo[-1].file_id
                sent = await context.bot.send_photo(
                    CHANNEL_ID,
                    photo=file_id,
                    caption=admin_msg,
                    reply_markup=keyboard
                )
                save_mapping(user.id, msg.chat_id, sent.message_id)
                save_to_mysql(user.id, user.username, user.full_name, sent.message_id, file_id)
                await msg.reply_text("Bukti kamu sudah kami terima. Tunggu verifikasi dari admin ya!")
                
            elif msg.document:
                file_id = msg.document.file_id
                sent = await context.bot.send_document(
                    CHANNEL_ID,
                    document=file_id,
                    caption=admin_msg,
                    reply_markup=keyboard
                )
                save_mapping(user.id, msg.chat_id, sent.message_id)
                save_to_mysql(user.id, user.username, user.full_name, sent.message_id, file_id)
                await msg.reply_text("Bukti kamu sudah kami terima. Tunggu verifikasi dari admin ya!")

        except Exception as e:
            logger.error(f"Error in handle_submission: {e}")
            await msg.reply_text("Maaf, terjadi error. Silakan kirim ulang.")
    
    else:
        # KALAU USER KIRIM TEKS BIASA
        admin_msg_text = (
            f"Pesan dari User\n"
            f"User ID: {user.id}\n"
            f"Nama: {user.full_name}\n"
            f"Username: @{user.username if user.username else 'N/A'}\n\n"
            f"Pesan: {msg.text}\n"
            f"Status: Menunggu Balasan Admin"
        )
        
        keyboard = get_admin_keyboard(user.id, "pending")
        
        sent = await context.bot.send_message(
            CHANNEL_ID,
            text=admin_msg_text,
            reply_markup=keyboard
        )
        
        save_mapping(user.id, msg.chat_id, sent.message_id)
        save_to_mysql(user.id, user.username, user.full_name, sent.message_id, None)
        
        await msg.reply_text("Pesan kamu sudah kami terima. Tunggu balasan dari admin ya!")
        return

async def process_album_after_delay(context, album_id):
    await asyncio.sleep(2)
    await process_album(context, album_id)

async def process_album(context, album_id):
    if album_id not in pending_albums:
        return
    
    album_data = pending_albums.pop(album_id)
    media_list = sorted(album_data["messages"], key=lambda m: m.message_id)
    
    try:
        media_group = []
        for i, m in enumerate(media_list[:10]):
            caption_text = album_data["admin_msg"] if i == 0 else ""
            media_group.append(
                InputMediaPhoto(media=m.photo[-1].file_id, caption=caption_text)
            )
        
        await context.bot.send_media_group(CHANNEL_ID, media=media_group)
        
        sent_msg = await context.bot.send_message(
            CHANNEL_ID,
            text=f"Album dari user {album_data['user_id']}\nTotal {len(media_list)} foto\n\nStatus: Menunggu Admin",
            reply_markup=album_data["keyboard"]
        )
        
        save_mapping(album_data["user_id"], album_data["chat_id"], sent_msg.message_id)
        save_to_mysql(album_data["user_id"], album_data["username"], album_data["full_name"], sent_msg.message_id, None)
        
        await context.bot.send_message(
            album_data["chat_id"],
            "Bukti kamu sudah kami terima. Tunggu verifikasi dari admin ya!"
        )
        
    except Exception as e:
        logger.error(f"Error processing album {album_id}: {e}")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHANNEL_ID:
        return

    msg = update.message
    if not msg.reply_to_message:
        return

    replied_id = msg.reply_to_message.message_id
    user_id = message_to_user.get(replied_id)
    
    if not user_id:
        try:
            db = get_db()
            if db:
                cursor = db.cursor()
                cursor.execute("SELECT user_id FROM submissions WHERE admin_msg_id = %s", (str(replied_id),))
                result = cursor.fetchone()
                if result:
                    user_id = int(result[0])
                db.close()
        except Exception as e:
            logger.error(f"DB Search Error: {e}")

    if not user_id:
        return

    reply_content = msg.text or msg.caption or "(pesan media)"
    reply_text = f"📩 Balasan dari Admin:\n\n{reply_content}\n\nUntuk membalas, kirim pesan baru ke bot di chat ini."

    try:
        if msg.photo:
            await context.bot.send_photo(user_id, photo=msg.photo[-1].file_id, caption=reply_text)
        elif msg.document:
            await context.bot.send_document(user_id, document=msg.document.file_id, caption=reply_text)
        else:
            await context.bot.send_message(user_id, reply_text)
    except Exception as e:
        logger.error(f"Gagal mengirim balasan: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_name = query.from_user.full_name
    await query.answer()
    
    data = query.data.split('_')
    if len(data) != 2:
        return

    action, user_id_str = data[0], data[1]
    user_id = int(user_id_str)
    
    if user_id not in user_data:
        user_data[user_id] = {"chat_id": user_id, "status": "pending"}
    
    user_info = user_data.get(user_id)
    msg_id = query.message.message_id
    message_to_user[msg_id] = user_id

    try:
        if action == "claim":
            update_admin_status(msg_id, "processing", admin_name)
            new_keyboard = get_admin_keyboard(user_id, "processing")
            
            if query.message.caption is not None:
                current_caption = query.message.caption
                new_caption = current_caption.replace("Status: Menunggu Admin", f"Status: Sedang dicek oleh {admin_name}")
                await query.edit_message_caption(caption=new_caption, reply_markup=new_keyboard)
            else:
                current_text = query.message.text
                new_text = current_text.replace("Status: Menunggu Admin", f"Status: Sedang dicek oleh {admin_name}")
                await query.edit_message_text(text=new_text, reply_markup=new_keyboard)
            
        elif action == "approve":
            update_admin_status(msg_id, "approved", admin_name)
            if user_info:
                user_info["status"] = "approved"
                await context.bot.send_message(
                    user_info["chat_id"],
                    f"Terima kasih ASTers! Persyaratan kamu sudah lengkap.\n\n"
                    f"Silakan klik link berikut untuk bergabung ke Grup Info SPMB Banten 2026:\n"
                    f"{GROUP_LINK}\n\nSampai jumpa di grup!"
                )

            if query.message.caption is not None:
                current = query.message.caption
                current = '\n'.join([line for line in current.split('\n') if not line.startswith("Pesan:") and not line.startswith("Status:")])
                new_caption = f"STATUS: LENGKAP\nDicek oleh: {admin_name}\n\n{current}"
                await query.edit_message_caption(caption=new_caption, reply_markup=None)
            else:
                current = query.message.text
                current = '\n'.join([line for line in current.split('\n') if not line.startswith("Pesan:") and not line.startswith("Status:")])
                new_text = f"STATUS: LENGKAP\nDicek oleh: {admin_name}\n\n{current}"
                await query.edit_message_text(text=new_text, reply_markup=None)

        elif action == "reject":
            update_admin_status(msg_id, "rejected", admin_name)
            if user_info:
                user_info["status"] = "rejected"
                await context.bot.send_message(
                    user_info["chat_id"],
                    "Oops! Sepertinya persyaratan kamu belum lengkap.\n\n"
                    "Mohon pastikan kamu telah mengirim persyaratan dalam bentuk foto atau PDF, yang berupa:\n\n"
                    "✅ Screenshot follow Instagram @anaksmatangerang\n"
                    "✅ Screenshot repost postingan ke Instagram Story\n"
                    "✅ Screenshot komentar yang berisi mention 5 teman di postingan alur join grup Telegram SPMB Banten 2026 (lihat di postingan yang dipin paling atas)\n\n"
                    "Silakan kirim ulang bukti kamu jika ada yang terlewat ya. Terima kasih 😊"
                )

            if query.message.caption is not None:
                current = query.message.caption
                current = '\n'.join([line for line in current.split('\n') if not line.startswith("Pesan:") and not line.startswith("Status:")])
                new_caption = f"STATUS: BELUM LENGKAP\nDicek oleh: {admin_name}\n\n{current}"
                await query.edit_message_caption(caption=new_caption, reply_markup=None)
            else:
                current = query.message.text
                current = '\n'.join([line for line in current.split('\n') if not line.startswith("Pesan:") and not line.startswith("Status:")])
                new_text = f"STATUS: BELUM LENGKAP\nDicek oleh: {admin_name}\n\n{current}"
                await query.edit_message_text(text=new_text, reply_markup=None)

        elif action == "reply":
            await query.message.reply_text(
                f"Silakan reply pesannya user {user_id}",
                reply_to_message_id=query.message.message_id
            )

    except Exception as e:
        logger.error(f"Error in handle_callback: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}", exc_info=True)

# ========== MAIN ==========
def main():
    logger.info("Starting bot...")
    
    # Test database connection
    db = get_db()
    if not db:
        logger.error("Database connection failed! Please check your MySQL configuration.")
        sys.exit(1)
    db.close()
    logger.info("Database connection successful")
    
    # Build and run bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.PHOTO | filters.Document.ALL | filters.TEXT) & (~filters.COMMAND),
        handle_submission
    ))
    app.add_handler(MessageHandler(
        filters.Chat(CHANNEL_ID) & filters.REPLY,
        handle_admin_reply
    ))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)

if __name__ == "__main__":
    main()