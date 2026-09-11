import sys
sys.stdout.reconfigure(encoding='utf-8')
import pymysql

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='#123**Vinnu@',
    database='pothole_db'
)
cursor = conn.cursor()

# Add damage_percentage column if not exists
cursor.execute("SHOW COLUMNS FROM reports LIKE 'damage_percentage'")
result = cursor.fetchone()
if result:
    print('Column already exists - no changes needed.')
else:
    cursor.execute("ALTER TABLE reports ADD COLUMN damage_percentage VARCHAR(100) DEFAULT NULL")
    conn.commit()
    print('SUCCESS: damage_percentage column added to MySQL!')

cursor.close()
conn.close()
