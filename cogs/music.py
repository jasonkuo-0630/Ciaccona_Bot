import discord
from discord.ext import commands
import asyncio
import yt_dlp
import os
import functools

# YouTube 下載器設定
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # 綁定到 ipv4，因為 ipv6 可能會有問題
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    """YouTube 音訊來源"""
    
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.uploader = data.get('uploader')

    @classmethod
    async def create_source(cls, search: str, *, loop=None, volume=0.5):
        """建立音訊來源"""
        loop = loop or asyncio.get_event_loop()
        
        # 在執行緒中運行 yt-dlp（避免阻塞）
        data = await loop.run_in_executor(
            None, 
            lambda: ytdl.extract_info(f"ytsearch:{search}", download=False)
        )
        
        if 'entries' in data:
            # 取得搜尋結果的第一個
            data = data['entries'][0]
        
        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, volume=volume)

    @classmethod
    async def get_info(cls, search: str, *, loop=None):
        """取得影片資訊（不下載）"""
        loop = loop or asyncio.get_event_loop()
        
        data = await loop.run_in_executor(
            None, 
            lambda: ytdl.extract_info(f"ytsearch:{search}", download=False)
        )
        
        if 'entries' in data:
            data = data['entries'][0]
        
        return {
            'title': data.get('title', 'Unknown'),
            'url': data.get('webpage_url', data.get('url')),
            'duration': data.get('duration', 0),
            'thumbnail': data.get('thumbnail'),
            'uploader': data.get('uploader', 'Unknown')
        }

class MusicQueue:
    """音樂佇列管理"""
    
    def __init__(self):
        self.queue = []
        self.current = None
        self.loop_mode = False  # 單曲循環
        self.volume = 0.5

    def add(self, item):
        """加入佇列"""
        self.queue.append(item)

    def get_next(self):
        """取得下一首歌"""
        if self.loop_mode and self.current:
            return self.current
        
        if self.queue:
            self.current = self.queue.pop(0)
            return self.current
        
        self.current = None
        return None

    def clear(self):
        """清空佇列"""
        self.queue.clear()
        self.current = None

    def skip(self):
        """跳過當前歌曲"""
        if self.queue:
            self.current = self.queue.pop(0)
            return self.current
        self.current = None
        return None

