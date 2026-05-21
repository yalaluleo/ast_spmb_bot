"""
© 2025 Tiara Chantika. All rights reserved.
This script is not licensed for reuse or distribution without permission.
Enhanced for SPMB Banten 2026: MySQL, Admin Claim (Ambil Tugas), and Transparency.
"""
import os
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
import asyncio
from datetime import datetime
import logging
import time

def get_db():
    try:
        ssl_ca_path = "ca.pem"
        if not os.path.exists(ssl_ca_path):
            ssl_ca_path = "/etc/ssl/certs/ca-certificates.crt"
        
        conn = mysql.connector.connect(
            host=os.getenv("MYSQLHOST"),        
            user=os.getenv("MYSQLUSER"),        
            password=os.getenv("MYSQLPASSWORD"),
            database=os.getenv("MYSQLDATABASE"),
            port=int(os.getenv("MYSQLPORT") or 3306), 
            ssl_disabled=False,
            ssl_ca=ssl_ca_path
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

# ========== KONFIGURASI ==========
BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHANNEL_ID = -1002605314830
GROUP_LINK = 'https://t.me/+LR28DxO9IJU2Y2Vl'

# ========== SETUP LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== DATABASE ==========
user_data = {}
message_to_user = {}
admin_replies = {}
pending_albums = {}

def save_to_mysql(user_id, username, full_name, msg_id, file_id=None):
    try:
        db = get_db()
        cursor = db.cursor()
        sql = "INSERT INTO submissions (user_id, username, full_name, admin_msg_id, file_id) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (user_id, username, full_name, msg_id, file_id))
        db.commit()
        db.close()
        logger.info(f"Data saved to MySQL for user {user_id}")
    except Exception as e:
        logger.error(f"MySQL Insert Error: {e}")

def update_admin_status(msg_id, status, admin_name):
    try:
        db = get_db()
        cursor = db.cursor()
        sql = "UPDATE submissions SET status = %s, admin_handler = %s WHERE admin_msg_id = %s"
        cursor.execute(sql, (status, admin_name, msg_id))
        db.commit()
        db.close()
        logger.info(f"Updated status for msg {msg_id} to {status} by {admin_name}")
    except Exception as e:
        logger.error(f"MySQL Update Error: {e}")

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

        #example_message = (
        #    "Silakan cek panduan lengkap mengenai persyaratan di bawah ini:\n"
        #    "https://www.instagram.com/s/aGlnaGxpZ2h0OjE3OTM1MTE5MTIwMDE2Mjg0?story_media_id=3642957998978679121_2999424744&igsh=MXU5dzBpM20ybGo3Zw=="
        #)

        #await update.message.reply_text(example_message)

    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan. Silakan coba lagi.")

async def handle_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    if not msg:
        return

    if msg.text and not msg.photo and not msg.document:
        pass
    elif not (msg.photo or msg.document):
        return

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
        # CEK APAKAH INI ALBUM (kirim banyak foto sekaligus)
        if msg.media_group_id:
            logger.info(f"Album detected: {msg.media_group_id}")
            
            if msg.media_group_id not in pending_albums:
                pending_albums[msg.media_group_id] = {
                    "messages": [],
                    "user_id": user.id,
                    "chat_id": msg.chat_id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "admin_msg": admin_msg,
                    "keyboard": keyboard,
                    "reply_sent": False
                }
            
            pending_albums[msg.media_group_id]["messages"].append(msg)
            logger.info(f"Album {msg.media_group_id} now has {len(pending_albums[msg.media_group_id]['messages'])} photos")
            
            # Tunggu 2 detik lalu proses album
            if len(pending_albums[msg.media_group_id]["messages"]) == 1:
                asyncio.create_task(process_album_after_delay(context, msg.media_group_id))
            return
            
        elif msg.photo:
            # Foto biasa (bukan album)
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
            
        elif msg.text:
            sent = await context.bot.send_message(
                CHANNEL_ID,
                text=admin_msg,
                reply_markup=keyboard
            )
            save_mapping(user.id, msg.chat_id, sent.message_id)
            save_to_mysql(user.id, user.username, user.full_name, sent.message_id, None)
            await msg.reply_text("Pesan kamu sudah kami terima. Tunggu balasan dari admin ya!")

    except Exception as e:
        logger.error(f"Error in handle_submission: {e}")
        await msg.reply_text("Maaf, terjadi error. Silakan kirim ulang.")

async def process_album_after_delay(context, album_id):
    """Tunggu 2 detik agar semua foto terkumpul, lalu proses album"""
    await asyncio.sleep(2)
    await process_album(context, album_id)

async def process_album(context, album_id):
    """Proses album: kirim semua foto sebagai 1 album, kirim pesan tombol terpisah"""
    if album_id not in pending_albums:
        return
    
    album_data = pending_albums.pop(album_id)
    media_list = sorted(album_data["messages"], key=lambda m: m.message_id)
    
    logger.info(f"Processing album {album_id} with {len(media_list)} photos")
    
    try:
        # Buat album dari semua foto
        media_group = []
        for i, m in enumerate(media_list[:10]):
            # Hanya foto pertama yang punya caption
            caption_text = album_data["admin_msg"] if i == 0 else ""
            media_group.append(
                InputMediaPhoto(media=m.photo[-1].file_id, caption=caption_text)
            )
        
        # Kirim semua foto sebagai 1 ALBUM
        await context.bot.send_media_group(CHANNEL_ID, media=media_group)
        logger.info(f"Album {album_id} sent with {len(media_group)} photos")
        
        # Kirim pesan tombol TERPISAH (bukan bagian dari album)
        sent_msg = await context.bot.send_message(
            CHANNEL_ID,
            text=f"Album dari user {album_data['user_id']}\nTotal {len(media_list)} foto\n\nStatus: Menunggu Admin",
            reply_markup=album_data["keyboard"]
        )
        
        # Simpan mapping
        save_mapping(album_data["user_id"], album_data["chat_id"], sent_msg.message_id)
        save_to_mysql(album_data["user_id"], album_data["username"], album_data["full_name"], sent_msg.message_id, None)
        
        # Kirim balasan ke user HANYA SEKALI (tidak per foto)
        await context.bot.send_message(
            album_data["chat_id"],
            "Bukti kamu sudah kami terima. Tunggu verifikasi dari admin ya!"
        )
        logger.info(f"Reply sent to user {album_data['user_id']} for album {album_id}")
        
    except Exception as e:
        logger.error(f"Error processing album {album_id}: {e}")

def save_mapping(user_id, chat_id, group_msg_id):
    user_data[user_id] = {
        "chat_id": chat_id,
        "group_msg_id": group_msg_id,
        "status": "pending"
    }
    message_to_user[group_msg_id] = user_id

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
            cursor = db.cursor()
            cursor.execute("SELECT user_id FROM submissions WHERE admin_msg_id = %s", (replied_id,))
            result = cursor.fetchone()
            if result:
                user_id = result[0]
            db.close()
        except Exception as e:
            logger.error(f"DB Search Error: {e}")

    if not user_id:
        if replied_id in admin_replies:
            user_id = message_to_user.get(admin_replies[replied_id])

    if not user_id:
        return

    target_chat_id = user_id 
    reply_content = msg.text or msg.caption or "(pesan media)"
    reply_text = (
        f"📩 Balasan dari Admin:\n\n"
        f"{reply_content}\n\n"
        f"Untuk membalas, kirim pesan baru ke bot di chat ini."
    )

    try:
        if msg.photo:
            await context.bot.send_photo(target_chat_id, photo=msg.photo[-1].file_id, caption=reply_text)
        elif msg.document:
            await context.bot.send_document(target_chat_id, document=msg.document.file_id, caption=reply_text)
        else:
            await context.bot.send_message(target_chat_id, reply_text)

        admin_replies[msg.message_id] = replied_id
        
    except Exception as e:
        logger.error(f"Gagal mengirim balasan: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_name = query.from_user.full_name
    await query.answer()
    
    logger.info(f"Callback received: {query.data}")
    
    data = query.data.split('_')
    if len(data) != 2:
        logger.warning(f"Invalid callback data: {query.data}")
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
            logger.info(f"Admin {admin_name} claiming task for user {user_id}")
            update_admin_status(msg_id, "processing", admin_name)
            
            new_keyboard = get_admin_keyboard(user_id, "processing")
            
            # Cek jenis pesan
            if query.message.caption is not None:
                current_caption = query.message.caption
                new_caption = current_caption.replace("Status: Menunggu Admin", f"Status: Sedang dicek oleh {admin_name}")
                await query.edit_message_caption(
                    caption=new_caption,
                    reply_markup=new_keyboard
                )
            else:
                current_text = query.message.text
                new_text = current_text.replace("Status: Menunggu Admin", f"Status: Sedang dicek oleh {admin_name}")
                await query.edit_message_text(
                    text=new_text,
                    reply_markup=new_keyboard
                )
            
        elif action == "approve":
            logger.info(f"Admin {admin_name} approving user {user_id}")
            update_admin_status(msg_id, "approved", admin_name)
            if user_info:
                user_info["status"] = "approved"
                await context.bot.send_message(
                    user_info["chat_id"],
                    f"Terima kasih ASTers! Persyaratan kamu sudah lengkap.\n\n"
                    "Silakan klik link berikut untuk bergabung ke Grup Info SPMB Banten 2026:\n"
                    f"{GROUP_LINK}\n\n"
                    "Sampai jumpa di grup!"
                )

            if query.message.caption is not None:
                current = query.message.caption
                current = '\n'.join([line for line in current.split('\n') if not line.startswith("Pesan:") and not line.startswith("Status:")])
                new_caption = f"STATUS: LENGKAP\nDicek oleh: {admin_name}\n\n{current}"
                await query.edit_message_caption(
                    caption=new_caption,
                    reply_markup=None
                )
            else:
                current = query.message.text
                current = '\n'.join([line for line in current.split('\n') if not line.startswith("Pesan:") and not line.startswith("Status:")])
                new_text = f"STATUS: LENGKAP\nDicek oleh: {admin_name}\n\n{current}"
                await query.edit_message_text(
                    text=new_text,
                    reply_markup=None
                )
            logger.info(f"Successfully approved user {user_id}")

        elif action == "reject":
            logger.info(f"Admin {admin_name} rejecting user {user_id}")
            update_admin_status(msg_id, "rejected", admin_name)
            if user_info:
                user_info["status"] = "rejected"
                await context.bot.send_message(
                    user_info["chat_id"],
                    "Oops! Sepertinya persyaratan kamu belum lengkap.\n\n"
                    "Mohon pastikan kamu telah mengirim persyaratan dalam bentuk foto atau PDF, yang berupa:\n"
                    "✅ Screenshot follow Instagram @anaksmatangerang\n"
                    "✅ Screenshot repost postingan ke Instagram Story\n"
                    "✅ Screenshot komentar yang berisi mention 5 teman di postingan alur join grup Telegram SPMB Banten 2026\n\n"
                    "Link postingan: https://www.instagram.com/p/DYEK3nyCWcz/?igsh=MXZ6dXVwb295MndodQ==\n\n"
                    "Silakan kirim ulang bukti kamu jika ada yang terlewat ya. Terima kasih 😊"
                )

            if query.message.caption is not None:
                current = query.message.caption
                current = '\n'.join([line for line in current.split('\n') if not line.startswith("Pesan:") and not line.startswith("Status:")])
                new_caption = f"STATUS: BELUM LENGKAP\nDicek oleh: {admin_name}\n\n{current}"
                await query.edit_message_caption(
                    caption=new_caption,
                    reply_markup=None
                )
            else:
                current = query.message.text
                current = '\n'.join([line for line in current.split('\n') if not line.startswith("Pesan:") and not line.startswith("Status:")])
                new_text = f"STATUS: BELUM LENGKAP\nDicek oleh: {admin_name}\n\n{current}"
                await query.edit_message_text(
                    text=new_text,
                    reply_markup=None
                )
            logger.info(f"Successfully rejected user {user_id}")

        elif action == "reply":
            await query.message.reply_text(
                f"Silakan reply pesannya user {user_id}",
                reply_to_message_id=query.message.message_id
            )

    except Exception as e:
        logger.error(f"Error in handle_callback: {e}")
        try:
            await query.message.reply_text(f"Error: {str(e)}")
        except:
            pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    logger.error(f"Error: {error}", exc_info=True)

def main():
    # Langsung panggil os.getenv di sini agar terbaca sempurna oleh Railway
    token_bot = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token_bot).build()

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

    logger.info("Bot Berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)