import os
from sqlalchemy import create_engine, text
from datetime import datetime

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
                CREATE TABLE IF NOT EXISTS migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE,
                    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()

            # Get list of executed migrations
            result = conn.execute(text("SELECT migration_name FROM migrations"))
            executed = {row[0] for row in result}

            # 3. Find and run new migrations
            migrations_dir = os.path.join(os.path.dirname(__file__), 'database', 'migrations')
            if not os.path.exists(migrations_dir):
                print(f"Migrations directory not found: {migrations_dir}")
                return False

            migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
            
            for migration in migration_files:
                if migration not in executed:
                    print(f"Running migration: {migration}")
                    file_path = os.path.join(migrations_dir, migration)
                    with open(file_path, 'r') as f:
                        sql = f.read()
                        # SQLAlchemy executes one statement at a time in many cases, 
                        # so if migration has multiple it might need splitting.
                        # For simplicity, we execute the whole block.
                        statements = [s.strip() for s in sql.split(';') if s.strip()]
                        for statement in statements:
                            conn.execute(text(statement))
                    
                    # Log as executed
                    conn.execute(text("INSERT INTO migrations (migration_name) VALUES (:name)"), {"name": migration})
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
