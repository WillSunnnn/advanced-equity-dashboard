import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from datetime import datetime, timedelta


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Equity Fundamental Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 1.2rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        max-width: 1900px;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 0.6rem;
    }

    div[data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 8px !important;
    }

    div[data-testid="stMetric"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.78rem;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.45rem;
        font-weight: 650;
    }

    div[data-testid="stMetricDelta"] {
        font-size: 0.85rem;
    }

    h1 {
        font-size: 2rem !important;
        margin-top: 0 !important;
        margin-bottom: 0.35rem !important;
    }

    h2 {
        margin-top: 0 !important;
    }

    h3 {
        font-size: 1.2rem !important;
        margin-top: 0 !important;
        margin-bottom: 0.1rem !important;
    }

    div[data-baseweb="input"] {
        border-radius: 6px;
    }

    div[data-baseweb="select"] > div {
        border-radius: 6px;
    }

    div[data-testid="stButton"] button,
    div[data-testid="stFormSubmitButton"] button {
        border-radius: 6px;
        min-height: 39px;
    }

    div[data-testid="stPlotlyChart"] {
        margin-top: -0.15rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LAYOUT CONSTANTS
# ============================================================

TOP_CARD_HEIGHT = 122
OVERVIEW_CARD_HEIGHT = 405

OVERVIEW_CHART_HEIGHT = 245
LARGE_CHART_HEIGHT = 330
MEDIUM_CHART_HEIGHT = 285


# ============================================================
# HEADER
# ============================================================

title_col, refresh_col = st.columns(
    [7, 1],
    gap="small",
)

with title_col:

    st.title("📊 Equity Fundamental Dashboard")

    st.caption(
        "Fundamental equity analysis powered exclusively by Yahoo Finance"
    )

    st.markdown(
        "<div style='height:8px'></div>",
        unsafe_allow_html=True,
    )


with refresh_col:

    if st.button(
        "↻ Refresh Data",
        use_container_width=True,
        key="refresh_data",
    ):

        st.cache_data.clear()

        st.session_state["last_refresh"] = (
            datetime.now().strftime("%H:%M:%S")
        )

        st.rerun()

    if "last_refresh" in st.session_state:

        st.caption(
            f"Last refresh: {st.session_state['last_refresh']}"
        )


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_number(value):

    try:

        if value is None:
            return None

        if pd.isna(value):
            return None

        return float(value)

    except Exception:

        return None


def format_large_number(value):

    if value is None:
        return "N/A"

    value = float(value)

    sign = "-" if value < 0 else ""
    absolute = abs(value)

    if absolute >= 1_000_000_000_000:

        return (
            f"{sign}$"
            f"{absolute / 1_000_000_000_000:.2f}T"
        )

    if absolute >= 1_000_000_000:

        return (
            f"{sign}$"
            f"{absolute / 1_000_000_000:.2f}B"
        )

    if absolute >= 1_000_000:

        return (
            f"{sign}$"
            f"{absolute / 1_000_000:.2f}M"
        )

    return f"{sign}${absolute:,.2f}"


def format_percent(value):

    if value is None:
        return "N/A"

    return f"{value:.2f}%"


def safe_divide(a, b):

    try:

        a = float(a)
        b = float(b)

        if b == 0:
            return None

        return a / b

    except Exception:

        return None


def safe_dataframe(value):

    if isinstance(value, pd.DataFrame):
        return value

    return pd.DataFrame()


# ============================================================
# SEARCH
# ============================================================

@st.cache_data(ttl=3600)
def search_company(query):

    query = query.strip()

    if not query:
        return None

    # --------------------------------------------------------
    # Try ticker directly
    # --------------------------------------------------------

    try:

        ticker = yf.Ticker(
            query.upper()
        )

        info = ticker.info

        if info and info.get("symbol"):

            return {
                "symbol": info.get("symbol"),
                "name": info.get(
                    "longName",
                    info.get(
                        "shortName",
                        query.upper(),
                    ),
                ),
            }

    except Exception:
        pass

    # --------------------------------------------------------
    # Company search
    # --------------------------------------------------------

    try:

        search = yf.Search(
            query,
            max_results=10,
        )

        for result in search.quotes:

            if result.get("quoteType") == "EQUITY":

                return {
                    "symbol": result.get("symbol"),
                    "name": result.get(
                        "longname",
                        result.get(
                            "shortname",
                            result.get("symbol"),
                        ),
                    ),
                }

    except Exception:
        pass

    return None


# ============================================================
# LOAD COMPANY DATA
# ============================================================

@st.cache_data(ttl=900)
def load_company_data(symbol):

    ticker = yf.Ticker(symbol)

    data = {}

    # --------------------------------------------------------
    # Info
    # --------------------------------------------------------

    try:
        data["info"] = ticker.info
    except Exception:
        data["info"] = {}

    # --------------------------------------------------------
    # Price history
    # --------------------------------------------------------

    try:

        data["history"] = ticker.history(
            period="10y",
            interval="1d",
            auto_adjust=True,
        )

    except Exception:

        data["history"] = pd.DataFrame()

    # --------------------------------------------------------
    # Annual statements
    # --------------------------------------------------------

    try:
        data["income"] = ticker.income_stmt
    except Exception:
        data["income"] = pd.DataFrame()

    try:
        data["cashflow"] = ticker.cashflow
    except Exception:
        data["cashflow"] = pd.DataFrame()

    try:
        data["balance"] = ticker.balance_sheet
    except Exception:
        data["balance"] = pd.DataFrame()

    # --------------------------------------------------------
    # Quarterly statements
    # --------------------------------------------------------

    try:
        data["quarterly_income"] = ticker.quarterly_income_stmt
    except Exception:
        data["quarterly_income"] = pd.DataFrame()

    try:
        data["quarterly_cashflow"] = ticker.quarterly_cashflow
    except Exception:
        data["quarterly_cashflow"] = pd.DataFrame()

    try:
        data["quarterly_balance"] = ticker.quarterly_balance_sheet
    except Exception:
        data["quarterly_balance"] = pd.DataFrame()

    # --------------------------------------------------------
    # Yahoo TTM
    # --------------------------------------------------------

    try:

        data["ttm_income"] = safe_dataframe(
            getattr(
                ticker,
                "ttm_income_stmt",
                pd.DataFrame(),
            )
        )

    except Exception:

        data["ttm_income"] = pd.DataFrame()

    try:

        data["ttm_cashflow"] = safe_dataframe(
            getattr(
                ticker,
                "ttm_cashflow",
                pd.DataFrame(),
            )
        )

    except Exception:

        data["ttm_cashflow"] = pd.DataFrame()

    # --------------------------------------------------------
    # Estimates
    # --------------------------------------------------------

    try:
        data["earnings_estimate"] = ticker.earnings_estimate
    except Exception:
        data["earnings_estimate"] = pd.DataFrame()

    try:
        data["revenue_estimate"] = ticker.revenue_estimate
    except Exception:
        data["revenue_estimate"] = pd.DataFrame()

    try:
        data["growth_estimates"] = ticker.growth_estimates
    except Exception:
        data["growth_estimates"] = pd.DataFrame()

    try:
        data["recommendations"] = ticker.recommendations_summary
    except Exception:
        data["recommendations"] = pd.DataFrame()

    try:
        data["price_targets"] = ticker.analyst_price_targets
    except Exception:
        data["price_targets"] = {}

    return data


# ============================================================
# BENCHMARK DATA
# ============================================================

@st.cache_data(ttl=900)
def load_benchmark():

    try:

        benchmark = yf.download(
            "SPY",
            period="5y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )

        if benchmark.empty:
            return pd.Series(dtype=float)

        close = benchmark["Close"].squeeze()

        return close.dropna()

    except Exception:

        return pd.Series(dtype=float)


# ============================================================
# STATEMENT ROW HELPER
# ============================================================

def get_statement_row(
    dataframe,
    possible_names,
):

    if (
        dataframe is None
        or dataframe.empty
    ):
        return None

    for name in possible_names:

        if name in dataframe.index:

            series = dataframe.loc[name]

            series = pd.to_numeric(
                series,
                errors="coerce",
            )

            return (
                series
                .dropna()
                .sort_index()
            )

    return None


# ============================================================
# ACCOUNTING SERIES
# ============================================================

def get_revenue_series(df):

    return get_statement_row(
        df,
        [
            "Total Revenue",
            "Operating Revenue",
        ],
    )


def get_net_income_series(df):

    return get_statement_row(
        df,
        [
            "Net Income",
            "Net Income Common Stockholders",
        ],
    )


def get_operating_income_series(df):

    return get_statement_row(
        df,
        [
            "Operating Income",
            "EBIT",
        ],
    )


def get_ebit_series(df):

    return get_statement_row(
        df,
        [
            "EBIT",
            "Operating Income",
        ],
    )


def get_ebitda_series(df):

    return get_statement_row(
        df,
        [
            "EBITDA",
            "Normalized EBITDA",
        ],
    )


def get_gross_profit_series(df):

    return get_statement_row(
        df,
        [
            "Gross Profit",
        ],
    )


def get_pretax_income_series(df):

    return get_statement_row(
        df,
        [
            "Pretax Income",
            "Income Before Tax",
        ],
    )


def get_tax_provision_series(df):

    return get_statement_row(
        df,
        [
            "Tax Provision",
            "Income Tax Expense",
        ],
    )


def get_shares_series(df):

    return get_statement_row(
        df,
        [
            "Ordinary Shares Number",
            "Share Issued",
        ],
    )


def get_equity_series(df):

    return get_statement_row(
        df,
        [
            "Stockholders Equity",
            "Common Stock Equity",
            "Total Equity Gross Minority Interest",
        ],
    )


def get_cash_series(df):

    return get_statement_row(
        df,
        [
            "Cash Cash Equivalents And Short Term Investments",
            "Cash And Cash Equivalents",
            "Cash Financial",
        ],
    )


def get_current_assets_series(df):

    return get_statement_row(
        df,
        [
            "Current Assets",
            "Total Current Assets",
        ],
    )


def get_current_liabilities_series(df):

    return get_statement_row(
        df,
        [
            "Current Liabilities",
            "Total Current Liabilities",
        ],
    )


def get_interest_expense_series(df):

    return get_statement_row(
        df,
        [
            "Interest Expense",
            "Interest Expense Non Operating",
        ],
    )


# ============================================================
# DEBT
# ============================================================

def get_debt_series(df):

    direct = get_statement_row(
        df,
        [
            "Total Debt",
        ],
    )

    if direct is not None:
        return direct

    long_term = get_statement_row(
        df,
        [
            "Long Term Debt",
            "Long Term Debt And Capital Lease Obligation",
        ],
    )

    current = get_statement_row(
        df,
        [
            "Current Debt",
            "Current Debt And Capital Lease Obligation",
        ],
    )

    if (
        long_term is not None
        and current is not None
    ):

        frame = pd.concat(
            [
                long_term.rename("LT"),
                current.rename("ST"),
            ],
            axis=1,
        ).fillna(0)

        return frame["LT"] + frame["ST"]

    return long_term


# ============================================================
# FREE CASH FLOW
# ============================================================

def get_fcf_series(df):

    direct = get_statement_row(
        df,
        [
            "Free Cash Flow",
        ],
    )

    if direct is not None:
        return direct

    ocf = get_statement_row(
        df,
        [
            "Operating Cash Flow",
            "Total Cash From Operating Activities",
        ],
    )

    capex = get_statement_row(
        df,
        [
            "Capital Expenditure",
            "Capital Expenditures",
        ],
    )

    if (
        ocf is None
        or capex is None
    ):
        return None

    frame = pd.concat(
        [
            ocf.rename("OCF"),
            capex.rename("CapEx"),
        ],
        axis=1,
    ).dropna()

    if frame.empty:
        return None

    values = []

    for _, row in frame.iterrows():

        operating_cf = float(
            row["OCF"]
        )

        capex_value = float(
            row["CapEx"]
        )

        if capex_value <= 0:

            fcf = (
                operating_cf
                + capex_value
            )

        else:

            fcf = (
                operating_cf
                - capex_value
            )

        values.append(fcf)

    return pd.Series(
        values,
        index=frame.index,
    )


# ============================================================
# TTM HELPER
# ============================================================

def get_ttm_value(
    yahoo_ttm_series,
    quarterly_series,
):

    # Yahoo native TTM

    if (
        yahoo_ttm_series is not None
        and not yahoo_ttm_series.empty
    ):

        try:

            value = float(
                yahoo_ttm_series.iloc[-1]
            )

            if pd.notna(value):
                return value

        except Exception:
            pass

    # Quarterly fallback

    if (
        quarterly_series is not None
        and not quarterly_series.empty
    ):

        q = (
            quarterly_series
            .dropna()
            .sort_index()
        )

        if len(q) >= 4:

            return float(
                q.tail(4).sum()
            )

    return None


# ============================================================
# CAGR
# ============================================================

def calculate_cagr(series, years=3):

    if (
        series is None
        or series.empty
    ):
        return None

    series = (
        series
        .dropna()
        .sort_index()
    )

    if len(series) < 2:
        return None

    periods = min(
        years,
        len(series) - 1,
    )

    end = float(
        series.iloc[-1]
    )

    start = float(
        series.iloc[-1 - periods]
    )

    if (
        start <= 0
        or end <= 0
        or periods <= 0
    ):
        return None

    return (
        (end / start) ** (1 / periods)
        - 1
    ) * 100


# ============================================================
# REVENUE GROWTH
# ============================================================

def build_revenue_growth_series(
    annual_income,
    quarterly_income,
    ttm_income,
):

    annual = get_revenue_series(
        annual_income
    )

    quarterly = get_revenue_series(
        quarterly_income
    )

    ttm = get_revenue_series(
        ttm_income
    )

    result = {}

    if annual is not None:

        annual = (
            annual
            .dropna()
            .sort_index()
            .tail(6)
        )

        growth = (
            annual.pct_change()
            * 100
        ).dropna()

        for date, value in growth.tail(5).items():

            result[
                str(
                    pd.Timestamp(date).year
                )
            ] = float(value)

    # TTM growth requires prior comparable period

    current_ttm = get_ttm_value(
        ttm,
        quarterly,
    )

    if (
        current_ttm is not None
        and quarterly is not None
    ):

        q = (
            quarterly
            .dropna()
            .sort_index()
        )

        # Strict YoY TTM when enough data exist

        if len(q) >= 8:

            previous_ttm = float(
                q.iloc[-8:-4].sum()
            )

            if previous_ttm != 0:

                result["TTM"] = (
                    current_ttm
                    / previous_ttm
                    - 1
                ) * 100

    return (
        pd.Series(result)
        if result
        else None
    )


# ============================================================
# DILUTION
# ============================================================

def build_dilution_history(
    annual_balance,
    quarterly_balance,
):

    annual = get_shares_series(
        annual_balance
    )

    quarterly = get_shares_series(
        quarterly_balance
    )

    result = {}

    if annual is not None:

        annual = (
            annual
            .dropna()
            .sort_index()
            .tail(6)
        )

        growth = (
            annual.pct_change()
            * 100
        ).dropna()

        for date, value in growth.tail(5).items():

            result[
                str(
                    pd.Timestamp(date).year
                )
            ] = float(value)

    if quarterly is not None:

        q = (
            quarterly
            .dropna()
            .sort_index()
        )

        if len(q) >= 5:

            current = float(
                q.iloc[-1]
            )

            one_year_ago = float(
                q.iloc[-5]
            )

            if one_year_ago != 0:

                result["TTM"] = (
                    current
                    / one_year_ago
                    - 1
                ) * 100

    return (
        pd.Series(result)
        if result
        else None
    )


# ============================================================
# FCF HISTORY
# ============================================================

def build_fcf_history(
    annual_cashflow,
    quarterly_cashflow,
    ttm_cashflow,
):

    annual = get_fcf_series(
        annual_cashflow
    )

    quarterly = get_fcf_series(
        quarterly_cashflow
    )

    ttm = get_fcf_series(
        ttm_cashflow
    )

    result = {}

    if annual is not None:

        annual = (
            annual
            .dropna()
            .sort_index()
            .tail(5)
        )

        for date, value in annual.items():

            result[
                str(
                    pd.Timestamp(date).year
                )
            ] = float(value)

    ttm_value = get_ttm_value(
        ttm,
        quarterly,
    )

    if ttm_value is not None:

        result["TTM"] = (
            ttm_value
        )

    return (
        pd.Series(result)
        if result
        else None
    )


# ============================================================
# DEBT / EQUITY
# ============================================================

def build_debt_to_equity_history(
    annual_balance,
    quarterly_balance,
):

    debt = get_debt_series(
        annual_balance
    )

    equity = get_equity_series(
        annual_balance
    )

    q_debt = get_debt_series(
        quarterly_balance
    )

    q_equity = get_equity_series(
        quarterly_balance
    )

    result = {}

    if (
        debt is not None
        and equity is not None
    ):

        df = pd.concat(
            [
                debt.rename("Debt"),
                equity.rename("Equity"),
            ],
            axis=1,
        ).dropna()

        df = (
            df
            .sort_index()
            .tail(5)
        )

        for date, row in df.iterrows():

            if row["Equity"] != 0:

                result[
                    str(
                        pd.Timestamp(date).year
                    )
                ] = (
                    row["Debt"]
                    / row["Equity"]
                )

    if (
        q_debt is not None
        and q_equity is not None
    ):

        df = pd.concat(
            [
                q_debt.rename("Debt"),
                q_equity.rename("Equity"),
            ],
            axis=1,
        ).dropna()

        df = df.sort_index()

        if not df.empty:

            latest = df.iloc[-1]

            if latest["Equity"] != 0:

                result["Latest"] = (
                    latest["Debt"]
                    / latest["Equity"]
                )

    return (
        pd.Series(result)
        if result
        else None
    )


# ============================================================
# ROE
# ============================================================

def build_roe_history(
    annual_income,
    annual_balance,
    quarterly_income,
    quarterly_balance,
    ttm_income,
):

    net_income = get_net_income_series(
        annual_income
    )

    equity = get_equity_series(
        annual_balance
    )

    q_net = get_net_income_series(
        quarterly_income
    )

    q_equity = get_equity_series(
        quarterly_balance
    )

    ttm_net = get_net_income_series(
        ttm_income
    )

    result = {}

    if (
        net_income is not None
        and equity is not None
    ):

        df = pd.concat(
            [
                net_income.rename("NI"),
                equity.rename("Equity"),
            ],
            axis=1,
        ).dropna()

        df = df.sort_index()

        df["AverageEquity"] = (
            df["Equity"]
            + df["Equity"].shift(1)
        ) / 2

        df["ROE"] = (
            df["NI"]
            / df["AverageEquity"]
            * 100
        )

        for date, value in (
            df["ROE"]
            .dropna()
            .tail(5)
            .items()
        ):

            result[
                str(
                    pd.Timestamp(date).year
                )
            ] = float(value)

    ttm_net_income = get_ttm_value(
        ttm_net,
        q_net,
    )

    if (
        ttm_net_income is not None
        and q_equity is not None
    ):

        q_equity = (
            q_equity
            .dropna()
            .sort_index()
        )

        if len(q_equity) >= 5:

            avg_equity = (
                float(q_equity.iloc[-1])
                + float(q_equity.iloc[-5])
            ) / 2

            if avg_equity != 0:

                result["TTM"] = (
                    ttm_net_income
                    / avg_equity
                    * 100
                )

    return (
        pd.Series(result)
        if result
        else None
    )


# ============================================================
# MARGINS HISTORY
# ============================================================

def build_margin_history(
    annual_income,
    annual_cashflow,
    quarterly_income,
    quarterly_cashflow,
    ttm_income,
    ttm_cashflow,
):

    annual_revenue = get_revenue_series(
        annual_income
    )

    annual_gross = get_gross_profit_series(
        annual_income
    )

    annual_ebit = get_ebit_series(
        annual_income
    )

    annual_net = get_net_income_series(
        annual_income
    )

    annual_fcf = get_fcf_series(
        annual_cashflow
    )

    result = {}

    if annual_revenue is not None:

        dates = annual_revenue.index

        for date in dates:

            revenue = clean_number(
                annual_revenue.get(
                    date
                )
            )

            if (
                revenue is None
                or revenue == 0
            ):
                continue

            year = str(
                pd.Timestamp(date).year
            )

            row = {}

            if (
                annual_gross is not None
                and date in annual_gross.index
            ):

                row["Gross"] = (
                    annual_gross.loc[date]
                    / revenue
                    * 100
                )

            if (
                annual_ebit is not None
                and date in annual_ebit.index
            ):

                row["EBIT"] = (
                    annual_ebit.loc[date]
                    / revenue
                    * 100
                )

            if (
                annual_net is not None
                and date in annual_net.index
            ):

                row["Net"] = (
                    annual_net.loc[date]
                    / revenue
                    * 100
                )

            if (
                annual_fcf is not None
                and date in annual_fcf.index
            ):

                row["FCF"] = (
                    annual_fcf.loc[date]
                    / revenue
                    * 100
                )

            result[year] = row

    # TTM

    ttm_revenue = get_ttm_value(
        get_revenue_series(
            ttm_income
        ),
        get_revenue_series(
            quarterly_income
        ),
    )

    if (
        ttm_revenue is not None
        and ttm_revenue != 0
    ):

        ttm_row = {}

        values = {
            "Gross": get_ttm_value(
                get_gross_profit_series(
                    ttm_income
                ),
                get_gross_profit_series(
                    quarterly_income
                ),
            ),
            "EBIT": get_ttm_value(
                get_ebit_series(
                    ttm_income
                ),
                get_ebit_series(
                    quarterly_income
                ),
            ),
            "Net": get_ttm_value(
                get_net_income_series(
                    ttm_income
                ),
                get_net_income_series(
                    quarterly_income
                ),
            ),
            "FCF": get_ttm_value(
                get_fcf_series(
                    ttm_cashflow
                ),
                get_fcf_series(
                    quarterly_cashflow
                ),
            ),
        }

        for name, value in values.items():

            if value is not None:

                ttm_row[name] = (
                    value
                    / ttm_revenue
                    * 100
                )

        result["TTM"] = ttm_row

    if not result:
        return pd.DataFrame()

    frame = (
        pd.DataFrame(result)
        .T
    )

    return frame.tail(6)


# ============================================================
# ROIC
# ============================================================

def build_roic_history(
    annual_income,
    annual_balance,
):

    ebit = get_ebit_series(
        annual_income
    )

    pretax = get_pretax_income_series(
        annual_income
    )

    taxes = get_tax_provision_series(
        annual_income
    )

    debt = get_debt_series(
        annual_balance
    )

    equity = get_equity_series(
        annual_balance
    )

    cash = get_cash_series(
        annual_balance
    )

    if (
        ebit is None
        or debt is None
        or equity is None
    ):
        return None

    frame = pd.concat(
        [
            ebit.rename("EBIT"),
            debt.rename("Debt"),
            equity.rename("Equity"),
        ],
        axis=1,
    )

    if cash is not None:

        frame = frame.join(
            cash.rename("Cash")
        )

    else:

        frame["Cash"] = 0

    if (
        pretax is not None
        and taxes is not None
    ):

        frame = frame.join(
            pretax.rename("Pretax")
        )

        frame = frame.join(
            taxes.rename("Taxes")
        )

    frame = frame.dropna(
        subset=[
            "EBIT",
            "Debt",
            "Equity",
        ]
    )

    result = {}

    for date, row in frame.iterrows():

        tax_rate = 0.21

        if (
            "Pretax" in row.index
            and "Taxes" in row.index
        ):

            pretax_value = clean_number(
                row.get("Pretax")
            )

            tax_value = clean_number(
                row.get("Taxes")
            )

            if (
                pretax_value is not None
                and pretax_value > 0
                and tax_value is not None
            ):

                effective_rate = (
                    tax_value
                    / pretax_value
                )

                if (
                    effective_rate >= 0
                    and effective_rate <= 0.50
                ):

                    tax_rate = (
                        effective_rate
                    )

        nopat = (
            row["EBIT"]
            * (1 - tax_rate)
        )

        invested_capital = (
            row["Debt"]
            + row["Equity"]
            - (
                row["Cash"]
                if pd.notna(row["Cash"])
                else 0
            )
        )

        if invested_capital != 0:

            result[
                str(
                    pd.Timestamp(date).year
                )
            ] = (
                nopat
                / invested_capital
                * 100
            )

    return (
        pd.Series(result)
        if result
        else None
    )


# ============================================================
# NET DEBT / EBITDA
# ============================================================

def build_net_debt_ebitda_history(
    annual_income,
    annual_balance,
):

    debt = get_debt_series(
        annual_balance
    )

    cash = get_cash_series(
        annual_balance
    )

    ebitda = get_ebitda_series(
        annual_income
    )

    if (
        debt is None
        or ebitda is None
    ):
        return None

    frame = pd.concat(
        [
            debt.rename("Debt"),
            ebitda.rename("EBITDA"),
        ],
        axis=1,
    )

    if cash is not None:

        frame = frame.join(
            cash.rename("Cash")
        )

    else:

        frame["Cash"] = 0

    frame = frame.dropna(
        subset=[
            "Debt",
            "EBITDA",
        ]
    )

    result = {}

    for date, row in frame.iterrows():

        ebitda_value = float(
            row["EBITDA"]
        )

        if ebitda_value == 0:
            continue

        net_debt = (
            float(row["Debt"])
            - (
                float(row["Cash"])
                if pd.notna(row["Cash"])
                else 0
            )
        )

        result[
            str(
                pd.Timestamp(date).year
            )
        ] = (
            net_debt
            / ebitda_value
        )

    return (
        pd.Series(result)
        if result
        else None
    )


# ============================================================
# GENERIC CHARTS
# ============================================================

def create_line_chart(
    series,
    percentage=False,
    billions=False,
    ratio=False,
    height=280,
):

    if (
        series is None
        or series.empty
    ):
        return None

    display = series.copy()

    if billions:

        display = (
            display
            / 1_000_000_000
        )

    labels = [
        str(x)
        for x in display.index
    ]

    text = []

    for value in display.values:

        if percentage:

            text.append(
                f"{value:.1f}%"
            )

        elif billions:

            text.append(
                f"${value:.1f}B"
            )

        elif ratio:

            text.append(
                f"{value:.2f}x"
            )

        else:

            text.append(
                f"{value:.2f}"
            )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=labels,
            y=display.values,
            mode="lines+markers+text",
            line=dict(
                width=2.2,
            ),
            marker=dict(
                size=6,
            ),
            text=text,
            textposition="top center",
            textfont=dict(
                size=10,
            ),
            hovertemplate=(
                "%{x}<br>"
                "%{y:.2f}"
                + (
                    "%"
                    if percentage
                    else "x"
                    if ratio
                    else ""
                )
                + "<extra></extra>"
            ),
        )
    )

    if display.min() < 0:

        fig.add_hline(
            y=0,
            line_dash="dot",
            opacity=0.35,
        )

    fig.update_layout(
        height=height,
        template="plotly_dark",
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(
            l=5,
            r=5,
            t=28,
            b=5,
        ),
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=labels,
            showgrid=False,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=(
                "rgba(128,128,128,0.13)"
            ),
            ticksuffix=(
                "%"
                if percentage
                else ""
            ),
        ),
    )

    return fig


