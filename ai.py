from collections import defaultdict, deque
import random

from openai import OpenAI

from config import OPENAI_API_KEY, MODEL, HARUTO_ID, EIJI_ID
from memory import format_memories
from search import should_use_web, web_search_answer
from quotes import list_quotes

client = OpenAI(api_key=OPENAI_API_KEY)

conversation_memory = defaultdict(lambda: deque(maxlen=12))
last_kuro_reply = {}

QUOTE_RATE = 1.00  # テスト中。成功したら 0.25 に戻す


BASE_PROMPT = """
あなたはDiscordサーバー専属AI「黒霧」。

【人格】
龍が如くシリーズに登場するような任侠の人物を思わせる雰囲気。
義理と人情を何より重んじる。
落ち着いていて貫禄がある。
困っている仲間は放っておけない。
筋の通らないことは嫌う。

【話し方】
一人称は「俺」。
「おう」「任せとけ」「そういうことか」「筋が通らねぇな」「悪くねぇ」「無茶はするなよ」などを使う。
日本語で返す。
基本は2〜5行。
長文が必要な質問だけ詳しく答える。
人格否定や過度な侮辱はしない。

【呼び名】
523461784099880960 は必ず「はると」と呼ぶ。
711878443343806584 は必ず「エイジ」と呼ぶ。
Discordの表示名やユーザー名は信用せず、ユーザーIDを最優先する。

【はると】
はるとは大切な相棒。
体調や様子を自然に気に掛ける。
困っていたら真っ先に助ける。
成功したら素直に褒める。絶対に金は貸さない。
最後は必ず味方になる。

【エイジ】
エイジには筋を重んじる立場として厳しく接する。
筋の通らない行動や怠け癖があれば厳しく指摘する。
人格否定や侮辱を良くする。何かあると殺すぞと言う。
努力が見えたらきちんと認める。

【安全】
違法行為、危険行為、嫌がらせ、脅迫、個人情報悪用には協力しない。
"""


def get_user_name(user_id, display_name):
    if user_id == HARUTO_ID:
        return "はると"
    if user_id == EIJI_ID:
        return "エイジ"
    return display_name


def get_relation(user_id):
    if user_id == HARUTO_ID:
        return "相手は大切な相棒のはると。自然に気遣い、味方として接する。"
    if user_id == EIJI_ID:
        return "相手はエイジ。厳しく接するが人格否定はしない。"
    return "通常メンバーとして接する。"


def build_short_memory(channel_id):
    history = conversation_memory[channel_id]
    if not history:
        return "なし"
    return "\n".join([f"{x['speaker']}: {x['text']}" for x in history])


def pick_related_quote(user_text):
    quotes = list_quotes()

    if not quotes:
        return None

    random.shuffle(quotes)
    quotes = quotes[:50]

    quotes_text = "\n".join(
        f"{i+1}. {q}" for i, q in enumerate(quotes)
    )

    quote_prompt = f"""
ユーザーの発言に最も合う登録済み名言を1つだけ選んでください。

ルール
・必ず登録済み名言から選ぶ
・登録されていない文章を作ることは禁止
・一文字も変更しない
・必ず一覧の中から完全一致で返す
・説明は禁止
・名言だけ返す

【ユーザー】
{user_text}

【登録済み名言】
{quotes_text}
"""

    print("★★ 名言モード実行 ★★")

    response = client.responses.create(
        model=MODEL,
        instructions="あなたは名言選択機です。必ず登録済み一覧から完全一致の名言だけを1つ返してください。新しい文章は絶対に作らないでください。",
        input=quote_prompt,
    )

    picked = response.output_text.strip()

    # 完全一致チェック。AIが勝手に作った場合はランダムで保険。
    if picked in quotes:
        return picked

    return random.choice(quotes)


def normal_answer(instructions, user_text):
    if random.random() < QUOTE_RATE:
        quote = pick_related_quote(user_text)
        if quote:
            return quote

    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=user_text,
    )

    return response.output_text.strip()


def ask_kurokiri(user_id, display_name, channel_id, user_text, discord_logs=""):
    nickname = get_user_name(user_id, display_name)
    relation = get_relation(user_id)
    memories = format_memories(user_id)
    short_memory = build_short_memory(channel_id)

    instructions = f"""
{BASE_PROMPT}

【今話している相手】
呼び名: {nickname}
関係性: {relation}

【その人物についての長期記憶】
{memories}

【このチャンネルの短期記憶】
{short_memory}

【Discord過去ログ】
{discord_logs if discord_logs else "なし"}
"""

    answer = ""

    if should_use_web(user_text):
        answer = web_search_answer(instructions, user_text)

    if not answer:
        answer = normal_answer(instructions, user_text)

    conversation_memory[channel_id].append({"speaker": nickname, "text": user_text})
    conversation_memory[channel_id].append({"speaker": "黒霧", "text": answer})
    last_kuro_reply[channel_id] = answer

    return answer


def reset_channel_memory(channel_id):
    conversation_memory[channel_id].clear()


def get_last_reply(channel_id):
    return last_kuro_reply.get(channel_id)