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
import math
import re
import hashlib
import difflib

try:
    import openvino_genai as ov_genai  # type: ignore
    OPENVINO_GENAI_AVAILABLE = True
except ImportError:
    ov_genai = None
    OPENVINO_GENAI_AVAILABLE = False


class VaultReference:
    """
    Loads and queries the vault index to help Jarvis understand
    file references and navigate the project structure.
    """
    
    def __init__(
        self,
        index_file: str = 'vault_index.json',
        semantic_index_file: str = 'vault_semantic_index.json',
        vector_cache_file: str = 'vector_cache.json'
    ):
        self.index_file = Path(index_file)
        self.semantic_index_file = Path(semantic_index_file)
        self.vector_cache_file = Path(vector_cache_file)
        self.index_data = None
        self.is_loaded = False
        self.semantic_index_data = {"created": None, "entries": {}}
        self.embedding_model_dir = os.getenv("VAULT_EMBED_MODEL_DIR", "models/embeddings-all-minilm-l6-v2-openvino")
        self.embedding_device_order = [
            d.strip().upper() for d in os.getenv("VAULT_EMBED_DEVICE_ORDER", "NPU,AUTO,CPU").split(",") if d.strip()
        ]
        self.embedding_pipeline = None
        self.embedding_backend = "hash"
        self.embedding_device = "cpu"
        self.load_index()
        self._load_semantic_index()
        self._init_embedding_runtime()
    
    def load_index(self) -> bool:
        """Load the vault index from JSON file."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r') as f:
                    self.index_data = json.load(f)
                self.is_loaded = True
                print(f"[OK] Vault index loaded from {self.index_file}")
                return True
            else:
                print(f"[WARN] Index file not found: {self.index_file}")
                print("  Run 'python create_vault_index.py' to generate it.")
                return False
        except Exception as e:
            print(f"[ERR] Error loading vault index: {e}")
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

    def _load_semantic_index(self) -> bool:
        """Load semantic index from disk if available."""
        try:
            for source in (self.vector_cache_file, self.semantic_index_file):
                if source.exists():
                    with open(source, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "entries" in data:
                        self.semantic_index_data = data
                        return True
        except Exception:
            pass
        self.semantic_index_data = {"created": None, "entries": {}}
        return False

    def _save_semantic_index(self) -> None:
        """Persist semantic index to legacy and vector cache files; best effort."""
        try:
            with open(self.semantic_index_file, 'w', encoding='utf-8') as f:
                json.dump(self.semantic_index_data, f, indent=2)
        except Exception:
            pass
        try:
            with open(self.vector_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.semantic_index_data, f, indent=2)
        except Exception:
            pass

    def _init_embedding_runtime(self) -> None:
        """Initialize embedding runtime, preferring OpenVINO on NPU."""
        model_dir = Path(self.embedding_model_dir)
        if not OPENVINO_GENAI_AVAILABLE or not model_dir.exists():
            return

        for device in self.embedding_device_order:
            try:
                self.embedding_pipeline = ov_genai.TextEmbeddingPipeline(str(model_dir), device)
                self.embedding_backend = "openvino"
                self.embedding_device = device
                return
            except Exception:
                continue

    def _hash_embedding(self, text: str, dims: int = 192) -> List[float]:
        """Deterministic lightweight embedding fallback."""
        vec = [0.0] * dims
        tokens = re.findall(r"[a-z0-9_./-]+", (text or "").lower())
        if not tokens:
            return vec

        def stable_bucket(token: str) -> int:
            digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
            return int(digest[:8], 16) % dims

        for token in tokens:
            idx = stable_bucket(token)
            vec[idx] += 1.0
            # add basic character n-gram signal
            if len(token) > 3:
                tri = token[:3]
                vec[stable_bucket(tri)] += 0.5
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [round(v / norm, 6) for v in vec]
        return vec

    def _embed_text(self, text: str) -> List[float]:
        """Generate embedding using OpenVINO pipeline when available."""
        if self.embedding_pipeline is not None:
            try:
                result = self.embedding_pipeline.embed(text)
                if hasattr(result, "tolist"):
                    vec = result.tolist()
                else:
                    vec = list(result)
                # Flatten common nested outputs
                if vec and isinstance(vec[0], list):
                    vec = vec[0]
                vec = [float(v) for v in vec]
                norm = math.sqrt(sum(v * v for v in vec))
                if norm > 0:
                    return [round(v / norm, 6) for v in vec]
            except Exception:
                pass
        return self._hash_embedding(text)

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Cosine similarity for normalized vectors."""
        if not a or not b:
            return 0.0
        n = min(len(a), len(b))
        if n == 0:
            return 0.0
        return float(sum(a[i] * b[i] for i in range(n)))

    def _build_semantic_text(self, path: Path, project_name: str, project_root: Path) -> str:
        """Build text payload used for file embedding."""
        rel = str(path.relative_to(project_root)).replace("\\", "/")
        chunks = [path.name, rel, project_name]
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2000)
            chunks.append(content)
        except Exception:
            pass
        return "\n".join(chunks)

    def _refresh_semantic_entries(self, projects: Dict) -> int:
        """Incrementally refresh semantic entries for changed/new files."""
        entries = self.semantic_index_data.setdefault("entries", {})
        changed = 0
        seen_paths = set()

        for project_name, project_data in projects.items():
            project_root = Path(project_data.get("path", ""))
            for fpath in list(project_data.get("root_files", {}).values()):
                p = Path(fpath)
                seen_paths.add(str(p))
                changed += self._upsert_semantic_entry(entries, p, project_name, project_root)
            for files in project_data.get("folders", {}).values():
                for fpath in files.values():
                    p = Path(fpath)
                    seen_paths.add(str(p))
                    changed += self._upsert_semantic_entry(entries, p, project_name, project_root)

        # Drop deleted files from semantic index.
        stale = [p for p in entries.keys() if p not in seen_paths]
        for p in stale:
            entries.pop(p, None)
            changed += 1

        self.semantic_index_data["created"] = datetime.now().isoformat()
        self.semantic_index_data["backend"] = self.embedding_backend
        self.semantic_index_data["device"] = self.embedding_device
        self._save_semantic_index()
        return changed

    def build_npu_semantic_index(self, projects: Dict) -> int:
        """Public semantic indexing entrypoint; uses OpenVINO/NPU when available."""
        return self._refresh_semantic_entries(projects)

    def _upsert_semantic_entry(self, entries: Dict, path: Path, project_name: str, project_root: Path) -> int:
        """Create/update single semantic entry if file changed."""
        try:
            st = path.stat()
        except Exception:
            return 0
        key = str(path)
        mtime = float(st.st_mtime)
        size = int(st.st_size)
        current = entries.get(key, {})
        if current.get("mtime") == mtime and current.get("size") == size:
            return 0
        try:
            rel = str(path.relative_to(project_root)).replace("\\", "/")
        except Exception:
            rel = path.name
        text = self._build_semantic_text(path, project_name, project_root)
        emb = self._embed_text(text)
        entries[key] = {
            "path": key,
            "name": path.name,
            "project": project_name,
            "relative": rel,
            "mtime": mtime,
            "size": size,
            "embedding": emb
        }
        return 1

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search indexed files by cosine similarity against semantic embeddings."""
        q = (query or "").strip()
        if not q:
            return []
        entries = self.semantic_index_data.get("entries", {})
        if not entries:
            return []
        q_emb = self._embed_text(q)
        q_tokens = [t for t in re.findall(r"[a-z0-9_./-]+", q.lower()) if len(t) > 1]
        scored = []
        for entry in entries.values():
            emb = entry.get("embedding") or []
            score = self._cosine_similarity(q_emb, emb)
            # Lexical boost: favors direct filename/path intent like "baseline architecture".
            name_l = (entry.get("name") or "").lower()
            path_l = (entry.get("path") or "").lower()
            token_hits = 0
            for token in q_tokens:
                if token in name_l:
                    score += 0.30
                    token_hits += 1
                elif token in path_l:
                    score += 0.10
                    token_hits += 1
            # Bonus for strong token overlap to prioritize likely direct user intent.
            if q_tokens:
                overlap = token_hits / len(q_tokens)
                score += overlap * 0.25
            if score <= 0:
                continue
            scored.append({
                "path": entry.get("path", ""),
                "name": entry.get("name", ""),
                "project": entry.get("project", ""),
                "score": round(score, 4)
            })
        scored.sort(key=lambda item: (-item["score"], item["name"]))
        return scored[:limit]

    def fuzzy_file_match(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """Find close filename matches and prioritize newest modified files."""
        q = (query or "").strip().lower()
        if not q or not self.index_data:
            return []

        candidates = []
        for project_name, project_data in self.index_data.get('projects', {}).items():
            for fname, fpath in project_data.get('root_files', {}).items():
                candidates.append((fname, fpath, project_name))
            for files in project_data.get('folders', {}).values():
                for fname, fpath in files.items():
                    candidates.append((fname, fpath, project_name))

        if not candidates:
            return []

        name_to_records = {}
        all_names = []
        for fname, fpath, project_name in candidates:
            key = fname.lower()
            all_names.append(key)
            name_to_records.setdefault(key, []).append((fname, fpath, project_name))

        close = difflib.get_close_matches(q, all_names, n=max(10, limit * 3), cutoff=0.45)
        if not close:
            return []

        hits = []
        for key in close:
            for fname, fpath, project_name in name_to_records.get(key, []):
                mtime = 0.0
                try:
                    mtime = float(Path(fpath).stat().st_mtime)
                except Exception:
                    pass
                ratio = difflib.SequenceMatcher(None, q, key).ratio()
                hits.append({
                    "path": fpath,
                    "name": fname,
                    "project": project_name,
                    "score": round(ratio, 4),
                    "modified": mtime
                })

        # Priority rule: most recent file first when fuzzy candidates compete.
        hits.sort(key=lambda h: (-h.get("modified", 0), -h.get("score", 0), h.get("name", "")))
        return hits[:limit]

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
        semantic_updated = self.build_npu_semantic_index(projects)
        return {
            'total_files': new_total,
            'new_files': max(0, new_total - old_total),
            'semantic_updated': semantic_updated
        }

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
        # Update semantic index with quick-scan hits so freshly-created files become searchable.
        if hits:
            entries = self.semantic_index_data.setdefault("entries", {})
            changed = 0
            for h in hits:
                p = Path(h["path"])
                project_root = p.parent
                # Try derive project root from known vault root.
                try:
                    root_str = self.index_data.get('vault_root') if self.index_data else None
                    if root_str:
                        root = Path(root_str)
                        if root in p.parents:
                            # project folder is first element under vault root
                            rel_parts = p.relative_to(root).parts
                            if rel_parts:
                                project_root = root / rel_parts[0]
                except Exception:
                    pass
                changed += self._upsert_semantic_entry(entries, p, h.get("project", ""), project_root)
            if changed:
                self.semantic_index_data["created"] = datetime.now().isoformat()
                self.semantic_index_data["backend"] = self.embedding_backend
                self.semantic_index_data["device"] = self.embedding_device
                self._save_semantic_index()
        return hits[:limit]


def demo_vault_reference():
    """Demonstrate how Jarvis would use the VaultReference class."""
    print("\n" + "="*70)
    print("ðŸ¤– DEMO: Jarvis using VaultReference Helper")
    print("="*70 + "\n")
    
    vault = VaultReference()
    
    if not vault.is_loaded:
        print("Index not loaded! Please run: python create_vault_index.py\n")
        return
    
    print("ðŸ“Š Vault Summary:")
    summary = vault.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print("\nðŸ” Example Queries:\n")
    
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
                print(f"  Query: 'main file' â†’ {filename}")
                print(f"    Full path: {result}\n")
        else:
            results = vault.get_files(query)
            if results:
                print(f"  Query: 'test files' â†’ Found {len(results)} file(s)")
                for r in results[:3]:  # Show first 3
                    print(f"    â€¢ {Path(r).name}")
                if len(results) > 3:
                    print(f"    ... and {len(results) - 3} more")
                print()
    
    print("ðŸ”Ž File Search Example:")
    searched_file = vault.search_file('jarvisgt2.py')
    if searched_file:
        print(f"  Finding 'jarvisgt2.py' â†’ {searched_file}\n")
    
    print("="*70 + "\n")


if __name__ == '__main__':
    demo_vault_reference()

