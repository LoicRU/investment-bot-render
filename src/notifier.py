"""
Notifier Telegram — envoi simple, sans polling
GitHub Actions n'a pas besoin d'un bot permanent
"""
import logging
import aiohttp

logger = logging.getLogger("notifier")


def _bar(score: int) -> str:
    filled = round(score / 10)
    return "█" * filled + "░" * (10 - filled)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self.url     = f"https://api.telegram.org/bot{token}/sendMessage"

    async def _send(self, text: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "chat_id":    self.chat_id,
                    "text":       text,
                    "parse_mode": "Markdown",
                }
                async with session.post(self.url, json=payload) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Erreur Telegram: {e}")
            return False

    async def send_alert(self, r) -> bool:
        score_lines = "\n".join(
            f"  {k:<20} {v}" for k, v in r.scores.items()
        )
        msg = (
            f"*{r.ticker}* — {r.conviction}\n"
            f"_{r.company_name}_\n\n"
            f"*Score : {r.total_score}/100*\n"
            f"`{_bar(r.total_score)}`\n\n"
            f"*Détail :*\n`{score_lines}`\n\n"
            f"*Thèse :* {r.thesis}\n\n"
            f"*Risques :* {r.risks}\n\n"
            f"*Cibles 3 ans :*\n"
            f"  🐂 {r.price_target_bull}\n"
            f"  📈 {r.price_target_base}\n"
            f"  🛡 Marge : {r.safety_margin}"
        )
        sent = await self._send(msg)
        if sent:
            logger.info(f"Alerte envoyée : {r.ticker} ({r.total_score}/100)")
        return sent

    async def send_summary(self, alerted: list, total: int):
        if not alerted:
            msg = (
                f"🔍 *Scan hebdomadaire terminé*\n"
                f"{total} tickers analysés\n"
                f"Aucune opportunité ≥ seuil cette semaine."
            )
        else:
            lines = "\n".join(
                f"  • *{r.ticker}* — {r.total_score}/100 {r.conviction}"
                for r in alerted[:8]
            )
            msg = (
                f"📋 *Résumé scan hebdomadaire*\n"
                f"{total} tickers · {len(alerted)} opportunité(s)\n\n"
                f"{lines}\n\n"
                f"_Détails envoyés ci-dessus pour chaque titre._"
            )
        await self._send(msg)
