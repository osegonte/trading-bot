# Helper functions
from datetime import datetime
import pytz
from config.config import WEIGHTS, BUY_SELL_THRESHOLDS, CONFIDENCE

def get_utc_timestamp():
    """Returns current UTC timestamp as string"""
    return datetime.now(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

def format_verdict(verdict):
    """Format verdict with emoji"""
    if verdict == "BUY":
        return "✅ Buy"
    elif verdict == "SELL":
        return "❌ Sell"
    else:
        return "➖ Neutral"

def calculate_percentage(wins, total):
    """Calculate percentage, handle division by zero"""
    if total == 0:
        return 0
    return round((wins / total) * 100, 1)

def aggregate_verdicts_with_macro(verdicts, macro_verdict):
    """
    Aggregate verdicts with macro gate
    Args:
        verdicts: dict of {module_name: verdict}
        macro_verdict: "BUY", "SELL", or "NEUTRAL"
    Returns: tuple (final_verdict, score, confidence, macro_adjusted)
    """
    score_map = {"BUY": 1, "SELL": -1, "NEUTRAL": 0}
    
    # Calculate weighted technical score
    total_score = 0
    buy_modules = []
    sell_modules = []
    
    for module, verdict in verdicts.items():
        weight = WEIGHTS.get(module, 0.5)
        module_score = score_map[verdict] * weight
        total_score += module_score
        
        if verdict == "BUY":
            buy_modules.append(module)
        elif verdict == "SELL":
            sell_modules.append(module)
    
    # Determine technical verdict before macro
    if total_score >= BUY_SELL_THRESHOLDS['buy']:
        technical_verdict = "BUY"
    elif total_score <= BUY_SELL_THRESHOLDS['sell']:
        technical_verdict = "SELL"
    else:
        technical_verdict = "NEUTRAL"
    
    # Apply macro gate
    macro_adjusted = False
    final_verdict = technical_verdict
    
    if technical_verdict == "BUY" and macro_verdict == "SELL":
        final_verdict = "NEUTRAL"
        macro_adjusted = True
    elif technical_verdict == "SELL" and macro_verdict == "BUY":
        final_verdict = "NEUTRAL"
        macro_adjusted = True
    
    # Calculate confidence
    aligned_count = len(buy_modules) if technical_verdict == "BUY" else len(sell_modules)
    confidence = CONFIDENCE['base'] + (aligned_count * CONFIDENCE['half_weight'])
    
    # Macro confidence adjustment
    if final_verdict != "NEUTRAL":
        if macro_verdict == final_verdict:
            confidence += CONFIDENCE['macro_align']
        elif macro_verdict != "NEUTRAL":
            confidence += CONFIDENCE['macro_contra']
    
    confidence = min(confidence, CONFIDENCE['cap'])
    confidence = max(confidence, 30)  # Floor at 30%
    
    return final_verdict, round(total_score, 1), confidence, macro_adjusted