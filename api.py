import asyncio
from typing import List, Sequence

BASE_URL = "https://fapi.binance.com"
KLINES_ENDPOINT = "/fapi/v1/klines"
MAX_LIMIT = 1500
RATE_LIMIT_SLEEP = 60  # секунд ожидания при Rate Limit


async def get_klines(
    session,
    symbol: str,
    interval: str,
    start: int,
    end: int,
    limit: int = MAX_LIMIT,
) -> List[Sequence]:
    """Получение свечей с Binance Futures REST API."""
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": min(limit, MAX_LIMIT),
        "startTime": int(start),
        "endTime": int(end),
    }

    while True:
        async with session.get(f"{BASE_URL}{KLINES_ENDPOINT}", params=params) as response:
            if response.status == 429:
                print(
                    f"[{symbol} {interval}] HTTP 429 (слишком частые запросы). "
                    f"Ждём {RATE_LIMIT_SLEEP} сек."
                )
                await asyncio.sleep(RATE_LIMIT_SLEEP)
                continue

            raw = await response.json()

        if isinstance(raw, dict) and raw.get("code"):
            code = raw.get("code")
            message = raw.get("msg", "")
            if code in (-1003, -1015):
                print(
                    f"[{symbol} {interval}] Rate limit {code}: {message}. "
                    f"Ждём {RATE_LIMIT_SLEEP} сек."
                )
                await asyncio.sleep(RATE_LIMIT_SLEEP)
                continue

            raise RuntimeError(f"Binance error {code}: {message}")

        if not isinstance(raw, list):
            raise RuntimeError(f"Unexpected response: {raw}")

        return raw