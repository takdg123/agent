#!/usr/bin/env python3
"""
Paper filtering utilities
Centralized paper relevance filtering logic
"""

from typing import List, Dict, Set

class PaperFilter:
    """Filters papers based on relevance criteria"""
    
    PRIMARY_KEYWORDS = [
        "kilonova", "kilonovae", "at2017gfo", 
        "grb", "gamma-ray burst", "gamma ray burst"
    ]
    
    SECONDARY_KEYWORDS = [
        "neutron star merger", "gravitational wave", 
        "r-process", "electromagnetic counterpart", 
        "afterglow", "jet", "gw170817"
    ]
    
    @staticmethod
    def calculate_relevance(paper: Dict) -> float:
        """
        Calculate relevance score for a paper
        
        Args:
            paper: Paper dictionary with 'title' and 'abstract'
            
        Returns:
            Relevance score (0-2)
        """
        title = paper.get('title', '').lower()
        abstract = paper.get('abstract', '').lower()
        full_text = f"{title} {abstract}"
        
        has_primary = any(
            kw.lower() in full_text 
            for kw in PaperFilter.PRIMARY_KEYWORDS
        )
        
        has_secondary = any(
            kw.lower() in full_text 
            for kw in PaperFilter.SECONDARY_KEYWORDS
        )
        
        if has_primary:
            return 2.0
        elif has_secondary and ("merger" in full_text or "transient" in full_text):
            return 1.0
        else:
            return 0.0
    
    @staticmethod
    def filter_papers(papers: List[Dict], min_score: float = 0.5) -> List[Dict]:
        """
        Filter papers by relevance score
        
        Args:
            papers: List of paper dictionaries
            min_score: Minimum relevance score
            
        Returns:
            Filtered and sorted papers with relevance_score added
        """
        filtered = []
        
        for paper in papers:
            score = PaperFilter.calculate_relevance(paper)
            if score >= min_score:
                paper['relevance_score'] = score
                filtered.append(paper)
        
        # Sort by relevance (highest first)
        filtered.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return filtered
    
    @staticmethod
    def extract_keywords(paper: Dict) -> Set[str]:
        """Extract keywords from paper for memory matching"""
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        
        found_keywords = set()
        all_keywords = PaperFilter.PRIMARY_KEYWORDS + PaperFilter.SECONDARY_KEYWORDS
        
        for kw in all_keywords:
            if kw.lower() in text:
                found_keywords.add(kw.lower())
        
        return found_keywords
