"""sx.py -- a small s-expression reader for KiCad files (analysis only; edits are made as text)."""
import re
TOK = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')
def parse(text):
    stack = [[]]
    for m in TOK.finditer(text):
        t = m.group()
        if t == '(':
            new = []; stack[-1].append(new); stack.append(new); new.append(('@', m.start()))
        elif t == ')':
            done = stack.pop(); done[0] = ('@', done[0][1], m.end())
        elif t[0] == '"': stack[-1].append(t[1:-1].replace('\\"', '"').replace('\\n', '\n'))
        else: stack[-1].append(t)
    return stack[0][0]
def kids(n, name): return [c for c in n[1:] if isinstance(c, list) and len(c) > 1 and c[1] == name]
def kid(n, name):
    k = kids(n, name); return k[0] if k else None
def span(n): return n[0][1], n[0][2]
