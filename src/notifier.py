"""
Notifier v5 — compatible avec FinalReport v5
"""
import logging
import aiohttp

logger = logging.getLogger("notifier")

def _bar(v):
    if v is None: return "░░░░░░░░░░ N/D"
    filled = max(0, min(10, round(v / 10)))
    return "█" * filled + "░" * (10 - filled)

def _stars(n):
    n = max(0, min(5, n or 0))
    return "★" * n + "☆" * (5 - n)

def _f(v, suf="", dec=1):
    if v is None: return "N/D"
    if isinstance(v, (int, float)):
        if abs(v) >= 1e9: return f"{v/1e9:.1f}Md{suf}"
        if abs(v) >= 1e6: return f"{v/1e6:.1f}M{suf}"
        return f"{v:.{dec}f}{suf}"
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

    async def send_report(self, r, d) -> bool:
        dec_e = DEC.get((r.decision or "").upper(), "📊")

        # Avertissement qualité données
        dq_warn = ""
        if r.data_quality < 70:
            dq_warn = f"⚠️ _Qualité données: {r.data_quality}/100_\n"
        if r.missing_fields:
            dq_warn += f"_N/D: {', '.join(r.missing_fields[:4])}_\n"

        # Valeur intrinsèque
        vi_str = f"${r.valeur_intrinseque:.2f}" if r.valeur_intrinseque else "N/D (FCF insuffisant)"

        # Potentiel
        pot_str = _p(r.potentiel_estime) if r.potentiel_estime else "N/D"

        # Alertes
        alertes_str = ""
        if r.alertes:
            alertes_str = "\n".join(f"  {a}" for a in r.alertes[:5])
        else:
            alertes_str = "  ✅ Aucune alerte détectée"

        # Insiders
        ins_emoji = {
            "très positif": "🟢🟢", "positif": "🟢",
            "neutre": "⚪", "négatif": "🔴",
            "très négatif": "🔴🔴", "insuffisant": "❓"
        }
        ins_e  = ins_emoji.get(d.insider_net_signal, "❓")
        r40    = d.rule_of_40
        r40_s  = f"{r40:.0f} {'🏆' if r40 and r40>=60 else '✅' if r40 and r40>=40 else '⚠️'}" if r40 is not None else "N/D"
        eq     = d.earnings_quality
        eq_s   = f"{eq:.2f} {'✅' if eq and eq>=0.8 else '⚠️' if eq and eq>=0.5 else '🔴'}" if eq is not None else "N/D"

        msg = (
            f"{dec_e} *{r.ticker}* — {r.decision}\n"
            f"_{r.company_name}_\n"
            f"{dq_warn}\n"
            f"💰 *Prix : ${_f(d.current_price, dec=2)}*\n\n"

            f"━━━━ *SCORE GLOBAL : {r.score_global}/100* ━━━━\n"
            f"`{_bar(r.score_global)}`\n\n"

            f"*Détail des scores :*\n"
            f"  Croissance      {r.score_croissance}/100\n"
            f"  Rentabilité     {r.score_rentabilite}/100\n"
            f"  Cash-flow       {r.score_cashflow}/100\n"
            f"  Bilan/Dette     {r.score_bilan}/100\n"
            f"  Management      {r.score_management}/100\n"
            f"  Valorisation    {r.score_valorisation}/100\n\n"

            f"*Conviction : {_stars(r.etoiles)} {r.conviction}*\n\n"

            f"━━━━ *DONNÉES RÉELLES* ━━━━\n"
            f"CA : {_f(d.revenue,'$')} | Croissance : {_p(d.rev_growth_1y)}\n"
            f"Marge brute : {_p(d.gross_margin)} | Nette : {_p(d.net_margin)}\n"
            f"FCF : {_f(d.fcf,'$')} | FCF margin : {_p(d.fcf_margin)}\n"
            f"Rule of 40 : {r40_s}\n"
            f"Qualité bénéfices : {eq_s}\n"
            f"Dilution 3Y : {_p(d.dilution_3y)}\n"
            f"Cash net : {_f(d.net_cash_position,'$')}\n"
            f"Insiders : {ins_e} {d.insider_net_signal}\n"
            f"Near 52W low : {'✅ OUI' if d.near_52w_low else 'Non'}\n\n"

            f"━━━━ *ALERTES* ━━━━\n"
            f"{alertes_str}\n\n"

            f"━━━━ *VALORISATION* ━━━━\n"
            f"Valeur intrinsèque : {vi_str}\n"
            f"Potentiel estimé : *{pot_str}*\n"
            f"Prix d'entrée idéal : {r.prix_entree_ideal or 'N/D'}\n"
            f"Target analystes : ${_f(d.analyst_target)} ({d.nb_analysts or 'N/D'} ana.)\n"
            f"Upside vs consensus : {_p(d.upside_vs_target)}\n\n"

            f"━━━━ *SCÉNARIOS* ━━━━\n"
            f"🐻 {r.scenario_pessimiste or 'N/D'}\n"
            f"📊 {r.scenario_moyen or 'N/D'}\n"
            f"🐂 {r.scenario_optimiste or 'N/D'}\n\n"

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
                f"*{r.ticker}* ${_f(r.current_price, dec=2)} "
                f"— {r.score_global}/100 | {_stars(r.etoiles)}"
                for r in reports[:8]
            )
            msg = (
                f"📋 *Résumé scan*\n"
                f"{total} actions · {len(reports)} opportunité(s)\n"
                f"🟢 {len(buy)} achat · 🟡 {len(watch)} surveiller\n\n"
                f"{lines}\n\n"
                f"_Données 100% réelles — N/D si indisponible._"
            )
        await self._send(msg)
