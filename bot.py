import json
import random
import os
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands

# ここにDeveloper PortalでコピーしたBot Tokenを入れる
TOKEN =  os.environ["TOKEN"]
# 名言を保存するファイル
DATA_FILE = Path("quotes.json")


def load_quotes():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError:
            return []


def save_quotes(quotes):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)


quotes = load_quotes()

intents = discord.Intents.default()
# 今回は「メンションされたときだけ反応」なので message_content intent なしで動く構成
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def setup_hook():
    # slash command をDiscordへ同期
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
        await interaction.response.send_message(
            "まだ名言は登録されていません。",
            ephemeral=True
        )
        return

    lines = [f"{i+1}. {q}" for i, q in enumerate(quotes)]
    text = "\n".join(lines)

    # 長すぎる場合に備えて分割
    if len(text) > 1900:
        text = text[:1900] + "\n\n以下省略"
    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(name="deletequote", description="番号を指定して名言を削除します")
@app_commands.describe(number="削除したい名言の番号")
async def deletequote(interaction: discord.Interaction, number: int):
    if not quotes:
        await interaction.response.send_message(
            "まだ名言は登録されていません。",
            ephemeral=True
        )
        return

    index = number - 1
    if index < 0 or index >= len(quotes):
        await interaction.response.send_message(
            "その番号は存在しません。",
            ephemeral=True
        )
        return

    removed = quotes.pop(index)
    save_quotes(quotes)
    await interaction.response.send_message(
        f"削除しました。\n「{removed}」",
        ephemeral=True
    )


@bot.event
async def on_message(message: discord.Message):
    global quotes

    # Bot自身や他Botには反応しない
    if message.author.bot:
        return

    # 黒霧botがメンションされた時だけ反応
    if bot.user is not None and bot.user.mentioned_in(message):
        quotes = load_quotes()

        if not quotes:
            await message.channel.send("まだ名言が登録されていません。 /addquote で追加してください。")
            return

        picked = random.choice(quotes)
        await message.channel.send(picked)

    # 他のコマンド処理も通す
    await bot.process_commands(message)


bot.run(TOKEN)
