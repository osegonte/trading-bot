# Trade planning and risk calculation
import pandas as pd
from config.config import (PIP_SIZE, PIP_VALUE_PER_LOT, BROKER_MIN_LOT, BROKER_LOT_STEP, 
                   BROKER_MAX_LOT, RISK_MODE, RISK_PER_TRADE, RR_TARGET, 
                   ATR_PERIOD, ATR_MULTIPLIER, ASSUMED_SPREAD)

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high = df['High']
    low = df['Low']
    close = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr.iloc[-1] if len(atr) > 0 else None

def calculate_lot_size(risk_amount, stop_pips):
    """Calculate position size based on risk"""
    if stop_pips <= 0:
        return BROKER_MIN_LOT
    
    lots = risk_amount / (stop_pips * PIP_VALUE_PER_LOT)
    
    # Round to broker step
    lots = round(lots / BROKER_LOT_STEP) * BROKER_LOT_STEP
    
    # Clamp to broker limits
    lots = max(BROKER_MIN_LOT, min(lots, BROKER_MAX_LOT))
    
    return round(lots, 2)

def create_trade_plan(df, direction, balance):
    """
    Create complete trade plan with entry, SL, TP, lots
    Args:
        df: OHLC dataframe
        direction: "BUY" or "SELL"
        balance: current account balance
    Returns: dict with trade plan details
    """
    if df is None or df.empty:
        return None
    
    entry_price = round(df['Close'].iloc[-1], 2)
    atr = calculate_atr(df, ATR_PERIOD)
    
    if atr is None or atr <= 0:
        return None
    
    # Calculate stop distance
    stop_distance = ATR_MULTIPLIER * atr
    stop_pips = round(stop_distance / PIP_SIZE)
    
    # Calculate TP distance
    tp_pips = round(RR_TARGET * stop_pips)
    
    # Calculate prices
    if direction == "BUY":
        sl_price = round(entry_price - (stop_pips * PIP_SIZE), 2)
        tp_price = round(entry_price + (tp_pips * PIP_SIZE), 2)
        
        # Adjust for spread (SL hit on ask, TP hit on bid)
        sl_price -= ASSUMED_SPREAD
        
    else:  # SELL
        sl_price = round(entry_price + (stop_pips * PIP_SIZE), 2)
        tp_price = round(entry_price - (tp_pips * PIP_SIZE), 2)
        
        # Adjust for spread
        sl_price += ASSUMED_SPREAD
    
    # Calculate risk amount
    if RISK_MODE == "LEVEL_STRICT":
        risk_amount = 0.20 * balance
    else:  # SAFER
        risk_amount = RISK_PER_TRADE * balance
    
    # Calculate lot size
    lots = calculate_lot_size(risk_amount, stop_pips)
    
    # Calculate potential PnL
    potential_loss = stop_pips * PIP_VALUE_PER_LOT * lots
    potential_gain = tp_pips * PIP_VALUE_PER_LOT * lots
    
    return {
        'direction': direction,
        'entry': entry_price,
        'sl': sl_price,
        'tp': tp_price,
        'lots': lots,
        'stop_pips': stop_pips,
        'tp_pips': tp_pips,
        'rr': RR_TARGET,
        'risk_amount': round(risk_amount, 2),
        'potential_loss': round(potential_loss, 2),
        'potential_gain': round(potential_gain, 2),
        'atr': round(atr, 2)
    }