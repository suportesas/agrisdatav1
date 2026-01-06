import sqlite3
import json
conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
c.execute("PRAGMA table_info('cadastros_cliente');")
cols = c.fetchall()
print(json.dumps([{'cid': r[0], 'name': r[1], 'type': r[2], 'notnull': r[3], 'dflt_value': r[4], 'pk': r[5]} for r in cols], indent=2, ensure_ascii=False))
