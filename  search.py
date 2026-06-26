from openai import OpenAI
from config import OPENAI_API_KEY, MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


def should_use_web(text: str) -> bool:
    keywords = [
        "最新", "今日", "ニュース", "天気", "台風", "試合", "結果",
        "株価", "為替", "今", "現在", "調べて", "検索", "web", "Web"
    ]
    return any(k in text for k in keywords)


def web_search_answer(instructions: str, query: str) -> str:
    try:
        response = client.responses.create(
            model=MODEL,
            tools=[{"type": "web_search_preview"}],
            instructions=instructions,
            input=query,
        )
        return response.output_text.strip()
    except Exception as e:
        print(f"Web search error: {e}")
        return ""