def create_bar_chart(
    series,
    percentage=False,
    ratio=False,
    height=280,
):

    if (
        series is None
        or series.empty
    ):
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=[
                str(x)
                for x in series.index
            ],
            y=series.values,
            text=[
                (
                    f"{x:.1f}%"
                    if percentage
                    else f"{x:.2f}x"
                    if ratio
                    else f"{x:.2f}"
                )
                for x in series.values
            ],
            textposition="outside",
            cliponaxis=False,
        )
    )

    if series.min() < 0:

        fig.add_hline(
            y=0,
            line_dash="dot",
            opacity=0.35,
        )

    fig.update_layout(
        height=height,
        template="plotly_dark",
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(
            l=5,
            r=5,
            t=30,
            b=5,
        ),
        xaxis=dict(
            showgrid=False,
        ),
        yaxis=dict(
            ticksuffix=(
                "%"
                if percentage
                else ""
            ),
            gridcolor=(
                "rgba(128,128,128,0.13)"
            ),
        ),
    )

    return fig


def create_multi_line_chart(
    dataframe,
    percentage=False,
    height=330,
):

    if (
        dataframe is None
        or dataframe.empty
    ):
        return None

    fig = go.Figure()

    for column in dataframe.columns:

        data = (
            dataframe[column]
            .dropna()
        )

        if data.empty:
            continue

        fig.add_trace(
            go.Scatter(
                x=[
                    str(x)
                    for x in data.index
                ],
                y=data.values,
                mode="lines+markers",
                name=column,
            )
        )

    fig.update_layout(
        height=height,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(
            l=10,
            r=10,
            t=25,
            b=10,
        ),
        legend=dict(
            orientation="h",
            y=1.03,
        ),
        yaxis=dict(
            ticksuffix=(
                "%"
                if percentage
                else ""
            ),
            gridcolor=(
                "rgba(128,128,128,0.13)"
            ),
        ),
        xaxis=dict(
            showgrid=False,
        ),
    )

    return fig


