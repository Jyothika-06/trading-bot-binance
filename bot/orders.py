"""
Order placement logic layer.

Sits between the CLI and the raw BinanceClient; handles formatting,
precision normalisation, and human-readable result rendering.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from .client import BinanceClient, BinanceAPIError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Precision helpers
# ---------------------------------------------------------------------------

def _fmt(value: Optional[Decimal]) -> Optional[str]:
    """Format a Decimal as a plain string without trailing zeros (or None)."""
    if value is None:
        return None
    # Normalise removes trailing zeros: Decimal('1.10') -> '1.1'
    return str(value.normalize())


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------

def _format_order_result(response: dict) -> dict:
    """
    Extract the most useful fields from a raw Binance order response.

    Returns a normalised dict that is logged and printed to the user.
    """
    return {
        "orderId":     response.get("orderId"),
        "symbol":      response.get("symbol"),
        "side":        response.get("side"),
        "type":        response.get("type"),
        "status":      response.get("status"),
        "origQty":     response.get("origQty"),
        "executedQty": response.get("executedQty"),
        "avgPrice":    response.get("avgPrice"),
        "price":       response.get("price"),
        "stopPrice":   response.get("stopPrice"),
        "timeInForce": response.get("timeInForce"),
        "updateTime":  response.get("updateTime"),
    }


def print_order_summary(params: dict) -> None:
    """Print a human-readable pre-flight summary of the order to stdout."""
    print("\n" + "=" * 55)
    print("  ORDER REQUEST SUMMARY")
    print("=" * 55)
    print(f"  Symbol     : {params['symbol']}")
    print(f"  Side       : {params['side']}")
    print(f"  Type       : {params['order_type']}")
    print(f"  Quantity   : {params['quantity']}")
    if params.get("price"):
        print(f"  Price      : {params['price']}")
    if params.get("stop_price"):
        print(f"  Stop Price : {params['stop_price']}")
    print("=" * 55)


def print_order_response(result: dict) -> None:
    """Print a human-readable summary of the Binance order response."""
    print("\n" + "=" * 55)
    print("  ORDER RESPONSE")
    print("=" * 55)
    print(f"  Order ID     : {result['orderId']}")
    print(f"  Symbol       : {result['symbol']}")
    print(f"  Side         : {result['side']}")
    print(f"  Type         : {result['type']}")
    print(f"  Status       : {result['status']}")
    print(f"  Orig Qty     : {result['origQty']}")
    print(f"  Executed Qty : {result['executedQty']}")
    avg = result.get("avgPrice")
    if avg and avg != "0":
        print(f"  Avg Price    : {avg}")
    lim = result.get("price")
    if lim and lim != "0":
        print(f"  Limit Price  : {lim}")
    stp = result.get("stopPrice")
    if stp and stp != "0":
        print(f"  Stop Price   : {stp}")
    tif = result.get("timeInForce")
    if tif:
        print(f"  TimeInForce  : {tif}")
    print("=" * 55)


# ---------------------------------------------------------------------------
# Core placement functions
# ---------------------------------------------------------------------------

def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
) -> dict:
    """
    Place a MARKET order and return the formatted result.

    Raises:
        BinanceAPIError: On any API-level rejection.
        requests.RequestException: On network failure.
    """
    params = {
        "symbol": symbol,
        "side": side,
        "order_type": "MARKET",
        "quantity": quantity,
        "price": None,
        "stop_price": None,
    }
    print_order_summary(params)

    logger.info("Submitting MARKET order: %s %s qty=%s", side, symbol, quantity)
    raw = client.place_order(
        symbol=symbol,
        side=side,
        order_type="MARKET",
        quantity=_fmt(quantity),
    )
    result = _format_order_result(raw)
    logger.info("MARKET order placed successfully: %s", result)
    return result


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    time_in_force: str = "GTC",
) -> dict:
    """
    Place a LIMIT order and return the formatted result.

    Raises:
        BinanceAPIError: On any API-level rejection.
        requests.RequestException: On network failure.
    """
    params = {
        "symbol": symbol,
        "side": side,
        "order_type": "LIMIT",
        "quantity": quantity,
        "price": price,
        "stop_price": None,
    }
    print_order_summary(params)

    logger.info(
        "Submitting LIMIT order: %s %s qty=%s @ %s", side, symbol, quantity, price
    )
    raw = client.place_order(
        symbol=symbol,
        side=side,
        order_type="LIMIT",
        quantity=_fmt(quantity),
        price=_fmt(price),
        time_in_force=time_in_force,
    )
    result = _format_order_result(raw)
    logger.info("LIMIT order placed successfully: %s", result)
    return result


def place_stop_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    stop_price: Decimal,
    time_in_force: str = "GTC",
) -> dict:
    """
    Place a STOP (stop-limit) order and return the formatted result.

    On Binance Futures the order type is 'STOP'; it acts as a stop-limit
    once *stopPrice* is touched.

    Raises:
        BinanceAPIError: On any API-level rejection.
        requests.RequestException: On network failure.
    """
    params = {
        "symbol": symbol,
        "side": side,
        "order_type": "STOP_LIMIT",
        "quantity": quantity,
        "price": price,
        "stop_price": stop_price,
    }
    print_order_summary(params)

    logger.info(
        "Submitting STOP_LIMIT order: %s %s qty=%s limit=%s stop=%s",
        side, symbol, quantity, price, stop_price,
    )
    raw = client.place_order(
        symbol=symbol,
        side=side,
        order_type="STOP_LIMIT",
        quantity=_fmt(quantity),
        price=_fmt(price),
        stop_price=_fmt(stop_price),
        time_in_force=time_in_force,
    )
    result = _format_order_result(raw)
    logger.info("STOP_LIMIT order placed successfully: %s", result)
    return result


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    time_in_force: str = "GTC",
) -> dict:
    """
    Unified dispatcher — routes to the correct order function.

    Returns the formatted order result dict on success, or re-raises on failure.
    """
    try:
        if order_type == "MARKET":
            return place_market_order(client, symbol, side, quantity)
        elif order_type == "LIMIT":
            return place_limit_order(client, symbol, side, quantity, price, time_in_force)
        elif order_type == "STOP_LIMIT":
            return place_stop_limit_order(
                client, symbol, side, quantity, price, stop_price, time_in_force
            )
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

    except BinanceAPIError as exc:
        logger.error("API rejected the order: code=%s message=%s", exc.code, exc.message)
        raise
    except Exception as exc:
        logger.exception("Unexpected error while placing order: %s", exc)
        raise
