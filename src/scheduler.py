"""
Scheduler - Scans automatiques
Mode WEEKLY (défaut free tier) : 1 scan/semaine le lundi 8h UTC
Mode DAILY  : 1 scan/jour à 8h UTC (consomme plus de tokens)
Configurable via variable d'env SCAN_MODE=weekly|daily
"""
import asyncio
import logging
import os
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("scheduler")

ALERT_THRESHOLD = int(os.environ.get("ALERT_THRESHOLD", "75"))
SCAN_MODE       = os.environ.get("SCAN_MODE", "weekly")   # weekly | daily


async def run_scan_once(notifier):
    from src.screener import Screener, WATCHLIST_ALL
    from src.scorer import AIScorer
    from src.database import Database

    db       = Database()
    screener = Screener()
    scorer   = AIScorer()

    logger.info(f"=== Scan démarré [{SCAN_MODE}] : {datetime.utcnow().isoformat()} ===")

    personal_wl      = db.get_watchlist()
    tickers_to_scan  = list(set(WATCHLIST_ALL + personal_wl))

    # 1. Filtre initial sans IA
    candidates = screener.scan(tickers_to_scan)
    logger.info(f"{len(candidates)} candidats après filtre initial")

    # 2. Scoring IA (limité à 20 par scan en mode free)
    max_batch = 20 if SCAN_MODE == "weekly" else 10
    results   = scorer.score_batch(candidates, max_batch=max_batch)
    logger.info(f"{len(results)} résultats ≥ 70/100")

    # 3. Alertes
    alerted = []
    for result in results:
        db.save_score(result)
        if result.total_score >= ALERT_THRESHOLD and not db.already_alerted_today(result.ticker):
            sent = await notifier.send_alert(result)
            if sent:
                db.log_alert(result.ticker, result.total_score, "telegram")
                alerted.append(result)
                await asyncio.sleep(1)

    await notifier.send_summary(alerted, scan_count=len(tickers_to_scan))
    logger.info(f"=== Scan terminé : {len(alerted)} alertes envoyées ===")
    return results


class InvestmentScheduler:
    def __init__(self, notifier):
        self.notifier  = notifier
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    def _setup_jobs(self):
        if SCAN_MODE == "weekly":
            # Lundi 8h00 UTC = 10h00 Paris
            trigger = CronTrigger(day_of_week="mon", hour=8, minute=0)
            name    = "Scan hebdomadaire (lundi 10h Paris)"
        else:
            # Daily : chaque jour 8h00 UTC
            trigger = CronTrigger(hour=8, minute=0)
            name    = "Scan quotidien (8h UTC)"

        self.scheduler.add_job(
            run_scan_once,
            trigger,
            args=[self.notifier],
            id="main_scan",
            name=name,
            replace_existing=True,
            misfire_grace_time=600,
        )
        logger.info(f"Job planifié : {name}")

    async def run(self):
        self._setup_jobs()
        self.scheduler.start()
        logger.info("Scheduler démarré")
        while True:
            await asyncio.sleep(60)