# ============================================================
# HISTORICAL VALUATION HELPERS
# ============================================================

def get_price_near_date(
    history,
    target_date,
):

    if (
        history is None
        or history.empty
        or "Close" not in history.columns
    ):
        return None

    prices = (
        history["Close"]
        .dropna()
        .copy()
    )

    if getattr(
        prices.index,
        "tz",
        None,
    ) is not None:

        prices.index = (
            prices.index
            .tz_localize(None)
        )

    target_date = pd.Timestamp(
        target_date
    )

    if target_date.tzinfo is not None:

        target_date = (
            target_date
            .tz_localize(None)
        )

    nearby = prices.loc[
        (
            prices.index
            >= target_date
            - timedelta(days=10)
        )
        &
        (
            prices.index
            <= target_date
            + timedelta(days=10)
        )
    ]

    if nearby.empty:
        return None

    distances = abs(
        nearby.index
        - target_date
    )

    position = distances.argmin()

    return float(
        nearby.iloc[position]
    )


def build_historical_valuation(
    income,
    cashflow,
    balance,
    history,
):

    revenue = get_revenue_series(
        income
    )

    net_income = get_net_income_series(
        income
    )

    ebitda = get_ebitda_series(
        income
    )

    fcf = get_fcf_series(
        cashflow
    )

    equity = get_equity_series(
        balance
    )

    debt = get_debt_series(
        balance
    )

    cash = get_cash_series(
        balance
    )

    shares = get_shares_series(
        balance
    )

    if shares is None:
        return pd.DataFrame()

    rows = []

    def value_at(
        series,
        date,
    ):

        if series is None:
            return None

        try:

            if date in series.index:

                return clean_number(
                    series.loc[date]
                )

        except Exception:
            pass

        return None

    for date in sorted(
        set(shares.index)
    ):

        date = pd.Timestamp(
            date
        )

        price = get_price_near_date(
            history,
            date,
        )

        share_count = value_at(
            shares,
            date,
        )

        if (
            price is None
            or share_count is None
        ):
            continue

        market_cap = (
            price
            * share_count
        )

        debt_value = value_at(
            debt,
            date,
        )

        cash_value = value_at(
            cash,
            date,
        )

        enterprise_value = (
            market_cap
            + (
                debt_value
                if debt_value is not None
                else 0
            )
            - (
                cash_value
                if cash_value is not None
                else 0
            )
        )

        row = {
            "Year": date.year
        }

        earnings = value_at(
            net_income,
            date,
        )

        book_value = value_at(
            equity,
            date,
        )

        sales = value_at(
            revenue,
            date,
        )

        EBITDA = value_at(
            ebitda,
            date,
        )

        FCF = value_at(
            fcf,
            date,
        )

        if (
            earnings is not None
            and earnings > 0
        ):

            row["P/E"] = (
                market_cap
                / earnings
            )

        if (
            book_value is not None
            and book_value > 0
        ):

            row["P/B"] = (
                market_cap
                / book_value
            )

        if (
            sales is not None
            and sales > 0
        ):

            row["EV/Revenue"] = (
                enterprise_value
                / sales
            )

        if (
            EBITDA is not None
            and EBITDA > 0
        ):

            row["EV/EBITDA"] = (
                enterprise_value
                / EBITDA
            )

        if (
            FCF is not None
            and FCF > 0
        ):

            row["P/FCF"] = (
                market_cap
                / FCF
            )

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .drop_duplicates(
            subset=["Year"],
            keep="last",
        )
        .sort_values("Year")
    )


