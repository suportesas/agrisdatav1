import sqlite3, json
conn=sqlite3.connect('db.sqlite3')
c=conn.cursor()
tables=['cadastros_cliente','cadastros_enderecocliente','cadastros_contatocliente','cadastros_contabancariacliente','cadastros_documentocliente']
res={}
for t in tables:
    try:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        res[t]=c.fetchone()[0]
    except Exception as e:
        res[t]=str(e)
print(json.dumps(res, indent=2))
