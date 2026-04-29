import discord
from discord.ext import commands, tasks
import sqlite3
import os
from datetime import datetime, timedelta
import random

# Import keep_alive pour Replit (optionnel, enlever la ligne si vous n'en avez pas besoin)
try:
    from keep_alive import keep_alive
    keep_alive()
    print("✅ Keep-Alive activé pour Replit!")
except ImportError:
    print("⚠️ keep_alive.py non trouvé - le bot s'arrêtera après quelques heures")

# Configuration du bot
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Base de données SQLite
DB_FILE = "xp.db"

def init_db():
    """Initialise la base de données"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        guild_id INTEGER,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
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
    """
    Calcule l'XP total nécessaire pour atteindre un niveau.
    Formule: 100 * level * (level + 1) / 2
    Niveau 1: 100 XP
    Niveau 2: 300 XP (100 + 200)
    Niveau 3: 600 XP (100 + 200 + 300)
    Niveau 4: 1000 XP (100 + 200 + 300 + 400)
    """
    if level <= 1:
        return 0    
    return 100 * level * (level + 1) // 2

def get_level_from_xp(xp):
    """Trouve le niveau en fonction de l'XP total"""
    level = 1
    while calculate_xp_for_level(level) <= xp:
        level += 1
    return level - 1

def get_user_data(user_id, guild_id):
    """Récupère les données d'un utilisateur"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT xp, level, voice_time FROM users WHERE user_id = ? AND guild_id = ?',
              (user_id, guild_id))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {'xp': result[0], 'level': result[1], 'voice_time': result[2]}
    return {'xp': 0, 'level': 1, 'voice_time': 0}

def add_xp(user_id, guild_id, amount):
    """Ajoute de l'XP à un utilisateur"""
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
    """Récupère le classement d'un serveur"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''SELECT user_id, xp, level FROM users 
                 WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?''',
              (guild_id, limit))
    results = c.fetchall()
    conn.close()
    return results

@bot.event
async def on_ready():
    """Quand le bot démarre"""
    init_db()
    print(f"✅ Bot connecté en tant que {bot.user}")
    print(f"📊 Serveurs: {len(bot.guilds)}")
    give_voice_xp.start()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, 
                                                        name="les vocaux | !help"))

@bot.event
async def on_voice_state_update(member, before, after):
    """Détecte quand quelqu'un rejoint/quitte un vocal"""
    guild_id = member.guild.id
    user_id = member.id
    
    # Rejoint un vocal
    if before.channel is None and after.channel is not None:
        if not member.bot:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO voice_sessions (user_id, guild_id, start_time) VALUES (?, ?, ?)',
                      (user_id, guild_id, datetime.now().timestamp()))
            conn.commit()
            conn.close()
            print(f"🎤 {member.name} a rejoint le vocal {after.channel.name}")
    
    # Quitte un vocal
    elif before.channel is not None and after.channel is None:
        if not member.bot:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM voice_sessions WHERE user_id = ? AND guild_id = ?',
                      (user_id, guild_id))
            conn.commit()
            conn.close()
            
            print(f"👋 {member.name} a quitté le vocal {before.channel.name}")