# ============================================================
# VALUATION SUMMARY
# ============================================================

def valuation_summary(
    valuation_history,
    current_metrics,
    years=5,
):

    if (
        valuation_history is None
        or valuation_history.empty
    ):
        return pd.DataFrame()

    history = (
        valuation_history
        .tail(years)
        .copy()
    )

    rows = []

    for metric, current in current_metrics.items():

        if (
            current is None
            or metric not in history.columns
        ):
            continue

        values = (
            pd.to_numeric(
                history[metric],
                errors="coerce",
            )
            .dropna()
        )

        values = values[
            (values > 0)
            & (values < 500)
        ]

        if values.empty:
            continue

        average = float(
            values.mean()
        )

        median = float(
            values.median()
        )

        premium = (
            current
            / average
            - 1
        ) * 100

        percentile = (
            values.lt(
                current
            ).mean()
            * 100
        )

        rows.append(
            {
                "Metric": metric,
                "Current": current,
                "Average": average,
                "Median": median,
                "Premium / Discount": premium,
                "Historical Percentile": percentile,
            }
        )

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .set_index("Metric")
    )


# ============================================================
# VALUATION OVERVIEW CHART
# ============================================================

def create_valuation_chart(
    current_metrics,
    valuation_history,
    years,
):

    current = pd.Series(
        current_metrics,
        dtype="float64",
    ).dropna()

    if current.empty:
        return None

    if (
        valuation_history is None
        or valuation_history.empty
    ):

        history = pd.DataFrame()

    else:

        history = valuation_history.tail(
            years
        )

    averages = {}

    for metric in current.index:

        if metric not in history.columns:
            continue

        values = (
            pd.to_numeric(
                history[metric],
                errors="coerce",
            )
            .dropna()
        )

        values = values[
            (values > 0)
            & (values < 500)
        ]

        if not values.empty:

            averages[metric] = (
                values.mean()
            )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=current.index,
            y=current.values,
            name="Current",
            text=[
                f"{x:.1f}x"
                for x in current.values
            ],
            textposition="outside",
        )
    )

    average_x = []
    average_y = []

    for metric in current.index:

        if metric in averages:

            average_x.append(
                metric
            )

            average_y.append(
                averages[metric]
            )

    if average_x:

        fig.add_trace(
            go.Scatter(
                x=average_x,
                y=average_y,
                mode="markers",
                name=f"{years}Y Average",
                marker=dict(
                    symbol="line-ew",
                    size=38,
                    color="#ff3b3b",
                    line=dict(
                        color="#ff3b3b",
                        width=4,
                    ),
                ),
            )
        )

    fig.update_layout(
        height=320,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(
            l=10,
            r=10,
            t=45,
            b=10,
        ),
        legend=dict(
            orientation="h",
            y=1.04,
        ),
        xaxis=dict(
            showgrid=False,
        ),
        yaxis=dict(
            title="Multiple (x)",
            gridcolor=(
                "rgba(128,128,128,0.13)"
            ),
            rangemode="tozero",
        ),
    )

    return fig


