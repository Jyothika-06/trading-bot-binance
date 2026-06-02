"""
Binance Futures Testnet REST client.

Handles authentication (HMAC-SHA256 signatures), request sending,
response parsing, and low-level error normalisation.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds
RECV_WINDOW = 5000    # ms


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or an error body."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceClient:
    """
    Thin, authenticated wrapper around the Binance USDM Futures REST API.

    Only the endpoints required by this bot are implemented; everything else
    can be added by following the same pattern.
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = TESTNET_BASE_URL) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")

        self._session = requests.Session()
        self._session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "trading-bot/1.0",
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Append a timestamp and HMAC-SHA256 signature to *params*."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> Dict[str, Any]:
        """
        Send an HTTP request and return the parsed JSON body.

        Logs the outgoing request (sanitised) and raw response at DEBUG level.
        Raises BinanceAPIError on any API-level failure.
        Raises requests.RequestException on network-level failures.
        """
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{self.base_url}{path}"

        # Log sanitised request (hide signature)
        log_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("REQUEST  %s %s  params=%s", method.upper(), path, log_params)

        try:
            if method.upper() == "GET":
                response = self._session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            elif method.upper() == "POST":
                response = self._session.post(url, data=params, timeout=DEFAULT_TIMEOUT)
            elif method.upper() == "DELETE":
                response = self._session.delete(url, params=params, timeout=DEFAULT_TIMEOUT)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise
        except requests.Timeout as exc:
            logger.error("Request timed out after %ss: %s", DEFAULT_TIMEOUT, exc)
            raise

        logger.debug(
            "RESPONSE %s %s  status=%s  body=%s",
            method.upper(), path, response.status_code, response.text[:500],
        )

        # Parse JSON (Binance always returns JSON)
        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response: %s", response.text[:200])
            response.raise_for_status()
            raise

        # Binance error bodies have a "code" key that is negative
        if isinstance(data, dict) and "code" in data and data["code"] < 0:
            raise BinanceAPIError(code=data["code"], message=data.get("msg", "Unknown error"))

        if not response.ok:
            raise BinanceAPIError(code=response.status_code, message=response.text[:200])

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return True if the testnet is reachable."""
        try:
            self._request("GET", "/fapi/v1/ping", signed=False)
            return True
        except Exception as exc:
            logger.error("Ping failed: %s", exc)
            return False

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch full exchange info (symbol filters, tick sizes, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def get_account(self) -> Dict[str, Any]:
        """Fetch account details (balance, positions, etc.)."""
        return self._request("GET", "/fapi/v2/account")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """
        Place a new order on Binance USDM Futures.

        Args:
            symbol:        Trading pair, e.g. 'BTCUSDT'.
            side:          'BUY' or 'SELL'.
            order_type:    'MARKET', 'LIMIT', or 'STOP' (stop-limit).
            quantity:      Order size as a string.
            price:         Limit price (required for LIMIT / STOP).
            stop_price:    Trigger price (required for STOP).
            time_in_force: 'GTC', 'IOC', or 'FOK' (ignored for MARKET).

        Returns:
            Raw order response dict from Binance.
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type if order_type != "STOP_LIMIT" else "STOP",
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force

        elif order_type == "STOP_LIMIT":
            params["price"] = price          # limit fill price
            params["stopPrice"] = stop_price  # trigger price
            params["timeInForce"] = time_in_force

        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s stopPrice=%s",
            side, order_type, symbol, quantity, price, stop_price,
        )
        return self._request("POST", "/fapi/v1/order", params=params)

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order by ID."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling order %s on %s", order_id, symbol)
        return self._request("DELETE", "/fapi/v1/order", params=params)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query a single order by ID."""
        return self._request("GET", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id})
