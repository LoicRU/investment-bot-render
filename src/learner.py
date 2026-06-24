"""
Apprenant de patterns — Niveau 2
Analyse les outcomes historiques pour détecter quels critères
prédisent réellement les hausses.
Source : uniquement les données vérifiées dans performance.json.
Aucune valeur inventée — si pas assez de données, dit honnêtement.
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("learner")

PATTERNS_FILE   = Path("data/patterns.json")
MIN_SAMPLES     = 5    # minimum de données vérifiées pour tirer des conclusions

# Pondérations par défaut du prescorer (à ajuster par apprentissage)
DEFAULT_WEIGHTS = {
    "croissance":   0.25,
    "rentabilite":  0.20,
    "cashflow":     0.20,
    "bilan":        0.10,
    "management":   0.10,
    "valorisation": 0.15,
}


class PatternLearner:
    def __init__(self):
        PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if PATTERNS_FILE.exists():
            try:
                return json.loads(PATTERNS_FILE.read_text())
            except Exception as e:
                logger.warning(f"Erreur lecture patterns: {e}")
        return {
            "weights":          DEFAULT_WEIGHTS.copy(),
            "feature_stats":    {},   # corrélation par critère
            "sector_stats":     {},   # performance par secteur
            "score_buckets":    {},   # win rate par tranche de score
            "last_update":      None,
            "samples_used":     0,
            "confidence":       "insufficient_data",
        }

    def save(self):
        try:
            PATTERNS_FILE.write_text(json.dumps(self.data, indent=2))
        except Exception as e:
            logger.error(f"Erreur sauvegarde patterns: {e}")

    # ── Analyse des outcomes ──────────────────────────────────────
    def learn(self, outcomes: list) -> dict:
        """
        Analyse les outcomes vérifiés et met à jour les pondérations.
        Retourne un résumé des apprentissages.
        """
        if len(outcomes) < MIN_SAMPLES:
            logger.info(f"  Apprentissage : {len(outcomes)} outcomes — insuffisant (min {MIN_SAMPLES})")
            self.data["confidence"] = f"insufficient_data ({len(outcomes)}/{MIN_SAMPLES})"
            self.save()
            return {"status": "insufficient_data", "samples": len(outcomes)}

        logger.info(f"  Apprentissage sur {len(outcomes)} outcomes vérifiés")
        self.data["samples_used"] = len(outcomes)

        # 1. Corrélation de chaque sous-score avec l'outcome
        self._analyze_feature_correlations(outcomes)

        # 2. Performance par tranche de score global
        self._analyze_score_buckets(outcomes)

        # 3. Ajustement des poids (prudent — max ±20% de variation)
        new_weights = self._compute_new_weights(outcomes)
        self.data["weights"] = new_weights

        self.data["confidence"] = "low" if len(outcomes) < 20 else \
                                  "medium" if len(outcomes) < 50 else "high"
        from src.tracker import _today
        self.data["last_update"] = _today()
        self.save()

        return {
            "status":     "updated",
            "samples":    len(outcomes),
            "confidence": self.data["confidence"],
            "weights":    new_weights,
        }

    def _analyze_feature_correlations(self, outcomes: list):
        """Calcule la corrélation entre chaque critère et l'outcome."""
        criteria = ["croissance", "rentabilite", "cashflow", "bilan", "management", "valorisation"]

        for criterion in criteria:
            wins   = [o for o in outcomes if o.get("outcome") == "win"    and o.get("scores", {}).get(criterion) is not None]
            losses = [o for o in outcomes if o.get("outcome") == "loss"   and o.get("scores", {}).get(criterion) is not None]
            all_v  = [o for o in outcomes if o.get("scores", {}).get(criterion) is not None]

            if len(all_v) < 3:
                continue

            avg_score_wins   = sum(o["scores"][criterion] for o in wins)   / len(wins)   if wins   else None
            avg_score_losses = sum(o["scores"][criterion] for o in losses) / len(losses) if losses else None

            # Corrélation simple : un score élevé dans ce critère prédit-il un win ?
            high_score = [o for o in all_v if o["scores"][criterion] >= 70]
            if high_score:
                win_rate_high = sum(1 for o in high_score if o["outcome"] == "win") / len(high_score)
            else:
                win_rate_high = None

            self.data["feature_stats"][criterion] = {
                "avg_score_wins":   round(avg_score_wins, 1)   if avg_score_wins   is not None else None,
                "avg_score_losses": round(avg_score_losses, 1) if avg_score_losses is not None else None,
                "win_rate_if_high": round(win_rate_high * 100, 1) if win_rate_high is not None else None,
                "n_wins":    len(wins),
                "n_losses":  len(losses),
            }

    def _analyze_score_buckets(self, outcomes: list):
        """Win rate par tranche de score global (55-64, 65-74, 75-84, 85+)."""
        buckets = {"55-64": [], "65-74": [], "75-84": [], "85+": []}
        for o in outcomes:
            s = o.get("score", 0)
            if   s >= 85: buckets["85+"].append(o)
            elif s >= 75: buckets["75-84"].append(o)
            elif s >= 65: buckets["65-74"].append(o)
            elif s >= 55: buckets["55-64"].append(o)

        result = {}
        for bucket, items in buckets.items():
            if not items:
                result[bucket] = {"win_rate": None, "n": 0}
                continue
            win_rate = sum(1 for o in items if o["outcome"] == "win") / len(items) * 100
            avg_change = sum(o.get("change_90", 0) or 0 for o in items) / len(items)
            result[bucket] = {
                "win_rate":  round(win_rate, 1),
                "avg_change_90j": round(avg_change, 1),
                "n":         len(items),
            }
        self.data["score_buckets"] = result

    def _compute_new_weights(self, outcomes: list) -> dict:
        """
        Ajuste les pondérations selon les corrélations observées.
        Variation max ±20% par rapport aux poids par défaut.
        Prudent : ne change pas ce qu'on ne comprend pas encore.
        """
        current = self.data["weights"].copy()
        stats   = self.data["feature_stats"]

        if len(outcomes) < 15:
            # Pas assez de données — garder les poids par défaut
            logger.info("  Poids inchangés (données insuffisantes pour ajustement)")
            return current

        new_weights = {}
        for criterion, default_w in DEFAULT_WEIGHTS.items():
            stat = stats.get(criterion, {})
            win_rate = stat.get("win_rate_if_high")

            if win_rate is None:
                new_weights[criterion] = current.get(criterion, default_w)
                continue

            # Si win_rate > 60% quand score élevé → augmenter le poids
            # Si win_rate < 40% → diminuer le poids
            if   win_rate >= 70: adjustment = +0.03
            elif win_rate >= 60: adjustment = +0.01
            elif win_rate <= 30: adjustment = -0.03
            elif win_rate <= 40: adjustment = -0.01
            else:                adjustment = 0.0

            # Bornes : ±20% des poids par défaut
            min_w = default_w * 0.80
            max_w = default_w * 1.20
            new_w = max(min_w, min(max_w, current.get(criterion, default_w) + adjustment))
            new_weights[criterion] = round(new_w, 4)

        # Normaliser pour que la somme = 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: round(v / total, 4) for k, v in new_weights.items()}

        logger.info(f"  Nouveaux poids: {new_weights}")
        return new_weights

    # ── Getters ───────────────────────────────────────────────────
    def get_weights(self) -> dict:
        return self.data.get("weights", DEFAULT_WEIGHTS.copy())

    def get_confidence(self) -> str:
        return self.data.get("confidence", "insufficient_data")

    def get_summary(self) -> str:
        """Résumé lisible pour Telegram."""
        conf    = self.data.get("confidence", "insufficient_data")
        n       = self.data.get("samples_used", 0)
        buckets = self.data.get("score_buckets", {})
        stats   = self.data.get("feature_stats", {})

        if n < MIN_SAMPLES:
            return f"_Auto-amélioration : données insuffisantes ({n}/{MIN_SAMPLES} outcomes vérifiés)_"

        lines = [f"*Auto-amélioration* — {n} outcomes | Confiance: {conf}"]

        # Meilleur critère prédictif
        best = max(stats.items(),
                   key=lambda x: x[1].get("win_rate_if_high") or 0,
                   default=(None, {}))
        if best[0] and best[1].get("win_rate_if_high"):
            lines.append(f"Critère le plus prédictif: *{best[0]}* ({best[1]['win_rate_if_high']}% win rate)")

        # Win rate par tranche
        for bucket, data in sorted(buckets.items()):
            if data["n"] > 0:
                lines.append(f"Score {bucket}: {data['win_rate']}% wins ({data['n']} cas) | avg +{data['avg_change_90j']}%")

        return "\n".join(lines)
