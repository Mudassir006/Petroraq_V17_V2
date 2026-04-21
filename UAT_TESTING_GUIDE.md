# 🧪 UAT Testing Guide - Duplicate Ledger Entries Fix

## 📋 UAT Testing Checklist

### ✅ Pre-Testing Setup
- [ ] **UAT deployment completed** successfully
- [ ] **UAT Odoo server restarted**
- [ ] **Module updated** in UAT Odoo
- [ ] **UAT accessible** via web interface
- [ ] **Test user accounts** available

## 🎯 Test 1: Menu Consolidation

### Objective:
Verify that duplicate "Financial Accounting" menus are consolidated.

### Steps:
1. **Login to UAT** with administrator account
2. **Navigate to main menu**
3. **Check Accounting section**

### Expected Results:
- [ ] **"Petroraq Accounting"** appears (not "Financial Accounting")
- [ ] **No duplicate accounting menus**
- [ ] **HR workspace shows "Accounting Approvals"** (not "Financial Accounting")

### Test Screenshots:
Take screenshots of:
- Main menu showing "Petroraq Accounting"
- HR workspace showing "Accounting Approvals"
- No duplicate menus visible

## 🎯 Test 2: Duplicate Ledger Entries Fix

### Objective:
Verify that duplicate ledger entries are now grouped by journal entry.

### Steps:
1. **Navigate to**: Accounting → Petroraq Accounting → Reports → Ledgers → General Ledger
2. **Look for existing entries** (CPV-2025-00002, CPV-2025-00004, CPV-2025-00015)
3. **Check if entries are grouped** by journal entry
4. **Expand groups** to see individual move lines

### Expected Results:
- [ ] **Entries are grouped** by journal entry (CPV, BPV, etc.)
- [ ] **No duplicate entries** appear in the list
- [ ] **Groups are expandable** to show individual move lines
- [ ] **Totals are correct** for each journal entry

### Before Fix (What you should NOT see):
```
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00  ← Duplicate
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00  ← Duplicate
```

### After Fix (What you SHOULD see):
```
📁 CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical...
   ├── Account A | 50.00
   ├── Account B | 30.00
   ├── Account C | 20.00
   └── Total: 100.00
```

## 🎯 Test 3: Partner Ledger

### Objective:
Verify that Partner Ledger also groups entries correctly.

### Steps:
1. **Navigate to**: Accounting → Petroraq Accounting → Reports → Ledgers → Partner Ledger
2. **Check if entries are grouped** by journal entry
3. **Verify partner information** is correct
4. **Check totals** are accurate

### Expected Results:
- [ ] **Entries are grouped** by journal entry
- [ ] **No duplicate entries** appear
- [ ] **Partner information** is correct
- [ ] **Balances are accurate**

## 🎯 Test 4: Create New Entries

### Objective:
Verify that new entries are created and displayed correctly.

### Steps:
1. **Create a new Cash Payment Voucher (CPV)** with multiple expense lines
2. **Post the voucher**
3. **Check General Ledger** to see how it appears
4. **Verify grouping** is correct

### Expected Results:
- [ ] **New CPV appears** as one grouped entry
- [ ] **Individual move lines** are visible when expanded
- [ ] **Totals are correct**
- [ ] **No duplicates** appear

## 🎯 Test 5: Data Integrity

### Objective:
Verify that all existing data is intact and accurate.

### Steps:
1. **Check account balances** before and after deployment
2. **Verify journal entry totals** are correct
3. **Check partner balances** are accurate
4. **Verify date information** is correct

### Expected Results:
- [ ] **All account balances** are unchanged
- [ ] **Journal entry totals** are correct
- [ ] **Partner balances** are accurate
- [ ] **Date information** is correct
- [ ] **No data loss** occurred

## 🎯 Test 6: Performance

### Objective:
Verify that the fix doesn't impact system performance.

### Steps:
1. **Load General Ledger** and measure load time
2. **Load Partner Ledger** and measure load time
3. **Expand/collapse groups** and check responsiveness
4. **Navigate between views** and check speed

### Expected Results:
- [ ] **Load times** are acceptable (< 5 seconds)
- [ ] **Group expansion** is responsive
- [ ] **Navigation** is smooth
- [ ] **No performance degradation**

## 📊 UAT Test Results

### Test Results Summary:
- [ ] **Test 1: Menu Consolidation** - ✅ PASS / ❌ FAIL
- [ ] **Test 2: Duplicate Ledger Entries Fix** - ✅ PASS / ❌ FAIL
- [ ] **Test 3: Partner Ledger** - ✅ PASS / ❌ FAIL
- [ ] **Test 4: Create New Entries** - ✅ PASS / ❌ FAIL
- [ ] **Test 5: Data Integrity** - ✅ PASS / ❌ FAIL
- [ ] **Test 6: Performance** - ✅ PASS / ❌ FAIL

### Overall UAT Result:
- [ ] **✅ UAT PASSED** - Ready for production deployment
- [ ] **❌ UAT FAILED** - Issues found, rollback required

## 🐛 Issue Reporting

### If Issues Found:
1. **Document the issue** with screenshots
2. **Note the steps** that led to the issue
3. **Check Odoo logs** for error messages
4. **Report to technical team**

### Common Issues:
- **Module update fails** - Check file permissions
- **Views not loading** - Clear browser cache
- **Still seeing duplicates** - Verify module was updated
- **Performance issues** - Check server resources

## 🔄 UAT Rollback

### If UAT Testing Fails:
1. **Run rollback script**: `UAT_ROLLBACK_SCRIPT.bat`
2. **Restart UAT Odoo server**
3. **Update module** to revert changes
4. **Verify system** returns to original state

## 📋 UAT Sign-off

### Technical Sign-off:
- [ ] **System Administrator** approval
- [ ] **Technical Lead** approval
- [ ] **No errors** in system logs

### Business Sign-off:
- [ ] **Accounting Manager** approval
- [ ] **End User** approval
- [ ] **Business requirements** met

### Documentation:
- [ ] **Test results** documented
- [ ] **Issues log** completed
- [ ] **UAT report** generated

---

**UAT Testing Date**: _______________
**UAT Tester**: _______________
**UAT Manager**: _______________
**Overall Result**: ✅ PASS / ❌ FAIL
**Comments**: _______________
