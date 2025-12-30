import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from calculation.kline_sorter import load_configured_candles
from settings import DATE_RANGE, LOOKBACK_DAYS, SYMBOL, TIMEFRAME


async def fetch_candles() -> List[Dict[str, Any]]:
    """Возвращает свечи согласно настройкам."""
    return await load_configured_candles()


def _sanitize_segment(raw: str) -> str:
    cleaned = re.sub(r"[^\w-]+", "-", raw.strip())
    return cleaned.strip("-") or "unknown"


def _build_filename() -> str:
    symbol_segment = _sanitize_segment(SYMBOL)
    start = (DATE_RANGE.get("start") or "").strip()
    end = (DATE_RANGE.get("end") or "").strip()

    if start and end:
        date_segment = f"{_sanitize_segment(start)}_{_sanitize_segment(end)}"
    else:
        days = LOOKBACK_DAYS if LOOKBACK_DAYS and LOOKBACK_DAYS > 0 else 1
        date_segment = f"last_{days}d"

    timeframe_segment = _sanitize_segment(TIMEFRAME)
    return f"{symbol_segment}_{date_segment}_{timeframe_segment}.json"


def _save_candles(candles: List[Dict[str, Any]]) -> Path:
    filepath = Path(_build_filename())
    filepath.write_text(json.dumps(candles, ensure_ascii=False, indent=2))
    return filepath


def run() -> List[Dict[str, Any]]:
    """Синхронная обертка: загружает и сохраняет свечи в JSON."""
    candles = asyncio.run(fetch_candles())
    _save_candles(candles)
    return candles


if __name__ == "__main__":
    candles = run()
    for candle in candles:
        print(candle)