# ============================================================
# STOCK RISK
# ============================================================

def calculate_stock_metrics(
    history,
    benchmark,
):

    if (
        history is None
        or history.empty
        or "Close" not in history.columns
    ):
        return {}

    stock = (
        history["Close"]
        .dropna()
        .copy()
    )

    if getattr(
        stock.index,
        "tz",
        None,
    ) is not None:

        stock.index = (
            stock.index
            .tz_localize(None)
        )

    returns = (
        stock.pct_change()
        .dropna()
    )

    metrics = {}

    # --------------------------------------------------------
    # Annual volatility
    # --------------------------------------------------------

    one_year = (
        returns.tail(252)
    )

    if not one_year.empty:

        metrics["Volatility"] = (
            one_year.std()
            * np.sqrt(252)
            * 100
        )

    # --------------------------------------------------------
    # Max drawdown
    # --------------------------------------------------------

    running_max = stock.cummax()

    drawdown = (
        stock
        / running_max
        - 1
    )

    if not drawdown.empty:

        metrics["Max Drawdown"] = (
            drawdown.min()
            * 100
        )

    # --------------------------------------------------------
    # Beta
    # --------------------------------------------------------

    if (
        benchmark is not None
        and not benchmark.empty
    ):

        benchmark = (
            benchmark.copy()
        )

        if getattr(
            benchmark.index,
            "tz",
            None,
        ) is not None:

            benchmark.index = (
                benchmark.index
                .tz_localize(None)
            )

        benchmark_returns = (
            benchmark.pct_change()
            .dropna()
        )

        combined = pd.concat(
            [
                returns.rename("Stock"),
                benchmark_returns.rename(
                    "Market"
                ),
            ],
            axis=1,
        ).dropna()

        if len(combined) > 50:

            covariance = (
                combined["Stock"]
                .cov(
                    combined["Market"]
                )
            )

            market_variance = (
                combined["Market"]
                .var()
            )

            if market_variance != 0:

                metrics["Beta"] = (
                    covariance
                    / market_variance
                )

    return metrics


def period_return(
    history,
    days=None,
    years=None,
):

    if (
        history is None
        or history.empty
    ):
        return None

    close = (
        history["Close"]
        .dropna()
        .copy()
    )

    if getattr(
        close.index,
        "tz",
        None,
    ) is not None:

        close.index = (
            close.index
            .tz_localize(None)
        )

    if years is not None:

        cutoff = (
            pd.Timestamp.now()
            - pd.DateOffset(
                years=years
            )
        )

    else:

        cutoff = (
            pd.Timestamp.now()
            - pd.Timedelta(
                days=days
            )
        )

    subset = close[
        close.index
        >= cutoff
    ]

    if len(subset) < 2:
        return None

    return (
        subset.iloc[-1]
        / subset.iloc[0]
        - 1
    ) * 100


# ============================================================
# SEARCH FORM
# ============================================================

with st.form(
    "company_search_form",
    border=False,
):

    search_col, button_col = st.columns(
        [8, 1],
        gap="small",
    )

    with search_col:

        search_query = st.text_input(
            "Ticker",
            value=st.session_state.get(
                "search_query",
                "AAPL",
            ),
            placeholder=(
                "Ticker or company name "
                "(e.g. AAPL, Microsoft, Nvidia...)"
            ),
            label_visibility="collapsed",
        )

    with button_col:

        analyze = st.form_submit_button(
            "Analyze",
            use_container_width=True,
        )


if analyze:

    st.session_state[
        "search_query"
    ] = search_query

    st.session_state[
        "active_query"
    ] = search_query


if "active_query" not in st.session_state:

    st.session_state[
        "active_query"
    ] = "AAPL"


# ============================================================
# LOAD SELECTED COMPANY
# ============================================================

company = search_company(
    st.session_state[
        "active_query"
    ]
)

if company is None:

    st.error(
        "Company not found."
    )

    st.stop()


symbol = company["symbol"]


with st.spinner(
    f"Loading {symbol}..."
):

    company_data = load_company_data(
        symbol
    )


# ============================================================
# UNPACK DATA
# ============================================================

info = company_data[
    "info"
]

history = company_data[
    "history"
]

income = company_data[
    "income"
]

cashflow = company_data[
    "cashflow"
]

balance = company_data[
    "balance"
]

quarterly_income = company_data[
    "quarterly_income"
]

quarterly_cashflow = company_data[
    "quarterly_cashflow"
]

quarterly_balance = company_data[
    "quarterly_balance"
]

ttm_income = company_data[
    "ttm_income"
]

ttm_cashflow = company_data[
    "ttm_cashflow"
]


# ============================================================
# COMPANY HEADER
# ============================================================

company_name = info.get(
    "longName",
    info.get(
        "shortName",
        company["name"],
    ),
)

exchange = info.get(
    "exchange",
    "",
)

sector = info.get(
    "sector",
    "",
)

industry = info.get(
    "industry",
    "",
)


current_price = clean_number(
    info.get(
        "currentPrice",
        info.get(
            "regularMarketPrice"
        ),
    )
)

previous_close = clean_number(
    info.get(
        "previousClose"
    )
)

market_cap = clean_number(
    info.get(
        "marketCap"
    )
)

enterprise_value = clean_number(
    info.get(
        "enterpriseValue"
    )
)

forward_pe = clean_number(
    info.get(
        "forwardPE"
    )
)


daily_change = None

if (
    current_price is not None
    and previous_close is not None
    and previous_close != 0
):

    daily_change = (
        current_price
        / previous_close
        - 1
    ) * 100


header, c1, c2, c3, c4 = st.columns(
    [
        2.45,
        1.25,
        1.25,
        1.25,
        1.25,
    ],
    gap="small",
)


with header:

    with st.container(
        border=True,
        height=TOP_CARD_HEIGHT,
    ):

        st.subheader(
            company_name
        )

        st.caption(
            f"{symbol}"
            + (
                f" · {exchange}"
                if exchange
                else ""
            )
        )

        details = []

        if sector:
            details.append(
                sector
            )

        if industry:
            details.append(
                industry
            )

        st.caption(
            " · ".join(details)
        )


with c1:

    with st.container(
        border=True,
        height=TOP_CARD_HEIGHT,
    ):

        st.metric(
            "Share Price",
            (
                f"${current_price:,.2f}"
                if current_price
                is not None
                else "N/A"
            ),
            (
                f"{daily_change:+.2f}%"
                if daily_change
                is not None
                else None
            ),
        )


with c2:

    with st.container(
        border=True,
        height=TOP_CARD_HEIGHT,
    ):

        st.metric(
            "Market Cap",
            format_large_number(
                market_cap
            ),
        )


with c3:

    with st.container(
        border=True,
        height=TOP_CARD_HEIGHT,
    ):

        st.metric(
            "Enterprise Value",
            format_large_number(
                enterprise_value
            ),
        )


with c4:

    with st.container(
        border=True,
        height=TOP_CARD_HEIGHT,
    ):

        st.metric(
            "Forward P/E",
            (
                f"{forward_pe:.2f}x"
                if forward_pe
                is not None
                else "N/A"
            ),
        )


# ============================================================
# BUILD DATA
# ============================================================

revenue_growth = (
    build_revenue_growth_series(
        income,
        quarterly_income,
        ttm_income,
    )
)

dilution = (
    build_dilution_history(
        balance,
        quarterly_balance,
    )
)

fcf_history = (
    build_fcf_history(
        cashflow,
        quarterly_cashflow,
        ttm_cashflow,
    )
)

debt_equity = (
    build_debt_to_equity_history(
        balance,
        quarterly_balance,
    )
)

roe = (
    build_roe_history(
        income,
        balance,
        quarterly_income,
        quarterly_balance,
        ttm_income,
    )
)

margin_history = (
    build_margin_history(
        income,
        cashflow,
        quarterly_income,
        quarterly_cashflow,
        ttm_income,
        ttm_cashflow,
    )
)

roic = (
    build_roic_history(
        income,
        balance,
    )
)

net_debt_ebitda = (
    build_net_debt_ebitda_history(
        income,
        balance,
    )
)

valuation_history = (
    build_historical_valuation(
        income,
        cashflow,
        balance,
        history,
    )
)


# ============================================================
# TABS
# ============================================================

(
    overview_tab,
    financials_tab,
    profitability_tab,
    valuation_tab,
    balance_tab,
    estimates_tab,
    risk_tab,
) = st.tabs(
    [
        "Overview",
        "Financials",
        "Profitability",
        "Valuation",
        "Balance Sheet",
        "Estimates",
        "Stock & Risk",
    ]
)


