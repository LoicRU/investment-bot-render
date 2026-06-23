# 🤖 Investment Bot IA — GitHub Actions (100% Gratuit à vie)

Scan automatique · Groq IA · Alertes Telegram · **0$ pour toujours · Pas de CB**

---

## Pourquoi GitHub Actions ?

- ✅ Gratuit à vie (2000 min/mois, largement suffisant)
- ✅ Aucune carte bancaire requise
- ✅ Aucun serveur à gérer
- ✅ Scan automatique chaque lundi
- ✅ Lancement manuel en 1 clic depuis GitHub

---

## Déploiement en 3 étapes (15 min)

---

### Étape 1 — Clé Groq gratuite (3 min)

1. Va sur https://console.groq.com
2. Sign up avec ton email (gratuit, pas de CB)
3. API Keys → Create API Key
4. Copie la clé : gsk_XXXX...

---

### Étape 2 — Créer le repo GitHub (5 min)

1. Va sur https://github.com → New repository
2. Nom : investment-bot (Private recommandé)
3. Dézippe ce projet dans le dossier, puis dans le terminal :

   git init
   git add .
   git commit -m "Investment bot"
   git remote add origin https://github.com/TON_USER/investment-bot.git
   git push -u origin main

---

### Étape 3 — Configurer les secrets (7 min)

Dans ton repo GitHub :
→ Settings → Secrets and variables → Actions → New repository secret

Ajoute ces 3 secrets :

   GROQ_API_KEY      →  gsk_XXXX...
   TELEGRAM_TOKEN    →  ton token Telegram
   TELEGRAM_CHAT_ID  →  ton chat ID Telegram

Optionnel (variable, pas secret) :
→ Settings → Secrets and variables → Actions → Variables → New variable

   ALERT_THRESHOLD   →  75

C'est tout ! Le bot est opérationnel. ✅

---

## Vérifier que ça fonctionne

1. Dans ton repo → onglet Actions
2. Clique sur "Investment Bot Scan"
3. Clique "Run workflow" → Run workflow
4. Regarde les logs en temps réel
5. Tu dois recevoir un message Telegram avec les résultats ✅

---

## Planning automatique

Le bot tourne automatiquement :
- Chaque lundi à 8h00 UTC (10h00 Paris)

Pour changer le planning, édite .github/workflows/scan.yml :
  cron: '0 8 * * 1'   ← lundi 8h UTC
  cron: '0 8 * * 1,4' ← lundi + jeudi
  cron: '0 8 * * *'   ← tous les jours

---

## Ajouter / modifier des tickers

Édite src/screener.py → liste WATCHLIST :

   WATCHLIST = [
       "NVDA", "AMD", "TON_TICKER",
       ...
   ]

Puis git commit + git push → actif immédiatement.

---

## Consommation GitHub Actions

Chaque scan prend environ 10-15 minutes.
1 scan/semaine = ~60 min/mois → bien en dessous des 2000 min gratuits.

Même avec 1 scan/jour = ~450 min/mois → toujours gratuit.
