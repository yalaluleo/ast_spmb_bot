"""
© 2025 Tiara Chantika. All rights reserved.
This script is not licensed for reuse or distribution without permission.
Enhanced for SPMB Banten 2026 & SPMB Jakarta 2026: MySQL, Admin Claim (Ambil Tugas), and Transparency.
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

# ========== KONFIGURASI MULTI BOT ==========
# Konfigurasi untuk Banten
BOT_TOKEN_BANTEN = os.getenv("BOT_TOKEN_BANTEN")
CHANNEL_ID_BANTEN = os.getenv("CHANNEL_ID_BANTEN")
GROUP_LINK_BANTEN = os.getenv("GROUP_LINK_BANTEN", 'https://t.me/+h0ph8Z8PV8QyZTc1')

# Konfigurasi untuk Jakarta
BOT_TOKEN_JAKARTA = os.getenv("BOT_TOKEN_JAKARTA")
CHANNEL_ID_JAKARTA = os.getenv("CHANNEL_ID_JAKARTA")
GROUP_LINK_JAKARTA = os.getenv("GROUP_LINK_JAKARTA", 'https://t.me/+8cJDNLD7Dw1iMWE1')

# Dictionary untuk menyimpan semua konfigurasi bot
BOTS_CONFIG = {
    "banten": {
        "name": "Banten",
        "token": BOT_TOKEN_BANTEN,
        "channel_id": CHANNEL_ID_BANTEN,
        "group_link": GROUP_LINK_BANTEN,
        "welcome_text": (
            "Hai ASTers! {full_name} 👋\n\n"
            "Selamat datang di AST | SPMB Banten 2026\n\n"
            "Silakan kirim bukti persyaratan kamu di sini untuk dapat join di Grup Telegram kami, yang berupa:\n"
            "✅ Screenshot follow Instagram @anaksmatangerang\n"
            "✅ Screenshot repost postingan ke Instagram Story\n"
            "✅ Screenshot komentar yang berisi mention 5 teman di postingan alur join grup Telegram SPMB Banten 2026\n\n"
            "Link postingan: https://www.instagram.com/p/DYEK3nyCWcz/?igsh=MXZ6dXVwb295MndodQ==\n\n"
            "Kirimkan bukti dalam bentuk foto (maksimal 10 foto) atau PDF di chat ini. Terima kasih 😊"
        ),
        "approve_text": (
            "Terima kasih ASTers! Persyaratan kamu sudah lengkap.\n\n"
            "Silakan klik link berikut untuk bergabung ke Grup Info SPMB Banten 2026:\n"
            "{group_link}\n\n"
            "Sampai jumpa di grup!"
        ),
        "reject_text": (
            "Oops! Sepertinya persyaratan kamu belum lengkap.\n\n"
            "Mohon pastikan kamu telah mengirim persyaratan dalam bentuk foto atau PDF, yang berupa:\n\n"
            "✅ Screenshot follow Instagram @anaksmatangerang\n"
            "✅ Screenshot repost postingan ke Instagram Story\n"
            "✅ Screenshot komentar yang berisi mention 5 teman di postingan alur join grup Telegram SPMB Banten 2026 (lihat di postingan yang dipin paling atas)\n\n"
            "Silakan kirim ulang bukti kamu jika ada yang terlewat ya. Terima kasih 😊"
        )
    },
    "jakarta": {
        "name": "Jakarta",
        "token": BOT_TOKEN_JAKARTA,
        "channel_id": CHANNEL_ID_JAKARTA,
        "group_link": GROUP_LINK_JAKARTA,
        "welcome_text": (
            "Hai JakStars! {full_name} 👋\n\n"
            "Selamat datang di ASJ | SPMB DKI Jakarta 2026\n\n"
            "Silakan kirim bukti persyaratan kamu di sini untuk dapat join di Grup Telegram kami, yang berupa:\n"
            "✅ Screenshot follow Instagram @anaksma.jakarta\n"
            "✅ Screenshot repost postingan ke Instagram Story\n"
            "✅ Screenshot komentar yang berisi mention 5 teman di postingan alur join grup Telegram SPMB DKI Jakarta 2026\n\n"
            "Link postingan: https://www.instagram.com/p/CONTOH_LINK_JAKARTA/\n\n"
            "Kirimkan bukti dalam bentuk foto (maksimal 10 foto) atau PDF di chat ini. Terima kasih 😊"
        ),
        "approve_text": (
            "Terima kasih JakStars! Persyaratan kamu sudah lengkap.\n\n"
            "Silakan klik link berikut untuk bergabung ke Grup Info SPMB DKI Jakarta 2026:\n"
            "{group_link}\n\n"
            "Sampai jumpa di grup!"
        ),
        "reject_text": (
            "Oops! Sepertinya persyaratan kamu belum lengkap.\n\n"
            "Mohon pastikan kamu telah mengirim persyaratan dalam bentuk foto atau PDF, yang berupa:\n\n"
            "✅ Screenshot follow Instagram @anaksma.jakarta\n"
            "✅ Screenshot repost postingan ke Instagram Story\n"
            "✅ Screenshot komentar yang berisi mention 5 teman di postingan alur join grup Telegram SPMB DKI Jakarta 2026 (lihat di postingan yang dipin paling atas)\n\n"
            "Silakan kirim ulang bukti kamu jika ada yang terlewat ya. Terima kasih 😊"
        )
    }
}

# CEK ENVIRONMENT VARIABLE PENTING untuk kedua bot
required_vars_banten = ["BOT_TOKEN_BANTEN", "CHANNEL_ID_BANTEN"]
required_vars_jakarta = ["BOT_TOKEN_JAKARTA", "CHANNEL_ID_JAKARTA"]
required_vars_mysql = ["MYSQLHOST", "MYSQLUSER", "MYSQLPASSWORD", "MYSQLDATABASE"]

missing_vars = []

for var in required_vars_banten:
    if not os.getenv(var):
        missing_vars.append(var)
for var in required_vars_jakarta:
    if not os.getenv(var):
        missing_vars.append(var)
for var in required_vars_mysql:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
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

# Global dictionaries - setiap bot punya dictionary sendiri
user_data_banten = {}
message_to_user_banten = {}
admin_replies_banten = {}
pending_albums_banten = {}

user_data_jakarta = {}
message_to_user_jakarta = {}
admin_replies_jakarta = {}
pending_albums_jakarta = {}

def save_to_mysql(user_id, username, full_name, msg_id, file_id=None, region="banten"):
    """Simpan data ke MySQL dengan region"""
    db = None
    try:
        db = get_db()
        if not db:
            logger.error("Failed to get database connection")
            return False
            
        cursor = db.cursor()
        sql = """INSERT INTO submissions (user_id, username, full_name, admin_msg_id, file_id, status, created_at, region) 
                 VALUES (%s, %s, %s, %s, %s, 'pending', NOW(), %s)"""
        cursor.execute(sql, (str(user_id), username or '', full_name or '', str(msg_id), file_id, region))
        db.commit()
        logger.info(f"Data saved to MySQL for user {user_id} in region {region}")
        return True
    except Exception as e:
        logger.error(f"MySQL Insert Error: {e}")
        return False
    finally:
        if db:
            db.close()

def update_admin_status(msg_id, status, admin_name, region="banten"):
    """Update status di database dengan region"""
    db = None
    try:
        db = get_db()
        if not db:
            return False
            
        cursor = db.cursor()
        sql = "UPDATE submissions SET status = %s, admin_handler = %s, updated_at = NOW() WHERE admin_msg_id = %s AND region = %s"
        cursor.execute(sql, (status, admin_name, str(msg_id), region))
        db.commit()
        logger.info(f"Updated status for msg {msg_id} to {status} by {admin_name} in region {region}")
        return True
    except Exception as e:
        logger.error(f"MySQL Update Error: {e}")
        return False
    finally:
        if db:
            db.close()

def get_admin_keyboard(user_id, status="pending", region="banten"):
    if status == "pending":
        return InlineKeyboardMarkup([[InlineKeyboardButton("Ambil Tugas", callback_data=f"claim_{region}_{user_id}")]])
    elif status == "processing":
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Lengkap", callback_data=f"approve_{region}_{user_id}"),
                InlineKeyboardButton("Belum Lengkap", callback_data=f"reject_{region}_{user_id}"),
                InlineKeyboardButton("Reply", callback_data=f"reply_{region}_{user_id}")
            ]
        ])
    return None

def save_mapping(user_id, chat_id, group_msg_id, region="banten"):
    """Simpan mapping user ke message ID sesuai region"""
    if region == "banten":
        user_data_banten[user_id] = {
            "chat_id": chat_id,
            "group_msg_id": group_msg_id,
            "status": "pending"
        }
        message_to_user_banten[group_msg_id] = user_id
    else:
        user_data_jakarta[user_id] = {
            "chat_id": chat_id,
            "group_msg_id": group_msg_id,
            "status": "pending"
        }
        message_to_user_jakarta[group_msg_id] = user_id

def get_user_data(user_id, region="banten"):
    """Ambil user data sesuai region"""
    if region == "banten":
        return user_data_banten.get(user_id)
    else:
        return user_data_jakarta.get(user_id)

def get_message_to_user(msg_id, region="banten"):
    """Ambil user dari message ID sesuai region"""
    if region == "banten":
        return message_to_user_banten.get(msg_id)
    else:
        return message_to_user_jakarta.get(msg_id)

def save_mapping_reply(msg_id, replied_id, region="banten"):
    """Simpan mapping reply admin"""
    if region == "banten":
        admin_replies_banten[msg_id] = replied_id
    else:
        admin_replies_jakarta[msg_id] = replied_id

def get_pending_albums(region="banten"):
    """Ambil pending albums sesuai region"""
    if region == "banten":
        return pending_albums_banten
    else:
        return pending_albums_jakarta

# ========== HANDLER FUNCTIONS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler start - menggunakan konfigurasi sesuai region"""
    user = update.effective_user
    # Ambil region dari context (sudah disimpan saat bot dibuat)
    region = context.bot_data.get("region", "banten")
    config = BOTS_CONFIG[region]
    
    try:
        welcome_message = config["welcome_text"].format(full_name=user.full_name)
        await update.message.reply_text(welcome_message)
    except Exception as e:
        logger.error(f"Error in start for {region}: {e}")

