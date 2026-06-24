"""
Investment Bot v6 — Auto-amélioration Niveau 1 + 2
- Niveau 1 : suit les prix réels à J+30/60/90 vs recommandations
- Niveau 2 : apprend les patterns, ajuste les poids du scoring
- Rotation intelligente : 785 tickers, mémoire persistante Git
- 0 valeur inventée
"""
import asyncio
import logging
import os
import time
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("main")

WATCHLIST = None  # chargé depuis universe.py

THRESHOLD    = int(os.environ.get("ALERT_THRESHOLD", "55"))
TICKERS_SCAN = int(os.environ.get("TICKERS_PER_SCAN", "40"))
MAX_AI_CALLS = int(os.environ.get("MAX_AI_CALLS", "15"))
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "3"))
WAIT_BETWEEN = int(os.environ.get("WAIT_BETWEEN", "30"))


async def run_scan(collector, analyzer, memory, notifier,
                   tracker, learner, scan_num: int) -> list:
    from agents.prescorer import score as prescore
    from src.universe     import ALL_TICKERS, WATCHLIST_CORE

    tickers = memory.select_tickers(ALL_TICKERS, WATCHLIST_CORE, n=TICKERS_SCAN)
    never_seen = sum(1 for t in tickers if not memory.get_ticker_info(t).get("last_scan"))
    logger.info(f"Scan {scan_num}: {len(tickers)} tickers ({never_seen} jamais vus)")
    logger.info(f"Couverture: {memory.coverage_report(ALL_TICKERS)}")

    # ── Phase 1 : Collecte parallèle (5 tickers à la fois) ────────
    import asyncio as _asyncio
    from concurrent.futures import ThreadPoolExecutor

    candidates = []
    invalid_tickers = []

    def collect_one(args):
        idx, sym = args
        d = collector.collect(sym)
        return idx, sym, d

    BATCH_SIZE = 5  # 5 en parallèle — respecte yfinance rate limits
    all_results = []

    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as pool:
        futures = list(pool.map(collect_one, enumerate(tickers, 1)))
        all_results = sorted(futures, key=lambda x: x[0])

    for idx, sym, d in all_results:
        logger.info(f"  [{idx}/{len(tickers)}] {sym}")
        if d.error or not d.current_price:
            if d.error == "INVALID_TICKER":
                invalid_tickers.append(sym)
                logger.warning(f"  ✗ {sym} invalide/délité — cooldown 180j")
            else:
                logger.debug(f"  Skip {sym}: {d.error or 'no price'}")
            continue

        # Filtre rapide avec quick_filter
        from agents.prescorer import quick_filter
        passes, reason = quick_filter(d)
        if not passes:
            logger.debug(f"  Filtré {sym}: {reason}")
            continue

        if d.current_price <= 50:
            candidates.append(d)
            logger.info(f"  ✓ {sym} ${d.current_price:.2f} CA{_p(d.rev_growth_1y)} q:{d.data_quality_score}/100")

    # Marquer les invalides en mémoire
    for sym in invalid_tickers:
        memory.mark_invalid(sym)

    logger.info(f"{len(candidates)} candidats après collecte")
    if not candidates:
        return []

    # ── Phase 2 : Pré-scoring Python (0 token, poids appris) ─────
    prescores = []
    for d in candidates:
        ps = prescore(d)
        prescores.append((d, ps))

    prescores.sort(key=lambda x: x[1].score_global, reverse=True)

    # Mise à jour mémoire
    for d, ps in prescores:
        memory.update_ticker(d.ticker, ps.score_global, "PRE_SCORE")

    # Filtre IA amélioré : skip les losers confirmés par la mémoire
    to_analyze = []
    for d, ps in prescores:
        if ps.score_global < THRESHOLD:
            continue
        # Skip si best_score historique très bas ET score actuel pas meilleur
        mem_info = memory.get_ticker_info(d.ticker)
        best_hist = mem_info.get("best_score", 0)
        scan_count = mem_info.get("scan_count", 0)
        if scan_count >= 3 and best_hist < 40 and ps.score_global < 50:
            logger.debug(f"  Skip IA {d.ticker}: loser confirmé (best={best_hist}, scans={scan_count})")
            continue
        to_analyze.append((d, ps))
        if len(to_analyze) >= MAX_AI_CALLS:
            break

    logger.info(f"{len(to_analyze)} candidats >= {THRESHOLD}/100 → IA")

    if not to_analyze:
        memory.save()
        return []

    # ── Phase 3 : Synthèse IA ────────────────────────────────────
    results = []
    for i, (d, ps) in enumerate(to_analyze, 1):
        logger.info(f"  IA [{i}/{len(to_analyze)}] {d.ticker} score:{ps.score_global}")
        try:
            report = analyzer.analyze(d, ps)
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
            # Enregistrer dans le tracker pour suivi futur
            tracker.record(
                ticker   = d.ticker,
                decision = report.decision or "",
                price    = d.current_price,
                score    = report.score_global,
                scores   = report.__dict__.get("scores_detail", {
                    "croissance":   report.score_croissance,
                    "rentabilite":  report.score_rentabilite,
                    "cashflow":     report.score_cashflow,
                    "bilan":        report.score_bilan,
                    "management":   report.score_management,
                    "valorisation": report.score_valorisation,
                }),
            )
        await asyncio.sleep(1.5)

    tracker.save()
    return sent


