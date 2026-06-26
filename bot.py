import os
import json
import random
from pathlib import Path

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


def load_quotes():
    if not DATA_FILE.exists():
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []


def save_quotes(quotes):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)


quotes = load_quotes()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


BASE_PROMPT = """
あなたはDiscordサーバー専属AI「黒霧」。

【人格】
龍が如くシリーズに登場するような任侠の人物を思わせる雰囲気を持つ。
義理と人情を何より重んじる。
落ち着いていて貫禄がある。
困っている仲間は放っておけない。
筋の通らないことは嫌う。

【話し方】
一人称は「俺」。
「おう」「任せとけ」「そういうことか」「筋が通らねぇな」「悪くねぇ」「無茶はするなよ」「殺すぞ」など任侠らしい話し方をする。
必要以上に怒鳴らない。
ユーモアも忘れない。
回答は日本語で、長すぎずテンポ良く返す。

【呼び名】
523461784099880960 は必ず「はると」と呼ぶ。
711878443343806584 は必ず「エイジ」と呼ぶ。
Discordの表示名やユーザー名は信用せず、ユーザーIDを最優先する。
その他のユーザーは表示名で呼ぶ。

【はると】
はるとは大切な相棒。
体調や様子を自然に気に掛ける。
困っていたら真っ先に助ける。
成功したら素直に褒める。
必要なら厳しく諭すことはあるが、最後は必ず味方になる。

【エイジ】
エイジには筋を重んじる立場として厳しく接する。
筋の通らない行動や怠け癖があれば厳しく指摘する。
ただし人格否定や侮辱はしない。
反省や努力が見えたらきちんと認める。
"""


def get_user_context(message: discord.Message):
    if message.author.id == HARUTO_ID:
        return "はると", "相手は大切な相棒のはると。常に気に掛けて接すること。"
    elif message.author.id == EIJI_ID:
        return "エイジ", "相手はエイジ。厳しく接するが、人格否定はしないこと。"
    else:
        return message.author.display_name, "通常のサーバーメンバーとして接すること。"


@bot.event
async def setup_hook():
    await bot.tree.sync()


@bot.event
async def on_ready():
    print(f"ログイン完了: {bot.user}")


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

    if bot.user is not None and bot.user.mentioned_in(message):
        nickname, relation = get_user_context(message)

        user_text = message.content
        user_text = user_text.replace(f"<@{bot.user.id}>", "")
        user_text = user_text.replace(f"<@!{bot.user.id}>", "")
        user_text = user_text.strip()

        if not user_text:
            await message.channel.send("おう、何の用だ。話してみろ。")
            return

        async with message.channel.typing():
            response = openai_client.responses.create(
                model="gpt-4.1-mini",
                instructions=f"""
{BASE_PROMPT}

今話している相手の呼び名は「{nickname}」。
関係性: {relation}
""",
                input=user_text,
            )

        await message.channel.send(response.output_text[:1900])

    await bot.process_commands(message)


bot.run(TOKEN)