"""
Investment Bot v3 — Architecture multi-agents
Données 100% réelles · Honnêteté sur les données manquantes
"""
import asyncio
import logging
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("main")

# Actions peu chères à fort potentiel — prix < 50$
WATCHLIST = [
    # IA & Tech émergente
    "SOUN", "BBAI", "IONQ", "QBTS", "RGTI",
    # Semi-conducteurs abordables
    "CRDO", "AEHR", "ENVX", "AAOI", "CEVA",
    # Biotech/Santé
    "RXRX", "NTLA", "BEAM", "EDIT", "TMDX",
    # Space & Defence
    "RKLB", "ASTS", "ACHR", "JOBY",
    # Fintech
    "AFRM", "UPST", "SOFI", "DAVE",
    # SaaS abordable
    "GTLB", "CFLT", "DOCN", "MGNI",
    # Énergie propre
    "ARRY", "STEM", "FLNC",
    # Consommation
    "CELH", "HIMS", "PRPL",
]

ALERT_THRESHOLD = int(os.environ.get("ALERT_THRESHOLD", "65"))
MAX_TO_ANALYZE  = int(os.environ.get("MAX_ANALYZE", "15"))   # limite tokens Groq


async def main():
    logger.info("=== Investment Bot v3 démarré ===")
    logger.info(f"Watchlist: {len(WATCHLIST)} tickers | Seuil: {ALERT_THRESHOLD}/100")

    from agents.collector import DataCollector
    from agents.analyzer  import MultiAgentAnalyzer
    from src.notifier     import TelegramNotifier

    notifier  = TelegramNotifier(
        token=os.environ["TELEGRAM_TOKEN"],
        chat_id=os.environ["TELEGRAM_CHAT_ID"],
    )
    collector = DataCollector()
    analyzer  = MultiAgentAnalyzer()

    # ── 1. Collecte des données réelles ──────────────────────────
    logger.info("Phase 1 : Collecte des données...")
    all_data = []
    for i, sym in enumerate(WATCHLIST, 1):
        logger.info(f"[{i}/{len(WATCHLIST)}] Collecte {sym}")
        d = collector.collect(sym)
        if not d.error and d.current_price:
            # Filtre rapide : prix < 50$, croissance > 10%
            if d.current_price <= 50 and (d.rev_growth_1y or 0) >= 10:
                all_data.append(d)
                logger.info(f"  ✓ ${d.current_price:.2f} | CA+{d.rev_growth_1y or 0:.0f}% | qualité:{d.data_quality_score}/100")
        time.sleep(1.2)

    logger.info(f"{len(all_data)} candidats retenus après filtre initial")

    if not all_data:
        await notifier._send("🔍 Scan terminé — aucun candidat après filtre.")
        return

    # Trier par score qualité des données + croissance
    all_data.sort(key=lambda d: (d.data_quality_score, d.rev_growth_1y or 0), reverse=True)
    to_analyze = all_data[:MAX_TO_ANALYZE]

    # ── 2. Analyse multi-agents ───────────────────────────────────
    logger.info(f"Phase 2 : Analyse IA de {len(to_analyze)} candidats...")
    results = []
    for i, d in enumerate(to_analyze, 1):
        logger.info(f"[{i}/{len(to_analyze)}] Analyse {d.ticker}...")
        try:
            report = analyzer.analyze(d)
            score  = report.score_global or 0
            logger.info(f"  → Score: {score}/100 | {report.decision} | {report.conviction}")
            if score >= ALERT_THRESHOLD:
                results.append((report, d))
        except Exception as e:
            logger.error(f"Erreur analyse {d.ticker}: {e}")
        time.sleep(1.0)

    # Trier par score global
    results.sort(key=lambda x: x[0].score_global or 0, reverse=True)

    # ── 3. Envoi des alertes ─────────────────────────────────────
    logger.info(f"Phase 3 : Envoi de {len(results)} rapports...")
    sent_reports = []
    for report, d in results:
        ok = await notifier.send_report(report, d)
        if ok:
            sent_reports.append(report)
        await asyncio.sleep(2)

    # ── 4. Résumé ────────────────────────────────────────────────
    await notifier.send_summary(sent_reports, total=len(WATCHLIST))
    logger.info(f"=== Terminé : {len(sent_reports)} rapports envoyés ===")


if __name__ == "__main__":
    asyncio.run(main())
