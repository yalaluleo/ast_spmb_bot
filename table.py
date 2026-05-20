import mysql.connector

conn = mysql.connector.connect(
    host="mysql-1c97201-spmb2026.e.aivencloud.com",
    port=25591,
    user="avnadmin",
    password="AVNS_I-hQWUMjZhW2Y3eGCk-",
    database="defaultdb",
    ssl_ca="ca.pem",
    ssl_verify_cert=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50),
    username VARCHAR(100),
    full_name VARCHAR(200),
    admin_msg_id VARCHAR(50),
    file_id TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    admin_handler VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
print("✅ Tabel berhasil dibuat!")

cursor.execute("SHOW TABLES")
for table in cursor.fetchall():
    print(f"📋 Tabel: {table[0]}")

cursor.close()
conn.close()