async def handle_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler submission - menggunakan konfigurasi sesuai region"""
    user = update.effective_user
    msg = update.message
    region = context.bot_data.get("region", "banten")
    config = BOTS_CONFIG[region]
    channel_id = int(config["channel_id"])

    if not msg:
        return

    if msg.photo or msg.document:
        admin_msg = (
            f"Peserta Baru - {config['name']}\n"
            f"User ID: {user.id}\n"
            f"Display name: {user.full_name}\n"
            f"Username: @{user.username if user.username else 'N/A'}\n\n"
            f"Pesan: {msg.text or msg.caption or '(tanpa teks)'}\n"
            f"Status: Menunggu Admin"
        )

        keyboard = get_admin_keyboard(user.id, "pending", region)

        try:
            if msg.media_group_id:
                # Handle album
                pending_albums = get_pending_albums(region)
                if msg.media_group_id not in pending_albums:
                    pending_albums[msg.media_group_id] = {
                        "messages": [],
                        "user_id": user.id,
                        "chat_id": msg.chat_id,
                        "username": user.username,
                        "full_name": user.full_name,
                        "admin_msg": admin_msg,
                        "keyboard": keyboard,
                        "region": region,
                        "channel_id": channel_id
                    }
                
                pending_albums[msg.media_group_id]["messages"].append(msg)
                
                if len(pending_albums[msg.media_group_id]["messages"]) == 1:
                    asyncio.create_task(process_album_after_delay(context, msg.media_group_id, region, channel_id))
                return
                
            elif msg.photo:
                file_id = msg.photo[-1].file_id
                sent = await context.bot.send_photo(
                    channel_id,
                    photo=file_id,
                    caption=admin_msg,
                    reply_markup=keyboard
                )
                save_mapping(user.id, msg.chat_id, sent.message_id, region)
                save_to_mysql(user.id, user.username, user.full_name, sent.message_id, file_id, region)
                await msg.reply_text("Bukti kamu sudah kami terima. Tunggu verifikasi dari admin ya!")
                
            elif msg.document:
                file_id = msg.document.file_id
                sent = await context.bot.send_document(
                    channel_id,
                    document=file_id,
                    caption=admin_msg,
                    reply_markup=keyboard
                )
                save_mapping(user.id, msg.chat_id, sent.message_id, region)
                save_to_mysql(user.id, user.username, user.full_name, sent.message_id, file_id, region)
                await msg.reply_text("Bukti kamu sudah kami terima. Tunggu verifikasi dari admin ya!")

        except Exception as e:
            logger.error(f"Error in handle_submission for {region}: {e}")
            await msg.reply_text("Maaf, terjadi error. Silakan kirim ulang.")
    
    else:
        # KALAU USER KIRIM TEKS BIASA
        admin_msg_text = (
            f"Pesan dari User - {config['name']}\n"
            f"User ID: {user.id}\n"
            f"Nama: {user.full_name}\n"
            f"Username: @{user.username if user.username else 'N/A'}\n\n"
            f"Pesan: {msg.text}\n"
            f"Status: Menunggu Balasan Admin"
        )
        
        keyboard = get_admin_keyboard(user.id, "pending", region)
        
        sent = await context.bot.send_message(
            channel_id,
            text=admin_msg_text,
            reply_markup=keyboard
        )
        
        save_mapping(user.id, msg.chat_id, sent.message_id, region)
        save_to_mysql(user.id, user.username, user.full_name, sent.message_id, None, region)
        
        await msg.reply_text("Pesan kamu sudah kami terima. Tunggu balasan dari admin ya!")
        return

async def process_album_after_delay(context, album_id, region, channel_id):
    await asyncio.sleep(2)
    await process_album(context, album_id, region, channel_id)

async def process_album(context, album_id, region, channel_id):
    pending_albums = get_pending_albums(region)
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
        
        await context.bot.send_media_group(channel_id, media=media_group)
        
        sent_msg = await context.bot.send_message(
            channel_id,
            text=f"Album dari user {album_data['user_id']} - {region}\nTotal {len(media_list)} foto\n\nStatus: Menunggu Admin",
            reply_markup=album_data["keyboard"]
        )
        
        save_mapping(album_data["user_id"], album_data["chat_id"], sent_msg.message_id, region)
        save_to_mysql(album_data["user_id"], album_data["username"], album_data["full_name"], sent_msg.message_id, None, region)
        
        await context.bot.send_message(
            album_data["chat_id"],
            "Bukti kamu sudah kami terima. Tunggu verifikasi dari admin ya!"
        )
        
    except Exception as e:
        logger.error(f"Error processing album {album_id} for {region}: {e}")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler admin reply - menggunakan konfigurasi sesuai region"""
    region = context.bot_data.get("region", "banten")
    config = BOTS_CONFIG[region]
    channel_id = int(config["channel_id"])
    
    if update.effective_chat.id != channel_id:
        return

    msg = update.message
    if not msg.reply_to_message:
        return

    replied_id = msg.reply_to_message.message_id
    user_id = get_message_to_user(replied_id, region)
    
    if not user_id:
        try:
            db = get_db()
            if db:
                cursor = db.cursor()
                cursor.execute("SELECT user_id FROM submissions WHERE admin_msg_id = %s AND region = %s", (str(replied_id), region))
                result = cursor.fetchone()
                if result:
                    user_id = int(result[0])
                db.close()
        except Exception as e:
            logger.error(f"DB Search Error for {region}: {e}")

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
        
        save_mapping_reply(msg.message_id, replied_id, region)
        
    except Exception as e:
        logger.error(f"Gagal mengirim balasan untuk {region}: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler callback - menggunakan konfigurasi sesuai region"""
    query = update.callback_query
    admin_name = query.from_user.full_name
    await query.answer()
    
    data = query.data.split('_')
    if len(data) < 3:
        return

    action = data[0]
    region = data[1]
    user_id_str = data[2]
    user_id = int(user_id_str)
    
    config = BOTS_CONFIG.get(region)
    if not config:
        logger.error(f"Unknown region: {region}")
        return
    
    channel_id = int(config["channel_id"])
    group_link = config["group_link"]
    
    user_info = get_user_data(user_id, region)
    if not user_info:
        if region == "banten":
            user_data_banten[user_id] = {"chat_id": user_id, "status": "pending"}
        else:
            user_data_jakarta[user_id] = {"chat_id": user_id, "status": "pending"}
    
    msg_id = query.message.message_id
    
    # Simpan mapping untuk callback
    if region == "banten":
        message_to_user_banten[msg_id] = user_id
    else:
        message_to_user_jakarta[msg_id] = user_id

    try:
        if action == "claim":
            update_admin_status(msg_id, "processing", admin_name, region)
            new_keyboard = get_admin_keyboard(user_id, "processing", region)
            
            if query.message.caption is not None:
                current_caption = query.message.caption
                new_caption = current_caption.replace("Status: Menunggu Admin", f"Status: Sedang dicek oleh {admin_name}")
                await query.edit_message_caption(caption=new_caption, reply_markup=new_keyboard)
            else:
                current_text = query.message.text
                new_text = current_text.replace("Status: Menunggu Admin", f"Status: Sedang dicek oleh {admin_name}")
                await query.edit_message_text(text=new_text, reply_markup=new_keyboard)
            
        elif action == "approve":
            update_admin_status(msg_id, "approved", admin_name, region)
            if user_info or (region == "banten" and user_id in user_data_banten) or (region == "jakarta" and user_id in user_data_jakarta):
                approve_message = config["approve_text"].format(group_link=group_link)
                await context.bot.send_message(user_id, approve_message)

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
            update_admin_status(msg_id, "rejected", admin_name, region)
            if user_info or (region == "banten" and user_id in user_data_banten) or (region == "jakarta" and user_id in user_data_jakarta):
                reject_message = config["reject_text"]
                await context.bot.send_message(user_id, reject_message)

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
        logger.error(f"Error in handle_callback for {region}: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}", exc_info=True)

# ========== FUNGSI UNTUK MENJALANKAN SATU BOT ==========
async def run_bot(region: str, config: dict):
    """Jalankan satu bot untuk region tertentu"""
    logger.info(f"Starting bot for {region}...")
    
    # Konversi channel_id ke integer
    channel_id = int(config["channel_id"])
    
    # Build application
    app = ApplicationBuilder().token(config["token"]).build()
    
    # Simpan region dan channel_id ke bot_data
    app.bot_data["region"] = region
    app.bot_data["channel_id"] = channel_id
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.PHOTO | filters.Document.ALL | filters.TEXT) & (~filters.COMMAND),
        handle_submission
    ))
    app.add_handler(MessageHandler(
        filters.Chat(channel_id) & filters.REPLY,
        handle_admin_reply
    ))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    logger.info(f"Bot for {region} is running...")
    
    # Initialize and start polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Keep the bot running
    try:
        await asyncio.Future()  # Run forever
    except asyncio.CancelledError:
        logger.info(f"Bot for {region} is stopping...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

# ========== MAIN ==========
async def main():
    logger.info("Starting Multi Bot System...")
    
    # Test database connection
    db = get_db()
    if not db:
        logger.error("Database connection failed! Please check your MySQL configuration.")
        sys.exit(1)
    db.close()
    logger.info("Database connection successful")
    
    # Siapkan daftar bot yang akan dijalankan
    bot_tasks = []
    
    for region, config in BOTS_CONFIG.items():
        if config["token"] and config["channel_id"]:
            bot_tasks.append(asyncio.create_task(run_bot(region, config)))
            logger.info(f"Prepared to start bot for {region}")
        else:
            logger.warning(f"Skipping {region} - missing token or channel_id")
    
    if not bot_tasks:
        logger.error("No bots configured! Exiting...")
        sys.exit(1)
    
    # Jalankan semua bot secara bersamaan
    await asyncio.gather(*bot_tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")