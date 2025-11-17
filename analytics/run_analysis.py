"""
Run AI-powered analysis on trading performance
"""
import sys
import os
sys.path.insert(0, '.')

from analytics.ai_analyzer import AIAnalyzer
from datetime import datetime

# Get API key from environment
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    print("⚠️  No OpenAI API key found in environment")
    print("Set it: export OPENAI_API_KEY='your-key'")
    print("Running basic analysis only...\n")

print("=" * 70)
print("🤖 INITIALIZING AI TRADING ANALYTICS")
print("=" * 70)
print()

# Initialize analyzer
analyzer = AIAnalyzer(
    db_path='trading_signals.db',
    api_key=OPENAI_API_KEY
)

# Generate report
print("📊 Analyzing module performance...\n")

report = analyzer.generate_report(days=7)
print(report)

# Get structured recommendations
print("\n" + "="*70)
print("📋 ACTIONABLE RECOMMENDATIONS")
print("="*70 + "\n")

recommendations = analyzer.export_recommendations()

if 'error' in recommendations:
    print(f"❌ {recommendations['error']}")
else:
    if recommendations['remove']:
        print("❌ REMOVE THESE MODULES:")
        for rec in recommendations['remove']:
            print(f"  - {rec['module'].upper()}: {rec['reason']}")
            print(f"    Action: {rec['action']}\n")

    if recommendations['reduce_weight']:
        print("⚠️  REDUCE WEIGHT:")
        for rec in recommendations['reduce_weight']:
            print(f"  - {rec['module'].upper()}: {rec['reason']}")
            print(f"    Action: {rec['action']}\n")

    if recommendations['increase_weight']:
        print("⬆️  INCREASE WEIGHT:")
        for rec in recommendations['increase_weight']:
            print(f"  - {rec['module'].upper()}: {rec['reason']}")
            print(f"    Action: {rec['action']}\n")

    if recommendations['keep_as_is']:
        print("✅ KEEP AS-IS (Performing Well):")
        for rec in recommendations['keep_as_is']:
            print(f"  - {rec['module'].upper()}: {rec['reason']}")

    if recommendations['tune_parameters']:
        print("\n🔧 NEEDS MORE DATA:")
        for rec in recommendations['tune_parameters']:
            print(f"  - {rec['module'].upper()}: {rec['reason']}")

# Save report
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"analytics/reports/analysis_{timestamp}.txt"

with open(filename, 'w') as f:
    f.write(report)

print(f"\n📄 Full report saved: {filename}")
print("\n" + "="*70)
print("✅ ANALYSIS COMPLETE")
print("="*70)
