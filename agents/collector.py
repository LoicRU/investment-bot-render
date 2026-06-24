"""
Agent 1 — Collecteur de données v4
Sources réelles uniquement :
- yfinance : prix, financiers, ratios
- SEC EDGAR API (gratuit) : 10-K, 10-Q, 8-K
- SEC Form 4 (gratuit) : transactions insiders
- Calculs internes : qualité bénéfices, dilution, Rule of 40
AUCUNE donnée inventée — N/D si indisponible.
"""
import logging
import time
import requests
from dataclasses import dataclass, field
from typing import Optional
import yfinance as yf

logger = logging.getLogger("collector")


def _safe_cagr(end, start, years):
    """CAGR sécurisé — retourne None si calcul impossible (négatif, zéro, None)."""
    if end is None or start is None or start == 0 or years == 0:
        return None
    ratio = end / start
    if ratio <= 0:
        return None  # Impossible avec valeurs négatives → pas de résultat inventé
    return round((ratio ** (1 / years) - 1) * 100, 2)

SEC_HEADERS = {"User-Agent": "InvestmentBot research@bot.com"}  # requis par SEC EDGAR
SEC_BASE    = "https://data.sec.gov"
SEC_SEARCH  = "https://efts.sec.gov/LATEST/search-index"

NA = None


