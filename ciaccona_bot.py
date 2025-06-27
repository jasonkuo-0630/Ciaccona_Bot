import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設定機器人的 intents（權限意圖）
intents = discord.Intents.default()
intents.message_content = True  # 讀取訊息內容
intents.voice_states = True     # 語音狀態變更

# 建立機器人實例
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """機器人啟動時執行"""
    print(f'🎵 {bot.user} (夏空) 已經上線了！')
    print(f'機器人 ID: {bot.user.id}')
    print('-------------------')
    
    # 同步斜線指令
    try:
        synced = await bot.tree.sync()
        print(f'✅ 同步了 {len(synced)} 個斜線指令')
    except Exception as e:
        print(f'❌ 同步指令失敗: {e}')

@bot.event
async def on_guild_join(guild):
    """機器人加入伺服器時"""
    print(f'🏠 夏空加入了新的伺服器: {guild.name}')

@bot.event
async def on_command_error(ctx, error):
    """處理指令錯誤"""
    if isinstance(error, commands.CommandNotFound):
        return  # 忽略找不到指令的錯誤
    
    print(f'發生錯誤: {error}')

# ===== 載入 Cogs =====
async def load_cogs():
    """載入所有 cog 模組"""
    cogs_to_load = [
        'cogs.music',      # 音樂功能
        # 'cogs.admin',    # 管理功能（之後可以加）
        # 'cogs.fun',      # 娛樂功能（之後可以加）
    ]
    
    for cog in cogs_to_load:
        try:
            await bot.load_extension(cog)
            print(f'✅ 成功載入: {cog}')
        except Exception as e:
            print(f'❌ 載入失敗 {cog}: {e}')

# ===== 基本指令（保留在主程式） =====

@bot.tree.command(name="hello", description="和夏空打招呼")
async def hello(interaction: discord.Interaction):
    """測試指令"""
    await interaction.response.send_message(f"你好！我是夏空 🌤️\n很高興見到你，{interaction.user.mention}！")

@bot.tree.command(name="ping", description="檢查機器人延遲")
async def ping(interaction: discord.Interaction):
    """檢查機器人回應時間"""
    latency = round(bot.latency * 1000)  # 轉換為毫秒
    await interaction.response.send_message(f"🏓 Pong! 延遲: {latency}ms")

@bot.tree.command(name="reload", description="重新載入音樂模組（開發用）")
async def reload_music(interaction: discord.Interaction):
    """重新載入音樂 cog（方便開發時測試）"""
    try:
        await bot.reload_extension('cogs.music')
        await interaction.response.send_message("🔄 音樂模組重新載入成功！")
    except Exception as e:
        await interaction.response.send_message(f"❌ 重新載入失敗: {e}")

# ===== 啟動機器人 =====
async def main():
    """主要啟動函數"""
    print("正在啟動夏空機器人...")
    
    # 載入所有 cogs
    await load_cogs()
    
    # 啟動機器人
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if not TOKEN:
        print("❌ 找不到 Discord Token！請檢查 .env 檔案")
        return
    
    try:
        await bot.start(TOKEN)
    except discord.LoginFailure:
        print("❌ Token 無效！請檢查你的機器人 Token")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")

if __name__ == "__main__":
    asyncio.run(main())