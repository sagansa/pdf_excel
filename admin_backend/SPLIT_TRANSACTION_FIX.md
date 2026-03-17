# Fix: Split Transactions Not Appearing in CoreTax Reports (2025)

## Problem

Split transactions (transactions with `parent_id`) were not appearing in CoreTax reports for year 2025, while they worked correctly in 2024.

Additionally, rent expense (Beban Sewa - COA 5315/5105) was appearing in CoreTax reports even without proper COA mappings.

## Root Cause

### 1. Incorrect mark_id Reference in income_statement_service.py

**Before:**
```python
if 'parent_id' in txn_columns:
    parent_join = "LEFT JOIN transactions t_parent ON t.parent_id = t_parent.id"
    mark_ref = (
        f"COALESCE({normalize_mark_ref('t.mark_id')}, "
        f"{normalize_mark_ref('t_parent.mark_id')})"
    )
```

This caused child transactions to use parent's mark_id (which is NULL), making the INNER JOIN with marks table fail.

**After:**
```python
if 'parent_id' in txn_columns:
    parent_join = "LEFT JOIN transactions t_parent ON t.parent_id = t_parent.id"
    # Use transaction's own mark_id (for both parent and child transactions)
    mark_ref = normalize_mark_ref('t.mark_id')
```

### 2. Missing Split Exclusion in Marks Summary Query

The `build_marks_summary_query()` function in `report_queries.py` was not using `_split_parent_exclusion_clause`, causing parent transactions to be counted alongside their children (double-counting).

### 3. Missing report_type Parameter

The marks summary API endpoint was not accepting or using the `report_type` parameter, so CoreTax filtering was not applied.

### 4. Rent Expense Without CoreTax Mapping

**IMPORTANT**: Rent expense (5315/5105) should **NOT** appear in CoreTax reports unless the mark has a proper CoreTax COA mapping. This is the correct behavior.

Database analysis shows:
- **real mappings**: 114 mappings (57 unique marks)
- **coretax mappings**: 2 mappings (1 unique mark)
- **Only 1 mark** has both real and coretax mappings

If rent expense is appearing in CoreTax without proper mappings, it indicates a data configuration issue, not a code bug.

## Solution

### How Split Transactions Work

1. **Parent Transaction**: Container for split entries, `mark_id = NULL`
2. **Child Transactions**: Individual split entries, each with their own `mark_id`
3. **Relationship**: `child.parent_id = parent.id`

### Correct Behavior

- **Parent should be excluded** from reports when it has children (to prevent double-counting)
- **Children should be included** in reports (they have the actual mark_id mappings)
- **Each child uses its own mark_id** for COA mapping, not parent's mark_id
- **CoreTax reports** only include transactions with CoreTax COA mappings

### Files Changed

1. **backend/services/reporting/report_sql_fragments.py**
   - Updated `_split_parent_exclusion_clause` with better documentation
   - Logic: Exclude parent if it has children with mark_id

2. **backend/routes/accounting_utils.py**
   - Updated `split_parent_exclusion_clause` with documentation
   - Logic: Exclude parent if it has children

3. **backend/routes/transactions/payroll_utils.py**
   - Updated `_split_parent_exclusion_clause` with documentation
   - Logic: Exclude parent if it has children

4. **backend/services/reporting/income_statement_service.py** ⭐ **CRITICAL FIX**
   - Changed `mark_ref` to use `t.mark_id` directly instead of COALESCE with parent
   - This ensures child transactions use their own mark_id for COA mapping

5. **backend/routes/reporting/report_queries.py** ⭐ **CRITICAL FIX**
   - Updated `build_marks_summary_query()` to accept `report_type` parameter
   - Added split exclusion clause to prevent double-counting
   - Added CoreTax filtering for marks summary

6. **backend/routes/reporting/report_bp.py**
   - Updated `get_marks_summary()` to accept and pass `report_type` parameter

## Testing

### Run Verification Test

```bash
cd /Users/gargar/Development/super_admin/pdf_excel/admin_backend
python3 test_split_transactions.py
```

### Expected Results

1. **Split transactions by year**:
   - 2024: ~60 child transactions
   - 2025: ~106 child transactions
   - All child transactions should have `mark_id IS NOT NULL`