async def run_learning_phase(tracker, learner, notifier):
    """
    Phase d'auto-amélioration :
    1. Vérifie les prix actuels des recommandations passées
    2. Calcule les outcomes (win/loss/neutral)
    3. Met à jour les poids du scoring
    4. Envoie un rapport sur Telegram
    """
    logger.info("=== Phase auto-amélioration ===")

    # Vérifier les performances passées
    updates = tracker.check_past()
    if updates:
        logger.info(f"  {len(updates)} vérifications de prix effectuées")
        for u in updates:
            logger.info(f"  {u['ticker']} J+{u['delay']}: {u['change']:+.1f}%")

    # Apprendre des outcomes vérifiés
    outcomes = tracker.get_outcomes()
    learn_result = learner.learn(outcomes)
    logger.info(f"  Apprentissage: {learn_result['status']} | confiance: {learn_result.get('confidence','N/D')}")

    # Rapport Telegram si données suffisantes
    stats_t = tracker.get_stats()
    if stats_t["total_recommendations"] > 0:
        conf     = learner.get_confidence()
        weights  = learner.get_weights()
        w_str    = " | ".join(f"{k}:{v:.0%}" for k, v in weights.items())

        msg = (
            f"🧠 *Rapport auto-amélioration*\n\n"
            f"*Suivi des recommandations :*\n"
            f"Total recommandations: {stats_t['total_recommendations']}\n"
            f"Vérifiées (J+90): {stats_t['verified']}\n"
        )

        if stats_t["verified"] > 0:
            msg += (
                f"✅ Gains (>+10%): {stats_t['wins']}\n"
                f"❌ Pertes (<-10%): {stats_t['losses']}\n"
                f"⚪ Neutres: {stats_t['neutral']}\n"
                f"Taux de réussite: *{stats_t['win_rate'] or 'N/D'}%*\n\n"
            )

        msg += (
            f"*Poids du scoring (ajustés) :*\n"
            f"`{w_str}`\n"
            f"Confiance: {conf}\n\n"
        )

        if learn_result["status"] == "insufficient_data":
            msg += f"_Données insuffisantes pour ajuster les poids ({outcomes.__len__()}/{5} min)_"
        else:
            msg += f"_Poids mis à jour sur {len(outcomes)} cas historiques_"

        msg += f"\n\n{learner.get_summary()}"
        await notifier._send(msg)


async def main():
    from agents.collector import DataCollector
    from agents.analyzer  import Analyzer
    from src.memory       import Memory
    from src.notifier     import TelegramNotifier
    from src.tracker      import PerformanceTracker
    from src.learner      import PatternLearner
    from src.universe     import ALL_TICKERS, TOTAL_TICKERS

    logger.info(f"=== Investment Bot v6 — Auto-amélioration L1+L2 ===")
    logger.info(f"Univers: {TOTAL_TICKERS} tickers | Seuil: {THRESHOLD}")

    notifier  = TelegramNotifier(os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"])
    collector = DataCollector()
    analyzer  = Analyzer()
    memory    = Memory()
    tracker   = PerformanceTracker()
    learner   = PatternLearner()

    stats    = memory.get_stats()
    t_stats  = tracker.get_stats()
    coverage = memory.coverage_report(ALL_TICKERS)
    conf     = learner.get_confidence()

    await notifier._send(
        f"🔄 *Scan démarré*\n"
        f"Univers: {TOTAL_TICKERS} actions | Seuil: {THRESHOLD}/100\n"
        f"Couverture: {coverage}\n"
        f"Scans: {stats['total_scans']} | Opportunités: {stats['opportunities']}\n"
        f"Watchlist dynamique: {stats['watchlist_size']} tickers\n"
        f"Recommandations suivies: {t_stats['total_recommendations']} "
        f"({t_stats['verified']} vérifiées)\n"
        f"Auto-amélioration: {conf}"
    )

    # ── Phase auto-amélioration (avant le scan) ───────────────────
    await run_learning_phase(tracker, learner, notifier)

    # ── Scans ─────────────────────────────────────────────────────
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
            sent = await run_scan(
                collector, analyzer, memory, notifier,
                tracker, learner, attempt
            )
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
            tracker.save()
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(30)

    # ── Résumé final ──────────────────────────────────────────────
    stats_final  = memory.get_stats()
    t_stats_f    = tracker.get_stats()
    coverage_f   = memory.coverage_report(ALL_TICKERS)

    if total_sent:
        await notifier.send_summary(total_sent, total=TICKERS_SCAN * attempt)
        await notifier._send(
            f"✅ *Scan terminé*\n"
            f"{attempt} tentative(s) | {len(total_sent)} opportunité(s)\n"
            f"Couverture: {coverage_f}\n"
            f"Watchlist: {stats_final['watchlist_size']} tickers\n"
            f"Recommandations suivies: {t_stats_f['total_recommendations']}"
        )
    else:
        wl     = memory.data.get("watchlist", [])
        wl_str = ", ".join(wl[:8]) + ("..." if len(wl) > 8 else "") if wl else "vide"
        await notifier._send(
            f"⚠️ *Scan terminé — Aucune opportunité*\n"
            f"{attempt} tentative(s) | Couverture: {coverage_f}\n\n"
            f"📋 Watchlist ({stats_final['watchlist_size']}): _{wl_str}_\n\n"
            f"_Aucun ticker ne dépasse {THRESHOLD}/100 aujourd'hui._"
        )

    logger.info(f"=== Terminé : {len(total_sent)} opportunités ===")


def _p(v):
    return f"{v:+.0f}%" if v is not None else "N/D"


if __name__ == "__main__":
    asyncio.run(main())
