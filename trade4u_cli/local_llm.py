import requests
import json

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2"

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
        "NSE": ["M&M", "TITAN", "BAJFINANCE", "ADANI", "PIDILITIND", "DMART", "BPCL", "HINDUNILVR"],
        "NYSE": ["UBER", "SNAP", "PINS", "TWLO", "PLTR", "SQ", "SHOP", "ROKU", "ZM", "DOCU"],
    },
}

INDIAN_COMPANY_NAMES = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "INFY": "Infosys",
    "HDFCBANK": "HDFC Bank",
    "ADANIENT": "Adani Enterprises",
    "SBIN": "State Bank of India",
    "BHARTIARTL": "Bharti Airtel",
    "ICICIBANK": "ICICI Bank",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "AXISBANK": "Axis Bank",
    "LT": "Larsen & Toubro",
    "WIPRO": "Wipro",
    "HCLTECH": "HCL Technologies",
    "TECHM": "Tech Mahindra",
    "BAJFINANCE": "Bajaj Finance",
    "M&M": "Mahindra & Mahindra",
    "TITAN": "Titan Company",
    "ADANI": "Adani Ports",
    "PIDILITIND": "Pidilite Industries",
    "DMART": "Avenue Supermarts",
    "BPCL": "Bharat Petroleum",
    "HINDUNILVR": "Hindustan Unilever",
}

US_COMPANY_NAMES = {
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
}

class LocalLLM:
    def __init__(self, model=None, url=None):
        self.model = model or DEFAULT_MODEL
        self.url = url or DEFAULT_OLLAMA_URL
        self.available = self._check_connection()
    
    def _check_connection(self):
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def is_available(self):
        return self.available
    
    def chat(self, prompt, system_prompt=None):
        if not self.available:
            return None
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(self.url, json=payload, timeout=120)
            if response.status_code == 200:
                return response.json().get("response", "")
        except:
            pass
        return None
    
    def list_models(self):
        if not self.available:
            return []
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except:
            pass
        return []

llm = LocalLLM()

def get_stock_info_for_ai(exchange, stock_list):
    stocks = STOCK_LISTS.get(stock_list, STOCK_LISTS["default"]).get(exchange, [])
    company_names = INDIAN_COMPANY_NAMES if exchange == "NSE" else US_COMPANY_NAMES
    
    stock_text = "\n".join([f"- {s}: {company_names.get(s, s)}" for s in stocks])
    
    return f"""Current settings:
- Exchange: {exchange}
- Stock List: {stock_list}
- Available stocks ({exchange}):

{stock_text}

Use these stock symbols when discussing prices or recommendations."""

def build_system_prompt(exchange, stock_list):
    stock_info = get_stock_info_for_ai(exchange, stock_list)
    return f"""You are Trade4U, a friendly AI trading assistant. You help users with:
- Stock prices and market data
- Portfolio tracking and analysis
- Market news and trends
- Crypto prices
- Investment recommendations

{stock_info}

Keep responses short and conversational. Use emojis where appropriate. 
If you don't know something, say so honestly. Always use the stock symbols from the available list above when referring to stocks."""

def ask_ai(query, exchange="NSE", stock_list="default", context=""):
    system_prompt = build_system_prompt(exchange, stock_list)
    full_prompt = f"{context}\n\nUser: {query}\n\nAssistant:"
    return llm.chat(full_prompt, system_prompt)

def is_ai_available():
    return llm.is_available()
