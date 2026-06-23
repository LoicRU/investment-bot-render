"""
Notifier — Telegram avec format rapport final propre
"""
import logging
import aiohttp
from agents.analyzer import FinalReport

logger = logging.getLogger("notifier")


def _bar(v, total=100):
    if v is None: return "░░░░░░░░░░ N/D"
    filled = round(v / total * 10)
    return "█" * filled + "░" * (10 - filled)

def _stars(n):
    return "★" * n + "☆" * (5 - n)

def _fmt(v, suffix="", decimals=1, prefix=""):
    if v is None: return "N/D"
    if isinstance(v, float) and abs(v) >= 1e9:
        return f"{prefix}{v/1e9:.{decimals}f}Md{suffix}"
    if isinstance(v, float) and abs(v) >= 1e6:
        return f"{prefix}{v/1e6:.{decimals}f}M{suffix}"
    return f"{prefix}{v:.{decimals}f}{suffix}"

def _pct(v):
    if v is None: return "N/D"
    return f"{v:+.1f}%"

DEC_EMOJI = {
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
                payload = {
                    "chat_id":    self.chat_id,
                    "text":       text[:4096],
                    "parse_mode": "Markdown",
                }
                async with session.post(self.url, json=payload) as resp:
                    ok = resp.status == 200
                    if not ok:
                        body = await resp.text()
                        logger.error(f"Telegram {resp.status}: {body[:200]}")
                    return ok
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def send_report(self, r: FinalReport, d) -> bool:
        dec_emoji = DEC_EMOJI.get(r.decision.upper(), "📊")
        stars_str = _stars(r.etoiles)

        # Avertissement qualité données
        quality_warn = ""
        if r.data_quality < 70:
            quality_warn = f"\n⚠️ _Qualité données: {r.data_quality}/100 — certaines données manquantes_\n"
        if r.missing_fields:
            quality_warn += f"_Données N/D: {', '.join(r.missing_fields[:4])}_\n"

        # Scores détaillés
        score_lines = []
        scores = [
            ("Qualité globale",  r.score_qualite),
            ("Croissance",       r.score_croissance),
            ("Rentabilité",      r.score_rentabilite),
            ("Management",       r.score_management),
            ("Valorisation",     r.score_valorisation),
            ("Risque",           r.score_risque),
        ]
        for label, score in scores:
            val = f"{score}/100" if score is not None else "N/D"
            score_lines.append(f"  {label:<16} {val}")

        # Insiders
        insider_str = ""
        if d.insider_transactions:
            last = d.insider_transactions[0]
            insider_str = f"\nDernière transaction: {last['name']} — {last['type']} {last['shares']:,} actions"
        elif d.recent_insider_buys == 0 and d.recent_insider_sells == 0:
            insider_str = "\nTransactions insiders: N/D (données non disponibles)"

        # Valeur intrinsèque
        vi_str = "N/D (données FCF insuffisantes pour DCF)"
        if r.valeur_intrinseque:
            vi_str = f"${r.valeur_intrinseque:.2f}"

        msg = (
            f"{dec_emoji} *{r.ticker}* — {r.decision}\n"
            f"_{r.company_name}_\n\n"
            f"💰 *Prix actuel : ${_fmt(r.current_price, decimals=2)}*\n"
            f"{quality_warn}\n"

            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Score global : {r.score_global or 'N/D'}/100*\n"
            f"`{_bar(r.score_global)}`\n\n"

            f"*Scores détaillés :*\n"
            f"`{''.join(l + chr(10) for l in score_lines)}`\n"

            f"*Conviction : {stars_str}*\n"
            f"Niveau : {r.conviction}\n\n"

            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *Données réelles :*\n"
            f"CA : {_fmt(d.revenue,'$')} | Croissance : {_pct(d.rev_growth_1y)}\n"
            f"Marge brute : {_pct(d.gross_margin)} | Marge nette : {_pct(d.net_margin)}\n"
            f"FCF : {_fmt(d.fcf,'$')} | FCF margin : {_pct(d.fcf_margin)}\n"
            f"Dette/Equity : {_fmt(d.debt_to_equity)} | Cash : {_fmt(d.cash,'$')}\n"
            f"PE : {_fmt(d.pe_ratio,'x')} | EV/EBITDA : {_fmt(d.ev_ebitda,'x')}\n"
            f"Insiders : {_pct(d.insider_ownership)} | Instit : {_pct(d.institutional_ownership)}"
            f"{insider_str}\n\n"

            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Valeur intrinsèque : {vi_str}*\n"
            f"Potentiel estimé : {_pct(r.potentiel_estime)}\n"
            f"Target analystes : {_fmt(d.analyst_target,'$')} "
            f"({d.nb_analysts or 'N/D'} analystes · {d.analyst_recommendation or 'N/D'})\n\n"

            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📋 *Scénarios :*\n"
            f"🐻 Pessimiste : {r.scenario_pessimiste or 'N/D'}\n"
            f"📊 Moyen : {r.scenario_moyen or 'N/D'}\n"
            f"🐂 Optimiste : {r.scenario_optimiste or 'N/D'}"
        )

        return await self._send(msg)

    async def send_summary(self, reports: list, total: int):
        if not reports:
            msg = f"🔍 *Scan terminé*\n{total} actions analysées\nAucune opportunité détectée."
        else:
            buy   = [r for r in reports if "ACHAT" in r.decision.upper()]
            watch = [r for r in reports if "SURVEILLER" in r.decision.upper()]
            lines = "\n".join(
                f"{'🟢' if 'ACHAT' in r.decision.upper() else '🟡'} "
                f"*{r.ticker}* ${_fmt(r.current_price, decimals=2)} "
                f"— {r.score_global or 'N/D'}/100 | {_stars(r.etoiles)}"
                for r in reports[:8]
            )
            msg = (
                f"📋 *Résumé scan hebdomadaire*\n"
                f"{total} actions · {len(reports)} opportunité(s)\n"
                f"🟢 {len(buy)} achat · 🟡 {len(watch)} surveiller\n\n"
                f"{lines}\n\n"
                f"_Rapport complet envoyé pour chaque titre._"
            )
        await self._send(msg)
