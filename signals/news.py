# News and calendar guard
from datetime import datetime, timedelta
from config.config import NEWS_BLACKOUT_MINUTES, UPCOMING_EVENTS

def check_news_blackout():
    """
    Check if we're in a news blackout window
    Returns: tuple (is_blackout, reason)
    """
    now = datetime.utcnow()
    
    for event_str in UPCOMING_EVENTS:
        try:
            event_time = datetime.strptime(event_str, "%Y-%m-%d %H:%M UTC")
            
            # Calculate window
            start_blackout = event_time - timedelta(minutes=NEWS_BLACKOUT_MINUTES)
            end_blackout = event_time + timedelta(minutes=NEWS_BLACKOUT_MINUTES)
            
            if start_blackout <= now <= end_blackout:
                minutes_until = int((event_time - now).total_seconds() / 60)
                if minutes_until > 0:
                    return (True, f"High-impact event in {minutes_until}m")
                else:
                    return (True, f"High-impact event just passed ({abs(minutes_until)}m ago)")
        
        except Exception as e:
            continue
    
    return (False, "Clear")