# ============================================================
# OVERVIEW
# ============================================================

with overview_tab:

    row1, row2, row3, row4 = st.columns(
        4,
        gap="small",
    )

    # --------------------------------------------------------
    # Revenue Growth
    # --------------------------------------------------------

    with row1:

        with st.container(
            border=True,
            height=OVERVIEW_CARD_HEIGHT,
        ):

            st.subheader(
                "Revenue Growth"
            )

            st.caption(
                "Annual growth · 5Y + TTM"
            )

            if (
                revenue_growth is not None
                and not revenue_growth.empty
            ):

                st.metric(
                    "Latest Growth",
                    f"{revenue_growth.iloc[-1]:+.2f}%",
                )

                st.plotly_chart(
                    create_line_chart(
                        revenue_growth,
                        percentage=True,
                        height=OVERVIEW_CHART_HEIGHT,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )

            else:

                st.info(
                    "Revenue growth unavailable"
                )

    # --------------------------------------------------------
    # Dilution
    # --------------------------------------------------------

    with row2:

        with st.container(
            border=True,
            height=OVERVIEW_CARD_HEIGHT,
        ):

            st.subheader(
                "Dilution"
            )

            st.caption(
                "Change in shares · 5Y + TTM"
            )

            if (
                dilution is not None
                and not dilution.empty
            ):

                st.metric(
                    "Latest Dilution",
                    f"{dilution.iloc[-1]:+.2f}%",
                )

                st.plotly_chart(
                    create_bar_chart(
                        dilution,
                        percentage=True,
                        height=OVERVIEW_CHART_HEIGHT,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )

            else:

                st.info(
                    "Dilution unavailable"
                )

    # --------------------------------------------------------
    # FCF
    # --------------------------------------------------------

    with row3:

        with st.container(
            border=True,
            height=OVERVIEW_CARD_HEIGHT,
        ):

            st.subheader(
                "Free Cash Flow"
            )

            st.caption(
                "Annual FCF · 5Y + TTM"
            )

            if (
                fcf_history is not None
                and not fcf_history.empty
            ):

                st.metric(
                    "Latest FCF",
                    format_large_number(
                        fcf_history.iloc[-1]
                    ),
                )

                st.plotly_chart(
                    create_line_chart(
                        fcf_history,
                        billions=True,
                        height=OVERVIEW_CHART_HEIGHT,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )

    # --------------------------------------------------------
    # Stock
    # --------------------------------------------------------

    with row4:

        with st.container(
            border=True,
            height=OVERVIEW_CARD_HEIGHT,
        ):

            st.subheader(
                "Stock"
            )

            st.caption(
                "Share price performance · 5Y"
            )

            stock_5y = period_return(
                history,
                years=5,
            )

            st.metric(
                "5Y Performance",
                (
                    f"{stock_5y:+.2f}%"
                    if stock_5y is not None
                    else "N/A"
                ),
            )

            if (
                history is not None
                and not history.empty
            ):

                price = history[
                    "Close"
                ].dropna().copy()

                if getattr(
                    price.index,
                    "tz",
                    None,
                ) is not None:

                    price.index = (
                        price.index
                        .tz_localize(None)
                    )

                cutoff = (
                    pd.Timestamp.now()
                    - pd.DateOffset(
                        years=5
                    )
                )

                price = price[
                    price.index
                    >= cutoff
                ]

                if len(price) >= 2:

                    normalized = (
                        price
                        / price.iloc[0]
                        - 1
                    ) * 100

                    fig = go.Figure()

                    fig.add_trace(
                        go.Scatter(
                            x=normalized.index,
                            y=normalized.values,
                            mode="lines",
                            fill="tozeroy",
                            fillcolor=(
                                "rgba(70,200,110,0.10)"
                            ),
                        )
                    )

                    fig.update_layout(
                        height=OVERVIEW_CHART_HEIGHT,
                        template="plotly_dark",
                        showlegend=False,
                        paper_bgcolor=(
                            "rgba(0,0,0,0)"
                        ),
                        plot_bgcolor=(
                            "rgba(0,0,0,0)"
                        ),
                        margin=dict(
                            l=5,
                            r=5,
                            t=25,
                            b=5,
                        ),
                        yaxis=dict(
                            ticksuffix="%",
                            gridcolor=(
                                "rgba(128,128,128,0.13)"
                            ),
                        ),
                        xaxis=dict(
                            showgrid=False,
                        ),
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={
                            "displayModeBar": False
                        },
                    )


    # ========================================================
    # OVERVIEW ROW 2
    # ========================================================

    o1, o2, o3, o4 = st.columns(
        4,
        gap="small",
    )

    # --------------------------------------------------------
    # ROIC
    # --------------------------------------------------------

    with o1:

        with st.container(
            border=True,
            height=OVERVIEW_CARD_HEIGHT,
        ):

            st.subheader(
                "ROIC"
            )

            st.caption(
                "Return on invested capital"
            )

            if (
                roic is not None
                and not roic.empty
            ):

                st.metric(
                    "Latest ROIC",
                    f"{roic.iloc[-1]:.2f}%",
                )

                st.plotly_chart(
                    create_line_chart(
                        roic,
                        percentage=True,
                        height=OVERVIEW_CHART_HEIGHT,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )

            else:

                st.info(
                    "ROIC unavailable"
                )

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    with o2:

        with st.container(
            border=True,
            height=OVERVIEW_CARD_HEIGHT,
        ):

            st.subheader(
                "Return on Equity"
            )

            st.caption(
                "ROE · 5Y + TTM"
            )

            if (
                roe is not None
                and not roe.empty
            ):

                st.metric(
                    "Latest ROE",
                    f"{roe.iloc[-1]:.2f}%",
                )

                st.plotly_chart(
                    create_line_chart(
                        roe,
                        percentage=True,
                        height=OVERVIEW_CHART_HEIGHT,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )

    # --------------------------------------------------------
    # Net Debt / EBITDA
    # --------------------------------------------------------

    with o3:

        with st.container(
            border=True,
            height=OVERVIEW_CARD_HEIGHT,
        ):

            st.subheader(
                "Net Debt / EBITDA"
            )

            st.caption(
                "Balance sheet leverage"
            )

            if (
                net_debt_ebitda is not None
                and not net_debt_ebitda.empty
            ):

                st.metric(
                    "Latest",
                    f"{net_debt_ebitda.iloc[-1]:.2f}x",
                )

                st.plotly_chart(
                    create_line_chart(
                        net_debt_ebitda,
                        ratio=True,
                        height=OVERVIEW_CHART_HEIGHT,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )

            else:

                st.info(
                    "Net Debt / EBITDA unavailable"
                )

    # --------------------------------------------------------
    # FCF Yield
    # --------------------------------------------------------

    with o4:

        with st.container(
            border=True,
            height=OVERVIEW_CARD_HEIGHT,
        ):

            st.subheader(
                "FCF Yield"
            )

            st.caption(
                "TTM Free Cash Flow / Market Cap"
            )

            ttm_fcf = get_ttm_value(
                get_fcf_series(
                    ttm_cashflow
                ),
                get_fcf_series(
                    quarterly_cashflow
                ),
            )

            fcf_yield = None

            if (
                ttm_fcf is not None
                and market_cap is not None
                and market_cap != 0
            ):

                fcf_yield = (
                    ttm_fcf
                    / market_cap
                    * 100
                )

            st.metric(
                "Current FCF Yield",
                (
                    f"{fcf_yield:.2f}%"
                    if fcf_yield
                    is not None
                    else "N/A"
                ),
            )

            st.markdown(
                "<div style='height:35px'></div>",
                unsafe_allow_html=True,
            )

            st.caption(
                "A higher FCF yield means the company generates "
                "more free cash flow relative to its market value."
            )


# ============================================================
# FINANCIALS
# ============================================================

with financials_tab:

    st.subheader(
        "Financial History"
    )

    st.caption(
        "Annual income statement and cash-flow trends"
    )

    revenue = get_revenue_series(
        income
    )

    ebitda = get_ebitda_series(
        income
    )

    ebit = get_ebit_series(
        income
    )

    net_income = get_net_income_series(
        income
    )

    fcf = get_fcf_series(
        cashflow
    )

    financial_data = {}

    for name, series in {
        "Revenue": revenue,
        "EBITDA": ebitda,
        "EBIT": ebit,
        "Net Income": net_income,
        "Free Cash Flow": fcf,
    }.items():

        if series is not None:

            financial_data[
                name
            ] = (
                series.tail(5)
                / 1_000_000_000
            )

    if financial_data:

        financial_df = pd.DataFrame(
            financial_data
        )

        financial_df.index = [
            str(
                pd.Timestamp(x).year
            )
            for x
            in financial_df.index
        ]

        st.plotly_chart(
            create_multi_line_chart(
                financial_df,
                percentage=False,
                height=400,
            ),
            use_container_width=True,
            config={
                "displayModeBar": False
            },
        )


    st.divider()


    # ========================================================
    # CAGR METRICS
    # ========================================================

    cagr1, cagr2, cagr3, cagr4 = st.columns(
        4
    )

    with cagr1:

        st.metric(
            "Revenue CAGR 3Y",
            format_percent(
                calculate_cagr(
                    revenue,
                    3,
                )
            ),
        )

    with cagr2:

        st.metric(
            "Revenue CAGR 5Y",
            format_percent(
                calculate_cagr(
                    revenue,
                    5,
                )
            ),
        )

    with cagr3:

        st.metric(
            "Net Income CAGR",
            format_percent(
                calculate_cagr(
                    net_income,
                    5,
                )
            ),
        )

    with cagr4:

        st.metric(
            "FCF CAGR",
            format_percent(
                calculate_cagr(
                    fcf,
                    5,
                )
            ),
        )


    st.divider()


    if financial_data:

        display_financials = (
            financial_df
            .copy()
            .round(2)
        )

        st.caption(
            "USD billions"
        )

        st.dataframe(
            display_financials,
            use_container_width=True,
        )


# ============================================================
# PROFITABILITY
# ============================================================

with profitability_tab:

    st.subheader(
        "Profitability"
    )

    st.caption(
        "Historical margins and capital efficiency"
    )

    p1, p2 = st.columns(
        [1.7, 1],
        gap="small",
    )

    with p1:

        with st.container(
            border=True,
        ):

            st.subheader(
                "Margins"
            )

            if (
                margin_history is not None
                and not margin_history.empty
            ):

                st.plotly_chart(
                    create_multi_line_chart(
                        margin_history,
                        percentage=True,
                        height=390,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )

    with p2:

        with st.container(
            border=True,
        ):

            st.subheader(
                "Capital Efficiency"
            )

            capital_df = pd.DataFrame()

            if roe is not None:

                capital_df[
                    "ROE"
                ] = roe

            if roic is not None:

                capital_df[
                    "ROIC"
                ] = roic

            if not capital_df.empty:

                st.plotly_chart(
                    create_multi_line_chart(
                        capital_df,
                        percentage=True,
                        height=390,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )


# ============================================================
# VALUATION
# ============================================================

with valuation_tab:

    st.subheader(
        "Valuation"
    )

    st.caption(
        "Current multiples relative to the company's own history"
    )

    valuation_period = st.selectbox(
        "Historical period",
        [
            "3 Years",
            "5 Years",
        ],
        index=1,
        key="full_valuation_period",
    )

    years = (
        3
        if valuation_period
        == "3 Years"
        else 5
    )

    current_valuation = {
        "P/E": clean_number(
            info.get(
                "trailingPE"
            )
        ),
        "P/B": clean_number(
            info.get(
                "priceToBook"
            )
        ),
        "EV/Revenue": clean_number(
            info.get(
                "enterpriseToRevenue"
            )
        ),
        "EV/EBITDA": clean_number(
            info.get(
                "enterpriseToEbitda"
            )
        ),
    }

    current_fcf = get_ttm_value(
        get_fcf_series(
            ttm_cashflow
        ),
        get_fcf_series(
            quarterly_cashflow
        ),
    )

    if (
        market_cap is not None
        and current_fcf is not None
        and current_fcf > 0
    ):

        current_valuation[
            "P/FCF"
        ] = (
            market_cap
            / current_fcf
        )


    v1, v2 = st.columns(
        [1.4, 1],
        gap="small",
    )


    with v1:

        with st.container(
            border=True,
        ):

            valuation_fig = create_valuation_chart(
                current_valuation,
                valuation_history,
                years,
            )

            if valuation_fig is not None:

                st.plotly_chart(
                    valuation_fig,
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )

            else:

                st.info(
                    "Valuation data temporarily unavailable from Yahoo Finance."
                )


    with v2:

        with st.container(
            border=True,
        ):

            st.subheader(
                "Valuation Summary"
            )

            valuation_table = (
                valuation_summary(
                    valuation_history,
                    current_valuation,
                    years,
                )
            )

            if not valuation_table.empty:

                display = (
                    valuation_table
                    .copy()
                )

                display[
                    "Current"
                ] = display[
                    "Current"
                ].map(
                    lambda x:
                    f"{x:.2f}x"
                )

                display[
                    "Average"
                ] = display[
                    "Average"
                ].map(
                    lambda x:
                    f"{x:.2f}x"
                )

                display[
                    "Median"
                ] = display[
                    "Median"
                ].map(
                    lambda x:
                    f"{x:.2f}x"
                )

                display[
                    "Premium / Discount"
                ] = display[
                    "Premium / Discount"
                ].map(
                    lambda x:
                    f"{x:+.1f}%"
                )

                display[
                    "Historical Percentile"
                ] = display[
                    "Historical Percentile"
                ].map(
                    lambda x:
                    f"{x:.0f}%"
                )

                st.dataframe(
                    display,
                    use_container_width=True,
                )

            else:

                st.info(
                    "Not enough historical valuation data."
                )


# ============================================================
# BALANCE SHEET
# ============================================================

with balance_tab:

    st.subheader(
        "Balance Sheet"
    )

    st.caption(
        "Leverage, liquidity and capital structure"
    )

    b1, b2, b3 = st.columns(
        3,
        gap="small",
    )

    # --------------------------------------------------------
    # Debt / Equity
    # --------------------------------------------------------

    with b1:

        with st.container(
            border=True,
        ):

            st.subheader(
                "Debt / Equity"
            )

            if debt_equity is not None:

                st.plotly_chart(
                    create_line_chart(
                        debt_equity,
                        ratio=True,
                        height=MEDIUM_CHART_HEIGHT,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )

    # --------------------------------------------------------
    # Net Debt / EBITDA
    # --------------------------------------------------------

    with b2:

        with st.container(
            border=True,
        ):

            st.subheader(
                "Net Debt / EBITDA"
            )

            if net_debt_ebitda is not None:

                st.plotly_chart(
                    create_line_chart(
                        net_debt_ebitda,
                        ratio=True,
                        height=MEDIUM_CHART_HEIGHT,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )

    # --------------------------------------------------------
    # Shares
    # --------------------------------------------------------

    with b3:

        with st.container(
            border=True,
        ):

            st.subheader(
                "Dilution / Buybacks"
            )

            if dilution is not None:

                st.plotly_chart(
                    create_bar_chart(
                        dilution,
                        percentage=True,
                        height=MEDIUM_CHART_HEIGHT,
                    ),
                    use_container_width=True,
                    config={
                        "displayModeBar": False
                    },
                )


    st.divider()


    # ========================================================
    # CURRENT RATIOS
    # ========================================================

    latest_debt = None
    latest_cash = None
    current_ratio = None
    interest_coverage = None

    q_debt = get_debt_series(
        quarterly_balance
    )

    q_cash = get_cash_series(
        quarterly_balance
    )

    q_assets = get_current_assets_series(
        quarterly_balance
    )

    q_liabilities = (
        get_current_liabilities_series(
            quarterly_balance
        )
    )

    q_ebit = get_ebit_series(
        quarterly_income
    )

    q_interest = (
        get_interest_expense_series(
            quarterly_income
        )
    )

    if q_debt is not None:

        latest_debt = float(
            q_debt.iloc[-1]
        )

    if q_cash is not None:

        latest_cash = float(
            q_cash.iloc[-1]
        )

    if (
        q_assets is not None
        and q_liabilities is not None
        and q_liabilities.iloc[-1] != 0
    ):

        current_ratio = (
            q_assets.iloc[-1]
            / q_liabilities.iloc[-1]
        )

    if (
        q_ebit is not None
        and q_interest is not None
    ):

        interest_ttm = (
            q_interest
            .tail(4)
            .abs()
            .sum()
        )

        ebit_ttm = (
            q_ebit
            .tail(4)
            .sum()
        )

        if interest_ttm != 0:

            interest_coverage = (
                ebit_ttm
                / interest_ttm
            )


    bm1, bm2, bm3, bm4 = st.columns(
        4
    )

    with bm1:

        st.metric(
            "Total Debt",
            format_large_number(
                latest_debt
            ),
        )

    with bm2:

        st.metric(
            "Cash",
            format_large_number(
                latest_cash
            ),
        )

    with bm3:

        st.metric(
            "Current Ratio",
            (
                f"{current_ratio:.2f}x"
                if current_ratio
                is not None
                else "N/A"
            ),
        )

    with bm4:

        st.metric(
            "Interest Coverage",
            (
                f"{interest_coverage:.2f}x"
                if interest_coverage
                is not None
                else "N/A"
            ),
        )


# ============================================================
# ESTIMATES
# ============================================================

with estimates_tab:

    st.subheader(
        "Analyst Estimates"
    )

    st.caption(
        "Consensus information available through Yahoo Finance"
    )

    price_targets = company_data[
        "price_targets"
    ]

    if isinstance(
        price_targets,
        dict,
    ):

        target_current = clean_number(
            price_targets.get(
                "current"
            )
        )

        target_mean = clean_number(
            price_targets.get(
                "mean"
            )
        )

        target_median = clean_number(
            price_targets.get(
                "median"
            )
        )

        target_high = clean_number(
            price_targets.get(
                "high"
            )
        )

        target_low = clean_number(
            price_targets.get(
                "low"
            )
        )

        upside = None

        if (
            current_price is not None
            and target_mean is not None
            and current_price != 0
        ):

            upside = (
                target_mean
                / current_price
                - 1
            ) * 100


        e1, e2, e3, e4, e5 = st.columns(
            5
        )

        with e1:

            st.metric(
                "Current",
                (
                    f"${target_current:.2f}"
                    if target_current
                    is not None
                    else "N/A"
                ),
            )

        with e2:

            st.metric(
                "Mean Target",
                (
                    f"${target_mean:.2f}"
                    if target_mean
                    is not None
                    else "N/A"
                ),
                (
                    f"{upside:+.1f}%"
                    if upside
                    is not None
                    else None
                ),
            )

        with e3:

            st.metric(
                "Median Target",
                (
                    f"${target_median:.2f}"
                    if target_median
                    is not None
                    else "N/A"
                ),
            )

        with e4:

            st.metric(
                "High Target",
                (
                    f"${target_high:.2f}"
                    if target_high
                    is not None
                    else "N/A"
                ),
            )

        with e5:

            st.metric(
                "Low Target",
                (
                    f"${target_low:.2f}"
                    if target_low
                    is not None
                    else "N/A"
                ),
            )


    st.divider()


    est1, est2 = st.columns(
        2,
        gap="small",
    )


    with est1:

        st.subheader(
            "EPS Estimates"
        )

        earnings_estimate = (
            company_data[
                "earnings_estimate"
            ]
        )

        if (
            earnings_estimate is not None
            and not earnings_estimate.empty
        ):

            st.dataframe(
                earnings_estimate,
                use_container_width=True,
            )

        else:

            st.info(
                "EPS consensus unavailable."
            )


    with est2:

        st.subheader(
            "Revenue Estimates"
        )

        revenue_estimate = (
            company_data[
                "revenue_estimate"
            ]
        )

        if (
            revenue_estimate is not None
            and not revenue_estimate.empty
        ):

            st.dataframe(
                revenue_estimate,
                use_container_width=True,
            )

        else:

            st.info(
                "Revenue consensus unavailable."
            )


    st.divider()


    rec1, rec2 = st.columns(
        2
    )


    with rec1:

        st.subheader(
            "Recommendations"
        )

        recommendations = (
            company_data[
                "recommendations"
            ]
        )

        if (
            recommendations is not None
            and not recommendations.empty
        ):

            st.dataframe(
                recommendations,
                use_container_width=True,
            )

        else:

            st.info(
                "Recommendations unavailable."
            )


    with rec2:

        st.subheader(
            "Growth Estimates"
        )

        growth_estimates = (
            company_data[
                "growth_estimates"
            ]
        )

        if (
            growth_estimates is not None
            and not growth_estimates.empty
        ):

            st.dataframe(
                growth_estimates,
                use_container_width=True,
            )

        else:

            st.info(
                "Growth estimates unavailable."
            )


# ============================================================
# STOCK & RISK
# ============================================================

with risk_tab:

    st.subheader(
        "Stock Performance & Risk"
    )

    benchmark = load_benchmark()

    risk_metrics = (
        calculate_stock_metrics(
            history,
            benchmark,
        )
    )

    returns = {
        "1M": period_return(
            history,
            days=30,
        ),
        "3M": period_return(
            history,
            days=90,
        ),
        "6M": period_return(
            history,
            days=180,
        ),
        "1Y": period_return(
            history,
            years=1,
        ),
        "3Y": period_return(
            history,
            years=3,
        ),
        "5Y": period_return(
            history,
            years=5,
        ),
    }


    r1, r2, r3, r4, r5, r6 = st.columns(
        6
    )

    for column, (
        label,
        value,
    ) in zip(
        [
            r1,
            r2,
            r3,
            r4,
            r5,
            r6,
        ],
        returns.items(),
    ):

        with column:

            st.metric(
                label,
                (
                    f"{value:+.2f}%"
                    if value
                    is not None
                    else "N/A"
                ),
            )


    st.divider()


    rm1, rm2, rm3 = st.columns(
        3
    )

    with rm1:

        st.metric(
            "1Y Volatility",
            (
                f"{risk_metrics.get('Volatility'):.2f}%"
                if risk_metrics.get(
                    "Volatility"
                ) is not None
                else "N/A"
            ),
        )

    with rm2:

        st.metric(
            "5Y Max Drawdown",
            (
                f"{risk_metrics.get('Max Drawdown'):.2f}%"
                if risk_metrics.get(
                    "Max Drawdown"
                ) is not None
                else "N/A"
            ),
        )

    with rm3:

        st.metric(
            "Beta vs S&P 500",
            (
                f"{risk_metrics.get('Beta'):.2f}"
                if risk_metrics.get(
                    "Beta"
                ) is not None
                else "N/A"
            ),
        )


    st.divider()


    if (
        history is not None
        and not history.empty
        and benchmark is not None
        and not benchmark.empty
    ):

        stock_price = (
            history["Close"]
            .dropna()
            .copy()
        )

        if getattr(
            stock_price.index,
            "tz",
            None,
        ) is not None:

            stock_price.index = (
                stock_price.index
                .tz_localize(None)
            )

        benchmark_price = (
            benchmark.copy()
        )

        combined = pd.concat(
            [
                stock_price.rename(
                    symbol
                ),
                benchmark_price.rename(
                    "S&P 500"
                ),
            ],
            axis=1,
        ).dropna()

        cutoff = (
            pd.Timestamp.now()
            - pd.DateOffset(
                years=5
            )
        )

        combined = combined[
            combined.index
            >= cutoff
        ]

        if len(combined) >= 2:

            normalized = (
                combined
                / combined.iloc[0]
                - 1
            ) * 100

            fig = go.Figure()

            for column in normalized.columns:

                fig.add_trace(
                    go.Scatter(
                        x=normalized.index,
                        y=normalized[
                            column
                        ],
                        mode="lines",
                        name=column,
                    )
                )

            fig.update_layout(
                height=420,
                template="plotly_dark",
                paper_bgcolor=(
                    "rgba(0,0,0,0)"
                ),
                plot_bgcolor=(
                    "rgba(0,0,0,0)"
                ),
                margin=dict(
                    l=10,
                    r=10,
                    t=30,
                    b=10,
                ),
                legend=dict(
                    orientation="h",
                    y=1.03,
                ),
                yaxis=dict(
                    ticksuffix="%",
                    gridcolor=(
                        "rgba(128,128,128,0.13)"
                    ),
                ),
                xaxis=dict(
                    showgrid=False,
                ),
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "displayModeBar": False
                },
            )


# ============================================================
# COMPANY INFORMATION
# ============================================================

st.divider()


with st.expander(
    "ℹ️ Company Information"
):

    description = info.get(
        "longBusinessSummary"
    )

    if description:

        st.write(
            description
        )

    i1, i2, i3, i4 = st.columns(
        4
    )

    with i1:

        st.write(
            "Sector:",
            info.get(
                "sector",
                "N/A",
            ),
        )

        st.write(
            "Industry:",
            info.get(
                "industry",
                "N/A",
            ),
        )

    with i2:

        st.write(
            "Country:",
            info.get(
                "country",
                "N/A",
            ),
        )

        st.write(
            "Employees:",
            info.get(
                "fullTimeEmployees",
                "N/A",
            ),
        )

    with i3:

        high = clean_number(
            info.get(
                "fiftyTwoWeekHigh"
            )
        )

        low = clean_number(
            info.get(
                "fiftyTwoWeekLow"
            )
        )

        st.write(
            "52W High:",
            (
                f"${high:,.2f}"
                if high
                is not None
                else "N/A"
            ),
        )

        st.write(
            "52W Low:",
            (
                f"${low:,.2f}"
                if low
                is not None
                else "N/A"
            ),
        )

    with i4:

        dividend = clean_number(
            info.get(
                "dividendYield"
            )
        )

        st.write(
            "Dividend Yield:",
            (
                f"{dividend * 100:.2f}%"
                if dividend
                is not None
                else "N/A"
            ),
        )

        st.write(
            "Website:",
            info.get(
                "website",
                "N/A",
            ),
        )


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Source: Yahoo Finance via yfinance · "
    "TTM = Trailing Twelve Months · "
    "Historical valuation multiples are reconstructed from available Yahoo Finance "
    "annual financial statements and fiscal-date market prices · "
    "Consensus and analyst data depend on Yahoo Finance availability."
)