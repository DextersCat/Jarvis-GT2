#!/usr/bin/env python3
"""
Vault Index Generator for Jarvis GT2
Creates a memory/index file documenting all folders and code files
for Jarvis to reference when understanding file requests.

Example: "Check main file" → jarvisgt2.py
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set

# Configuration
VAULT_ROOT = r'C:\Users\spencer\Documents\Projects'
INDEX_OUTPUT = 'vault_index.json'
CODE_EXTENSIONS = {'.py', '.json', '.bat', '.js', '.ts', '.html', '.css', '.md', '.yaml', '.yml', '.xml'}
IGNORE_FOLDERS = {'.git', '.venv', '__pycache__', '.pytest_cache', 'node_modules', '.vscode', '.idea'}


class VaultIndexer:
    def __init__(self, vault_root: str):
        self.vault_root = Path(vault_root)
        self.index_data = {
            'created': datetime.now().isoformat(),
            'vault_root': str(self.vault_root),
            'projects': {},
            'file_reference_map': {}  # Maps common names to actual files
        }
    
    def scan_vault(self):
        """Recursively scan vault and catalog all projects and files."""
        print(f"\n{'='*70}")
        print("🔍 VAULT INDEXER - CREATING MEMORY FILE")
        print(f"{'='*70}")
        print(f"\n📁 Scanning vault: {self.vault_root}\n")
        
        for project_folder in self.vault_root.iterdir():
            if project_folder.is_dir() and project_folder.name not in IGNORE_FOLDERS:
                self._index_project(project_folder)
        
        # Create reference map for common file queries
        self._build_reference_map()
        
        print("\n" + "="*70)
    
    def _index_project(self, project_path: Path):
        """Index a single project folder."""
        project_name = project_path.name
        print(f"  📂 Project: {project_name}")
        
        self.index_data['projects'][project_name] = {
            'path': str(project_path),
            'folders': {},
            'root_files': {}
        }
        
        # Get files in project root
        root_files = self._get_code_files(project_path)
        if root_files:
            self.index_data['projects'][project_name]['root_files'] = root_files
            print(f"     📄 Root files: {len(root_files)}")
            for fname in sorted(root_files.keys()):
                print(f"        • {fname}")
        
        # Get all subdirectories
        for item in sorted(project_path.iterdir()):
            if item.is_dir() and item.name not in IGNORE_FOLDERS:
                self._index_folder(item, project_name, project_path)
    
    def _index_folder(self, folder_path: Path, project_name: str, project_root: Path):
        """Index a subfolder within a project."""
        rel_path = folder_path.relative_to(project_root)
        folder_key = str(rel_path)
        
        code_files = self._get_code_files(folder_path)
        
        if code_files:
            print(f"     📁 {folder_key}/ ({len(code_files)} files)")
            self.index_data['projects'][project_name]['folders'][folder_key] = code_files
            for fname in sorted(code_files.keys()):
                print(f"        • {fname}")
        
        # Recursively check subdirs
        for item in sorted(folder_path.iterdir()):
            if item.is_dir() and item.name not in IGNORE_FOLDERS:
                self._index_folder(item, project_name, project_root)
    
    def _get_code_files(self, folder_path: Path) -> Dict[str, str]:
        """Get all code files in a folder (non-recursive, one level only)."""
        code_files = {}
        
        try:
            for item in folder_path.iterdir():
                if item.is_file() and item.suffix.lower() in CODE_EXTENSIONS:
                    code_files[item.name] = str(item)
        except PermissionError:
            pass
        
        return code_files
    
    def _build_reference_map(self):
        """Build a map of common queries to actual files."""
        print("\n📚 Building file reference map...")
        
        reference_map = {
            'main': [],
            'startup': [],
            'config': [],
            'test': [],
            'utils': [],
            'memory': [],
            'ear': [],
        }
        
        for project_name, project_data in self.index_data['projects'].items():
            # Root files
            for fname, fpath in project_data['root_files'].items():
                fname_lower = fname.lower()
                
                if 'main' in fname_lower:
                    reference_map['main'].append({'file': fname, 'path': fpath, 'project': project_name})
                if 'start' in fname_lower or 'jarvis' in fname_lower and fname_lower.endswith('.py'):
                    reference_map['startup'].append({'file': fname, 'path': fpath, 'project': project_name})
                if 'config' in fname_lower:
                    reference_map['config'].append({'file': fname, 'path': fpath, 'project': project_name})
                if 'test' in fname_lower:
                    reference_map['test'].append({'file': fname, 'path': fpath, 'project': project_name})
                if 'memory' in fname_lower:
                    reference_map['memory'].append({'file': fname, 'path': fpath, 'project': project_name})
                if 'ear' in fname_lower:
                    reference_map['ear'].append({'file': fname, 'path': fpath, 'project': project_name})
            
            # Subfolder files
            for folder, files in project_data['folders'].items():
                for fname, fpath in files.items():
                    fname_lower = fname.lower()
                    
                    if 'util' in folder.lower():
                        reference_map['utils'].append({'file': fname, 'path': fpath, 'project': project_name, 'folder': folder})
                    if 'test' in fname_lower:
                        reference_map['test'].append({'file': fname, 'path': fpath, 'project': project_name, 'folder': folder})
        
        # Clean up empty entries
        self.index_data['file_reference_map'] = {k: v for k, v in reference_map.items() if v}
        
        print(f"\n📍 Reference Map Summary:")
        for ref_type, matches in self.index_data['file_reference_map'].items():
            print(f"   • {ref_type}: {len(matches)} file(s)")
    
    def save_index(self, output_file: str = INDEX_OUTPUT):
        """Save index to JSON file."""
        output_path = self.vault_root / 'New_Jarvis' / output_file
        
        with open(output_path, 'w') as f:
            json.dump(self.index_data, f, indent=2)
        
        print(f"\n✅ Index saved to: {output_path}")
        return output_path
    
    def print_summary(self):
        """Print summary statistics."""
        total_projects = len(self.index_data['projects'])
        total_folders = sum(len(p['folders']) for p in self.index_data['projects'].values())
        total_files = sum(
            len(p['root_files']) + sum(len(f) for f in p['folders'].values())
            for p in self.index_data['projects'].values()
        )
        
        print(f"\n📊 VAULT SUMMARY:")
        print(f"   • Projects: {total_projects}")
        print(f"   • Folders: {total_folders}")
        print(f"   • Code Files: {total_files}")
        print(f"   • Reference Types: {len(self.index_data['file_reference_map'])}")
        print(f"\n{'='*70}\n")


def demo_query(index_data: Dict):
    """Demonstrate how Jarvis would use the index."""
    print("🤖 DEMO: How Jarvis would use this index\n")
    
    demo_queries = [
        ("Check main file", "main"),
        ("Run startup", "startup"),
        ("Load config", "config"),
        ("Run memory test", "memory"),
    ]
    
    for query, ref_type in demo_queries:
        print(f"User: '{query}'")
        if ref_type in index_data['file_reference_map']:
            matches = index_data['file_reference_map'][ref_type]
            if matches:
                print(f"Jarvis: Found {len(matches)} match(es):")
                for match in matches[:2]:  # Show top 2 matches
                    if 'folder' in match:
                        print(f"  → {match['file']} (in {match['folder']})")
                    else:
                        print(f"  → {match['file']} ({match['project']})")
            else:
                print(f"Jarvis: No matches found for '{ref_type}'")
        print()


if __name__ == '__main__':
    try:
        # Create indexer
        indexer = VaultIndexer(VAULT_ROOT)
        
        # Scan vault
        indexer.scan_vault()
        
        # Save index
        indexer.save_index(INDEX_OUTPUT)
        
        # Print summary
        indexer.print_summary()
        
        # Demo reference lookups
        demo_query(indexer.index_data)
        
        print("✨ Vault index created successfully!")
        print(f"Jarvis can now reference files using: vault_index.json\n")
        
    except Exception as e:
        print(f"\n❌ Error creating vault index: {e}")
        import traceback
        traceback.print_exc()
