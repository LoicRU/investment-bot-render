"""
Base de données SQLite
- Historique de tous les scores
- Watchlist personnelle
- Log des alertes envoyées
"""
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from src.scorer import ScoreResult

logger = logging.getLogger("database")

DB_PATH = Path("data/investment_bot.db")


class Database:
    def __init__(self, path: Path = DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"Base de données connectée : {path}")

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS scores (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT NOT NULL,
                company     TEXT,
                score       INTEGER,
                conviction  TEXT,
                thesis      TEXT,
                risks       TEXT,
                scores_json TEXT,
                pt_bull     TEXT,
                pt_base     TEXT,
                safety      TEXT,
                scanned_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS alerts_sent (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT NOT NULL,
                score       INTEGER,
                channel     TEXT,
                sent_at     TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                ticker      TEXT PRIMARY KEY,
                added_at    TEXT DEFAULT (datetime('now')),
                notes       TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_scores_ticker ON scores(ticker);
            CREATE INDEX IF NOT EXISTS idx_scores_date  ON scores(scanned_at);
        """)
        self.conn.commit()

    # ----------------------------------------------------------
    # Scores
    # ----------------------------------------------------------
    def save_score(self, result: ScoreResult):
        self.conn.execute(
            """INSERT INTO scores
               (ticker, company, score, conviction, thesis, risks,
                scores_json, pt_bull, pt_base, safety)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                result.ticker,
                result.company_name,
                result.total_score,
                result.conviction,
                result.thesis,
                result.risks,
                json.dumps(result.scores),
                result.price_target_bull,
                result.price_target_base,
                result.safety_margin,
            ),
        )
        self.conn.commit()

    def get_last_score(self, ticker: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM scores WHERE ticker=? ORDER BY scanned_at DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        return dict(row) if row else None

    def already_alerted_today(self, ticker: str) -> bool:
        row = self.conn.execute(
            """SELECT id FROM alerts_sent
               WHERE ticker=? AND date(sent_at)=date('now')""",
            (ticker,),
        ).fetchone()
        return row is not None

    # ----------------------------------------------------------
    # Alertes
    # ----------------------------------------------------------
    def log_alert(self, ticker: str, score: int, channel: str):
        self.conn.execute(
            "INSERT INTO alerts_sent (ticker, score, channel) VALUES (?,?,?)",
            (ticker, score, channel),
        )
        self.conn.commit()

    # ----------------------------------------------------------
    # Watchlist
    # ----------------------------------------------------------
    def get_watchlist(self) -> list[str]:
        rows = self.conn.execute("SELECT ticker FROM watchlist").fetchall()
        return [r["ticker"] for r in rows]

    def add_to_watchlist(self, ticker: str, notes: str = ""):
        self.conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, notes) VALUES (?,?)",
            (ticker, notes),
        )
        self.conn.commit()

    # ----------------------------------------------------------
    # Rapport
    # ----------------------------------------------------------
    def get_top_scores(self, limit: int = 10, min_score: int = 70) -> list[dict]:
        rows = self.conn.execute(
            """SELECT ticker, company, score, conviction, thesis, scanned_at
               FROM scores
               WHERE score >= ?
               ORDER BY scanned_at DESC, score DESC
               LIMIT ?""",
            (min_score, limit),
        ).fetchall()
        return [dict(r) for r in rows]
