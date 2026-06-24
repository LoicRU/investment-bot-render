"""
Pré-scoreur Python — calcule tous les scores en pur Python
ZÉRO token Groq utilisé ici.
L'IA n'intervient que pour la synthèse narrative finale.
"""
from dataclasses import dataclass
from typing import Optional
from agents.collector import CompanyData

# ── Filtre rapide niveau 1 (avant prescoring) ────────────────────
def quick_filter(d: CompanyData) -> tuple[bool, str]:
    """
    Filtre strict avant le scoring complet.
    Retourne (passe, raison_rejet).
    Élimine les tickers clairement non qualifiés sans gaspiller de tokens IA.
    """
    # Volume minimum — évite les illiquides et manipulables
    if d.volume_avg and d.volume_avg < 200_000:
        return False, f"volume trop faible ({d.volume_avg:,.0f})"

    # Marge brute minimum — modèle économique viable
    if d.gross_margin is not None and d.gross_margin < 20:
        return False, f"marge brute trop faible ({d.gross_margin:.1f}%)"

    # Croissance CA minimum — pas de sociétés en déclin
    if d.rev_growth_1y is not None and d.rev_growth_1y < -20:
        return False, f"CA en chute libre ({d.rev_growth_1y:.1f}%)"

    # Cash minimum — société viable (>3 mois de trésorerie)
    if d.cash_burn_months is not None and d.cash_burn_months < 3:
        return False, f"cash runway critique ({d.cash_burn_months:.1f} mois)"

    # Momentum : ne pas acheter ce qui chute fortement SANS raison
    # Exception : near 52W low avec insiders qui achètent = setup valable
    if (d.perf_3m is not None and d.perf_3m < -40
            and d.insider_net_signal not in ("positif", "très positif")):
        return False, f"chute momentum (-{abs(d.perf_3m):.0f}% sur 3M sans signal insider)"

    # Dilution excessive — destructeur de valeur
    if d.dilution_3y is not None and d.dilution_3y > 30:
        return False, f"dilution excessive ({d.dilution_3y:.1f}% sur 3 ans)"

    return True, "OK"


@dataclass
class PreScore:
    ticker: str

    # Scores par dimension (0-100)
    score_croissance:    int = 0
    score_rentabilite:   int = 0
    score_cashflow:      int = 0
    score_bilan:         int = 0
    score_management:    int = 0
    score_valorisation:  int = 0
    score_qualite_data:  int = 0
    score_global:        int = 0

    # Flags qualitatifs calculés
    rule_of_40_ok:       bool = False
    earnings_quality_ok: bool = False
    dilution_ok:         bool = False
    near_52w_low:        bool = False
    insider_positive:    bool = False
    sec_recent:          bool = False

    # Alertes détectées automatiquement
    alertes: list = None

    # Résumé chiffré compact pour le prompt IA (< 300 tokens)
    data_summary: str = ""

    def __post_init__(self):
        if self.alertes is None:
            self.alertes = []


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, int(v)))


