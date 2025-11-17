"""
AI-Powered Trading Analytics
Uses OpenAI GPT to analyze module performance and suggest improvements
"""
import sqlite3
import json
from datetime import datetime, timedelta
from openai import OpenAI
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """
    Analyzes trading performance using AI
    Provides insights beyond simple statistics
    """
    
    def __init__(self, db_path: str = 'trading_signals.db', api_key: str = None):
        self.db_path = db_path
        self.client = OpenAI(api_key=api_key) if api_key else None
    
    def get_module_detailed_stats(self, days: int = 7) -> Dict:
        """Get detailed stats for each module"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get all completed trades with module verdicts
        cursor.execute("""
            SELECT 
                t.id,
                t.direction,
                t.entry,
                t.result,
                t.pnl,
                t.timestamp,
                s.trend_verdict,
                s.candle_verdict,
                s.sr_verdict,
                s.volume_verdict,
                s.rsi_verdict,
                s.macd_verdict,
                s.bollinger_verdict,
                s.macro_verdict,
                s.score,
                s.confidence
            FROM trades t
            JOIN signals s ON t.signal_id = s.id
            WHERE t.result IN ('WIN', 'LOSS')
            AND t.timestamp > ?
            ORDER BY t.timestamp DESC
        """, (cutoff,))
        
        trades = cursor.fetchall()
        conn.close()
        
        if not trades:
            logger.warning("No completed trades in timeframe")
            return {}
        
        # Analyze each module
        modules = ['trend', 'candlestick', 'sr', 'volume', 'rsi', 'macd', 'bollinger', 'macro']
        module_stats = {}
        
        for idx, module in enumerate(modules):
            verdict_idx = 6 + idx  # Column index in query
            
            agreed_wins = 0
            agreed_losses = 0
            disagreed_wins = 0
            disagreed_losses = 0
            neutral_count = 0
            
            for trade in trades:
                direction = trade[1]
                result = trade[3]
                verdict = trade[verdict_idx]
                
                if verdict == 'NEUTRAL':
                    neutral_count += 1
                    continue
                
                agreed = (verdict == direction)
                
                if agreed and result == 'WIN':
                    agreed_wins += 1
                elif agreed and result == 'LOSS':
                    agreed_losses += 1
                elif not agreed and result == 'WIN':
                    disagreed_wins += 1
                elif not agreed and result == 'LOSS':
                    disagreed_losses += 1
            
            total_opinions = agreed_wins + agreed_losses + disagreed_wins + disagreed_losses
            
            if total_opinions > 0:
                accuracy = (agreed_wins + disagreed_losses) / total_opinions * 100
                confidence_ratio = agreed_wins / (agreed_wins + agreed_losses) if (agreed_wins + agreed_losses) > 0 else 0
            else:
                accuracy = 0
                confidence_ratio = 0
            
            module_stats[module] = {
                'agreed_wins': agreed_wins,
                'agreed_losses': agreed_losses,
                'disagreed_wins': disagreed_wins,
                'disagreed_losses': disagreed_losses,
                'neutral': neutral_count,
                'total_opinions': total_opinions,
                'accuracy': round(accuracy, 1),
                'confidence_ratio': round(confidence_ratio * 100, 1),
                'sample_size': total_opinions + neutral_count
            }
        
        return module_stats
    
    def analyze_with_ai(self, module_stats: Dict, total_trades: int) -> str:
        """Use GPT to analyze module performance and suggest improvements"""
        
        if not self.client:
            return "⚠️ OpenAI API key not configured - showing basic analysis only"
        
        prompt = f"""You are an expert quantitative trading system analyst. Analyze this module performance data from a gold (XAU/USD) trading bot and provide actionable insights.

CONTEXT:
- Total completed trades analyzed: {total_trades}
- Trading strategy: Council-based voting system
- Each module votes BUY/SELL/NEUTRAL
- Current threshold: ±1.5 aggregate score to execute trade

MODULE PERFORMANCE DATA:
{json.dumps(module_stats, indent=2)}

DEFINITIONS:
- agreed_wins: Module voted with trade direction, trade won
- agreed_losses: Module voted with trade direction, trade lost
- disagreed_wins: Module voted opposite, trade still won (module was wrong)
- disagreed_losses: Module voted opposite, trade lost (module was right to warn)
- neutral: Module had no strong opinion
- accuracy: % of times module's opinion was correct
- confidence_ratio: Win rate when module takes a position

PROVIDE SPECIFIC ANALYSIS:

1. **TOP 3 PERFORMERS** 
   - Which modules show best accuracy and why?
   - Should their weights be increased?

2. **BOTTOM 3 PERFORMERS**
   - Which modules are unreliable?
   - Should they be removed or need different parameters?

3. **NEUTRAL BIAS ANALYSIS**
   - Which modules are too neutral (avoiding decisions)?
   - Is this helpful caution or useless noise?

4. **PARAMETER TUNING SUGGESTIONS**
   - Specific parameter changes for each underperforming module
   - Example: "RSI oversold threshold: 30 → 25"

5. **PORTFOLIO REBALANCING**
   - Recommended weight distribution
   - Should we consolidate to fewer, better modules?

6. **IMMEDIATE ACTIONS** (Priority ranked)
   - Top 3 changes to make RIGHT NOW
   - Expected impact of each change

Be quantitative, specific, and actionable. Focus on WHAT TO DO, not just observations."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert quantitative trading analyst specializing in algorithmic trading systems and module optimization."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return f"❌ AI analysis failed: {e}"
    
    def generate_report(self, days: int = 7) -> str:
        """Generate comprehensive analysis report"""
        stats = self.get_module_detailed_stats(days)
        
        if not stats:
            return "⚠️ No trade data available for analysis"
        
        total_trades = sum(s['agreed_wins'] + s['agreed_losses'] + s['disagreed_wins'] + s['disagreed_losses'] for s in stats.values()) // len(stats)
        
        # Generate text report
        report = f"""
{'='*70}
🤖 AI-POWERED MODULE PERFORMANCE ANALYSIS
{'='*70}
Period: Last {days} days
Total Trades: {total_trades}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}

"""
        
        # Sort by accuracy
        sorted_modules = sorted(stats.items(), key=lambda x: x[1]['accuracy'], reverse=True)
        
        report += "\n📊 MODULE RANKINGS (by accuracy):\n\n"
        
        for rank, (module, data) in enumerate(sorted_modules, 1):
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            verdict = '✅ EXCELLENT' if data['accuracy'] >= 60 else '✅ GOOD' if data['accuracy'] >= 50 else '⚠️ REVIEW' if data['accuracy'] >= 45 else '❌ REMOVE'
            
            report += f"""
{emoji} {module.upper()} - {verdict}
   Accuracy: {data['accuracy']}% | Confidence: {data['confidence_ratio']}%
   When Agreed: {data['agreed_wins']}W - {data['agreed_losses']}L
   When Disagreed: {data['disagreed_wins']}W (wrong) - {data['disagreed_losses']}L (correct warning)
   Neutral: {data['neutral']} times ({data['neutral']/data['sample_size']*100:.0f}% of time)
   Sample Size: {data['sample_size']} signals
"""
        
        # Add AI analysis
        report += f"""
{'='*70}
🧠 GPT-4 DEEP ANALYSIS
{'='*70}

{self.analyze_with_ai(stats, total_trades)}

{'='*70}
"""
        
        return report
    
    def export_recommendations(self) -> Dict:
        """Export actionable recommendations as structured data"""
        stats = self.get_module_detailed_stats()
        
        if not stats:
            return {'error': 'No data available'}
        
        recommendations = {
            'remove': [],
            'reduce_weight': [],
            'increase_weight': [],
            'keep_as_is': [],
            'tune_parameters': []
        }
        
        for module, data in stats.items():
            accuracy = data['accuracy']
            sample_size = data['sample_size']
            
            # Need minimum sample size for reliable recommendations
            if sample_size < 5:
                recommendations['tune_parameters'].append({
                    'module': module,
                    'reason': f"Insufficient data ({sample_size} samples)",
                    'action': 'Collect more data before making changes'
                })
                continue
            
            if accuracy < 45:
                recommendations['remove'].append({
                    'module': module,
                    'reason': f"Low accuracy ({accuracy}%)",
                    'action': f'Disable in config/modules.yaml'
                })
            elif accuracy < 50:
                recommendations['reduce_weight'].append({
                    'module': module,
                    'reason': f"Below-average accuracy ({accuracy}%)",
                    'action': f'Reduce weight by 50% (to {data["accuracy"]/100:.2f})'
                })
            elif accuracy > 65:
                recommendations['increase_weight'].append({
                    'module': module,
                    'reason': f"High accuracy ({accuracy}%)",
                    'action': f'Consider increasing weight by 25-50%'
                })
            else:
                recommendations['keep_as_is'].append({
                    'module': module,
                    'reason': f"Solid performance ({accuracy}%)"
                })
        
        return recommendations
