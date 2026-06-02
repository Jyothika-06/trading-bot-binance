"""
CLI entry point for the Binance Futures Testnet trading bot.

Usage examples:
    python -m bot.cli place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
    python -m bot.cli place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 80000
    python -m bot.cli place --symbol BTCUSDT --side BUY --type STOP_LIMIT \\
        --quantity 0.001 --price 95000 --stop-price 94500
"""

from __future__ import annotations

import argparse
import os
import sys

from .client import BinanceAPIError, BinanceClient
from .logging_config import setup_logging
from .orders import place_order, print_order_response
from .validators import validate_all

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_credentials() -> tuple[str, str]:
    """
    Load API key and secret from environment variables.

    Raises SystemExit with a helpful message if either is missing.
    """
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    missing = []
    if not api_key:
        missing.append("BINANCE_API_KEY")
    if not api_secret:
        missing.append("BINANCE_API_SECRET")

    if missing:
        print(
            f"\n[ERROR] Missing environment variable(s): {', '.join(missing)}\n\n"
            "Set them before running:\n"
            "  export BINANCE_API_KEY=<your_key>\n"
            "  export BINANCE_API_SECRET=<your_secret>\n",
            file=sys.stderr,
        )
        sys.exit(1)

    return api_key, api_secret


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Binance Futures Testnet trading bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- place ----
    place_parser = subparsers.add_parser(
        "place",
        help="Place an order on Binance Futures Testnet.",
    )
    place_parser.add_argument(
        "--symbol", "-s",
        required=True,
        help="Trading pair symbol (e.g. BTCUSDT).",
    )
    place_parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        help="Order side: BUY or SELL.",
    )
    place_parser.add_argument(
        "--type", "-t",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
        help="Order type: MARKET, LIMIT, or STOP_LIMIT.",
    )
    place_parser.add_argument(
        "--quantity", "-q",
        required=True,
        help="Order quantity (base asset).",
    )
    place_parser.add_argument(
        "--price", "-p",
        default=None,
        help="Limit price (required for LIMIT and STOP_LIMIT).",
    )
    place_parser.add_argument(
        "--stop-price",
        dest="stop_price",
        default=None,
        help="Stop/trigger price (required for STOP_LIMIT).",
    )
    place_parser.add_argument(
        "--tif",
        dest="time_in_force",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time-in-force for LIMIT orders (default: GTC).",
    )
    place_parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for log files (default: logs/).",
    )

    # ---- ping ----
    ping_parser = subparsers.add_parser(
        "ping",
        help="Check connectivity to Binance Futures Testnet.",
    )
    ping_parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for log files (default: logs/).",
    )

    return parser


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def cmd_place(args: argparse.Namespace) -> int:
    """Handle the 'place' sub-command. Returns exit code."""
    import logging
    logger = logging.getLogger(__name__)

    # Validate all inputs first
    try:
        validated = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        print(f"\n[VALIDATION ERROR] {exc}\n", file=sys.stderr)
        logger.error("Input validation failed: %s", exc)
        return 2

    api_key, api_secret = _get_credentials()
    client = BinanceClient(api_key=api_key, api_secret=api_secret)

    # Optional: verify testnet reachability
    if not client.ping():
        print(
            "\n[ERROR] Cannot reach Binance Futures Testnet. "
            "Check your internet connection.\n",
            file=sys.stderr,
        )
        return 1

    try:
        result = place_order(
            client=client,
            symbol=validated["symbol"],
            side=validated["side"],
            order_type=validated["order_type"],
            quantity=validated["quantity"],
            price=validated["price"],
            stop_price=validated["stop_price"],
            time_in_force=args.time_in_force,
        )
    except BinanceAPIError as exc:
        print(f"\n[API ERROR] {exc}\n", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[ERROR] Unexpected failure: {exc}\n", file=sys.stderr)
        return 1

    print_order_response(result)
    print(f"\n✅  Order placed successfully! Order ID: {result['orderId']}\n")
    logger.info("Order placed successfully. orderId=%s", result["orderId"])
    return 0


def cmd_ping(args: argparse.Namespace) -> int:
    """Handle the 'ping' sub-command. Returns exit code."""
    api_key, api_secret = _get_credentials()
    client = BinanceClient(api_key=api_key, api_secret=api_secret)
    if client.ping():
        print("\n✅  Binance Futures Testnet is reachable.\n")
        return 0
    else:
        print("\n❌  Cannot reach Binance Futures Testnet.\n", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Boot logging (done after parsing so we respect --log-dir)
    log_dir = getattr(args, "log_dir", "logs")
    setup_logging(log_dir=log_dir)

    import logging
    logger = logging.getLogger(__name__)
    logger.info("trading-bot started | command=%s", args.command)

    dispatch = {
        "place": cmd_place,
        "ping": cmd_ping,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()