def score(d: CompanyData) -> PreScore:
    ps = PreScore(ticker=d.ticker)
    alertes = []

    # ── 1. CROISSANCE (20 pts) ────────────────────────────────────
    s_croissance = 0

    rev1y = d.rev_growth_1y or 0
    if   rev1y >= 50: s_croissance += 20
    elif rev1y >= 30: s_croissance += 16
    elif rev1y >= 20: s_croissance += 12
    elif rev1y >= 10: s_croissance += 7
    elif rev1y >= 0:  s_croissance += 3
    else:             alertes.append("⚠️ CA en déclin")

    # Bonus accélération (CAGR 3Y vs 1Y)
    if d.rev_growth_1y and d.rev_growth_3y_cagr:
        if d.rev_growth_1y > d.rev_growth_3y_cagr + 5:
            s_croissance = min(20, s_croissance + 3)  # accélération

    # Bonus croissance FCF
    if d.fcf_growth_1y and d.fcf_growth_1y >= 20:
        s_croissance = min(20, s_croissance + 2)

    ps.score_croissance = _clamp(s_croissance * 5)  # normalize to 100

    # ── 2. RENTABILITÉ (15 pts) ───────────────────────────────────
    s_rent = 0

    gm = d.gross_margin or 0
    if   gm >= 70: s_rent += 5
    elif gm >= 50: s_rent += 4
    elif gm >= 30: s_rent += 2
    else:          alertes.append("⚠️ Marge brute faible")

    om = d.operating_margin or 0
    if   om >= 20:  s_rent += 5
    elif om >= 10:  s_rent += 3
    elif om >= 0:   s_rent += 1
    else:           alertes.append("⚠️ Marge opérationnelle négative")

    # Expansion marge brute
    if d.gross_margin_expansion and d.gross_margin_expansion > 0:
        s_rent += 3
    elif d.gross_margin_expansion and d.gross_margin_expansion < -3:
        alertes.append("⚠️ Compression des marges")
        s_rent -= 2

    # ROE
    roe = d.roe or 0
    if   roe >= 20: s_rent += 2
    elif roe >= 10: s_rent += 1

    ps.score_rentabilite = _clamp(s_rent * 5)

    # ── 3. CASH-FLOW (15 pts) ────────────────────────────────────
    s_cf = 0

    fcfm = d.fcf_margin or 0
    if   fcfm >= 20:  s_cf += 7
    elif fcfm >= 10:  s_cf += 5
    elif fcfm >= 0:   s_cf += 2
    else:
        alertes.append("⚠️ FCF négatif")
        if d.cash_burn_months and d.cash_burn_months < 12:
            alertes.append("🔴 CRITIQUE: < 12 mois de cash")

    # Qualité des bénéfices
    eq = d.earnings_quality or 0
    if eq >= 1.2:
        s_cf += 5
        ps.earnings_quality_ok = True
    elif eq >= 0.8:
        s_cf += 3
    elif eq < 0.5 and eq > 0:
        alertes.append("⚠️ Qualité bénéfices suspecte (FCF << NI)")

    # Métriques adaptées au secteur
    sector = (d.sector or "").lower()
    is_saas      = any(w in sector for w in ["technology", "software", "internet"])
    is_biotech    = any(w in sector for w in ["healthcare", "biotechnology", "pharmaceutical"])
    is_industrial = any(w in sector for w in ["industrial", "manufacturing", "energy"])

    r40 = d.rule_of_40 or 0
    if is_saas:
        # SaaS : Rule of 40 est la métrique clé
        if   r40 >= 60: s_cf += 4; ps.rule_of_40_ok = True
        elif r40 >= 40: s_cf += 2; ps.rule_of_40_ok = True
        elif r40 >= 20: s_cf += 1
        elif r40 <  10: s_cf -= 1
    elif is_biotech:
        # Biotech : cash runway est la métrique clé (pas de Rule of 40)
        runway = d.cash_burn_months
        if   runway and runway > 24: s_cf += 4
        elif runway and runway > 12: s_cf += 2
        elif runway and runway > 6:  s_cf += 0
        elif runway and runway <= 6: s_cf -= 2
        else:                        s_cf += 1  # FCF positif en biotech = rare, bon signe
    else:
        # Autres secteurs : Rule of 40 standard
        if   r40 >= 60: s_cf += 3; ps.rule_of_40_ok = True
        elif r40 >= 40: s_cf += 2; ps.rule_of_40_ok = True
        elif r40 >= 20: s_cf += 1

    ps.score_cashflow = _clamp(s_cf * 5)

    # ── 4. BILAN / DETTE (10 pts) ────────────────────────────────
    s_bilan = 0

    de = d.debt_to_equity or 0
    if   de <= 0.3:   s_bilan += 5
    elif de <= 1.0:   s_bilan += 3
    elif de <= 2.0:   s_bilan += 1
    else:             alertes.append("⚠️ Endettement élevé")

    cr = d.current_ratio or 0
    if   cr >= 2.0:   s_bilan += 3
    elif cr >= 1.5:   s_bilan += 2
    elif cr >= 1.0:   s_bilan += 1
    else:             alertes.append("⚠️ Liquidité court terme faible")

    ncp = d.net_cash_position or 0
    if ncp > 0:       s_bilan += 2

    # Dilution
    dil = d.dilution_3y or 0
    if   dil <= 2:
        ps.dilution_ok = True
    elif dil >= 10:
        alertes.append(f"⚠️ Dilution forte: {dil:.1f}% sur 3 ans")
        s_bilan -= 2
    elif dil >= 5:
        alertes.append(f"⚠️ Dilution modérée: {dil:.1f}% sur 3 ans")

    ps.score_bilan = _clamp(s_bilan * 10)

    # ── 5. MANAGEMENT / INSIDERS (10 pts) ────────────────────────
    s_mgmt = 5  # base neutre

    sig = d.insider_net_signal or "insuffisant"
    if   sig == "très positif":  s_mgmt += 4; ps.insider_positive = True
    elif sig == "positif":       s_mgmt += 2; ps.insider_positive = True
    elif sig == "très négatif":  s_mgmt -= 3; alertes.append("🔴 Ventes massives insiders")
    elif sig == "négatif":       s_mgmt -= 1

    ins_own = d.insider_ownership or 0
    if   ins_own >= 10: s_mgmt += 2
    elif ins_own >= 5:  s_mgmt += 1

    # Signal composite : insiders + short interest = squeeze potential
    short_pct = d.short_percent or 0
    if (d.insider_net_signal in ("positif", "très positif")
            and short_pct >= 15
            and (d.perf_1m or 0) > 0):
        # Setup squeeze : insiders achètent + fort short interest + momentum positif
        s_mgmt += 3
        alertes.append("🎯 Setup squeeze potentiel (insiders+short+momentum)")
    elif short_pct >= 30:
        # Short interest très élevé sans signal positif = danger
        alertes.append(f"⚠️ Short interest très élevé ({short_pct:.0f}%)")
        s_mgmt -= 1

    # SEC à jour ?
    if d.sec_10q_date:
        from datetime import datetime
        try:
            dt   = datetime.strptime(d.sec_10q_date[:10], "%Y-%m-%d")
            days = (datetime.now() - dt).days
            if days <= 90:
                ps.sec_recent = True
                s_mgmt += 1
            elif days > 180:
                alertes.append("⚠️ 10-Q > 6 mois — reporting en retard")
        except Exception:
            pass

    ps.score_management = _clamp(s_mgmt * 10)

    # ── 6. VALORISATION + MOMENTUM (10 pts) ─────────────────────
    s_val = 5  # base neutre

    # ── Bonus/malus momentum réel des prix ────────────────────────
    # Un bon titre doit confirmer sa qualité par le prix
    p3m = d.perf_3m or 0
    p1m = d.perf_1m or 0
    if   p3m >= 30:  s_val += 2   # Forte accélération
    elif p3m >= 10:  s_val += 1   # Momentum positif
    elif p3m <= -30: s_val -= 2   # Chute forte
    elif p3m <= -15: s_val -= 1   # Tendance baissière
    # Momentum court terme (1 mois) confirme ?
    if p1m > 0 and p3m > 0: s_val += 1   # Double confirmation

    # PEG
    peg = d.peg_ratio or 0
    if   0 < peg <= 1.0:  s_val += 3
    elif 0 < peg <= 1.5:  s_val += 2
    elif peg > 3:         s_val -= 2; alertes.append("⚠️ PEG élevé")

    # Upside analystes
    up = d.upside_vs_target or 0
    if   up >= 50: s_val += 3
    elif up >= 25: s_val += 2
    elif up >= 10: s_val += 1
    elif up < -10: s_val -= 2

    # Near 52W low
    if d.near_52w_low:
        s_val += 2
        ps.near_52w_low = True

    # PS ratio (pour growth stocks)
    ps_r = d.ps_ratio or 0
    if d.rev_growth_1y and d.rev_growth_1y >= 30 and ps_r <= 5:
        s_val += 1   # bon rapport croissance/valorisation
    elif ps_r > 30:
        alertes.append("⚠️ P/S très élevé")

    ps.score_valorisation = _clamp(s_val * 10)

    # ── 7. QUALITÉ DES DONNÉES ───────────────────────────────────
    ps.score_qualite_data = d.data_quality_score

    # ── SCORE GLOBAL PONDÉRÉ ─────────────────────────────────────
    # Poids dynamiques — ajustés par apprentissage si disponible
    try:
        from src.learner import PatternLearner
        w = PatternLearner().get_weights()
    except Exception:
        w = {"croissance":0.25,"rentabilite":0.20,"cashflow":0.20,
             "bilan":0.10,"management":0.10,"valorisation":0.15}

    ps.score_global = _clamp(
        ps.score_croissance   * w.get("croissance",   0.25) +
        ps.score_rentabilite  * w.get("rentabilite",  0.20) +
        ps.score_cashflow     * w.get("cashflow",     0.20) +
        ps.score_bilan        * w.get("bilan",        0.10) +
        ps.score_management   * w.get("management",   0.10) +
        ps.score_valorisation * w.get("valorisation", 0.15)
    )

    # Pénalité données insuffisantes
    if d.data_quality_score < 50:
        ps.score_global = _clamp(ps.score_global - 10)
        alertes.append("⚠️ Données incomplètes — score pénalisé")

    ps.alertes = alertes

    # ── RÉSUMÉ COMPACT POUR IA (< 300 tokens) ────────────────────
    def _n(v, suf=""):
        if v is None: return "N/D"
        if abs(v) >= 1e9: return f"{v/1e9:.1f}Md{suf}"
        if abs(v) >= 1e6: return f"{v/1e6:.1f}M{suf}"
        return f"{v:.1f}{suf}"

    def _pp(v):
        return f"{v:+.1f}%" if v is not None else "N/D"

    ps.data_summary = (
        f"{d.ticker}|{d.company_name or 'N/D'}|{d.sector or 'N/D'}|${_n(d.current_price)}|"
        f"Cap:{_n(d.market_cap,'$')}|"
        f"CA:{_n(d.revenue,'$')} {_pp(d.rev_growth_1y)}YoY {_pp(d.rev_growth_3y_cagr)}CAGR3Y|"
        f"MB:{_pp(d.gross_margin)}(exp:{_pp(d.gross_margin_expansion)})|"
        f"FCF:{_n(d.fcf,'$')} {_pp(d.fcf_margin)}m|"
        f"R40:{_n(d.rule_of_40)}|EQ:{_n(d.earnings_quality)}|"
        f"D/E:{_n(d.debt_to_equity)}|NetCash:{_n(d.net_cash_position,'$')}|"
        f"Dil3Y:{_pp(d.dilution_3y)}|"
        f"PE:{_n(d.pe_ratio,'x')}|PS:{_n(d.ps_ratio,'x')}|PEG:{_n(d.peg_ratio)}|"
        f"Ins:{d.insider_net_signal or 'N/D'}({d.recent_insider_buys}B/{d.recent_insider_sells}S)|"
        f"InsOwn:{_pp(d.insider_ownership)}|"
        f"52W:+{_pp(d.pct_from_52w_low)}low|-{_pp(d.pct_from_52w_high)}high|"
        f"Target:{_n(d.analyst_target,'$')}(+{_pp(d.upside_vs_target)})|"
        f"Reco:{d.analyst_recommendation}|Ana:{d.nb_analysts}|"
        f"SEC:10K={d.sec_10k_date or 'N/D'},10Q={d.sec_10q_date or 'N/D'}|"
        f"Scores:C{ps.score_croissance}/R{ps.score_rentabilite}/CF{ps.score_cashflow}/"
        f"B{ps.score_bilan}/M{ps.score_management}/V{ps.score_valorisation}|"
        f"Alertes:{';'.join(ps.alertes) or 'aucune'}"
    )

    return ps
