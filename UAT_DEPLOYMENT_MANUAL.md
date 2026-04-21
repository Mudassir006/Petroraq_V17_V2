# 🚀 UAT Deployment - Manual Steps

## 📋 UAT Deployment Checklist

### ✅ Current Status:
- **GitHub Repository**: ✅ Updated with latest changes (commit `2d99e26`)
- **Local Repository**: ✅ Has all the fixes
- **UAT Server**: ❌ Needs to be updated

## 🔧 Manual UAT Deployment Steps

### Step 1: Access Your UAT Server
```bash
# Connect to your UAT server
ssh your-uat-server
# OR
# Access via remote desktop to your UAT server
```

### Step 2: Navigate to Odoo Modules Directory
```bash
# Navigate to your Odoo modules directory
cd /path/to/your/odoo/modules
# OR
cd /opt/odoo/addons
# OR
cd /var/lib/odoo/addons
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
ls -la pr_account/views/menu_items.xml
```

### Step 5: Restart UAT Odoo Server
```bash
# Option 1: Systemctl (if using systemd)
sudo systemctl restart odoo

# Option 2: Service (if using init.d)
sudo service odoo restart

# Option 3: Manual restart (if running as process)
# Find the process and kill it, then restart
ps aux | grep odoo
kill -9 <process_id>
# Then restart Odoo
```

### Step 6: Update Module in UAT Odoo
1. **Access UAT Odoo** via web browser
2. **Login** as administrator
3. **Go to Apps** → **Update Apps List**
4. **Search for** `accounting_pdf_reports`
5. **Click Update** on the accounting_pdf_reports module
6. **Wait for update** to complete

### Step 7: Test the Fixes

#### Test Menu Consolidation:
- [ ] **Navigate to**: Main menu
- [ ] **Check**: "Petroraq Accounting" appears (not "Financial Accounting")
- [ ] **Check**: No duplicate accounting menus
- [ ] **Check**: HR workspace shows "Accounting Approvals"

#### Test Duplicate Entries Fix:
- [ ] **Navigate to**: Accounting → Petroraq Accounting → Reports → Ledgers → General Ledger
- [ ] **Check**: Entries are grouped by journal entry
- [ ] **Check**: No duplicate entries appear
- [ ] **Check**: Groups can be expanded

## 🔄 UAT Rollback (if needed)

### If Issues Occur:
```bash
# Rollback to previous commit
git checkout HEAD~1

# Restart Odoo server
sudo systemctl restart odoo

# Update module in Odoo to revert changes
```

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

## 🆘 Troubleshooting

### Common Issues:

**Issue**: Git pull fails
**Solution**: Check internet connection and GitHub access

**Issue**: Odoo server won't restart
**Solution**: Check logs and file permissions

**Issue**: Module update fails
**Solution**: Check file permissions and restart Odoo

**Issue**: Still seeing duplicates
**Solution**: Verify module was updated and clear browser cache

## 📞 UAT Support

**UAT Server**: _______________
**UAT URL**: _______________
**Deployment Date**: _______________
**Deployed By**: _______________

---

**Ready for UAT Deployment!** 🚀
