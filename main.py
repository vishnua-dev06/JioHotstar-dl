
import logging
import os
import tempfile

import yt_dlp
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Load environment variables from .env
load_dotenv()

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to JioHotstar Downloader Bot!\n"
        "Send any JioHotstar video link to download."
    )


# Handle JioHotstar links
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "hotstar.com" in text:
        context.user_data["hotstar_url"] = text

        keyboard = [
            [InlineKeyboardButton("1080p (Full HD)", callback_data="q_1080p")],
            [InlineKeyboardButton("720p (HD)", callback_data="q_720p")],
            [InlineKeyboardButton("480p", callback_data="q_480p")],
        ]

        await update.message.reply_text(
            "📥 Select video quality for download:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await update.message.reply_text(
            "Please send a valid JioHotstar link containing 'hotstar.com'."
        )


# Handle quality selection and downloads
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("q_"):
        quality = query.data.split("_")[1]
        context.user_data["quality"] = quality

        keyboard = [
            [
                InlineKeyboardButton(
                    "Submit / Download 🚀",
                    callback_data="start_download",
                )
            ]
        ]

        await query.edit_message_text(
            text=f"Selected Quality: {quality}\n"
                 "Click Submit to start downloading:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "start_download":
        await query.edit_message_text(
            text="⏳ Downloading video from JioHotstar... Please wait."
        )

        url = context.user_data.get("hotstar_url")
        quality = context.user_data.get("quality", "720p")

        if not url:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ Please send a JioHotstar link first.",
            )
            return

        height = quality.replace("p", "")
        cookie_file_path = None

        try:
            os.makedirs("downloads", exist_ok=True)

            # yt-dlp settings - direct connection, no proxy
            ydl_opts = {
                "format": f"best[height<={height}]/best",
                "outtmpl": "downloads/%(title)s.%(ext)s",
                "noplaylist": True,
            }

            # Read Hotstar cookies from .env
            hotstar_cookies = os.getenv("HOTSTAR_COOKIES")

            if hotstar_cookies:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    suffix=".txt",
                    delete=False,
                ) as cookie_file:
                    cookie_file.write(hotstar_cookies)
                    cookie_file_path = cookie_file.name

                ydl_opts["cookiefile"] = cookie_file_path

            # Download video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):
                raise FileNotFoundError("Downloaded video file was not found.")

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="✅ Download completed! Uploading to Telegram...",
            )

            # Upload video to Telegram
            with open(filename, "rb") as video_file:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=video_file,
                )

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="🎉 Video sent successfully!",
            )

            # Delete downloaded video
            os.remove(filename)

        except Exception as e:
            logger.exception("Download error")

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"❌ Download failed: {str(e)}",
            )

        finally:
            # Always delete temporary cookie file
            if cookie_file_path and os.path.exists(cookie_file_path):
                os.remove(cookie_file_path)


def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    if not TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is missing from environment variables!"
        )

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    app.add_handler(CallbackQueryHandler(button_handler))

    print("JioHotstar Downloader Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
