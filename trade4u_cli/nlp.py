import re
from difflib import SequenceMatcher

INTENTS = {
    "PRICE": {
        "keywords": ["price", "cost", "worth", "value", "at", "trading at", "quote", "how much", "going for", "trading for", "at what", "check", "get", "show me", "look up", "52 week", "year high", "year low", "range", "trading", "going", "current", "share", "doing", "at"],
        "patterns": [r"\bat\s+\$?(\d+)", r"\bwhat'?s?\s+(\w+)\s+(at|trading|worth)", r"\bhow much is\s+(\w+)", r"how'?s?\s+(\w+)\s+(doing|looking|trading)", r"(?:what|how)\s+(?:is|are)\s+(\w+)\s+doing"],
    },
    "PORTFOLIO": {
        "keywords": ["portfolio", "holdings", "investments", "positions", "my stocks", "my shares", "my investments", "show my", "show portfolio", "my positions", "my stuff", "my account", "what i own", "show positions", "i own", "own", "my positions", "positions"],
        "patterns": [r"show\s+(?:my\s+)?(?:portfolio|holdings|positions)", r"what\s+(?:do|i)\s+own", r"list\s+(?:my\s+)?(?:holdings|positions)"],
    },
    "ADD_HOLDING": {
        "keywords": ["bought", "purchased", "bought", "acquired", "added", "i have", "i bought", "i purchased", "just bought", "own", "hold", "invested", "put in", "added to portfolio", "new position", "take position"],
        "patterns": [r"(?:bought|purchased|acquired)\s+(\d+)\s+(\w+)", r"(\d+)\s+shares?\s+(?:of\s+)?(\w+)", r"(?:bought|purchased)\s+(\w+)\s+(\d+)", r"i own (\d+)\s+(\w+)", r"add\s+(\w+)\s+(\d+)"],
    },
    "REMOVE_HOLDING": {
        "keywords": ["sold", "removed", "deleted", "liquidated", "stopped owning", "no longer", "sold all", "liquidate", "close position", "exit", "unwind", "sold out"],
        "patterns": [r"(?:sold|remove|liquidate)\s+(?:all\s+)?(\w+)", r"close\s+(?:my\s+)?(\w+)", r"sell\s+(?:all\s+)?(\w+)"],
    },
    "ALERT": {
        "keywords": ["alert", "notify", "tell me when", "wake me", "notify me", "notify when", "trigger", "watch", "wake me", "let me know", "remind", "alert me", "track", "monitor", "watch", "let me know when", "notify if"],
        "patterns": [r"alert\s+(?:me\s+)?(?:when|if)\s+(\w+)\s+(hits?|goes?|reaches?|drops?|falls?|above|below)\s+\$?(\d+)", r"notify\s+me\s+when\s+(\w+)\s+\$?(\d+)", r"watch\s+(\w+)\s+(?:at|when|if)\s*\$?(\d+)", r"(?:watch|monitor)\s+(\w+)", r"(?:let|keep)\s+me\s+know\s+when"],
    },
    "NEWS": {
        "keywords": ["news", "headlines", "market update", "what's happening", "what happened", "latest", "current events", "happen", "what's new", "buzz", "rumors", "reports", "stories", "headlines"],
        "patterns": [r"(?:any|latest|recent)\s+news", r"what'?s?\s+(?:going\s+on|new|happening)"],
    },
    "CHART": {
        "keywords": ["chart", "graph", "plot", "visual", "candlestick", "price history", "trend", "show me chart", "draw", "display", "show graph", "technical", "visualize", "diagram"],
        "patterns": [r"(?:show|draw|display)\s+(?:me\s+)?(?:a\s+)?(?:chart|graph|plot)"],
    },
    "MARKET_STATUS": {
        "keywords": ["market open", "market closed", "trading hours", "is market open", "is market closed", "when market", "market hours", "open today", "closed today", "time until", "time till", "when open", "when close", "nyse", "us market"],
        "patterns": [r"(?:is|are)\s+(?:the\s+)?market\s+(?:open|closed)"],
    },
    "TOP_GAINERS": {
        "keywords": ["top gainers", "best stocks", "winning", "up the most", "best performers", "most up", "gaining", "gainers", "trending up", "biggest gains", "highest gain", "movers", "leaders", "outperformers", "performing stocks", "best performing", "trending higher"],
        "patterns": [r"(?:top|best)\s+(?:gaining|gainers|performers)", r"stocks?\s+(?:up|gaining)", r"(?:who'?s|which\s+are)\s+(?:winning|up|gaining)", r"best\s+(?:performing|trending)"],
    },
    "TOP_LOSERS": {
        "keywords": ["top losers", "worst stocks", "losing", "down the most", "worst performers", "most down", "falling", "losers", "trending down", "biggest losses", "worst", "decliners", "underperformers"],
        "patterns": [r"(?:top|worst)\s+(?:losing|losers|performers)", r"stocks?\s+(?:down|losing)", r"(?:who'?s|which\s+are)\s+(?:losing|down)"],
    },
    "INDEX": {
        "keywords": ["s&p", "sp500", "spx", "dow", "dji", "djia", "nasdaq", "ixic", "russell", "rut", "market index", "indices", "dow jones", "spider", "ticker", "broad market", "wall street"],
        "patterns": [r"(?:the\s+)?(?:s&p\s*500|sp500|spx|dow\s*jones|nasdaq|russell)"],
    },
    "CRYPTO": {
        "keywords": ["bitcoin", "btc", "ethereum", "eth", "crypto", "dogecoin", "solana", "cryptocurrency", "digital currency", "xrp", "ada", "cardano", "dot", "polkadot", "avax", "avalanche", "matic", "link", "uni", "aave"],
        "patterns": [r"(?:bitcoin|btc|ethereum|eth|crypto)\s+(?:price|at|worth)", r"(?:what|how)\s+(?:is|are)\s+(?:bitcoin|btc|eth)"],
    },
    "HELP": {
        "keywords": ["help", "what can you do", "commands", "what do you know", "options", "capabilities", "what all", "what do you support", "list commands", "how do i", "guide", "tutorial"],
        "patterns": [r"(?:what\s+can\s+(?:you|i)|how\s+does)\s+(?:you|i)\s+(?:do|work|know)"],
    },
    "GREETING": {
        "keywords": ["hi", "hello", "hey", "howdy", "good morning", "good afternoon", "good evening", "greetings", "hi there", "yo", "wassup", "whats up", "sup", "hiya", "hallo", "heya", "ai", "chat", "talk", "ask"],
        "patterns": [],
        "min_score": 2,
    },
    "GOODBYE": {
        "keywords": ["bye", "exit", "quit", "see you", "goodbye", "later", "take care", "cya", "laters", "farewell", "see ya", "gotta go", "got to go", "moving on"],
        "patterns": [],
    },
    "THANKS": {
        "keywords": ["thanks", "thank you", "thx", "appreciate", "grateful", "much appreciated", "ty", "thnx", "kudos", "props", "cheers", "so much", "a lot"],
        "patterns": [],
        "min_score": 2,
    },
    "PORTFOLIO_VALUE": {
        "keywords": ["portfolio worth", "total value", "how much is my portfolio", "portfolio value", "worth my portfolio", "portfolio total", "how much my portfolio", "portfolio balance", "account value", "net worth"],
        "patterns": [r"(?:how\s+much\s+(?:is|are)|what\s+is)\s+(?:my\s+)?portfolio"],
    },
    "CASH": {
        "keywords": ["cash", "balance", "available", "money", "funds", "buying power", "dry powder", "liquid"],
        "patterns": [r"(?:show\s+)?(?:my\s+)?(?:cash|balance|funds|money)"],
    },
    "ADD_CASH": {
        "keywords": ["add cash", "deposit", "put money", "add money", "add to cash", "deposit cash", "add funds", "top up", "transfer in", "wire money", "add balance"],
        "patterns": [r"(?:add|deposit|top\s*up)\s+\$?(\d+)", r"(?:add|deposit)\s+(?:cash|money|funds)\s+\$?(\d+)", r"put\s+\$?(\d+)\s+(?:in|cash)"],
    },
    "52WEEK": {
        "keywords": ["52 week", "52w", "year high", "year low", "52 week high", "52 week low", "all time", "high", "low", "support", "resistance", "ATH", "ATL"],
        "patterns": [r"52\s*[-]?week\s+(high|low)", r"(?:all\s+)?time\s+(high|low|high|low)", r"support\s+level", r"resistance\s+level"],
    },
    "EARNINGS": {
        "keywords": ["earnings", "revenue", "eps", "profit", "loss", "beat", "miss", "report", "quarterly", "results", "income", "guidance", "outlook"],
        "patterns": [r"(?:earnings|revenue)\s+(?:report|beat|miss|estimate)", r"quarter\s+(?:results|report)"],
    },
    "PE_RATIO": {
        "keywords": ["pe", "p/e", "ratio", "valuation", "expensive", "cheap", "overvalued", "undervalued", "multiple"],
        "patterns": [r"(?:p\/e|pe\s+ratio)", r"(?:over|under)valued"],
    },
    "DIVIDEND": {
        "keywords": ["dividend", "yield", "payout", "distribution", "quarterly", "annual", "ex-dividend", "dividend date"],
        "patterns": [r"(?:dividend|yield)\s+(?:yield|date|payout)", r"pay\s+(?:quarterly|annual)"],
    },
    "VOLUME": {
        "keywords": ["volume", "trading volume", "shares traded", "turnover", "liquidity"],
        "patterns": [r"(?:trading\s+)?volume", r"(?:shares?\s+)?traded"],
    },
    "WHO": {
        "keywords": ["who are you", "what are you", "your name", "tell me about yourself", "what is this", "what are you"],
        "patterns": [r"(?:who|what)\s+(?:are|is)\s+(?:you|this)"],
    },
    "HOW_ARE_YOU": {
        "keywords": ["how are you", "how do you do", "how is it going", "hows it going", "how you doing"],
        "patterns": [],
    },
    "CLEAR": {
        "keywords": ["clear", "reset", "start over", "clear portfolio", "empty portfolio", "wipe"],
        "patterns": [r"(?:clear|reset|empty|wipe)\s+(?:portfolio|positions)"],
    },
    "LIST": {
        "keywords": ["list", "show all", "display", "see all", "what do i have", "list everything"],
        "patterns": [r"(?:list|show|display)\s+(?:all|everything)"],
    },
    "RECOMMEND": {
        "keywords": ["recommend", "suggest", "buy", "sell", "what to buy", "what to invest", "which stock", "best stock", "good stock", "pick", "investment idea", "hot stock", "momentum", "short term", "long term", "intraday", "today", "what stocks", "list stocks", "show stocks", "available stocks", "stocks to buy", "stocks to watch"],
        "patterns": [r"(?:which|what|give me|recommend|suggest)\s+.*(?:buy|pick|stock|invest)", r"best\s+(?:stock|pick|buy)", r"(?:hot|top|momentum)\s+stock", r"what\s+to\s+buy", r"investment\s+idea", r"(?:short|long|intraday)\s*term", r"(?:what|show|list)\s+stocks?\s+(?:can|to|available)", r"available\s+stocks"],
    },
    "AI": {
        "keywords": ["think", "analyze", "opinion", "view", "your thoughts", "what do you think", "explain", "why", "reason", "should i", "is it good", "worth it", "advice", "insight", "perspective"],
        "patterns": [r"what\s+(do\s+you\s+think|do\s+you\s+say|about|your\s+opinion)", r"your\s+(thoughts?|opinion|view|advice)", r"(should|could)\s+you\s+(explain|analyze|tell)", r"why\s+(do\s+you|is|are|should)", r"(?:give\s+me\s+)?(?:your\s+)?(?:opinion|thoughts?|advice|insight)"],
    },
}


