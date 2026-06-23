"""
Scorer IA complet — analyse fondamentale profonde via Groq
Joue le rôle d'analyste financier + gestionnaire de portefeuille
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
    current_price: float
    total_score: int
    scores: dict
    conviction: str           # FORT / MOYEN / FAIBLE
    decision: str             # ACHETER / SURVEILLER / EVITER
    probability_up: int       # % probabilité hausse 12 mois
    probability_down: int     # % probabilité baisse 12 mois
    entry_price: str
    target_5y: str
    thesis: str
    risks: str
    scenario_bull: str
    scenario_base: str
    scenario_bear: str
    upside_analyst: float     # % upside vs target analystes
    safety_margin: str


PROMPT = """Tu es un analyste buy-side senior + gestionnaire de portefeuille avec 20 ans d'expérience.
Analyse cette action en profondeur et réponds UNIQUEMENT en JSON valide.

=== DONNÉES COMPLÈTES ===
Ticker: {ticker} | {company_name}
Secteur: {sector} | {industry}
Employés: {employees}

PRIX & MARCHÉ:
Prix actuel: ${price:.2f} | Cap: {cap_m:.0f}M$
52S High: ${w52h:.2f} | Low: ${w52l:.2f}
Perf 1M: {p1m:.1f}% | 3M: {p3m:.1f}% | 1Y: {p1y:.1f}%
Beta: {beta:.2f} | Volume moy: {vol:,.0f}
Insider: {insider:.1f}% | Institutionnels: {instit:.1f}%
Short ratio: {short:.1f}

FINANCIERS:
CA: ${rev_m:.0f}M | Croissance: +{rev_g:.1f}%
Marge brute: {gm:.1f}% | Marge op: {om:.1f}% | Marge nette: {nm:.1f}%
EBITDA: ${ebitda_m:.0f}M | EPS: ${eps:.2f}
FCF: ${fcf_m:.0f}M | FCF margin: {fcfm:.1f}%
Cash: ${cash_m:.0f}M | Dette: ${debt_m:.0f}M
ROE: {roe:.1f}% | ROA: {roa:.1f}%
D/E: {de:.2f} | Current ratio: {cr:.2f} | Quick: {qr:.2f}

VALORISATION:
PE: {pe:.1f}x | PB: {pb:.1f}x | PS: {ps:.1f}x
EV/EBITDA: {eveb:.1f}x | PEG: {peg:.2f}

ANALYSTES:
Target consensus: ${target:.2f} | Reco: {reco} | Nb analystes: {nb_ana}

DESCRIPTION:
{desc}

=== MISSION ===
En tant qu'analyste senior, évalue cette action comme si tu allais investir ton propre argent.
Note sur 100 pts selon ce barème:
- Croissance (20pts): vitesse, qualité, durabilité
- Rentabilité (15pts): marges, trajectoire
- Cash-flow (15pts): FCF, conversion
- Dette (10pts): solidité bilan
- Management (10pts): alignement, track record
- Avantage concurrentiel (10pts): moat, barrières
- Marché (10pts): TAM, croissance secteur
- Valorisation (10pts): cherté vs croissance

Estime la probabilité que l'action monte ou baisse dans les 12 prochains mois.

