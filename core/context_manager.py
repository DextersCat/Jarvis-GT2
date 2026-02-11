from datetime import date
from collections import defaultdict
from typing import List, Dict, Optional, Any

class ShortKeyGenerator:
    """Generates persistent, date-based short keys for session items."""
    def __init__(self):
        self._today = date.today()
        self._counters = defaultdict(int)

    def _reset_if_new_day(self):
        """Resets counters if the date has changed."""
        today = date.today()
        if today != self._today:
            self._today = today
            self._counters.clear()

    def generate(self, item_type: str) -> str:
        """Generate a new short key for a given item type."""
        self._reset_if_new_day()
        self._counters[item_type] += 1
        date_str = self._today.strftime('%Y%m%d')
        # Ensure 'wr' for web results is handled correctly
        type_prefix = 'wr' if item_type == 'w' else item_type
        return f"{date_str}-{type_prefix}{self._counters[item_type]}"

class SessionContext:
    """Manages volatile 'working memory' for the current user session."""
    def __init__(self):
        self.items: Dict[str, Dict[str, Any]] = {} # short_alias -> item_data

    def add_item(self, full_key: str, label: str, item_type: str, metadata: Dict):
        """Adds an item to the session context."""
        short_alias = full_key.split('-')[-1]
        self.items[short_alias] = {
            'full_key': full_key,
            'label': label,
            'type': item_type,
            'metadata': metadata
        }

    def get_item(self, short_alias: str) -> Optional[Dict]:
        """Retrieves an item by its short alias."""
        return self.items.get(short_alias)

    def get_all_items_for_ticker(self) -> List[Dict]:
        """Returns all items formatted for the dashboard ticker."""
        return [
            {'short_key': key, 'label': item['label']}
            for key, item in self.items.items()
        ]

    def clear(self):
        """Clears the session context."""
        self.items.clear()

class ConversationalLedger:
    """Manages the persistent, long-term memory ledger using MemoryIndex."""
    def __init__(self, memory_index, short_key_generator):
        self.memory_index = memory_index
        self.short_key_generator = short_key_generator

    def add_entry(self, item_type: str, description: str, metadata: Dict) -> Dict:
        """Adds a new entry to the ledger, assigns a short key, and saves it."""
        short_key = self.short_key_generator.generate(item_type)
        metadata_with_key = metadata.copy()
        metadata_with_key['short_key'] = short_key
        
        action = self.memory_index.add_action(
            action_type=item_type,
            description=description,
            metadata=metadata_with_key
        )
        return action