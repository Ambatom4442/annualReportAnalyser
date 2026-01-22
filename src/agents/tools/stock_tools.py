"""
Stock data tools for fetching real-time market data.
Focused on Swedish/Nordic markets (OMX Stockholm) with SEK currency.
"""
from typing import Optional, List
from langchain.tools import tool


def get_exchange_rate_to_sek(from_currency: str) -> Optional[float]:
    """
    Get exchange rate from a currency to SEK.
    
    Args:
        from_currency: Source currency code (e.g., "USD", "JPY", "EUR")
    
    Returns:
        Exchange rate (1 from_currency = X SEK), or None if unavailable
    """
    if from_currency == "SEK":
        return 1.0
    
    try:
        import yfinance as yf
        
        # yfinance format for currency pairs: XXXSEK=X
        pair = f"{from_currency}SEK=X"
        ticker = yf.Ticker(pair)
        
        # Try to get current price
        hist = ticker.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        
        # Fallback to info
        info = ticker.info
        rate = info.get("regularMarketPrice") or info.get("previousClose")
        if rate:
            return rate
            
    except Exception:
        pass
    
    # Fallback approximate rates (as of 2024 - should be updated periodically)
    fallback_rates = {
        "USD": 10.5,
        "EUR": 11.3,
        "GBP": 13.2,
        "JPY": 0.070,  # 1 JPY ≈ 0.07 SEK
        "NOK": 0.98,
        "DKK": 1.52,
        "CHF": 11.8,
        "CAD": 7.7,
        "AUD": 6.8,
        "CNY": 1.45,
        "HKD": 1.35,
        "KRW": 0.0078,
    }
    return fallback_rates.get(from_currency)


