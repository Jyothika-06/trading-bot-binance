"""
Input validation for trading bot CLI arguments.
All validation raises ValueError with a descriptive message on failure.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}

# Binance symbol: 2–10 uppercase letters/digits ending in a quote asset
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{3,12}$")


def validate_symbol(symbol: str) -> str:
    """Return uppercased symbol or raise ValueError."""
    symbol = symbol.strip().upper()
    if not SYMBOL_PATTERN.match(symbol):
        raise ValueError(
            f"Invalid symbol '{symbol}'. "
            "Must be 3–12 uppercase alphanumeric characters (e.g. BTCUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    """Return uppercased side or raise ValueError."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Return uppercased order type or raise ValueError."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Parse and validate quantity; must be a positive number."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a numeric value.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {qty}.")
    return qty


def validate_price(price: Optional[str | float], required: bool = False) -> Optional[Decimal]:
    """
    Parse and validate price.

    Args:
        price: Price value (string or float) or None.
        required: If True, raises ValueError when price is None/empty.
    """
    if price is None or str(price).strip() == "":
        if required:
            raise ValueError("Price is required for LIMIT and STOP_LIMIT orders.")
        return None
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Invalid price '{price}'. Must be a numeric value.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {p}.")
    return p


def validate_stop_price(
    stop_price: Optional[str | float], required: bool = False
) -> Optional[Decimal]:
    """Parse and validate stop price for STOP_LIMIT orders."""
    if stop_price is None or str(stop_price).strip() == "":
        if required:
            raise ValueError("Stop price is required for STOP_LIMIT orders.")
        return None
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Invalid stop price '{stop_price}'. Must be a numeric value.")
    if sp <= 0:
        raise ValueError(f"Stop price must be greater than zero, got {sp}.")
    return sp


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
) -> dict:
    """
    Run all validations and return a clean params dict.

    Returns:
        dict with keys: symbol, side, order_type, quantity, price, stop_price
    """
    order_type_clean = validate_order_type(order_type)
    needs_price = order_type_clean in ("LIMIT", "STOP_LIMIT")
    needs_stop = order_type_clean == "STOP_LIMIT"

    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": order_type_clean,
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, required=needs_price),
        "stop_price": validate_stop_price(stop_price, required=needs_stop),
    }
