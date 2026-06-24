"""
Système de mémoire — fichier JSON persistant sur GitHub
Gère :
- Rotation des tickers (évite de rescanner les mêmes)
- Cooldown par ticker (pas rescanner avant N semaines)
- Watchlist dynamique (tickers à surveiller de près)
- Historique des scores
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("memory")

MEMORY_FILE  = Path("data/memory.json")
COOLDOWN_DAYS_DEFAULT    = 21   # 3 semaines avant de rescanner un ticker normal
COOLDOWN_DAYS_WATCHLIST  = 7    # 1 semaine pour les tickers en watchlist
COOLDOWN_DAYS_REJECTED   = 60   # 2 mois pour les tickers clairement rejetés
TICKERS_PER_SCAN         = 40   # tickers analysés par scan


def _today() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")


def _days_since(date_str: str) -> int:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return (datetime.now(timezone.utc).replace(tzinfo=None) - dt).days
    except Exception:
        return 999


class Memory:
    def __init__(self):
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Erreur lecture mémoire: {e}")
        return {
            "tickers": {},       # ticker → {last_scan, last_score, status, scan_count}
            "watchlist": [],     # tickers à surveiller prioritairement
            "stats": {
                "total_scans": 0,
                "total_tickers_seen": 0,
                "opportunities_found": 0,
                "created": _today(),
            }
        }

    def save(self):
        try:
            with open(MEMORY_FILE, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde mémoire: {e}")

    # ── Statut d'un ticker ────────────────────────────────────────
    def get_ticker_info(self, ticker: str) -> dict:
        return self.data["tickers"].get(ticker, {})

    def update_ticker(self, ticker: str, score: int, decision: str):
        info = self.data["tickers"].get(ticker, {
            "last_scan": None, "last_score": None,
            "best_score": 0, "scan_count": 0,
            "status": "unknown", "decision": None,
        })
        info["last_scan"]  = _today()
        info["last_score"] = score
        info["scan_count"] = info.get("scan_count", 0) + 1
        info["decision"]   = decision
        info["best_score"] = max(info.get("best_score", 0), score)

        # Statut basé sur le score
        if score >= 70:
            info["status"] = "watchlist"
        elif score >= 55:
            info["status"] = "interesting"
        elif score < 40:
            info["status"] = "rejected"
        else:
            info["status"] = "neutral"

        self.data["tickers"][ticker] = info

        # Auto-ajout à la watchlist si score élevé
        if score >= 70 and ticker not in self.data["watchlist"]:
            self.data["watchlist"].append(ticker)
            logger.info(f"  ★ {ticker} ajouté à la watchlist (score: {score})")

        # Retrait de la watchlist si score chute
        if score < 45 and ticker in self.data["watchlist"]:
            self.data["watchlist"].remove(ticker)
            logger.info(f"  ✗ {ticker} retiré de la watchlist (score: {score})")

    # ── Cooldown ──────────────────────────────────────────────────
    def is_on_cooldown(self, ticker: str) -> bool:
        info = self.get_ticker_info(ticker)
        if not info.get("last_scan"):
            return False  # jamais scanné → pas de cooldown

        days = _days_since(info["last_scan"])
        status = info.get("status", "unknown")

        if status == "watchlist":
            return days < COOLDOWN_DAYS_WATCHLIST
        elif status == "rejected":
            return days < COOLDOWN_DAYS_REJECTED
        else:
            return days < COOLDOWN_DAYS_DEFAULT

    # ── Sélection des tickers pour le prochain scan ───────────────
    def select_tickers(self, all_tickers: list, core_watchlist: list, n: int = TICKERS_PER_SCAN) -> list:
        """
        Sélectionne N tickers pour le prochain scan en prioritisant :
        1. Core watchlist (toujours incluse)
        2. Tickers en watchlist dynamique (cooldown court)
        3. Tickers jamais vus
        4. Tickers dont le cooldown est expiré (rotation)
        Exclut les tickers en cooldown actif.
        """
        selected = []
        seen_set = set()

        def add(t):
            if t not in seen_set:
                seen_set.add(t)
                selected.append(t)

        # Priorité 1 : core watchlist (toujours)
        for t in core_watchlist:
            if not self.is_on_cooldown(t):
                add(t)

        # Priorité 2 : watchlist dynamique (bons scores passés)
        for t in self.data.get("watchlist", []):
            if len(selected) >= n: break
            if not self.is_on_cooldown(t):
                add(t)

        # Priorité 3 : jamais vus
        never_seen = [t for t in all_tickers
                      if t not in self.data["tickers"] and t not in seen_set]
        import random
        random.shuffle(never_seen)
        for t in never_seen:
            if len(selected) >= n: break
            add(t)

        # Priorité 4 : cooldown expiré, pas rejeté
        if len(selected) < n:
            expired = [
                t for t in all_tickers
                if t not in seen_set
                and not self.is_on_cooldown(t)
                and self.data["tickers"].get(t, {}).get("status") != "rejected"
            ]
            random.shuffle(expired)
            for t in expired:
                if len(selected) >= n: break
                add(t)

        # Priorité 5 : si encore de la place, prendre des rejetés anciens
        if len(selected) < n:
            old_rejected = [
                t for t in all_tickers
                if t not in seen_set
                and not self.is_on_cooldown(t)
            ]
            random.shuffle(old_rejected)
            for t in old_rejected:
                if len(selected) >= n: break
                add(t)

        return selected[:n]

    # ── Stats ─────────────────────────────────────────────────────
    def increment_scan(self):
        self.data["stats"]["total_scans"] = self.data["stats"].get("total_scans", 0) + 1

    def increment_opportunity(self):
        self.data["stats"]["opportunities_found"] = self.data["stats"].get("opportunities_found", 0) + 1

    def get_stats(self) -> dict:
        s = self.data["stats"]
        tickers = self.data["tickers"]
        return {
            "total_scans":        s.get("total_scans", 0),
            "total_tickers_seen": len(tickers),
            "opportunities":      s.get("opportunities_found", 0),
            "watchlist_size":     len(self.data.get("watchlist", [])),
            "rejected":           sum(1 for v in tickers.values() if v.get("status") == "rejected"),
            "never_seen":         0,  # calculé à la demande
            "created":            s.get("created", "N/D"),
        }

    def coverage_report(self, all_tickers: list) -> str:
        seen   = len(self.data["tickers"])
        total  = len(all_tickers)
        pct    = round(seen / total * 100, 1) if total > 0 else 0
        wl     = len(self.data.get("watchlist", []))
        return f"{seen}/{total} ({pct}%) | watchlist: {wl}"
