import sys
path = sys.argv[1]
with open(path, 'r', encoding='utf-8', errors='replace') as fh:
    for i, line in enumerate(fh):
        if i>=100: break
        parts = line.split(';')
        first = parts[0].strip()
        print(i+1, repr(first))
