"""
Tracker de performances — Niveau 1
Suit les recommandations passées vs prix réels.
Source de vérité : prix yfinance uniquement, jamais inventé.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("tracker")

TRACKER_FILE = Path("data/performance.json")

# Délais de suivi (jours)
CHECK_DELAYS = [30, 60, 90]

# Seuils de performance
WIN_THRESHOLD  =  10.0  # +10% = bonne décision
LOSS_THRESHOLD = -10.0  # -10% = mauvaise décision


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _days_since(date_str: str) -> int:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return 0


class PerformanceTracker:
    def __init__(self):
        TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if TRACKER_FILE.exists():
            try:
                return json.loads(TRACKER_FILE.read_text())
            except Exception as e:
                logger.warning(f"Erreur lecture tracker: {e}")
        return {
            "recommendations": {},   # ticker_date → recommandation
            "outcomes": [],          # résultats vérifiés
            "stats": {
                "total_recommendations": 0,
                "verified": 0,
                "wins": 0,
                "losses": 0,
                "neutral": 0,
            }
        }

    def save(self):
        try:
            TRACKER_FILE.write_text(json.dumps(self.data, indent=2))
        except Exception as e:
            logger.error(f"Erreur sauvegarde tracker: {e}")

    # ── Enregistrer une recommandation ───────────────────────────
    def record(self, ticker: str, decision: str, price: float,
               score: int, scores: dict):
        """Enregistre une recommandation avec le prix d'entrée réel."""
        if price is None or price <= 0:
            return
        key = f"{ticker}_{_today()}"
        self.data["recommendations"][key] = {
            "ticker":    ticker,
            "date":      _today(),
            "decision":  decision,
            "price_in":  round(price, 4),
            "score":     score,
            "scores":    scores,
            "checks":    {},   # {30: prix, 60: prix, 90: prix}
            "outcome":   None, # "win" / "loss" / "neutral" / None
        }
        self.data["stats"]["total_recommendations"] += 1
        logger.info(f"  📝 Recommandation enregistrée: {ticker} @ ${price:.2f} ({decision})")

    # ── Vérifier les performances passées ────────────────────────
    def check_past(self) -> list:
        """
        Récupère les prix actuels pour les recommandations non vérifiées.
        Retourne la liste des vérifications effectuées.
        """
        import yfinance as yf

        updates = []
        for key, rec in self.data["recommendations"].items():
            if rec.get("outcome") == "verified_final":
                continue

            days = _days_since(rec["date"])
            ticker = rec["ticker"]

            # Vérifier aux jalons 30/60/90j
            for delay in CHECK_DELAYS:
                check_key = str(delay)
                if days >= delay and check_key not in rec["checks"]:
                    try:
                        tk   = yf.Ticker(ticker)
                        info = tk.info or {}
                        price_now = info.get("currentPrice") or info.get("regularMarketPrice")
                        if price_now:
                            price_now = float(price_now)
                            pct_change = round((price_now - rec["price_in"]) / rec["price_in"] * 100, 2)
                            rec["checks"][check_key] = {
                                "price":  round(price_now, 4),
                                "change": pct_change,
                                "date":   _today(),
                            }
                            updates.append({
                                "ticker":    ticker,
                                "delay":     delay,
                                "price_in":  rec["price_in"],
                                "price_now": price_now,
                                "change":    pct_change,
                                "decision":  rec["decision"],
                            })
                            logger.info(f"  📊 {ticker} J+{delay}: {pct_change:+.1f}% (${rec['price_in']} → ${price_now:.2f})")
                        import time
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"  Erreur check {ticker} J+{delay}: {e}")

            # Calculer l'outcome final à J+90
            if "90" in rec["checks"] and rec.get("outcome") != "verified_final":
                change_90 = rec["checks"]["90"]["change"]
                if change_90 >= WIN_THRESHOLD:
                    rec["outcome"] = "win"
                elif change_90 <= LOSS_THRESHOLD:
                    rec["outcome"] = "loss"
                else:
                    rec["outcome"] = "neutral"
                rec["outcome_final"] = "verified_final"

                self.data["outcomes"].append({
                    "ticker":   ticker,
                    "decision": rec["decision"],
                    "score":    rec["score"],
                    "scores":   rec["scores"],
                    "change_30": rec["checks"].get("30", {}).get("change"),
                    "change_60": rec["checks"].get("60", {}).get("change"),
                    "change_90": change_90,
                    "outcome":  rec["outcome"],
                })
                self._update_stats()

        if updates:
            self.save()
        return updates

    def _update_stats(self):
        outcomes = self.data["outcomes"]
        self.data["stats"]["verified"] = len(outcomes)
        self.data["stats"]["wins"]     = sum(1 for o in outcomes if o["outcome"] == "win")
        self.data["stats"]["losses"]   = sum(1 for o in outcomes if o["outcome"] == "loss")
        self.data["stats"]["neutral"]  = sum(1 for o in outcomes if o["outcome"] == "neutral")

    def get_stats(self) -> dict:
        s = self.data["stats"]
        verified = s["verified"]
        win_rate = round(s["wins"] / verified * 100, 1) if verified > 0 else None
        return {**s, "win_rate": win_rate}

    def get_outcomes(self) -> list:
        return self.data["outcomes"]
