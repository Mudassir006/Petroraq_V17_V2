# 🚀 UAT Deployment Commands

## Quick UAT Deployment Commands

### 1. Pull Latest Changes to UAT Server
```bash
# Navigate to your Odoo modules directory on UAT server
cd /path/to/your/odoo/modules

# Pull latest changes from GitHub test branch
git pull origin test

# Verify the latest commit
git log --oneline -1
# Should show: 2d99e26 Fix duplicate ledger entries and consolidate accounting menus
```

### 2. Restart UAT Odoo Server
```bash
# Option 1: Systemctl (if using systemd)
sudo systemctl restart odoo

# Option 2: Service (if using init.d)
sudo service odoo restart

# Option 3: Manual restart (if running as process)
# Kill the process and restart
```

### 3. Verify UAT Deployment
```bash
# Check if new files exist
ls -la accounting_pdf_reports/views/ledger_fix.xml
ls -la deployment_package/

# Check file permissions
ls -la accounting_pdf_reports/views/ledger_menu.xml
ls -la accounting_pdf_reports/__manifest__.py
```

### 4. UAT Testing URLs
```
# UAT General Ledger
https://your-uat-server/accounting_pdf_reports/action_account_moves_ledger_general_fixed

# UAT Partner Ledger  
https://your-uat-server/accounting_pdf_reports/action_account_moves_ledger_partner_fixed

# UAT Menu Structure
https://your-uat-server/web#action=menu&cids=2
```

### 5. UAT Rollback Commands (if needed)
```bash
# Option 1: Git rollback
git checkout HEAD~1
sudo systemctl restart odoo

# Option 2: Use deployment package rollback
cd deployment_package
chmod +x ROLLBACK_LEDGER_FIX.bat
./ROLLBACK_LEDGER_FIX.bat
```

## UAT Verification Commands

### Check Git Status
```bash
git status
git log --oneline -5
```

### Check Odoo Logs
```bash
# Check for errors
tail -f /var/log/odoo/odoo.log

# Or check your Odoo log file
tail -f /path/to/your/odoo.log
```

### Check Module Status
```bash
# In Odoo shell or via web interface
# Apps → Update Apps List → Search "accounting_pdf_reports"
```

## UAT Testing Checklist Commands

### Test Menu Consolidation
```bash
# Navigate to UAT and check:
# 1. Accounting menu should show "Petroraq Accounting" (not "Financial Accounting")
# 2. HR workspace should show "Accounting Approvals" (not "Financial Accounting")
```

### Test Duplicate Entries Fix
```bash
# Navigate to UAT and check:
# 1. General Ledger should group entries by journal entry
# 2. No duplicate entries should appear
# 3. Groups should be expandable
```

## UAT Success Criteria

### ✅ UAT Deployment Successful If:
- [ ] Git pull completed without errors
- [ ] Odoo server restarted successfully
- [ ] Module updated without errors
- [ ] No errors in Odoo logs
- [ ] UAT accessible via web interface

### ✅ UAT Testing Successful If:
- [ ] Menu consolidation works (no duplicate "Financial Accounting" menus)
- [ ] Ledger entries are grouped by journal entry
- [ ] No duplicate entries appear
- [ ] All existing data is intact
- [ ] Performance is acceptable

## UAT Deployment Timeline

```
T+0:  Start UAT deployment
T+5:  Git pull completed
T+10: Odoo server restarted
T+15: Module updated
T+20: UAT testing begins
T+30: UAT testing completed
T+35: UAT sign-off
```

## UAT Contact Information

**UAT Server**: _______________
**UAT URL**: _______________
**UAT Manager**: _______________
**Deployment Date**: _______________

---

**Ready for UAT Deployment!** 🚀
