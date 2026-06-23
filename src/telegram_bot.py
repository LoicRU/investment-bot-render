"""
Bot Telegram
- Envoie les alertes automatiques
- Commandes : /scan /top /watchlist /analyse TICKER /help
"""
import logging
import os

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

logger = logging.getLogger("telegram")

CONVICTION_EMOJI = {
    "EXCEPTIONNEL":    "🚀",
    "FORTE CONVICTION": "🟢",
    "POTENTIEL":       "🟡",
    "REJET":           "🔴",
}


def _score_bar(score: int) -> str:
    filled = round(score / 10)
    return "█" * filled + "░" * (10 - filled)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self.app     = Application.builder().token(token).build()
        self._register_commands()

    def _register_commands(self):
        self.app.add_handler(CommandHandler("start",     self._cmd_start))
        self.app.add_handler(CommandHandler("help",      self._cmd_help))
        self.app.add_handler(CommandHandler("top",       self._cmd_top))
        self.app.add_handler(CommandHandler("watchlist", self._cmd_watchlist))
        self.app.add_handler(CommandHandler("analyse",   self._cmd_analyse))
        self.app.add_handler(CommandHandler("scan",      self._cmd_scan))

    # ----------------------------------------------------------
    # Envoi d'alertes
    # ----------------------------------------------------------
    async def send_alert(self, result) -> bool:
        """Envoie une alerte pour une opportunité détectée."""
        emoji = CONVICTION_EMOJI.get(result.conviction, "📊")
        bar   = _score_bar(result.total_score)

        # Détail des sous-scores
        score_lines = "\n".join(
            f"  • {k.replace('_', ' ').capitalize():<22} {v}"
            for k, v in result.scores.items()
        )

        msg = (
            f"{emoji} *{result.ticker}* — {result.conviction}\n"
            f"_{result.company_name}_\n\n"
            f"*Score global : {result.total_score}/100*\n"
            f"`{bar}`\n\n"
            f"*Sous-scores :*\n`{score_lines}`\n\n"
            f"*Thèse :*\n{result.thesis}\n\n"
            f"*Risques :*\n{result.risks}\n\n"
            f"*Prix cibles (3 ans) :*\n"
            f"  🐂 Haussier : {result.price_target_bull}\n"
            f"  📈 Base     : {result.price_target_base}\n"
            f"  🛡 Marge    : {result.safety_margin}\n"
        )

        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.info(f"Alerte envoyée : {result.ticker} ({result.total_score}/100)")
            return True
        except Exception as e:
            logger.error(f"Erreur envoi alerte {result.ticker}: {e}")
            return False

    async def send_summary(self, results: list, scan_count: int):
        """Résumé de fin de scan."""
        if not results:
            msg = f"🔍 Scan terminé — {scan_count} tickers analysés\nAucune opportunité ≥ 70/100 aujourd'hui."
        else:
            lines = "\n".join(
                f"{CONVICTION_EMOJI.get(r.conviction,'📊')} *{r.ticker}* — {r.total_score}/100 ({r.conviction})"
                for r in results[:5]
            )
            msg = (
                f"📋 *Résumé du scan*\n"
                f"{scan_count} tickers analysés · {len(results)} opportunités\n\n"
                f"{lines}\n\n"
                f"_Détails envoyés pour chaque titre ci-dessus._"
            )

        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"Erreur envoi résumé: {e}")

    # ----------------------------------------------------------
    # Commandes Telegram
    # ----------------------------------------------------------
    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 *Investment Bot actif !*\n\n"
            "Je scanne automatiquement les marchés chaque jour.\n"
            "Tape /help pour voir les commandes disponibles.",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "*Commandes disponibles :*\n\n"
            "/scan — Lance un scan immédiat\n"
            "/top — Top 10 des meilleures opportunités\n"
            "/watchlist — Affiche ta watchlist\n"
            "/analyse TICKER — Analyse un ticker précis\n"
            "/help — Ce message",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _cmd_top(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        from src.database import Database
        db = Database()
        top = db.get_top_scores(limit=10)
        if not top:
            await update.message.reply_text("Aucun score en base. Lance /scan d'abord.")
            return
        lines = "\n".join(
            f"{i+1}. *{r['ticker']}* — {r['score']}/100 | {r['conviction']}"
            for i, r in enumerate(top)
        )
        await update.message.reply_text(
            f"🏆 *Top opportunités*\n\n{lines}",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _cmd_watchlist(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        from src.database import Database
        db = Database()
        wl = db.get_watchlist()
        if not wl:
            await update.message.reply_text("Ta watchlist est vide.")
            return
        await update.message.reply_text(
            "*Watchlist :*\n" + "\n".join(f"• {t}" for t in wl),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _cmd_analyse(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        args = ctx.args
        if not args:
            await update.message.reply_text("Usage : /analyse TICKER (ex: /analyse NVDA)")
            return
        ticker = args[0].upper()
        await update.message.reply_text(f"⏳ Analyse de {ticker} en cours...")

        from src.screener import Screener
        from src.scorer import AIScorer

        screener = Screener()
        data = screener.fetch_ticker(ticker)

        scorer = AIScorer()
        result = scorer.score_ticker(data)

        if result:
            await self.send_alert(result)
        else:
            await update.message.reply_text(f"❌ Impossible d'analyser {ticker}.")

    async def _cmd_scan(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("⏳ Scan lancé manuellement... (peut prendre plusieurs minutes)")
        # Déclenche un scan via le scheduler
        from src.scheduler import run_scan_once
        await run_scan_once(self)

    # ----------------------------------------------------------
    # Démarrage du polling
    # ----------------------------------------------------------
    async def run_polling(self):
        logger.info("Bot Telegram démarré (polling)")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        # Tourne indéfiniment
        await self.app.updater.idle()

    async def stop(self):
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
