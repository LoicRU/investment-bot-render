"""
Scorer IA — Groq API (100% gratuit, 14 400 req/jour)
Modèle : llama-3.3-70b-versatile
Inscription : https://console.groq.com (gratuit, pas de CB)
"""
import json
import logging
import os
import re
import time
from dataclasses import dataclass

from groq import Groq

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


PROMPT = """Tu es un analyste buy-side senior spécialisé small/mid caps.
Note cette action sur 100 pts et réponds UNIQUEMENT en JSON valide.

{ticker} | {company_name} | {sector} | {industry}
Cap: {cap_m:.0f}M$ | CA+{rev_g:.0f}% | MB:{gm:.0f}% | MO:{om:.0f}% | MN:{nm:.0f}%
FCF margin:{fcfm:.0f}% | ROE:{roe:.0f}% | D/E:{de:.1f} | CR:{cr:.1f}
EV/EBITDA:{eveb:.1f}x | PE:{pe:.0f}x | PS:{ps:.1f}x
{desc}

Barème : Croissance/20 · Rentabilité/15 · Cashflow/15 · Dette/10 · Management/15 · Moat/10 · TAM/10 · Valorisation/10 · Risques(0 à -5)

{{"ticker":"{ticker}","company_name":"{company_name}","total_score":75,"scores":{{"croissance":15,"rentabilite":12,"cashflow":11,"dette":8,"management":11,"moat":8,"tam":7,"valorisation":7,"risques":-4}},"conviction":"FORTE CONVICTION","thesis":"Thèse en 2-3 phrases.","risks":"2 risques principaux.","price_target_bull":"+80% sur 3 ans","price_target_base":"+40% sur 3 ans","safety_margin":"25%"}}"""

LABELS = {90: "🚀 EXCEPTIONNEL", 80: "🟢 FORTE CONVICTION", 70: "🟡 POTENTIEL", 0: "🔴 REJET"}


def conviction_label(score: int) -> str:
    for t, l in sorted(LABELS.items(), reverse=True):
        if score >= t:
            return l
    return "🔴 REJET"


class AIScorer:
    def __init__(self):
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.model  = "llama-3.3-70b-versatile"

    def score(self, d: TickerData) -> ScoreResult | None:
        prompt = PROMPT.format(
            ticker=d.ticker, company_name=d.company_name,
            sector=d.sector, industry=d.industry,
            cap_m=d.market_cap / 1_000_000,
            rev_g=d.revenue_growth_yoy, gm=d.gross_margin,
            om=d.operating_margin, nm=d.net_margin,
            fcfm=d.fcf_margin, roe=d.roe,
            de=d.debt_to_equity, cr=d.current_ratio,
            eveb=d.ev_ebitda, pe=d.pe_ratio, ps=d.ps_ratio,
            desc=(d.description or "")[:200],
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1,
            )
            raw   = resp.choices[0].message.content.strip()
            clean = re.sub(r"```json|```", "", raw).strip()

            # Extraire le JSON si du texte parasite entoure
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                clean = match.group()

            p = json.loads(clean)
            total = int(p.get("total_score", 0))
            return ScoreResult(
                ticker=d.ticker,
                company_name=d.company_name,
                total_score=total,
                scores=p.get("scores", {}),
                conviction=p.get("conviction", conviction_label(total)),
                thesis=p.get("thesis", ""),
                risks=p.get("risks", ""),
                price_target_bull=p.get("price_target_bull", "N/A"),
                price_target_base=p.get("price_target_base", "N/A"),
                safety_margin=p.get("safety_margin", "N/A"),
            )
        except Exception as e:
            logger.error(f"Erreur scoring {d.ticker}: {e}")
            return None

    def score_batch(self, candidates: list[TickerData], max_batch: int = 30) -> list[ScoreResult]:
        # Trier par croissance décroissante, prendre les meilleurs candidats
        top = sorted(candidates, key=lambda x: x.revenue_growth_yoy, reverse=True)[:max_batch]
        results = []
        for d in top:
            logger.info(f"Scoring : {d.ticker}")
            r = self.score(d)
            if r and r.total_score >= 70:
                logger.info(f"  ✓ {r.total_score}/100 {r.conviction}")
                results.append(r)
            time.sleep(0.5)   # respecter le rate limit Groq
        return sorted(results, key=lambda r: r.total_score, reverse=True)
