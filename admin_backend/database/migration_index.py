import re
from collections import Counter
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parent / 'migrations'
_MIGRATION_RE = re.compile(r'^(?P<prefix>\d{3})_(?P<name>.+)\.sql$')


def _migration_key(path):
    match = _MIGRATION_RE.match(path.name)
    if match:
        return int(match.group('prefix')), path.name
    return 10**9, path.name


def list_mysql_migrations():
    if not MIGRATIONS_DIR.exists():
        return []
    files = [
        path for path in MIGRATIONS_DIR.iterdir()
        if path.is_file() and path.suffix == '.sql' and not path.name.endswith('_sqlite.sql')
    ]
    return sorted(files, key=_migration_key)


def list_sqlite_migrations():
    if not MIGRATIONS_DIR.exists():
        return []
    files = [
        path for path in MIGRATIONS_DIR.iterdir()
        if path.is_file() and path.name.endswith('_sqlite.sql')
    ]
    return sorted(files, key=_migration_key)


def duplicate_prefixes():
    counts = Counter()
    for path in list_mysql_migrations():
        match = _MIGRATION_RE.match(path.name)
        if match:
            counts[match.group('prefix')] += 1
    return {prefix: count for prefix, count in counts.items() if count > 1}


def invalid_migration_names():
    if not MIGRATIONS_DIR.exists():
        return []
    invalid = []
    for path in sorted(MIGRATIONS_DIR.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.suffix != '.sql':
            continue
        candidate = path.name
        if candidate.endswith('_sqlite.sql'):
            candidate = candidate[:-11] + '.sql'
        if not _MIGRATION_RE.match(candidate):
            invalid.append(path)
    return invalid


def sqlite_files_without_mysql_pair():
    mysql_names = {path.name for path in list_mysql_migrations()}
    missing_pairs = []
    for sqlite_path in list_sqlite_migrations():
        expected_mysql_name = sqlite_path.name[:-11] + '.sql'
        if expected_mysql_name not in mysql_names:
            missing_pairs.append((sqlite_path, expected_mysql_name))
    return missing_pairs


def migration_summary():
    mysql_migrations = list_mysql_migrations()
    sqlite_migrations = list_sqlite_migrations()
    duplicates = duplicate_prefixes()
    invalid_names = invalid_migration_names()
    sqlite_orphans = sqlite_files_without_mysql_pair()

    warnings = []
    errors = []

    for prefix, count in sorted(duplicates.items()):
        warnings.append(f'duplicate prefix {prefix} appears {count} times')

    for path in invalid_names:
        errors.append(f'invalid migration filename: {path.name}')

    for sqlite_path, expected_mysql_name in sqlite_orphans:
        errors.append(
            f'sqlite migration {sqlite_path.name} has no MySQL pair {expected_mysql_name}'
        )

    next_prefix = None
    if mysql_migrations:
        match = _MIGRATION_RE.match(mysql_migrations[-1].name)
        if match:
            next_prefix = f"{int(match.group('prefix')) + 1:03d}"

    return {
        'mysql_count': len(mysql_migrations),
        'sqlite_count': len(sqlite_migrations),
        'warnings': warnings,
        'errors': errors,
        'next_prefix': next_prefix,
    }
