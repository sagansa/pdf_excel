# Database Folder

This folder stores SQL migrations and the helper used by `migrate.py` to load them safely.

## Layout

- `migrations/`
  - MySQL migrations: `NNN_description.sql`
  - SQLite-only variants: `NNN_description_sqlite.sql`
- `migration_index.py`
  - Central place for migration discovery and ordering
- `validate_migrations.py`
  - Local validator for migration naming and pairing

## Important Rules

1. Do not rename migrations that may already be recorded in `pdf_excel_migrations`.
2. MySQL runtime only executes `.sql` files that do not end with `_sqlite.sql`.
3. Duplicate numeric prefixes currently exist. Execution order is resolved by:
   - numeric prefix first
   - full filename second
4. If you add a new migration, prefer a new unused prefix instead of reusing an existing one.
5. If you need SQLite support, add a paired `_sqlite.sql` file rather than mixing dialects in one migration.

## Current Caveat

Several historical migrations reuse the same numeric prefix, for example `012`, `013`, `017`, `018`, `020`, `026`, `027`, `028`, `043`, and `045`.

That is preserved for compatibility. The loader now warns about duplicates at startup so the ordering remains explicit instead of implicit.

## Validation

Run this from `admin_backend`:

```bash
python3 database/validate_migrations.py
```

The validator reports:

- warning: duplicate numeric prefixes
- error: invalid migration filename pattern
- error: `_sqlite.sql` file without a matching MySQL migration
