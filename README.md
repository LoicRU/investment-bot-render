# 🤖 Investment Bot IA — Koyeb (Gratuit à vie)

Scan automatique · Groq IA · Alertes Telegram · **0$/mois pour toujours**

---

## Coût : 0$ pour toujours

| Service | Plan | Coût |
|---------|------|------|
| **Koyeb** | Free Worker (permanent) | 0$ |
| **Groq API** | Free (14 400 req/jour) | 0$ |
| **yfinance** | Gratuit | 0$ |
| **Telegram** | Gratuit | 0$ |
| **Total** | | **0$/mois** |

---

## Déploiement en 4 étapes (25 min)

### Étape 1 — Clé Groq (5 min)

1. Va sur **[console.groq.com](https://console.groq.com)**
2. Crée un compte gratuit (email suffit, pas de CB)
3. **API Keys** → **Create API Key**
4. Copie la clé : gsk_XXXX...

### Étape 2 — Bot Telegram (5 min)

1. Ouvre Telegram → cherche @BotFather
2. Tape /newbot → suis les instructions → copie le token
3. Envoie /start à ton nouveau bot
4. Ouvre dans ton navigateur :
   https://api.telegram.org/bot<TON_TOKEN>/getUpdates
5. Cherche "chat":{"id":XXXXXXX} → copie ce nombre = ton CHAT_ID

### Étape 3 — Mettre sur GitHub (5 min)

  git init
  git add .
  git commit -m "Investment bot initial"
  git remote add origin https://github.com/TON_USER/investment-bot.git
  git push -u origin main

### Étape 4 — Déployer sur Koyeb (10 min)

1. Va sur koyeb.com → Sign up (gratuit, pas de CB)
2. Clique Create App
3. Choisis GitHub → connecte ton compte → sélectionne ton repo
4. Configure :
   - Service type : Worker  ← IMPORTANT, pas "Web"
   - Branch : main
   - Build command : pip install -r requirements.txt
   - Run command : python main.py
   - Instance : Free
5. Variables d'environnement à ajouter :
   GROQ_API_KEY      = gsk_XXXX...
   TELEGRAM_TOKEN    = 1234567890:AAFxxx...
   TELEGRAM_CHAT_ID  = 123456789
   SCAN_MODE         = weekly
   ALERT_THRESHOLD   = 75
6. Clique Deploy ✅

---

## Vérifier que ça tourne

Koyeb → ton service → Logs :
  === Investment Bot démarré ===
  Telegram polling démarré
  Scheduler démarré

Envoie /start à ton bot Telegram → il doit répondre immédiatement ✅

---

## Commandes Telegram

/start        Démarre le bot
/help         Liste des commandes
/scan         Lance un scan immédiat
/top          Top 10 opportunités
/analyse NVDA Analyse un ticker précis
/watchlist    Ta liste personnelle
/ajouter NVDA Ajoute un ticker
/supprimer    Retire un ticker
/status       État du bot
