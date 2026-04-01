import click
import re
import requests
from rich.console import Console
from datetime import datetime
from trade4u_cli.nlp import parse_command
from trade4u_cli.local_llm import ask_ai, is_ai_available, llm

console = Console()

AI_STATUS = " (with AI 🤖)" if is_ai_available() else ""

GREETING = f"""🤖 Hi! I'm Trade4U, your market assistant. Ask me anything about stocks, markets, or your portfolio{AI_STATUS}!

I can help with:
• Stock prices & quotes
• Market indices (S&P 500, NASDAQ, Dow)
• Your portfolio & P&L
• Price alerts
• Market news
• Sector performance
• Crypto prices
• AI-powered analysis (when available)

Just ask naturally!"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

MARKET_INDICES = {
    "^GSPC": ("S&P 500", "SPX"),
    "^DJI": ("Dow Jones", "DJI"),
    "^IXIC": ("NASDAQ", "IXIC"),
    "^RUT": ("Russell 2000", "RUT"),
}

CRYPTO_SYMBOLS = {
    "BTC": "BTC-USD",
    "BITCOIN": "BTC-USD",
    "ETH": "ETH-USD",
    "ETHEREUM": "ETH-USD",
}

STOCK_SYMBOLS = {
    "AAPL": "Apple", "GOOGL": "Google", "GOOG": "Google", "MSFT": "Microsoft",
    "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla", "NVDA": "NVIDIA",
    "AMD": "AMD", "NFLX": "Netflix", "DIS": "Disney", "PYPL": "PayPal",
    "INTC": "Intel", "IBM": "IBM", "ORCL": "Oracle", "CRM": "Salesforce",
    "ADBE": "Adobe", "UBER": "Uber", "LYFT": "Lyft", "SPOT": "Spotify",
    "SQ": "Square", "SHOP": "Shopify", "COIN": "Coinbase", "JPM": "JPMorgan",
    "BAC": "Bank of America", "WMT": "Walmart", "TGT": "Target", "COST": "Costco",
    "V": "Visa", "MA": "Mastercard", "JNJ": "Johnson & Johnson", "UNH": "UnitedHealth",
    "XOM": "Exxon", "CVX": "Chevron", "PFE": "Pfizer", "ABBV": "AbbVie",
    "KO": "Coca-Cola", "PEP": "Pepsi", "MCD": "McDonald's", "NKE": "Nike",
}

COMPANY_NAMES = {
    "APPLE": "AAPL", "TESLA": "TSLA", "GOOGLE": "GOOGL", "ALPHABET": "GOOGL",
    "AMAZON": "AMZN", "MICROSOFT": "MSFT", "META": "META", "FACEBOOK": "META",
    "NVIDIA": "NVDA", "NETFLIX": "NFLX", "INTEL": "INTC", "DISNEY": "DIS",
    "ADOBE": "ADBE", "PAYPAL": "PYPL", "SALESFORCE": "CRM", "ORACLE": "ORCL",
    "WALMART": "WMT", "NIKE": "NKE", "COKE": "KO", "MCDONALD": "MCD",
}

STOP_WORDS = {"WHAT", "HOW", "WHEN", "WHERE", "WHY", "WHO", "THE", "THIS", 
              "THAT", "FOR", "FROM", "WITH", "ABOUT", "WHATS", "HERE", "THERE",
              "WHICH", "BEEN", "BEING", "HAVE", "HAS", "HAD", "WILL", "WOULD",
              "COULD", "SHOULD", "THEIR", "THESE", "THOSE", "THEN", "JUST", "LIKE",
              "MORE", "SOME", "SUCH", "INTO", "OVER", "AFTER", "ABOVE", "BELOW",
              "UNDER", "SINCE", "AGAIN", "ONCE", "EACH", "BOTH", "FEW", "MANY",
              "MUCH", "OTHER", "SAME", "ONLY", "THAN", "ALSO", "VERY", "NOW",
              "DOES", "DID", "CAN", "MAY", "MUST", "SHALL", "TELL", "ME",
              "MA", "PA", "SO", "DO", "NO", "IF", "IS", "IT", "IN", "ON", "AT",
              "AN", "AS", "WE", "US", "BE", "BY", "TO", "MY", "GO", "UP", "AM"}


DEFAULT_SETTINGS = {
    "exchange": "NSE",
    "stock_list": "default",
    "timezone": "Asia/Kolkata",
    "currency": "INR",
    "display": "compact",
    "alerts_enabled": True,
}

STOCK_LISTS = {
    "default": {
        "NSE": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ADANIENT", "SBIN", "BHARTIARTL", "ICICIBANK"],
        "NYSE": ["NVDA", "TSLA", "AMD", "META", "AAPL", "AMZN", "MSFT", "GOOGL"],
    },
    "nifty50": {
        "NSE": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", "KOTAKBANK", "AXISBANK", "LT"],
        "NYSE": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JPM", "V"],
    },
    "tech": {
        "NSE": ["INFY", "TCS", "WIPRO", "HCLTECH", "TECHM"],
        "NYSE": ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "IBM", "MSFT", "GOOGL", "META", "CRM"],
    },
    "finance": {
        "NSE": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "BAJFINANCE"],
        "NYSE": ["JPM", "BAC", "WFC", "GS", "C", "MS", "AXP", "BLK", "COF", "USB"],
    },
    "midcap": {
        "NSE": ["ADANIENT", "DELIVERY", "CAMS", "CDSL", "POLYCAB", "GLAXO", "BAJAJFINSV"],
        "NYSE": ["SNAP", "ROKU", "ZM", "DOCU", "TWLO", "NET", "DDOG", "CRWD", "SNOW", "PLTR"],
    },
}


def load_settings():
    import json
    from pathlib import Path
    path = Path.home() / ".trade4u" / "settings.json"
    if path.exists():
        with open(path) as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    import json
    from pathlib import Path
    Path(Path.home() / ".trade4u").mkdir(exist_ok=True)
    path = Path.home() / ".trade4u" / "settings.json"
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)


def load_portfolio():
    import json
    from pathlib import Path
    path = Path.home() / ".trade4u" / "portfolio.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"holdings": [], "cash": 0}

def save_portfolio(portfolio):
    import json
    from pathlib import Path
    Path(Path.home() / ".trade4u").mkdir(exist_ok=True)
    path = Path.home() / ".trade4u" / "portfolio.json"
    with open(path, "w") as f:
        json.dump(portfolio, f, indent=2)

def load_alerts():
    import json
    from pathlib import Path
    path = Path.home() / ".trade4u" / "alerts.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []

def save_alerts(alerts):
    import json
    from pathlib import Path
    Path(Path.home() / ".trade4u").mkdir(exist_ok=True)
    path = Path.home() / ".trade4u" / "alerts.json"
    with open(path, "w") as f:
        json.dump(alerts, f, indent=2)

def get_quote(symbol):
    settings = load_settings()
    exchange = settings.get("exchange", "NSE")
    
    if exchange == "NSE" and not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"
    
    try:
        response = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "1d"},
            headers=HEADERS,
            timeout=10
        )
        data = response.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = meta["regularMarketPrice"]
        prev = meta.get("previousClose") or meta.get("chartPreviousClose") or price
        change = price - prev
        change_pct = (change / prev) * 100 if prev else 0
        return {
            "symbol": symbol.upper(),
            "name": meta.get("shortName") or meta.get("symbol", symbol),
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "prev_close": prev,
            "high_52w": meta.get("fiftyTwoWeekHigh"),
            "low_52w": meta.get("fiftyTwoWeekLow"),
            "market_cap": meta.get("marketCap"),
        }
    except:
        return None

def get_multiple_quotes(symbols):
    results = {}
    for sym in symbols:
        q = get_quote(sym)
        if q:
            results[sym] = q
    return results

def extract_symbol(text):
    text_clean = text.replace("'", " ").upper()
    
    for name, sym in COMPANY_NAMES.items():
        if name in text_clean:
            return sym
    
    for sym in list(STOCK_SYMBOLS.keys()) + list(CRYPTO_SYMBOLS.keys()):
        if sym in text_clean:
            return CRYPTO_SYMBOLS.get(sym, sym)
    
    for index_sym, (name, short) in MARKET_INDICES.items():
        if short in text_clean or name.upper().replace(" ", "") in text_clean:
            return index_sym
    
    words = text_clean.split()
    for word in words:
        clean = re.sub(r'[^A-Z]', '', word)
        if clean in STOCK_SYMBOLS:
            return clean
        if clean in CRYPTO_SYMBOLS:
            return CRYPTO_SYMBOLS[clean]
        if clean and 2 <= len(clean) <= 5 and clean not in STOP_WORDS and clean.isalpha():
            if clean in STOCK_SYMBOLS:
                return clean
    
    match = re.search(r'\b([A-Z]{2,5})\b', text_clean)
    if match:
        sym = match.group(1)
        if sym in STOCK_SYMBOLS:
            return sym
    
    return None

def extract_numbers(text):
    return [float(n) for n in re.findall(r'\d+\.?\d*', text)]

def get_news():
    try:
        response = requests.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={"q": "stock market", "newsType": "authoritative"},
            headers=HEADERS,
            timeout=10
        )
        articles = response.json().get("news", [])[:5]
        return [(a.get("title", ""), a.get("provider", "")) for a in articles if a.get("title")]
    except:
        return []


class Trade4UChat:
    def __init__(self):
        self.portfolio = load_portfolio()
        self.alerts = load_alerts()
        self.settings = load_settings()
    
    def respond(self, user_input):
        parsed = parse_command(user_input)
        intent = parsed["intent"]
        entities = parsed["entities"]
        
        exchange = self.settings.get("exchange", "NSE")
        stock_list = self.settings.get("stock_list", "default")
        
        if intent == "GREETING":
            return "Hey! 👋 What can I help you with today?"
        
        if intent == "GOODBYE":
            return "Bye! Come back when you need market info. 📈"
        
        if intent == "THANKS":
            return "You're welcome! 😊"
        
        if intent == "HELP":
            return """I can help you with:

• Stock prices: "What's Apple at?" or "AAPL"
• Market indices: "How's the S&P 500?"
• Crypto: "What's Bitcoin?"
• Portfolio: "Show my portfolio"
• Alerts: "Alert me when TSLA hits $500"
• News: "Any market news?"
• Charts: "Chart for NVDA"
• AI analysis: "What do you think about NVDA?"

Just ask naturally!"""
        
        if intent == "PRICE":
            symbol = entities.get("symbol")
            if symbol:
                return self.handle_price(symbol)
            return "Which stock?"
        
        if intent == "PORTFOLIO":
            return self.handle_portfolio()
        
        if intent == "PORTFOLIO_VALUE":
            return self.handle_portfolio_value()
        
        if intent == "ADD_HOLDING":
            symbol = entities.get("symbol")
            shares = entities.get("shares")
            price = entities.get("price")
            if symbol and shares and price:
                return self.handle_add_holding_simple(symbol, int(shares), float(price))
            if symbol:
                return f"How many shares of {symbol} did you buy?"
            return "Which stock did you buy? Try: 'I bought 10 AAPL at $200'"
        
        if intent == "REMOVE_HOLDING":
            symbol = entities.get("symbol")
            return self.handle_remove_holding(symbol)
        
        if intent == "ALERT":
            symbol = entities.get("symbol")
            price = entities.get("target_price")
            direction = entities.get("direction", "above")
            if symbol and price:
                return self.handle_alert_simple(symbol, float(price), direction)
            return "Which stock and price?"
        
        if intent == "NEWS":
            return self.handle_news()
        
        if intent == "RECOMMEND":
            text = user_input.lower()
            if "available" in text or "show" in text or "list" in text or "what stocks" in text:
                return self.handle_available_stocks()
            return self.handle_recommend(user_input)
        
        if intent == "CHART":
            symbol = entities.get("symbol")
            if symbol:
                return self.handle_chart(symbol)
            return "Which stock?"
        
        if intent == "MARKET_STATUS":
            now = datetime.now()
            hour = now.hour
            day = now.weekday()
            is_open = 9 <= hour < 16 and day < 5
            status = "🟢 Market is OPEN" if is_open else "🔴 Market is CLOSED"
            return f"{status}\nMarket hours: Mon-Fri, 9:30 AM - 4:00 PM ET"
        
        if intent == "TOP_GAINERS":
            return self.handle_top_movers("gainers")
        
        if intent == "TOP_LOSERS":
            return self.handle_top_movers("losers")
        
        if intent == "INDEX":
            text_lower = user_input.lower()
            if "dow" in text_lower or "jones" in text_lower:
                return self.handle_price("^DJI")
            if "nasdaq" in text_lower:
                return self.handle_price("^IXIC")
            if "s&p" in text_lower or "500" in text_lower:
                return self.handle_price("^GSPC")
            return self.handle_price("^GSPC")
        
        if intent == "CRYPTO":
            text_lower = user_input.lower()
            if "eth" in text_lower:
                return self.handle_price("ETH-USD")
            return self.handle_price("BTC-USD")
        
        if intent == "CASH":
            return self.handle_cash_balance()
        
        if intent == "ADD_CASH":
            numbers = entities.get("numbers", [])
            if numbers:
                return self.handle_add_cash(float(numbers[0]))
            return "How much cash?"
        
        if intent == "WHO":
            return "I'm Trade4U, your AI-powered market assistant! I can help you with stock prices, portfolio tracking, crypto, news, and more. Just ask naturally!"
        
        if intent == "HOW_ARE_YOU":
            return "I'm doing great! Ready to help you with the markets. What would you like to know?"
        
        if intent == "52WEEK":
            symbol = entities.get("symbol")
            if symbol:
                quote = get_quote(symbol)
                if quote and quote.get("high_52w") and quote.get("low_52w"):
                    return f"**{symbol}** 52-week range:\nHigh: ${quote['high_52w']:,.2f}\nLow: ${quote['low_52w']:,.2f}"
            return "Which stock's 52-week range?"
        
        if intent == "EARNINGS":
            symbol = entities.get("symbol")
            if symbol:
                return f"Earnings data for {symbol} - Check financial news for latest earnings report."
            return "Which stock's earnings?"
        
        if intent == "PE_RATIO":
            symbol = entities.get("symbol")
            if symbol:
                return f"P/E ratio for {symbol} - Check financial data for current valuation metrics."
            return "Which stock's P/E ratio?"
        
        if intent == "VOLUME":
            symbol = entities.get("symbol")
            if symbol:
                quote = get_quote(symbol)
                if quote and quote.get("volume"):
                    vol = quote["volume"]
                    if vol >= 1e6:
                        return f"**{symbol}** Volume: {vol/1e6:.2f}M"
                    elif vol >= 1e3:
                        return f"**{symbol}** Volume: {vol/1e3:.2f}K"
            return "Which stock's volume?"
        
        if intent == "UNKNOWN":
            if entities.get("symbol"):
                return self.handle_price(entities["symbol"])
            if "market" in user_input.lower():
                return self.handle_price("^GSPC")
            if is_ai_available():
                ai_response = ask_ai(user_input, exchange, stock_list)
                if ai_response:
                    return ai_response
        
        if intent == "AI":
            if is_ai_available():
                ai_response = ask_ai(user_input, exchange, stock_list)
                if ai_response:
                    return ai_response
            return "AI is not available. Install Ollama to enable AI features."
        
        return "I'm not sure what you're asking about. Try 'help' for options."

    def handle_add_holding_simple(self, symbol, shares, price):
        portfolio = load_portfolio()
        portfolio.setdefault("holdings", []).append({
            "symbol": symbol,
            "shares": shares,
            "purchase_price": price
        })
        save_portfolio(portfolio)
        self.portfolio = portfolio
        return f"✅ Added! {shares} shares of {symbol} at ${price:,.2f}"
    
    def handle_alert_simple(self, symbol, price, direction):
        alerts = load_alerts()
        alerts.append({
            "id": len(alerts) + 1,
            "symbol": symbol,
            "target_price": price,
            "direction": direction,
            "triggered": False
        })
        save_alerts(alerts)
        return f"🔔 Got it! I'll notify you when {symbol} goes {direction} ${price:,.2f}"
    
    def handle_top_movers(self, movers_type):
        settings = load_settings()
        exchange = settings.get("exchange", "NSE")
        currency = settings.get("currency", "INR")
        stock_list = settings.get("stock_list", "default")
        curr_symbol = "₹" if currency == "INR" else "$"
        
        symbols = STOCK_LISTS.get(stock_list, STOCK_LISTS["default"]).get(exchange, STOCK_LISTS["default"]["NYSE"])
        
        quotes = get_multiple_quotes(symbols)
        
        sorted_quotes = sorted(quotes.values(), key=lambda x: x["change_pct"], reverse=(movers_type == "gainers"))
        top = sorted_quotes[:5]
        
        emoji = "📈" if movers_type == "gainers" else "📉"
        title = "Top Gainers" if movers_type == "gainers" else "Top Losers"
        
        lines = [f"{emoji} **{title}** ({exchange})", ""]
        for q in top:
            sign = "+" if q["change_pct"] >= 0 else ""
            lines.append(f"{q['symbol']}: {sign}{q['change_pct']:.2f}% ({curr_symbol}{q['price']:,.2f})")
        
        return "\n".join(lines)

    def handle_recommend(self, user_input):
        text = user_input.lower()
        settings = load_settings()
        
        exchange = settings.get("exchange", "NSE")
        currency = settings.get("currency", "INR")
        stock_list = settings.get("stock_list", "default")
        
        symbols = STOCK_LISTS.get(stock_list, STOCK_LISTS["default"]).get(exchange, STOCK_LISTS["default"]["NYSE"])
        
        quotes = get_multiple_quotes(symbols)
        
        curr_symbol = "₹" if currency == "INR" else "$"
        
        if "short" in text or "intraday" in text or "today" in text:
            sorted_quotes = sorted(quotes.values(), key=lambda x: x["change_pct"], reverse=True)[:5]
            title = "📈 Short Term / Intraday Picks"
        elif "long" in text:
            valid_quotes = [q for q in quotes.values() if q.get("market_cap") or q.get("price")]
            if not valid_quotes:
                valid_quotes = list(quotes.values())
            sorted_quotes = sorted(valid_quotes, key=lambda x: x.get("market_cap") or x.get("price") or 0, reverse=True)[:5]
            title = "💎 Long Term Picks"
        else:
            sorted_quotes = sorted(quotes.values(), key=lambda x: x["change_pct"], reverse=True)[:5]
            title = "🔥 Top Stock Recommendations"
        
        lines = [title, f"*{exchange}/{stock_list} • {currency} • {settings.get('timezone', 'UTC')}*", ""]
        for q in sorted_quotes:
            sign = "+" if q["change_pct"] >= 0 else ""
            lines.append(f"{q['symbol']}: {sign}{q['change_pct']:.2f}% today ({curr_symbol}{q['price']:,.2f})")
        
        lines.append("")
        lines.append("*Note: These are just suggestions based on market data. Do your own research!*")
        
        return "\n".join(lines)

    def handle_available_stocks(self):
        settings = load_settings()
        exchange = settings.get("exchange", "NSE")
        stock_list = settings.get("stock_list", "default")
        
        symbols = STOCK_LISTS.get(stock_list, STOCK_LISTS["default"]).get(exchange, STOCK_LISTS["default"]["NYSE"])
        
        lines = [f"📋 Available Stocks ({exchange}/{stock_list})", ""]
        lines.append(", ".join(symbols))
        lines.append("")
        lines.append(f"Type 'top gainers' or 'which stock to buy' for live data!")
        
        return "\n".join(lines)

    def handle_price(self, symbol):
        settings = load_settings()
        currency = settings.get("currency", "USD")
        curr_symbol = "₹" if currency == "INR" else "$"
        
        quote = get_quote(symbol)
        if not quote:
            return f"I couldn't find data for {symbol}. Try another symbol like AAPL, TSLA, or NVDA."
        
        arrow = "📈" if quote["change"] >= 0 else "📉"
        sign = "+" if quote["change"] >= 0 else ""
        
        low = quote['high_52w']
        high = quote['low_52w']
        range_str = f"{curr_symbol}{low:,.2f} - {curr_symbol}{high:,.2f}" if low and high else "N/A"
        
        market_cap = ""
        if quote.get("market_cap"):
            cap = quote["market_cap"]
            sym = "₹" if currency == "INR" else "$"
            if cap >= 1e12:
                market_cap = f"\nMarket Cap: {sym}{cap/1e12:.2f}T"
            elif cap >= 1e9:
                market_cap = f"\nMarket Cap: {sym}{cap/1e9:.2f}B"
        
        return f"""{arrow} **{quote['name']} ({quote['symbol']})**
