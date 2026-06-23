"""
Investment Bot — Mode GitHub Actions
Analyse les actions peu chères à fort potentiel
et envoie les meilleures opportunités sur Telegram
"""
import asyncio
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("main")


async def main():
    logger.info("=== Investment Bot démarré ===")

    from src.screener import Screener, WATCHLIST
    from src.scorer   import AIScorer
    from src.notifier import TelegramNotifier

    threshold = int(os.environ.get("ALERT_THRESHOLD", "65"))

    notifier = TelegramNotifier(
        token=os.environ["TELEGRAM_TOKEN"],
        chat_id=os.environ["TELEGRAM_CHAT_ID"],
    )

    # 1. Scan — filtre actions peu chères
    candidates = Screener().scan(WATCHLIST)
    logger.info(f"{len(candidates)} candidats retenus")

    if not candidates:
        await notifier._send("🔍 Scan terminé — aucun candidat après filtre initial.")
        return

    # 2. Scoring IA complet
    results = AIScorer().score_batch(candidates, max_batch=25)
    logger.info(f"{len(results)} opportunités >= {threshold}/100")

    # 3. Alertes — seulement ACHETER et SURVEILLER
    alerted = []
    for r in results:
        if r.total_score >= threshold:
            sent = await notifier.send_alert(r)
            if sent:
                alerted.append(r)
                await asyncio.sleep(2)

    # 4. Résumé
    await notifier.send_summary(alerted, total=len(WATCHLIST))
    logger.info(f"=== Terminé : {len(alerted)} alertes envoyées ===")


if __name__ == "__main__":
    asyncio.run(main())
