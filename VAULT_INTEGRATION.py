"""
INTEGRATION GUIDE: Using VaultReference in Jarvis

This shows how to integrate the vault indexing system into jarvisgt2.py
for intelligent file reference resolution.

SETUP:
------
1. Keep vault_reference.py in the project root
2. Keep vault_index.json in the project root
3. Regenerate index periodically: python create_vault_index.py

BASIC USAGE IN JARVISGT2:
------------------------
"""

from vault_reference import VaultReference
import os


# ============================================================================
# EXAMPLE 1: Initialize VaultReference in Jarvis __init__
# ============================================================================

def jarvis_init_example():
    """Add this to JarvisGT2 class __init__ method."""
    
    # Load vault reference for intelligent file resolution
    self.vault = VaultReference()
    
    if not self.vault.is_loaded:
        print("Warning: Vault index not available. File searches may be limited.")


# ============================================================================
# EXAMPLE 2: Handle user requests for files
# ============================================================================

def process_file_request(user_request: str) -> str:
    """
    When user says things like:
      - "Check my main file"
      - "Load config"
      - "Show me the startup"
    
    This resolves them to actual files.
    """
    
    vault = VaultReference()
    
    request_lower = user_request.lower()
    
    # Map common phrases to reference types
    file_references = {
        'main': ['main file', 'main script', 'main program'],
        'config': ['config', 'configuration', 'settings'],
        'startup': ['startup', 'start', 'launcher', 'initialization'],
        'test': ['test', 'testing', 'tests'],
        'memory': ['memory', 'memories', 'saved memory', 'persistent data'],
        'ear': ['ear', 'listening', 'speech', 'audio'],
    }
    
    # Find which reference type matches
    for ref_type, phrases in file_references.items():
        for phrase in phrases:
            if phrase in request_lower:
                file_path = vault.get_file(ref_type)
                if file_path:
                    return file_path
    
    return None


# ============================================================================
# EXAMPLE 3: Ask Jarvis to find a file
# ============================================================================

def jarvis_find_file_method(filename: str) -> str:
    """
    Add this method to JarvisGT2 class.
    
    Usage: path = self.find_project_file('jarvisgt2.py')
    """
    vault = VaultReference()
    path = vault.search_file(filename)
    
    if path and os.path.exists(path):
        return path
    else:
        return None


# ============================================================================
# EXAMPLE 4: Get all test files (for running all tests)
# ============================================================================

def get_all_tests() -> list:
    """Get all test files in project."""
    vault = VaultReference()
    test_files = vault.get_files('test')
    
    # Filter to only .py files
    return [f for f in test_files if f.endswith('.py')]


# ============================================================================
# EXAMPLE 5: Display project structure to user
# ============================================================================

def show_project_structure():
    """Display organized project structure."""
    vault = VaultReference()
    structure = vault.get_project_structure('New_Jarvis')
    
    print("\n📂 Project Structure:")
    print(f"\n  Root Files ({len(structure.get('root_files', {}))} total):")
    
    for filename in sorted(structure.get('root_files', {}).keys())[:10]:
        print(f"    • {filename}")
    
    if len(structure.get('root_files', {})) > 10:
        print(f"    ... and {len(structure.get('root_files', {})) - 10} more")


# ============================================================================
# COMPLETE INTEGRATION EXAMPLE
# ============================================================================

class JarvisVaultIntegration:
    """
    Complete example of how to integrate VaultReference into Jarvis.
    """
    
    def __init__(self):
        """Initialize Jarvis with vault reference."""
        self.vault = VaultReference()
        self.project_files = {}
        self.reference_map = {}
        
        if self.vault.is_loaded:
            self._cache_file_map()
    
    def _cache_file_map(self):
        """Pre-cache common file references for quick lookup."""
        self.reference_map = {
            'main': self.vault.get_file('main'),
            'config': self.vault.get_file('config'),
            'startup': self.vault.get_file('startup'),
            'memory': self.vault.get_file('memory'),
            'ear': self.vault.get_file('ear'),
        }
    
    def understand_file_reference(self, user_utterance: str) -> str:
        """
        Intelligently resolve user reference to actual file.
        
        Examples:
            "Check main" → jarvis_main.py
            "Load config" → config.json
            "Show startup" → jarvisgt2.py
            "What's in earpy" → jarvis_ear.py
        """
        utterance = user_utterance.lower()
        
        # Direct cache lookup first
        for ref_type, filepath in self.reference_map.items():
            if ref_type in utterance and filepath:
                return filepath
        
        # Fuzzy search for exact filename
        filename_match = self.vault.search_file(user_utterance)
        if filename_match:
            return filename_match
        
        return None
    
    def get_file_contents(self, reference: str) -> str:
        """Get the full path to a referenced file."""
        filepath = self.understand_file_reference(reference)
        
        if filepath and os.path.exists(filepath):
            return filepath
        
        return None


# ============================================================================
# HOW TO USE IN JARVISGT2.PY
# ============================================================================

"""
In jarvisgt2.py, add this to the JarvisGT2 class:

    def __init__(self, root=None):
        # ... existing init code ...
        
        # Add vault reference system
        self.vault = VaultReference()
        if self.vault.is_loaded:
            print("✓ Vault index loaded - file reference system active")
        
    def process_user_request_new(self, user_text: str):
        # When user mentions a file, Jarvis can now understand:
        
        if 'check' in user_text and 'file' in user_text:
            file_path = self.vault.get_file('main')
            if file_path:
                print(f"Opening {file_path}...")
        
        elif 'config' in user_text:
            config_file = self.vault.get_file('config')
            if config_file:
                print(f"Loading {config_file}...")
        
        elif 'test' in user_text:
            test_files = self.vault.get_files('test')
            print(f"Found {len(test_files)} test files")

"""

if __name__ == '__main__':
    print("📚 VaultReference Integration Guide\n")
    print("This file shows how to integrate the vault indexing system.")
    print("See the examples above for implementation details.\n")
    
    # Quick demo
    print("Quick Demo:")
    print("-" * 50)
    
    integration = JarvisVaultIntegration()
    
    test_queries = [
        "Check main file",
        "Load config",
        "Show startup",
        "What's in memory",
    ]
    
    for query in test_queries:
        result = integration.understand_file_reference(query)
        if result:
            filename = os.path.basename(result)
            print(f"User: '{query}'")
            print(f"Jarvis: Found → {filename}\n")
