import os
import json
from datetime import datetime, timedelta

import requests


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CONFIG_PATH = "weather_config.json"
HISTORY_PATH = "weather_history.json"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    resp = requests.post(url, data=data, timeout=15)
    resp.raise_for_status()


def main():
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        raise RuntimeError("Не заданы переменные окружения TELEGRAM_*.")

    config = load_json(CONFIG_PATH, {})
    history = load_json(HISTORY_PATH, {"last_update": "", "history": []})
    city_name = config.get("city", {}).get("name", "Город")

    records = history.get("history", [])

    if len(records) < 3:
        send_telegram_message(
            "📊 Еженедельный отчёт по погоде\n\n"
            "Пока недостаточно данных для анализа недели. "
            "Подождите ещё несколько ежедневных обновлений."
        )
        return

    # Берём данные за последние 7 дней
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    week_records = []
    for rec in records:
        try:
            ts = datetime.strptime(rec["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            continue
        if ts >= week_ago:
            week_records.append(rec)

    if not week_records:
        send_telegram_message(
            "📊 Еженедельный отчёт по погоде\n\n"
            "За последнюю неделю нет данных."
        )
        return

    temps = [r["temp"] for r in week_records]
    avg_temp = sum(temps) / len(temps)
    min_temp = min(temps)
    max_temp = max(temps)

    if avg_temp >= 20:
        summary = "Неделя была в целом тёплой и комфортной."
    elif avg_temp >= 10:
        summary = "Неделя была умеренно прохладной."
    elif avg_temp >= 0:
        summary = "Неделя была прохладной, иногда холодной."
    else:
        summary = "Неделя была холодной, возможны морозы."

    if max_temp >= 25:
        recommendation = "Готовьтесь к более тёплой погоде: не забывайте про лёгкую одежду и воду."
    elif min_temp <= -5:
        recommendation = "Ожидается прохладная или холодная погода: держите тёплую одежду под рукой."
    else:
        recommendation = "Сильных перепадов температуры не ожидается, подойдёт стандартная одежда по сезону."

    msg = (
        f"📊 *Еженедельный отчёт о погоде*\n"
        f"Город: *{city_name}*\n\n"
        f"Период: последние 7 дней\n"
        f"Средняя температура: *{avg_temp:.1f}°C*\n"
        f"Минимальная: {min_temp:.1f}°C\n"
        f"Максимальная: {max_temp:.1f}°C\n\n"
        f"Общая характеристика:\n{summary}\n\n"
        f"Рекомендации на следующую неделю:\n{recommendation}"
    )

    send_telegram_message(msg)


if __name__ == "__main__":
    main()
