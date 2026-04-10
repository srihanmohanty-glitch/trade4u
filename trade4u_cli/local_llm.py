import requests
import json
from trade4u_cli.data.stocks import ALL_STOCKS, STOCK_LISTS

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2"


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

        payload = {"model": self.model, "prompt": prompt, "stream": False}
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


def get_stock_list_text(exchange, stock_list_key):
    stock_lists = STOCK_LISTS.get(stock_list_key, STOCK_LISTS["default"])
    symbols = stock_lists.get(exchange, [])
    if not symbols:
        symbols = stock_lists.get("NYSE", [])

    stock_info = []
    for sym in symbols[:50]:
        name = ALL_STOCKS.get(sym, sym)
        stock_info.append(f"- {sym}: {name}")
    return "\n".join(stock_info)


def get_all_stock_info():
    info = ["Available stocks:\n"]
    for sym, name in sorted(ALL_STOCKS.items())[:200]:
        info.append(f"- {sym}: {name}")
    return "\n".join(info)


def build_system_prompt(exchange, stock_list):
    stock_list_text = get_stock_list_text(exchange, stock_list)

    return f"""You are Trade4U, an advanced AI trading assistant with deep market knowledge.

You have access to {len(ALL_STOCKS)}+ stocks including:
- US stocks (NYSE, NASDAQ): Apple, Microsoft, Google, Amazon, Tesla, NVIDIA, Meta, etc.
- Indian stocks (NSE): Reliance, TCS, Infosys, HDFC Bank, etc.
- Crypto: Bitcoin, Ethereum, etc.
- Commodities: Gold, Silver, Oil, etc.
- Forex: USD/INR, EUR/USD, etc.
- ETFs: SPY, QQQ, VTI, etc.

Current user's exchange: {exchange}
Stock list: {stock_list}

Available stocks for this user:
{stock_list_text}

You help users with:
- Stock prices and real-time quotes
- Portfolio analysis and P&L calculations
- Market news and trends
- Technical analysis
- Investment recommendations
- Risk assessment
- Sector analysis
- Crypto and commodities
- Forex rates

Guidelines:
- Give specific stock symbols when making recommendations
- Use current market data when available
- Keep responses concise but informative
- Use emojis appropriately
- Be honest when you don't have current data
- Always cite sources when possible
- If asked about a stock not in the list, try to help using your general knowledge"""


def ask_ai(query, exchange="NSE", stock_list="default", context=""):
    system_prompt = build_system_prompt(exchange, stock_list)
    full_prompt = f"{context}\n\nUser: {query}\n\nAssistant:"
    return llm.chat(full_prompt, system_prompt)


def is_ai_available():
    return llm.is_available()
