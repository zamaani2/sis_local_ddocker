#!/usr/bin/env python
"""
Comprehensive validation script for Enhanced Score Entry setup
Run this to verify everything is configured correctly
"""

import os
import re

def check_file_exists(path, description):
    """Check if a file exists"""
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path} {'(exists)' if exists else '(MISSING)'}")
    return exists

def check_template_structure():
    """Check template file structure"""
    print("\n" + "="*60)
    print("TEMPLATE STRUCTURE CHECK")
    print("="*60)
    
    template_path = 'shs_system/templates/student/enhanced_enter_scores.html'
    if not os.path.exists(template_path):
        print(f"❌ Template file not found: {template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'Extends base.html': '{% extends \'base.html\' %}' in content,
        'Loads static': '{% load static %}' in content,
        'Has extra_js block': '{% block extra_js %}' in content,
        'Config object defined': 'window.enhancedScoresConfig' in content,
        'External JS referenced': 'enhanced_enter_scores.js' in content,
        'handleTeacherFilterChange defined': 'window.handleTeacherFilterChange' in content,
        'updateAssignmentSelection defined': 'window.updateAssignmentSelection' in content,
    }
    
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}")
    
    return all(checks.values())

def check_javascript_file():
    """Check JavaScript file structure"""
    print("\n" + "="*60)
    print("JAVASCRIPT FILE CHECK")
    print("="*60)
    
    js_path = 'static/js/enhanced_enter_scores.js'
    if not os.path.exists(js_path):
        print(f"❌ JavaScript file not found: {js_path}")
        return False
    
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Basic structure checks
    checks = {
        'Config object referenced': 'window.enhancedScoresConfig' in content,
        'Config safety check': 'typeof window.enhancedScoresConfig' in content,
        'scoringConfig defined': 'const scoringConfig =' in content,
        'jQuery ready handler': '$(document).ready' in content or '$(function' in content,
        'jQuery usage': '$(' in content or 'jQuery(' in content,
        'SweetAlert2 usage': 'Swal.' in content,
        'Bootstrap usage': 'bootstrap.' in content,
    }
    
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}")
    
    # Check for common functions
    print("\nFunction checks:")
    functions = [
        'calculateClassScore',
        'calculateTotalScore',
        'updateGradeAndRemarks',
        'calculatePositions',
        'handleSingleExport',
        'handleSingleImport',
        'showEnhancedBatchExportDialog',
        'showEnhancedBatchImportDialog',
    ]
    
    for func in functions:
        found = func in content or f'function {func}' in content
        status = "✅" if found else "❌"
        print(f"{status} {func}")
    
    # Check bracket balance
    open_braces = content.count('{')
    close_braces = content.count('}')
    open_parens = content.count('(')
    close_parens = content.count(')')
    
    print(f"\nSyntax balance:")
    print(f"{'✅' if open_braces == close_braces else '❌'} Braces: {open_braces} open, {close_braces} close")
    print(f"{'✅' if open_parens == close_parens else '❌'} Parentheses: {open_parens} open, {close_parens} close")
    
    return all(checks.values()) and open_braces == close_braces and open_parens == close_parens

def check_dependencies():
    """Check if dependencies are loaded in base template"""
    print("\n" + "="*60)
    print("DEPENDENCY CHECK")
    print("="*60)
    
    base_template = 'shs_system/templates/base.html'
    if not os.path.exists(base_template):
        print(f"❌ Base template not found: {base_template}")
        return False
    
    with open(base_template, 'r', encoding='utf-8') as f:
        content = f.read()
    
    dependencies = {
        'jQuery': 'jquery' in content.lower(),
        'Bootstrap': 'bootstrap' in content.lower(),
        'SweetAlert2': 'sweetalert' in content.lower(),
        'DataTables': 'datatables' in content.lower() or 'dataTables' in content,
    }
    
    for dep, found in dependencies.items():
        status = "✅" if found else "❌"
        print(f"{status} {dep} loaded in base template")
    
    return all(dependencies.values())

def check_url_references():
    """Check that URL references are properly configured"""
    print("\n" + "="*60)
    print("URL REFERENCES CHECK")
    print("="*60)
    
    template_path = 'shs_system/templates/student/enhanced_enter_scores.html'
    if not os.path.exists(template_path):
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    url_names = [
        'export_enhanced_scores',
        'export_enhanced_scores_batch',
        'import_enhanced_scores',
        'import_enhanced_scores_batch',
    ]
    
    for url_name in url_names:
        found = f"'{url_name}'" in content or f'"{url_name}"' in content
        status = "✅" if found else "❌"
        print(f"{status} URL reference: {url_name}")
    
    return all(f"'{name}'" in content or f'"{name}"' in content for name in url_names)

def main():
    """Run all validation checks"""
    print("="*60)
    print("ENHANCED SCORE ENTRY - COMPREHENSIVE VALIDATION")
    print("="*60)
    
    # Check file existence
    print("\n" + "="*60)
    print("FILE EXISTENCE CHECK")
    print("="*60)
    files = [
        ('static/js/enhanced_enter_scores.js', 'External JavaScript file'),
        ('shs_system/templates/student/enhanced_enter_scores.html', 'Template file'),
        ('shs_system/templates/base.html', 'Base template'),
    ]
    
    all_files_exist = all(check_file_exists(path, desc) for path, desc in files)
    
    # Run checks
    template_ok = check_template_structure()
    js_ok = check_javascript_file()
    deps_ok = check_dependencies()
    urls_ok = check_url_references()
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    results = {
        'Files exist': all_files_exist,
        'Template structure': template_ok,
        'JavaScript structure': js_ok,
        'Dependencies loaded': deps_ok,
        'URL references': urls_ok,
    }
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - System is ready for testing!")
    else:
        print("⚠️  SOME CHECKS FAILED - Please review the issues above")
    print("="*60)
    
    return all_passed

if __name__ == '__main__':
    main()


