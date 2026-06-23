"""
Investment Bot v5 — Mode boucle
Scanne en continu jusqu'à trouver au moins 1 opportunité.
Max 5 tentatives pour rester dans les limites Groq gratuit.
Données 100% réelles. Rien d'inventé.
"""
import asyncio
import logging
import os
import time
import random

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

THRESHOLD    = int(os.environ.get("ALERT_THRESHOLD", "55"))
MAX_ANALYZE  = int(os.environ.get("MAX_ANALYZE", "15"))
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "5"))   # max boucles
WAIT_BETWEEN = int(os.environ.get("WAIT_BETWEEN", "60"))  # secondes entre tentatives


async def run_one_scan(collector, notifier) -> list:
    """
    Lance un scan complet.
    Retourne la liste des rapports envoyés (vide si aucune opportunité).
    """
    from agents.prescorer import score as prescore
    from agents.analyzer  import Analyzer

    analyzer = Analyzer()

    # ── Collecte données réelles ──────────────────────────────────
    # Mélanger la watchlist pour varier les tickers scannés en cas de relance
    tickers = WATCHLIST.copy()
    random.shuffle(tickers)

    candidates = []
    for i, sym in enumerate(tickers, 1):
        logger.info(f"  [{i}/{len(tickers)}] {sym}")
        d = collector.collect(sym)
        if d.error or not d.current_price:
            logger.debug(f"  Skipped {sym}: {d.error or 'no price'}")
            time.sleep(0.5)
            continue
        if d.current_price <= 50 and (d.rev_growth_1y or 0) >= 5:
            candidates.append(d)
            logger.info(f"  ✓ {sym} ${d.current_price:.2f} | CA{_p(d.rev_growth_1y)} | q:{d.data_quality_score}/100")
        time.sleep(1.2)

    logger.info(f"  {len(candidates)} candidats après filtre")
    if not candidates:
        return []

    # ── Pré-scoring Python (0 token) ──────────────────────────────
    prescores = []
    for d in candidates:
        ps = prescore(d)
        logger.info(f"  Score {d.ticker}: {ps.score_global}/100 | alertes:{len(ps.alertes)}")
        prescores.append((d, ps))

    prescores.sort(key=lambda x: x[1].score_global, reverse=True)
    to_analyze = [(d, ps) for d, ps in prescores if ps.score_global >= THRESHOLD][:MAX_ANALYZE]

    if not to_analyze:
        logger.info(f"  Aucun ticker >= {THRESHOLD}/100 dans ce scan")
        return []

    logger.info(f"  {len(to_analyze)} candidats >= {THRESHOLD}/100 → IA")

    # ── Synthèse IA (1 appel par ticker) ─────────────────────────
    results = []
    for i, (d, ps) in enumerate(to_analyze, 1):
        logger.info(f"  IA [{i}/{len(to_analyze)}] {d.ticker} (score:{ps.score_global})")
        try:
            report = analyzer.analyze(d, ps)
            results.append((report, d))
            logger.info(f"  → {report.decision} | {report.conviction} | {report.etoiles}★")
        except Exception as e:
            logger.error(f"  Erreur IA {d.ticker}: {e}")
        time.sleep(0.6)

    # ── Envoi Telegram ────────────────────────────────────────────
    sent = []
    for report, d in results:
        ok = await notifier.send_report(report, d)
        if ok:
            sent.append(report)
        await asyncio.sleep(1.5)

    return sent


async def main():
    logger.info(f"=== Investment Bot v5 — Mode boucle ===")
    logger.info(f"Seuil: {THRESHOLD}/100 | Max tentatives: {MAX_ATTEMPTS} | Attente: {WAIT_BETWEEN}s")

    from agents.collector import DataCollector
    from src.notifier     import TelegramNotifier

    notifier  = TelegramNotifier(os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"])
    collector = DataCollector()

    total_sent     = []
    total_tokens   = 0
    attempt        = 0

    await notifier._send(
        f"🔄 *Scan démarré*\n"
        f"{len(WATCHLIST)} actions surveillées\n"
        f"Seuil: {THRESHOLD}/100 | Max {MAX_ATTEMPTS} tentatives\n"
        f"_Le bot tourne jusqu'à trouver une opportunité._"
    )

    while attempt < MAX_ATTEMPTS:
        attempt += 1
        logger.info(f"\n{'='*50}")
        logger.info(f"TENTATIVE {attempt}/{MAX_ATTEMPTS}")
        logger.info(f"{'='*50}")

        # Notifier le début de tentative (sauf la 1ère pour ne pas spammer)
        if attempt > 1:
            await notifier._send(
                f"🔄 *Tentative {attempt}/{MAX_ATTEMPTS}*\n"
                f"Aucune opportunité trouvée jusqu'ici — nouveau scan..."
            )

        try:
            sent = await run_one_scan(collector, notifier)
            total_tokens += MAX_ANALYZE * 700  # estimation conservative
            total_sent.extend(sent)

            if sent:
                # Opportunité(s) trouvée(s) — arrêter la boucle
                logger.info(f"✅ {len(sent)} opportunité(s) trouvée(s) — arrêt de la boucle")
                break
            else:
                logger.info(f"Aucune opportunité cette tentative")
                if attempt < MAX_ATTEMPTS:
                    logger.info(f"Attente {WAIT_BETWEEN}s avant relance...")
                    await asyncio.sleep(WAIT_BETWEEN)

        except Exception as e:
            logger.error(f"Erreur tentative {attempt}: {e}")
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(30)

    # ── Résumé final ──────────────────────────────────────────────
    if total_sent:
        await notifier.send_summary(total_sent, total=len(WATCHLIST))
        await notifier._send(
            f"✅ *Scan terminé avec succès*\n"
            f"{attempt} tentative(s) nécessaires\n"
            f"{len(total_sent)} opportunité(s) trouvée(s) et envoyées\n"
            f"~{total_tokens:,} tokens Groq utilisés"
        )
    else:
        await notifier._send(
            f"⚠️ *Scan terminé — Aucune opportunité*\n"
            f"{attempt} tentative(s) effectuées\n"
            f"Aucune action n'a dépassé le seuil de {THRESHOLD}/100 aujourd'hui.\n"
            f"_Ce résultat est honnête — mieux vaut ne rien trouver que de forcer._"
        )

    logger.info(f"=== Terminé : {len(total_sent)} opportunités | {attempt} tentatives | ~{total_tokens:,} tokens ===")


def _p(v):
    return f"{v:+.0f}%" if v is not None else "N/D"


if __name__ == "__main__":
    asyncio.run(main())
