import pymysql

DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "",
    "db":       "attendance_db",
    "charset":  "utf8mb4",
}

try:
    conn = pymysql.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE attendance MODIFY COLUMN status ENUM('present','late','absent') NOT NULL DEFAULT 'present'")
    conn.commit()
    conn.close()
    print("✓ Database updated successfully!")
except Exception as e:
    print(f"✗ Error: {e}")