class Music(commands.Cog):
    """音樂功能 Cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # 每個伺服器的音樂佇列
        
    def get_queue(self, guild_id):
        """取得或建立伺服器的音樂佇列"""
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]
        
    @commands.Cog.listener()
    async def on_ready(self):
        """當 Cog 載入完成時"""
        print("🎵 音樂模組已載入（完整版）")

    # ===== 語音頻道相關 =====
    
    @discord.app_commands.command(name="join", description="讓夏空加入你的語音頻道")
    async def join(self, interaction: discord.Interaction):
        """加入語音頻道"""
        if not interaction.user.voice:
            await interaction.response.send_message("❌ 你需要先加入一個語音頻道！", ephemeral=True)
            return
        
        channel = interaction.user.voice.channel
        
        if interaction.guild.voice_client:
            if interaction.guild.voice_client.channel == channel:
                await interaction.response.send_message("🎵 夏空已經在這個語音頻道了！", ephemeral=True)
                return
            else:
                await interaction.guild.voice_client.move_to(channel)
                await interaction.response.send_message(f"🎵 夏空移動到了 **{channel.name}**")
        else:
            await channel.connect()
            await interaction.response.send_message(f"🎵 夏空加入了 **{channel.name}**")

    @discord.app_commands.command(name="leave", description="讓夏空離開語音頻道")
    async def leave(self, interaction: discord.Interaction):
        """離開語音頻道"""
        if interaction.guild.voice_client:
            # 停止播放並清空佇列
            queue = self.get_queue(interaction.guild.id)
            queue.clear()
            
            if interaction.guild.voice_client.is_playing():
                interaction.guild.voice_client.stop()
            
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("👋 夏空已經離開語音頻道了")
        else:
            await interaction.response.send_message("❌ 夏空目前不在任何語音頻道中", ephemeral=True)

    # ===== 音樂播放相關 =====
    
    @discord.app_commands.command(name="play", description="播放音樂")
    async def play(self, interaction: discord.Interaction, *, 歌曲: str):
        """播放音樂"""
        # 檢查用戶是否在語音頻道
        if not interaction.user.voice:
            await interaction.response.send_message("❌ 你需要先加入語音頻道！", ephemeral=True)
            return
        
        # 如果機器人不在語音頻道，自動加入
        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect()
        
        # 延遲回應，因為搜尋可能需要時間
        await interaction.response.defer()
        
        try:
            # 搜尋歌曲資訊
            info = await YTDLSource.get_info(歌曲)
            
            queue = self.get_queue(interaction.guild.id)
            
            # 建立歌曲項目
            song_item = {
                'info': info,
                'search': 歌曲,
                'requester': interaction.user
            }
            
            # 如果沒有在播放，直接播放
            if not interaction.guild.voice_client.is_playing():
                queue.current = song_item
                await self._play_song(interaction.guild.voice_client, song_item, queue)
                
                embed = discord.Embed(
                    title="🎵 開始播放",
                    description=f"**{info['title']}**",
                    color=discord.Color.green()
                )
                embed.add_field(name="👤 請求者", value=interaction.user.mention, inline=True)
                embed.add_field(name="⏱️ 長度", value=self._format_duration(info['duration']), inline=True)
                
                if info['thumbnail']:
                    embed.set_thumbnail(url=info['thumbnail'])
                
                await interaction.followup.send(embed=embed)
            else:
                # 加入佇列
                queue.add(song_item)
                
                embed = discord.Embed(
                    title="📝 加入播放佇列",
                    description=f"**{info['title']}**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="👤 請求者", value=interaction.user.mention, inline=True)
                embed.add_field(name="📍 佇列位置", value=f"{len(queue.queue)}", inline=True)
                embed.add_field(name="⏱️ 長度", value=self._format_duration(info['duration']), inline=True)
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            print(f"播放錯誤: {e}")
            await interaction.followup.send(f"❌ 搜尋或播放歌曲時發生錯誤: {str(e)}")

    async def _play_song(self, voice_client, song_item, queue):
        """播放歌曲"""
        try:
            # 建立音訊來源
            source = await YTDLSource.create_source(song_item['search'], volume=queue.volume)
            
            # 播放完成後的回調函數
            def after_playing(error):
                if error:
                    print(f'播放錯誤: {error}')
                else:
                    # 播放下一首
                    asyncio.run_coroutine_threadsafe(self._play_next(voice_client, queue), self.bot.loop)
            
            voice_client.play(source, after=after_playing)
            
        except Exception as e:
            print(f"播放歌曲錯誤: {e}")

    async def _play_next(self, voice_client, queue):
        """播放下一首歌曲"""
        next_song = queue.get_next()
        if next_song and voice_client.is_connected():
            await self._play_song(voice_client, next_song, queue)

    def _format_duration(self, seconds):
        """格式化時間長度"""
        if not seconds:
            return "未知"
        
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    @discord.app_commands.command(name="queue", description="顯示播放佇列")
    async def queue_info(self, interaction: discord.Interaction):
        """顯示當前播放佇列"""
        queue = self.get_queue(interaction.guild.id)
        
        embed = discord.Embed(
            title="🎵 播放佇列",
            color=discord.Color.blue()
        )
        
        # 目前播放的歌曲
        if queue.current:
            current_info = queue.current['info']
            embed.add_field(
                name="🎵 目前播放",
                value=f"**{current_info['title']}**\n👤 {queue.current['requester'].mention}",
                inline=False
            )
        
        # 佇列中的歌曲
        if queue.queue:
            queue_text = ""
            for i, song in enumerate(queue.queue[:10]):  # 只顯示前10首
                song_info = song['info']
                queue_text += f"{i+1}. **{song_info['title']}**\n   👤 {song['requester'].mention}\n"
            
            embed.add_field(name="📝 佇列", value=queue_text or "佇列是空的", inline=False)
            
            if len(queue.queue) > 10:
                embed.set_footer(text=f"還有 {len(queue.queue) - 10} 首歌曲...")
        else:
            embed.add_field(name="📝 佇列", value="佇列是空的", inline=False)
        
        embed.add_field(name="🔁 循環模式", value="開啟" if queue.loop_mode else "關閉", inline=True)
        embed.add_field(name="🔊 音量", value=f"{int(queue.volume * 100)}%", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="skip", description="跳過目前播放的歌曲")
    async def skip(self, interaction: discord.Interaction):
        """跳過歌曲"""
        if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
            await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)
            return
        
        queue = self.get_queue(interaction.guild.id)
        
        if queue.current:
            skipped_song = queue.current['info']['title']
            interaction.guild.voice_client.stop()  # 這會觸發 after_playing 回調
            await interaction.response.send_message(f"⏭️ 跳過了：**{skipped_song}**")
        else:
            await interaction.response.send_message("❌ 沒有可跳過的歌曲", ephemeral=True)

    @discord.app_commands.command(name="stop", description="停止播放音樂")
    async def stop(self, interaction: discord.Interaction):
        """停止播放"""
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            queue = self.get_queue(interaction.guild.id)
            queue.clear()  # 清空佇列
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏹️ 音樂已停止，佇列已清空")
        else:
            await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)

    @discord.app_commands.command(name="pause", description="暫停播放")
    async def pause(self, interaction: discord.Interaction):
        """暫停播放"""
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("⏸️ 音樂已暫停")
        else:
            await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)

    @discord.app_commands.command(name="resume", description="繼續播放")
    async def resume(self, interaction: discord.Interaction):
        """繼續播放"""
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message("▶️ 音樂已繼續播放")
        else:
            await interaction.response.send_message("❌ 音樂沒有被暫停", ephemeral=True)

    @discord.app_commands.command(name="volume", description="調整音量")
    async def volume(self, interaction: discord.Interaction, 音量: int):
        """調整播放音量"""
        if not 0 <= 音量 <= 100:
            await interaction.response.send_message("❌ 音量必須在 0-100 之間！", ephemeral=True)
            return
        
        queue = self.get_queue(interaction.guild.id)
        queue.volume = 音量 / 100.0
        
        # 如果正在播放，立即調整音量
        if interaction.guild.voice_client and interaction.guild.voice_client.source:
            interaction.guild.voice_client.source.volume = queue.volume
        
        await interaction.response.send_message(f"🔊 音量設定為: {音量}%")

    @discord.app_commands.command(name="loop", description="切換單曲循環模式")
    async def loop(self, interaction: discord.Interaction):
        """切換循環模式"""
        queue = self.get_queue(interaction.guild.id)
        queue.loop_mode = not queue.loop_mode
        
        status = "開啟" if queue.loop_mode else "關閉"
        emoji = "🔁" if queue.loop_mode else "➡️"
        await interaction.response.send_message(f"{emoji} 單曲循環已{status}")

    @discord.app_commands.command(name="clear", description="清空播放佇列")
    async def clear_queue(self, interaction: discord.Interaction):
        """清空播放佇列"""
        queue = self.get_queue(interaction.guild.id)
        
        count = len(queue.queue)
        queue.queue.clear()
        
        if count > 0:
            await interaction.response.send_message(f"🗑️ 已清空播放佇列（移除了 {count} 首歌曲）")
        else:
            await interaction.response.send_message("📭 播放佇列本來就是空的！", ephemeral=True)

    @discord.app_commands.command(name="nowplaying", description="顯示目前播放的歌曲")
    async def now_playing(self, interaction: discord.Interaction):
        """顯示目前播放的歌曲"""
        queue = self.get_queue(interaction.guild.id)
        
        if not queue.current:
            await interaction.response.send_message("❌ 目前沒有在播放音樂", ephemeral=True)
            return
        
        current_info = queue.current['info']
        
        embed = discord.Embed(
            title="🎵 目前播放",
            description=f"**{current_info['title']}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="👤 請求者", value=queue.current['requester'].mention, inline=True)
        embed.add_field(name="⏱️ 長度", value=self._format_duration(current_info['duration']), inline=True)
        embed.add_field(name="🔊 音量", value=f"{int(queue.volume * 100)}%", inline=True)
        embed.add_field(name="🔁 循環", value="開啟" if queue.loop_mode else "關閉", inline=True)
        
        if current_info['uploader']:
            embed.add_field(name="📺 頻道", value=current_info['uploader'], inline=True)
        
        if current_info['thumbnail']:
            embed.set_thumbnail(url=current_info['thumbnail'])
        
        await interaction.response.send_message(embed=embed)

    # ===== 錯誤處理 =====
    
    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        """處理 Cog 內的錯誤"""
        print(f"音樂模組錯誤: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ 發生錯誤，請稍後再試", ephemeral=True)

# ===== 設定函數 =====
async def setup(bot):
    """載入 Cog 時呼叫的函數"""
    await bot.add_cog(Music(bot))
    print("🎵 音樂 Cog 設定完成（完整版）")