def fuzzy_match(word, keywords, threshold=0.8):
    for kw in keywords:
        ratio = SequenceMatcher(None, word, kw).ratio()
        if ratio >= threshold:
            return True
    return False


INTENT_PRIORITY = {
    "GREETING": 100,
    "GOODBYE": 100,
    "THANKS": 100,
    "WHO": 95,
    "HOW_ARE_YOU": 95,
    "HELP": 90,
    "ADD_HOLDING": 85,
    "REMOVE_HOLDING": 85,
    "ALERT": 80,
    "ADD_CASH": 75,
    "PORTFOLIO": 70,
    "PORTFOLIO_VALUE": 70,
    "PRICE": 50,
    "INDEX": 50,
    "CRYPTO": 50,
    "RECOMMEND": 55,
    "MARKET_STATUS": 60,
    "TOP_GAINERS": 60,
    "TOP_LOSERS": 60,
    "NEWS": 40,
    "CHART": 40,
    "52WEEK": 30,
    "EARNINGS": 30,
    "PE_RATIO": 30,
    "VOLUME": 30,
    "CASH": 20,
}


def classify_intent(text):
    text_lower = text.lower().strip()
    scores = {}
    
    if text_lower == "stock market":
        return "INDEX"
    
    if re.search(r'\b(thank|thx|thanks|appreciate|grateful|cheers)\b', text_lower):
        return "THANKS"
    
    if re.search(r'\bhow\s+(are\s+)?you\b', text_lower):
        return "HOW_ARE_YOU"
    
    if re.search(r'\b(who\s+(are|is)\s+(you|this)|what\s+(are|is)\s+(you|this)|your\s+name)\b', text_lower):
        return "WHO"
    
    if re.search(r'\b(what\s+(do\s+i\s+own|am\s+i\s+holding)|show\s+(my\s+)?(portfolio|holdings|positions))\b', text_lower):
        return "PORTFOLIO"
    
    if re.search(r'\b(my\s+)?holdings\b', text_lower):
        return "PORTFOLIO"
    
    if re.search(r'\b(watch|alert|notify|monitor|track)\s+\w+', text_lower) and re.search(r'\b\d+\b', text_lower):
        return "ALERT"
    
    if re.search(r'\b(add|deposit|put|top\s*up)\s+\d+', text_lower):
        return "ADD_CASH"
    
    if re.search(r'\b(buy|pick|suggest|recommend|which|what to|instant)\s+.*(stock|pick|invest|trade)\b', text_lower):
        return "RECOMMEND"
    
    if re.search(r'\b(stock|stock to|stock for)\s+(buy|invest|trade|pick)\b', text_lower):
        return "RECOMMEND"
    
    if re.search(r'\b(what|show|list)\s+(stocks?|available)\b', text_lower):
        return "RECOMMEND"
    
    if re.search(r'\b(short|long|intraday)\s*term\b', text_lower):
        return "RECOMMEND"
    
    if re.search(r'\b(watch|alert|notify|monitor|track)\s+\w+', text_lower) and re.search(r'\b\d+\b', text_lower):
        return "ALERT"
    
    if re.search(r'\b(what\s+(is|was)\s+happening|latest\s+news|recent\s+news|headlines|market\s+news)\b', text_lower):
        return "NEWS"
    
    if re.search(r'\b(any|latest|market)\s+(market\s+)?(info|information|update|data)\b', text_lower):
        return "NEWS"
    
    if re.search(r'\b(show|get|fetch|fetch|retrieve|give|give me)\s+.*(price|quote|value|info|data|details)\b', text_lower):
        return "PRICE"
    
    if re.search(r'\b(how|what)\s+(is|are|was|were)\s+(\w+)\s+(doing|looking|trading|worth|valued)\b', text_lower):
        return "PRICE"
    
    if re.search(r'\b(price|quote|value|worth)\s+(of|for|on)\b', text_lower):
        return "PRICE"
    
    if re.search(r'\b(stock\s+market|market\s+news|trading\s+news|market\s+update)\b', text_lower):
        return "NEWS"
    
    if re.search(r'\b(anything|everything)\s+(about|on)\s+(the\s+)?(market|stocks|stock|crypto)\b', text_lower):
        return "NEWS"
    
    if re.search(r'\b(anything|everything)\s+(about|on)\b', text_lower):
        return "PRICE"
    
    if text_lower.strip() == "stock market":
        return "INDEX"
    
    if re.search(r'\b(stock\s+market|market\s+news|trading\s+news|market\s+update)\b', text_lower):
        return "NEWS"
    
    if re.search(r'\b(show|get|tell|give|what)\s+.*(market|stock|trading)\b', text_lower):
        return "NEWS"
    
    if re.search(r'\b(best|top)\s+(performing|performers?|gaining|gainers?|stocks?|movers|level|tier)\b', text_lower):
        return "TOP_GAINERS"
    
    if re.search(r'\b(how|what)\s+(is|are|was|were)\s+(\w+)\s+(doing|looking|trading)\b', text_lower):
        return "PRICE"
    
    text_lower_clean = text_lower.replace("what is", "").replace("how much", "").replace("what's", "").replace("how's", "")
    
    for intent, config in INTENTS.items():
        score = 0
        for keyword in config["keywords"]:
            if keyword in text_lower:
                score += 1
            elif " " in keyword and keyword in text_lower_clean:
                score += 1
        
        for pattern in config["patterns"]:
            if re.search(pattern, text_lower):
                score += 3
        
        if score > 0:
            scores[intent] = score
    
    if not scores:
        return "UNKNOWN"
    
    best_intent = max(scores.keys(), key=lambda k: (scores[k], INTENT_PRIORITY.get(k, 0)))
    
    return best_intent


