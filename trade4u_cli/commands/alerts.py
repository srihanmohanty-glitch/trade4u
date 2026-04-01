import click
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from datetime import datetime
from trade4u_cli.commands.price import get_stock_quote

console = Console()
DATA_DIR = Path.home() / ".trade4u"
DATA_DIR.mkdir(exist_ok=True)
ALERTS_FILE = DATA_DIR / "alerts.json"

def load_alerts():
    if ALERTS_FILE.exists():
        with open(ALERTS_FILE) as f:
            return json.load(f)
    return []

def save_alerts(alerts):
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)

@click.group(name="alerts")
def alerts_group():
    """Manage price alerts"""
    pass

@alerts_group.command()
@click.argument("symbol")
@click.argument("price", type=float)
@click.option("--above", "direction", flag_value="above", default=True, help="Alert when price goes above")
@click.option("--below", "direction", flag_value="below", help="Alert when price goes below")
@click.option("--note", default="", help="Add a note to this alert")
def add(symbol, price, direction, note):
    """Add an alert for SYMBOL at PRICE (above or below)"""
    alerts = load_alerts()
    alert = {
        "id": len(alerts) + 1,
        "symbol": symbol.upper(),
        "target_price": price,
        "direction": direction,
        "note": note,
        "created_at": datetime.now().isoformat(),
        "triggered": False
    }
    alerts.append(alert)
    save_alerts(alerts)
    console.print(f"[green]✓[/green] Alert added: {symbol.upper()} {direction} ${price:.2f}")

@alerts_group.command()
def list():
    """List all active alerts"""
    alerts = [a for a in load_alerts() if not a["triggered"]]
    
    if not alerts:
        console.print("[yellow]No active alerts.[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", width=4)
    table.add_column("Symbol", style="cyan")
    table.add_column("Condition", width=12)
    table.add_column("Target", justify="right")
    table.add_column("Note")
    
    for alert in alerts:
        condition = f"{alert['direction'].title()} ${alert['target_price']:.2f}"
        table.add_row(
            str(alert["id"]),
            alert["symbol"],
            condition,
            "",
            alert["note"] or "-"
        )
    
    console.print(table)

@alerts_group.command()
@click.argument("alert_id", type=int)
def remove(alert_id):
    """Remove alert by ID"""
    alerts = load_alerts()
    original_len = len(alerts)
    alerts = [a for a in alerts if a["id"] != alert_id]
    
    if len(alerts) < original_len:
        save_alerts(alerts)
        console.print(f"[green]✓[/green] Alert {alert_id} removed")
    else:
        console.print(f"[red]Error:[/red] Alert {alert_id} not found")

@alerts_group.command()
def check():
    """Check all alerts against current prices"""
    alerts = load_alerts()
    triggered = []
    
    console.print("[bold]Checking alerts...[/bold]\n")
    
    for alert in alerts:
        if alert["triggered"]:
            continue
        
        quote = get_stock_quote(alert["symbol"])
        if not quote:
            continue
        
        current = quote["price"]
        target = alert["target_price"]
        direction = alert["direction"]
        
        should_trigger = (
            (direction == "above" and current >= target) or
            (direction == "below" and current <= target)
        )
        
        if should_trigger:
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now().isoformat()
            alert["triggered_price"] = current
            triggered.append(alert)
            console.print(f"[bold red]🔔 TRIGGERED:[/bold red] {alert['symbol']} {direction} ${target:.2f}")
            console.print(f"   Current price: ${current:.2f} | Note: {alert['note'] or 'N/A'}\n")
    
    if triggered:
        save_alerts(alerts)
    
    active = [a for a in alerts if not a["triggered"]]
    if not triggered:
        console.print("[yellow]No alerts triggered this check.[/yellow]")
    console.print(f"\nActive alerts: {len(active)} | Triggered: {len(triggered)}")
