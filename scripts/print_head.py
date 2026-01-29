import sys
path = sys.argv[1]
with open(path, 'r', encoding='utf-8', errors='replace') as fh:
    for i in range(10):
        line = fh.readline()
        if not line:
            break
        print(f'{i+1}: {line.rstrip()}')
