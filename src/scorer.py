"""
Scorer IA - Analyse fondamentale via Claude API
Version optimisée tokens : prompt compact, haiku au lieu de sonnet,
batch limité pour rester dans le free tier.
"""
import json
import logging
import os
import re
from dataclasses import dataclass

import anthropic

from src.screener import TickerData

logger = logging.getLogger("scorer")


@dataclass
class ScoreResult:
    ticker: str
    company_name: str
    total_score: int
    scores: dict
    conviction: str
    thesis: str
    risks: str
    price_target_bull: str
    price_target_base: str
    safety_margin: str
    raw_response: str = ""


# Prompt compact — 3x moins de tokens que la version complète
SCORING_PROMPT = """Analyste buy-side senior. Note cette action sur 100 pts.

{ticker} | {company_name} | {sector}
Cap: {market_cap_m:.0f}M$ | CA+{revenue_growth:.0f}% | MB:{gross_margin:.0f}% | MO:{operating_margin:.0f}% | MN:{net_margin:.0f}%
FCF:{fcf_margin:.0f}% | ROE:{roe:.0f}% | D/E:{debt_to_equity:.1f} | CR:{current_ratio:.1f}
EV/EBITDA:{ev_ebitda:.1f}x | PE:{pe_ratio:.0f}x | PS:{ps_ratio:.1f}x
{description_short}

JSON UNIQUEMENT (pas de texte avant/après) :
{{"ticker":"{ticker}","company_name":"{company_name}","total_score":0,"scores":{{"croissance":0,"rentabilite":0,"cashflow":0,"dette":0,"management":0,"moat":0,"tam":0,"valorisation":0,"risques":0}},"max_scores":{{"croissance":20,"rentabilite":15,"cashflow":15,"dette":10,"management":15,"moat":10,"tam":10,"valorisation":10,"risques":0}},"conviction":"FORTE CONVICTION","thesis":"3 phrases max.","risks":"2 risques max.","price_target_bull":"+X% sur 3 ans","price_target_base":"+Y% sur 3 ans","safety_margin":"Z%"}}"""

CONVICTION_LABELS = {90: "EXCEPTIONNEL", 80: "FORTE CONVICTION", 70: "POTENTIEL", 0: "REJET"}


class AIScorer:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        # haiku-3 = ~20x moins cher que sonnet, largement suffisant pour le scoring
        self.model = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

    def _conviction(self, score: int) -> str:
        for t, l in sorted(CONVICTION_LABELS.items(), reverse=True):
            if score >= t:
                return l
        return "REJET"

    def score_ticker(self, data: TickerData) -> ScoreResult | None:
        prompt = SCORING_PROMPT.format(
            ticker=data.ticker,
            company_name=data.company_name,
            sector=data.sector,
            market_cap_m=data.market_cap / 1_000_000,
            revenue_growth=data.revenue_growth_yoy,
            gross_margin=data.gross_margin,
            operating_margin=data.operating_margin,
            net_margin=data.net_margin,
            fcf_margin=data.fcf_margin,
            roe=data.roe,
            debt_to_equity=data.debt_to_equity,
            current_ratio=data.current_ratio,
            ev_ebitda=data.ev_ebitda,
            pe_ratio=data.pe_ratio,
            ps_ratio=data.ps_ratio,
            description_short=(data.description or "")[:200],
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=600,       # réduit pour économiser
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            clean = re.sub(r"```json|```", "", raw).strip()
            parsed = json.loads(clean)
            total = parsed.get("total_score", 0)
            return ScoreResult(
                ticker=data.ticker,
                company_name=data.company_name,
                total_score=total,
                scores=parsed.get("scores", {}),
                conviction=parsed.get("conviction", self._conviction(total)),
                thesis=parsed.get("thesis", ""),
                risks=parsed.get("risks", ""),
                price_target_bull=parsed.get("price_target_bull", "N/A"),
                price_target_base=parsed.get("price_target_base", "N/A"),
                safety_margin=parsed.get("safety_margin", "N/A"),
                raw_response=raw,
            )
        except Exception as e:
            logger.error(f"Erreur scoring {data.ticker}: {e}")
            return None

    def score_batch(self, candidates: list[TickerData], max_batch: int = 20) -> list[ScoreResult]:
        """
        max_batch : limite le nombre de tickers scorés par IA par scan
        pour rester dans le free tier (~20 appels × 800 tokens = ~16K tokens/scan)
        """
        # Trier par croissance décroissante pour scorer les meilleurs en premier
        sorted_candidates = sorted(
            candidates,
            key=lambda d: d.revenue_growth_yoy,
            reverse=True
        )[:max_batch]

        results = []
        for data in sorted_candidates:
            logger.info(f"Scoring IA ({self.model}): {data.ticker}")
            result = self.score_ticker(data)
            if result and result.total_score >= 70:
                logger.info(f"  → {result.total_score}/100 ({result.conviction})")
                results.append(result)
        return sorted(results, key=lambda r: r.total_score, reverse=True)
