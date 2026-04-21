# Custom User Portal - Purchase Requisition Access Control

## Overview
This module implements access control for Purchase Requisitions (PRs) based on user roles and assignments.

## Access Control Rules

### 1. Supervisor Access
- **Who**: Users assigned as supervisors to specific PRs
- **What they can see**: Only PRs where `supervisor_user_id` matches their user ID
- **Permissions**: Read, Write, Create (no delete)

### 2. Creator Access
- **Who**: Users who created the PR
- **What they can see**: PRs they created (tracked by `create_uid`)
- **Permissions**: Read, Write, Create (no delete)

### 3. Manager Access
- **Who**: Users with Purchase Manager group (`purchase.group_purchase_manager`)
- **What they can see**: All PRs in the system
- **Permissions**: Read, Write, Create, Delete

## How It Works

### Supervisor Assignment
1. When a PR is created, the `supervisor` field can be filled with a name
2. The system automatically tries to find the corresponding user:
   - First searches for an employee with that name
   - If found, uses the employee's associated user
   - If not found, searches for a user with that name directly
3. The found user is stored in `supervisor_user_id` field

### Security Rules
The module implements multiple record rules that work together:
- `purchase_requisition_supervisor_rule`: Allows supervisors to see assigned PRs
- `purchase_requisition_creator_rule`: Allows creators to see their own PRs
- `purchase_requisition_manager_rule`: Allows managers to see all PRs
- Similar rules exist for PR line items

### User Interface
- List view shows supervisor and supervisor user fields
- Form view displays who created the PR and who is assigned as supervisor
- Users can only see PRs they have access to based on the security rules

## Technical Details

### Model Fields
- `supervisor_user_id`: Many2one field linking to res.users
- `create_uid`: Many2one field tracking who created the PR
- `supervisor`: Char field for supervisor name (auto-links to user)

### Security Files
- `security/purchase_requisition_security.xml`: Record rules for access control
- `security/ir.model.access.csv`: Basic access rights

## Testing the Access Control

1. **Create a PR as User A**
2. **Assign Supervisor B to the PR**
3. **Login as Supervisor B** - should see the PR
4. **Login as User C** - should not see the PR
5. **Login as Purchase Manager** - should see all PRs

## Notes
- The system uses Odoo's standard record rule mechanism
- Rules are additive (if multiple rules apply, user gets access)
- Purchase managers have full access to all PRs
- Users cannot delete PRs (only managers can) 