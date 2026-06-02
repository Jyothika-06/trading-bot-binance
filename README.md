# Binance Futures Testnet Trading Bot

A clean, production-structured Python trading bot for the Binance USDM Futures Testnet.  
Supports **MARKET**, **LIMIT**, and **STOP_LIMIT** orders via a simple CLI.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── __main__.py        # Enables: python -m bot
│   ├── client.py          # Binance REST client (auth, signing, HTTP)
│   ├── orders.py          # Order placement logic + result formatting
│   ├── validators.py      # Input validation (symbol, side, qty, price)
│   ├── logging_config.py  # Rotating file + console log setup
│   └── cli.py             # argparse CLI entry point
├── logs/
│   └── trading_bot.log    # Sample log output (included)
├── README.md
└── requirements.txt
├── .gitignore
├── .env
```

---

## Setup

### 1. Get Testnet API Credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub account
3. Under **API Key**, generate a new key pair
4. Save both the **API Key** and **Secret Key**

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Python 3.9+ is recommended. No other external packages are required.

### 3. Set Environment Variables

```bash
export BINANCE_API_KEY=your_api_key_here
export BINANCE_API_SECRET=your_secret_key_here
```

On Windows (PowerShell):
```powershell
$env:BINANCE_API_KEY="your_api_key_here"
$env:BINANCE_API_SECRET="your_secret_key_here"
```

---

## How to Run

All commands are run from the `trading_bot/` directory.

### Check Connectivity

```bash
python -m bot ping
```

---

### Place a MARKET Order

```bash
# Buy 0.001 BTC at market price
python -m bot place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Sell 0.01 ETH at market price
python -m bot place --symbol ETHUSDT --side SELL --type MARKET --quantity 0.01
```

---

### Place a LIMIT Order

```bash
# Buy 0.001 BTC with a limit at $65,000
python -m bot place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 65000

# Sell 0.001 BTC with a limit at $72,000 (GTC by default)
python -m bot place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 72000

# With explicit time-in-force
python -m bot place --symbol BTCUSDT --side BUY --type LIMIT \
    --quantity 0.001 --price 65000 --tif IOC
```

---

### Place a STOP_LIMIT Order *(Bonus)*

A stop-limit triggers a limit order once the market hits the stop price.

```bash
# Buy 0.001 BTC: trigger at $69,500, fill at up to $70,000
python -m bot place --symbol BTCUSDT --side BUY --type STOP_LIMIT \
    --quantity 0.001 --price 70000 --stop-price 69500

# Sell 0.001 BTC: trigger at $64,000, fill at $63,500 minimum
python -m bot place --symbol BTCUSDT --side SELL --type STOP_LIMIT \
    --quantity 0.001 --price 63500 --stop-price 64000
```

---

### Custom Log Directory

```bash
python -m bot place --symbol BTCUSDT --side BUY --type MARKET \
    --quantity 0.001 --log-dir /tmp/my_logs
```

---

## Sample Output

```
=======================================================
  ORDER REQUEST SUMMARY
=======================================================
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
=======================================================

=======================================================
  ORDER RESPONSE
=======================================================
  Order ID     : 4723805
  Symbol       : BTCUSDT
  Side         : BUY
  Type         : MARKET
  Status       : FILLED
  Orig Qty     : 0.001
  Executed Qty : 0.001
  Avg Price    : 68245.10
=======================================================

✅  Order placed successfully! Order ID: 4723805
```

---

## Logging

All activity is logged to `logs/trading_bot.log` (rotated at 5 MB, 3 backups kept).

| Level   | Where          | What is logged                                      |
|---------|----------------|-----------------------------------------------------|
| DEBUG   | File only      | Full request params (signature hidden), raw responses |
| INFO    | File + Console | Order intent, success confirmation, connectivity    |
| WARNING | File + Console | Unexpected but recoverable situations               |
| ERROR   | File + Console | API rejections, network failures, validation errors |

---

## Error Handling

| Scenario                        | Behaviour                                                    |
|---------------------------------|--------------------------------------------------------------|
| Missing env vars                | Clear message + exit code 1 before any network call          |
| Invalid CLI input               | Validation error printed; exit code 2                        |
| Binance API error (e.g. -1111)  | Error code + message printed and logged; exit code 1         |
| Network timeout / DNS failure   | Exception logged with traceback; exit code 1                 |
| Wrong price precision           | Binance returns -1111; caught and surfaced cleanly           |

---

## Assumptions

- **Testnet only**: The base URL is hard-coded to `https://testnet.binancefuture.com`.  
  To use mainnet, change `TESTNET_BASE_URL` in `bot/client.py`.

- **No `python-binance` library**: Uses `requests` only, so behaviour is fully transparent  
  and there are no third-party library versioning issues.

- **Quantity precision**: The bot sends the quantity and price exactly as entered.  
  Binance will reject orders that violate the symbol's `LOT_SIZE` or `PRICE_FILTER`  
  filters. Check `GET /fapi/v1/exchangeInfo` for the exact step sizes.

- **Credentials via environment variables**: API credentials are never stored on disk.

---

## Bonus Feature

**STOP_LIMIT orders** are implemented as the third order type, mapped to Binance's  
`STOP` futures order type (which is a stop-limit, not a stop-market).

---

## Requirements

```
requests>=2.31.0
```

Python standard library modules used: `argparse`, `hashlib`, `hmac`, `logging`,  
`decimal`, `os`, `sys`, `time`, `re`, `urllib.parse`.
