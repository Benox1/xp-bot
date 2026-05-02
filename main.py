import discord
from discord.ext import commands, tasks
import sqlite3
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random

# Charger les variables d'environnement (.env)
load_dotenv()

# Configuration du bot
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Base de données SQLite
DB_FILE = "xp.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        guild_id INTEGER,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0,
        voice_time INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS voice_sessions (
        user_id INTEGER,
        guild_id INTEGER,
        start_time REAL,
        UNIQUE(user_id, guild_id)
    )''')
    conn.commit()
    conn.close()

def calculate_xp_for_level(level):
    if level <= 0:
        return 0
    return 100 * level * (level + 1) // 2

def get_level_from_xp(xp):
    level = 0
    while calculate_xp_for_level(level + 1) <= xp:
        level += 1
    return level

def get_user_data(user_id, guild_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT xp, level, voice_time FROM users WHERE user_id = ? AND guild_id = ?',
              (user_id, guild_id))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {'xp': result[0], 'level': result[1], 'voice_time': result[2]}
    return {'xp': 0, 'level': 0, 'voice_time': 0}

def add_xp(user_id, guild_id, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    data = get_user_data(user_id, guild_id)
    new_xp = data['xp'] + amount
    new_level = get_level_from_xp(new_xp)
    c.execute('''INSERT OR REPLACE INTO users (user_id, guild_id, xp, level, voice_time)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, guild_id, new_xp, new_level, data['voice_time']))
    conn.commit()
    conn.close()
    return {'old_level': data['level'], 'new_level': new_level, 'new_xp': new_xp}

def get_leaderboard(guild_id, limit=10):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''SELECT user_id, xp, level FROM users 
                 WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?''',
              (guild_id, limit))
    results = c.fetchall()
    conn.close()
    return results

@tasks.loop(minutes=30)
async def heartbeat():
    """Écrit un log toutes les 30 min pour éviter la mise en veille Oracle"""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("activity.log", "a") as f:
            f.write(f"[{now}] Serveur en vie - Bot OK\n")
        print(f"💓 Heartbeat : Activité logguée à {now}")
    except Exception as e:
        print(f"Erreur Heartbeat: {e}")

@bot.event
async def on_ready():
    init_db()
    if not heartbeat.is_running():
        heartbeat.start()
    if not give_voice_xp.is_running():
        give_voice_xp.start()
    print(f"✅ Bot connecté en tant que {bot.user.name}")
    
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, 
                                                        name="!help pour les commandes"))

@bot.event
async def on_voice_state_update(member, before, after):
    guild_id = member.guild.id
    user_id = member.id
    if before.channel is None and after.channel is not None:
        if not member.bot:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO voice_sessions (user_id, guild_id, start_time) VALUES (?, ?, ?)',
                      (user_id, guild_id, datetime.now().timestamp()))
            conn.commit()
            conn.close()
    elif before.channel is not None and after.channel is None:
        if not member.bot:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM voice_sessions WHERE user_id = ? AND guild_id = ?',
                      (user_id, guild_id))
            conn.commit()
            conn.close()

@tasks.loop(minutes=5)
async def give_voice_xp():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT user_id, guild_id FROM voice_sessions')
    sessions = c.fetchall()
    conn.close()
    for user_id, guild_id in sessions:
        try:
            guild = bot.get_guild(guild_id)
            if guild:
                for channel in guild.voice_channels:
                    members_in_channel = [m for m in channel.members if not m.bot]
                    for member in members_in_channel:
                        if member.id == user_id and len(members_in_channel) >= 2:
                            add_xp(user_id, guild_id, 1)
        except: pass

@bot.command(name="level")
async def level(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_user_data(member.id, ctx.guild.id)
    
    xp_current_level = calculate_xp_for_level(data['level'])
    xp_next_level = calculate_xp_for_level(data['level'] + 1)
    xp_in_level = data['xp'] - xp_current_level
    xp_needed = xp_next_level - xp_current_level
    
    embed = discord.Embed(title=f"📊 Profil de {member.display_name}", color=discord.Color.blurple())
    embed.add_field(name="Niveau", value=f"**{data['level']}**", inline=True)
    embed.add_field(name="XP Total", value=f"**{data['xp']}**", inline=True)
    embed.add_field(name=f"Vers Niveau {data['level'] + 1}", value=f"**{xp_in_level}** / {xp_needed} XP", inline=False)
    
    progress = int((xp_in_level / xp_needed) * 20) if xp_needed > 0 else 0
    bar = "█" * progress + "░" * (20 - progress)
    percent = int((xp_in_level / xp_needed) * 100) if xp_needed > 0 else 0
    embed.add_field(name="Progression", value=f"`{bar}` {percent}%", inline=False)
    
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb", "top"])
async def leaderboard(ctx):
    leaderboard_data = get_leaderboard(ctx.guild.id, 10)
    if not leaderboard_data:
        await ctx.send("❌ Aucun utilisateur enregistré !")
        return
    
    embed = discord.Embed(title="🏆 Classement du serveur", color=discord.Color.gold())

    for idx, (user_id, xp, level) in enumerate(leaderboard_data, 1):
        try:
            user = await bot.fetch_user(user_id)
            username = user.display_name
            medal = ["🥇", "🥈", "🥉"][idx - 1] if idx <= 3 else f"{idx}️⃣"
            embed.add_field(
                name=f"{medal} {username}",
                value=f"**Niveau {level}** • {xp} XP",
                inline=False
            )
        except:
            embed.add_field(
            name=f"{idx}. Utilisateur inconnu",
            value=f"**Niveau {level}** • {xp} XP",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(name="reset")
@commands.has_permissions(administrator=True)
async def reset(ctx, member: discord.Member = None):
    member = member or ctx.author
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE user_id = ? AND guild_id = ?', (member.id, ctx.guild.id))
    conn.commit()
    conn.close()
    await ctx.send(f"✅ XP de {member.mention} réinitialisé !")

@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="📖 Commandes disponibles",
        description="Voici les commandes du bot d'expérience vocale",
        color=discord.Color.purple()
    )
    embed.add_field(name="!level [@member]", value="Affiche votre niveau ou celui d'un membre", inline=False)
    embed.add_field(name="!leaderboard", value="Affiche le top 10 du serveur", inline=False)
    embed.add_field(name="!reset [@member]", value="Réinitialise l'XP d'un membre (Admin)", inline=False)
    embed.add_field(name="!ping", value="Affiche la latence du bot", inline=False)
    embed.add_field(name="✅ Comment ça marche ?", 
                    value="• 1 XP toutes les 5 min en vocal\n• ⚠️ **MINIMUM 2 PERSONNES EN VOCAL**\n• Débute au niveau 0\n• Le bot est fait par un **GOAT**",
                    inline=False)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong ! {round(bot.latency * 1000)}ms")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ Token manquant")