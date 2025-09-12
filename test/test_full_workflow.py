#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for full Agent workflow
Tests: Search -> Ingest -> Report generation
"""

import sys
sys.path.insert(0, '.')

from src.agent import Agent

def test_full_workflow():
    """Test the complete Agent workflow"""
    
    print("🚀 Testing Complete Agent Workflow")
    print("=" * 50)
    
    try:
        # Initialize the system
        print("1. Initializing Agent system...")
        agent = Agent()
        
        print("2. Initializing components...")
        if not agent.initialize():
            print("❌ System initialization failed")
            return False
        
        print("3. Getting system status...")
        status = agent.get_system_status()
        print(f"   ✅ System initialized: {status['initialized']}")
        print(f"   ✅ PDF Processing: {status['pdf_processing']}")
        print(f"   ✅ Database: {status['database']}")
        print(f"   ✅ LLM: {status['llm']}")
        print(f"   ✅ Current Model: {status['current_model']}")
        print(f"   ✅ GPU Device: {agent.config.gpu_device}")
        
        # Test ingestion first
        print("\n4. Testing paper ingestion...")
        ingest_result = agent.ingest_papers()
        
        if ingest_result["success"]:
            print("✅ Ingestion completed!")
            print(f"   Papers processed: {ingest_result['papers_processed']}")
            print(f"   Papers ingested: {ingest_result['papers_ingested']}")
            print(f"   Papers skipped: {ingest_result['papers_skipped']}")
        else:
            print(f"❌ Ingestion failed: {ingest_result['error']}")
            # Continue anyway to test reporting with existing papers
        
        # Test reporting with 10 days of papers
        print("\n5. Testing daily report generation (last 10 days)...")
        report_result = agent.generate_daily_report(hours_back=240)  # 10 days = 240 hours
        
        if report_result["success"]:
            print("✅ Report generation completed!")
            print(f"   Papers analyzed: {report_result.get('papers_analyzed', 0)}")
            print(f"   Categories analyzed: {report_result.get('categories_analyzed', 0)}")
            print(f"   Summaries generated: {report_result.get('summaries_generated', 0)}")
            print(f"   Report path: {report_result.get('report_path', 'N/A')}")
            print(f"   Email sent: {report_result.get('email_sent', False)}")
            
            if report_result.get('report_path'):
                print(f"\n📄 Report saved to: {report_result['report_path']}")
                print("   You can view the generated report in your data/reports directory!")
        else:
            print(f"❌ Report generation failed: {report_result['error']}")
        
        print("\n🎉 Full workflow test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_workflow()
    sys.exit(0 if success else 1)
