import sqlite3
con = sqlite3.connect('db.sqlite3')
c = con.cursor()
c.execute("PRAGMA table_info('cadastros_vehicle')")
rows = c.fetchall()
for r in rows:
    print(r)
con.close()
