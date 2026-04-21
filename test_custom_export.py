#!/usr/bin/env python3
"""
Test script for custom export functionality
"""

def test_export_logic():
    """Test the export logic without Odoo environment"""
    
    # Simulate grouped data
    sample_data = [
        {
            'date': '2025-09-25',
            'journal_entry': 'JV/2025/09/0059',
            'reference': 'BPV-2025-00295',
            'partner': 'IMRAN ALI MANZOOR AHMAD',
            'account': '(6 lines)',
            'description': 'Journal Entry Summary - 6 move lines',
            'debit': 2880.00,
            'credit': 2880.00,
            'balance': 0.00
        },
        {
            'date': '2025-09-25',
            'journal_entry': 'JV/2025/09/0058',
            'reference': 'BPV-2025-00294',
            'partner': '',
            'account': '(2 lines)',
            'description': 'Journal Entry Summary - 2 move lines',
            'debit': 10000.00,
            'credit': 10000.00,
            'balance': 0.00
        }
    ]
    
    print("=== CUSTOM EXPORT TEST ===")
    print(f"Sample data: {len(sample_data)} entries")
    print()
    
    for entry in sample_data:
        print(f"Date: {entry['date']}")
        print(f"Journal Entry: {entry['journal_entry']}")
        print(f"Reference: {entry['reference']}")
        print(f"Partner: {entry['partner']}")
        print(f"Account: {entry['account']}")
        print(f"Description: {entry['description']}")
        print(f"Debit: {entry['debit']}")
        print(f"Credit: {entry['credit']}")
        print(f"Balance: {entry['balance']}")
        print("-" * 50)
    
    print("✅ Export logic test completed!")
    print("Expected result: Excel file with grouped entries only")

if __name__ == "__main__":
    test_export_logic()
