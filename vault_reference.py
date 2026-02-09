#!/usr/bin/env python3
"""
vault_reference.py - Helper module for Jarvis to query the vault index

Usage in jarvisgt2.py:
    from vault_reference import VaultReference
    
    vault = VaultReference()
    
    # Query examples:
    filename = vault.get_file('main')  # Returns jarvis_main.py path
    config = vault.get_file('config')  # Returns config.json path
    tests = vault.get_files('test')    # Returns list of all test files
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict


class VaultReference:
    """
    Loads and queries the vault index to help Jarvis understand
    file references and navigate the project structure.
    """
    
    def __init__(self, index_file: str = 'vault_index.json'):
        self.index_file = Path(index_file)
        self.index_data = None
        self.is_loaded = False
        self.load_index()
    
    def load_index(self) -> bool:
        """Load the vault index from JSON file."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r') as f:
                    self.index_data = json.load(f)
                self.is_loaded = True
                print(f"✓ Vault index loaded from {self.index_file}")
                return True
            else:
                print(f"⚠ Index file not found: {self.index_file}")
                print("  Run 'python create_vault_index.py' to generate it.")
                return False
        except Exception as e:
            print(f"✗ Error loading vault index: {e}")
            return False
    
    def get_file(self, reference_type: str) -> Optional[str]:
        """
        Get the most likely file for a reference type.
        
        Args:
            reference_type: 'main', 'startup', 'config', 'test', 'memory', 'ear'
        
        Returns:
            Path to the file or None if not found
        """
        if not self.is_loaded or not self.index_data:
            return None
        
        ref_map = self.index_data.get('file_reference_map', {})
        
        if reference_type.lower() in ref_map:
            matches = ref_map[reference_type.lower()]
            if matches:
                return matches[0]['path']  # Return first/best match
        
        return None
    
    def get_files(self, reference_type: str) -> List[str]:
        """
        Get all files matching a reference type.
        
        Args:
            reference_type: 'main', 'startup', 'config', 'test', 'memory', 'ear'
        
        Returns:
            List of file paths matching the reference
        """
        if not self.is_loaded or not self.index_data:
            return []
        
        ref_map = self.index_data.get('file_reference_map', {})
        
        if reference_type.lower() in ref_map:
            matches = ref_map[reference_type.lower()]
            return [match['path'] for match in matches]
        
        return []
    
    def get_project_structure(self, project_name: str = 'New_Jarvis') -> Dict:
        """
        Get the complete structure of a project.
        
        Returns:
            Dictionary containing files and folders
        """
        if not self.is_loaded or not self.index_data:
            return {}
        
        projects = self.index_data.get('projects', {})
        return projects.get(project_name, {})
    
    def list_all_files(self, project_name: str = 'New_Jarvis') -> List[str]:
        """Get all code files in a project."""
        if not self.is_loaded or not self.index_data:
            return []
        
        project = self.get_project_structure(project_name)
        files = []
        
        # Root files
        for fname, fpath in project.get('root_files', {}).items():
            files.append(fpath)
        
        # Files in subfolders
        for folder, folder_files in project.get('folders', {}).items():
            for fname, fpath in folder_files.items():
                files.append(fpath)
        
        return files
    
    def search_file(self, filename: str) -> Optional[str]:
        """
        Search for a file by name.
        
        Args:
            filename: Name of the file to search for
        
        Returns:
            Path to the file if found
        """
        if not self.is_loaded or not self.index_data:
            return None
        
        filename_lower = filename.lower()
        
        for project_name, project_data in self.index_data.get('projects', {}).items():
            # Check root files
            for fname, fpath in project_data.get('root_files', {}).items():
                if fname.lower() == filename_lower:
                    return fpath
            
            # Check subfolders
            for folder, folder_files in project_data.get('folders', {}).items():
                for fname, fpath in folder_files.items():
                    if fname.lower() == filename_lower:
                        return fpath
        
        return None
    
    def get_summary(self) -> Dict:
        """Get summary statistics about the vault."""
        if not self.is_loaded or not self.index_data:
            return {}
        
        total_projects = len(self.index_data.get('projects', {}))
        total_files = sum(
            len(p.get('root_files', {})) + sum(len(f) for f in p.get('folders', {}).values())
            for p in self.index_data.get('projects', {}).values()
        )
        ref_types = len(self.index_data.get('file_reference_map', {}))
        
        return {
            'created': self.index_data.get('created'),
            'vault_root': self.index_data.get('vault_root'),
            'total_projects': total_projects,
            'total_files': total_files,
            'reference_types': ref_types
        }


def demo_vault_reference():
    """Demonstrate how Jarvis would use the VaultReference class."""
    print("\n" + "="*70)
    print("🤖 DEMO: Jarvis using VaultReference Helper")
    print("="*70 + "\n")
    
    vault = VaultReference()
    
    if not vault.is_loaded:
        print("Index not loaded! Please run: python create_vault_index.py\n")
        return
    
    print("📊 Vault Summary:")
    summary = vault.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print("\n🔍 Example Queries:\n")
    
    # Test various queries
    queries = [
        ("main", "get_file"),
        ("startup", "get_file"),
        ("config", "get_file"),
        ("test", "get_files"),
        ("memory", "get_file"),
    ]
    
    for query, method in queries:
        if method == "get_file":
            result = vault.get_file(query)
            if result:
                filename = Path(result).name
                print(f"  Query: 'main file' → {filename}")
                print(f"    Full path: {result}\n")
        else:
            results = vault.get_files(query)
            if results:
                print(f"  Query: 'test files' → Found {len(results)} file(s)")
                for r in results[:3]:  # Show first 3
                    print(f"    • {Path(r).name}")
                if len(results) > 3:
                    print(f"    ... and {len(results) - 3} more")
                print()
    
    print("🔎 File Search Example:")
    searched_file = vault.search_file('jarvisgt2.py')
    if searched_file:
        print(f"  Finding 'jarvisgt2.py' → {searched_file}\n")
    
    print("="*70 + "\n")


if __name__ == '__main__':
    demo_vault_reference()
