import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password=""
)

cursor = db.cursor()

# Buat database
cursor.execute("CREATE DATABASE IF NOT EXISTS spmb_banten")
cursor.execute("USE spmb_banten")

# Buat tabel
table_query = """
CREATE TABLE IF NOT EXISTS submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    username VARCHAR(255),
    full_name VARCHAR(255),
    file_id VARCHAR(255),
    status ENUM('pending', 'processing', 'approved', 'rejected') DEFAULT 'pending',
    admin_handler VARCHAR(255),
    admin_msg_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""
cursor.execute(table_query)

# TAMBAHKAN INDEX (INI YANG MEMPERCEPAT)
try:
    cursor.execute("CREATE INDEX idx_user_id ON submissions(user_id)")
    cursor.execute("CREATE INDEX idx_admin_msg_id ON submissions(admin_msg_id)")
    cursor.execute("CREATE INDEX idx_status ON submissions(status)")
    print("Index berhasil ditambahkan!")
except Exception as e:
    print(f"Index mungkin sudah ada: {e}")

print("Database dan tabel siap!")

db.close()