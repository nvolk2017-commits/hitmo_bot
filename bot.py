import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from scraper import search_tracks, get_download_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Хранилище результатов поиска (в памяти, по chat_id)
search_results: dict[int, list[dict]] = {}


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎵 <b>Hitmo Music Bot</b>\n\n"
        "Я помогу найти и скачать музыку бесплатно с сайта hitmotop.\n\n"
        "Просто напиши название песни или исполнителя 👇",
        parse_mode="HTML"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Как пользоваться:</b>\n\n"
        "1. Напиши название трека или исполнителя\n"
        "2. Выбери нужный трек из списка\n"
        "3. Получи MP3 файл прямо в чате\n\n"
        "Пример: <code>Eminem Lose Yourself</code>",
        parse_mode="HTML"
    )


@dp.message(F.text)
async def handle_search(message: Message):
    query = message.text.strip()
    if not query:
        return

    status_msg = await message.answer("🔍 Ищу треки...")

    try:
        tracks = await search_tracks(query)
    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_msg.edit_text("❌ Ошибка при поиске. Попробуй ещё раз.")
        return

    if not tracks:
        await status_msg.edit_text("😔 Ничего не найдено. Попробуй другой запрос.")
        return

    # Сохраняем результаты для этого пользователя
    search_results[message.from_user.id] = tracks

    # Формируем инлайн-кнопки (до 10 треков)
    buttons = []
    for i, track in enumerate(tracks[:10]):
        label = f"🎵 {track['artist']} — {track['title']}"
        if len(label) > 60:
            label = label[:57] + "..."
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"dl:{i}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await status_msg.edit_text(
        f"🎶 Найдено <b>{len(tracks[:10])}</b> треков по запросу «{query}».\nВыбери нужный:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("dl:"))
async def handle_download(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_index = int(callback.data.split(":")[1])

    tracks = search_results.get(user_id)
    if not tracks or track_index >= len(tracks):
        await callback.answer("❌ Результаты поиска устарели. Поищи снова.", show_alert=True)
        return

    track = tracks[track_index]
    await callback.answer()
    status_msg = await callback.message.answer(
        f"⬇️ Скачиваю <b>{track['artist']} — {track['title']}</b>...",
        parse_mode="HTML"
    )

    try:
        mp3_url = await get_download_url(track["url"])
        if not mp3_url:
            await status_msg.edit_text("❌ Не удалось получить ссылку на скачивание.")
            return

        await callback.message.answer_audio(
            audio=mp3_url,
            title=track["title"],
            performer=track["artist"],
            caption=f"🎵 {track['artist']} — {track['title']}\n\n<i>via Hitmo Music Bot</i>",
            parse_mode="HTML"
        )
        await status_msg.delete()

    except Exception as e:
        logger.error(f"Download error: {e}")
        await status_msg.edit_text("❌ Ошибка при скачивании. Попробуй другой трек.")


async def main():
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
