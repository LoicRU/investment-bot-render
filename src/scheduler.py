"""
Scheduler — scans automatiques
SCAN_MODE=weekly  → chaque lundi 8h UTC (10h Paris) — recommandé
SCAN_MODE=daily   → chaque jour 8h UTC
ALERT_THRESHOLD   → score minimum pour alerte (défaut 75)
"""
import asyncio
import logging
import os
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("scheduler")

THRESHOLD = int(os.environ.get("ALERT_THRESHOLD", "75"))
MODE      = os.environ.get("SCAN_MODE", "weekly")


async def run_scan_once(notifier):
    from src.screener import Screener, WATCHLIST
    from src.scorer   import AIScorer
    from src.database import Database

    db       = Database()
    screener = Screener()
    scorer   = AIScorer()

    logger.info(f"=== Scan [{MODE}] démarré : {datetime.utcnow().isoformat()} ===")

    # Fusionner watchlist perso + liste par défaut
    all_tickers = list(set(WATCHLIST + db.get_watchlist()))

    # 1. Filtre sans IA
    candidates = screener.scan(all_tickers)

    # 2. Scoring IA Groq (max 30 en weekly, 15 en daily)
    max_b   = 30 if MODE == "weekly" else 15
    results = scorer.score_batch(candidates, max_batch=max_b)

    # 3. Alertes
    alerted = []
    for r in results:
        db.save_score(r)
        if r.total_score >= THRESHOLD and not db.already_alerted_today(r.ticker):
            sent = await notifier.send_alert(r)
            if sent:
                db.log_alert(r.ticker, r.total_score)
                alerted.append(r)
                await asyncio.sleep(1)

    await notifier.send_summary(alerted, total=len(all_tickers))
    logger.info(f"=== Scan terminé : {len(alerted)} alertes ===")
    return results


class InvestmentScheduler:
    def __init__(self, notifier):
        self.notifier  = notifier
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    def _setup(self):
        if MODE == "weekly":
            trigger = CronTrigger(day_of_week="mon", hour=8, minute=0)
            label   = "Lundi 8h UTC (10h Paris)"
        else:
            trigger = CronTrigger(hour=8, minute=0)
            label   = "Quotidien 8h UTC"

        self.scheduler.add_job(
            run_scan_once, trigger,
            args=[self.notifier],
            id="scan", name=label,
            replace_existing=True,
            misfire_grace_time=600,
        )
        logger.info(f"Job planifié : {label}")

    async def run(self):
        self._setup()
        self.scheduler.start()
        logger.info("Scheduler démarré")
        while True:
            await asyncio.sleep(60)