2. **CoreTax mappings**:
   - Check if marks have `report_type='coretax'` mappings in `mark_coa_mapping` table
   - Without coretax mappings, transactions will not appear in CoreTax reports

3. **Income Statement (CoreTax)**:
   - Split transactions should appear with their respective COA mappings
   - Parent transactions should not appear (no double-counting)
   - Total amounts should be correct

4. **Marks Summary (CoreTax)**:
   - Only marks with coretax COA mappings should appear
   - Split transactions should be counted once (no double-counting)

### To Verify the Fix

1. **Create a split transaction** for year 2025:
   - Create a parent transaction
   - Split it into multiple child transactions with different marks
   - Ensure each child has a COA mapping with `report_type='coretax'`

2. **Check Income Statement** (CoreTax report type):
   - Child transactions should appear with their respective COA mappings
   - Parent transaction should not appear (to prevent double-counting)
   - Total amounts should be correct

3. **Compare 2024 vs 2025**:
   - Both years should now behave consistently
   - Split transactions should appear in both years (if they have coretax mappings)

## Database Schema

The fix assumes the following schema:

```sql
CREATE TABLE transactions (
    id CHAR(36) PRIMARY KEY,
    parent_id CHAR(36),              -- NULL for standalone/parent, references parent for children
    mark_id CHAR(36),                -- NULL for parent, set for children
    -- ... other fields
    FOREIGN KEY (parent_id) REFERENCES transactions(id),
    FOREIGN KEY (mark_id) REFERENCES marks(id)
);

CREATE TABLE mark_coa_mapping (
    id CHAR(36) PRIMARY KEY,
    mark_id CHAR(36),
    coa_id CHAR(36),
    report_type VARCHAR(20),         -- 'real' or 'coretax'
    mapping_type VARCHAR(20),        -- 'DEBIT' or 'CREDIT'
    FOREIGN KEY (mark_id) REFERENCES marks(id),
    FOREIGN KEY (coa_id) REFERENCES chart_of_accounts(id)
);
```

## Related Code

### save_transaction_splits (history_bp.py)

When splits are saved:
```python
# Parent mark_id is set to NULL
UPDATE transactions SET mark_id = NULL WHERE id = :txn_id

# Children are created with their own mark_id
INSERT INTO transactions (parent_id, mark_id, ...) VALUES (:parent_id, :mark_id, ...)
```

### _split_parent_exclusion_clause

```python
# Excludes parent from reports when children exist
" AND NOT EXISTS ("
"SELECT 1 FROM transactions t_child "
"WHERE t_child.parent_id = t.id "
"AND mark_id IS NOT NULL)"
```

## Impact

- **CoreTax reports (2025)**: Split transactions now appear correctly (if they have coretax mappings)
- **Real reports**: No change (already working)
- **Historical data (2024)**: No change (already working)
- **Future years**: Will work correctly with split transactions
- **Rent expense**: Will only appear in CoreTax if mark has coretax COA mapping

## Important Notes

### Rent Expense in CoreTax

If rent expense (5315/5105) is appearing in CoreTax reports without proper mappings:

1. **Check mark_coa_mapping table**:
   ```sql
   SELECT mark_id, coa_id, report_type
   FROM mark_coa_mapping
   WHERE coa_id IN (
       SELECT id FROM chart_of_accounts WHERE code IN ('5315', '5105')
   );
   ```

2. **Add coretax mapping if needed**:
   - Go to Marks view
   - Edit the mark
   - Add COA mapping with report_type = 'coretax'

3. **Or configure amortization settings**:
   - Set `prepaid_rent_expense_coa` in `amortization_settings` table
   - This will create automatic rent expense adjustments

### Data Migration

To add coretax mappings for existing marks:

```sql
-- Copy real mappings to coretax (if appropriate)
INSERT INTO mark_coa_mapping (id, mark_id, coa_id, report_type, mapping_type, created_at, updated_at)
SELECT UUID(), mark_id, coa_id, 'coretax', mapping_type, NOW(), NOW()
FROM mark_coa_mapping
WHERE report_type = 'real'
  AND mark_id NOT IN (
      SELECT mark_id FROM mark_coa_mapping WHERE report_type = 'coretax'
  );
```

**⚠️ Warning**: Only do this after reviewing with accounting team. Not all real mappings should have coretax equivalents.
