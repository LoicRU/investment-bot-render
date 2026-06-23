"""
Agent 1 — Collecteur de données réelles
Toutes les données viennent de yfinance + SEC EDGAR + APIs publiques.
Si une donnée est indisponible, elle est marquée None avec un flag manquant.
AUCUNE donnée inventée.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Optional
import requests
import yfinance as yf

logger = logging.getLogger("collector")

NA = None  # Donnée non disponible — jamais inventée


@dataclass
class CompanyData:
    ticker: str

    # ── Métadonnées ──────────────────────────────────────────────
    company_name: Optional[str]       = NA
    sector: Optional[str]             = NA
    industry: Optional[str]           = NA
    description: Optional[str]        = NA
    employees: Optional[int]          = NA
    country: Optional[str]            = NA
    website: Optional[str]            = NA

    # ── Prix & marché ────────────────────────────────────────────
    current_price: Optional[float]    = NA
    week52_high: Optional[float]      = NA
    week52_low: Optional[float]       = NA
    perf_1m: Optional[float]          = NA
    perf_3m: Optional[float]          = NA
    perf_6m: Optional[float]          = NA
    perf_1y: Optional[float]          = NA
    perf_3y: Optional[float]          = NA
    perf_5y: Optional[float]          = NA
    beta: Optional[float]             = NA
    volume_avg: Optional[float]       = NA
    market_cap: Optional[float]       = NA
    shares_outstanding: Optional[float] = NA
    float_shares: Optional[float]     = NA
    max_drawdown_1y: Optional[float]  = NA

    # ── Bilan ────────────────────────────────────────────────────
    total_assets: Optional[float]     = NA
    total_liabilities: Optional[float]= NA
    current_assets: Optional[float]   = NA
    current_liabilities: Optional[float] = NA
    cash: Optional[float]             = NA
    total_debt: Optional[float]       = NA
    equity: Optional[float]           = NA
    goodwill: Optional[float]         = NA
    inventory: Optional[float]        = NA
    receivables: Optional[float]      = NA
    book_value_per_share: Optional[float] = NA

    # ── Compte de résultat ───────────────────────────────────────
    revenue: Optional[float]          = NA
    revenue_1y_ago: Optional[float]   = NA
    revenue_3y_ago: Optional[float]   = NA
    revenue_5y_ago: Optional[float]   = NA
    gross_profit: Optional[float]     = NA
    ebit: Optional[float]             = NA
    ebitda: Optional[float]           = NA
    net_income: Optional[float]       = NA
    eps_ttm: Optional[float]          = NA
    rd_expense: Optional[float]       = NA

    # ── Cash flow ────────────────────────────────────────────────
    operating_cashflow: Optional[float] = NA
    capex: Optional[float]            = NA
    fcf: Optional[float]              = NA
    dividends_paid: Optional[float]   = NA
    buybacks: Optional[float]         = NA
    shares_issued: Optional[float]    = NA

    # ── Ratios calculés ──────────────────────────────────────────
    gross_margin: Optional[float]     = NA
    operating_margin: Optional[float] = NA
    net_margin: Optional[float]       = NA
    fcf_margin: Optional[float]       = NA
    roe: Optional[float]              = NA
    roa: Optional[float]              = NA
    debt_to_equity: Optional[float]   = NA
    current_ratio: Optional[float]    = NA
    quick_ratio: Optional[float]      = NA
    pe_ratio: Optional[float]         = NA
    pb_ratio: Optional[float]         = NA
    ps_ratio: Optional[float]         = NA
    ev_ebitda: Optional[float]        = NA
    peg_ratio: Optional[float]        = NA
    ev_sales: Optional[float]         = NA

    # ── Croissance ───────────────────────────────────────────────
    rev_growth_1y: Optional[float]    = NA
    rev_growth_3y_cagr: Optional[float] = NA
    rev_growth_5y_cagr: Optional[float] = NA
    net_income_growth_1y: Optional[float] = NA

    # ── Actionnariat ─────────────────────────────────────────────
    insider_ownership: Optional[float]= NA
    institutional_ownership: Optional[float] = NA
    short_ratio: Optional[float]      = NA
    short_percent: Optional[float]    = NA

    # ── Analystes ────────────────────────────────────────────────
    analyst_target: Optional[float]   = NA
    analyst_recommendation: Optional[str] = NA
    nb_analysts: Optional[int]        = NA

    # ── SEC / Insiders ───────────────────────────────────────────
    recent_insider_buys: int          = 0
    recent_insider_sells: int         = 0
    insider_transactions: list        = field(default_factory=list)

    # ── Flags de qualité des données ─────────────────────────────
    missing_fields: list              = field(default_factory=list)
    data_quality_score: int           = 0   # 0-100
    error: Optional[str]              = None


class DataCollector:
    """
    Collecte toutes les données disponibles.
    Jamais d'invention — si indisponible, marqué comme manquant.
    """

    def collect(self, symbol: str) -> CompanyData:
        d = CompanyData(ticker=symbol)
        try:
            tk   = yf.Ticker(symbol)
            info = tk.info or {}

            if not info or "longName" not in info:
                d.error = "Ticker introuvable ou données insuffisantes"
                return d

            # ── Métadonnées ──────────────────────────────────────
            d.company_name    = info.get("longName")
            d.sector          = info.get("sector")
            d.industry        = info.get("industry")
            d.description     = (info.get("longBusinessSummary") or "")[:600] or None
            d.employees       = info.get("fullTimeEmployees")
            d.country         = info.get("country")
            d.website         = info.get("website")

            # ── Prix ─────────────────────────────────────────────
            d.current_price   = info.get("currentPrice") or info.get("regularMarketPrice")
            d.week52_high     = info.get("fiftyTwoWeekHigh")
            d.week52_low      = info.get("fiftyTwoWeekLow")
            d.beta            = info.get("beta")
            d.volume_avg      = info.get("averageVolume")
            d.market_cap      = info.get("marketCap")
            d.shares_outstanding = info.get("sharesOutstanding")
            d.float_shares    = info.get("floatShares")

            # ── Bilan ─────────────────────────────────────────────
            d.cash            = info.get("totalCash")
            d.total_debt      = info.get("totalDebt")
            d.equity          = info.get("totalStockholderEquity") or info.get("bookValue")
            d.current_ratio   = info.get("currentRatio")
            d.quick_ratio     = info.get("quickRatio")
            d.book_value_per_share = info.get("bookValue")

            # ── P&L ───────────────────────────────────────────────
            d.revenue         = info.get("totalRevenue")
            d.ebitda          = info.get("ebitda")
            d.net_income      = info.get("netIncomeToCommon")
            d.eps_ttm         = info.get("trailingEps")
            d.gross_margin    = _pct(info.get("grossMargins"))
            d.operating_margin = _pct(info.get("operatingMargins"))
            d.net_margin      = _pct(info.get("profitMargins"))

            # ── Cash flow ─────────────────────────────────────────
            d.fcf             = info.get("freeCashflow")
            d.operating_cashflow = info.get("operatingCashflow")
            if d.revenue and d.fcf:
                d.fcf_margin  = round(d.fcf / d.revenue * 100, 2)

            # ── Ratios ────────────────────────────────────────────
            d.roe             = _pct(info.get("returnOnEquity"))
            d.roa             = _pct(info.get("returnOnAssets"))
            d.debt_to_equity  = info.get("debtToEquity")
            d.pe_ratio        = info.get("trailingPE")
            d.pb_ratio        = info.get("priceToBook")
            d.ps_ratio        = info.get("priceToSalesTrailing12Months")
            d.ev_ebitda       = info.get("enterpriseToEbitda")
            d.peg_ratio       = info.get("pegRatio")
            d.ev_sales        = info.get("enterpriseToRevenue")

            # ── Actionnariat ─────────────────────────────────────
            d.insider_ownership = _pct(info.get("heldPercentInsiders"))
            d.institutional_ownership = _pct(info.get("heldPercentInstitutions"))
            d.short_ratio     = info.get("shortRatio")
            d.short_percent   = _pct(info.get("shortPercentOfFloat"))

            # ── Analystes ─────────────────────────────────────────
            d.analyst_target  = info.get("targetMeanPrice")
            d.analyst_recommendation = info.get("recommendationKey")
            d.nb_analysts     = info.get("numberOfAnalystOpinions")

            # ── Historique des prix (performances réelles) ────────
            try:
                hist5y = tk.history(period="5y")
                if not hist5y.empty:
                    p_now = hist5y["Close"].iloc[-1]
                    def _perf(days):
                        if len(hist5y) > days:
                            p = hist5y["Close"].iloc[-days]
                            return round((p_now - p) / p * 100, 2) if p > 0 else None
                        return None
                    d.perf_1m  = _perf(22)
                    d.perf_3m  = _perf(66)
                    d.perf_6m  = _perf(132)
                    d.perf_1y  = _perf(252)
                    d.perf_3y  = _perf(756)
                    d.perf_5y  = _perf(1260)

                    # Drawdown max 1 an
                    hist1y = hist5y.tail(252)
                    if not hist1y.empty:
                        roll_max = hist1y["Close"].cummax()
                        dd = (hist1y["Close"] - roll_max) / roll_max * 100
                        d.max_drawdown_1y = round(dd.min(), 2)
            except Exception as e:
                logger.debug(f"Perf history error {symbol}: {e}")

            # ── Croissance CA sur plusieurs années (financials) ───
            try:
                fin = tk.financials
                if fin is not None and not fin.empty and "Total Revenue" in fin.index:
                    rev = fin.loc["Total Revenue"].dropna().sort_index()
                    revs = list(rev.values)
                    if len(revs) >= 1: d.revenue = revs[-1]
                    if len(revs) >= 2:
                        d.revenue_1y_ago = revs[-2]
                        if revs[-2] > 0:
                            d.rev_growth_1y = round((revs[-1] - revs[-2]) / revs[-2] * 100, 2)
                    if len(revs) >= 4:
                        d.revenue_3y_ago = revs[-4]
                        if revs[-4] > 0:
                            d.rev_growth_3y_cagr = round(
                                ((revs[-1] / revs[-4]) ** (1/3) - 1) * 100, 2)
                    if len(revs) >= 6:
                        d.revenue_5y_ago = revs[-6]
                        if revs[-6] > 0:
                            d.rev_growth_5y_cagr = round(
                                ((revs[-1] / revs[-6]) ** (1/5) - 1) * 100, 2)

                if "Net Income" in fin.index:
                    ni = fin.loc["Net Income"].dropna().sort_index().values
                    if len(ni) >= 2 and ni[-2] != 0:
                        d.net_income_growth_1y = round((ni[-1] - ni[-2]) / abs(ni[-2]) * 100, 2)

                if "Research And Development" in fin.index:
                    rd = fin.loc["Research And Development"].dropna()
                    d.rd_expense = float(rd.iloc[-1]) if not rd.empty else None

            except Exception as e:
                logger.debug(f"Financials error {symbol}: {e}")

            # ── Bilan détaillé ────────────────────────────────────
            try:
                bal = tk.balance_sheet
                if bal is not None and not bal.empty:
                    def _b(key):
                        if key in bal.index:
                            v = bal.loc[key].dropna()
                            return float(v.iloc[0]) if not v.empty else None
                        return None
                    d.total_assets      = _b("Total Assets")
                    d.total_liabilities = _b("Total Liabilities Net Minority Interest")
                    d.current_assets    = _b("Current Assets")
                    d.current_liabilities = _b("Current Liabilities")
                    d.goodwill          = _b("Goodwill")
                    d.inventory         = _b("Inventory")
                    d.receivables       = _b("Accounts Receivable")
                    d.equity            = _b("Stockholders Equity")
            except Exception as e:
                logger.debug(f"Balance sheet error {symbol}: {e}")

            # ── Cash flow détaillé ────────────────────────────────
            try:
                cf = tk.cashflow
                if cf is not None and not cf.empty:
                    def _c(key):
                        if key in cf.index:
                            v = cf.loc[key].dropna()
                            return float(v.iloc[0]) if not v.empty else None
                        return None
                    d.capex           = _c("Capital Expenditure")
                    d.dividends_paid  = _c("Cash Dividends Paid")
                    d.buybacks        = _c("Repurchase Of Capital Stock")
                    d.shares_issued   = _c("Issuance Of Capital Stock")
            except Exception as e:
                logger.debug(f"Cashflow error {symbol}: {e}")

            # ── Transactions insiders (SEC Form 4) ────────────────
            try:
                insiders = tk.insider_transactions
                if insiders is not None and not insiders.empty:
                    recent = insiders.head(10)
                    for _, row in recent.iterrows():
                        txn = {
                            "name":   row.get("Insider", "N/A"),
                            "title":  row.get("Position", "N/A"),
                            "type":   row.get("Transaction", "N/A"),
                            "shares": row.get("Shares", 0),
                            "value":  row.get("Value", 0),
                            "date":   str(row.get("Start Date", ""))[:10],
                        }
                        d.insider_transactions.append(txn)
                        if "Buy" in str(txn["type"]) or "Purchase" in str(txn["type"]):
                            d.recent_insider_buys += 1
                        elif "Sale" in str(txn["type"]) or "Sell" in str(txn["type"]):
                            d.recent_insider_sells += 1
            except Exception as e:
                logger.debug(f"Insider error {symbol}: {e}")

            # ── Score qualité des données ─────────────────────────
            d.missing_fields, d.data_quality_score = _quality(d)

        except Exception as e:
            d.error = str(e)
            logger.warning(f"Erreur collecte {symbol}: {e}")

        return d


def _pct(v):
    return round(v * 100, 2) if v is not None else None


def _quality(d: CompanyData):
    """Calcule un score de qualité des données (0-100) et liste les champs manquants."""
    checks = [
        ("Prix actuel",        d.current_price),
        ("Market cap",         d.market_cap),
        ("Chiffre d'affaires", d.revenue),
        ("Marge brute",        d.gross_margin),
        ("FCF",                d.fcf),
        ("ROE",                d.roe),
        ("Dette/Equity",       d.debt_to_equity),
        ("Croissance CA 1Y",   d.rev_growth_1y),
        ("EV/EBITDA",          d.ev_ebitda),
        ("Actionnariat insiders", d.insider_ownership),
    ]
    missing = [name for name, val in checks if val is None]
    score = round((1 - len(missing) / len(checks)) * 100)
    return missing, score
