# 🎵 Bot Discord - Système d'Expérience Vocale

Un bot Discord gratuit et open-source qui gère un système d'expérience complet pour les utilisateurs en vocal.

## ✨ Fonctionnalités

✅ **Gain d'XP en vocal** - 1 XP par minute + 10 XP bonus à la sortie  
✅ **Système de niveau** - Nouvelle progression tous les 100 XP  
✅ **Classement serveur** - Top 10 avec commande `!leaderboard`  
✅ **Profils personnels** - Consultez votre niveau avec `!level`  
✅ **Base de données SQLite** - Pas besoin de configuration externe  
✅ **Gratuit et open-source** - Entièrement personnalisable  

## 📋 Prérequis

- Python 3.8+
- Compte Discord
- Un serveur Discord où vous pouvez ajouter des bots

## 🚀 Installation

### 1. **Créer une application Discord**

1. Allez sur [Discord Developer Portal](https://discord.com/developers/applications)
2. Cliquez sur "New Application"
3. Donnez-lui un nom (ex: "XP Bot")
4. Allez dans l'onglet "Bot" et cliquez "Add Bot"
5. Sous "TOKEN", cliquez "Copy" (gardez-le secret!)

### 2. **Configurer les permissions**

1. Allez dans "OAuth2" → "URL Generator"
2. Sélectionnez les scopes:
   - `bot`
   - `applications.commands`
3. Sélectionnez les permissions:
   - `Send Messages`
   - `Embed Links`
   - `Read Message History`
   - `Manage Messages`
4. Copiez l'URL générée et ouvrez-la pour ajouter le bot à votre serveur

### 3. **Installer les dépendances**

```bash
pip install -r requirements.txt
```

### 4. **Créer un fichier .env**

Créez un fichier `.env` à la racine du projet:

```
DISCORD_TOKEN=votre_token_ici
```

⚠️ **Important**: Ne partagez JAMAIS votre token!

### 5. **Lancer le bot**

```bash
python bot.py
```

Vous devriez voir:
```
✅ Bot connecté en tant que [NomDuBot]
```

## 📖 Commandes

| Commande | Description |
|----------|-------------|
| `!level [@member]` | Affiche votre niveau/celui d'un membre |
| `!leaderboard` | Top 10 du serveur |
| `!stats` | Vos statistiques vocales |
| `!reset [@member]` | Réinitialise l'XP (admin) |
| `!help` | Affiche l'aide |

## 🎮 Système d'expérience

### Gain d'XP
- **1 XP par minute** en vocal
- **10 XP bonus** à la sortie du vocal
- Fonctionne même si vous êtes seul en vocal

### Niveaux
```
Niveau 1: 0 XP
Niveau 2: 100 XP
Niveau 3: 200 XP
Niveau 4: 300 XP
...
```

### Notifications
Vous recevrez un message privé quand vous montez de niveau! 🎉

## 📊 Structure de la base de données

Le bot crée automatiquement `xp.db` avec les tables:

- **users**: Stocke l'XP, le niveau et le temps en vocal
- **voice_sessions**: Suivi des sessions vocales actives

## 🔧 Personnalisation

### Modifier le gain d'XP

Dans `bot.py`, ligne ~110:
```python
xp_gain = max(10, (duration // 60) * 10)  # 10 XP par minute
```

### Modifier le XP nécessaire par niveau

Dans `bot.py`, ligne ~48:
```python
new_level = 1 + (new_xp // 100)  # 100 XP par niveau
```

### Ajouter un message de bienvenue

Vous pouvez modifier les messages des embeds (Discord.py utilise `discord.Embed`)

## 🐛 Dépannage

### "❌ Erreur: Ajoutez votre token"
→ Vérifiez que votre fichier `.env` existe et contient le token

### Le bot ne voit pas les vocaux
→ Vérifiez que le bot a les permissions "Connect" et "Speak" dans les paramètres du canal vocal

### Les commandes ne fonctionnent pas
→ Assurez-vous que le préfixe est correct (`!`)

### "Intents" errors
→ Allez dans Discord Developer Portal → Bot → Cochez "Server Members Intent" et "Message Content Intent"

## 📝 Notes

- Le bot stocke les données **par serveur** (chaque serveur a son propre classement)
- Les données sont **persistantes** (elles restent même après un redémarrage)
- Vous pouvez exécuter le bot 24/7 sur un VPS/hébergeur gratuit (ex: Heroku alternative, Replit, etc.)

## 🆓 Gratuit?

Oui! Ce bot:
- N'utilise **aucune API payante**
- Utilise **SQLite** (gratuit et léger)
- Fonctionne sur **Python pur** (gratuit)
- Peut s'héberger **gratuitement** (Heroku alternatif, VPS gratuit, votre PC)

## 📜 Licence

Gratuit et open-source. Faites-en ce que vous voulez!

## 💬 Support

Des questions? Vérifiez:
1. Les logs d'erreur dans le terminal
2. Que votre token est valide
3. Que le bot a les bonnes permissions

Bonne chance! 🚀