def extract_entities(text):
    text_clean = text.replace("'", " ").upper()
    text_lower = text.lower()
    
    entities = {
        "symbol": None,
        "numbers": [],
        "direction": None,
    }
    
    entities["numbers"] = [float(n.replace(",", "")) for n in re.findall(r'\d+\.?\d*', text)]
    
    crypto_map = {
        "BITCOIN": "BTC-USD", "BTC": "BTC-USD", "XRP": "XRP-USD",
        "ETHEREUM": "ETH-USD", "ETH": "ETH-USD",
        "DOGECOIN": "DOGE-USD", "DOGE": "DOGE-USD",
        "SOLANA": "SOL-USD", "SOL": "SOL-USD",
        "CARDANO": "ADA-USD", "ADA": "ADA-USD",
        "POLKADOT": "DOT-USD", "DOT": "DOT-USD",
        "AVALANCHE": "AVAX-USD", "AVAX": "AVAX-USD",
        "MATIC": "MATIC-USD", "POLYGON": "MATIC-USD",
        "CHAINLINK": "LINK-USD", "LINK": "LINK-USD",
        "UNICRYPT": "UNI-USD", "UNI": "UNI-USD",
        "AAVE": "AAVE-USD",
    }
    
    for name, sym in crypto_map.items():
        if name in text_clean:
            entities["symbol"] = sym
            return entities
    
    company_map = {
        "APPLE": "AAPL", "TESLA": "TSLA", "GOOGLE": "GOOGL", "ALPHABET": "GOOGL",
        "AMAZON": "AMZN", "MICROSOFT": "MSFT", "META": "META", "FACEBOOK": "META",
        "NVIDIA": "NVDA", "NETFLIX": "NFLX", "INTEL": "INTC", "DISNEY": "DIS",
        "ADOBE": "ADBE", "PAYPAL": "PYPL", "SALESFORCE": "CRM", "ORACLE": "ORCL",
        "WALMART": "WMT", "NIKE": "NKE", "COKE": "KO", "MCDONALD": "MCD",
        "UBER": "UBER", "LYFT": "LYFT", "SPOTIFY": "SPOT", "SPOT": "SPOT",
        "SQUARE": "SQ", "SQ": "SQ", "SHOPIFY": "SHOP", "SHOP": "SHOP",
        "COINBASE": "COIN", "COIN": "COIN", "JP MORGAN": "JPM", "JPMORGAN": "JPM",
        "BANK OF AMERICA": "BAC", "BAC": "BAC", "TARGET": "TGT", "COSTCO": "COST",
        "VISA": "V", "MASTERCARD": "MA", "JOHNSON": "JNJ", "JOHNSON & JOHNSON": "JNJ",
        "UNITEDHEALTH": "UNH", "EXXON": "XOM", "CHEVRON": "CVX", "PFIZER": "PFE",
        "ABBVie": "ABBV", "COCA COLA": "KO", "PEPSI": "PEP", "MCDONALD'S": "MCD",
        "AMD": "AMD", "INTERNATIONAL BUSINESS MACHINES": "IBM", "IBM": "IBM",
        "SPOTIFY TECHNOLOGY": "SPOT", "MARGIN": "PYPL", "SNAP": "SNAP",
        "TWITTER": "X", "X": "X", "BERKSHIRE": "BRK.B", "BRK": "BRK.B",
        "RELIANCE": "RELIANCE", "TCS": "TCS", "INFOSYS": "INFY", "INFY": "INFY",
        "HDFC": "HDFCBANK", "SBIN": "SBIN", "BHARTI": "BHARTIARTL", "ICICI": "ICICIBANK",
        "ADANI": "ADANIENT", "WIPRO": "WIPRO", "HCL": "HCLTECH", "MARUTI": "MARUTI",
        "TATA": "TATAMOTORS", "KOTAK": "KOTAKBANK", "AXIS": "AXISBANK",
        "QUALCOMM": "QCOM", "BROADCOM": "AVGO", "AVGO": "AVGO",
        "GOLDMAN": "GS", "GS": "GS", "MORGAN STANLEY": "MS", "MS": "MS",
        "CITI": "C", "CITIGROUP": "C", "AMERICAN EXPRESS": "AXP", "AXP": "AXP",
        "BLACKROCK": "BLK", "CAPITAL ONE": "COF", "USB": "USB", "WELLS FARGO": "WFC",
        "SNAPCHAT": "SNAP", "PINTEREST": "PINS", "TWILIO": "TWLO",
        "PALANTIR": "PLTR", "ROKU": "ROKU", "ZOOM": "ZM", "DOCUSIGN": "DOCU",
    }
    
    for name, sym in company_map.items():
        if name in text_clean:
            entities["symbol"] = sym
            return entities
    
    index_map = {
        "^GSPC": ["S&P", "SP500", "SPX", "SANDP", "500", "SPIDER"],
        "^DJI": ["DOW", "DOW JONES", "DJI", "DJIA", "JONES"],
        "^IXIC": ["NASDAQ", "IXIC", "TECH"],
        "^RUT": ["RUSSELL", "RUT", "2000"],
    }
    
    for sym, names in index_map.items():
        for name in names:
            if name in text_clean:
                entities["symbol"] = sym
                return entities
    
    stock_symbols = [
        "AAPL", "GOOGL", "GOOG", "MSFT", "AMZN", "META", "TSLA", "NVDA",
        "AMD", "NFLX", "DIS", "PYPL", "INTC", "IBM", "ORCL", "CRM", "ADBE",
        "UBER", "LYFT", "SPOT", "SQ", "SHOP", "COIN", "JPM", "BAC", "WMT",
        "TGT", "COST", "V", "MA", "JNJ", "UNH", "XOM", "CVX", "PFE", "ABBV",
        "KO", "PEP", "MCD", "NKE", "SNAP", "X", "SQ", "ROKU", "ZM", "DOCU",
        "TWLO", "SNOW", "CRWD", "NET", "DDOG", "PLTR", "SOFI", "RIVN", "LCID",
        "QCOM", "AVGO", "BRK.B", "GS", "MS", "C", "AXP", "BLK", "COF", "USB", "WFC",
        "PINS", "RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "BHARTIARTL", "ICICIBANK",
    ]
    
    words = text_clean.split()
    for word in words:
        clean = re.sub(r'[^A-Z]', '', word)
        if clean in stock_symbols:
            entities["symbol"] = clean
            return entities
    
    match = re.search(r'\b([A-Z]{2,5})\b', text_clean)
    if match:
        sym = match.group(1)
        if sym in stock_symbols:
            entities["symbol"] = sym
            return entities
    
    return entities


