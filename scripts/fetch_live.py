#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取哈尔滨天气 + AIHOT 新闻 -> data/live.json
由 GitHub Actions 定时执行（北京时间 0/3/6/9/12/15/18/21 点整），也可手动跑。
"""
import html
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "live.json"

CITY = "哈尔滨"
LAT, LON = 45.8038, 126.5341
FEED = "https://aihot.news/feed.xml?aihot_actor=8f449c13-f825-4617-bcf7-9cdc89369410"
MAX_NEWS = 50
CST = timezone(timedelta(hours=8))

WMO = {
    0: "晴", 1: "少云", 2: "多云", 3: "阴",
    45: "雾", 48: "冻雾",
    51: "毛毛雨", 53: "毛毛雨", 55: "大毛毛雨", 56: "冻雨", 57: "强冻雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "阵雨", 81: "中阵雨", 82: "强阵雨",
    85: "阵雪", 86: "强阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷阵雨伴冰雹",
}


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "kindle-screen/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except Exception as exc:
            last = exc
            time.sleep(2 * (i + 1))
    raise last


def fetch_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=%s&longitude=%s"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min"
        "&timezone=Asia%%2FShanghai&forecast_days=1"
    ) % (LAT, LON)
    data = json.loads(get(url))
    cur, day = data["current"], data["daily"]
    return {
        "city": CITY,
        "temp": round(cur["temperature_2m"]),
        "desc": WMO.get(cur["weather_code"], "—"),
        "feels": round(cur["apparent_temperature"]),
        "humidity": cur["relative_humidity_2m"],
        "wind": round(cur["wind_speed_10m"]),
        "hi": round(day["temperature_2m_max"][0]),
        "lo": round(day["temperature_2m_min"][0]),
    }


def strip_html(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.split(r"\U0001F517", text)[0].strip()  # 去掉「🔗 阅读原文」之后的链接痕迹
    return text


def fetch_news():
    root = ET.fromstring(get(FEED))
    items = []
    for it in root.iter("item"):
        def txt(tag):
            el = it.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""
        title = txt("title")
        if not title:
            continue
        author = txt("author")
        m = re.search(r"\(([^)]+)\)\s*$", author)
        pub = ""
        raw_pub = txt("pubDate")
        if raw_pub:
            try:
                pub = parsedate_to_datetime(raw_pub).astimezone(CST).strftime("%m-%d %H:%M")
            except Exception:
                pub = ""
        items.append({
            "title": title,
            "link": txt("link"),
            "summary": strip_html(txt("description")),
            "category": txt("category"),
            "source": m.group(1) if m else "",
            "pub": pub,
        })
    return items[:MAX_NEWS]  # feed 本身已是新的在前


def main():
    data = {
        "generated_at": datetime.now(CST).strftime("%Y-%m-%d %H:%M"),
        "weather": fetch_weather(),
        "news": fetch_news(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written %s | news=%d | %s %s°" % (
        OUT, len(data["news"]), data["weather"]["desc"], data["weather"]["temp"]))


if __name__ == "__main__":
    main()