@tasks.loop(minutes=5)
async def give_voice_xp():
    """Donne 1 XP toutes les 5 minutes aux utilisateurs en vocal (si 2+ personnes) + 5 XP bonus toutes les heures"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT user_id, guild_id FROM voice_sessions')
    sessions = c.fetchall()
    conn.close()
    
    for user_id, guild_id in sessions:
        # Vérifier le nombre de personnes en vocal
        try:
            guild = bot.get_guild(guild_id)
            if guild:
                # Trouver le canal où l'utilisateur est
                for channel in guild.voice_channels:
                    members_in_channel = [m for m in channel.members if not m.bot]
                    for member in members_in_channel:
                        if member.id == user_id:
                            # 1 XP toutes les 5 minutes en vocal (avec 2+ personnes)
                            if len(members_in_channel) >= 2:
                                result_xp = add_xp(user_id, guild_id, 1)
                                
                                # Bonus 5 XP toutes les heures (chaque 60 minutes)
                                conn_check = sqlite3.connect(DB_FILE)
                                c_check = conn_check.cursor()
                                c_check.execute('SELECT start_time FROM voice_sessions WHERE user_id = ? AND guild_id = ?',
                                              (user_id, guild_id))
                                result_time = c_check.fetchone()
                                conn_check.close()
                                
                                if result_time:
                                    duration = int(datetime.now().timestamp() - result_time[0])
                                    # Bonus toutes les 60 minutes exactes
                                    if duration > 0 and duration % 3600 == 0:
                                        bonus_xp = add_xp(user_id, guild_id, 5)
                                        print(f"🎁 {member.name} a gagné 5 XP bonus! (Niveau {bonus_xp['new_level']}) - {len(members_in_channel)} personnes en vocal")
                                        
                                        # Notification de levelup pour bonus
                                        if bonus_xp['old_level'] < bonus_xp['new_level']:
                                            try:
                                                await member.send(f"🎉 **Félicitations!** Vous avez atteint le niveau **{bonus_xp['new_level']}**!\nXP: {bonus_xp['new_xp']}")
                                            except:
                                                pass
        except:
            pass

@bot.command(name="level")
async def level(ctx, member: discord.Member = None):
    """Affiche le niveau d'un utilisateur"""
    if member is None:
        member = ctx.author
    
    data = get_user_data(member.id, ctx.guild.id)
    
    # XP pour le niveau actuel et le suivant
    xp_current_level = calculate_xp_for_level(data['level'])
    xp_next_level = calculate_xp_for_level(data['level'] + 1)
    xp_in_level = data['xp'] - xp_current_level
    xp_needed = xp_next_level - xp_current_level

    if xp_needed <= 0: xp_needed = 100
        percent = max(0, min(100, int((xp_in_level / xp_needed) * 100)))
    embed = discord.Embed(
        title=f"📊 Profil de {member.name}",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Niveau", value=f"**{data['level']}**", inline=True)
    embed.add_field(name="XP Total", value=f"**{data['xp']}**", inline=True)
    embed.add_field(name=f"Progression vers Niveau {data['level'] + 1}", value=f"**{xp_in_level}** / {xp_needed} XP", inline=False)
    
    # Barre de progression
    progress = int((xp_in_level / xp_needed) * 20) if xp_needed > 0 else 20
    bar = "█" * progress + "░" * (20 - progress)
    embed.add_field(name="Barre de progression", value=f"`{bar}` {int((xp_in_level / xp_needed) * 100)}%", inline=False)
    
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb", "top"])
async def leaderboard(ctx):
    """Affiche le classement du serveur"""
    leaderboard_data = get_leaderboard(ctx.guild.id, 10)
    
    if not leaderboard_data:
        await ctx.send("❌ Aucun utilisateur dans la base de données encore!")
        return
    
    embed = discord.Embed(
        title="🏆 Classement du serveur",
        color=discord.Color.gold()
    )
    
    for idx, (user_id, xp, level) in enumerate(leaderboard_data, 1):
        try:
            user = await bot.fetch_user(user_id)
            medal = ["🥇", "🥈", "🥉"][idx - 1] if idx <= 3 else f"{idx}️⃣"
            embed.add_field(
                name=f"{medal} {user.name}",
                value=f"**Niveau {level}** • {xp} XP",
                inline=False
            )
        except:
            pass
    
    await ctx.send(embed=embed)

@bot.command(name="reset")
@commands.has_permissions(administrator=True)
async def reset(ctx, member: discord.Member = None):
    """Réinitialise l'XP (admin seulement)"""
    if member is None:
        member = ctx.author
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE user_id = ? AND guild_id = ?',
              (member.id, ctx.guild.id))
    conn.commit()
    conn.close()
    
    await ctx.send(f"✅ XP de {member.mention} réinitialisé!")

@bot.command(name="stats")
async def stats(ctx):
    """Affiche les statistiques vocales"""
    data = get_user_data(ctx.author.id, ctx.guild.id)
    
    embed = discord.Embed(
        title=f"📈 Statistiques vocales",
        color=discord.Color.green()
    )
    embed.add_field(name="Niveau", value=data['level'], inline=True)
    embed.add_field(name="XP Total", value=data['xp'], inline=True)
    embed.add_field(name="Temps en vocal", value=f"{data['voice_time']} minutes", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="help")
async def help_command(ctx):
    """Liste les commandes disponibles"""
    embed = discord.Embed(
        title="📖 Commandes disponibles",
        description="Voici les commandes du bot d'expérience vocale",
        color=discord.Color.purple()
    )
    embed.add_field(name="!level [@member]", value="Affiche votre niveau ou celui d'un membre", inline=False)
    embed.add_field(name="!leaderboard", value="Affiche le top 10 du serveur", inline=False)
    embed.add_field(name="!stats", value="Affiche vos statistiques vocales", inline=False)
    embed.add_field(name="!table", value="Affiche la table des XP par niveau", inline=False)
    embed.add_field(name="!reset [@member]", value="Réinitialise l'XP (admin)", inline=False)
    embed.add_field(name="!ping", value="Affiche la latence du bot", inline=False)
    embed.add_field(name="✅ Comment ça marche?", 
                    value="• 1 XP toutes les 5 minutes en vocal\n• 5 XP bonus toutes les heures\n• ⚠️ **IL FAUT MINIMUM 2 PERSONNES EN VOCAL**\n• Les niveaux demandent progressivement plus d'XP\n• 🤖 Le bot **NE SE CONNECTE PAS** au vocal (détection seulement)",
                    inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="table")
async def table_command(ctx):
    """Affiche la table des XP nécessaires par niveau"""
    embed = discord.Embed(
        title="📈 Table des XP par Niveau",
        color=discord.Color.gold()
    )
    
    description = "```\n"
    description += "Niveau | XP Total | XP pour ce niveau\n"
    description += "-------|----------|------------------\n"
    
    for level in range(1, 21):
        xp_total = calculate_xp_for_level(level)
        if level == 1:
            xp_for_level = xp_total
        else:
            xp_for_level = xp_total - calculate_xp_for_level(level - 1)
        description += f"{level:6d} | {xp_total:8d} | {xp_for_level:16d}\n"
    
    description += "```"
    embed.description = description
    
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    """Affiche la latence du bot"""
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# Lance le bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Erreur: Ajoutez DISCORD_TOKEN dans les Secrets Replit")
    else:
        bot.run(token)
