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
    ])
    
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


@tool
def get_historical_stock_data(company_or_ticker: str, period: str = "1mo", date: str = None) -> str:
    """
    Fetch historical stock price data for a company or ticker symbol.
    Use this tool when user asks about past/historical stock prices, price history,
    or stock values at a specific date or time period.
    
    Args:
        company_or_ticker: Company name OR stock ticker symbol. Examples:
            - "Sony", "AAPL", "Volvo", "ERIC-B.ST", "6758.T"
        period: Time period for historical data. Options:
            - "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
            - Default is "1mo" (1 month)
        date: Specific date to get stock price (format: "YYYY-MM-DD" or "YYYY-MM" or "December 2024")
            - If provided, returns the stock price around that date
    
    Returns:
        Historical stock prices with open, high, low, close, volume.
        Foreign stocks show both native currency and SEK equivalent.
    """
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        
        # Resolve company name to ticker
        ticker = resolve_ticker(company_or_ticker)
        stock = yf.Ticker(ticker)
        
        # Get stock info for currency
        info = stock.info
        currency = info.get("currency", "SEK")
        stock_name = info.get("longName", info.get("shortName", ticker))
        
        # Handle specific date request
        if date:
            # Parse various date formats
            parsed_date = None
            
            # Try different date formats
            date_formats = [
                "%Y-%m-%d",  # 2024-12-15
                "%Y-%m",     # 2024-12
                "%B %Y",     # December 2024
                "%b %Y",     # Dec 2024
                "%Y/%m/%d",  # 2024/12/15
                "%d-%m-%Y",  # 15-12-2024
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date, fmt)
                    break
                except ValueError:
                    continue
            
            # Handle month-year format (get the whole month)
            if parsed_date:
                if len(date) <= 8 or "202" in date and len(date.split("-")) == 2:
                    # It's a month-year format, get the whole month
                    start_date = parsed_date.replace(day=1)
                    # Get end of month
                    if parsed_date.month == 12:
                        end_date = parsed_date.replace(year=parsed_date.year + 1, month=1, day=1)
                    else:
                        end_date = parsed_date.replace(month=parsed_date.month + 1, day=1)
                else:
                    # Specific date - get a week around it
                    start_date = parsed_date - timedelta(days=3)
                    end_date = parsed_date + timedelta(days=4)
                
                hist = stock.history(start=start_date.strftime("%Y-%m-%d"), 
                                    end=end_date.strftime("%Y-%m-%d"))
            else:
                # Couldn't parse date, use period instead
                hist = stock.history(period=period)
        else:
            # Use period
            hist = stock.history(period=period)
        
        if hist.empty:
            return f"No historical data found for {ticker}"
        
        # Get exchange rate for foreign currencies
        is_foreign = currency != "SEK"
        exchange_rate = None
        if is_foreign:
            exchange_rate = get_exchange_rate_to_sek(currency)
        
        currency_symbol = {
            "SEK": "kr ", "NOK": "kr ", "DKK": "kr ",
            "EUR": "€", "USD": "$", "JPY": "¥", "GBP": "£",
            "CHF": "CHF ", "CNY": "¥", "HKD": "HK$", "KRW": "₩",
        }.get(currency, currency + " ")
        
        def format_price(price):
            if is_foreign and exchange_rate:
                sek_price = price * exchange_rate
                return f"{currency_symbol}{price:,.2f} (~{sek_price:,.2f} kr SEK)"
            return f"{currency_symbol}{price:,.2f}"
        
        # Build response
        lines = [
            f"**Historical Stock Data: {stock_name}** ({ticker})",
            f"Currency: {currency}" + (f" (1 {currency} ≈ {exchange_rate:.4f} SEK)" if is_foreign and exchange_rate else ""),
            ""
        ]
        
        # Show summary stats
        lines.extend([
            "**Period Summary:**",
            f"  • Start: {hist.index[0].strftime('%Y-%m-%d')} - Close: {format_price(hist['Close'].iloc[0])}",
            f"  • End: {hist.index[-1].strftime('%Y-%m-%d')} - Close: {format_price(hist['Close'].iloc[-1])}",
            f"  • Period High: {format_price(hist['High'].max())}",
            f"  • Period Low: {format_price(hist['Low'].min())}",
            f"  • Avg Volume: {hist['Volume'].mean():,.0f}",
            ""
        ])
        
        # Calculate change
        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        change = end_price - start_price
        change_pct = (change / start_price) * 100
        change_symbol = "📈" if change >= 0 else "📉"
        
        lines.append(f"**Change:** {change_symbol} {format_price(abs(change))} ({change_pct:+.2f}%)")
        lines.append("")
        
        # Show recent data points (last 10 or all if less)
        num_rows = min(10, len(hist))
        lines.append(f"**Recent Prices (last {num_rows} trading days):**")
        
        for idx in hist.tail(num_rows).itertuples():
            date_str = idx.Index.strftime('%Y-%m-%d')
            lines.append(f"  • {date_str}: {format_price(idx.Close)} (Vol: {idx.Volume:,.0f})")
        
        return "\n".join(lines)
        
    except ImportError:
        return "yfinance not installed. Run: pip install yfinance"
    except Exception as e:
        return f"Error fetching historical data: {str(e)}"


def create_stock_tool():
    """Create the stock data tools for agent use."""
    return [get_stock_data, get_historical_stock_data]


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
    
    # Major international companies (prevent .ST suffix)
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    
    # Japanese companies (Tokyo Stock Exchange - .T suffix)
    "sony": "6758.T",
    "toyota": "7203.T",
    "honda": "7267.T",
    "nintendo": "7974.T",
    "softbank": "9984.T",
    "mitsubishi": "8058.T",
    "panasonic": "6752.T",
    "hitachi": "6501.T",
    "canon": "7751.T",
    "nikon": "7731.T",
    "suzuki": "7269.T",
    "mazda": "7261.T",
    "nissan": "7201.T",
    "subaru": "7270.T",
    "yamaha": "7951.T",
    "fujitsu": "6702.T",
    "sharp": "6753.T",
    "toshiba": "6502.T",
    "sony group": "6758.T",
    
    # Other major international
    "samsung": "005930.KS",  # Korea
    "alibaba": "BABA",
    "tencent": "0700.HK",
    "hsbc": "HSBA.L",
    "shell": "SHEL.L",
    "bp": "BP.L",
    "nestle": "NESN.SW",
    "novartis": "NOVN.SW",
    "roche": "ROG.SW",
    "lvmh": "MC.PA",
    "asml": "ASML.AS",
    "volkswagen": "VOW3.DE",
    "bmw": "BMW.DE",
    "mercedes": "MBG.DE",
    "siemens": "SIE.DE",
    "sap": "SAP.DE",
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
