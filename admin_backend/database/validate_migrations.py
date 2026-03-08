from migration_index import migration_summary


def main():
    summary = migration_summary()

    print(f"MySQL migrations : {summary['mysql_count']}")
    print(f"SQLite migrations: {summary['sqlite_count']}")
    if summary['next_prefix']:
        print(f"Suggested next prefix: {summary['next_prefix']}")

    if summary['warnings']:
        print("\nWarnings:")
        for warning in summary['warnings']:
            print(f"- {warning}")

    if summary['errors']:
        print("\nErrors:")
        for error in summary['errors']:
            print(f"- {error}")
        return 1

    print("\nMigration validation passed.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
