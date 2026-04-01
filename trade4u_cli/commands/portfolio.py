import click
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime
from trade4u_cli.commands.price import get_stock_quote

console = Console()
DATA_DIR = Path.home() / ".trade4u"
DATA_DIR.mkdir(exist_ok=True)
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"

def load_portfolio():
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE) as f:
            return json.load(f)
    return {"holdings": [], "cash": 0.0}

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)

@click.group(name="portfolio")
def portfolio_group():
    """Portfolio management and tracking"""
    pass

@portfolio_group.command()
@click.argument("symbol")
@click.argument("shares", type=float)
@click.argument("purchase_price", type=float)
@click.option("--date", default=None, help="Purchase date (YYYY-MM-DD)")
def add(symbol, shares, purchase_price, date):
    """Add SHARES of SYMBOL at PURCHASE_PRICE to portfolio"""
    portfolio = load_portfolio()
    holding = {
        "symbol": symbol.upper(),
        "shares": shares,
        "purchase_price": purchase_price,
        "purchase_date": date or datetime.now().strftime("%Y-%m-%d")
    }
    portfolio["holdings"].append(holding)
    save_portfolio(portfolio)
    console.print(f"[green]✓[/green] Added {shares} shares of {symbol.upper()} at ${purchase_price:.2f}")

@portfolio_group.command()
def show():
    """Display current portfolio with P&L"""
    portfolio = load_portfolio()
    holdings = portfolio.get("holdings", [])
    
    if not holdings:
        console.print("[yellow]Portfolio is empty. Add holdings with 'trade4u portfolio add'.[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Symbol", style="cyan", width=10)
    table.add_column("Shares", justify="right", width=8)
    table.add_column("Avg Cost", justify="right", width=10)
    table.add_column("Current", justify="right", width=10)
    table.add_column("Value", justify="right", width=12)
    table.add_column("P&L", justify="right", width=12)
    table.add_column("P&L %", justify="right", width=8)
    
    total_cost = 0
    total_value = 0
    
    for holding in holdings:
        quote = get_stock_quote(holding["symbol"])
        current_price = quote["price"] if quote else holding["purchase_price"]
        cost = holding["shares"] * holding["purchase_price"]
        value = holding["shares"] * current_price
        pnl = value - cost
        pnl_pct = (pnl / cost) * 100 if cost > 0 else 0
        
        total_cost += cost
        total_value += value
        
        color = "green" if pnl >= 0 else "red"
        table.add_row(
            holding["symbol"],
            f"{holding['shares']:.2f}",
            f"${holding['purchase_price']:.2f}",
            f"${current_price:.2f}",
            f"${value:,.2f}",
            f"[{color}]{pnl:+,.2f}[/{color}]",
            f"[{color}]{pnl_pct:+.2f}%[/{color}]"
        )
    
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
    pnl_color = "green" if total_pnl >= 0 else "red"
    
    console.print(f"\n[bold]Total Cost:[/bold] ${total_cost:,.2f}")
    console.print(f"[bold]Total Value:[/bold] ${total_value:,.2f}")
    console.print(f"[bold]Total P&L:[/bold] [{pnl_color}]{total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)[/{pnl_color}]")
    console.print(f"[bold]Cash:[/bold] ${portfolio.get('cash', 0):,.2f}")
    console.print(f"[bold]Portfolio + Cash:[/bold] ${total_value + portfolio.get('cash', 0):,.2f}\n")
    console.print(table)

@portfolio_group.command()
@click.argument("symbol")
@click.option("--all", "remove_all", is_flag=True, help="Remove all shares")
def remove(symbol, remove_all):
    """Remove shares of SYMBOL from portfolio"""
    portfolio = load_portfolio()
    original_len = len(portfolio["holdings"])
    portfolio["holdings"] = [h for h in portfolio["holdings"] if h["symbol"].upper() != symbol.upper()]
    
    if len(portfolio["holdings"]) < original_len:
        save_portfolio(portfolio)
        console.print(f"[green]✓[/green] Removed {symbol.upper()} from portfolio")
    else:
        console.print(f"[red]Error:[/red] {symbol.upper()} not found in portfolio")

@portfolio_group.command()
@click.argument("amount", type=float)
def addcash(amount):
    """Add cash to portfolio"""
    portfolio = load_portfolio()
    portfolio["cash"] = portfolio.get("cash", 0) + amount
    save_portfolio(portfolio)
    console.print(f"[green]✓[/green] Added ${amount:.2f} | Total cash: ${portfolio['cash']:.2f}")

@portfolio_group.command()
def summary():
    """Show portfolio summary and statistics"""
    portfolio = load_portfolio()
    holdings = portfolio.get("holdings", [])
    
    if not holdings:
        console.print("[yellow]No holdings to analyze.[/yellow]")
        return
    
    symbols = [h["symbol"] for h in holdings]
    quotes = {}
    for sym in symbols:
        q = get_stock_quote(sym)
        if q:
            quotes[sym] = q
    
    gains = []
    losses = []
    
    for h in holdings:
        if h["symbol"] in quotes:
            current = quotes[h["symbol"]]["price"]
            cost = h["purchase_price"]
            pnl_pct = ((current - cost) / cost) * 100
            if pnl_pct >= 0:
                gains.append((h["symbol"], pnl_pct))
            else:
                losses.append((h["symbol"], pnl_pct))
    
    gains.sort(key=lambda x: x[1], reverse=True)
    losses.sort(key=lambda x: x[1])
    
    console.print("\n[bold cyan]Top Gainers:[/bold cyan]")
    for sym, pct in gains[:5]:
        console.print(f"  {sym}: [green]+{pct:.2f}%[/green]")
    
    console.print("\n[bold cyan]Top Losers:[/bold cyan]")
    for sym, pct in losses[:5]:
        console.print(f"  {sym}: [red]{pct:.2f}%[/red]")
    
    console.print(f"\n[bold]Winners:[/bold] {len(gains)} | [bold]Losers:[/bold] {len(losses)}")