COMPANY_NAMES = {
    "APPLE": "AAPL", "TESLA": "TSLA", "GOOGLE": "GOOGL", "ALPHABET": "GOOGL",
    "AMAZON": "AMZN", "MICROSOFT": "MSFT", "META": "META", "FACEBOOK": "META",
    "NVIDIA": "NVDA", "NETFLIX": "NFLX", "INTEL": "INTC", "DISNEY": "DIS",
    "ADOBE": "ADBE", "PAYPAL": "PYPL", "SALESFORCE": "CRM", "ORACLE": "ORCL",
    "WALMART": "WMT", "NIKE": "NKE", "COKE": "KO", "MCDONALD": "MCD",
    "UBER": "UBER", "SNAP": "SNAP", "PINTEREST": "PINS", "TWILIO": "TWLO",
    "PALANTIR": "PLTR", "ROKU": "ROKU", "ZOOM": "ZM", "DOCUSIGN": "DOCU",
    "QUALCOMM": "QCOM", "BROADCOM": "AVGO", "RELIANCE": "RELIANCE",
    "TCS": "TCS", "INFOSYS": "INFY", "HDFC": "HDFCBANK", "SBIN": "SBIN",
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
    "QCOM": "Qualcomm", "AVGO": "Broadcom", "BRK.B": "Berkshire Hathaway",
    "GS": "Goldman Sachs", "MS": "Morgan Stanley", "C": "Citigroup",
    "AXP": "American Express", "BLK": "BlackRock", "COF": "Capital One",
    "USB": "US Bancorp", "WFC": "Wells Fargo", "SNAP": "Snap", "PINS": "Pinterest",
    "TWLO": "Twilio", "PLTR": "Palantir", "ROKU": "Roku", "ZM": "Zoom",
    "DOCU": "DocuSign",
}

