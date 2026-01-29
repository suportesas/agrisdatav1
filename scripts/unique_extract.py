import csv
seen=set()
out=r'c:\erp_agricola\arq_ncm\ncm_extracted_unique.csv'
with open(r'c:\erp_agricola\arq_ncm\ncm_extracted.csv','r',encoding='utf-8') as fh:
    r=csv.DictReader(fh)
    rows=[]
    for row in r:
        if row['codigo'] not in seen:
            seen.add(row['codigo'])
            rows.append(row)
with open(out,'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=['codigo','nome'])
    w.writeheader()
    w.writerows(rows)
print('Unique exported', len(rows), 'to', out)