# Документация проекта

## Структура
- `settings.py` — все параметры запроса: торговая пара (`SYMBOL`), таймфрейм (`TIMEFRAME`), количество дней при отсутствии дат (`LOOKBACK_DAYS`), произвольные даты `DATE_RANGE`, формат строк дат `DATE_FORMAT`.
- `api.py` — низкоуровневый клиент Binance Futures (`https://fapi.binance.com/fapi/v1/klines`). Следит за лимитами и возвращает «сырые» массивы свечей.
- `calculation/kline_sorter.py` — основной сборщик свечей. `CandleFetcher`:
  - рассчитывает границы периода (по датам или `LOOKBACK_DAYS`);
  - шагает по истории кусками, запрашивая до 1500 свечей за раз;
  - автоматически продолжает с последней полученной свечи;
  - приводит значения к числовому виду и убирает дубликаты;
  - предупреждает, если биржа не отдала весь запрошенный диапазон.
- `main.py` — удобная точка входа. `fetch_candles()` отдаёт результат асинхронно, `run()` — синхронная обёртка, которая дополнительно сохраняет свечи в JSON.

## Настройки таймфреймов
Допустимые значения `TIMEFRAME` (как у Binance):  
`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M`.  
Если в `settings.py` оставить `DATE_RANGE["start"]` и `DATE_RANGE["end"]` пустыми, используется `LOOKBACK_DAYS`.

## Формат свечи
Каждый элемент в результате из `calculation.kline_sorter.load_configured_candles()` содержит:
```text
{
    "open_time": <int>,   # миллисекунды Binance
    "open": <float>,
    "high": <float>,
    "low": <float>,
    "close": <float>,
    "volume": <float>,
    "close_time": <int>,
    "quote_asset_volume": <float>,
    "trade_count": <int>,
    "taker_buy_base_volume": <float>,
    "taker_buy_quote_volume": <float>
}
```

## Как получить свечи
```python
from main import run

candles = run()  # параллельно создаёт JSON-файл
```
Асинхронный вариант:
```python
import asyncio
from main import fetch_candles

async def example():
    data = await fetch_candles()
    ...

asyncio.run(example())
```

### Формат имени сохраняемого файла
```
<SYMBOL>_<START-END | last_<LOOKBACK_DAYS>d>_<TIMEFRAME>.json
```
Символ очищается от пробелов и спецсимволов, поэтому `BTC_USDT` и `BTCUSDT` дадут одинаковый файл.  
Пример: `BTCUSDT_last_30d_1m.json` или `ETHUSDT_2024-01-01_2024-01-10_4h.json`.