CRYPTO_SYMBOLS = {
    "BTC": "BTC-USD", "BITCOIN": "BTC-USD",
    "ETH": "ETH-USD", "ETHEREUM": "ETH-USD",
}

MARKET_INDICES = {
    "^GSPC": ("S&P 500", "SPX"),
    "^DJI": ("Dow Jones", "DJI"),
    "^IXIC": ("NASDAQ", "IXIC"),
    "^RUT": ("Russell 2000", "RUT"),
}

STOP_WORDS = {
    "WHAT", "HOW", "WHEN", "WHERE", "WHY", "WHO", "THE", "THIS", 
    "THAT", "FOR", "FROM", "WITH", "ABOUT", "WHATS", "HERE", "THERE",
    "WHICH", "BEEN", "BEING", "HAVE", "HAS", "HAD", "WILL", "WOULD",
    "COULD", "SHOULD", "THEIR", "THESE", "THOSE", "THEN", "JUST", "LIKE",
    "MORE", "SOME", "SUCH", "INTO", "OVER", "AFTER", "ABOVE", "BELOW",
    "UNDER", "SINCE", "AGAIN", "ONCE", "EACH", "BOTH", "FEW", "MANY",
    "MUCH", "OTHER", "SAME", "ONLY", "THAN", "ALSO", "VERY", "NOW",
    "DOES", "DID", "CAN", "MAY", "MUST", "SHALL", "TELL", "ME",
    "MA", "PA", "SO", "DO", "NO", "IF", "IS", "IT", "IN", "ON", "AT",
    "AN", "AS", "WE", "US", "BE", "BY", "TO", "MY", "GO", "UP", "AM",
    "GET", "SET", "LET", "SAY", "SAID", "ONE", "TWO", "NEW", "OLD",
    "QCOM", "AVGO", "GS", "MS", "C", "AXP", "BLK", "COF", "USB", "WFC",
    "PINS", "RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "BHARTIARTL", "ICICIBANK",
}


