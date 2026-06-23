"""
Screener avancé — focus actions peu chères à fort potentiel
Prix < 50$ | Small/Micro caps | Croissance forte
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Optional
import yfinance as yf

logger = logging.getLogger("screener")

# Universe élargi — actions peu chères, small/micro caps
WATCHLIST = [
    # IA & Tech émergente
    "SOUN", "BBAI", "IONQ", "QBTS", "RGTI", "QUBT", "AGEN",
    "CRKN", "INPX", "AGFY", "ALBT", "ANGI", "ANPX",
    # Semi-conducteurs abordables
    "CRDO", "AEHR", "WOLF", "ENVX", "AAOI", "CEVA", "FORM",
    # Biotech/Santé
    "RXRX", "NTLA", "BEAM", "EDIT", "VERV", "TMDX", "ACAD",
    "ALDX", "ALEC", "ALGS", "ALKT", "ALLK", "ALNY",
    # Space & Defence
    "RKLB", "ASTS", "ACHR", "JOBY", "LILM", "SPIR", "MNTS",
    # Fintech
    "AFRM", "UPST", "SOFI", "DAVE", "MGRM", "RELY",
    # SaaS abordable
    "GTLB", "CFLT", "ESTC", "DOCN", "MGNI", "TBLA", "TTD",
    # Énergie propre
    "ARRY", "STEM", "OPAL", "GDEV", "FLNC", "NOVA",
    # Consommation/Retail
    "CELH", "HIMS", "XPOF", "LQDT", "PRPL",
    # Crypto/Web3
    "MARA", "CLSK", "RIOT", "IREN", "CIFR",
]


@dataclass
class TickerData:
    ticker: str
    company_name: str = ""
    # Prix
    current_price: float = 0.0
    week52_high: float = 0.0
    week52_low: float = 0.0
    perf_1m: float = 0.0
    perf_3m: float = 0.0
    perf_1y: float = 0.0
    beta: float = 0.0
    volume: float = 0.0
    avg_volume: float = 0.0
    # Taille
    market_cap: float = 0.0
    shares_outstanding: float = 0.0
    float_shares: float = 0.0
    # P&L
    revenue: float = 0.0
    revenue_growth_yoy: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0
    ebitda: float = 0.0
    eps: float = 0.0
    # Bilan
    cash: float = 0.0
    total_debt: float = 0.0
    debt_to_equity: float = 0.0
    current_ratio: float = 0.0
    quick_ratio: float = 0.0
    book_value: float = 0.0
    # Cash flow
    fcf: float = 0.0
    fcf_margin: float = 0.0
    operating_cashflow: float = 0.0
    capex: float = 0.0
    # Rentabilité
    roe: float = 0.0
    roa: float = 0.0
    roic: float = 0.0
    # Valorisation
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    ps_ratio: float = 0.0
    ev_ebitda: float = 0.0
    peg_ratio: float = 0.0
    # Actionnariat
    insider_ownership: float = 0.0
    institutional_ownership: float = 0.0
    short_ratio: float = 0.0
    # Infos
    sector: str = ""
    industry: str = ""
    description: str = ""
    employees: int = 0
    # Analystes
    analyst_target: float = 0.0
    analyst_recommendation: str = ""
    nb_analysts: int = 0
    error: Optional[str] = None


class Screener:
    # Focus actions peu chères
    MAX_PRICE        = 50.0       # max 50$ par action
    MIN_MARKET_CAP   = 10_000_000  # 10M$ min
    MAX_MARKET_CAP   = 5_000_000_000  # 5Md$ max
    MIN_REV_GROWTH   = 10.0       # croissance CA min 10%
    MAX_DEBT_EQUITY  = 5.0
    EXCLUDED_SECTORS = {"Real Estate", "Utilities"}

    def fetch(self, symbol: str) -> TickerData:
        d = TickerData(ticker=symbol)
        try:
            tk   = yf.Ticker(symbol)
            info = tk.info or {}

            d.company_name          = info.get("longName", symbol)
            d.current_price         = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            d.week52_high           = info.get("fiftyTwoWeekHigh") or 0
            d.week52_low            = info.get("fiftyTwoWeekLow") or 0
            d.beta                  = info.get("beta") or 0
            d.volume                = info.get("regularMarketVolume") or 0
            d.avg_volume            = info.get("averageVolume") or 0
            d.market_cap            = info.get("marketCap") or 0
            d.shares_outstanding    = info.get("sharesOutstanding") or 0
            d.float_shares          = info.get("floatShares") or 0
            d.sector                = info.get("sector", "")
            d.industry              = info.get("industry", "")
            d.description           = (info.get("longBusinessSummary") or "")[:400]
            d.employees             = info.get("fullTimeEmployees") or 0

            # P&L
            d.revenue               = info.get("totalRevenue") or 0
            d.gross_margin          = (info.get("grossMargins") or 0) * 100
            d.operating_margin      = (info.get("operatingMargins") or 0) * 100
            d.net_margin            = (info.get("profitMargins") or 0) * 100
            d.ebitda                = info.get("ebitda") or 0
            d.eps                   = info.get("trailingEps") or 0

            # Bilan
            d.cash                  = info.get("totalCash") or 0
            d.total_debt            = info.get("totalDebt") or 0
            d.debt_to_equity        = info.get("debtToEquity") or 0
            d.current_ratio         = info.get("currentRatio") or 0
            d.quick_ratio           = info.get("quickRatio") or 0
            d.book_value            = info.get("bookValue") or 0

            # Cash flow
            d.fcf                   = info.get("freeCashflow") or 0
            d.operating_cashflow    = info.get("operatingCashflow") or 0
            if d.revenue > 0 and d.fcf:
                d.fcf_margin        = (d.fcf / d.revenue) * 100

            # Rentabilité
            d.roe                   = (info.get("returnOnEquity") or 0) * 100
            d.roa                   = (info.get("returnOnAssets") or 0) * 100

            # Valorisation
            d.pe_ratio              = info.get("trailingPE") or 0
            d.pb_ratio              = info.get("priceToBook") or 0
            d.ps_ratio              = info.get("priceToSalesTrailing12Months") or 0
            d.ev_ebitda             = info.get("enterpriseToEbitda") or 0
            d.peg_ratio             = info.get("pegRatio") or 0

            # Actionnariat
            d.insider_ownership     = (info.get("heldPercentInsiders") or 0) * 100
            d.institutional_ownership = (info.get("heldPercentInstitutions") or 0) * 100
            d.short_ratio           = info.get("shortRatio") or 0

            # Analystes
            d.analyst_target        = info.get("targetMeanPrice") or 0
            d.analyst_recommendation = info.get("recommendationKey", "")
            d.nb_analysts           = info.get("numberOfAnalystOpinions") or 0

            # Performances
            try:
                hist = tk.history(period="1y")
                if not hist.empty and len(hist) > 20:
                    p_now = hist["Close"].iloc[-1]
                    p_1m  = hist["Close"].iloc[-22] if len(hist) > 22 else hist["Close"].iloc[0]
                    p_3m  = hist["Close"].iloc[-66] if len(hist) > 66 else hist["Close"].iloc[0]
                    p_1y  = hist["Close"].iloc[0]
                    d.perf_1m = ((p_now - p_1m) / p_1m) * 100 if p_1m > 0 else 0
                    d.perf_3m = ((p_now - p_3m) / p_3m) * 100 if p_3m > 0 else 0
                    d.perf_1y = ((p_now - p_1y) / p_1y) * 100 if p_1y > 0 else 0
            except Exception:
                pass

            # Croissance CA YoY
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
            logger.warning(f"Erreur {symbol}: {e}")
        return d

    def passes(self, d: TickerData) -> bool:
        if d.error:                                                          return False
        if d.current_price <= 0 or d.current_price > self.MAX_PRICE:        return False
        if not (self.MIN_MARKET_CAP <= d.market_cap <= self.MAX_MARKET_CAP): return False
        if d.revenue_growth_yoy < self.MIN_REV_GROWTH:                      return False
        if d.debt_to_equity > self.MAX_DEBT_EQUITY:                         return False
        if d.sector in self.EXCLUDED_SECTORS:                               return False
        return True

    def scan(self, tickers=None, delay=1.2):
        tickers = tickers or WATCHLIST
        results = []
        logger.info(f"Scan de {len(tickers)} tickers (prix < {self.MAX_PRICE}$)...")
        for i, sym in enumerate(tickers, 1):
            logger.info(f"[{i}/{len(tickers)}] {sym}")
            d = self.fetch(sym)
            if self.passes(d):
                logger.info(f"  ✓ {sym} ${d.current_price:.2f} cap:{d.market_cap/1e6:.0f}M$")
                results.append(d)
            time.sleep(delay)
        logger.info(f"{len(results)} candidats retenus")
        return results
