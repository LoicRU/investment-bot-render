"""
Screener - Récupère et filtre les tickers selon les critères fondamentaux
Sources : yfinance + Financial Modeling Prep (FMP) API
"""
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
import yfinance as yf

logger = logging.getLogger("screener")

# ------------------------------------------------------------
# Listes de tickers à surveiller
# Remplace ou étend selon tes marchés cibles
# ------------------------------------------------------------
WATCHLIST_NASDAQ = [
    "NVDA", "AMD", "SMCI", "CRDO", "ASTS", "IONQ", "RKLB", "ACHR",
    "JOBY", "LILM", "CELH", "DUOL", "AXON", "TTD", "BILL", "GLBE",
    "TMDX", "RXRX", "NTLA", "BEAM", "EDIT", "CRSP", "PACB", "ILMN",
    "AEHR", "WOLF", "ENVX", "IREN", "MARA", "CLSK", "RIOT", "COIN",
    "HOOD", "SOFI", "AFRM", "UPST", "AI", "PATH", "SOUN", "BBAI",
    "PLTR", "SNOW", "DDOG", "NET", "ZS", "CFLT", "MDB", "ESTC",
    "GTLB", "HUBS", "FRSH", "WIX", "SHOP", "MELI", "SE", "GRAB",
]
WATCHLIST_NYSE = [
    "TSM", "ASML", "LRCX", "AMAT", "KLAC", "TER", "ACLS", "ENTG",
    "AZTA", "ONTO", "ICHR", "FORM", "CAMT", "MKSI", "UCTT",
]
WATCHLIST_ALL = list(set(WATCHLIST_NASDAQ + WATCHLIST_NYSE))


@dataclass
class TickerData:
    ticker: str
    company_name: str = ""
    market_cap: float = 0.0          # en dollars
    revenue_growth_yoy: float = 0.0  # %
    gross_margin: float = 0.0        # %
    operating_margin: float = 0.0    # %
    net_margin: float = 0.0          # %
    fcf: float = 0.0                 # free cash flow absolu
    fcf_margin: float = 0.0          # %
    roe: float = 0.0                 # %
    roic: float = 0.0                # %
    debt_to_equity: float = 0.0
    current_ratio: float = 0.0
    ev_ebitda: float = 0.0
    pe_ratio: float = 0.0
    ps_ratio: float = 0.0
    pb_ratio: float = 0.0
    sector: str = ""
    industry: str = ""
    employees: int = 0
    description: str = ""
    error: Optional[str] = None


class Screener:
    """
    Récupère les données fondamentales pour une liste de tickers
    et filtre selon les critères minimaux.
    """

    # Seuils minimaux pour passer le premier filtre
    MIN_MARKET_CAP = 50_000_000        # 50 M$
    MAX_MARKET_CAP = 10_000_000_000    # 10 Md$
    MIN_REVENUE_GROWTH = 15.0          # 15% YoY minimum
    MIN_GROSS_MARGIN = 30.0            # 30% minimum
    MAX_DEBT_EQUITY = 3.0              # ratio max

    def __init__(self):
        self.fmp_key = os.environ.get("FMP_API_KEY", "")

    # ----------------------------------------------------------
    # Collecte des données via yfinance
    # ----------------------------------------------------------
    def fetch_ticker(self, symbol: str) -> TickerData:
        data = TickerData(ticker=symbol)
        try:
            tk = yf.Ticker(symbol)
            info = tk.info or {}

            data.company_name    = info.get("longName", symbol)
            data.market_cap      = info.get("marketCap", 0) or 0
            data.sector          = info.get("sector", "")
            data.industry        = info.get("industry", "")
            data.employees       = info.get("fullTimeEmployees", 0) or 0
            data.description     = (info.get("longBusinessSummary") or "")[:500]

            data.gross_margin    = (info.get("grossMargins") or 0) * 100
            data.operating_margin = (info.get("operatingMargins") or 0) * 100
            data.net_margin      = (info.get("profitMargins") or 0) * 100
            data.roe             = (info.get("returnOnEquity") or 0) * 100
            data.roic            = (info.get("returnOnAssets") or 0) * 100  # proxy
            data.debt_to_equity  = info.get("debtToEquity") or 0
            data.current_ratio   = info.get("currentRatio") or 0
            data.ev_ebitda       = info.get("enterpriseToEbitda") or 0
            data.pe_ratio        = info.get("trailingPE") or 0
            data.ps_ratio        = info.get("priceToSalesTrailing12Months") or 0
            data.pb_ratio        = info.get("priceToBook") or 0
            data.fcf             = info.get("freeCashflow") or 0

            # Calcul FCF margin
            revenue = info.get("totalRevenue") or 0
            if revenue > 0 and data.fcf:
                data.fcf_margin = (data.fcf / revenue) * 100

            # Croissance du CA (YoY) via historique financier
            try:
                financials = tk.financials
                if financials is not None and not financials.empty and "Total Revenue" in financials.index:
                    rev_row = financials.loc["Total Revenue"].dropna()
                    if len(rev_row) >= 2:
                        r_current = rev_row.iloc[0]
                        r_prev    = rev_row.iloc[1]
                        if r_prev > 0:
                            data.revenue_growth_yoy = ((r_current - r_prev) / r_prev) * 100
            except Exception:
                pass

        except Exception as e:
            data.error = str(e)
            logger.warning(f"Erreur fetch {symbol}: {e}")

        return data

    # ----------------------------------------------------------
    # Filtre de premier niveau (rapide, sans IA)
    # ----------------------------------------------------------
    def passes_filter(self, d: TickerData) -> bool:
        if d.error:
            return False
        if not (self.MIN_MARKET_CAP <= d.market_cap <= self.MAX_MARKET_CAP):
            return False
        if d.revenue_growth_yoy < self.MIN_REVENUE_GROWTH:
            return False
        if d.gross_margin < self.MIN_GROSS_MARGIN:
            return False
        if d.debt_to_equity > self.MAX_DEBT_EQUITY:
            return False
        # Secteurs à éviter
        excluded = {"Financial Services", "Real Estate", "Utilities", "Energy"}
        if d.sector in excluded:
            return False
        return True

    # ----------------------------------------------------------
    # Scan complet de la watchlist
    # ----------------------------------------------------------
    def scan(self, tickers: list[str] | None = None, delay: float = 1.0) -> list[TickerData]:
        """
        Scanne une liste de tickers, retourne ceux qui passent le filtre.
        delay : pause entre chaque requête pour éviter le rate-limit
        """
        if tickers is None:
            tickers = WATCHLIST_ALL

        results = []
        total = len(tickers)
        logger.info(f"Début du scan : {total} tickers")

        for i, symbol in enumerate(tickers, 1):
            logger.info(f"[{i}/{total}] {symbol}")
            data = self.fetch_ticker(symbol)
            if self.passes_filter(data):
                logger.info(f"  ✓ {symbol} passe le filtre")
                results.append(data)
            time.sleep(delay)

        logger.info(f"Scan terminé : {len(results)}/{total} passent le filtre")
        return results