def get_stock_info(ticker: str) -> dict:
    """
    Fetch stock data using yfinance.
    
    Args:
        ticker: Stock ticker symbol (e.g., "VOLV-B.ST" for Volvo, "ERIC-B.ST" for Ericsson)
    
    Returns:
        Dictionary with stock data
    """
    try:
        import yfinance as yf
        
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extract key metrics
        return {
            "ticker": ticker,
            "name": info.get("longName", info.get("shortName", ticker)),
            "price": info.get("currentPrice", info.get("regularMarketPrice")),
            "currency": info.get("currency", "SEK"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "50_day_avg": info.get("fiftyDayAverage"),
            "200_day_avg": info.get("twoHundredDayAverage"),
            "volume": info.get("volume"),
            "avg_volume": info.get("averageVolume"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "exchange": info.get("exchange"),
            "description": info.get("longBusinessSummary", "")[:500]  # Truncate description
        }
    except ImportError:
        return {"error": "yfinance not installed. Run: pip install yfinance"}
    except Exception as e:
        return {"error": str(e)}


def format_stock_data(data: dict) -> str:
    """Format stock data dictionary as readable string with SEK conversion for foreign stocks."""
    if "error" in data:
        return f"Error fetching stock data: {data['error']}"
    
    def format_number(n, prefix="", suffix=""):
        if n is None:
            return "N/A"
        if isinstance(n, float):
            if n >= 1_000_000_000_000:
                return f"{prefix}{n/1_000_000_000_000:.2f}T{suffix}"
            elif n >= 1_000_000_000:
                return f"{prefix}{n/1_000_000_000:.2f}B{suffix}"
            elif n >= 1_000_000:
                return f"{prefix}{n/1_000_000:.2f}M{suffix}"
            else:
                return f"{prefix}{n:,.2f}{suffix}"
        return f"{prefix}{n}{suffix}"
    
    currency = data.get("currency", "SEK")
    is_foreign = currency != "SEK"
    
    # Get exchange rate for foreign currencies
    exchange_rate = None
    if is_foreign:
        exchange_rate = get_exchange_rate_to_sek(currency)
    
    currency_symbol = {
        "SEK": "kr ", 
        "NOK": "kr ", 
        "DKK": "kr ",
        "EUR": "€",
        "USD": "$", 
        "JPY": "¥", 
        "GBP": "£",
        "CHF": "CHF ",
        "CNY": "¥",
        "HKD": "HK$",
        "KRW": "₩",
    }.get(currency, currency + " ")
    
    def format_with_sek(value, prefix=""):
        """Format a value with optional SEK equivalent for foreign stocks."""
        if value is None:
            return "N/A"
        native = f"{prefix}{currency_symbol}{format_number(value)}"
        if is_foreign and exchange_rate:
            sek_value = value * exchange_rate
            sek_formatted = format_number(sek_value)
            return f"{native} (~{sek_formatted} kr SEK)"
        return native
    
    lines = [
        f"**{data.get('name', data['ticker'])}** ({data['ticker']})",
        f"Exchange: {data.get('exchange', 'N/A')} | Sector: {data.get('sector', 'N/A')}",
    ]
    
    # Show exchange rate info for foreign stocks
    if is_foreign and exchange_rate:
        lines.append(f"*Currency: {currency} (1 {currency} ≈ {exchange_rate:.4f} SEK)*")
    
    lines.extend([
        "",
        f"**Current Price:** {format_with_sek(data.get('price'))}",
        f"**Market Cap:** {format_with_sek(data.get('market_cap'))}",
        "",
        "**Valuation:**",
        f"  • P/E Ratio (TTM): {format_number(data.get('pe_ratio'))}",
        f"  • Forward P/E: {format_number(data.get('forward_pe'))}",
        f"  • Dividend Yield: {format_number(data.get('dividend_yield'), suffix='%') if data.get('dividend_yield') else 'N/A'}",
        "",
        "**Price Range (52 Week):**",
        f"  • High: {format_with_sek(data.get('52_week_high'))}",
        f"  • Low: {format_with_sek(data.get('52_week_low'))}",
        "",
        "**Moving Averages:**",
        f"  • 50-Day: {format_with_sek(data.get('50_day_avg'))}",
        f"  • 200-Day: {format_with_sek(data.get('200_day_avg'))}",
        "",
        f"**Volume:** {format_number(data.get('volume'))} (Avg: {format_number(data.get('avg_volume'))})",
    ]
    
    if data.get("description"):
        lines.extend(["", "**About:**", data["description"][:300] + "..."])
    
    return "\n".join(lines)


@tool
def get_stock_data(company_or_ticker: str) -> str:
    """
    Fetch real-time stock market data for a company or ticker symbol.
    Focused on Swedish/Nordic markets (OMX Stockholm) with SEK currency.
    
    Use this tool when user asks about stock prices, market data, or company valuations.
    
    Args:
        company_or_ticker: Company name OR stock ticker symbol. Examples:
            - Swedish companies: "Volvo", "Ericsson", "H&M", "ABB", "Atlas Copco"
            - Swedish tickers: "VOLV-B.ST", "ERIC-B.ST", "HM-B.ST"
            - Nordic tickers: "NOVO-B.CO" (Novo Nordisk), "EQNR.OL" (Equinor)
            - Other markets: "AAPL" (US), "7203.T" (Japan)
    
    Returns:
        Formatted stock data including current price, market cap, P/E ratio, etc.
        All Swedish stocks displayed in SEK (Swedish Krona).
    """
    # Resolve company name to ticker if needed
    ticker = resolve_ticker(company_or_ticker)
    data = get_stock_info(ticker)
    return format_stock_data(data)


def create_stock_tool():
    """Create the stock data tool for agent use."""
    return get_stock_data


# Common ticker mappings for convenience
# Swedish stocks use .ST suffix (Stockholm Stock Exchange)
COMMON_TICKERS = {
    # Swedish companies (OMX Stockholm - Nasdaq Stockholm)
    "volvo": "VOLV-B.ST",
    "ericsson": "ERIC-B.ST",
    "h&m": "HM-B.ST",
    "hm": "HM-B.ST",
    "hennes & mauritz": "HM-B.ST",
    "atlas copco": "ATCO-A.ST",
    "abb": "ABB.ST",
    "sandvik": "SAND.ST",
    "seb": "SEB-A.ST",
    "swedbank": "SWED-A.ST",
    "handelsbanken": "SHB-A.ST",
    "nordea": "NDA-SE.ST",
    "investor": "INVE-B.ST",
    "essity": "ESSITY-B.ST",
    "hexagon": "HEXA-B.ST",
    "assa abloy": "ASSA-B.ST",
    "skf": "SKF-B.ST",
    "telia": "TELIA.ST",
    "electrolux": "ELUX-B.ST",
    "epiroc": "EPI-A.ST",
    "securitas": "SECU-B.ST",
    "svenska cellulosa": "SCA-B.ST",
    "sca": "SCA-B.ST",
    "boliden": "BOL.ST",
    "husqvarna": "HUSQ-B.ST",
    "alfa laval": "ALFA.ST",
    "getinge": "GETI-B.ST",
    "nibe": "NIBE-B.ST",
    "evolution": "EVO.ST",
    "evolution gaming": "EVO.ST",
    "spotify": "SPOT",  # US listed but Swedish company
    "kinnevik": "KINV-B.ST",
    "latour": "LATO-B.ST",
    "lundbergföretagen": "LUND-B.ST",
    "industrivärden": "INDU-C.ST",
    "trelleborg": "TREL-B.ST",
    "autoliv": "ALIV-SDB.ST",
    "saab": "SAAB-B.ST",
    "skanska": "SKA-B.ST",
    "ncc": "NCC-B.ST",
    "peab": "PEAB-B.ST",
    "castellum": "CAST.ST",
    "fabege": "FABG.ST",
    "fastighets balder": "BALD-B.ST",
    "balder": "BALD-B.ST",
    "addtech": "ADDT-B.ST",
    "indutrade": "INDT.ST",
    "lifco": "LIFCO-B.ST",
    "thule": "THULE.ST",
    "dometic": "DOM.ST",
    "vitrolife": "VITR.ST",
    "swedish match": "SWMA.ST",
    "avanza": "AZA.ST",
    "collector": "COLL.ST",
    
    # Other Nordic companies (Denmark, Norway, Finland)
    "novo nordisk": "NOVO-B.CO",
    "maersk": "MAERSK-B.CO",
    "carlsberg": "CARL-B.CO",
    "vestas": "VWS.CO",
    "orsted": "ORSTED.CO",
    "equinor": "EQNR.OL",
    "telenor": "TEL.OL",
    "dnb": "DNB.OL",
    "yara": "YAR.OL",
    "nokia": "NOKIA.HE",
    "kone": "KNEBV.HE",
    "fortum": "FORTUM.HE",
    
    # Major international for reference
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "nvidia": "NVDA",
}


def resolve_ticker(name_or_ticker: str) -> str:
    """
    Resolve a company name to its ticker symbol.
    Prioritizes Swedish/Nordic stocks.
    
    Args:
        name_or_ticker: Company name or ticker symbol
    
    Returns:
        Ticker symbol (Swedish stocks with .ST suffix)
    """
    # Check if it's already a ticker (has suffix or is all uppercase)
    if "." in name_or_ticker or name_or_ticker.isupper():
        return name_or_ticker
    
    # Try to find in common tickers
    name_lower = name_or_ticker.lower().strip()
    if name_lower in COMMON_TICKERS:
        return COMMON_TICKERS[name_lower]
    
    # Try partial match
    for name, ticker in COMMON_TICKERS.items():
        if name_lower in name or name in name_lower:
            return ticker
    
    # Default: assume Swedish stock, try with .ST suffix
    # This helps with Swedish company names not in our list
    ticker_guess = name_or_ticker.upper().replace(" ", "-")
    return f"{ticker_guess}.ST"
