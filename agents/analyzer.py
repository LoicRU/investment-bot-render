"""
Agents 2-9 — Analyse multi-agents via Groq (Llama 3.3 70B)
Chaque agent a un rôle précis et travaille sur des données réelles.
Honnêteté totale : si données manquantes, l'agent le dit.
"""
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from groq import Groq
from agents.collector import CompanyData

logger = logging.getLogger("analyzer")


@dataclass
class AgentReport:
    agent_name: str
    score: Optional[int]      = None   # /100 si applicable
    summary: str              = ""
    details: dict             = field(default_factory=dict)
    missing_data: list        = field(default_factory=list)
    error: Optional[str]      = None


@dataclass
class FinalReport:
    ticker: str
    company_name: str
    current_price: Optional[float]

    # Scores par dimension
    score_qualite: Optional[int]       = None
    score_croissance: Optional[int]    = None
    score_rentabilite: Optional[int]   = None
    score_management: Optional[int]    = None
    score_valorisation: Optional[int]  = None
    score_risque: Optional[int]        = None
    score_global: Optional[int]        = None

    # Conviction
    etoiles: int                       = 0     # 1-5
    conviction: str                    = ""    # TRÈS FORT / FORT / MOYEN / FAIBLE
    decision: str                      = ""    # ACHAT FORT / ACHAT / SURVEILLER / ÉVITER

    # Valeurs réelles
    valeur_intrinseque: Optional[float] = None
    potentiel_estime: Optional[float]   = None
    scenario_pessimiste: Optional[str]  = None
    scenario_moyen: Optional[str]       = None
    scenario_optimiste: Optional[str]   = None

    # Rapports agents
    agent_reports: list                = field(default_factory=list)
    data_quality: int                  = 0
    missing_fields: list               = field(default_factory=list)


def _fmt_num(v, unit="", decimals=1):
    """Formate un nombre réel ou retourne 'N/D' si None."""
    if v is None:
        return "N/D"
    if abs(v) >= 1e9:
        return f"{v/1e9:.{decimals}f}Md{unit}"
    if abs(v) >= 1e6:
        return f"{v/1e6:.{decimals}f}M{unit}"
    return f"{v:.{decimals}f}{unit}"


def _pct_str(v):
    return f"{v:+.1f}%" if v is not None else "N/D"


