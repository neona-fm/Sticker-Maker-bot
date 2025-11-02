import os
import aiohttp
import asyncio
import shutil
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from rembg import remove
from dotenv import load_dotenv
import subprocess

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

TMP = "/tmp/frames"

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("🎬 Пришли видео до 3 сек (до 1 МБ), и я сделаю его с прозрачным фоном.")

@dp.message(F.video | F.document | F.animation)
async def handle_video(message: Message):
    file = message.video or message.document or message.animation
    if not file:
        await message.answer("⚠️ Пришли видео-файл до 3 секунд.")
        return

    if file.file_size and file.file_size > 1_000_000:
        await message.answer("❌ Видео слишком большое. До 1 МБ.")
        return

    # Проверка продолжительности (только если есть)
    duration = None
    if message.video:
        duration = message.video.duration
    elif message.animation:
        duration = message.animation.duration

    if duration and duration > 3:
        await message.answer("❌ Видео слишком длинное. До 3 секунд.")
        return

    await message.answer("📥 Скачиваю файл...")
    try:
        tg_file = await bot.get_file(file.file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{tg_file.file_path}"
        input_path = f"/tmp/input_{file.file_id}.webm"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await message.answer(f"❌ Не удалось скачать файл: {resp.status}")
                    return
                with open(input_path, "wb") as f:
                    f.write(await resp.read())
    except Exception as e:
        await message.answer(f"❌ Ошибка скачивания: {e}")
        return

    await message.answer("🧪 Удаляю фон...")

    output_path = await process_video(input_path)
    if output_path and os.path.exists(output_path):
        await message.answer_document(FSInputFile(output_path))
        os.remove(output_path)
    else:
        await message.answer("❌ Обработка не удалась.")

    if os.path.exists(input_path):
        os.remove(input_path)

async def process_video(file_path: str) -> str:
    os.makedirs(TMP, exist_ok=True)
    OUTPUT = file_path.replace(".webm", "_processed.webm")

    subprocess.run([
        "ffmpeg", "-y", "-i", file_path,
        "-vf", "fps=12,scale=512:512:force_original_aspect_ratio=decrease,format=rgba",
        f"{TMP}/frame_%04d.png"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    frames = sorted([f for f in os.listdir(TMP) if f.endswith(".png")])
    if not frames:
        return None

    for fname in frames:
        path = os.path.join(TMP, fname)
        try:
            with open(path, "rb") as f:
                out = remove(f.read())
            with open(path, "wb") as g:
                g.write(out)
        except:
            pass

    subprocess.run([
        "ffmpeg", "-y", "-framerate", "15", "-i", f"{TMP}/frame_%04d.png",
        "-vcodec", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
        "-t", "3", "-an", OUTPUT
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f in frames:
        os.remove(os.path.join(TMP, f))
    shutil.rmtree(TMP, ignore_errors=True)

    return OUTPUT if os.path.exists(OUTPUT) else None

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


