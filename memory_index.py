"""
Jarvis Memory Index System
Efficient indexed storage and retrieval for unlimited action history.
"""
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Optional, Any
import bisect


class MemoryIndex:
    """
    Indexed memory system for fast searching across unlimited actions.
    
    Features:
    - Unlimited action storage (no artificial limits)
    - Fast lookup by action_type, date range, keywords
    - Automatic indexing on load/save
    - Efficient search without loading entire history
    """
    
    def __init__(self, memory_file="jarvis_memory.json", index_file="jarvis_memory_index.json"):
        self.memory_file = memory_file
        self.index_file = index_file
        self.actions = []  # Full action history
        self.index = {
            "by_type": defaultdict(list),      # action_type -> [indices]
            "by_date": [],                      # sorted list of (date, index) tuples
            "by_keyword": defaultdict(set),     # keyword -> {indices}
            "total_count": 0
        }
        self.load()
    
    def load(self):
        """Load actions and rebuild index from memory file."""
        if not os.path.exists(self.memory_file):
            return
        
        try:
            with open(self.memory_file, 'r') as f:
                memory = json.load(f)
            
            self.actions = memory.get('vault_actions', [])
            self._rebuild_index()
            
        except Exception as e:
            print(f"Error loading memory index: {e}")
    
    def _rebuild_index(self):
        """Rebuild all indexes from current actions."""
        self.index = {
            "by_type": defaultdict(list),
            "by_date": [],
            "by_keyword": defaultdict(set),
            "total_count": len(self.actions)
        }
        
        for idx, action in enumerate(self.actions):
            # Index by action type
            action_type = action.get('action_type', 'unknown')
            self.index['by_type'][action_type].append(idx)
            
            # Index by date (for fast date range queries)
            timestamp = action.get('timestamp')
            if timestamp:
                self.index['by_date'].append((timestamp, idx))
            
            # Index by keywords (from description and metadata)
            keywords = self._extract_keywords(action)
            for keyword in keywords:
                self.index['by_keyword'][keyword].add(idx)
        
        # Sort date index for binary search
        self.index['by_date'].sort()
    
    def _extract_keywords(self, action: Dict) -> List[str]:
        """Extract searchable keywords from action."""
        keywords = []
        
        # From description
        description = action.get('description', '').lower()
        keywords.extend(description.split())
        
        # From metadata
        metadata = action.get('metadata', {})
        for key, value in metadata.items():
            if isinstance(value, str):
                keywords.append(value.lower())
            elif key == 'filename':
                keywords.append(value.lower().replace('.', ' ').replace('_', ' '))
        
        # Clean and deduplicate
        return list(set(k for k in keywords if len(k) > 2))
    
    def add_action(self, action_type: str, description: str, metadata: Optional[Dict] = None):
        """Add new action and update indexes."""
        action = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'description': description,
            'metadata': metadata or {}
        }
        
        idx = len(self.actions)
        self.actions.append(action)
        
        # Update indexes incrementally
        self.index['by_type'][action_type].append(idx)
        self.index['total_count'] += 1
        
        timestamp = action['timestamp']
        bisect.insort(self.index['by_date'], (timestamp, idx))
        
        keywords = self._extract_keywords(action)
        for keyword in keywords:
            self.index['by_keyword'][keyword].add(idx)
        
        return action
    
    def search_by_type(self, action_type: str, limit: int = 50) -> List[Dict]:
        """Get recent actions of a specific type."""
        indices = self.index['by_type'].get(action_type, [])
        # Return most recent first
        return [self.actions[i] for i in reversed(indices[-limit:])]
    
    def search_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get all actions within a date range."""
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()
        
        # Binary search for start position
        start_idx = bisect.bisect_left(self.index['by_date'], (start_iso, 0))
        end_idx = bisect.bisect_right(self.index['by_date'], (end_iso, float('inf')))
        
        indices = [idx for _, idx in self.index['by_date'][start_idx:end_idx]]
        return [self.actions[i] for i in indices]
    
    def search_by_keyword(self, keyword: str, limit: int = 50) -> List[Dict]:
        """Search actions by keyword (filename, description, metadata)."""
        keyword = keyword.lower()
        
        # Exact match
        if keyword in self.index['by_keyword']:
            indices = list(self.index['by_keyword'][keyword])[-limit:]
            return [self.actions[i] for i in reversed(indices)]
        
        # Partial match
        matching_indices = set()
        for kw, idx_set in self.index['by_keyword'].items():
            if keyword in kw:
                matching_indices.update(idx_set)
        
        indices = sorted(matching_indices)[-limit:]
        return [self.actions[i] for i in reversed(indices)]
    
    def get_last_n(self, n: int = 50) -> List[Dict]:
        """Get last N actions (most recent first)."""
        return list(reversed(self.actions[-n:]))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "total_actions": self.index['total_count'],
            "action_types": {k: len(v) for k, v in self.index['by_type'].items()},
            "oldest_action": self.actions[0]['timestamp'] if self.actions else None,
            "newest_action": self.actions[-1]['timestamp'] if self.actions else None,
            "unique_keywords": len(self.index['by_keyword']),
            "memory_size_kb": os.path.getsize(self.memory_file) / 1024 if os.path.exists(self.memory_file) else 0
        }
    
    def save(self, full_memory: Dict):
        """Save actions back to memory file (called by main save_memory)."""
        full_memory['vault_actions'] = self.actions
        
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(full_memory, f, indent=2)
            
            # Save separate index file for fast startup (optional optimization)
            with open(self.index_file, 'w') as f:
                json.dump({
                    'by_type': {k: list(v) for k, v in self.index['by_type'].items()},
                    'by_date': self.index['by_date'],
                    'total_count': self.index['total_count']
                }, f)
        except Exception as e:
            print(f"Error saving memory index: {e}")
