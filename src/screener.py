"""
Screener — collecte les données financières via yfinance (gratuit)
Filtre initial sans IA pour limiter les appels Groq
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional

import yfinance as yf

logger = logging.getLogger("screener")

# ----------------------------------------------------------------
# Univers de tickers surveillés
# Modifie ces listes pour ajouter tes propres tickers
# ----------------------------------------------------------------
WATCHLIST = [
    # IA & Semi-conducteurs
    "NVDA", "AMD", "CRDO", "SMCI", "AEHR", "WOLF", "ONTO", "ACLS",
    # SaaS / Cloud
    "DDOG", "NET", "ZS", "SNOW", "MDB", "GTLB", "CFLT", "ESTC",
    "BILL", "GLBE", "TTD", "HUBS", "FRSH", "PATH", "PLTR", "AI",
    # Santé / Biotech
    "TMDX", "RXRX", "NTLA", "BEAM", "CRSP", "PACB", "ILMN",
    # Énergie propre / Space
    "RKLB", "ACHR", "JOBY", "ASTS", "ENVX", "IREN",
    # Fintech / Consommation
    "SOFI", "AFRM", "UPST", "HOOD", "COIN", "CELH", "DUOL",
    # Global
    "MELI", "SE", "SHOP", "TSM",
]


@dataclass
class TickerData:
    ticker: str
    company_name: str = ""
    market_cap: float = 0.0
    revenue_growth_yoy: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0
    fcf: float = 0.0
    fcf_margin: float = 0.0
    roe: float = 0.0
    debt_to_equity: float = 0.0
    current_ratio: float = 0.0
    ev_ebitda: float = 0.0
    pe_ratio: float = 0.0
    ps_ratio: float = 0.0
    pb_ratio: float = 0.0
    sector: str = ""
    industry: str = ""
    description: str = ""
    error: Optional[str] = None


class Screener:
    MIN_MARKET_CAP   = 50_000_000
    MAX_MARKET_CAP   = 10_000_000_000
    MIN_REV_GROWTH   = 15.0
    MIN_GROSS_MARGIN = 30.0
    MAX_DEBT_EQUITY  = 3.0
    EXCLUDED_SECTORS = {"Financial Services", "Real Estate", "Utilities", "Energy"}

    def fetch(self, symbol: str) -> TickerData:
        d = TickerData(ticker=symbol)
        try:
            tk   = yf.Ticker(symbol)
            info = tk.info or {}

            d.company_name    = info.get("longName", symbol)
            d.market_cap      = info.get("marketCap", 0) or 0
            d.sector          = info.get("sector", "")
            d.industry        = info.get("industry", "")
            d.description     = (info.get("longBusinessSummary") or "")[:300]
            d.gross_margin    = (info.get("grossMargins") or 0) * 100
            d.operating_margin= (info.get("operatingMargins") or 0) * 100
            d.net_margin      = (info.get("profitMargins") or 0) * 100
            d.roe             = (info.get("returnOnEquity") or 0) * 100
            d.debt_to_equity  = info.get("debtToEquity") or 0
            d.current_ratio   = info.get("currentRatio") or 0
            d.ev_ebitda       = info.get("enterpriseToEbitda") or 0
            d.pe_ratio        = info.get("trailingPE") or 0
            d.ps_ratio        = info.get("priceToSalesTrailing12Months") or 0
            d.pb_ratio        = info.get("priceToBook") or 0
            d.fcf             = info.get("freeCashflow") or 0

            revenue = info.get("totalRevenue") or 0
            if revenue > 0 and d.fcf:
                d.fcf_margin = (d.fcf / revenue) * 100

            try:
                fin = tk.financials
                if fin is not None and not fin.empty and "Total Revenue" in fin.index:
                    row = fin.loc["Total Revenue"].dropna()
                    if len(row) >= 2 and row.iloc[1] > 0:
                        d.revenue_growth_yoy = ((row.iloc[0] - row.iloc[1]) / row.iloc[1]) * 100
            except Exception:
                pass

        except Exception as e:
            d.error = str(e)
            logger.warning(f"Erreur fetch {symbol}: {e}")
        return d

    def passes(self, d: TickerData) -> bool:
        if d.error:
            return False
        if not (self.MIN_MARKET_CAP <= d.market_cap <= self.MAX_MARKET_CAP):
            return False
        if d.revenue_growth_yoy < self.MIN_REV_GROWTH:
            return False
        if d.gross_margin < self.MIN_GROSS_MARGIN:
            return False
        if d.debt_to_equity > self.MAX_DEBT_EQUITY:
            return False
        if d.sector in self.EXCLUDED_SECTORS:
            return False
        return True

    def scan(self, tickers: list[str] | None = None, delay: float = 1.2) -> list[TickerData]:
        tickers = tickers or WATCHLIST
        results = []
        logger.info(f"Scan de {len(tickers)} tickers...")
        for i, sym in enumerate(tickers, 1):
            logger.info(f"[{i}/{len(tickers)}] {sym}")
            d = self.fetch(sym)
            if self.passes(d):
                results.append(d)
            time.sleep(delay)
        logger.info(f"{len(results)} candidats retenus")
        return results
