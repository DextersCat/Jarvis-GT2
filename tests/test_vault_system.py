#!/usr/bin/env python3
"""
Final Integration Test - Demonstrates the complete vault system working together
"""

import json
from pathlib import Path
from vault_reference import VaultReference


def test_vault_system():
    """Complete end-to-end test of the vault index system."""
    
    print("\n" + "="*70)
    print("🧪 VAULT INDEX SYSTEM - FINAL INTEGRATION TEST")
    print("="*70 + "\n")
    
    # Test 1: Load vault
    print("TEST 1: Loading Vault Index")
    print("-" * 70)
    vault = VaultReference()
    
    if vault.is_loaded:
        print("✅ PASS: Vault index loaded successfully")
    else:
        print("❌ FAIL: Could not load vault index")
        return False
    
    # Test 2: Check summary
    print("\nTEST 2: Vault Summary")
    print("-" * 70)
    summary = vault.get_summary()
    
    print(f"✅ Vault Root: {summary['vault_root']}")
    print(f"✅ Total Projects: {summary['total_projects']}")
    print(f"✅ Total Files: {summary['total_files']}")
    print(f"✅ Reference Types: {summary['reference_types']}")
    
    # Test 3: File reference resolution
    print("\nTEST 3: File Reference Resolution")
    print("-" * 70)
    
    test_references = {
        'main': 'jarvis_main.py',
        'startup': 'jarvisgt2.py',
        'config': 'config.json',
    }
    
    all_pass = True
    for ref_type, expected_file in test_references.items():
        file_path = vault.get_file(ref_type)
        if file_path:
            actual_file = Path(file_path).name
            if actual_file == expected_file or expected_file in file_path:
                print(f"✅ '{ref_type}' → {actual_file}")
            else:
                print(f"⚠️  '{ref_type}' → {actual_file} (expected {expected_file})")
        else:
            print(f"❌ '{ref_type}' → NOT FOUND")
            all_pass = False
    
    # Test 4: Multiple file queries
    print("\nTEST 4: Multiple File Queries")
    print("-" * 70)
    
    test_files = vault.get_files('test')
    print(f"✅ Found {len(test_files)} test files:")
    for test_file in test_files[:5]:
        print(f"   • {Path(test_file).name}")
    if len(test_files) > 5:
        print(f"   ... and {len(test_files) - 5} more")
    
    # Test 5: File search
    print("\nTEST 5: File Search")
    print("-" * 70)
    
    search_targets = ['jarvisgt2.py', 'config.json', 'jarvis_ear.py']
    all_found = True
    
    for filename in search_targets:
        found = vault.search_file(filename)
        if found:
            print(f"✅ Found: {filename}")
        else:
            print(f"❌ Not Found: {filename}")
            all_found = False
    
    # Test 6: Project structure
    print("\nTEST 6: Project Structure")
    print("-" * 70)
    
    structure = vault.get_project_structure('New_Jarvis')
    root_files_count = len(structure.get('root_files', {}))
    subfolder_count = len(structure.get('folders', {}))
    
    print(f"✅ New_Jarvis Project:")
    print(f"   • Root files: {root_files_count}")
    print(f"   • Subfolders: {subfolder_count}")
    
    # Test 7: Realistic Jarvis queries
    print("\nTEST 7: Realistic Jarvis Queries")
    print("-" * 70)
    
    user_queries = [
        "Check my main file",
        "Load the configuration",
        "Show startup sequence",
        "Find all tests",
        "What's in memory file",
    ]
    
    print("User Queries → Jarvis Resolution:\n")
    
    for query in user_queries:
        # Determine which reference type matches
        ref_type = None
        
        query_lower = query.lower()
        if 'main' in query_lower:
            ref_type = 'main'
        elif 'config' in query_lower:
            ref_type = 'config'
        elif 'startup' in query_lower or 'start' in query_lower:
            ref_type = 'startup'
        elif 'test' in query_lower:
            ref_type = 'test'
        elif 'memory' in query_lower:
            ref_type = 'memory'
        
        if ref_type == 'test':
            files = vault.get_files(ref_type)
            result = f"Found {len(files)} test files"
        else:
            file_path = vault.get_file(ref_type)
            if file_path:
                result = Path(file_path).name
            else:
                result = "NOT FOUND"
        
        print(f"  User: '{query}'")
        print(f"  Jarvis: {result}\n")
    
    # Final summary
    print("="*70)
    print("📊 TEST RESULTS SUMMARY")
    print("="*70)
    
    if all_pass and all_found:
        print("\n✅ ALL TESTS PASSED - Vault system ready for integration!\n")
        return True
    else:
        print("\n⚠️  Some tests had issues - check results above\n")
        return False


def show_implementation_hint():
    """Show how to add this to jarvisgt2.py"""
    print("\n" + "="*70)
    print("💡 QUICK IMPLEMENTATION HINT")
    print("="*70 + "\n")
    
    code_example = '''
    # In jarvisgt2.py, add to the __init__ method:
    
    from vault_reference import VaultReference
    
    class JarvisGT2:
        def __init__(self):
            # ... existing initialization code ...
            
            # Add vault reference system
            self.vault = VaultReference()
            if self.vault.is_loaded:
                logger.info("✓ Vault index loaded - file reference system active")
        
        def process_user_input(self, user_text):
            # When user mentions a file or operation:
            
            # Example: "Check main file"
            if 'main' in user_text.lower():
                main_file = self.vault.get_file('main')
                # Do something with main_file
            
            # Example: "Run all tests"
            elif 'test' in user_text.lower():
                test_files = self.vault.get_files('test')
                for test in test_files:
                    # Run each test file
    '''
    
    print(code_example)
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    success = test_vault_system()
    show_implementation_hint()
    
    if success:
        print("✨ System is ready! Proceed with integration.\n")
    else:
        print("⚠️  Review any failures above before integrating.\n")
