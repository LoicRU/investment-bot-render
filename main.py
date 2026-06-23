"""
Investment Bot v5 — Ultra-efficient
- Données réelles : yfinance + SEC EDGAR
- Scores : Python pur (0 token)
- IA : 1 appel × 700 tokens par ticker (vs 9500 en v4)
- Réduction : 88% moins de tokens, même précision
"""
import asyncio
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("main")

WATCHLIST = [
    "SOUN","BBAI","IONQ","QBTS","RGTI",
    "CRDO","AEHR","ENVX","CEVA","AAOI",
    "RXRX","NTLA","BEAM","EDIT","TMDX",
    "RKLB","ASTS","ACHR","JOBY",
    "AFRM","UPST","SOFI","DAVE",
    "GTLB","CFLT","DOCN","MGNI",
    "ARRY","STEM","FLNC",
    "CELH","HIMS","PRPL",
]

THRESHOLD   = int(os.environ.get("ALERT_THRESHOLD", "55"))
MAX_ANALYZE = int(os.environ.get("MAX_ANALYZE", "15"))


async def main():
    logger.info(f"=== Investment Bot v5 === {len(WATCHLIST)} tickers")

    from agents.collector import DataCollector
    from agents.prescorer import score as prescore
    from agents.analyzer  import Analyzer
    from src.notifier     import TelegramNotifier

    notifier  = TelegramNotifier(os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"])
    collector = DataCollector()
    analyzer  = Analyzer()

    # Phase 1 — Collecte (0 token)
    logger.info("Phase 1 — Collecte données réelles...")
    all_data = []
    for i, sym in enumerate(WATCHLIST, 1):
        logger.info(f"[{i}/{len(WATCHLIST)}] {sym}")
        d = collector.collect(sym)
        if d.error or not d.current_price:
            continue
        if d.current_price <= 50 and (d.rev_growth_1y or 0) >= 5:
            all_data.append(d)
            logger.info(f"  ✓ ${d.current_price:.2f} | CA{_p(d.rev_growth_1y)} | q:{d.data_quality_score}/100")
        time.sleep(1.2)

    logger.info(f"{len(all_data)} candidats collectés")
    if not all_data:
        await notifier._send("🔍 Scan terminé — aucun candidat.")
        return

    # Phase 2 — Pré-scoring Python (0 token)
    logger.info("Phase 2 — Scoring Python (0 token Groq)...")
    prescores = []
    for d in all_data:
        ps = prescore(d)
        logger.info(f"  {d.ticker}: {ps.score_global}/100 | alertes:{len(ps.alertes)}")
        prescores.append((d, ps))

    # Trier et filtrer avant d'appeler l'IA
    prescores.sort(key=lambda x: x[1].score_global, reverse=True)
    to_analyze = [(d, ps) for d, ps in prescores if ps.score_global >= THRESHOLD][:MAX_ANALYZE]
    logger.info(f"{len(to_analyze)} candidats >= {THRESHOLD}/100 → envoi IA")

    # Phase 3 — 1 appel IA par ticker (700 tokens chacun)
    logger.info(f"Phase 3 — Synthèse IA ({len(to_analyze)} appels × ~700 tokens)...")
    results = []
    for i, (d, ps) in enumerate(to_analyze, 1):
        logger.info(f"[{i}/{len(to_analyze)}] IA {d.ticker} (score Python: {ps.score_global}/100)")
        try:
            report = analyzer.analyze(d, ps)
            results.append((report, d))
            logger.info(f"  → {report.decision} | {report.conviction} | {report.etoiles}★")
        except Exception as e:
            logger.error(f"  Erreur {d.ticker}: {e}")
        time.sleep(0.5)

    # Phase 4 — Envoi Telegram
    logger.info(f"Phase 4 — Envoi {len(results)} rapports...")
    sent = []
    for report, d in results:
        ok = await notifier.send_report(report, d)
        if ok: sent.append(report)
        await asyncio.sleep(1.5)

    await notifier.send_summary(sent, total=len(WATCHLIST))

    # Stats tokens
    tokens_used = len(to_analyze) * 700
    logger.info(f"=== Terminé : {len(sent)} rapports | ~{tokens_used:,} tokens Groq utilisés ===")


def _p(v):
    return f"{v:+.0f}%" if v is not None else "N/D"

if __name__ == "__main__":
    asyncio.run(main())
