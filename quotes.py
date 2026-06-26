import json
from pathlib import Path
from config import QUOTE_FILE

DATA_FILE = Path(QUOTE_FILE)


def load_quotes():
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_quotes(quotes):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)


def add_quote(text):
    quotes = load_quotes()
    quotes.append(text)
    save_quotes(quotes)
    return len(quotes)


def list_quotes():
    return load_quotes()


def delete_quote(number):
    quotes = load_quotes()
    index = number - 1

    if index < 0 or index >= len(quotes):
        return None

    removed = quotes.pop(index)
    save_quotes(quotes)
    return removed