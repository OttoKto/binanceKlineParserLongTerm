SYMBOL = "BTC_USDT"
TIMEFRAME = "1m"  # Binance интервалы: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 1w, 1M

# Сколько последних дней забирать, если не заданы start/end.
LOOKBACK_DAYS = 365

# Укажи даты в удобном формате, например "2024-12-01 00:00".
# Оставь пустыми строки, чтобы использовать LOOKBACK_DAYS.
DATE_RANGE = {
    "start": "2025-01-01",
    "end": "2025-03-01",
}

# Пользовательский формат для start/end.
DATE_FORMAT = "%Y-%m-%d %H:%M"

