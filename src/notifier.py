"""
Notifier Telegram — messages riches avec analyse complète
"""
import logging
import aiohttp

logger = logging.getLogger("notifier")

def _bar(score):
    filled = round(score / 10)
    return "█" * filled + "░" * (10 - filled)

def _prob_bar(pct):
    filled = round(pct / 10)
    return "▓" * filled + "░" * (10 - filled)

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token   = token
        self.chat_id = chat_id
        self.url     = f"https://api.telegram.org/bot{token}/sendMessage"

    async def _send(self, text):
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "chat_id":    self.chat_id,
                    "text":       text[:4096],  # limite Telegram
                    "parse_mode": "Markdown",
                }
                async with session.post(self.url, json=payload) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"Telegram error {resp.status}: {body}")
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Erreur Telegram: {e}")
            return False

    async def send_alert(self, r) -> bool:
        # Emoji décision
        dec_emoji = {"ACHETER": "🟢", "SURVEILLER": "🟡", "EVITER": "🔴"}.get(r.decision, "📊")

        # Scores détaillés
        score_lines = "\n".join(
            f"  {k:<22} {v}" for k, v in r.scores.items()
        )

        # Upside analystes
        upside_str = f"+{r.upside_analyst:.0f}% vs consensus" if r.upside_analyst > 0 else "N/A"

        msg = (
            f"{dec_emoji} *{r.ticker}* — {r.decision}\n"
            f"_{r.company_name}_\n"
            f"💰 Prix : *${r.current_price:.2f}*\n\n"

            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Score global : {r.total_score}/100*\n"
            f"`{_bar(r.total_score)}`\n"
            f"Conviction : {r.conviction}\n\n"

            f"*Scores détaillés :*\n`{score_lines}`\n\n"

            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📈 *Probabilités 12 mois :*\n"
            f"Hausse : {r.probability_up}% `{_prob_bar(r.probability_up)}`\n"
            f"Baisse : {r.probability_down}% `{_prob_bar(r.probability_down)}`\n\n"

            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Prix d'entrée idéal :* {r.entry_price}\n"
            f"🚀 *Objectif 5 ans :* {r.target_5y}\n"
            f"📐 *Marge de sécurité :* {r.safety_margin}\n"
            f"🏦 *Analystes :* {upside_str}\n\n"

            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *Thèse :*\n{r.thesis}\n\n"

            f"⚠️ *Risques :*\n{r.risks}\n\n"

            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📋 *Scénarios :*\n"
            f"🐂 {r.scenario_bull}\n"
            f"📊 {r.scenario_base}\n"
            f"🐻 {r.scenario_bear}"
        )

        sent = await self._send(msg)
        if sent:
            logger.info(f"Alerte envoyée : {r.ticker} ${r.current_price:.2f} | {r.total_score}/100 | {r.decision}")
        return sent

    async def send_summary(self, alerted, total):
        if not alerted:
            msg = (
                f"🔍 *Scan hebdomadaire terminé*\n"
                f"{total} actions analysées\n"
                f"Aucune opportunité détectée cette semaine."
            )
        else:
            buy    = [r for r in alerted if r.decision == "ACHETER"]
            watch  = [r for r in alerted if r.decision == "SURVEILLER"]

            lines = "\n".join(
                f"{'🟢' if r.decision=='ACHETER' else '🟡'} *{r.ticker}* ${r.current_price:.2f} "
                f"— {r.total_score}/100 | ↑{r.probability_up}%"
                for r in alerted[:8]
            )
            msg = (
                f"📋 *Résumé scan hebdomadaire*\n"
                f"{total} actions analysées · {len(alerted)} opportunité(s)\n"
                f"🟢 {len(buy)} à acheter · 🟡 {len(watch)} à surveiller\n\n"
                f"{lines}\n\n"
                f"_Analyse complète envoyée pour chaque titre ci-dessus._"
            )
        await self._send(msg)
