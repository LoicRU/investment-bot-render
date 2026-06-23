# 🤖 Investment Bot IA — 100% Gratuit à vie

Scan automatique · Groq IA (Llama 3.3 70B) · Alertes Telegram · Render free tier

---

## Coût : 0$ pour toujours

| Service | Plan | Limite | Coût |
|---------|------|--------|------|
| **Render** | Free Worker | Tourne 24h/24 | 0$ |
| **Groq API** | Free | 14 400 req/jour | 0$ |
| **yfinance** | Gratuit | Illimité | 0$ |
| **Telegram** | Gratuit | Illimité | 0$ |
| **Total** | | | **0$/mois** |

---

## Déploiement en 4 étapes (25 min)

### Étape 1 — Clé Groq (5 min)

1. Va sur **[console.groq.com](https://console.groq.com)**
2. Crée un compte gratuit (email suffit, pas de CB)
3. **API Keys** → **Create API Key**
4. Copie la clé : `gsk_XXXX...`

### Étape 2 — Bot Telegram (5 min)

1. Ouvre Telegram → cherche **@BotFather**
2. Tape `/newbot` → donne un nom → copie le **token**
3. Envoie `/start` à ton nouveau bot
4. Ouvre dans ton navigateur :
   `https://api.telegram.org/bot<TON_TOKEN>/getUpdates`
5. Cherche `"chat":{"id":XXXXXXX}` → copie ce nombre = **CHAT_ID**

### Étape 3 — Mettre sur GitHub (5 min)

```bash
# Dézippe le projet, puis dans le dossier :
git init
git add .
git commit -m "Investment bot"

# Sur github.com → New repository → copie l'URL puis :
git remote add origin https://github.com/TON_USER/investment-bot.git
git push -u origin main
```

### Étape 4 — Déployer sur Render (10 min)

1. Va sur **[render.com](https://render.com)** → créer un compte gratuit
2. **New** → **Background Worker**
3. Connecte ton compte GitHub → sélectionne ton repo
4. Configure :
   - **Runtime** : Python 3
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `python main.py`
5. Dans **Environment Variables**, ajoute :

```
GROQ_API_KEY       →  gsk_XXXX...
TELEGRAM_TOKEN     →  1234567890:AAFxxx...
TELEGRAM_CHAT_ID   →  123456789
SCAN_MODE          →  weekly
ALERT_THRESHOLD    →  75
```

6. Clique **Create Background Worker** → 🎉 Déployé !

---

## Commandes Telegram

| Commande | Action |
|----------|--------|
| `/start` | Démarre le bot |
| `/help` | Liste des commandes |
| `/scan` | Lance un scan immédiat |
| `/top` | Top 10 opportunités en base |
| `/analyse NVDA` | Analyse un ticker précis |
| `/watchlist` | Ta liste personnelle |
| `/ajouter NVDA` | Ajoute un ticker |
| `/supprimer NVDA` | Retire un ticker |
| `/status` | État du bot |

---

## Scoring (100 points)

| Critère | Max |
|---------|-----|
| Croissance CA | 20 pts |
| Rentabilité | 15 pts |
| Cash-flow | 15 pts |
| Management | 15 pts |
| Dette | 10 pts |
| Moat | 10 pts |
| TAM | 10 pts |
| Valorisation | 10 pts |
| Risques | -5 à 0 |

**Seuils :** 🚀 ≥90 · 🟢 ≥80 · 🟡 ≥75 · 🔴 <70

---

## Personnaliser les tickers

Édite `src/screener.py` → liste `WATCHLIST` :

```python
WATCHLIST = [
    "NVDA", "AMD", "TON_TICKER",
    # Ajoute autant de tickers que tu veux
]
```

---

## Changer la fréquence des scans

Dans Render → Environment :
- `SCAN_MODE=weekly` → chaque lundi (recommandé)
- `SCAN_MODE=daily` → chaque jour à 8h UTC
