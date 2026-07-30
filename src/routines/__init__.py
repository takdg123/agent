"""
Routines package for TORRI System
"""

# Only import modules actually used in refactored code
from .rss_fetcher import RSSFetcher

# IngestRoutine and downloader are not used in refactored version
# (kept in file for backward compatibility if needed)

__all__ = ['RSSFetcher']
