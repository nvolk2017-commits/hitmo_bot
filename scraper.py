import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

BASE_URL = "https://eu.hitmo-top.com"
SEARCH_URL = f"{BASE_URL}/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": BASE_URL,
}


async def search_tracks(query: str) -> list[dict]:
    """
    Ищет треки по запросу на hitmotop.
    Возвращает список словарей: {artist, title, url, duration}
    """
    params = {"q": query}

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning(f"Search returned status {resp.status}")
                    return []
                html = await resp.text()
        except asyncio.TimeoutError:
            logger.error("Search request timed out")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"Search request failed: {e}")
            return []

    soup = BeautifulSoup(html, "html.parser")
    tracks = []

    # hitmotop использует теги <li class="song-item"> или аналогичные
    # Пробуем несколько возможных селекторов
    items = (
        soup.select("ul.song-list li.song-item")
        or soup.select("li.song-item")
        or soup.select(".track-list .track-item")
        or soup.select("li[data-id]")
    )

    for item in items:
        try:
            track = _parse_track_item(item)
            if track:
                tracks.append(track)
        except Exception as e:
            logger.debug(f"Error parsing track item: {e}")
            continue

    logger.info(f"Found {len(tracks)} tracks for query: {query!r}")
    return tracks


def _parse_track_item(item) -> dict | None:
    """Парсит один элемент трека из HTML."""
    # Заголовок трека
    title_el = (
        item.select_one(".song-name")
        or item.select_one(".track-name")
        or item.select_one("strong")
        or item.select_one(".title")
    )

    # Исполнитель
    artist_el = (
        item.select_one(".song-artist")
        or item.select_one(".track-artist")
        or item.select_one(".artist")
        or item.select_one("span.name")
    )

    # Ссылка на страницу трека
    link_el = item.select_one("a[href]")

    if not link_el:
        return None

    href = link_el.get("href", "")
    if not href:
        return None

    # Нормализуем URL
    if href.startswith("http"):
        track_url = href
    else:
        track_url = BASE_URL + href

    # Длительность (опционально)
    duration_el = item.select_one(".song-duration") or item.select_one(".duration")
    duration = duration_el.get_text(strip=True) if duration_el else ""

    # Извлекаем имена
    if title_el and artist_el:
        title = title_el.get_text(strip=True)
        artist = artist_el.get_text(strip=True)
    elif title_el:
        # Пробуем разбить "Исполнитель - Трек"
        full = title_el.get_text(strip=True)
        parts = full.split(" - ", 1)
        if len(parts) == 2:
            artist, title = parts
        else:
            artist = "Unknown"
            title = full
    else:
        # Берём текст ссылки
        full = link_el.get_text(strip=True)
        parts = full.split(" - ", 1)
        if len(parts) == 2:
            artist, title = parts
        else:
            artist = "Unknown"
            title = full

    if not title:
        return None

    return {
        "artist": artist.strip(),
        "title": title.strip(),
        "url": track_url,
        "duration": duration,
    }


async def get_download_url(track_page_url: str) -> str | None:
    """
    Заходит на страницу трека и извлекает прямую ссылку на MP3.
    hitmotop хранит ссылку в теге <a class="download"> или data-атрибуте плеера.
    """
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(track_page_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning(f"Track page returned status {resp.status}")
                    return None
                html = await resp.text()
        except asyncio.TimeoutError:
            logger.error("Track page request timed out")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Track page request failed: {e}")
            return None

    soup = BeautifulSoup(html, "html.parser")

    # Попытка 1: кнопка скачивания <a class="download" href="...">
    dl_link = (
        soup.select_one("a.download[href]")
        or soup.select_one("a[download][href]")
        or soup.select_one("a.btn-download[href]")
        or soup.select_one(".download-btn a[href]")
    )
    if dl_link:
        href = dl_link.get("href", "")
        if href and ".mp3" in href:
            return href if href.startswith("http") else BASE_URL + href

    # Попытка 2: HTML5 аудио-плеер <audio src="..."> или <source src="...">
    audio_el = soup.select_one("audio[src]")
    if audio_el:
        src = audio_el.get("src", "")
        if src:
            return src if src.startswith("http") else BASE_URL + src

    source_el = soup.select_one("audio source[src]")
    if source_el:
        src = source_el.get("src", "")
        if src:
            return src if src.startswith("http") else BASE_URL + src

    # Попытка 3: data-атрибут плеера
    player_el = soup.select_one("[data-url]") or soup.select_one("[data-mp3]") or soup.select_one("[data-src]")
    if player_el:
        for attr in ("data-url", "data-mp3", "data-src"):
            val = player_el.get(attr, "")
            if val and (".mp3" in val or "audio" in val):
                return val if val.startswith("http") else BASE_URL + val

    # Попытка 4: поиск .mp3 ссылки в JS/HTML
    mp3_match = re.search(r'(https?://[^\s"\'<>]+\.mp3)', html)
    if mp3_match:
        return mp3_match.group(1)

    logger.warning(f"Could not find MP3 URL on page: {track_page_url}")
    return None
