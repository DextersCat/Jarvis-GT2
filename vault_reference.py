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
from datetime import datetime


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

    def _iter_code_files(self, root: Path):
        """Yield code/docs files beneath root, skipping noisy folders."""
        code_ext = {'.py', '.json', '.bat', '.js', '.ts', '.html', '.css', '.md', '.yaml', '.yml', '.xml', '.txt'}
        ignore = {'.git', '.venv', '__pycache__', '.pytest_cache', 'node_modules', '.vscode', '.idea'}
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ignore]
            for fname in files:
                path = Path(base) / fname
                if path.suffix.lower() in code_ext:
                    yield path

    def _total_files_count(self) -> int:
        """Count indexed file entries."""
        if not self.index_data:
            return 0
        total = 0
        for pdata in self.index_data.get('projects', {}).values():
            total += len(pdata.get('root_files', {}))
            total += sum(len(folder_files) for folder_files in pdata.get('folders', {}).values())
        return total

    def _build_reference_map(self, projects_map: Dict) -> Dict:
        """Build minimal reference map from current project structure."""
        reference_map = {
            'main': [], 'startup': [], 'config': [], 'test': [], 'utils': [], 'memory': [], 'ear': []
        }
        for project_name, project_data in projects_map.items():
            for fname, fpath in project_data.get('root_files', {}).items():
                lower = fname.lower()
                if 'main' in lower:
                    reference_map['main'].append({'file': fname, 'path': fpath, 'project': project_name})
                if ('start' in lower) or ('jarvis' in lower and lower.endswith('.py')):
                    reference_map['startup'].append({'file': fname, 'path': fpath, 'project': project_name})
                if 'config' in lower:
                    reference_map['config'].append({'file': fname, 'path': fpath, 'project': project_name})
                if 'test' in lower:
                    reference_map['test'].append({'file': fname, 'path': fpath, 'project': project_name})
                if 'memory' in lower:
                    reference_map['memory'].append({'file': fname, 'path': fpath, 'project': project_name})
                if 'ear' in lower:
                    reference_map['ear'].append({'file': fname, 'path': fpath, 'project': project_name})
            for folder, files in project_data.get('folders', {}).items():
                for fname, fpath in files.items():
                    lower = fname.lower()
                    if 'util' in folder.lower():
                        reference_map['utils'].append({'file': fname, 'path': fpath, 'project': project_name, 'folder': folder})
                    if 'test' in lower:
                        reference_map['test'].append({'file': fname, 'path': fpath, 'project': project_name, 'folder': folder})
        return {k: v for k, v in reference_map.items() if v}

    def scan(self) -> Dict[str, int]:
        """Refresh vault index from filesystem and persist.

        Returns:
            dict with total_files and new_files.
        """
        root_str = None
        if self.index_data:
            root_str = self.index_data.get('vault_root')
        root = Path(root_str) if root_str else Path(r'C:\Users\spencer\Documents\Projects')
        old_total = self._total_files_count()

        projects = {}
        if root.exists() and root.is_dir():
            for project_folder in root.iterdir():
                if not project_folder.is_dir():
                    continue
                if project_folder.name in {'.git', '.venv', '__pycache__', 'node_modules'}:
                    continue
                pdata = {'path': str(project_folder), 'folders': {}, 'root_files': {}}
                for path in self._iter_code_files(project_folder):
                    rel = path.relative_to(project_folder)
                    if len(rel.parts) == 1:
                        pdata['root_files'][path.name] = str(path)
                    else:
                        folder = str(rel.parent)
                        pdata['folders'].setdefault(folder, {})
                        pdata['folders'][folder][path.name] = str(path)
                projects[project_folder.name] = pdata

        self.index_data = {
            'created': datetime.now().isoformat(),
            'vault_root': str(root),
            'projects': projects,
            'file_reference_map': self._build_reference_map(projects)
        }

        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index_data, f, indent=2)
        except Exception:
            # Keep in-memory refresh even if disk write fails.
            pass

        self.is_loaded = True
        new_total = self._total_files_count()
        return {'total_files': new_total, 'new_files': max(0, new_total - old_total)}

    def quick_scan(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Quick filename scan directly on filesystem for newly created files."""
        query_l = (query or '').strip().lower()
        if not query_l:
            return []

        root_str = None
        if self.index_data:
            root_str = self.index_data.get('vault_root')
        root = Path(root_str) if root_str else Path(r'C:\Users\spencer\Documents\Projects')
        if not root.exists():
            return []

        hits = []
        for path in self._iter_code_files(root):
            name_l = path.name.lower()
            if query_l in name_l:
                score = 2 if name_l == query_l else 1
                hits.append({
                    'path': str(path),
                    'name': path.name,
                    'project': path.parts[4] if len(path.parts) > 4 else '',
                    'score': score
                })

        hits.sort(key=lambda h: (-h['score'], h['name']))
        return hits[:limit]


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