Price: **{curr_symbol}{quote['price']:,.2f}**
{arrow} {sign}{quote['change']:,.2f} ({sign}{quote['change_pct']:.2f}%)
Prev Close: {curr_symbol}{quote['prev_close']:,.2f}
52W Range: {range_str}{market_cap}"""

    def handle_52w(self, symbol):
        quote = get_quote(symbol)
        if not quote:
            return f"Couldn't find data for {symbol}."
        
        low = quote['low_52w']
        high = quote['high_52w']
        if low and high:
            return f"**{symbol}** 52-week range: ${low:,.2f} - ${high:,.2f}"
        return f"Couldn't find 52-week data for {symbol}."
    
    def handle_portfolio(self):
        holdings = self.portfolio.get("holdings", [])
        if not holdings:
            return "Your portfolio is empty. Tell me when you buy something, like: 'I bought 10 shares of AAPL at $200'"
        
        total_cost = 0
        total_value = 0
        lines = []
        
        for h in holdings:
            quote = get_quote(h["symbol"])
            current = quote["price"] if quote else h["purchase_price"]
            cost = h["shares"] * h["purchase_price"]
            value = h["shares"] * current
            pnl = value - cost
            pnl_pct = (pnl / cost) * 100 if cost else 0
            
            total_cost += cost
            total_value += value
            
            emoji = "🟢" if pnl >= 0 else "🔴"
            sign = "+" if pnl >= 0 else ""
            lines.append(f"{emoji} {h['symbol']}: {h['shares']} shares | ${value:,.2f} ({sign}{pnl_pct:.1f}%)")
        
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost else 0
        cash = self.portfolio.get("cash", 0)
        
        result = "\n".join(lines)
        result += f"\n\n💰 Total: ${total_value:,.2f} ({'+' if total_pnl >= 0 else ''}{total_pnl:,.2f} / {'+' if total_pnl >= 0 else ''}{total_pnl_pct:.1f}%)"
        result += f"\n💵 Cash: ${cash:,.2f}"
        result += f"\n📊 Total with cash: ${total_value + cash:,.2f}"
        return result

    def handle_portfolio_value(self):
        holdings = self.portfolio.get("holdings", [])
        if not holdings:
            return "Your portfolio is empty."
        
        total = 0
        for h in holdings:
            quote = get_quote(h["symbol"])
            if quote:
                total += h["shares"] * quote["price"]
            else:
                total += h["shares"] * h["purchase_price"]
        
        cash = self.portfolio.get("cash", 0)
        return f"Your portfolio is worth **${total + cash:,.2f}** (${total:,.2f} in stocks + ${cash:,.2f} cash)"

    def handle_add_holding(self, symbol, numbers, text):
        if not symbol:
            return "Which stock did you buy? Try: 'I bought 10 shares of AAPL at $200'"
        
        shares = numbers[0] if numbers else None
        price = numbers[1] if len(numbers) > 1 else None
        
        if not shares:
            return f"How many shares of {symbol} did you buy?"
        
        if not price:
            return f"At what price did you buy {symbol}?"
        
        portfolio = load_portfolio()
        portfolio.setdefault("holdings", []).append({
            "symbol": symbol,
            "shares": shares,
            "purchase_price": price
        })
        save_portfolio(portfolio)
        self.portfolio = portfolio
        return f"✅ Added! {shares} shares of {symbol} at ${price:,.2f}"

    def handle_remove_holding(self, symbol):
        if not symbol:
            return "Which stock did you sell?"
        
        portfolio = load_portfolio()
        original = len(portfolio.get("holdings", []))
        portfolio["holdings"] = [h for h in portfolio["holdings"] if h["symbol"].upper() != symbol.upper()]
        
        if len(portfolio["holdings"]) < original:
            save_portfolio(portfolio)
            self.portfolio = portfolio
            return f"✅ Removed {symbol} from your portfolio."
        return f"You don't have {symbol} in your portfolio."

    def handle_add_cash(self, amount):
        portfolio = load_portfolio()
        portfolio["cash"] = portfolio.get("cash", 0) + amount
        save_portfolio(portfolio)
        self.portfolio = portfolio
        return f"✅ Added ${amount:,.2f} to your cash balance. Total: ${portfolio['cash']:,.2f}"

    def handle_cash_balance(self):
        cash = self.portfolio.get("cash", 0)
        return f"You have ${cash:,.2f} in cash."

    def handle_alert(self, symbol, numbers, text):
        if not symbol:
            return "Which stock do you want to set an alert for?"
        
        if not numbers:
            return f"What price should I alert you for {symbol}?"
        
        price = numbers[0]
        direction = "above" if "above" in text else "below"
        
        alerts = load_alerts()
        alerts.append({
            "id": len(alerts) + 1,
            "symbol": symbol,
            "target_price": price,
            "direction": direction,
            "triggered": False
        })
        save_alerts(alerts)
        return f"🔔 Got it! I'll notify you when {symbol} goes {direction} ${price:,.2f}"

    def handle_news(self):
        news = get_news()
        if not news:
            return """📰 **Market News**