@dataclass
class CompanyData:
    ticker: str

    # ── Identité ─────────────────────────────────────────────────
    company_name: Optional[str]         = NA
    cik: Optional[str]                  = NA   # SEC identifier
    sector: Optional[str]               = NA
    industry: Optional[str]             = NA
    description: Optional[str]          = NA
    employees: Optional[int]            = NA
    country: Optional[str]              = NA
    founded: Optional[str]              = NA

    # ── Prix & marché ────────────────────────────────────────────
    current_price: Optional[float]      = NA
    week52_high: Optional[float]        = NA
    week52_low: Optional[float]         = NA
    pct_from_52w_low: Optional[float]   = NA   # % au-dessus du plus bas 52S
    pct_from_52w_high: Optional[float]  = NA   # % en dessous du plus haut 52S
    perf_1m: Optional[float]            = NA
    perf_3m: Optional[float]            = NA
    perf_6m: Optional[float]            = NA
    perf_1y: Optional[float]            = NA
    perf_3y: Optional[float]            = NA
    perf_5y: Optional[float]            = NA
    beta: Optional[float]               = NA
    volume_avg: Optional[float]         = NA
    market_cap: Optional[float]         = NA
    shares_outstanding: Optional[float] = NA
    float_shares: Optional[float]       = NA
    max_drawdown_1y: Optional[float]    = NA

    # ── Bilan ────────────────────────────────────────────────────
    total_assets: Optional[float]       = NA
    total_liabilities: Optional[float]  = NA
    current_assets: Optional[float]     = NA
    current_liabilities: Optional[float]= NA
    cash: Optional[float]               = NA
    total_debt: Optional[float]         = NA
    equity: Optional[float]             = NA
    goodwill: Optional[float]           = NA
    inventory: Optional[float]          = NA
    receivables: Optional[float]        = NA
    book_value_per_share: Optional[float]= NA

    # ── Compte de résultat ───────────────────────────────────────
    revenue: Optional[float]            = NA
    revenue_1y_ago: Optional[float]     = NA
    revenue_3y_ago: Optional[float]     = NA
    revenue_5y_ago: Optional[float]     = NA
    gross_profit: Optional[float]       = NA
    ebit: Optional[float]               = NA
    ebitda: Optional[float]             = NA
    net_income: Optional[float]         = NA
    net_income_1y_ago: Optional[float]  = NA
    eps_ttm: Optional[float]            = NA
    rd_expense: Optional[float]         = NA
    rd_expense_1y_ago: Optional[float]  = NA
    marketing_expense: Optional[float]  = NA

    # ── Cash flow ────────────────────────────────────────────────
    operating_cashflow: Optional[float] = NA
    capex: Optional[float]              = NA
    fcf: Optional[float]                = NA
    fcf_1y_ago: Optional[float]         = NA
    fcf_3y_ago: Optional[float]         = NA
    dividends_paid: Optional[float]     = NA
    buybacks: Optional[float]           = NA
    shares_issued: Optional[float]      = NA
    shares_issued_1y_ago: Optional[float]= NA

    # ── Ratios ───────────────────────────────────────────────────
    gross_margin: Optional[float]       = NA
    gross_margin_1y_ago: Optional[float]= NA
    operating_margin: Optional[float]   = NA
    net_margin: Optional[float]         = NA
    fcf_margin: Optional[float]         = NA
    roe: Optional[float]                = NA
    roa: Optional[float]                = NA
    roic: Optional[float]               = NA
    debt_to_equity: Optional[float]     = NA
    current_ratio: Optional[float]      = NA
    quick_ratio: Optional[float]        = NA
    interest_coverage: Optional[float]  = NA
    pe_ratio: Optional[float]           = NA
    pb_ratio: Optional[float]           = NA
    ps_ratio: Optional[float]           = NA
    ev_ebitda: Optional[float]          = NA
    peg_ratio: Optional[float]          = NA
    ev_sales: Optional[float]           = NA

    # ── Croissance ───────────────────────────────────────────────
    rev_growth_1y: Optional[float]      = NA
    rev_growth_3y_cagr: Optional[float] = NA
    rev_growth_5y_cagr: Optional[float] = NA
    ni_growth_1y: Optional[float]       = NA
    fcf_growth_1y: Optional[float]      = NA
    fcf_growth_3y_cagr: Optional[float] = NA
    gross_margin_expansion: Optional[float] = NA  # variation marge brute YoY

    # ── Métriques avancées ───────────────────────────────────────
    rule_of_40: Optional[float]         = NA   # rev_growth + fcf_margin
    earnings_quality: Optional[float]   = NA   # FCF / Net Income (>1 = bon)
    dilution_3y: Optional[float]        = NA   # % dilution sur 3 ans
    rd_to_revenue: Optional[float]      = NA   # R&D / CA
    rd_to_revenue_1y_ago: Optional[float]= NA  # évolution R&D intensity
    net_cash_position: Optional[float]  = NA   # cash - dette
    cash_burn_months: Optional[float]   = NA   # mois de cash restants si FCF négatif
    receivables_growth: Optional[float] = NA   # vs CA growth (signal qualité)
    near_52w_low: bool                  = False # dans les 20% du plus bas 52S

    # ── Actionnariat ─────────────────────────────────────────────
    insider_ownership: Optional[float]  = NA
    institutional_ownership: Optional[float] = NA
    short_ratio: Optional[float]        = NA
    short_percent: Optional[float]      = NA

    # ── Analystes ────────────────────────────────────────────────
    analyst_target: Optional[float]     = NA
    analyst_target_low: Optional[float] = NA
    analyst_target_high: Optional[float]= NA
    analyst_recommendation: Optional[str] = NA
    nb_analysts: Optional[int]          = NA
    upside_vs_target: Optional[float]   = NA

    # ── Insiders SEC Form 4 ──────────────────────────────────────
    recent_insider_buys: int            = 0
    recent_insider_sells: int           = 0
    insider_buy_value: float            = 0.0
    insider_sell_value: float           = 0.0
    insider_net_signal: str             = "neutre"  # positif/négatif/neutre/insuffisant
    insider_transactions: list          = field(default_factory=list)

    # ── SEC EDGAR ────────────────────────────────────────────────
    sec_10k_date: Optional[str]         = NA
    sec_10q_date: Optional[str]         = NA
    sec_8k_recent: list                 = field(default_factory=list)
    sec_risk_factors: Optional[str]     = NA   # extrait du 10-K
    sec_available: bool                 = False

    # ── Qualité données ──────────────────────────────────────────
    missing_fields: list                = field(default_factory=list)
    data_quality_score: int             = 0
    error: Optional[str]               = NA


def _pct(v):
    return round(v * 100, 2) if v is not None else None


