import sqlite3

db_path = 'db.sqlite3'
con = sqlite3.connect(db_path)
cur = con.cursor()

def show_table(table):
    print(f"\nTable: {table}")
    cur.execute(f"PRAGMA table_info('{table}')")
    rows = cur.fetchall()
    print('cid | name | type | notnull | dflt_value | pk')
    for r in rows:
        print(' | '.join(str(x) for x in r))

show_table('cadastros_cliente')
show_table('cadastros_enderecocliente')
con.close()
