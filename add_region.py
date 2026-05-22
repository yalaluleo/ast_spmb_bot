import mysql.connector

MYSQLHOST = "monorail.proxy.rlwy.net" 
MYSQLUSER = "root"  
MYSQLPASSWORD = "jTXeuHolkXnJTxuieaVjjXOOvPBJjUge"  
MYSQLDATABASE = "railway"
MYSQLPORT = 43153

try:
    conn = mysql.connector.connect(
        host=MYSQLHOST,
        user=MYSQLUSER,
        password=MYSQLPASSWORD,
        database=MYSQLDATABASE,
        port=MYSQLPORT
    )
    
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE submissions ADD COLUMN region VARCHAR(20) DEFAULT 'banten'")
    conn.commit()
    print("✅ Kolom region BERHASIL ditambahkan!")

except Exception as e:
    print(f"Error: {e}")

finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()