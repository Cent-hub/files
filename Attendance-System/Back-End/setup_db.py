"""
Database Setup Script — Attendance Management System
Run this once to initialize the MySQL database with the schema.
"""

import os
import pymysql

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "port":     int(os.environ.get("DB_PORT", 3306)),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "charset":  "utf8mb4",
}

def setup_database():
    try:
        # Connect to MySQL (without specifying database)
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            # Read and execute the schema file
            schema_path = os.path.join(os.path.dirname(__file__), "database.sql")
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = f.read()
            
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in schema.split(";") if s.strip()]
            for stmt in statements:
                cur.execute(stmt)
            
            # Alter existing table if needed
            cur.execute("ALTER TABLE users MODIFY COLUMN email VARCHAR(180) NULL")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS student_type ENUM('regular','irregular') DEFAULT 'regular'")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(20) NULL")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100) NULL")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_picture TEXT NULL")
            cur.execute("ALTER TABLE attendance MODIFY COLUMN status ENUM('present','late','absent') NOT NULL DEFAULT 'present'")
        
        conn.commit()
        conn.close()
        print("✓ Database setup completed successfully!")
        print("  - Database: attendance_db")
        print("  - Tables: users, sessions, attendance")
        return True
    except pymysql.Error as e:
        print(f"✗ MySQL Error: {e}")
        return False
    except FileNotFoundError:
        print("✗ database.sql not found!")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("Setting up Attendance Management System database...")
    setup_database()
