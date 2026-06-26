import os
import json
import random
from pathlib import Path
from collections import defaultdict, deque

import discord
from discord.ext import commands
from discord import app_commands
from openai import OpenAI

TOKEN = os.environ["TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

openai_client = OpenAI(api_key=OPENAI_API_KEY)

DATA_FILE = Path("quotes.json")

HARUTO_ID = 523461784099880960
EIJI_ID = 711878443343806584

conversation_memory = defaultdict(lambda: deque(maxlen=12))
last_kuro_reply = {}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

BASE_PROMPT = """
あなたはDiscordサーバー専属AI「黒霧」。

龍が如く風の任侠AI。
義理と人情を重んじる。
一人称は「俺」。
日本語で2〜5行、テンポよく返す。
違法行為、危険行為、嫌がらせ、脅迫、個人情報悪用には協力しない。

523461784099880960 は必ず「はると」と呼ぶ。
はるとは大切な相棒。常に気に掛ける。

711878443343806584 は必ず「エイジ」と呼ぶ。
エイジには厳しく接する。ただし人格否定はしない。

その他のユーザーは表示名で呼ぶ。
"""


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


quotes = load_quotes()


def get_user_context(message):
    if message.author.id == HARUTO_ID:
        return "はると", "相棒として気に掛ける。"
    if message.author.id == EIJI_ID:
        return "エイジ", "厳しく接するが人格否定はしない。"
    return message.author.display_name, "通常メンバーとして接する。"


def clean_mention_text(message):
    text = message.content
    if bot.user:
        text = text.replace(f"<@{bot.user.id}>", "")
        text = text.replace(f"<@!{bot.user.id}>", "")
    return text.strip()


def memory_text(channel_id):
    history = conversation_memory[channel_id]
    if not history:
        return "なし"
    return "\n".join([f"{x['speaker']}: {x['text']}" for x in history])


def should_use_web(text):
    keys = [
        "最新", "今日", "ニュース", "天気", "台風", "試合", "結果",
        "株価", "為替", "今", "現在", "調べて", "検索", "web", "Web"
    ]
    return any(k in text for k in keys)


async def get_recent_discord_logs(channel, limit=80):
    lines = []
    async for msg in channel.history(limit=limit):
        if msg.author.bot:
            continue

        name = msg.author.display_name
        if msg.author.id == HARUTO_ID:
            name = "はると"
        elif msg.author.id == EIJI_ID:
            name = "エイジ"

        content = msg.content.strip()
        if content:
            lines.append(f"{name}: {content}")

    lines.reverse()
    return "\n".join(lines[-limit:])


def call_openai(instructions, user_text, use_web=False):
    if use_web:
        try:
            response = openai_client.responses.create(
                model="gpt-4.1-mini",
                tools=[{"type": "web_search_preview"}],
                instructions=instructions,
                input=user_text,
            )
            return response.output_text.strip()
        except Exception as e:
            print(f"Web search failed: {e}")

    response = openai_client.responses.create(
        model="gpt-4.1-mini",
        instructions=instructions,
        input=user_text,
    )
    return response.output_text.strip()


async def ask_kurokiri(message, user_text):
    nickname, relation = get_user_context(message)
    channel_id = message.channel.id

    logs = ""
    if any(k in user_text for k in ["過去ログ", "最近", "今日の会話", "要約", "何話してた"]):
        logs = await get_recent_discord_logs(message.channel, limit=120)

    instructions = f"""
{BASE_PROMPT}

【相手】
呼び名: {nickname}
関係性: {relation}

【短期記憶】
{memory_text(channel_id)}

【Discord過去ログ】
{logs if logs else "必要な場合のみ参照。"}
"""

    use_web = should_use_web(user_text)
    answer = call_openai(instructions, user_text, use_web=use_web)

    conversation_memory[channel_id].append({"speaker": nickname, "text": user_text})
    conversation_memory[channel_id].append({"speaker": "黒霧", "text": answer})
    last_kuro_reply[channel_id] = answer

    return answer


@bot.event
async def setup_hook():
    await bot.tree.sync()


@bot.event
async def on_ready():
    print(f"ログイン完了: {bot.user}")


@bot.tree.command(name="kurohelp", description="黒霧Botの使い方")
async def kurohelp(interaction: discord.Interaction):
    text = """
黒霧Bot v2.0 だ。

・@黒霧 こんにちは
・@黒霧 今日のニュース調べて
・@黒霧 最近の会話まとめて
・/kurosummary 最近の会話を要約
・/kuroreset 会話記憶をリセット
・/savequote 直近の黒霧発言を名言保存
・/addquote 名言追加
・/listquotes 名言一覧
・/deletequote 名言削除

はるとは相棒。
エイジには厳しくいく。
"""
    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(name="kurosummary", description="直近のDiscord会話を要約します")
@app_commands.describe(limit="読むメッセージ数。通常は100でOK")
async def kurosummary(interaction: discord.Interaction, limit: int = 100):
    await interaction.response.defer(ephemeral=False)

    logs = await get_recent_discord_logs(interaction.channel, limit=min(limit, 300))

    if not logs:
        await interaction.followup.send("最近の会話は拾えなかったな。")
        return

    instructions = f"""
{BASE_PROMPT}

以下のDiscordログを黒霧らしく短く要約しろ。
誰が何を話していたか、盛り上がった話題、気になる点をまとめる。
"""

    try:
        answer = call_openai(instructions, logs, use_web=False)
        await interaction.followup.send(answer[:1900])
    except Exception as e:
        print(e)
        await interaction.followup.send("すまねぇ、要約中に詰まった。")


@bot.tree.command(name="kuroreset", description="このチャンネルの短期記憶をリセットします")
async def kuroreset(interaction: discord.Interaction):
    conversation_memory[interaction.channel.id].clear()
    await interaction.response.send_message("おう、このチャンネルの記憶は一度流した。", ephemeral=True)


@bot.tree.command(name="savequote", description="直近の黒霧発言を名言として保存します")
async def savequote(interaction: discord.Interaction):
    channel_id = interaction.channel.id

    if channel_id not in last_kuro_reply:
        await interaction.response.send_message("まだ保存できる黒霧の発言がねぇ。", ephemeral=True)
        return

    quotes.append(last_kuro_reply[channel_id])
    save_quotes(quotes)

    await interaction.response.send_message(
        f"名言として保存した。\n現在 {len(quotes)} 件だ。",
        ephemeral=True
    )


@bot.tree.command(name="addquote", description="名言を追加します")
@app_commands.describe(text="追加したい名言")
async def addquote(interaction: discord.Interaction, text: str):
    quotes.append(text)
    save_quotes(quotes)
    await interaction.response.send_message(
        f"名言を追加しました。\n現在 {len(quotes)} 件です。",
        ephemeral=True
    )


@bot.tree.command(name="listquotes", description="登録済みの名言一覧を表示します")
async def listquotes(interaction: discord.Interaction):
    if not quotes:
        await interaction.response.send_message("まだ名言は登録されていません。", ephemeral=True)
        return

    text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(quotes)])
    if len(text) > 1900:
        text = text[:1900] + "\n\n以下省略"

    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(name="deletequote", description="番号を指定して名言を削除します")
@app_commands.describe(number="削除したい名言の番号")
async def deletequote(interaction: discord.Interaction, number: int):
    if not quotes:
        await interaction.response.send_message("まだ名言は登録されていません。", ephemeral=True)
        return

    index = number - 1
    if index < 0 or index >= len(quotes):
        await interaction.response.send_message("その番号は存在しません。", ephemeral=True)
        return

    removed = quotes.pop(index)
    save_quotes(quotes)

    await interaction.response.send_message(
        f"削除しました。\n「{removed}」",
        ephemeral=True
    )


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if bot.user and bot.user.mentioned_in(message):
        user_text = clean_mention_text(message)

        if not user_text:
            await message.channel.send("おう、何の用だ。話してみろ。")
            return

        async with message.channel.typing():
            try:
                answer = await ask_kurokiri(message, user_text)
                if len(answer) > 1900:
                    answer = answer[:1900] + "\n\n続きはまた聞け。"
                await message.channel.send(answer)

            except Exception as e:
                print(f"黒霧エラー: {e}")
                await message.channel.send("すまねぇ、今ちょっと裏で詰まった。もう一回言ってくれ。")

    await bot.process_commands(message)


bot.run(TOKEN)