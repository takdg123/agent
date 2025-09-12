#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database management class for TORRI system
Handles all Qdrant vector database operations
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, PointStruct, VectorParams, Distance, Range

class DatabaseManager:
    """Handles all database operations for TORRI system"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to Qdrant database"""
        try:
            db_config = self.config.get_database_config()
            self.client = QdrantClient(
                host=db_config["host"], 
                port=db_config["port"]
            )
            
            # Test connection
            self.client.get_collections()
            self.connected = True
            print(f"✅ Connected to Qdrant at {db_config['host']}:{db_config['port']}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to Qdrant: {e}")
            self.connected = False
            return False
    
    def ensure_collection(self, collection_name: Optional[str] = None) -> bool:
        """Ensure the collection exists with proper configuration"""
        if not self.connected:
            if not self.connect():
                return False
        
        collection_name = collection_name or self.config.collection_name
        
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                print(f"📚 Creating collection: {collection_name}")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=768,  # Standard embedding size
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Collection '{collection_name}' created successfully")
            else:
                print(f"✅ Collection '{collection_name}' already exists")
            
            return True
            
        except Exception as e:
            print(f"❌ Error ensuring collection: {e}")
            return False
    
    def save_paper(self, paper: Dict[str, Any]) -> bool:
        """Save a paper to the database"""
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            # Ensure collection exists
            if not self.ensure_collection():
                return False
            
            # Generate unique ID
            paper_id = paper.get('id') or self._generate_paper_id(paper)
            
            # Prepare payload
            now = datetime.now()
            published_date = paper.get('published_date', '')
            
            # Convert published_date to timestamp if available
            published_timestamp = None
            if published_date:
                try:
                    # Parse ISO datetime string to timestamp
                    from dateutil import parser
                    parsed_date = parser.parse(published_date)
                    published_timestamp = parsed_date.timestamp()
                except Exception as e:
                    print(f"⚠️ Could not parse published_date '{published_date}': {e}")
                    published_timestamp = now.timestamp()  # Fallback to current time
            
            payload = {
                'title': paper.get('title', ''),
                'authors': paper.get('authors', []),
                'abstract': paper.get('abstract', ''),
                'url': paper.get('url', ''),
                'categories': paper.get('categories', []),
                'published_date': published_date,
                'published_timestamp': published_timestamp,  # Numeric timestamp for filtering
                'pdf_path': paper.get('pdf_path', ''),
                'pdf_text': paper.get('pdf_text', ''),
                'ingested_at': now.isoformat(),
                'ingested_at_timestamp': now.timestamp(),  # Numeric timestamp for filtering
                'source': paper.get('source', ''),
                'paper_hash': self._calculate_paper_hash(paper)
            }
            
            # Create point (for now, use dummy vector - can be enhanced later)
            point = PointStruct(
                id=paper_id,
                vector=[0.0] * 768,  # Placeholder vector
                payload=payload
            )
            
            # Upsert the point
            self.client.upsert(
                collection_name=self.config.collection_name,
                points=[point]
            )
            
            print(f"✅ Paper saved: {paper.get('title', 'N/A')[:50]}...")
            return True
            
        except Exception as e:
            print(f"❌ Error saving paper: {e}")
            return False
    
    def get_papers(self, filters: Optional[Dict[str, Any]] = None, 
                   limit: int = 100) -> List[Dict[str, Any]]:
        """Get papers from database with optional filters"""
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            # Build filter conditions
            filter_conditions = []
            
            if filters:
                if 'hours_back' in filters:
                    hours_back = filters['hours_back']
                    cutoff_time = datetime.now() - timedelta(hours=hours_back)
                    cutoff_timestamp = cutoff_time.timestamp()
                    
                    # Filter by published_date using numeric timestamp (not when ingested)
                    filter_conditions.append(
                        FieldCondition(
                            key="published_timestamp",
                            range=Range(gte=cutoff_timestamp)
                        )
                    )
                    print(f"📅 Filtering papers published after: {cutoff_time.isoformat()} (timestamp: {cutoff_timestamp})")
                
            # Create filter object if conditions exist
            qdrant_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # Query database
            result = self.client.scroll(
                collection_name=self.config.collection_name,
                scroll_filter=qdrant_filter,
                limit=limit
            )
            
            papers = []
            for point in result[0]:
                paper = point.payload.copy()
                paper['id'] = point.id
                papers.append(paper)
            
            return papers
            
        except Exception as e:
            print(f"❌ Error getting papers: {e}")
            return []
    
    def get_papers_with_content(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get papers with full content for analysis"""
        papers = self.get_papers({'hours_back': hours_back})
        
        # Filter papers with PDF content
        papers_with_content = []
        for paper in papers:
            if paper.get('pdf_text') or paper.get('pdf_path'):
                papers_with_content.append(paper)
        
        return papers_with_content
    
    def paper_exists(self, url: str, title: Optional[str] = None) -> bool:
        """Check if a paper already exists in the database"""
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            # Check by URL first
            result = self.client.scroll(
                collection_name=self.config.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="url", match=MatchValue(value=url))]
                ),
                limit=1
            )
            
            if result[0]:
                return True
            
            # Check by title if provided
            if title:
                result = self.client.scroll(
                    collection_name=self.config.collection_name,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="title", match=MatchValue(value=title))]
                    ),
                    limit=1
                )
                
                if result[0]:
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking if paper exists: {e}")
            return False
    
    def clear_collection(self, collection_name: Optional[str] = None) -> bool:
        """Clear a collection from the database"""
        if not self.connected:
            if not self.connect():
                return False
        
        collection_name = collection_name or self.config.collection_name
        
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                print(f"ℹ️ Collection '{collection_name}' does not exist. Nothing to clear.")
                return True
            
            # Get current count
            collection_info = self.client.get_collection(collection_name)
            current_count = collection_info.points_count
            
            if current_count == 0:
                print("ℹ️ Database is already empty.")
                return True
            
            print(f"🗑️ Deleting collection '{collection_name}' with {current_count} papers...")
            self.client.delete_collection(collection_name)
            print("✅ Collection deleted successfully!")
            
            return True
            
        except Exception as e:
            print(f"❌ Error clearing collection: {e}")
            return False
    
    def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about a collection"""
        if not self.connected:
            if not self.connect():
                return {"error": "Not connected"}
        
        collection_name = collection_name or self.config.collection_name
        
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                return {"error": f"Collection '{collection_name}' not found"}
            
            collection_info = self.client.get_collection(collection_name)
            
            return {
                "name": collection_name,
                "points_count": collection_info.points_count,
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance.value
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_paper_id(self, paper: Dict[str, Any]) -> str:
        """Generate a unique ID for a paper"""
        # Use URL hash as ID
        url = paper.get('url', '')
        if url:
            return hashlib.md5(url.encode()).hexdigest()
        
        # Fallback to title hash
        title = paper.get('title', '')
        if title:
            return hashlib.md5(title.encode()).hexdigest()
        
        # Final fallback
        return hashlib.md5(str(datetime.now()).encode()).hexdigest()
    
    def _calculate_paper_hash(self, paper: Dict[str, Any]) -> str:
        """Calculate a hash of paper content for change detection"""
        content = f"{paper.get('title', '')}{paper.get('abstract', '')}{paper.get('url', '')}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def is_connected(self) -> bool:
        """Check if connected to database"""
        return self.connected
