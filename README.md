# 🤖 Investment Bot IA — Déploiement Render (Gratuit)

Scan automatique · Scoring Claude IA · Alertes Telegram · **100% gratuit**

---

## Coût réel

| Service | Plan | Coût |
|---------|------|------|
| Render Worker | Free | 0$ |
| Claude API | Free tier (5$ offerts) | 0$ ~2-4 mois |
| yfinance | Gratuit | 0$ |
| Telegram Bot | Gratuit | 0$ |
| **Total** | | **0$/mois** |

> Après épuisement des 5$ : recharger 5$ sur console.anthropic.com
> pour encore ~2-4 mois, soit ~2$/mois en mode weekly.

---

## Déploiement en 4 étapes (20 min)

### 1. Créer ton bot Telegram

1. Ouvre Telegram → cherche **@BotFather**
2. Tape `/newbot` → donne un nom (ex: `MonInvestBot`)
3. Copie le **token** → `1234567890:AAFxxx...`
4. Envoie `/start` à ton nouveau bot
5. Ouvre dans ton navigateur :
   `https://api.telegram.org/bot<TON_TOKEN>/getUpdates`
6. Cherche `"chat":{"id":` → copie le nombre = ton **CHAT_ID**

### 2. Obtenir ta clé Claude API (gratuite)

1. Va sur [console.anthropic.com](https://console.anthropic.com)
2. Crée un compte (gratuit)
3. **API Keys** → **Create Key**
4. Copie la clé `sk-ant-...`

### 3. Mettre le code sur GitHub

```bash
git init
git add .
git commit -m "Investment bot initial"
# Créer un repo sur github.com puis :
git remote add origin https://github.com/TON_USER/investment-bot.git
git push -u origin main
```

### 4. Déployer sur Render

1. Va sur [render.com](https://render.com) → **New** → **Background Worker**
2. Connecte ton repo GitHub
3. Configure :
   - **Runtime** : Python 3
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `python main.py`
4. Dans **Environment Variables**, ajoute :

```
ANTHROPIC_API_KEY  →  sk-ant-XXXX
TELEGRAM_TOKEN     →  1234567890:AAFxxx
TELEGRAM_CHAT_ID   →  123456789
SCAN_MODE          →  weekly
ALERT_THRESHOLD    →  75
CLAUDE_MODEL       →  claude-haiku-4-5-20251001
```

5. Clique **Create Background Worker** → déploiement automatique ✅

---

## Commandes Telegram

```
/start       — Démarre le bot
/help        — Liste des commandes
/scan        — Lance un scan immédiat
/top         — Top 10 opportunités en base
/analyse NVDA — Analyse un ticker précis
/watchlist   — Ta watchlist personnelle
```

---

## Système de scoring (100 pts)

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

**Seuils :** 🚀 ≥90 Exceptionnel · 🟢 ≥80 Forte conviction · 🟡 ≥75 Potentiel

---

## Personnalisation

- **Tickers surveillés** → `src/screener.py` → `WATCHLIST_NASDAQ`
- **Critères de filtre** → `src/screener.py` → constantes `MIN_*`
- **Fréquence** → variable `SCAN_MODE=weekly` ou `daily`
- **Seuil alerte** → variable `ALERT_THRESHOLD=75`
