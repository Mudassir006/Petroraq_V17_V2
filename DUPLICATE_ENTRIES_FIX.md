# Duplicate Ledger Entries Fix

## Problem Identified
The ledger view was showing duplicate entries because it was displaying **move lines** instead of **journal entries**. Each payment voucher creates multiple move lines (which is correct accounting), but the view was showing each move line as a separate entry, causing the appearance of duplicates.

## Root Cause
- **General Ledger** was using `account.view_move_line_tree_grouped_general` view
- This view displays individual **move lines** instead of grouping them by **journal entry**
- Each payment voucher (CPV, BPV) creates multiple move lines for different expense types
- The view showed each move line as a separate row, creating "duplicate" appearance

## Solution Implemented

### 1. Created Custom Views
**File**: `accounting_pdf_reports/views/ledger_fix.xml`

- **`view_move_line_tree_grouped_by_journal`**: Groups move lines by journal entry
- **`view_move_line_tree_grouped_by_journal_partner`**: Groups partner ledger by journal entry
- **Key Change**: `default_group_by="move_id"` groups by journal entry instead of showing individual lines

### 2. Created Fixed Actions
- **`action_account_moves_ledger_general_fixed`**: Uses custom view with journal entry grouping
- **`action_account_moves_ledger_partner_fixed`**: Uses custom view with journal entry grouping
- **Key Change**: `search_default_group_by_move_id: 1` ensures grouping by journal entry

### 3. Updated Menu References
**File**: `accounting_pdf_reports/views/ledger_menu.xml`
- Updated menu items to use the fixed actions instead of original ones

### 4. Updated Manifest
**File**: `accounting_pdf_reports/__manifest__.py`
- Added `views/ledger_fix.xml` to the data files list

## Technical Details

### Before Fix:
```
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00  ← Duplicate
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00  ← Duplicate
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00  ← Duplicate
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00  ← Duplicate
```

### After Fix:
```
📁 CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical...
   ├── Account A | 50.00
   ├── Account B | 30.00
   ├── Account C | 20.00
   └── Total: 100.00
```

## Files Modified

1. **`accounting_pdf_reports/views/ledger_fix.xml`** (NEW)
   - Custom views that group by journal entry
   - Fixed actions that use the custom views

2. **`accounting_pdf_reports/views/ledger_menu.xml`** (MODIFIED)
   - Updated menu items to use fixed actions

3. **`accounting_pdf_reports/__manifest__.py`** (MODIFIED)
   - Added new ledger fix file to data list

## Deployment Instructions

### For Production:
1. **Deploy the modified files** to production server
2. **Update the module** in Odoo (Apps → Update Apps → accounting_pdf_reports)
3. **No data migration required** - this is a view-only change
4. **No configuration changes needed**

### For UAT:
1. **Deploy the modified files** to UAT server
2. **Update the module** in Odoo
3. **Test the General Ledger and Partner Ledger** views
4. **Verify that entries are now grouped by journal entry**

## Benefits

✅ **Eliminates duplicate entries display**
✅ **Maintains data integrity** - no data changes
✅ **Improves user experience** - cleaner ledger view
✅ **Preserves accounting accuracy** - all move lines still visible when expanded
✅ **No business disruption** - can be deployed during normal hours

## Testing

After deployment, verify:
1. **General Ledger** shows journal entries grouped properly
2. **Partner Ledger** shows journal entries grouped properly
3. **Expandable groups** show individual move lines when needed
4. **Totals are correct** for each journal entry
5. **No duplicate entries** appear in the list

## Rollback Plan

If issues occur:
1. **Revert the modified files** to original versions
2. **Update the module** to restore original views
3. **No data loss** - this change only affects display

## Impact Assessment

- **Data Impact**: NONE - View-only change
- **Configuration Impact**: NONE - No settings changed
- **User Impact**: POSITIVE - Cleaner, more organized ledger view
- **Business Impact**: NONE - All functionality preserved
