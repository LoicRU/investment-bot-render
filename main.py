"""
Investment Bot v6 — Rotation intelligente
- Univers de 500+ tickers
- Mémoire persistante (JSON sur GitHub)
- Rotation : chaque ticker vu toutes les 3 semaines max
- Watchlist dynamique : bons tickers surveillés plus souvent
- Tickers rejetés mis en pause 2 mois
- Boucle jusqu'à trouver une opportunité (max 3 tentatives)
- 0 mensonge : N/D si donnée manquante
"""
import asyncio
import logging
import os
import time
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("main")

MAX_ATTEMPTS  = int(os.environ.get("MAX_ATTEMPTS", "3"))
WAIT_BETWEEN  = int(os.environ.get("WAIT_BETWEEN", "30"))
THRESHOLD     = int(os.environ.get("ALERT_THRESHOLD", "55"))
TICKERS_SCAN  = int(os.environ.get("TICKERS_PER_SCAN", "40"))
MAX_AI_CALLS  = int(os.environ.get("MAX_AI_CALLS", "15"))


async def run_scan(collector, analyzer, memory, notifier, scan_num: int) -> list:
    from agents.prescorer import score as prescore
    from src.universe     import ALL_TICKERS, WATCHLIST_CORE

    # ── Sélection intelligente des tickers ───────────────────────
    tickers = memory.select_tickers(ALL_TICKERS, WATCHLIST_CORE, n=TICKERS_SCAN)
    never_seen = sum(1 for t in tickers if not memory.get_ticker_info(t).get("last_scan"))
    logger.info(f"Scan {scan_num}: {len(tickers)} tickers sélectionnés ({never_seen} jamais vus)")
    logger.info(f"Couverture totale: {memory.coverage_report(ALL_TICKERS)}")

    # ── Phase 1 : Collecte données réelles ───────────────────────
    candidates = []
    for i, sym in enumerate(tickers, 1):
        logger.info(f"  [{i}/{len(tickers)}] {sym}")
        d = collector.collect(sym)

        if d.error or not d.current_price:
            logger.debug(f"  Skip {sym}: {d.error or 'no price'}")
            time.sleep(0.4)
            continue

        # Filtre : prix < 50$, croissance > 0%
        if d.current_price <= 50 and (d.rev_growth_1y or 0) >= 0:
            candidates.append(d)
            logger.info(f"  ✓ {sym} ${d.current_price:.2f} CA{_p(d.rev_growth_1y)} q:{d.data_quality_score}/100")
        time.sleep(1.1)

    logger.info(f"{len(candidates)} candidats après collecte")
    if not candidates:
        return []

    # ── Phase 2 : Pré-scoring Python (0 token) ───────────────────
    prescores = []
    for d in candidates:
        ps = prescore(d)
        prescores.append((d, ps))

    prescores.sort(key=lambda x: x[1].score_global, reverse=True)

    # Mettre à jour la mémoire avec les scores Python (même sans IA)
    for d, ps in prescores:
        memory.update_ticker(d.ticker, ps.score_global, "PRE_SCORE")

    # Filtrer pour l'IA
    to_analyze = [(d, ps) for d, ps in prescores if ps.score_global >= THRESHOLD][:MAX_AI_CALLS]
    logger.info(f"{len(to_analyze)} candidats >= {THRESHOLD}/100 → IA")

    if not to_analyze:
        memory.save()
        return []

    # ── Phase 3 : Synthèse IA (1 appel par ticker) ───────────────
    results = []
    for i, (d, ps) in enumerate(to_analyze, 1):
        logger.info(f"  IA [{i}/{len(to_analyze)}] {d.ticker} score:{ps.score_global}")
        try:
            report = analyzer.analyze(d, ps)
            # Mettre à jour la mémoire avec la décision IA
            memory.update_ticker(d.ticker, report.score_global, report.decision or "")
            if report.score_global >= 70:
                memory.increment_opportunity()
            results.append((report, d))
            logger.info(f"  → {report.decision} | {report.etoiles}★ | {report.conviction}")
        except Exception as e:
            logger.error(f"  Erreur IA {d.ticker}: {e}")
        time.sleep(0.6)

    memory.increment_scan()
    memory.save()

    # ── Phase 4 : Envoi Telegram ──────────────────────────────────
    sent = []
    for report, d in results:
        ok = await notifier.send_report(report, d)
        if ok:
            sent.append(report)
        await asyncio.sleep(1.5)

    return sent


