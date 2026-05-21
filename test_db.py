import os
import mysql.connector

try:
    conn = mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT") or 3306)
    )
    print("Database connected!")
    conn.close()
except Exception as e:
    print(f"Error: {e}")