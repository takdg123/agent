#!/usr/bin/env python3
"""
Main entry point for Agent system
Used by systemd service to run daily operations
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import Agent

def main():
    """Main Agent system execution"""
    try:
        print("🚀 Agent System starting...")
        
        # Initialize Agent system
        agent = Agent()
        
        if not agent.initialize():
            print("❌ Failed to initialize Agent system")
            sys.exit(1)
        
        print("✅ Agent System initialized")
        
        # Run daily ingestion
        print("\n📚 Running daily paper ingestion...")
        ingest_result = agent.ingest_papers()
        
        if ingest_result.get("success"):
            print("✅ Ingestion completed!")
            print(f"   Papers processed: {ingest_result.get('papers_processed', 0)}")
            print(f"   Papers ingested: {ingest_result.get('papers_ingested', 0)}")
            print(f"   Papers skipped: {ingest_result.get('papers_skipped', 0)}")
        else:
            print(f"❌ Ingestion failed: {ingest_result.get('error', 'Unknown error')}")
        
        # Generate daily report
        print("\n📊 Generating daily report...")
        report_result = agent.generate_daily_report(hours_back=24)
        
        if report_result.get("success"):
            print("✅ Report generation completed!")
            print(f"   Papers analyzed: {report_result.get('papers_analyzed', 0)}")
            print(f"   Report path: {report_result.get('report_path', 'N/A')}")
        else:
            print(f"❌ Report generation failed: {report_result.get('error', 'Unknown error')}")
        
        print("\n🎉 Agent daily execution completed!")
        return True
        
    except Exception as e:
        print(f"❌ Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