async def main():
    from agents.collector import DataCollector
    from agents.analyzer  import Analyzer
    from src.memory       import Memory
    from src.notifier     import TelegramNotifier
    from src.universe     import ALL_TICKERS, TOTAL_TICKERS

    logger.info(f"=== Investment Bot v6 ===")
    logger.info(f"Univers: {TOTAL_TICKERS} tickers | Seuil: {THRESHOLD} | Max: {MAX_ATTEMPTS} scans")

    notifier  = TelegramNotifier(os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"])
    collector = DataCollector()
    analyzer  = Analyzer()
    memory    = Memory()

    stats = memory.get_stats()
    coverage = memory.coverage_report(ALL_TICKERS)

    await notifier._send(
        f"🔄 *Scan démarré*\n"
        f"Univers: {TOTAL_TICKERS} actions | Seuil: {THRESHOLD}/100\n"
        f"Couverture mémoire: {coverage}\n"
        f"Scans précédents: {stats['total_scans']} | "
        f"Opportunités trouvées: {stats['opportunities']}\n"
        f"Watchlist dynamique: {stats['watchlist_size']} tickers"
    )

    total_sent = []
    attempt    = 0

    while attempt < MAX_ATTEMPTS:
        attempt += 1
        logger.info(f"\n{'='*50}\nTENTATIVE {attempt}/{MAX_ATTEMPTS}\n{'='*50}")

        if attempt > 1:
            await notifier._send(
                f"🔄 *Tentative {attempt}/{MAX_ATTEMPTS}*\n"
                f"Couverture: {memory.coverage_report(ALL_TICKERS)}"
            )

        try:
            sent = await run_scan(collector, analyzer, memory, notifier, attempt)
            total_sent.extend(sent)

            if sent:
                logger.info(f"✅ {len(sent)} opportunité(s) — arrêt")
                break
            else:
                logger.info("Aucune opportunité cette tentative")
                if attempt < MAX_ATTEMPTS:
                    await asyncio.sleep(WAIT_BETWEEN)

        except Exception as e:
            logger.error(f"Erreur tentative {attempt}: {e}")
            memory.save()
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(30)

    # ── Résumé final ──────────────────────────────────────────────
    stats_final = memory.get_stats()
    coverage_final = memory.coverage_report(ALL_TICKERS)

    if total_sent:
        await notifier.send_summary(total_sent, total=TICKERS_SCAN * attempt)
        await notifier._send(
            f"✅ *Scan terminé*\n"
            f"{attempt} tentative(s) | {len(total_sent)} opportunité(s)\n"
            f"Couverture totale: {coverage_final}\n"
            f"Watchlist dynamique: {stats_final['watchlist_size']} tickers\n"
            f"Total historique: {stats_final['total_tickers_seen']} tickers vus"
        )
    else:
        wl = memory.data.get("watchlist", [])
        wl_str = ", ".join(wl[:10]) + ("..." if len(wl) > 10 else "") if wl else "vide"
        await notifier._send(
            f"⚠️ *Scan terminé — Aucune opportunité*\n"
            f"{attempt} tentative(s) | {TICKERS_SCAN * attempt} tickers analysés\n"
            f"Couverture totale: {coverage_final}\n\n"
            f"📋 *Watchlist surveillée ({stats_final['watchlist_size']}) :*\n"
            f"_{wl_str}_\n\n"
            f"_Résultat honnête — aucun ticker ne dépasse {THRESHOLD}/100 aujourd'hui._"
        )

    logger.info(f"=== Terminé : {len(total_sent)} opps | {stats_final['total_tickers_seen']} tickers vus au total ===")


def _p(v):
    return f"{v:+.0f}%" if v is not None else "N/D"


if __name__ == "__main__":
    asyncio.run(main())
