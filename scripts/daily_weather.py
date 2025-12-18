import os
import json
import requests
from datetime import datetime, timezone


OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY_ID = os.getenv("CITY_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CONFIG_PATH = "weather_config.json"
HISTORY_PATH = "weather_history.json"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_weather():
    # ИСПРАВЛЕННЫЙ URL - weather вместо weather2!
    url = f"https://api.openweathermap.org/data/2.5/weather?id={CITY_ID}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def pick_temperature_category(config, temp):
    categories = config["temperature_categories"]
    for name, cfg in categories.items():
        if cfg["min"] <= temp <= cfg["max"]:
            return name, cfg
    return "cool", categories["cool"]


def get_weather_emoji(config, main):
    emojis = config.get("weather_emojis", {})
    return emojis.get(main, "")


def format_message(config, weather, category_name, category_cfg):
    city_name = config["city"]["name"]
    temp = weather["main"]["temp"]
    feels_like = weather["main"]["feels_like"]
    humidity = weather["main"]["humidity"]
    wind = weather["wind"]["speed"]
    weather_main = weather["weather"][0]["main"]
    weather_desc = weather["weather"][0]["description"].capitalize()

    emoji = get_weather_emoji(config, weather_main)

    clothes_list = "- " + "\n- ".join(category_cfg["clothes"])
    activities_list = "- " + "\n- ".join(category_cfg["activities"])

    now_utc = datetime.now(timezone.utc)
    tz_offset = config["city"].get("timezone_offset", 0)
    local_time = now_utc.timestamp() + tz_offset
    local_dt = datetime.fromtimestamp(local_time)

    msg = (
        f"📅 *Ежедневный прогноз погоды*\n"
        f"Город: *{city_name}*\n"
        f"Время: {local_dt.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"Погода: *{weather_desc}* {emoji}\n"
        f"Температура: *{temp:.1f}°C* (ощущается как {feels_like:.1f}°C)\n"
        f"Влажность: {humidity}%\n"
        f"Ветер: {wind:.1f} м/с\n\n"
        f"Категория температуры: *{category_name}*\n\n"
        f"👕 Рекомендации по одежде:\n{clothes_list}\n\n"
        f"🏃 Идеи для активности:\n{activities_list}"
    )
    return msg


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    resp = requests.post(url, data=data, timeout=15)
    resp.raise_for_status()


def update_history(weather):
    history = load_json(HISTORY_PATH, {"last_update": "", "history": []})

    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    temp = weather["main"]["temp"]

    record = {
        "timestamp": now,
        "temp": temp,
        "weather_main": weather["weather"][0]["main"],
        "weather_description": weather["weather"][0]["description"],
        "humidity": weather["main"]["humidity"],
        "wind": weather["wind"]["speed"]
    }

    history["last_update"] = now
    history["history"].append(record)

    save_json(HISTORY_PATH, history)


def main():
    if not (OPENWEATHER_API_KEY and CITY_ID and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        raise RuntimeError("Не заданы все переменные окружения с секретами.")

    config = load_json(CONFIG_PATH, {})
    if not config:
        raise RuntimeError("Файл weather_config.json не найден или пуст.")

    weather = get_weather()
    temp = weather["main"]["temp"]
    category_name, category_cfg = pick_temperature_category(config, temp)
    message = format_message(config, weather, category_name, category_cfg)

    send_telegram_message(message)
    update_history(weather)


if __name__ == "__main__":
    main()