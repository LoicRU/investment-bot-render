"""
Base de données SQLite — historique scores, watchlist, alertes
"""
import json
import logging
import sqlite3
from pathlib import Path

from src.scorer import ScoreResult

logger = logging.getLogger("database")
DB_PATH = Path("data/bot.db")


class Database:
    def __init__(self, path: Path = DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()
        logger.info(f"DB : {path}")

    def _init(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS scores (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker     TEXT,
                company    TEXT,
                score      INTEGER,
                conviction TEXT,
                thesis     TEXT,
                risks      TEXT,
                scores_json TEXT,
                pt_bull    TEXT,
                pt_base    TEXT,
                safety     TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS alerts_sent (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker   TEXT,
                score    INTEGER,
                sent_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker   TEXT PRIMARY KEY,
                notes    TEXT,
                added_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_s_ticker ON scores(ticker);
            CREATE INDEX IF NOT EXISTS idx_s_date   ON scores(created_at);
        """)
        self.conn.commit()

    def save_score(self, r: ScoreResult):
        self.conn.execute(
            """INSERT INTO scores
               (ticker,company,score,conviction,thesis,risks,scores_json,pt_bull,pt_base,safety)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (r.ticker, r.company_name, r.total_score, r.conviction,
             r.thesis, r.risks, json.dumps(r.scores),
             r.price_target_bull, r.price_target_base, r.safety_margin),
        )
        self.conn.commit()

    def already_alerted_today(self, ticker: str) -> bool:
        row = self.conn.execute(
            "SELECT id FROM alerts_sent WHERE ticker=? AND date(sent_at)=date('now')",
            (ticker,),
        ).fetchone()
        return row is not None

    def log_alert(self, ticker: str, score: int):
        self.conn.execute(
            "INSERT INTO alerts_sent (ticker,score) VALUES (?,?)", (ticker, score)
        )
        self.conn.commit()

    def get_top(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            """SELECT ticker,company,score,conviction,thesis,created_at
               FROM scores WHERE score>=70
               ORDER BY created_at DESC, score DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_watchlist(self) -> list[str]:
        return [r["ticker"] for r in self.conn.execute("SELECT ticker FROM watchlist").fetchall()]

    def add_watchlist(self, ticker: str, notes: str = ""):
        self.conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker,notes) VALUES (?,?)", (ticker, notes)
        )
        self.conn.commit()

    def remove_watchlist(self, ticker: str):
        self.conn.execute("DELETE FROM watchlist WHERE ticker=?", (ticker,))
        self.conn.commit()
