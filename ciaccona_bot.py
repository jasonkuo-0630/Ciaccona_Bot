import discord
from discord.ext import commands
import json
import os

# 讀取 config 檔案取得 TOKEN
def load_config():
    try:
        with open("config/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("⚠️ 找不到 config/config.json！")

# 載入 config 中的 token
config = load_config()
TOKEN = config["TOKEN"]

# 建立 bot 並開啟 intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# bot啟動時執行這段
@bot.event
async def on_ready():
    print(f"🎀 夏空上線囉！Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ 指令同步完成，共 {len(synced)} 個指令")
    except Exception as e:
        print(f"❌ 指令同步失敗：{e}")

# Ping 指令測試
@bot.tree.command(name="ping", description="測試夏空是否在線")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong！夏空在這裡等你點歌呢～🎶")

# 載入 Cogs 擴充模組
async def load_extensions():
    await bot.load_extension("cogs.music")

# 主啟動
async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())
