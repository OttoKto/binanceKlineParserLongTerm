import asyncio
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

import aiohttp

from api import get_klines
from settings import DATE_FORMAT, DATE_RANGE, LOOKBACK_DAYS, SYMBOL, TIMEFRAME

if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

MAX_CANDLES_PER_REQUEST = 1500
ERROR_SLEEP_SECONDS = 60

TIMEFRAME_TO_SECONDS: Dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
    "1M": 2592000,
}

FALLBACK_DATE_FORMATS: Tuple[str, ...] = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class CandleFetcher:
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        lookback_days: Optional[int] = None,
        date_range: Optional[Dict[str, str]] = None,
        date_format: Optional[str] = None,
    ) -> None:
        if timeframe not in TIMEFRAME_TO_SECONDS:
            raise ValueError(f"Неизвестный таймфрейм: {timeframe}")

        self.symbol = symbol.replace("_", "").upper()
        self.timeframe = timeframe
        self.timeframe_seconds = TIMEFRAME_TO_SECONDS[timeframe]
        self.lookback_days = lookback_days
        self.date_range = date_range or {}
        self.date_formats = self._build_format_list(date_format)

    async def fetch(self) -> List[Dict[str, Any]]:
        start_ts, end_ts = self._resolve_time_bounds()
        if start_ts >= end_ts:
            return []

        start_ms = start_ts * 1000
        end_ms = end_ts * 1000

        aggregated: Dict[int, Dict[str, Any]] = {}

        async with aiohttp.ClientSession() as session:
            cursor = start_ms
            while cursor < end_ms:
                chunk = await self._fetch_chunk(
                    session=session,
                    start=cursor,
                    end=end_ms,
                )
                if not chunk:
                    break

                formatted = [self._format_candle(raw) for raw in chunk]
                for candle in formatted:
                    aggregated[candle["open_time"]] = candle

                last_close = formatted[-1]["close_time"]
                next_cursor = last_close + 1
                if next_cursor <= cursor:
                    break
                cursor = next_cursor

                if len(chunk) < MAX_CANDLES_PER_REQUEST:
                    if cursor >= end_ms:
                        break

        candles = sorted(aggregated.values(), key=lambda candle: candle["open_time"])
        self._warn_if_missing(start_ts, end_ts, candles)
        return candles

    def _warn_if_missing(self, start_ts: int, end_ts: int, candles: List[Dict[str, Any]]) -> None:
        if not candles:
            print("[WARN] Не удалось получить ни одной свечи.")
            return

        requested_days = max((end_ts - start_ts) / 86400, 0)
        actual_start = candles[0]["open_time"] // 1000
        actual_end = candles[-1]["close_time"] // 1000
        actual_days = max((actual_end - actual_start) / 86400, 0)

        if actual_start > start_ts:
            missing_days = (actual_start - start_ts) / 86400
            print(
                "[WARN] Биржа вернула данные только с "
                f"{datetime.utcfromtimestamp(actual_start)} "
                f"(~{actual_days:.1f} дн. вместо запрошенных ~{requested_days:.1f} дн.; "
                f"не хватает ~{missing_days:.1f} дн.)"
            )

    async def _fetch_chunk(
        self,
        session: aiohttp.ClientSession,
        start: int,
        end: int,
    ) -> Optional[List[Sequence[Any]]]:
        max_retries = 3

        for attempt in range(max_retries):
            try:
                return await get_klines(
                    session=session,
                    symbol=self.symbol,
                    interval=self.timeframe,
                    start=start,
                    end=end,
                    limit=MAX_CANDLES_PER_REQUEST,
                )
            except Exception as exc:
                print(
                    f"[{self.symbol} {self.timeframe}] Ошибка запроса "
                    f"{attempt + 1}/{max_retries} (start={start}, end={end}): {exc}"
                )
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(ERROR_SLEEP_SECONDS)
        return None

    def _build_format_list(self, primary_format: Optional[str]) -> Tuple[str, ...]:
        formats = []
        if primary_format:
            formats.append(primary_format)
        formats.extend(fmt for fmt in FALLBACK_DATE_FORMATS if fmt not in formats)
        return tuple(formats)

    def _resolve_time_bounds(self) -> Tuple[int, int]:
        start_str = (self.date_range or {}).get("start")
        end_str = (self.date_range or {}).get("end")

        if start_str and end_str:
            start_dt = self._parse_date(start_str)
            end_dt = self._parse_date(end_str)
        else:
            end_dt = datetime.utcnow()
            days = self.lookback_days if self.lookback_days and self.lookback_days > 0 else 1
            start_dt = end_dt - timedelta(days=days)

        return int(start_dt.timestamp()), int(end_dt.timestamp())

    def _parse_date(self, value: str) -> datetime:
        for fmt in self.date_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Не удалось распарсить дату: {value}") from exc

    def _format_candle(self, candle: Sequence[Any]) -> Dict[str, Any]:
        return {
            "open_time": _safe_int(candle[0]),
            "open": _safe_float(candle[1]),
            "high": _safe_float(candle[2]),
            "low": _safe_float(candle[3]),
            "close": _safe_float(candle[4]),
            "volume": _safe_float(candle[5]),
            "close_time": _safe_int(candle[6]),
            "quote_asset_volume": _safe_float(candle[7]),
            "trade_count": _safe_int(candle[8]),
            "taker_buy_base_volume": _safe_float(candle[9]),
            "taker_buy_quote_volume": _safe_float(candle[10]),
        }


async def load_configured_candles() -> List[Dict[str, Any]]:
    fetcher = CandleFetcher(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        lookback_days=LOOKBACK_DAYS,
        date_range=DATE_RANGE,
        date_format=DATE_FORMAT,
    )
    return await fetcher.fetch()
