import os
import json
from datetime import datetime, timezone

import requests


OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY_ID = os.getenv("CITY_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CONFIG_PATH = "weather_config.json"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_weather():
    url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"id={CITY_ID}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    resp = requests.post(url, data=data, timeout=15)
    resp.raise_for_status()


def check_alerts(weather):
    temp = weather["main"]["temp"]
    wind = weather["wind"]["speed"]
    weather_main = weather["weather"][0]["main"]
    weather_desc = weather["weather"][0]["description"]

    alerts = []

    if temp >= 30:
        alerts.append("Сильная жара (температура выше 30°C). Избегайте длительного пребывания на солнце.")
    if temp <= -15:
        alerts.append("Сильный мороз (температура ниже -15°C). Одевайтесь как можно теплее.")
    if wind >= 15:
        alerts.append("Сильный ветер (более 15 м/с). Будьте осторожны на улице.")
    if weather_main == "Thunderstorm":
        alerts.append("Гроза. Старайтесь не находиться на открытой местности.")
    if weather_main == "Snow":
        alerts.append("Сильный снегопад возможен. Будьте осторожны на дороге и при ходьбе.")

    return alerts, temp, wind, weather_desc


def main():
    if not (OPENWEATHER_API_KEY and CITY_ID and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        raise RuntimeError("Не заданы все переменные окружения с секретами.")

    config = load_json(CONFIG_PATH, {})
    city_name = config.get("city", {}).get("name", "Город")
    tz_offset = config.get("city", {}).get("timezone_offset", 0)

    weather = get_weather()
    alerts, temp, wind, desc = check_alerts(weather)

    now_utc = datetime.now(timezone.utc)
    local_time = now_utc.timestamp() + tz_offset
    local_dt = datetime.fromtimestamp(local_time)

    if alerts:
        header = (
            f"🚨 *Экстренное погодное предупреждение!*\n"
            f"Город: *{city_name}*\n"
            f"Время: {local_dt.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Текущая погода: {desc.capitalize()}, {temp:.1f}°C, ветер {wind:.1f} м/с.\n\n"
            f"Опасные условия:\n"
        )
        alerts_text = "- " + "\n- ".join(alerts)
        send_telegram_message(header + alerts_text)
    else:
        msg = (
            f"✅ *Погодные условия в норме*\n"
            f"Город: *{city_name}*\n"
            f"Время: {local_dt.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Текущая погода: {desc.capitalize()}, {temp:.1f}°C, ветер {wind:.1f} м/с.\n\n"
            f"Серьёзных погодных угроз не обнаружено."
        )
        send_telegram_message(msg)


if __name__ == "__main__":
    main()
