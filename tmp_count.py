import sqlite3,os,sys

db='db.sqlite3'
if not os.path.exists(db):
    print('DB file not found:', db)
    sys.exit(0)
conn=sqlite3.connect(db)
cur=conn.cursor()
try:
    cur.execute('SELECT count(*) FROM cadastros_ncm')
    n=cur.fetchone()[0]
except Exception as e:
    n='ERROR: '+str(e)
try:
    cur.execute('SELECT count(*) FROM cadastros_empresancm')
    m=cur.fetchone()[0]
except Exception as e:
    m='ERROR: '+str(e)
print('cadastros_ncm:', n)
print('cadastros_empresancm:', m)
conn.close()
