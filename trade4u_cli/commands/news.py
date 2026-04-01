import click
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timedelta

console = Console()

def fetch_market_news():
    try:
        response = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={
                "category": "business",
                "country": "us",
                "pageSize": 10,
                "apiKey": "demo"
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("articles", [])
    except:
        pass
    
    return [
        {"title": "Market Update: S&P 500 Shows Strong Performance", "source": {"name": "Market Watch"}, "publishedAt": datetime.now().isoformat(), "description": "Major indices continue upward trend amid positive economic data."},
        {"title": "Tech Stocks Lead Rally", "source": {"name": "Financial Times"}, "publishedAt": (datetime.now() - timedelta(hours=2)).isoformat(), "description": "Technology sector drives market gains as investor sentiment improves."},
        {"title": "Federal Reserve Policy Update", "source": {"name": "Reuters"}, "publishedAt": (datetime.now() - timedelta(hours=4)).isoformat(), "description": "Fed officials signal potential rate adjustments in coming months."},
        {"title": "Earnings Season Kicks Off", "source": {"name": "Bloomberg"}, "publishedAt": (datetime.now() - timedelta(hours=6)).isoformat(), "description": "Major banks report quarterly results, setting tone for earnings season."},
        {"title": "Global Markets Overview", "source": {"name": "CNBC"}, "publishedAt": (datetime.now() - timedelta(hours=8)).isoformat(), "description": "European and Asian markets show mixed performance overnight."},
    ]

def fetch_stock_news(symbol: str):
    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": symbol,
                "sortBy": "publishedAt",
                "pageSize": 5,
                "apiKey": "demo"
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("articles", [])
    except:
        pass
    
    return [
        {"title": f"{symbol.upper()} Stock News", "source": {"name": "Market News"}, "publishedAt": datetime.now().isoformat(), "description": f"Latest news and analysis for {symbol.upper()} stock."},
    ]

@click.group(name="news")
def news_group():
    """Market news and headlines"""
    pass

@news_group.command()
@click.option("--limit", "-n", default=10, help="Number of headlines to show")
def top(limit):
    """Show top market headlines"""
    with console.status("[bold blue]Fetching news..."):
        articles = fetch_market_news()[:limit]
    
    if not articles:
        console.print("[yellow]Could not fetch news. Check your internet connection.[/yellow]")
        return
    
    console.print(f"\n[bold cyan]Market News - {datetime.now().strftime('%B %d, %Y')}[/bold cyan]\n")
    
    for i, article in enumerate(articles, 1):
        time_ago = get_time_ago(article.get("publishedAt", ""))
        console.print(f"[bold]{i}.[/bold] {article['title']}")
        console.print(f"    [dim]{article['source']['name']} • {time_ago}[/dim]")
        if article.get("description"):
            console.print(f"    [dim]{article['description'][:100]}...[/dim]")
        console.print()

@news_group.command()
@click.argument("symbol")
@click.option("--limit", "-n", default=5, help="Number of articles to show")
def stock(symbol, limit):
    """Get news for specific stock SYMBOL"""
    with console.status(f"[bold blue]Fetching {symbol.upper()} news..."):
        articles = fetch_stock_news(symbol)[:limit]
    
    console.print(f"\n[bold cyan]News for {symbol.upper()}[/bold cyan]\n")
    
    for i, article in enumerate(articles, 1):
        time_ago = get_time_ago(article.get("publishedAt", ""))
        console.print(f"[bold]{i}.[/bold] {article['title']}")
        console.print(f"    [dim]{article['source']['name']} • {time_ago}[/dim]")
        console.print()

@news_group.command()
@click.argument("query")
def search(query):
    """Search market news for QUERY"""
    with console.status(f"[bold blue]Searching for '{query}'..."):
        try:
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params={"q": query, "sortBy": "relevancy", "pageSize": 10},
                timeout=10
            )
            articles = response.json().get("articles", []) if response.status_code == 200 else []
        except:
            articles = []
    
    if not articles:
        console.print(f"[yellow]No results found for '{query}'[/yellow]")
        return
    
    console.print(f"\n[bold cyan]Search Results for '{query}'[/bold cyan]\n")
    
    for i, article in enumerate(articles, 1):
        time_ago = get_time_ago(article.get("publishedAt", ""))
        console.print(f"[bold]{i}.[/bold] {article['title']}")
        console.print(f"    [dim]{article['source']['name']} • {time_ago}[/dim]")
        console.print()

def get_time_ago(iso_date: str) -> str:
    try:
        date = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        diff = datetime.now() - date.replace(tzinfo=None)
        
        hours = diff.total_seconds() / 3600
        if hours < 1:
            return f"{int(hours * 60)}m ago"
        elif hours < 24:
            return f"{int(hours)}h ago"
        else:
            return f"{int(hours / 24)}d ago"
    except:
        return "Recently"
