import os
import time
from urllib.parse import urljoin, urlparse

import psycopg2
import requests
from bs4 import BeautifulSoup

# === CONFIG: CHANGE THESE TO MATCH YOUR SITE ===
BASE_URL = "https://www.blacktowhite.net/"
START_URL = https://www.blacktowhite.net/fucking-videos/  # starting page that links to videos
ALLOWED_DOMAIN = urlparse(BASE_URL).netloc
MAX_PAGES = 200  # safety cap so we don't crawl forever

DATABASE_URL = os.environ.get("DATABASE_URL")

HEADERS = {
    "User-Agent": "VideoIndexerBot/1.0 (respecting robots.txt; contact: you@example.com)"
}


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            id SERIAL PRIMARY KEY,
            title TEXT,
            page_url TEXT,
            mp4_url TEXT,
            description TEXT,
            UNIQUE(page_url, mp4_url)
        )
        """
    )
    conn.commit()
    conn.close()


def save_video(title, page_url, mp4_url, description=""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO videos (title, page_url, mp4_url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (page_url, mp4_url) DO NOTHING
        """,
        (title, page_url, mp4_url, description),
    )
    conn.commit()
    conn.close()


def get_page(url):
    print(f"Fetching {url}")
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def is_same_domain(url):
    parsed = urlparse(url)
    # Empty netloc = relative URL (same domain)
    return parsed.netloc == "" or parsed.netloc == ALLOWED_DOMAIN


def crawl():
    init_db()

    to_visit = [START_URL]
    visited = set()
    pages_count = 0

    while to_visit and pages_count < MAX_PAGES:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)
        pages_count += 1

        try:
            html = get_page(url)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            continue

        soup = BeautifulSoup(html, "html.parser")

        # === FIND VIDEOS VIA <video> OR <source> TAGS ===
        for video_tag in soup.find_all(["video", "source"]):
            src = video_tag.get("src")
            if src and src.endswith(".mp4"):
                mp4_url = urljoin(url, src)  # keep MP4 exactly as is
                # Add /lightbox to the original page URL
                page_url = url.rstrip("/") + "/lightbox"
                title = (soup.title.string.strip() if soup.title else "Untitled")
                save_video(title, page_url, mp4_url)

        # === FIND DIRECT LINKS TO .mp4 FILES ===
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.endswith(".mp4"):
                mp4_url = urljoin(url, href)  # keep MP4 as is
                page_url = url.rstrip("/") + "/lightbox"
                link_text = a.get_text(strip=True)
                title = link_text or (soup.title.string.strip() if soup.title else "Untitled")
                save_video(title, page_url, mp4_url)

        # === DISCOVER MORE INTERNAL PAGES TO CRAWL ===
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(url, href)
            if is_same_domain(full_url) and full_url.startswith(BASE_URL):
                if full_url not in visited and full_url not in to_visit:
                    to_visit.append(full_url)

        # Be polite to the server
        time.sleep(0.5)


if __name__ == "__main__":
    crawl()
    print("Crawl complete.")
