import sys, re
path = sys.argv[1]
valid = 0
invalid = 0
samples_valid = []
samples_invalid = []
with open(path, 'r', encoding='utf-8', errors='replace') as fh:
    for i, line in enumerate(fh):
        parts = line.split(';')
        if not parts: continue
        first = parts[0].strip()
        if i==0:
            # header
            header = first
            continue
        code_norm = re.sub(r'\D', '', first)
        if len(code_norm)==8:
            valid += 1
            if len(samples_valid)<10:
                samples_valid.append(code_norm)
        else:
            invalid += 1
            if len(samples_invalid)<10:
                samples_invalid.append(first)
print('header:', header)
print('rows:', valid+invalid, 'valid:', valid, 'invalid:', invalid)
print('valid samples:', samples_valid[:10])
print('invalid samples:', samples_invalid[:10])
