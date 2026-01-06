import sys
p='static/js/cadastros_cliente.js'
s=open(p,'rb').read().decode('utf8')
pairs={'(':')','[':']','{':'}'}
stack=[]
for i,ch in enumerate(s,1):
    if ch in '([{': stack.append((ch,i))
    elif ch in ')]}':
        if not stack:
            print('UNMATCHED CLOSING',ch,'at',i); sys.exit(1)
        o,pos = stack.pop()
        if pairs[o]!=ch:
            print('MISMATCH',o,'at',pos,'vs',ch,'at',i); sys.exit(1)
if stack:
    print('UNMATCHED OPENING',stack[-1][0],'at',stack[-1][1]); sys.exit(1)
print('BRACKETS_OK')
if s.count('`')%2!=0:
    print('UNMATCHED_BACKTICK')
else:
    print('BACKTICKS_OK')
