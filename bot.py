import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile
from aiogram.client.session.aiohttp import AiohttpSession
from PIL import Image, ImageChops
from typing import BinaryIO
import io
import cv2
import tempfile
import imageio
import urllib.request
from datetime import datetime
from pathlib import Path

# logging.basicConfig(level=logging.INFO, stream=sys.stdout)
log_save_path = os.path.join(
    os.getcwd(), "logs", f"{datetime.now().strftime('%Y-%m-%d')}.log"
)
Path(os.path.dirname(log_save_path)).mkdir(parents=True, exist_ok=True)

if not os.path.exists(log_save_path):
    with open(log_save_path, "w", errors="ignore", encoding="utf-8"):
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_save_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
proxy = "http://127.0.0.1:62333/"


# Check if the proxy is working
def check_proxy(proxy):
    proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
    opener = urllib.request.build_opener(proxy_handler)
    try:
        urllib.request.install_opener(opener)
        urllib.request.urlopen("https://api.telegram.org")
        logging.info("Proxy is working")
        return proxy
    except Exception as e:
        logging.error(f"Proxy Error: {str(e)}")
        return None


proxy = check_proxy(proxy)

dp = Dispatcher()
session = AiohttpSession(proxy=proxy)
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=session,
)


def trim(image):
    bg = Image.new(image.mode, image.size, (255, 255, 255))
    diff = ImageChops.difference(image, bg)
    bbox = diff.getbbox()
    return image.crop(bbox) if bbox else image


def webm_to_gif_buffered_input_file(webm_io: io.BytesIO) -> BufferedInputFile:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
        temp_file.write(webm_io.read())
        temp_file_path = temp_file.name
    video_cap = cv2.VideoCapture(temp_file_path)
    logging.info(f"Video Frame Count: {int(video_cap.get(cv2.CAP_PROP_FRAME_COUNT))}")
    frames = []
    while True:
        ret, frame = video_cap.read()
        if not ret:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame)
    video_cap.release()

    gif_bytes = io.BytesIO()
    imageio.mimsave(gif_bytes, frames, format="GIF", loop=0)
    gif_bytes.seek(0)
    logging.info(f"Converted GIF Size: {len(gif_bytes.getvalue())}")

    gif_file = BufferedInputFile(gif_bytes.read(), filename="animation.gif")
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
        logging.info(f"Deleted Temp File: {temp_file_path}")
    return gif_file


async def handle_sticker(
    message: Message, sticker_obj: BinaryIO, is_animated: bool, is_video: bool
):
    if not is_animated and not is_video:
        webp_image = Image.open(sticker_obj)
        logging.info(f"Sticker WebP Image Size: {webp_image.size}")

        if webp_image.mode in ("RGBA", "LA"):
            background = Image.new("RGB", webp_image.size, (255, 255, 255))
            background.paste(webp_image, (0, 0), webp_image.convert("RGBA"))
            jpg_image = background
        else:
            jpg_image = webp_image.convert("RGB")

        jpg_image = trim(jpg_image)
        logging.info(f"Sticker JPG Image Size: {jpg_image.size}")

        image_io = io.BytesIO()
        jpg_image.save(image_io, "JPEG")
        image_bytes = image_io.getvalue()

        will_send_image = BufferedInputFile(image_bytes, filename="sticker.jpg")
        logging.info(f"Will Send Image type: {type(will_send_image)}")

        await message.answer_photo(will_send_image, caption="Converted to jpg")
    elif is_video:
        will_send_image = webm_to_gif_buffered_input_file(sticker_obj)
        await message.answer_document(will_send_image, caption="Converted to gif")


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


@dp.message()
async def echo_handler(message: Message) -> None:
    try:
        if message.sticker:
            is_animated = message.sticker.is_animated
            is_video = message.sticker.is_video
            logging.info(f"Sticker is_animated: {is_animated}")
            logging.info(f"Sticker is_video: {is_video}")

            sticker_id: str = message.sticker.file_id
            logging.info(f"Sticker ID: {sticker_id}")

            sticker = await bot.get_file(sticker_id)
            sticker_path = sticker.file_path
            logging.info(f"Sticker Path: {sticker_path}")

            sticker_obj: BinaryIO = await bot.download_file(sticker_path)
            await handle_sticker(message, sticker_obj, is_animated, is_video)
        else:
            await message.send_copy(chat_id=message.chat.id)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        await message.answer(f"Error: Unsupported message type, {str(e)}")


async def main() -> None:

    await bot.send_message(OWNER_ID, "I'm alive! 🥰")
    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
