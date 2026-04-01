# Trade4U - Your AI Trading Assistant

A smart CLI chatbot for stock trading, portfolio management, and market analysis.

## Installation

```bash
pip install trade4u
```

## Usage

```bash
trade4u
```

Or run in chat mode:

```bash
python -m trade4u_cli.main
```

## Chat Commands

Just type naturally! Examples:

| You Say | What Trade4U Does |
|---------|------------------|
| `What's Apple's stock price?` | Gets AAPL quote |
| `lookup AAPL` | Gets AAPL quote |
| `my portfolio` | Shows holdings & P&L |
| `add TSLA 10 250` | Adds TSLA to portfolio |
| `alert AAPL 300` | Sets price alert |
| `news` | Top market news |
| `chart NVDA` | ASCII chart |
| `which stock to buy` | Stock recommendations |
| `-settings` | Configure exchange, stock lists, etc. |
| `help` | Show all commands |
| `exit` | Quit |

## Features

- **Natural Language** - Talk like a human, not a robot
- **Multi-Exchange** - Support for NSE (India), NYSE (US)
- **Stock Lists** - default, nifty50, tech, finance, midcap
- **Portfolio Tracking** - Track holdings, P&L, cash
- **Price Alerts** - Get notified of price targets
- **Stock Recommendations** - Buy/sell suggestions
- **Market News** - Latest headlines and updates
- **Stock Charts** - ASCII price charts
- **Settings** - Customize exchange, currency, timezone

## Settings

Run `-settings` to configure:
- **Exchange**: NSE, NYSE, NASDAQ
- **Stock List**: default, nifty50, tech, finance, midcap
- **Timezone**: Asia/Kolkata, America/New_York, etc.
- **Currency**: INR, USD, EUR

## Data Storage

Your data is saved in `~/.trade4u/`:
- `portfolio.json` - Your holdings
- `alerts.json` - Price alerts
- `settings.json` - Your settings

## Examples

```
You: what's Tesla at?
Trade4U: 📈 TSLA - Tesla, Inc.
         Price: $371.75
         Change: +16.47 (+4.64%)

You: show my portfolio
Trade4U: 💼 Your Portfolio
         - AAPL: 10 shares @ $200 → $253.79
           🟢 +$537.90 (+26.90%)

You: -settings
⚙️ Current Settings:
  📌 Exchange: NSE
  📋 Stock List: nifty50
  🌐 Timezone: Asia/Kolkata
  💰 Currency: INR
  📊 Display: compact
  🔔 Alerts: Enabled
```

## Requirements

- Python 3.10+
- rich (for beautiful terminal output)
