"""
Notifier v4 — Format rapport final exact demandé
Données 100% réelles, N/D si manquant
"""
import logging
import aiohttp
from agents.analyzer import FinalReport
from agents.collector import CompanyData

logger = logging.getLogger("notifier")

def _bar(v):
    if v is None: return "░░░░░░░░░░ N/D"
    filled = max(0, min(10, round(v / 10)))
    return "█" * filled + "░" * (10 - filled)

def _stars(n):
    n = max(0, min(5, n or 0))
    return "★" * n + "☆" * (5 - n)

def _f(v, suf="", dec=2, pre=""):
    if v is None: return "N/D"
    if isinstance(v, (int, float)):
        if abs(v) >= 1e9: return f"{pre}{v/1e9:.1f}Md{suf}"
        if abs(v) >= 1e6: return f"{pre}{v/1e6:.1f}M{suf}"
        return f"{pre}{v:.{dec}f}{suf}"
    return str(v)

def _p(v):
    if v is None: return "N/D"
    return f"{v:+.1f}%"

DEC = {
    "ACHAT FORT": "🟢🟢",
    "ACHETER":    "🟢",
    "SURVEILLER": "🟡",
    "ÉVITER":     "🔴",
    "EVITER":     "🔴",
}


class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token   = token
        self.chat_id = chat_id
        self.url     = f"https://api.telegram.org/bot{token}/sendMessage"

    async def _send(self, text: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json={
                    "chat_id":    self.chat_id,
                    "text":       text[:4096],
                    "parse_mode": "Markdown",
                }) as resp:
                    ok = resp.status == 200
                    if not ok:
                        logger.error(f"Telegram {resp.status}: {await resp.text()[:100]}")
                    return ok
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False

    async def send_report(self, r: FinalReport, d: CompanyData) -> bool:
        dec_e = DEC.get(r.decision.upper(), "📊")

        # Avertissement données
        dq_warn = ""
        if r.data_quality < 70:
            dq_warn = f"\n⚠️ _Qualité données: {r.data_quality}/100_\n"
        if r.missing_fields:
            dq_warn += f"_N/D: {', '.join(r.missing_fields[:5])}_\n"

        # Valeur intrinsèque
        if r.valeur_intrinseque:
            vi_str = f"${r.valeur_intrinseque:.2f}"
        else:
            vi_str = "N/D (FCF insuffisant pour DCF fiable)"

        # Potentiel
        pot_str = _p(r.potentiel_estime) if r.potentiel_estime else "N/D"

        # Insiders signal
        ins_emoji = {"très positif":"🟢🟢","positif":"🟢","neutre":"⚪","négatif":"🔴","très négatif":"🔴🔴","insuffisant":"❓"}
        ins_e = ins_emoji.get(d.insider_net_signal, "❓")

        # Rule of 40 label
        r40 = d.rule_of_40
        r40_label = ""
        if r40 is not None:
            if r40 >= 60: r40_label = "🏆 Excellent"
            elif r40 >= 40: r40_label = "✅ Bon"
            else: r40_label = "⚠️ Insuffisant"

        # Qualité bénéfices
        eq = d.earnings_quality
        eq_label = ""
        if eq is not None:
            if eq >= 1.2: eq_label = "✅ Excellente"
            elif eq >= 0.8: eq_label = "✅ Bonne"
            elif eq >= 0.5: eq_label = "⚠️ Acceptable"
            else: eq_label = "🔴 Suspecte"

        msg = (
            f"{dec_e} *{r.ticker}* — {r.decision}\n"
            f"_{r.company_name}_\n"
            f"{dq_warn}\n"

            f"💰 *Prix actuel : ${_f(d.current_price)}*\n"
            f"📊 *Score global : {r.score_global or 'N/D'}/100*\n"
            f"`{_bar(r.score_global)}`\n\n"

            f"━━━━ *SCORES DÉTAILLÉS* ━━━━\n"
            f"  Qualité globale    {r.score_qualite or 'N/D'}/100\n"
            f"  Croissance         {r.score_croissance or 'N/D'}/100\n"
            f"  Rentabilité        {r.score_rentabilite or 'N/D'}/100\n"
            f"  Management         {r.score_management or 'N/D'}/100\n"
            f"  Valorisation       {r.score_valorisation or 'N/D'}/100\n"
            f"  Risque             {r.score_risque or 'N/D'}/100\n\n"

            f"*Conviction : {_stars(r.etoiles)} {r.conviction}*\n\n"

            f"━━━━ *DONNÉES RÉELLES* ━━━━\n"
            f"CA : {_f(d.revenue,'$',1)} | Croissance : {_p(d.rev_growth_1y)}\n"
            f"Marge brute : {_p(d.gross_margin)} | Nette : {_p(d.net_margin)}\n"
            f"FCF : {_f(d.fcf,'$',1)} | Marge FCF : {_p(d.fcf_margin)}\n"
            f"Rule of 40 : {_f(d.rule_of_40,'')} {r40_label}\n"
            f"Qualité bénéfices : {_f(d.earnings_quality,'')} {eq_label}\n"
            f"Dilution 3Y : {_p(d.dilution_3y)}\n"
            f"Cash net : {_f(d.net_cash_position,'$',1)}\n"
            f"Insiders : {ins_e} {d.insider_net_signal} (achats:{d.recent_insider_buys} ventes:{d.recent_insider_sells})\n"
            f"Near 52W low : {'✅ OUI' if d.near_52w_low else 'Non'} ({_p(d.pct_from_52w_low)} au-dessus du plus bas)\n\n"

            f"━━━━ *VALORISATION* ━━━━\n"
            f"Valeur intrinsèque : {vi_str}\n"
            f"Potentiel estimé : *{pot_str}*\n"
            f"Prix d'entrée idéal : {r.prix_entree_ideal or 'N/D'}\n"
            f"Target analystes : ${_f(d.analyst_target)} ({d.nb_analysts or 'N/D'} analystes)\n"
            f"Upside vs consensus : {_p(d.upside_vs_target)}\n\n"

            f"━━━━ *SCÉNARIOS* ━━━━\n"
            f"🐻 Pessimiste : {r.scenario_pessimiste or 'N/D'}\n"
            f"📊 Moyen : {r.scenario_moyen or 'N/D'}\n"
            f"🐂 Optimiste : {r.scenario_optimiste or 'N/D'}\n\n"

            f"━━━━ *SYNTHÈSE* ━━━━\n"
            f"_{r.synthese or 'N/D'}_\n\n"

            f"_SEC: 10-K={d.sec_10k_date or 'N/D'} | 10-Q={d.sec_10q_date or 'N/D'}_"
        )
        return await self._send(msg)

    async def send_summary(self, reports: list, total: int):
        if not reports:
            msg = f"🔍 *Scan terminé*\n{total} actions analysées\nAucune opportunité détectée."
        else:
            buy   = [r for r in reports if "ACHAT" in (r.decision or "").upper()]
            watch = [r for r in reports if "SURVEILLER" in (r.decision or "").upper()]
            lines = "\n".join(
                f"{'🟢🟢' if 'FORT' in (r.decision or '') else '🟢' if 'ACHAT' in (r.decision or '') else '🟡'} "
                f"*{r.ticker}* ${_f(r.current_price)} "
                f"— {r.score_global or 'N/D'}/100 | {_stars(r.etoiles)} | {r.conviction}"
                for r in reports[:8]
            )
            msg = (
                f"📋 *Résumé scan hebdomadaire*\n"
                f"{total} actions · {len(reports)} opportunité(s)\n"
                f"🟢 {len(buy)} achat · 🟡 {len(watch)} surveiller\n\n"
                f"{lines}\n\n"
                f"_Rapport complet envoyé pour chaque titre._\n"
                f"_Toutes les données sont réelles — N/D si indisponible._"
            )
        await self._send(msg)
