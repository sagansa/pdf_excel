import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from database.migration_index import MIGRATIONS_DIR, list_mysql_migrations, migration_summary

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
logger = logging.getLogger(__name__)

# Connection info from environment or defaults
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DB_BASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}"


def _split_sql_statements(sql):
    if 'DELIMITER //' in sql:
        sections = sql.split('DELIMITER //')
        statements = []

        if sections[0].strip():
            statements.extend([s.strip() for s in sections[0].split(';') if s.strip()])

        for section in sections[1:]:
            if '//' in section:
                blocks = section.split('//')
                for block in blocks[:-1]:
                    if block.strip():
                        statements.append(block.strip())

                last_part = blocks[-1].replace('DELIMITER ;', '')
                if last_part.strip():
                    statements.extend([s.strip() for s in last_part.split(';') if s.strip()])
            elif section.strip():
                statements.extend([s.strip() for s in section.split(';') if s.strip()])
        return statements

    return [s.strip() for s in sql.split(';') if s.strip()]


def validate_migration_layout():
    summary = migration_summary()

    logger.info(
        "Migration inventory: mysql=%s sqlite=%s next_prefix=%s",
        summary['mysql_count'],
        summary['sqlite_count'],
        summary['next_prefix'] or 'n/a',
    )

    for warning in summary['warnings']:
        logger.warning("Migration validation warning: %s", warning)

    if summary['errors']:
        for error in summary['errors']:
            logger.error("Migration validation error: %s", error)
        return False

    return True


def run_migrations():
    logger.info("--- Starting Database Migrations ---")

    if not validate_migration_layout():
        logger.error("Database migration validation failed. Aborting migration run.")
        return False
    
    # 1. Ensure Database exists
    try:
        base_engine = create_engine(DB_BASE_URL)
        with base_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
            conn.commit()
    except Exception as e:
        logger.error("Error ensuring database exists: %s", e)
        return False

    # 2. Connect to the database
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            # Create migrations table if not exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pdf_excel_migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE,
                    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()

            # Get list of executed migrations
            result = conn.execute(text("SELECT migration_name FROM pdf_excel_migrations"))
            executed = {row[0] for row in result}

            # 3. Find and run new migrations
            if not MIGRATIONS_DIR.exists():
                logger.error("Migrations directory not found: %s", MIGRATIONS_DIR)
                return False

            migration_files = list_mysql_migrations()
            applied_count = 0
            skipped_count = 0
            current_migration_name = None
            current_statement = None
            
            for migration in migration_files:
                migration_name = migration.name
                if migration_name not in executed:
                    current_migration_name = migration_name
                    logger.info("Running migration: %s", migration_name)
                    with migration.open('r') as f:
                        sql = f.read()

                        statements = _split_sql_statements(sql)

                        for statement in statements:
                            if statement:
                                current_statement = statement
                                conn.execute(text(statement))
                    
                    # Log as executed
                    conn.execute(text("INSERT INTO pdf_excel_migrations (migration_name) VALUES (:name)"), {"name": migration_name})
                    conn.commit()
                    applied_count += 1
                    current_statement = None
                    logger.info("Migration %s completed.", migration_name)
                else:
                    skipped_count += 1

            logger.info(
                "Migration summary: applied=%s skipped=%s total=%s",
                applied_count,
                skipped_count,
                len(migration_files),
            )

    except Exception as e:
        logger.error("Migration failed: %s", e)
        if 'current_migration_name' in locals() and current_migration_name:
            logger.error("Failed migration file: %s", current_migration_name)
        if 'current_statement' in locals() and current_statement:
            preview = " ".join(current_statement.strip().split())
            logger.error("Failed SQL statement: %s", preview[:500])
        return False

    logger.info("--- Migrations Finished ---")
    return True

if __name__ == "__main__":
    run_migrations()
