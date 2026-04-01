import click
import requests
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.live import Live
import time

console = Console()
DATA_DIR = Path.home() / ".trade4u"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

def get_stock_quote(symbol: str):
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
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose") or price
        change = price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0
        return {
            "symbol": symbol.upper(),
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "prev_close": prev_close,
            "market": meta.get("marketState", "CLOSED")
        }
    except Exception as e:
        return None

@click.group(name="price")
def price_group():
    """Stock price lookup and tracking"""
    pass

@price_group.command()
@click.argument("symbol")
def lookup(symbol):
    """Get current stock price for SYMBOL"""
    with console.status(f"[bold blue]Fetching {symbol.upper()}..."):
        quote = get_stock_quote(symbol)
    
    if quote:
        console.print(f"\n[bold cyan]{quote['symbol']}[/bold cyan] - {quote['market']}\n")
        console.print(f"  Price:      [green]${quote['price']:.2f}[/green]")
        console.print(f"  Change:     {'[green]' if quote['change'] >= 0 else '[red]'}{quote['change']:+.2f} ({quote['change_pct']:+.2f}%)[/]")
        console.print(f"  Prev Close: ${quote['prev_close']:.2f}\n")
    else:
        console.print(f"[red]Error:[/red] Could not fetch data for {symbol}. Check symbol and try again.")

@price_group.command()
@click.argument("symbols", nargs=-1)
def watch(symbols):
    """Watch multiple stocks in real-time (press Ctrl+C to exit)"""
    if not symbols:
        console.print("[red]Error:[/red] Please provide at least one symbol")
        return
    
    console.print(f"[bold]Watching:[/bold] {', '.join(s.upper() for s in symbols)}")
    console.print("Press Ctrl+C to exit\n")
    
    try:
        with Live(refresh_per_second=1) as live:
            while True:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Symbol", style="cyan", width=10)
                table.add_column("Price", justify="right", width=12)
                table.add_column("Change", justify="right", width=12)
                table.add_column("%", justify="right", width=10)
                
                for symbol in symbols:
                    quote = get_stock_quote(symbol)
                    if quote:
                        color = "green" if quote['change'] >= 0 else "red"
                        table.add_row(
                            quote['symbol'],
                            f"${quote['price']:.2f}",
                            f"[{color}]{quote['change']:+.2f}[/{color}]",
                            f"[{color}]{quote['change_pct']:+.2f}%[/{color}]"
                        )
                    else:
                        table.add_row(symbol.upper(), "[red]Error[/red]", "-", "-")
                
                live.update(table)
                time.sleep(10)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching.[/yellow]")

@price_group.command()
@click.argument("symbol")
def chart(symbol):
    """Show simple ASCII chart for SYMBOL"""
    try:
        response = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1h", "range": "1d"},
            headers=HEADERS,
            timeout=10
        )
        data = response.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"][-30:]
        closes = result["indicators"]["quote"][0]["close"][-30:]
        
        min_p, max_p = min(closes), max(closes)
        scale = 10 / (max_p - min_p) if max_p != min_p else 1
        
        console.print(f"\n[bold cyan]{symbol.upper()}[/bold cyan] - Last 30 data points\n")
        for i, (ts, close) in enumerate(zip(timestamps, closes)):
            bar_len = int((close - min_p) * scale) + 1
            console.print(f"  {'█' * bar_len} ${close:.2f}")
    except Exception as e:
        console.print(f"[red]Error:[/red] Could not fetch chart data")