JSON UNIQUEMENT (pas de texte avant/après):
{{"ticker":"{ticker}","company_name":"{company_name}","total_score":0,"scores":{{"croissance":0,"rentabilite":0,"cashflow":0,"dette":0,"management":0,"moat":0,"marche":0,"valorisation":0}},"conviction":"FORT","decision":"ACHETER","probability_up":60,"probability_down":25,"entry_price":"$X.XX (dans cette zone)","target_5y":"$XX.XX (+XX% soit Xbagger)","thesis":"Thèse en 3 phrases: avantage concurrentiel + catalyseur de croissance + pourquoi maintenant.","risks":"3 risques principaux numérotés.","scenario_bull":"Scénario optimiste 3 ans: conditions + objectif prix.","scenario_base":"Scénario de base 3 ans: conditions + objectif prix.","scenario_bear":"Scénario pessimiste 3 ans: conditions + objectif prix.","safety_margin":"XX%"}}"""


class AIScorer:
    def __init__(self):
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.model  = "llama-3.3-70b-versatile"

    def _label(self, score):
        if score >= 85: return "🚀 EXCEPTIONNEL"
        if score >= 75: return "🟢 FORT"
        if score >= 65: return "🟡 MOYEN"
        return "🔴 FAIBLE"

    def _upside(self, d: TickerData) -> float:
        if d.analyst_target > 0 and d.current_price > 0:
            return ((d.analyst_target - d.current_price) / d.current_price) * 100
        return 0

    def score(self, d: TickerData) -> ScoreResult | None:
        prompt = PROMPT.format(
            ticker=d.ticker, company_name=d.company_name,
            sector=d.sector, industry=d.industry, employees=d.employees,
            price=d.current_price,
            cap_m=d.market_cap/1e6,
            w52h=d.week52_high, w52l=d.week52_low,
            p1m=d.perf_1m, p3m=d.perf_3m, p1y=d.perf_1y,
            beta=d.beta, vol=d.avg_volume,
            insider=d.insider_ownership, instit=d.institutional_ownership,
            short=d.short_ratio,
            rev_m=d.revenue/1e6, rev_g=d.revenue_growth_yoy,
            gm=d.gross_margin, om=d.operating_margin, nm=d.net_margin,
            ebitda_m=d.ebitda/1e6, eps=d.eps,
            fcf_m=d.fcf/1e6, fcfm=d.fcf_margin,
            cash_m=d.cash/1e6, debt_m=d.total_debt/1e6,
            roe=d.roe, roa=d.roa,
            de=d.debt_to_equity, cr=d.current_ratio, qr=d.quick_ratio,
            pe=d.pe_ratio, pb=d.pb_ratio, ps=d.ps_ratio,
            eveb=d.ev_ebitda, peg=d.peg_ratio,
            target=d.analyst_target, reco=d.analyst_recommendation,
            nb_ana=d.nb_analysts,
            desc=(d.description or "")[:300],
        )
        try:
            resp  = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.1,
            )
            raw   = resp.choices[0].message.content.strip()
            clean = re.sub(r"```json|```", "", raw).strip()
            m     = re.search(r"\{.*\}", clean, re.DOTALL)
            if m: clean = m.group()
            p     = json.loads(clean)
            total = int(p.get("total_score", 0))
            return ScoreResult(
                ticker=d.ticker,
                company_name=d.company_name,
                current_price=d.current_price,
                total_score=total,
                scores=p.get("scores", {}),
                conviction=p.get("conviction", self._label(total)),
                decision=p.get("decision", "SURVEILLER"),
                probability_up=int(p.get("probability_up", 50)),
                probability_down=int(p.get("probability_down", 30)),
                entry_price=p.get("entry_price", "N/A"),
                target_5y=p.get("target_5y", "N/A"),
                thesis=p.get("thesis", ""),
                risks=p.get("risks", ""),
                scenario_bull=p.get("scenario_bull", ""),
                scenario_base=p.get("scenario_base", ""),
                scenario_bear=p.get("scenario_bear", ""),
                upside_analyst=self._upside(d),
                safety_margin=p.get("safety_margin", "N/A"),
            )
        except Exception as e:
            logger.error(f"Erreur scoring {d.ticker}: {e}")
            return None

    def score_batch(self, candidates, max_batch=25):
        # Trier par croissance CA décroissante
        top = sorted(candidates, key=lambda x: x.revenue_growth_yoy, reverse=True)[:max_batch]
        results = []
        for d in top:
            logger.info(f"Scoring IA: {d.ticker} ${d.current_price:.2f}")
            r = self.score(d)
            if r and r.total_score >= 60:
                logger.info(f"  ✓ {r.total_score}/100 | {r.decision} | ↑{r.probability_up}% ↓{r.probability_down}%")
                results.append(r)
            time.sleep(0.5)
        return sorted(results, key=lambda r: r.total_score, reverse=True)