def parse_command(text):
    text = text.strip()
    if not text:
        return {"intent": "UNKNOWN", "entities": {"symbol": None, "numbers": [], "direction": None}}
    
    intent = classify_intent(text)
    entities = extract_entities(text)
    
    text_lower = text.lower()
    
    if intent == "ADD_HOLDING":
        numbers = entities.get("numbers", [])
        if numbers:
            entities["shares"] = numbers[0]
            if len(numbers) > 1:
                entities["price"] = numbers[1]
        
        match = re.search(r'(?:bought|purchased)\s+(\w+)\s+(?:at\s+)?\$?(\d+(?:\.\d+)?)', text_lower)
        if match:
            if not entities.get("symbol"):
                sym_match = re.search(r'(?:bought|purchased)\s+(\w+)', text_lower)
                if sym_match:
                    potential = sym_match.group(1).upper()
                    if potential in STOCK_SYMBOLS:
                        entities["symbol"] = potential
            if len(numbers) < 2:
                price_match = re.search(r'(?:bought|purchased)\s+\w+\s+(?:at\s+)?\$?(\d+(?:\.\d+)?)', text_lower)
                if price_match:
                    entities["price"] = float(price_match.group(1))
    
    if intent == "ALERT":
        numbers = entities.get("numbers", [])
        if numbers:
            entities["target_price"] = numbers[0]
        
        if any(w in text_lower for w in ["below", "drops", "falls", "under", "down"]):
            entities["direction"] = "below"
        else:
            entities["direction"] = "above"
    
    if intent == "ADD_CASH":
        numbers = entities.get("numbers", [])
        if not numbers:
            match = re.search(r'(?:add|deposit|put|top\s*up)\s+\$?(\d+(?:\.\d+)?)', text_lower)
            if match:
                entities["numbers"] = [float(match.group(1))]
    
    if intent == "CHART":
        if not entities.get("symbol"):
            for word in text.split():
                clean = re.sub(r'[^A-Z]', '', word.upper())
                if clean in STOCK_SYMBOLS:
                    entities["symbol"] = clean
                    break
    
    if intent == "INDEX":
        text_lower = text.lower()
        if "dow" in text_lower or "jones" in text_lower:
            entities["symbol"] = "^DJI"
        elif "nasdaq" in text_lower:
            entities["symbol"] = "^IXIC"
        elif "s&p" in text_lower or "500" in text_lower or "spx" in text_lower:
            entities["symbol"] = "^GSPC"
        elif "russell" in text_lower:
            entities["symbol"] = "^RUT"
        else:
            entities["symbol"] = "^GSPC"
    
    if intent == "CRYPTO":
        if "eth" in text_lower:
            entities["symbol"] = "ETH-USD"
        else:
            entities["symbol"] = "BTC-USD"
    
    return {"intent": intent, "entities": entities}
