#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Example usage of the new class-based Agent system
Demonstrates how to use the system for various tasks
"""

from src.agent import Agent

def main():
    """Demonstrate Agent system usage"""
    
    print("🚀 Agent System Example Usage")
    print("=" * 50)
    
    try:
        # Initialize the system
        print("\n1. Initializing Agent system...")
        agent = Agent()
        
        # Initialize components
        print("\n2. Initializing components...")
        if not agent.initialize():
            print("❌ System initialization failed")
            return
        
        # Get system status
        print("\n3. System status:")
        status = agent.get_system_status()
        for key, value in status.items():
            if key == "configuration":
                print(f"   {key}:")
                for config_key, config_value in value.items():
                    print(f"     {config_key}: {config_value}")
            else:
                print(f"   {key}: {value}")
        
        # Generate daily report
        print("\n4. Generating daily report...")
        report_result = agent.generate_daily_report(hours_back=168)  # 7 days
        
        if report_result["success"]:
            print(f"✅ Report generated successfully!")
            print(f"   Papers analyzed: {report_result['papers_analyzed']}")
            print(f"   Categories analyzed: {report_result['categories_analyzed']}")
            print(f"   Summaries generated: {report_result['summaries_generated']}")
            print(f"   Report saved to: {report_result['report_path']}")
            print(f"   Email sent: {report_result['email_sent']}")
        else:
            print(f"❌ Report generation failed: {report_result['error']}")
        
        # Example: Analyze a specific PDF (if available)
        print("\n5. PDF analysis example:")
        # This would analyze a specific PDF file
        # pdf_result = agent.analyze_pdf("/path/to/paper.pdf")
        # if pdf_result["success"]:
        #     print(f"✅ PDF analysis completed")
        #     print(f"   Content preview: {pdf_result['content_preview']}")
        # else:
        #     print(f"❌ PDF analysis failed: {pdf_result['error']}")
        
        print("\n🎉 Agent system demonstration completed!")
        
    except Exception as e:
        print(f"❌ Error in example usage: {e}")

if __name__ == "__main__":
    main()
