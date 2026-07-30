#!/usr/bin/env python3
"""
Test paper fetching from arXiv
"""

import sys
import httpx
import xml.etree.ElementTree as ET

def test_arxiv_fetch():
    """Test fetching from arXiv API"""
    
    # Simple test URL - just get 5 latest astro-ph.HE papers
    url = "https://export.arxiv.org/api/query?search_query=cat:astro-ph.HE&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
    
    print("🔍 Testing arXiv API fetch...")
    print(f"   URL: {url[:80]}...")
    
    try:
        print("   📡 Sending request...")
        response = httpx.get(url, timeout=30, follow_redirects=True)
        print(f"   ✅ Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ Bad status code: {response.status_code}")
            return
        
        print(f"   📄 Response length: {len(response.text)} chars")
        
        # Parse XML
        print("   🔍 Parsing XML...")
        root = ET.fromstring(response.text)
        
        # Find entries
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        print(f"   📚 Found {len(entries)} entries")
        
        if len(entries) == 0:
            print("   ⚠️  No entries found in XML")
            print("\n   First 500 chars of response:")
            print(response.text[:500])
            return
        
        # Extract titles
        for i, entry in enumerate(entries, 1):
            title = entry.find(".//{http://www.w3.org/2005/Atom}title")
            title_text = title.text.strip() if title is not None and title.text else "No Title"
            
            # Get arXiv ID
            id_elem = entry.find(".//{http://www.w3.org/2005/Atom}id")
            arxiv_id = ""
            if id_elem is not None and id_elem.text:
                arxiv_id = id_elem.text.split('/')[-1]
            
            print(f"\n   [{i}] {arxiv_id}")
            print(f"       {title_text[:100]}")
        
        print("\n✅ Fetch test successful!")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_arxiv_fetch()