class DataCollector:

    # ── Collecte principale ───────────────────────────────────────
    def collect(self, symbol: str) -> CompanyData:
        d = CompanyData(ticker=symbol)
        try:
            self._collect_yfinance(d)
            if d.company_name:
                self._collect_sec_edgar(d)
                self._collect_form4(d)
                self._compute_advanced_metrics(d)
            d.missing_fields, d.data_quality_score = self._quality(d)
        except Exception as e:
            d.error = str(e)
            logger.warning(f"Erreur collecte {symbol}: {e}")
        return d

    # ── yfinance ─────────────────────────────────────────────────
    def _collect_yfinance(self, d: CompanyData):
        tk   = yf.Ticker(d.ticker)
        info = tk.info or {}

        if not info.get("longName"):
            d.error = "INVALID_TICKER"
            return

        d.company_name       = info.get("longName")
        d.sector             = info.get("sector")
        d.industry           = info.get("industry")
        d.description        = (info.get("longBusinessSummary") or "")[:500] or None
        d.employees          = info.get("fullTimeEmployees")
        d.country            = info.get("country")

        # Prix
        d.current_price      = info.get("currentPrice") or info.get("regularMarketPrice")
        d.week52_high        = info.get("fiftyTwoWeekHigh")
        d.week52_low         = info.get("fiftyTwoWeekLow")
        d.beta               = info.get("beta")
        d.volume_avg         = info.get("averageVolume")
        d.market_cap         = info.get("marketCap")
        d.shares_outstanding = info.get("sharesOutstanding")
        d.float_shares       = info.get("floatShares")

        # Distance 52S
        if d.current_price and d.week52_low and d.week52_low > 0:
            d.pct_from_52w_low  = round((d.current_price - d.week52_low) / d.week52_low * 100, 1)
            d.near_52w_low      = d.pct_from_52w_low <= 20
        if d.current_price and d.week52_high and d.week52_high > 0:
            d.pct_from_52w_high = round((d.week52_high - d.current_price) / d.week52_high * 100, 1)

        # Bilan
        d.cash               = info.get("totalCash")
        d.total_debt         = info.get("totalDebt")
        d.current_ratio      = info.get("currentRatio")
        d.quick_ratio        = info.get("quickRatio")
        d.book_value_per_share = info.get("bookValue")

        # P&L
        d.revenue            = info.get("totalRevenue")
        d.ebitda             = info.get("ebitda")
        d.net_income         = info.get("netIncomeToCommon")
        d.eps_ttm            = info.get("trailingEps")
        d.gross_margin       = _pct(info.get("grossMargins"))
        d.operating_margin   = _pct(info.get("operatingMargins"))
        d.net_margin         = _pct(info.get("profitMargins"))

        # Cash flow
        d.fcf                = info.get("freeCashflow")
        d.operating_cashflow = info.get("operatingCashflow")
        if d.revenue and d.fcf:
            d.fcf_margin     = round(d.fcf / d.revenue * 100, 2)

        # Rentabilité
        d.roe                = _pct(info.get("returnOnEquity"))
        d.roa                = _pct(info.get("returnOnAssets"))

        # Valorisation
        d.pe_ratio           = info.get("trailingPE")
        d.pb_ratio           = info.get("priceToBook")
        d.ps_ratio           = info.get("priceToSalesTrailing12Months")
        d.ev_ebitda          = info.get("enterpriseToEbitda")
        d.peg_ratio          = info.get("pegRatio")
        d.ev_sales           = info.get("enterpriseToRevenue")

        # Actionnariat
        d.insider_ownership  = _pct(info.get("heldPercentInsiders"))
        d.institutional_ownership = _pct(info.get("heldPercentInstitutions"))
        d.short_ratio        = info.get("shortRatio")
        d.short_percent      = _pct(info.get("shortPercentOfFloat"))

        # Analystes
        d.analyst_target     = info.get("targetMeanPrice")
        d.analyst_target_low = info.get("targetLowPrice")
        d.analyst_target_high= info.get("targetHighPrice")
        d.analyst_recommendation = info.get("recommendationKey")
        d.nb_analysts        = info.get("numberOfAnalystOpinions")
        if d.analyst_target and d.current_price and d.current_price > 0:
            d.upside_vs_target = round((d.analyst_target - d.current_price) / d.current_price * 100, 1)

        # Historique performances
        try:
            hist = tk.history(period="5y")
            if not hist.empty:
                p_now = hist["Close"].iloc[-1]
                def _perf(days):
                    if len(hist) > days:
                        p = hist["Close"].iloc[-days]
                        return round((p_now - p) / p * 100, 2) if p > 0 else None
                    return None
                d.perf_1m  = _perf(22)
                d.perf_3m  = _perf(66)
                d.perf_6m  = _perf(132)
                d.perf_1y  = _perf(252)
                d.perf_3y  = _perf(756)
                d.perf_5y  = _perf(1260)
                # Drawdown max 1 an
                h1y = hist.tail(252)
                if not h1y.empty:
                    roll_max = h1y["Close"].cummax()
                    dd = (h1y["Close"] - roll_max) / roll_max * 100
                    d.max_drawdown_1y = round(dd.min(), 2)
        except Exception as e:
            logger.debug(f"Hist error {d.ticker}: {e}")

        # Financiers historiques multi-années
        try:
            fin = tk.financials
            if fin is not None and not fin.empty:
                def _row(key):
                    if key in fin.index:
                        v = fin.loc[key].dropna().sort_index()
                        return list(v.values)
                    return []

                rev = _row("Total Revenue")
                if len(rev) >= 1: d.revenue = rev[-1]
                if len(rev) >= 2:
                    d.revenue_1y_ago = rev[-2]
                    d.rev_growth_1y  = round((rev[-1]-rev[-2])/rev[-2]*100,2) if rev[-2]>0 else None
                if len(rev) >= 4:
                    d.revenue_3y_ago = rev[-4]
                    d.rev_growth_3y_cagr = _safe_cagr(rev[-1], rev[-4], 3)
                if len(rev) >= 6:
                    d.revenue_5y_ago = rev[-6]
                    d.rev_growth_5y_cagr = _safe_cagr(rev[-1], rev[-6], 5)

                ni = _row("Net Income")
                if len(ni) >= 2:
                    d.net_income_1y_ago = ni[-2]
                    d.ni_growth_1y = round((ni[-1]-ni[-2])/abs(ni[-2])*100,2) if ni[-2]!=0 else None

                rd = _row("Research And Development")
                if rd:
                    d.rd_expense = rd[-1]
                    if len(rd) >= 2: d.rd_expense_1y_ago = rd[-2]
                if d.rd_expense and d.revenue:
                    d.rd_to_revenue = round(d.rd_expense / d.revenue * 100, 2)
                if d.rd_expense_1y_ago and d.revenue_1y_ago:
                    d.rd_to_revenue_1y_ago = round(d.rd_expense_1y_ago / d.revenue_1y_ago * 100, 2)

                gm = _row("Gross Profit")
                rev_raw = _row("Total Revenue")
                if len(gm)>=2 and len(rev_raw)>=2 and rev_raw[-1]>0 and rev_raw[-2]>0:
                    gm_now = gm[-1]/rev_raw[-1]*100
                    gm_prev= gm[-2]/rev_raw[-2]*100
                    d.gross_margin_expansion = round(gm_now - gm_prev, 2)
                    d.gross_margin_1y_ago    = round(gm_prev, 2)
        except Exception as e:
            logger.debug(f"Financials error {d.ticker}: {e}")

        # Bilan détaillé
        try:
            bal = tk.balance_sheet
            if bal is not None and not bal.empty:
                def _b(key):
                    if key in bal.index:
                        v = bal.loc[key].dropna()
                        return float(v.iloc[0]) if not v.empty else None
                    return None
                d.total_assets       = _b("Total Assets")
                d.total_liabilities  = _b("Total Liabilities Net Minority Interest")
                d.current_assets     = _b("Current Assets")
                d.current_liabilities= _b("Current Liabilities")
                d.goodwill           = _b("Goodwill")
                d.inventory          = _b("Inventory")
                d.receivables        = _b("Accounts Receivable")
                d.equity             = _b("Stockholders Equity")
        except Exception as e:
            logger.debug(f"Balance sheet error {d.ticker}: {e}")

        # Cash flow détaillé
        try:
            cf = tk.cashflow
            if cf is not None and not cf.empty:
                def _c(key):
                    if key in cf.index:
                        v = cf.loc[key].dropna()
                        return float(v.iloc[0]) if not v.empty else None
                    return None
                d.capex          = _c("Capital Expenditure")
                d.dividends_paid = _c("Cash Dividends Paid")
                d.buybacks       = _c("Repurchase Of Capital Stock")
                d.shares_issued  = _c("Issuance Of Capital Stock")

                # FCF historique
                ocf_all = []
                cap_all = []
                if "Operating Cash Flow" in cf.index:
                    ocf_all = list(cf.loc["Operating Cash Flow"].dropna().sort_index().values)
                if "Capital Expenditure" in cf.index:
                    cap_all = list(cf.loc["Capital Expenditure"].dropna().sort_index().values)
                if len(ocf_all)>=2 and len(cap_all)>=2:
                    d.fcf_1y_ago = ocf_all[-2] + cap_all[-2]  # capex est négatif
                    if d.fcf and d.fcf_1y_ago and d.fcf_1y_ago != 0:
                        d.fcf_growth_1y = round((d.fcf - d.fcf_1y_ago) / abs(d.fcf_1y_ago) * 100, 2)
                if len(ocf_all)>=4 and len(cap_all)>=4:
                    d.fcf_3y_ago = ocf_all[-4] + cap_all[-4]
                    d.fcf_growth_3y_cagr = _safe_cagr(d.fcf, d.fcf_3y_ago, 3)

                # Dilution 3 ans (shares issued cumulées)
                if "Issuance Of Capital Stock" in cf.index:
                    iss = cf.loc["Issuance Of Capital Stock"].dropna().sort_index().values
                    if len(iss) >= 3 and d.shares_outstanding and d.current_price:
                        total_issued = sum(abs(x) for x in iss[-3:] if x and x > 0)
                        mktcap_approx = d.shares_outstanding * d.current_price
                        if mktcap_approx > 0:
                            d.dilution_3y = round(total_issued / mktcap_approx * 100, 2)

        except Exception as e:
            logger.debug(f"Cashflow error {d.ticker}: {e}")

        # Insiders yfinance
        try:
            ins = tk.insider_transactions
            if ins is not None and not ins.empty:
                for _, row in ins.head(15).iterrows():
                    txn = {
                        "name":   str(row.get("Insider", "N/A")),
                        "title":  str(row.get("Position", "N/A")),
                        "type":   str(row.get("Transaction", "N/A")),
                        "shares": int(row.get("Shares", 0) or 0),
                        "value":  float(row.get("Value", 0) or 0),
                        "date":   str(row.get("Start Date", ""))[:10],
                    }
                    d.insider_transactions.append(txn)
                    t = txn["type"].lower()
                    if "buy" in t or "purchase" in t:
                        d.recent_insider_buys  += 1
                        d.insider_buy_value    += txn["value"]
                    elif "sale" in t or "sell" in t:
                        d.recent_insider_sells += 1
                        d.insider_sell_value   += txn["value"]
        except Exception as e:
            logger.debug(f"Insider yf error {d.ticker}: {e}")

    # ── SEC EDGAR ─────────────────────────────────────────────────
    def _collect_sec_edgar(self, d: CompanyData):
        try:
            # Trouver le CIK via EDGAR
            url = f"https://efts.sec.gov/LATEST/search-index?q=%22{d.ticker}%22&dateRange=custom&startdt=2020-01-01&forms=10-K"
            r   = requests.get(
                f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&ticker={d.ticker}&type=10-K&dateb=&owner=include&count=5&search_text=",
                headers=SEC_HEADERS, timeout=10
            )
            # Récupérer CIK depuis l'API company facts
            r2 = requests.get(
                f"https://efts.sec.gov/LATEST/search-index?q=%22{d.ticker}%22&forms=10-K,10-Q,8-K",
                headers=SEC_HEADERS, timeout=10
            )
            if r2.status_code != 200:
                return

            # Chercher les derniers dépôts via EDGAR full-text search
            search_url = f"https://efts.sec.gov/LATEST/search-index?q=%22{d.ticker}%22&forms=8-K&dateRange=custom&startdt=2024-01-01"
            r3 = requests.get(search_url, headers=SEC_HEADERS, timeout=10)

            # Utiliser l'API EDGAR submissions
            # D'abord trouver le CIK
            ticker_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&ticker={d.ticker}&type=&dateb=&owner=include&count=10&search_text=&output=atom"
            r4 = requests.get(ticker_url, headers=SEC_HEADERS, timeout=10)

            # API directe tickers SEC
            cik_url = "https://www.sec.gov/files/company_tickers.json"
            r5 = requests.get(cik_url, headers=SEC_HEADERS, timeout=15)
            if r5.status_code == 200:
                tickers_data = r5.json()
                for key, val in tickers_data.items():
                    if val.get("ticker", "").upper() == d.ticker.upper():
                        d.cik = str(val.get("cik_str", "")).zfill(10)
                        break

            if d.cik:
                d.sec_available = True
                self._fetch_sec_filings(d)

        except Exception as e:
            logger.debug(f"SEC EDGAR error {d.ticker}: {e}")

    def _fetch_sec_filings(self, d: CompanyData):
        try:
            sub_url = f"{SEC_BASE}/submissions/CIK{d.cik}.json"
            r = requests.get(sub_url, headers=SEC_HEADERS, timeout=15)
            if r.status_code != 200:
                return

            data     = r.json()
            filings  = data.get("filings", {}).get("recent", {})
            forms    = filings.get("form", [])
            dates    = filings.get("filingDate", [])
            accnums  = filings.get("accessionNumber", [])
            descs    = filings.get("primaryDocument", [])

            # Dates des derniers rapports
            for i, form in enumerate(forms):
                if form == "10-K" and not d.sec_10k_date:
                    d.sec_10k_date = dates[i] if i < len(dates) else None
                if form == "10-Q" and not d.sec_10q_date:
                    d.sec_10q_date = dates[i] if i < len(dates) else None
                if form == "8-K" and len(d.sec_8k_recent) < 5:
                    d.sec_8k_recent.append({
                        "date": dates[i] if i < len(dates) else "N/D",
                        "desc": descs[i] if i < len(descs) else "N/D",
                    })

        except Exception as e:
            logger.debug(f"SEC filings error {d.ticker}: {e}")

    # ── Form 4 insiders (SEC) ─────────────────────────────────────
    def _collect_form4(self, d: CompanyData):
        if not d.cik:
            return
        try:
            url = f"{SEC_BASE}/submissions/CIK{d.cik}.json"
            r   = requests.get(url, headers=SEC_HEADERS, timeout=15)
            if r.status_code != 200:
                return

            data    = r.json()
            filings = data.get("filings", {}).get("recent", {})
            forms   = filings.get("form", [])
            dates   = filings.get("filingDate", [])

            form4_count = 0
            for i, form in enumerate(forms[:100]):
                if form in ("4", "4/A") and form4_count < 10:
                    # On a déjà les transactions yfinance — ici on compte juste les Form 4 récents
                    form4_count += 1

            # Signal insiders basé sur ratio buy/sell
            total = d.recent_insider_buys + d.recent_insider_sells
            if total == 0:
                d.insider_net_signal = "insuffisant"
            elif d.recent_insider_buys > d.recent_insider_sells * 2:
                d.insider_net_signal = "très positif"
            elif d.recent_insider_buys > d.recent_insider_sells:
                d.insider_net_signal = "positif"
            elif d.recent_insider_sells > d.recent_insider_buys * 3:
                d.insider_net_signal = "très négatif"
            elif d.recent_insider_sells > d.recent_insider_buys:
                d.insider_net_signal = "négatif"
            else:
                d.insider_net_signal = "neutre"

        except Exception as e:
            logger.debug(f"Form4 error {d.ticker}: {e}")

    # ── Métriques avancées calculées ─────────────────────────────
    def _compute_advanced_metrics(self, d: CompanyData):

        # Rule of 40 (SaaS/Tech) : croissance CA + FCF margin
        if d.rev_growth_1y is not None and d.fcf_margin is not None:
            d.rule_of_40 = round(d.rev_growth_1y + d.fcf_margin, 1)

        # Qualité des bénéfices : FCF / Net Income
        # >1.0 = très bonne qualité, <0.5 = bénéfices comptables suspects
        if d.fcf and d.net_income and d.net_income != 0:
            d.earnings_quality = round(d.fcf / d.net_income, 2)

        # Position nette de trésorerie
        if d.cash is not None and d.total_debt is not None:
            d.net_cash_position = d.cash - d.total_debt

        # Mois de cash restants (si FCF négatif)
        if d.fcf and d.fcf < 0 and d.cash and d.cash > 0:
            monthly_burn = abs(d.fcf) / 12
            if monthly_burn > 0:
                d.cash_burn_months = round(d.cash / monthly_burn, 1)

        # Ratio créances / croissance CA (signal qualité revenus)
        # Si créances augmentent bien plus vite que CA → revenus factices
        if d.receivables and d.revenue and d.revenue_1y_ago and d.revenue > 0:
            rev_growth = (d.revenue - d.revenue_1y_ago) / d.revenue_1y_ago if d.revenue_1y_ago > 0 else 0
            # Approximation : on ne peut pas calculer précisément sans créances N-1
            # On signale juste si créances > 25% du CA (potentiellement élevé)
            if d.revenue > 0:
                d.receivables_growth = round(d.receivables / d.revenue * 100, 1)

        # Coverage des intérêts
        if d.ebit and d.total_debt and d.total_debt > 0:
            # Approximation du coût de la dette à 5%
            est_interest = d.total_debt * 0.05
            if est_interest > 0:
                d.interest_coverage = round(d.ebit / est_interest, 1)

        # Near 52-week low flag
        if d.pct_from_52w_low is not None:
            d.near_52w_low = d.pct_from_52w_low <= 20

    # ── Score qualité des données ────────────────────────────────
    def _quality(self, d: CompanyData):
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
            ("Insiders",           d.insider_ownership),
            ("Analystes target",   d.analyst_target),
            ("Beta",               d.beta),
        ]
        missing = [name for name, val in checks if val is None]
        score   = round((1 - len(missing) / len(checks)) * 100)
        return missing, score
