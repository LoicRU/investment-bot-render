"""
Analyzer v5 — 1 seul appel Groq par ticker (au lieu de 7 en v4)
Les scores sont calculés en Python pur (prescorer.py).
L'IA fait uniquement : synthèse narrative + scénarios + décision finale.
Réduction tokens : ~88%
"""
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from groq import Groq
from agents.collector import CompanyData
from agents.prescorer import PreScore

logger = logging.getLogger("analyzer")


@dataclass
class FinalReport:
    ticker: str
    company_name: str
    current_price: Optional[float]

    score_global: int          = 0
    score_croissance: int      = 0
    score_rentabilite: int     = 0
    score_cashflow: int        = 0
    score_bilan: int           = 0
    score_management: int      = 0
    score_valorisation: int    = 0

    etoiles: int               = 0
    conviction: str            = ""
    decision: str              = ""
    valeur_intrinseque: Optional[float] = None
    potentiel_estime: Optional[float]   = None
    prix_entree_ideal: Optional[str]    = None
    scenario_pessimiste: str   = ""
    scenario_moyen: str        = ""
    scenario_optimiste: str    = ""
    synthese: str              = ""

    alertes: list              = field(default_factory=list)
    data_quality: int          = 0
    missing_fields: list       = field(default_factory=list)


SYSTEM = "Gestionnaire de portefeuille senior. Données réelles. JSON uniquement. Ne rien inventer."

USER = """Données réelles:
{summary}

Scores calculés en Python:
Global:{g} Croissance:{c} Rentabilité:{r} CF:{cf} Bilan:{b} Mgmt:{m} Valo:{v}
Alertes: {alertes}
Qualité données: {dq}/100 | Manquantes: {missing}

Synthèse + décision + scénarios basés sur ces faits uniquement.
JSON: {{"etoiles":0,"conviction":"FORT","decision":"ACHETER","valeur_intrinseque":null,"potentiel_estime":null,"prix_entree_ideal":"$X","scenario_pessimiste":"1 phrase","scenario_moyen":"1 phrase","scenario_optimiste":"1 phrase","synthese":"2-3 phrases honnêtes."}}"""


class Analyzer:
    def __init__(self):
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.model  = "llama-3.3-70b-versatile"

    def analyze(self, d: CompanyData, ps: PreScore) -> FinalReport:
        r = FinalReport(
            ticker=d.ticker,
            company_name=d.company_name or d.ticker,
            current_price=d.current_price,
            score_global=ps.score_global,
            score_croissance=ps.score_croissance,
            score_rentabilite=ps.score_rentabilite,
            score_cashflow=ps.score_cashflow,
            score_bilan=ps.score_bilan,
            score_management=ps.score_management,
            score_valorisation=ps.score_valorisation,
            alertes=ps.alertes,
            data_quality=d.data_quality_score,
            missing_fields=d.missing_fields,
        )

        try:
            prompt = USER.format(
                summary=ps.data_summary,
                g=ps.score_global, c=ps.score_croissance,
                r=ps.score_rentabilite, cf=ps.score_cashflow,
                b=ps.score_bilan, m=ps.score_management,
                v=ps.score_valorisation,
                alertes="; ".join(ps.alertes) or "aucune",
                dq=d.data_quality_score,
                missing=", ".join(d.missing_fields) or "aucune",
            )

            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=400,
                temperature=0.05,
            )

            raw   = resp.choices[0].message.content.strip()
            clean = re.sub(r"```json|```", "", raw).strip()
            m     = re.search(r"\{.*\}", clean, re.DOTALL)
            p     = json.loads(m.group()) if m else {}

            # Parsing robuste — valeur par défaut cohérente si champ absent/null
            etoiles_raw          = p.get("etoiles")
            r.etoiles            = int(etoiles_raw) if etoiles_raw is not None else _etoiles_from_score(ps.score_global)
            r.conviction         = p.get("conviction") or _conv(ps.score_global)
            r.decision           = p.get("decision") or _dec(ps.score_global)
            r.valeur_intrinseque = p.get("valeur_intrinseque")  # None OK
            r.potentiel_estime   = p.get("potentiel_estime")    # None OK
            r.prix_entree_ideal  = p.get("prix_entree_ideal") or "N/D"
            r.scenario_pessimiste= p.get("scenario_pessimiste") or "N/D"
            r.scenario_moyen     = p.get("scenario_moyen") or "N/D"
            r.scenario_optimiste = p.get("scenario_optimiste") or "N/D"
            r.synthese           = p.get("synthese") or f"Score Python: {ps.score_global}/100."

        except Exception as e:
            logger.error(f"Groq error {d.ticker}: {e}")
            r.decision   = _dec(ps.score_global)
            r.conviction = _conv(ps.score_global)
            r.etoiles    = ps.score_global // 20
            r.synthese   = f"Score Python: {ps.score_global}/100. Synthèse IA indisponible."

        return r


def _dec(s):
    if s >= 80: return "ACHAT FORT"
    if s >= 70: return "ACHETER"
    if s >= 55: return "SURVEILLER"
    return "ÉVITER"

def _etoiles_from_score(s):
    if s >= 85: return 5
    if s >= 75: return 4
    if s >= 65: return 3
    if s >= 55: return 2
    return 1

def _conv(s):
    if s >= 80: return "TRÈS FORT"
    if s >= 70: return "FORT"
    if s >= 55: return "MOYEN"
    return "FAIBLE"
