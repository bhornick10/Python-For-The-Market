# --- Do not remove these libs ---
from sysconfig import expand_makefile_vars

from freqtrade.strategy import IStrategy
from typing import List
import numpy as np
from pandas import DataFrame
import requests
import datetime as dt
# --------------------------------

import talib.abstract as ta

class BrandonStrategy001(IStrategy):
    """
    Strategy 001: Volume Bias + VWAP entry above EMA200 with comparison to smoothed line
    """
    INTERFACE_VERSION: int = 3

    minimal_roi = {
        "480": 0.03,
        "120": 0.04,
        "60": 0.05,
        "0": 0.06
    }

    stoploss = -0.015
    timeframe = '1h'
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    process_only_new_candles = False
    startup_candle_count: int = 200

    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'limit',
        'stoploss_on_exchange': False
    }

    def informative_pairs(self) -> List:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        lookback_ema = 10
        vwap_len     = 50
        lookback     = 10
        smoothing    = 10

        # EMA 200 for trend filter
        dataframe['ema200'] = ta.EMA(dataframe['close'], timeperiod = 200)

        # VWAP via rolling volume‐weighted average
        tpv = dataframe['close'] * dataframe['volume']
        dataframe['vwapp'] = tpv.rolling(window=lookback_ema).sum() / dataframe['volume'].rolling(window=lookback_ema).sum()

        # non-anchored VWAP (Pine’s ta.vwma equivalent)
        vwap_lookback = lookback_ema
        dataframe['vwapppp'] = (
            (dataframe['close'] * dataframe['volume'])
            .rolling(window=vwap_lookback).sum()
            /
            dataframe['volume']
            .rolling(window=vwap_lookback).sum()
        )

        # Raw volumeBias: +volume if up‐bar, –volume if down‐bar
        dataframe['volumeBias_raw'] = np.where(
            dataframe['close'] > dataframe['open'],
            dataframe['volume'],
            -dataframe['volume']
        )

        # Double‐EMA smoothing
        dataframe['volumeBias'] = dataframe['volumeBias_raw'].ewm(span=lookback, adjust=False).mean()
        dataframe['volumeBias'] = dataframe['volumeBias'].ewm(span=smoothing, adjust=False).mean()

        # Combine bias + VWAP
        dataframe['volumeBias_vwap_raw'] = np.where(
            dataframe['close'] > dataframe['open'],
            dataframe['volumeBias'] + dataframe['vwapp'],
            dataframe['volumeBias'] - dataframe['vwapp']
        )

        # Smooth combined series (first pass)
        dataframe['volumeBias_vwap'] = dataframe['volumeBias_vwap_raw'].ewm(span=smoothing, adjust=False).mean()
        # Smooth combined series (second pass)
        dataframe['volumeBias_vwap_smoothed'] = dataframe['volumeBias_vwap'].ewm(span=vwap_len, adjust=False).mean()

        dataframe['zero'] = 0.0

        # shorter ema volume and longer ema volume lookbacks
        ema_short = 2
        ema_long = 4

        # create a volume ema varaiable that is an ema of the last 2 candles' volume
        dataframe['volume_ema'] = dataframe['volume'].ewm(span=ema_short, adjust=False).mean()
        dataframe['volume_ema2'] = dataframe['volume'].ewm(span=ema_long, adjust=False).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0

        dataframe.loc[
            (
                (dataframe['close'] > dataframe['ema200']) &
                (dataframe['volumeBias_vwap'] > 0) &
                (dataframe['close'] > dataframe['vwapppp']) &
                (dataframe['volumeBias_vwap'] > dataframe['volumeBias_vwap'].shift(1)) &
                (dataframe['volume_ema'] > dataframe['volume_ema2']) &
                (dataframe['low'] > dataframe['ema200'])
            ),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        return dataframe