1. S&P 500 Shows Steady Performance
2. Tech Sector Leads Market Gains
3. Fed Signals Potential Policy Changes
4. Earnings Season in Focus
5. Global Markets Update"""
        
        lines = ["📰 **Market News**", ""]
        for i, (title, source) in enumerate(news[:5], 1):
            lines.append(f"{i}. {title}")
            lines.append(f"   __{source}__")
        return "\n".join(lines)

    def handle_chart(self, symbol):
        try:
            response = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"interval": "5m", "range": "1d"},
                headers=HEADERS,
                timeout=10
            )
            closes = response.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"][-20:]
            closes = [c for c in closes if c]
            
            if not closes:
                return f"No chart data for {symbol}."
            
            min_p, max_p = min(closes), max(closes)
            scale = 20 / (max_p - min_p) if max_p != min_p else 1
            
            quote = get_quote(symbol)
            name = quote["name"] if quote else symbol
            
            result = f"📈 **{name} ({symbol})** - Today\n\n"
            for close in closes:
                bar_len = max(2, int((close - min_p) * scale) + 1)
                result += f"│{'█' * bar_len} ${close:.2f}\n"
            return result
        except:
            return f"Couldn't load chart for {symbol}."


def run_chat():
    chat = Trade4UChat()
    console.print(f"\n[bold cyan]Trade4U:[/bold cyan] {GREETING}\n")
    
    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ")
            if not user_input.strip():
                continue
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print("\n[bold cyan]Trade4U:[/bold cyan] Bye! Happy trading! 📈\n")
                break
            
            if user_input.lower().strip() == "-settings":
                from rich.prompt import Prompt
                from rich.console import Console
                
                settings = load_settings()
                console.print("\n[bold yellow]⚙️ Current Settings:[/bold yellow]\n")
                console.print(f"  📌 Exchange: [cyan]{settings['exchange']}[/cyan]")
                console.print(f"  📋 Stock List: [cyan]{settings.get('stock_list', 'default')}[/cyan]")
                console.print(f"  🌐 Timezone: [cyan]{settings['timezone']}[/cyan]")
                console.print(f"  💰 Currency: [cyan]{settings['currency']}[/cyan]")
                console.print(f"  📊 Display: [cyan]{settings['display']}[/cyan]")
                console.print(f"  🔔 Alerts: [cyan]{'Enabled' if settings['alerts_enabled'] else 'Disabled'}[/cyan]\n")
                
                change = Prompt.ask("[bold]Change a setting? (y/n)[/bold]", default="n")
                if change.lower() == "y":
                    console.print("\n[bold]Available settings:[/bold]")
                    console.print("  1. Exchange (NSE, NYSE, NASDAQ)")
                    console.print("  2. Stock List (default, nifty50, tech, finance, midcap)")
                    console.print("  3. Timezone (Asia/Kolkata, America/New_York, etc.)")
                    console.print("  4. Currency (INR, USD, EUR)")
                    console.print("  5. Display (compact, detailed)")
                    console.print("  6. Alerts (on, off)")
                    
                    choice = Prompt.ask("[bold]Enter number (or press Enter to skip):[/bold]", default="")
                    if choice.strip() == "1":
                        new_val = Prompt.ask("[bold]Enter exchange:[/bold]", default=settings['exchange'])
                        settings['exchange'] = new_val.upper()
                    elif choice.strip() == "2":
                        console.print("\n[bold]Available stock lists:[/bold]")
                        for lst in STOCK_LISTS:
                            console.print(f"  • {lst}")
                        new_val = Prompt.ask("[bold]Enter stock list:[/bold]", default=settings.get('stock_list', 'default'))
                        settings['stock_list'] = new_val.lower()
                    elif choice.strip() == "3":
                        new_val = Prompt.ask("[bold]Enter timezone:[/bold]", default=settings['timezone'])
                        settings['timezone'] = new_val
                    elif choice.strip() == "4":
                        new_val = Prompt.ask("[bold]Enter currency:[/bold]", default=settings['currency'])
                        settings['currency'] = new_val.upper()
                    elif choice.strip() == "5":
                        new_val = Prompt.ask("[bold]Display (compact/detailed):[/bold]", default=settings['display'])
                        settings['display'] = new_val.lower()
                    elif choice.strip() == "6":
                        new_val = Prompt.ask("[bold]Alerts (on/off):[/bold]", default="on" if settings['alerts_enabled'] else "off")
                        settings['alerts_enabled'] = new_val.lower() == "on"
                    
                    save_settings(settings)
                    console.print("[bold green]✓ Settings saved![/bold green]\n")
                else:
                    console.print()
                continue
            
            console.print()
            response = chat.respond(user_input)
            console.print(f"[bold cyan]Trade4U:[/bold cyan] {response}\n")
            
        except KeyboardInterrupt:
            console.print("\n\n[bold cyan]Trade4U:[/bold cyan] Bye! Happy trading! 📈\n")
            break
        except EOFError:
            break


@click.command()
@click.version_option(version="0.2.0", prog_name="Trade4U", message="Trade4U v0.2.0")
def cli():
    """Trade4U - Your Market Assistant"""
    run_chat()


if __name__ == "__main__":
    cli()
