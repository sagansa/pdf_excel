import os
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connection info from environment or defaults
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DB_BASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}"

def run_migrations():
    print("--- Starting Database Migrations ---")
    
    # 1. Ensure Database exists
    try:
        base_engine = create_engine(DB_BASE_URL)
        with base_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
            conn.commit()
    except Exception as e:
        print(f"Error ensuring database exists: {e}")
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
            migrations_dir = os.path.join(os.path.dirname(__file__), 'database', 'migrations')
            if not os.path.exists(migrations_dir):
                print(f"Migrations directory not found: {migrations_dir}")
                return False

            migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql') and not f.endswith('_sqlite.sql')])
            
            for migration in migration_files:
                if migration not in executed:
                    print(f"Running migration: {migration}")
                    file_path = os.path.join(migrations_dir, migration)
                    with open(file_path, 'r') as f:
                        sql = f.read()
                        
                        # Handle DELIMITER //
                        if 'DELIMITER //' in sql:
                            # Split into sections by DELIMITER //
                            sections = sql.split('DELIMITER //')
                            statements = []
                            
                            # The first section is regular SQL
                            if sections[0].strip():
                                statements.extend([s.strip() for s in sections[0].split(';') if s.strip()])
                            
                            for section in sections[1:]:
                                if '//' in section:
                                    # This section contains one or more blocks followed by //
                                    blocks = section.split('//')
                                    # All except the last one are trigger/proc blocks
                                    for block in blocks[:-1]:
                                        if block.strip():
                                            statements.append(block.strip())
                                    
                                    # The last part of the last section might have regular SQL after DELIMITER ;
                                    last_part = blocks[-1].replace('DELIMITER ;', '')
                                    if last_part.strip():
                                        statements.extend([s.strip() for s in last_part.split(';') if s.strip()])
                                else:
                                    # This shouldn't happen with well-formed DELIMITER // ... // DELIMITER ;
                                    if section.strip():
                                        statements.extend([s.strip() for s in section.split(';') if s.strip()])
                        else:
                            # Standard splitting by semicolon
                            statements = [s.strip() for s in sql.split(';') if s.strip()]
                            
                        for statement in statements:
                            if statement:
                                conn.execute(text(statement))
                    
                    # Log as executed
                    conn.execute(text("INSERT INTO pdf_excel_migrations (migration_name) VALUES (:name)"), {"name": migration})
                    conn.commit()
                    print(f"Migration {migration} completed.")
                else:
                    # print(f"Skipping {migration} (already executed)")
                    pass

    except Exception as e:
        print(f"Migration failed: {e}")
        return False

    print("--- Migrations Finished ---")
    return True

if __name__ == "__main__":
    run_migrations()
