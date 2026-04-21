# 🚀 UAT DEPLOYMENT - Step by Step Guide

## 📋 IMMEDIATE DEPLOYMENT STEPS

### Step 1: Access Your UAT Server
```bash
# Connect to your UAT server
ssh your-uat-server-ip
# OR
# Use remote desktop to connect to UAT server
```

### Step 2: Navigate to Odoo Modules Directory
```bash
# Find your Odoo modules directory (common locations):
cd /opt/odoo/addons
# OR
cd /var/lib/odoo/addons
# OR
cd /home/odoo/addons
# OR
cd /path/to/your/odoo/modules
```

### Step 3: Pull Latest Changes from GitHub
```bash
# Pull the latest changes from GitHub test branch
git pull origin test

# Verify the latest commit
git log --oneline -1
# Should show: 2d99e26 Fix duplicate ledger entries and consolidate accounting menus
```

### Step 4: Verify Files Are Updated
```bash
# Check if new files exist
ls -la accounting_pdf_reports/views/ledger_fix.xml
ls -la deployment_package/

# Check modified files
ls -la accounting_pdf_reports/views/ledger_menu.xml
ls -la accounting_pdf_reports/__manifest__.py
```

### Step 5: Restart UAT Odoo Server
```bash
# Restart Odoo service
sudo systemctl restart odoo
# OR
sudo service odoo restart
```

### Step 6: Update Module in UAT Odoo
1. **Open web browser** and go to your UAT Odoo URL
2. **Login** as administrator
3. **Go to Apps** → **Update Apps List**
4. **Search for** `accounting_pdf_reports`
5. **Click Update** on the accounting_pdf_reports module
6. **Wait for update** to complete

### Step 7: Test the Fixes

#### Test 1: Menu Consolidation
- [ ] **Navigate to**: Main menu
- [ ] **Check**: "Petroraq Accounting" appears (not "Financial Accounting")
- [ ] **Check**: No duplicate accounting menus

#### Test 2: Duplicate Entries Fix
- [ ] **Navigate to**: Accounting → Petroraq Accounting → Reports → Ledgers → General Ledger
- [ ] **Check**: Entries are grouped by journal entry
- [ ] **Check**: No duplicate entries appear

## 🎯 Expected Results

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

## 🔄 Rollback (if needed)

### If Issues Occur:
```bash
# Rollback to previous commit
git checkout HEAD~1

# Restart Odoo server
sudo systemctl restart odoo

# Update module in Odoo to revert changes
```

## 📞 Support

**UAT Server**: _______________
**UAT URL**: _______________
**Deployment Date**: _______________

---

**Ready for UAT Deployment!** 🚀
