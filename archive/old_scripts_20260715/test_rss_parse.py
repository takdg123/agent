#!/usr/bin/env python3
"""Debug RSS parsing"""

import httpx
import xml.etree.ElementTree as ET

url = "http://export.arxiv.org/rss/astro-ph.HE"

print(f"Fetching: {url}")
response = httpx.get(url, timeout=10, follow_redirects=True)
print(f"Status: {response.status_code}")
print(f"Length: {len(response.text)}")

# Parse
root = ET.fromstring(response.text)

# Try different namespace patterns
print("\nTrying Atom namespace:")
entries_atom = root.findall(".//{http://www.w3.org/2005/Atom}entry")
print(f"  Atom entries: {len(entries_atom)}")

print("\nTrying RSS namespace:")
items_rss = root.findall(".//item")
print(f"  RSS items: {len(items_rss)}")

print("\nRoot tag:", root.tag)
print("\nFirst few tags:")
for i, child in enumerate(root.iter()):
    if i < 20:
        print(f"  {child.tag}")
    else:
        break

# If RSS items found, show first one
if len(items_rss) > 0:
    print("\n=== First RSS Item ===")
    item = items_rss[0]
    for child in item:
        print(f"{child.tag}: {child.text[:100] if child.text else 'None'}")