class MultiAgentAnalyzer:
    def __init__(self):
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.model  = "llama-3.3-70b-versatile"

    def _call(self, system: str, user: str, max_tokens: int = 600) -> dict:
        """Appel Groq avec extraction JSON robuste."""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                max_tokens=max_tokens,
                temperature=0.05,
            )
            raw   = resp.choices[0].message.content.strip()
            clean = re.sub(r"```json|```", "", raw).strip()
            m     = re.search(r"\{.*\}", clean, re.DOTALL)
            return json.loads(m.group()) if m else {}
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return {}

    # ── Agent 2 : Analyste financier ─────────────────────────────
    def agent_financial(self, d: CompanyData) -> AgentReport:
        user = f"""Données RÉELLES de {d.ticker} ({d.company_name}):

CA: {_fmt_num(d.revenue,'$')} | Croissance 1Y: {_pct_str(d.rev_growth_1y)} | 3Y CAGR: {_pct_str(d.rev_growth_3y_cagr)} | 5Y CAGR: {_pct_str(d.rev_growth_5y_cagr)}
Marge brute: {_pct_str(d.gross_margin)} | Marge op: {_pct_str(d.operating_margin)} | Marge nette: {_pct_str(d.net_margin)}
EBITDA: {_fmt_num(d.ebitda,'$')} | Résultat net: {_fmt_num(d.net_income,'$')} | EPS: {_fmt_num(d.eps_ttm,'$')}
FCF: {_fmt_num(d.fcf,'$')} | FCF margin: {_pct_str(d.fcf_margin)} | R&D: {_fmt_num(d.rd_expense,'$')}
ROE: {_pct_str(d.roe)} | ROA: {_pct_str(d.roa)}
Cash: {_fmt_num(d.cash,'$')} | Dette: {_fmt_num(d.total_debt,'$')} | D/E: {_fmt_num(d.debt_to_equity)} | CR: {_fmt_num(d.current_ratio)} | QR: {_fmt_num(d.quick_ratio)}
Données manquantes: {', '.join(d.missing_fields) or 'aucune'}

Analyse ces données RÉELLES. Sois honnête si des données manquent.
JSON: {{"score":75,"resume":"3 phrases max sur la santé financière réelle.","forces":["force1","force2"],"faiblesses":["faiblesse1"],"donnees_manquantes":[]}}"""

        r = self._call("Tu es un analyste financier CFA. Analyse uniquement les données fournies. Si une donnée est manquante, dis-le.", user)
        return AgentReport(
            agent_name="Analyste Financier",
            score=r.get("score"),
            summary=r.get("resume", ""),
            details={"forces": r.get("forces",[]), "faiblesses": r.get("faiblesses",[])},
            missing_data=r.get("donnees_manquantes", []),
        )

    # ── Agent 3 : Analyste croissance ────────────────────────────
    def agent_growth(self, d: CompanyData) -> AgentReport:
        user = f"""Données croissance RÉELLES de {d.ticker}:

CA actuel: {_fmt_num(d.revenue,'$')}
CA il y a 1 an: {_fmt_num(d.revenue_1y_ago,'$')} → croissance: {_pct_str(d.rev_growth_1y)}
CA il y a 3 ans: {_fmt_num(d.revenue_3y_ago,'$')} → CAGR 3Y: {_pct_str(d.rev_growth_3y_cagr)}
CA il y a 5 ans: {_fmt_num(d.revenue_5y_ago,'$')} → CAGR 5Y: {_pct_str(d.rev_growth_5y_cagr)}
Croissance bénéfice net 1Y: {_pct_str(d.net_income_growth_1y)}
Marge brute évolution: {_pct_str(d.gross_margin)}
Employés: {d.employees or 'N/D'}
Secteur: {d.sector} | {d.industry}
Performance boursière: 1M:{_pct_str(d.perf_1m)} 3M:{_pct_str(d.perf_3m)} 1Y:{_pct_str(d.perf_1y)} 3Y:{_pct_str(d.perf_3y)} 5Y:{_pct_str(d.perf_5y)}

Analyse la trajectoire de croissance réelle. Note les données manquantes.
JSON: {{"score":70,"resume":"évaluation honnête de la croissance.","acceleration":true,"durable":true,"donnees_manquantes":[]}}"""

        r = self._call("Tu es un analyste growth spécialisé. Base-toi uniquement sur les chiffres réels fournis.", user)
        return AgentReport(
            agent_name="Analyste Croissance",
            score=r.get("score"),
            summary=r.get("resume", ""),
            details={"acceleration": r.get("acceleration"), "durable": r.get("durable")},
            missing_data=r.get("donnees_manquantes", []),
        )

    # ── Agent 4 : Analyste management & insiders ─────────────────
    def agent_management(self, d: CompanyData) -> AgentReport:
        insider_str = "Aucune transaction récente disponible"
        if d.insider_transactions:
            lines = [f"  {t['date']} | {t['name']} ({t['title']}) | {t['type']} | {t['shares']:,} actions | ${t['value']:,.0f}" for t in d.insider_transactions[:5]]
            insider_str = "\n".join(lines)

        user = f"""Données management RÉELLES de {d.ticker}:

Participation insiders: {_pct_str(d.insider_ownership)}
Participation institutionnels: {_pct_str(d.institutional_ownership)}
Achats insiders récents (30j): {d.recent_insider_buys}
Ventes insiders récents (30j): {d.recent_insider_sells}
Short ratio: {_fmt_num(d.short_ratio)} | Short % float: {_pct_str(d.short_percent)}

Transactions insiders récentes (SEC Form 4):
{insider_str}

Rachats d'actions: {_fmt_num(d.buybacks,'$')}
Émissions d'actions: {_fmt_num(d.shares_issued,'$')}
Dividendes versés: {_fmt_num(d.dividends_paid,'$')}

Description entreprise: {(d.description or 'N/D')[:200]}

Analyse l'alignement management/actionnaires basé sur ces données réelles.
JSON: {{"score":65,"resume":"analyse honnête du management.","alignement":"bon/moyen/faible","signal_insiders":"positif/neutre/négatif/insuffisant","donnees_manquantes":[]}}"""

        r = self._call("Tu es un analyste spécialisé gouvernance d'entreprise. Analyse uniquement les faits disponibles.", user)
        return AgentReport(
            agent_name="Analyste Management",
            score=r.get("score"),
            summary=r.get("resume", ""),
            details={"alignement": r.get("alignement"), "signal_insiders": r.get("signal_insiders")},
            missing_data=r.get("donnees_manquantes", []),
        )

    # ── Agent 5 : Analyste valorisation + DCF ────────────────────
    def agent_valuation(self, d: CompanyData) -> AgentReport:
        # Calcul upside analystes
        upside_analyst = None
        if d.analyst_target and d.current_price and d.current_price > 0:
            upside_analyst = round((d.analyst_target - d.current_price) / d.current_price * 100, 1)

        user = f"""Données valorisation RÉELLES de {d.ticker} (prix: ${_fmt_num(d.current_price)}):

Multiples de marché:
PE: {_fmt_num(d.pe_ratio,'x')} | PB: {_fmt_num(d.pb_ratio,'x')} | PS: {_fmt_num(d.ps_ratio,'x')}
EV/EBITDA: {_fmt_num(d.ev_ebitda,'x')} | EV/Sales: {_fmt_num(d.ev_sales,'x')} | PEG: {_fmt_num(d.peg_ratio)}

Données pour DCF:
FCF: {_fmt_num(d.fcf,'$')} | FCF margin: {_pct_str(d.fcf_margin)}
Croissance CA 1Y: {_pct_str(d.rev_growth_1y)} | 3Y CAGR: {_pct_str(d.rev_growth_3y_cagr)}
CA: {_fmt_num(d.revenue,'$')} | Market cap: {_fmt_num(d.market_cap,'$')}

Analystes: target ${_fmt_num(d.analyst_target)} | upside: {_pct_str(upside_analyst)} | reco: {d.analyst_recommendation or 'N/D'} | nb: {d.nb_analysts or 'N/D'}

52S: ${_fmt_num(d.week52_low)} — ${_fmt_num(d.week52_high)} | Drawdown max 1Y: {_pct_str(d.max_drawdown_1y)}

Si les données FCF sont disponibles, calcule une valeur intrinsèque DCF approximative.
Si données insuffisantes pour DCF, dis-le honnêtement.
JSON: {{"score":70,"valeur_intrinseque":null,"marge_securite":null,"cherente":"elevee/moderee/faible","upside_potentiel":null,"resume":"analyse honnête de la valorisation.","donnees_manquantes":[]}}"""

        r = self._call("Tu es un analyste valorisation CFA. Calcule uniquement ce qui est calculable avec les données réelles. Sois honnête sur les limitations.", user, max_tokens=500)
        return AgentReport(
            agent_name="Analyste Valorisation",
            score=r.get("score"),
            summary=r.get("resume", ""),
            details={
                "valeur_intrinseque": r.get("valeur_intrinseque"),
                "marge_securite":     r.get("marge_securite"),
                "cherente":           r.get("cherente"),
                "upside_potentiel":   r.get("upside_potentiel"),
            },
            missing_data=r.get("donnees_manquantes", []),
        )

    # ── Agent 6 : Risk manager ────────────────────────────────────
    def agent_risk(self, d: CompanyData) -> AgentReport:
        user = f"""Analyse des risques RÉELS de {d.ticker} ({d.sector}):

Données financières de risque:
Dette totale: {_fmt_num(d.total_debt,'$')} | Cash: {_fmt_num(d.cash,'$')} | D/E: {_fmt_num(d.debt_to_equity)}
Current ratio: {_fmt_num(d.current_ratio)} | Quick ratio: {_fmt_num(d.quick_ratio)}
Beta: {_fmt_num(d.beta)} | Drawdown max 1Y: {_pct_str(d.max_drawdown_1y)}
Short ratio: {_fmt_num(d.short_ratio)} | Short %: {_pct_str(d.short_percent)}
Émissions d'actions récentes: {_fmt_num(d.shares_issued,'$')}
Ventes insiders: {d.recent_insider_sells} transactions

Pays: {d.country or 'N/D'} | Employés: {d.employees or 'N/D'}
Goodwill: {_fmt_num(d.goodwill,'$')}
Volatilité 1Y (perf range): {_pct_str(d.perf_1y)}

Identifie les risques RÉELS basés sur ces chiffres. Pas de risques inventés.
JSON: {{"score_risque":70,"niveau":"faible/modere/eleve/tres_eleve","risques_principaux":["risque1","risque2","risque3"],"resume":"évaluation honnête des risques.","donnees_manquantes":[]}}"""

        r = self._call("Tu es un risk manager senior. Identifie uniquement les risques visibles dans les données. Pas de spéculation.", user)
        return AgentReport(
            agent_name="Risk Manager",
            score=r.get("score_risque"),
            summary=r.get("resume", ""),
            details={"niveau": r.get("niveau"), "risques": r.get("risques_principaux", [])},
            missing_data=r.get("donnees_manquantes", []),
        )

    # ── Agent 7 : Portfolio manager — décision finale ─────────────
    def agent_portfolio(self, d: CompanyData, reports: list) -> AgentReport:
        scores_str = "\n".join(
            f"  {r.agent_name}: {r.score}/100 — {r.summary[:100]}"
            for r in reports if r.score is not None
        )

        user = f"""Synthèse pour {d.ticker} ({d.company_name}) — Prix: ${_fmt_num(d.current_price)}

Rapports des agents spécialisés:
{scores_str}

Qualité des données: {d.data_quality_score}/100
Données manquantes: {', '.join(d.missing_fields) or 'aucune'}

Prix actuel: ${_fmt_num(d.current_price)}
52S: ${_fmt_num(d.week52_low)} — ${_fmt_num(d.week52_high)}
Target analystes: ${_fmt_num(d.analyst_target)} ({d.nb_analysts or 'N/D'} analystes)
Reco consensus: {d.analyst_recommendation or 'N/D'}

Sur la base de ces données RÉELLES uniquement (pas d'invention), donne:
- Score global pondéré
- Décision d'investissement
- Scénarios basés sur les fondamentaux réels

JSON: {{"score_global":0,"score_qualite":0,"score_croissance":0,"score_rentabilite":0,"score_management":0,"score_valorisation":0,"score_risque":0,"etoiles":3,"conviction":"FORT","decision":"ACHETER","potentiel_estime":null,"valeur_intrinseque":null,"scenario_pessimiste":"basé sur faits","scenario_moyen":"basé sur faits","scenario_optimiste":"basé sur faits","synthese":"3 phrases de synthèse honnête."}}"""

        r = self._call("Tu es un gestionnaire de portefeuille senior. Décision basée uniquement sur les données réelles. Sois honnête sur l'incertitude.", user, max_tokens=700)
        return AgentReport(
            agent_name="Portfolio Manager",
            score=r.get("score_global"),
            summary=r.get("synthese", ""),
            details=r,
        )

    # ── Orchestrateur ─────────────────────────────────────────────
    def analyze(self, d: CompanyData) -> FinalReport:
        logger.info(f"Analyse multi-agents: {d.ticker} (qualité données: {d.data_quality_score}/100)")

        report = FinalReport(
            ticker=d.ticker,
            company_name=d.company_name or d.ticker,
            current_price=d.current_price,
            data_quality=d.data_quality_score,
            missing_fields=d.missing_fields,
        )

        agents_run = []

        # Agents spécialisés
        for agent_fn, label in [
            (self.agent_financial,  "financier"),
            (self.agent_growth,     "croissance"),
            (self.agent_management, "management"),
            (self.agent_valuation,  "valorisation"),
            (self.agent_risk,       "risque"),
        ]:
            logger.info(f"  Agent {label}...")
            try:
                ar = agent_fn(d)
                agents_run.append(ar)
            except Exception as e:
                logger.error(f"  Agent {label} error: {e}")
                agents_run.append(AgentReport(agent_name=label, error=str(e)))
            time.sleep(0.4)

        # Agent portfolio manager — synthèse finale
        logger.info("  Agent portfolio manager...")
        pm = self.agent_portfolio(d, agents_run)
        agents_run.append(pm)

        # Remplir le rapport final
        det = pm.details or {}
        report.score_global       = det.get("score_global")
        report.score_qualite      = det.get("score_qualite")
        report.score_croissance   = det.get("score_croissance")
        report.score_rentabilite  = det.get("score_rentabilite")
        report.score_management   = det.get("score_management")
        report.score_valorisation = det.get("score_valorisation")
        report.score_risque       = det.get("score_risque")
        report.etoiles            = det.get("etoiles", 0)
        report.conviction         = det.get("conviction", "")
        report.decision           = det.get("decision", "")
        report.valeur_intrinseque = det.get("valeur_intrinseque")
        report.potentiel_estime   = det.get("potentiel_estime")
        report.scenario_pessimiste = det.get("scenario_pessimiste")
        report.scenario_moyen     = det.get("scenario_moyen")
        report.scenario_optimiste = det.get("scenario_optimiste")
        report.agent_reports      = agents_run

        return report
