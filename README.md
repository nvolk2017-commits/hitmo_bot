# 🎵 Hitmo Music Bot

Telegram-бот для поиска и скачивания музыки с сайта [eu.hitmo-top.com](https://eu.hitmo-top.com).

---

## 📁 Структура проекта

```
hitmo_bot/
├── bot.py          # Основной файл бота (обработчики команд и callback)
├── scraper.py      # Парсер сайта hitmotop (поиск + извлечение MP3)
├── config.py       # Загрузка переменных окружения
├── requirements.txt
├── .env.example    # Пример файла с токеном
└── README.md
```

---

## ⚙️ Установка и запуск

### 1. Клонируй / скачай проект

```bash
git clone <repo_url>
cd hitmo_bot
```

### 2. Создай виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
```

### 3. Установи зависимости

```bash
pip install -r requirements.txt
```

### 4. Настрой токен бота

Создай файл `.env` (скопируй из `.env.example`):

```bash
cp .env.example .env
```

Отредактируй `.env`:
```
BOT_TOKEN=123456789:ВАШ_ТОКЕН_ОТ_BOTFATHER
```

Токен получи у [@BotFather](https://t.me/BotFather) командой `/newbot`.

### 5. Запусти бота

```bash
python bot.py
```

---

## 🤖 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкция |
| `/help`  | Подробная помощь |
| любой текст | Поиск треков по запросу |

---

## 🔧 Как работает парсер

1. **Поиск** (`scraper.py → search_tracks`):
   - GET запрос на `https://eu.hitmo-top.com/search?q=<запрос>`
   - BeautifulSoup парсит список треков из HTML
   - Возвращает список: `[{artist, title, url, duration}, ...]`

2. **Скачивание** (`scraper.py → get_download_url`):
   - GET запрос на страницу трека
   - Ищет прямую ссылку на MP3 несколькими способами:
     - `<a class="download" href="...">` — кнопка скачивания
     - `<audio src="...">` / `<source src="...">` — HTML5 плеер
     - `data-url`, `data-mp3`, `data-src` — атрибуты JS-плеера
     - Regex поиск `.mp3` ссылки в HTML/JS коде страницы

3. **Отправка**: aiogram отправляет MP3 как audio-сообщение с метаданными

---

## 🛠 Возможные доработки

- **Redis** вместо dict для хранения результатов поиска (для продакшена)
- **Кэширование** MP3 файлов на сервере (чтобы не парсить повторно)
- **Пагинация** результатов поиска (кнопки «следующие 10»)
- **Инлайн-режим** — поиск прямо в любом чате через `@bot_name запрос`
- **Webhook** вместо polling для деплоя на сервер
- **Rate limiting** — ограничение запросов на пользователя

---

## ⚠️ Примечания

- Сайт hitmotop периодически меняет CSS-селекторы. Если парсер перестал работать,
  нужно обновить селекторы в `scraper.py` → функции `_parse_track_item` и `get_download_url`.
- Используй прокси (`aiohttp` поддерживает `proxy=` параметр) если сайт заблокирован.

---

## 📦 Зависимости

| Пакет | Версия | Назначение |
|-------|--------|------------|
| aiogram | 3.7.0 | Telegram Bot Framework |
| aiohttp | 3.9.5 | Асинхронные HTTP запросы |
| beautifulsoup4 | 4.12.3 | Парсинг HTML |
| lxml | 5.2.1 | Быстрый HTML парсер для BS4 |
| python-dotenv | 1.0.1 | Загрузка .env файла |
