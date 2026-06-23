"""
Bot Telegram — notifications + commandes interactives
"""
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger("telegram")


def _bar(score: int) -> str:
    filled = round(score / 10)
    return "█" * filled + "░" * (10 - filled)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self.app     = Application.builder().token(token).build()
        self._register()

    def _register(self):
        cmds = [
            ("start",     self._start),
            ("help",      self._help),
            ("scan",      self._scan),
            ("top",       self._top),
            ("watchlist", self._watchlist),
            ("ajouter",   self._ajouter),
            ("supprimer", self._supprimer),
            ("analyse",   self._analyse),
            ("status",    self._status),
        ]
        for name, fn in cmds:
            self.app.add_handler(CommandHandler(name, fn))

    # ----------------------------------------------------------------
    # Envoi d'alertes
    # ----------------------------------------------------------------
    async def send_alert(self, r) -> bool:
        score_lines = "\n".join(
            f"  {k:<22} {v}" for k, v in r.scores.items()
        )
        msg = (
            f"*{r.ticker}* — {r.conviction}\n"
            f"_{r.company_name}_\n\n"
            f"*Score : {r.total_score}/100*\n"
            f"`{_bar(r.total_score)}`\n\n"
            f"*Détail :*\n`{score_lines}`\n\n"
            f"*Thèse :* {r.thesis}\n\n"
            f"*Risques :* {r.risks}\n\n"
            f"*Cibles 3 ans :*\n"
            f"  🐂 {r.price_target_bull}\n"
            f"  📈 {r.price_target_base}\n"
            f"  🛡 Marge : {r.safety_margin}"
        )
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id, text=msg, parse_mode=ParseMode.MARKDOWN
            )
            return True
        except Exception as e:
            logger.error(f"Erreur alerte {r.ticker}: {e}")
            return False

    async def send_summary(self, alerted: list, total: int):
        if not alerted:
            msg = f"🔍 Scan terminé — {total} tickers\nAucune opportunité ≥ seuil aujourd'hui."
        else:
            lines = "\n".join(
                f"  • *{r.ticker}* — {r.total_score}/100 {r.conviction}"
                for r in alerted[:5]
            )
            msg = (
                f"📋 *Résumé du scan*\n"
                f"{total} tickers · {len(alerted)} opportunité(s)\n\n"
                f"{lines}"
            )
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id, text=msg, parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Erreur résumé: {e}")

    # ----------------------------------------------------------------
    # Commandes
    # ----------------------------------------------------------------
    async def _start(self, u: Update, _):
        await u.message.reply_text(
            "🤖 *Investment Bot actif !*\n"
            "Scan automatique · Groq IA · 100% gratuit\n\n"
            "Tape /help pour les commandes.",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _help(self, u: Update, _):
        await u.message.reply_text(
            "*Commandes :*\n\n"
            "/scan — Lance un scan immédiat\n"
            "/top — Top 10 opportunités\n"
            "/analyse NVDA — Analyse un ticker\n"
            "/watchlist — Ta liste personnelle\n"
            "/ajouter NVDA — Ajoute à la watchlist\n"
            "/supprimer NVDA — Retire de la watchlist\n"
            "/status — État du bot\n"
            "/help — Ce message",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _status(self, u: Update, _):
        from src.database import Database
        db  = Database()
        top = db.get_top(limit=1)
        wl  = db.get_watchlist()
        last = top[0]["created_at"][:16] if top else "Aucun scan"
        await u.message.reply_text(
            f"*Status du bot*\n\n"
            f"✅ En ligne\n"
            f"🕐 Dernier scan : {last}\n"
            f"⭐ Watchlist : {len(wl)} titre(s)\n"
            f"📊 Scores en base : {len(db.get_top(limit=100))}",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _top(self, u: Update, _):
        from src.database import Database
        top = Database().get_top(limit=10)
        if not top:
            await u.message.reply_text("Aucun score. Lance /scan d'abord.")
            return
        lines = "\n".join(
            f"{i+1}. *{r['ticker']}* — {r['score']}/100 | {r['conviction']}"
            for i, r in enumerate(top)
        )
        await u.message.reply_text(
            f"🏆 *Top opportunités*\n\n{lines}", parse_mode=ParseMode.MARKDOWN
        )

    async def _watchlist(self, u: Update, _):
        from src.database import Database
        wl = Database().get_watchlist()
        if not wl:
            await u.message.reply_text(
                "Watchlist vide.\nUtilise /ajouter TICKER pour ajouter un titre."
            )
            return
        await u.message.reply_text(
            "*Ta watchlist :*\n" + "\n".join(f"• {t}" for t in wl),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _ajouter(self, u: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not ctx.args:
            await u.message.reply_text("Usage : /ajouter TICKER (ex: /ajouter NVDA)")
            return
        ticker = ctx.args[0].upper()
        Database_cls = __import__("src.database", fromlist=["Database"]).Database
        Database_cls().add_watchlist(ticker)
        await u.message.reply_text(f"✅ *{ticker}* ajouté à ta watchlist.", parse_mode=ParseMode.MARKDOWN)

    async def _supprimer(self, u: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not ctx.args:
            await u.message.reply_text("Usage : /supprimer TICKER")
            return
        ticker = ctx.args[0].upper()
        Database_cls = __import__("src.database", fromlist=["Database"]).Database
        Database_cls().remove_watchlist(ticker)
        await u.message.reply_text(f"🗑 *{ticker}* retiré.", parse_mode=ParseMode.MARKDOWN)

    async def _analyse(self, u: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not ctx.args:
            await u.message.reply_text("Usage : /analyse TICKER (ex: /analyse NVDA)")
            return
        ticker = ctx.args[0].upper()
        await u.message.reply_text(f"⏳ Analyse de *{ticker}* en cours...", parse_mode=ParseMode.MARKDOWN)

        from src.screener import Screener
        from src.scorer import AIScorer
        data   = Screener().fetch(ticker)
        result = AIScorer().score(data)

        if result:
            await self.send_alert(result)
        else:
            await u.message.reply_text(f"❌ Impossible d'analyser {ticker}. Vérifie le ticker.")

    async def _scan(self, u: Update, _):
        await u.message.reply_text("⏳ Scan manuel lancé... (2-3 min)")
        from src.scheduler import run_scan_once
        await run_scan_once(self)

    # ----------------------------------------------------------------
    async def run_polling(self):
        logger.info("Telegram polling démarré")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        await self.app.updater.idle()

    async def stop(self):
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
