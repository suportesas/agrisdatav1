import os
import sqlite3

db = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'db.sqlite3'))
print('DB:', db)
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("PRAGMA table_info('cadastros_vehicle')")
rows = c.fetchall()
for r in rows:
    print(r)
conn.close()
