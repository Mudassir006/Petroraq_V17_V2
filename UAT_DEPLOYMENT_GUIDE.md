# 🧪 UAT Deployment Guide - Duplicate Ledger Entries Fix

## 📋 UAT Deployment Checklist

### ✅ Pre-Deployment (UAT)
- [ ] **UAT server access** confirmed
- [ ] **UAT database backup** completed
- [ ] **UAT maintenance window** scheduled
- [ ] **UAT users notified** of testing
- [ ] **GitHub repository** updated with latest changes

### ✅ Changes Pushed to GitHub
**Commit**: `2d99e26` - "Fix duplicate ledger entries and consolidate accounting menus"
**Branch**: `test`
**Status**: ✅ Successfully pushed to GitHub

## 🚀 UAT Deployment Steps

### Step 1: Pull Latest Changes to UAT Server
```bash
# On UAT server, navigate to your Odoo modules directory
cd /path/to/your/odoo/modules

# Pull latest changes from GitHub
git pull origin test
```

### Step 2: Verify Files Are Updated
Check that these files exist and are updated:
- `accounting_pdf_reports/views/ledger_fix.xml` (NEW)
- `accounting_pdf_reports/views/ledger_menu.xml` (MODIFIED)
- `accounting_pdf_reports/__manifest__.py` (MODIFIED)
- `pr_account/views/menu_items.xml` (MODIFIED)
- `de_hr_workspace_account/views/menu.xml` (MODIFIED)

### Step 3: Restart UAT Odoo Server
```bash
# Restart Odoo service
sudo systemctl restart odoo
# OR
sudo service odoo restart
```

### Step 4: Update Module in UAT
1. **Access UAT Odoo** (your UAT URL)
2. **Login** as administrator
3. **Go to Apps** → **Update Apps List**
4. **Search for** `accounting_pdf_reports`
5. **Click Update** on the accounting_pdf_reports module
6. **Wait for update** to complete

### Step 5: Test the Fixes

#### Test 1: Menu Consolidation
- [ ] **Navigate to**: Accounting menu
- [ ] **Verify**: "Petroraq Accounting" appears (not "Financial Accounting")
- [ ] **Verify**: No duplicate accounting menus
- [ ] **Verify**: HR workspace shows "Accounting Approvals" (not "Financial Accounting")

#### Test 2: Duplicate Ledger Entries Fix
- [ ] **Navigate to**: Accounting → Petroraq Accounting → Reports → Ledgers → General Ledger
- [ ] **Verify**: Entries are grouped by journal entry (CPV, BPV, etc.)
- [ ] **Verify**: No duplicate entries appear
- [ ] **Verify**: Groups can be expanded to show individual move lines
- [ ] **Verify**: Totals are correct for each journal entry

#### Test 3: Partner Ledger
- [ ] **Navigate to**: Accounting → Petroraq Accounting → Reports → Ledgers → Partner Ledger
- [ ] **Verify**: Entries are grouped by journal entry
- [ ] **Verify**: No duplicate entries appear
- [ ] **Verify**: Partner information is correct

## 🧪 UAT Testing Scenarios

### Scenario 1: Cash Payment Vouchers (CPV)
- [ ] **Create a new CPV** with multiple expense lines
- [ ] **Post the voucher**
- [ ] **Check General Ledger** - should show as one grouped entry
- [ ] **Expand the group** - should show individual move lines
- [ ] **Verify totals** are correct

### Scenario 2: Bank Payment Vouchers (BPV)
- [ ] **Create a new BPV** with multiple expense lines
- [ ] **Post the voucher**
- [ ] **Check General Ledger** - should show as one grouped entry
- [ ] **Expand the group** - should show individual move lines
- [ ] **Verify totals** are correct

### Scenario 3: Existing Data
- [ ] **Check existing CPV entries** (like CPV-2025-00002, CPV-2025-00004, CPV-2025-00015)
- [ ] **Verify they are grouped** properly
- [ ] **Verify no duplicates** appear
- [ ] **Verify all data** is intact

## 📊 Expected UAT Results

### Before Fix (Current UAT):
```
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00  ← Duplicate
CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical... | 100.00  ← Duplicate
```

### After Fix (Expected UAT):
```
📁 CPV-2025-00002 | 2025-01-29 | Fuel, Food, Medical...
   ├── Account A | 50.00
   ├── Account B | 30.00
   ├── Account C | 20.00
   └── Total: 100.00
```

## 🔄 UAT Rollback Plan

### If Issues Occur in UAT:
```bash
# On UAT server
git checkout HEAD~1  # Go back to previous commit
sudo systemctl restart odoo
# Update module in Odoo to revert changes
```

### Alternative Rollback:
Use the deployment package rollback script:
```bash
cd deployment_package
./ROLLBACK_LEDGER_FIX.bat
```

## 📋 UAT Sign-off Checklist

### Technical Validation:
- [ ] **All tests pass** successfully
- [ ] **No errors** in Odoo logs
- [ ] **Performance** is acceptable
- [ ] **Data integrity** maintained

### Business Validation:
- [ ] **Accounting team** approves the changes
- [ ] **Users can navigate** easily
- [ ] **Reports are accurate**
- [ ] **No business disruption**

### UAT Approval:
- [ ] **UAT Manager** approval
- [ ] **Business User** approval
- [ ] **Technical Lead** approval

## 🚀 Next Steps After UAT Success

### If UAT Testing Passes:
1. **Document UAT results**
2. **Schedule production deployment**
3. **Prepare production deployment package**
4. **Notify production users**

### If UAT Testing Fails:
1. **Document issues found**
2. **Implement fixes**
3. **Re-test in UAT**
4. **Repeat until successful**

## 📞 UAT Support

**UAT Deployment Date**: _______________
**UAT Manager**: _______________
**Technical Lead**: _______________
**Business User**: _______________

**UAT Results**: ✅ PASS / ❌ FAIL
**Comments**: _______________

---

**Ready for UAT Deployment!** 🚀
