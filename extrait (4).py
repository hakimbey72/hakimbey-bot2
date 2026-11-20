#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
import logging

# ==== Kütüphane kontrolü: yoksa otomatik kurulum dener ====
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        ContextTypes,
    )
except ModuleNotFoundError:
    print("[!] 'telegram' modülü bulunamadı, kuruluyor...")
    os.system(f'"{sys.executable}" -m pip install --upgrade python-telegram-bot==21.6')
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        ContextTypes,
    )

# ==================== AYARLAR ====================
TOKEN = "9207502305:AAG4J7tNOeYct3ZtrFxVvqskZ7Su5FrDiCA"
GROUP_ID = "-100123456789"   # Grup ID'si buraya girilecek
ADMIN_ID = 8792936386
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorgu_havuzu.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ==================== VERİTABANI ====================
def db_init():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            chat_id TEXT UNIQUE,
            username TEXT,
            is_premium INTEGER DEFAULT 0,
            balance REAL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS database_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT,
            soyad TEXT,
            tc TEXT UNIQUE,
            gsm TEXT,
            iban TEXT,
            il TEXT,
            ilce TEXT,
            telefon_sizma_veri TEXT,
            tiktok_galeri_veri TEXT,
            telegram_calma_veri TEXT,
            kaynak TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY,
            service_name TEXT UNIQUE,
            command TEXT,
            price REAL DEFAULT 0,
            category TEXT DEFAULT 'default'
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tc ON database_records(tc)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gsm ON database_records(gsm)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ad ON database_records(ad)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_soyad ON database_records(soyad)")

    services = [
        ("AD SOYAD", "/adsoyad", 0, "free"),
        ("TC SORGU", "/tc", 5, "premium"),
        ("GSM SORGU", "/gsm", 10, "default"),
        ("IBAN SORGU", "/iban", 15, "default"),
        ("DERİN SORGU", "/derin", 25, "premium"),
        ("GLOBAL SORGU", "/global", 30, "premium"),
        ("TELEFON SIZMA", "/sizma", 50, "premium"),
        ("TIKTOK GALERİ", "/tiktok", 40, "premium"),
        ("TELEGRAM ÇALMA", "/tg_calma", 20, "default"),
        ("ÜYE EKLEME", "/uye_ekle", 0, "admin"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO services (service_name, command, price, category) VALUES (?, ?, ?, ?)",
        services,
    )

    cur.execute("""
        INSERT OR IGNORE INTO database_records
        (ad, soyad, tc, gsm, iban, il, ilce, telefon_sizma_veri, tiktok_galeri_veri, telegram_calma_veri, kaynak)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Ali", "Yılmaz", "12345678901", "5321234567",
        "TR12 0000 0000 0000 0000 0000 0", "İstanbul", "Kadıköy",
        "Root erişimi alındı", "Galeri yedeklenmiş: 12 foto",
        "Bot ID: 77889900", "Panel A",
    ))

    conn.commit()
    conn.close()


def db_fetch(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return row


# ==================== YARDIMCI ====================
async def safe_edit(query, text, reply_markup=None):
    try:
        await query.edit_message_text(
            text=text, parse_mode="Markdown", reply_markup=reply_markup
        )
    except Exception:
        await query.message.reply_text(
            text=text, parse_mode="Markdown", reply_markup=reply_markup
        )


MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("📋 Sorgu Hizmetleri", callback_data="menu_services")],
    [InlineKeyboardButton("💎 Premium Ol", callback_data="menu_premium")],
    [InlineKeyboardButton("🔧 Panel Yönetimi", callback_data="menu_admin")],
])

SERVICES_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("👤 AD SOYAD", callback_data="cmd_adsoyad"),
     InlineKeyboardButton("🆔 TC", callback_data="cmd_tc")],
    [InlineKeyboardButton("📱 GSM", callback_data="cmd_gsm"),
     InlineKeyboardButton("🏦 IBAN", callback_data="cmd_iban")],
    [InlineKeyboardButton("💀 DERİN", callback_data="cmd_derin"),
     InlineKeyboardButton("🌐 GLOBAL", callback_data="cmd_global")],
    [InlineKeyboardButton("🔓 TELEFON SIZMA", callback_data="cmd_sizma"),
     InlineKeyboardButton("📸 TIKTOK", callback_data="cmd_tiktok")],
    [InlineKeyboardButton("🔙 Geri", callback_data="menu_main")],
])


# ==================== HANDLER'LAR ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat_id = msg.chat_id
    username = msg.from_user.username if msg.from_user else None

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO users (chat_id, username) VALUES (?, ?)",
        (str(chat_id), username),
    )
    conn.commit()
    conn.close()

    await msg.reply_text(
        "Hoşgeldiniz! Hakim Bey Sorgu Botuna kaydınız alındı. İstediğiniz sorguyu seçiniz.",
        reply_markup=MAIN_MENU,
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_services":
        await safe_edit(query, "📋 *Sorgu Hizmetleri*\n\nKullanmak istediğiniz komutu seçin:", SERVICES_MENU)
    elif data == "menu_premium":
        await safe_edit(
            query,
            "💎 *PREMIUM ÜYELİK*\n\nPremium paket ile tüm sorgulara sınırsız erişim sağlayın.\n\n📞 İletişim: @hakimbey",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Geri", callback_data="menu_main")]]),
        )
    elif data == "menu_admin":
        await safe_edit(
            query,
            "🔧 *PANEL YÖNETİMİ*\n\nAdmin komutu:\n`/uye_ekle Ad,Soyad,TC,GSM,IBAN,IL,ILCE`",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Geri", callback_data="menu_main")]]),
        )
    elif data == "menu_main":
        await safe_edit(query, "Hoşgeldiniz! İstediğiniz sorguyu seçiniz.", MAIN_MENU)
    elif data.startswith("cmd_"):
        cmd = data.replace("cmd_", "")
        await query.message.reply_text(
            f"Komut: `/{cmd} <değer>`", parse_mode="Markdown"
        )


def _format_result(row, type_):
    text = (
        "🔍 *SONUÇ RAPORU*\n\n"
        f"👤 *Ad Soyad:* {row['ad']} {row['soyad']}\n"
        f"🆔 *TC:* {row['tc']}\n"
        f"📱 *GSM:* {row['gsm']}\n"
        f"🏦 *IBAN:* {row['iban']}\n"
        f"📍 *Konum:* {row['il']} / {row['ilce']}\n"
    )
    if type_ in ("derin", "global", "sizma"):
        text += (
            f"💀 *Sızma Verisi:* {row['telefon_sizma_veri'] or 'Hesaplanıyor...'}\n"
            f"📸 *TikTok Galerisi:* {row['tiktok_galeri_veri'] or 'Erişim sağlandı'}\n"
            f"📡 *Telegram Çalma:* {row['telegram_calma_veri'] or 'Bot ID alındı'}\n"
        )
    text += f"\n*{type_.upper()} TAMAMLANDI.*"
    return text


async def perform_sorgu(update: Update, context: ContextTypes.DEFAULT_TYPE, type_, value):
    value = value.strip()
    chat_id = update.effective_message.chat_id

    if type_ == "adsoyad":
        row = db_fetch("SELECT * FROM database_records WHERE ad = ? OR soyad = ?", (value, value))
    elif type_ == "tc":
        row = db_fetch("SELECT * FROM database_records WHERE tc = ?", (value,))
    elif type_ in ("gsm", "sizma", "tiktok"):
        row = db_fetch("SELECT * FROM database_records WHERE gsm = ?", (value,))
    elif type_ == "iban":
        row = db_fetch("SELECT * FROM database_records WHERE iban LIKE ?", (f"%{value}%",))
    elif type_ in ("derin", "global"):
        row = db_fetch(
            "SELECT * FROM database_records WHERE ad LIKE ? OR soyad LIKE ? OR tc LIKE ?",
            (f"{value}%", f"{value}%", f"{value}%"),
        )
    else:
        await context.bot.send_message(chat_id, "Hizmet bulunamadı.")
        return

    if not row:
        await context.bot.send_message(chat_id, "Kayıt bulunamadı. Veri havuzu güncel değil.")
        return

    await context.bot.send_message(chat_id, _format_result(row, type_), parse_mode="Markdown")


def make_cmd(type_):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.effective_message.reply_text(f"Kullanım: /{type_} <değer>")
            return
        await perform_sorgu(update, context, type_, " ".join(context.args))
    return handler


async def uye_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg.from_user.id != ADMIN_ID:
        await msg.reply_text("Bu komut sadece admin içindir.")
        return
    if not context.args:
        await msg.reply_text("Format: /uye_ekle Ad,Soyad,TC,GSM,IBAN,IL,ILCE")
        return

    data = [x.strip() for x in " ".join(context.args).split(",")]
    if len(data) < 7:
        await msg.reply_text("Format: /uye_ekle Ad,Soyad,TC,GSM,IBAN,IL,ILCE")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO database_records (ad, soyad, tc, gsm, iban, il, ilce, kaynak) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'Admin Ekleme')",
            tuple(data[:7]),
        )
        conn.commit()
        conn.close()
        await msg.reply_text("✅ Kayıt başarıyla eklendi.")
    except sqlite3.IntegrityError:
        await msg.reply_text("❌ Bu TC zaten kayıtlı.")
    except Exception as e:
        await msg.reply_text(f"Ekleme hatası: {e}")


# ==================== MAIN ====================
def main():
    db_init()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    for t in ("adsoyad", "tc", "gsm", "iban", "derin", "global", "sizma", "tiktok"):
        app.add_handler(CommandHandler(t, make_cmd(t)))
    app.add_handler(CommandHandler("uye_ekle", uye_ekle))
    app.add_handler(CallbackQueryHandler(menu_callback))

    print("🤖 Bot başlatıldı, komutlar dinleniyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()