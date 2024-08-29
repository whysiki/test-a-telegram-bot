import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.types import FSInputFile, InputFile
from PIL import Image, ImageChops
from typing import BinaryIO
from aiogram.types import BufferedInputFile, URLInputFile
from aiogram.client.session.aiohttp import AiohttpSession
import io

# from rich import print
import cv2
import tempfile
import imageio


# Bot token can be obtained via https://t.me/BotFather
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# All handlers should be attached to the Router (or Dispatcher)
# session = AiohttpSession(proxy="http://127.0.0.1:62333/")
dp = Dispatcher()
# Initialize Bot instance with default bot properties which will be passed to all API calls
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    # session=session,
)


def trim(image):
    # Create a background image of the same size with a white background
    bg = Image.new(image.mode, image.size, (255, 255, 255))

    # Find the bounding box of the non-white areas
    diff = ImageChops.difference(image, bg)
    bbox = diff.getbbox()

    if bbox:
        return image.crop(bbox)
    else:
        return image  # If there's no non-white area, return the original image


# @dp.message(Command("test"))
# async def command_test_handler(message: Message) -> None:
#     text_file = BufferedInputFile(b"Hello, world!", filename="file.txt")
#     await message.answer_document(text_file, caption="Test file")
def webm_to_gif_buffered_input_file(webm_io: io.BytesIO) -> BufferedInputFile:
    # 将 BytesIO 对象保存为临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
        temp_file.write(webm_io.read())
        temp_file_path = temp_file.name

    # 使用 OpenCV 读取临时文件
    video_cap = cv2.VideoCapture(temp_file_path)

    frames = []
    while True:
        ret, frame = video_cap.read()
        if not ret:
            break
        # OpenCV 读取的是 BGR 格式，需要转换为 RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame)

    video_cap.release()

    # 将帧列表保存为 GIF
    gif_bytes = io.BytesIO()
    imageio.mimsave(gif_bytes, frames, format="GIF", duration=0.1)
    gif_bytes.seek(0)

    # 创建 BufferedInputFile 对象
    gif_file = BufferedInputFile(gif_bytes.read(), filename="animation.gif")
    return gif_file


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


@dp.message()
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # if message is a sticker, get the webp content and convert it to jpg

        if message.sticker:

            is_animated = message.sticker.is_animated

            is_video = message.sticker.is_video

            print(f"Sticker is_animated : {message.sticker.is_animated}")

            print(f"Sticker is_video : {message.sticker.is_video}")  # webm

            sticker_id: str = message.sticker.file_id

            print(f"Sticker ID: {sticker_id}")

            sticker = await bot.get_file(sticker_id)
            sticker_path = sticker.file_path

            print(f"Sticker Path: {sticker_path}")

            sticker_obj: BinaryIO = await bot.download_file(
                sticker_path
            )  # io.BinaryIO()

            if not is_animated and not is_video:
                webp_image = Image.open(sticker_obj)
                print(f"Sticker WebP Image Size: {webp_image.size}")

                # Convert the image to RGBA (if it has an alpha channel)
                if webp_image.mode in ("RGBA", "LA"):
                    background = Image.new(
                        "RGB", webp_image.size, (255, 255, 255)
                    )  # Create a white background
                    background.paste(
                        webp_image, (0, 0), webp_image.convert("RGBA")
                    )  # Paste the image onto the background
                    jpg_image = background
                else:
                    jpg_image = webp_image.convert("RGB")

                # Automatically crop white borders
                jpg_image = trim(jpg_image)

                print(f"Sticker JPG Image Size: {jpg_image.size}")

                image_io = io.BytesIO()

                jpg_image.save(image_io, "JPEG")  # 图像文件格式

                # image_io.seek(0)

                # will_send_image = BufferedInputFile(
                #     image_io.read(), filename="sticker.jpg"
                # )

                # jpg_image.save("sticker.jpg", "JPEG")
                # with open("sticker.jpg", "rb") as photo_file:
                #     photo = BufferedInputFile(photo_file.read(), filename="photo.jpg")

                image_bytes = image_io.getvalue()

                will_send_image = BufferedInputFile(image_bytes, filename="sticker.jpg")

                print(f"Will Send Image type: {type(will_send_image)}")

                await message.answer_photo(will_send_image, caption="Converted to jpg")

                # upload with URLInputFile

                # will_send_image = URLInputFile(
                #     "https://www.python.org/static/community_logos/python-powered-h-140x182.png",
                #     filename="python-logo.png",
                # )
                # # Will Send Image type: <class 'aiogram.types.input_file.URLInputFile'>

                # will_send_image_fs = FSInputFile("sticker.jpg")
                # await message.answer_photo(
                #     will_send_image_fs, caption="Converted to jpg"
                # )

            elif is_video:

                # webm to gif

                will_send_image = webm_to_gif_buffered_input_file(sticker_obj)

                await message.answer_document(
                    will_send_image, caption="Converted to gif"
                )

        else:

            # Send a copy of the received message
            await message.send_copy(chat_id=message.chat.id)

    except TypeError as e:

        print(f"Error: {str(e)}")

        # But not all the types is supported to be copied so need to handle it
        await message.answer(f"Error: Unsupported message type, {str(e)}")


async def main() -> None:

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
