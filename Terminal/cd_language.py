"""Interpreteur et editeur du langage CD pour Clem Terminal."""
from __future__ import annotations
import ast
import re
import shlex
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

EDITOR_NAME = "Clem Editor"

class CDError(Exception):
    pass

class CDInterpreter:
    def __init__(self, command_runner, output, max_steps=10000):
        self.command_runner = command_runner
        self.output = output
        self.max_steps = max_steps
        self.steps = 0
        self.globals = {}
        self.functions = {}

    def say(self, value=""):
        self.output(str(value))

    def tick(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise CDError("Limite d'instructions dépassée (boucle infinie ?) ")

    @staticmethod
    def _split_top(text, separator=','):
        parts, start, depth, quote, escaped = [], 0, 0, None, False
        for i, ch in enumerate(text):
            if quote:
                if ch == quote and not escaped: quote = None
                escaped = (ch == '\\' and not escaped)
                if ch != '\\': escaped = False
                continue
            if ch in ('"', "'"): quote = ch
            elif ch in '([{': depth += 1
            elif ch in ')]}': depth -= 1
            elif ch == separator and depth == 0:
                parts.append(text[start:i].strip()); start = i + 1
        parts.append(text[start:].strip())
        return [p for p in parts if p]

    def expr(self, source, env):
        source = source.strip()
        if source.startswith('|') and source.endswith('|'):
            inner = source[1:-1].strip()
            if not inner: return []
            entries = self._split_top(inner, ';')
            if all(':' in x for x in entries):
                result = {}
                for item in entries:
                    k, v = item.split(':', 1)
                    key = k.strip().strip('\"\'')
                    try: value = self.expr(v, env)
                    except CDError: value = v.strip().strip('\"\'')
                    result[key] = value
                return result
            values = []
            for item in self._split_top(inner):
                try: values.append(self.expr(item, env))
                except CDError: values.append(item.strip().strip('\"\''))
            return values
        try:
            tree = ast.parse(source, mode='eval')
            return self._eval_node(tree.body, env)
        except CDError: raise
        except Exception as exc: raise CDError(f"Expression invalide '{source}': {exc}")

    def _eval_node(self, n, env):
        if isinstance(n, ast.Constant): return n.value
        if isinstance(n, ast.Name):
            if n.id in env: return env[n.id]
            if n.id in self.globals: return self.globals[n.id]
            raise CDError(f"Variable inconnue : {n.id}")
        if isinstance(n, ast.List): return [self._eval_node(x, env) for x in n.elts]
        if isinstance(n, ast.Tuple): return tuple(self._eval_node(x, env) for x in n.elts)
        if isinstance(n, ast.Dict): return {self._eval_node(k, env): self._eval_node(v, env) for k,v in zip(n.keys,n.values)}
        if isinstance(n, ast.Subscript): return self._eval_node(n.value, env)[self._eval_node(n.slice, env)]
        if isinstance(n, ast.BinOp) and type(n.op) in _BINOPS:
            return _BINOPS[type(n.op)](self._eval_node(n.left, env), self._eval_node(n.right, env))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _UNARY:
            return _UNARY[type(n.op)](self._eval_node(n.operand, env))
        if isinstance(n, ast.Compare):
            left = self._eval_node(n.left, env)
            for op, comp in zip(n.ops, n.comparators):
                right = self._eval_node(comp, env)
                fn = _CMPS.get(type(op))
                if not fn or not fn(left, right): return False
                left = right
            return True
        if isinstance(n, ast.BoolOp):
            vals = [self._eval_node(x, env) for x in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            name = n.func.id
            args = [self._eval_node(x, env) for x in n.args]
            if name == 'print': self.say(' '.join(map(str,args))); return None
            if name in self.functions: return self.call_function(name, args)
            raise CDError(f"Fonction inconnue : {name}")
        raise CDError(f"Expression non autorisée : {ast.dump(n, include_attributes=False)}")

    def call_function(self, name, args):
        params, body = self.functions[name]
        if len(args) != len(params): raise CDError(f"{name} attend {len(params)} argument(s)")
        local = dict(zip(params, args))
        returned, value = self.execute(body, local, in_function=True)
        if not returned: raise CDError(f"La fonction {name} s'est terminée sans return")
        return value

    def _extract_block(self, lines, start):
        # Le crochet ouvrant doit être sur la ligne de début ou la suivante.
        line = lines[start].strip()
        if '[' in line:
            before, after = line.split('[', 1)
            initial = after
        else:
            before, initial = line, ''
            start += 1
            if start >= len(lines) or lines[start].strip() != '[':
                raise CDError("Crochet '[' attendu")
        depth = 1
        body = []
        if initial.strip():
            if ']' in initial:
                content, tail = initial.split(']',1)
                if content.strip(): body.append(content)
                return before.strip(), body, start
            body.append(initial)
        i = start + 1
        while i < len(lines):
            current = lines[i]
            # Compte les crochets hors chaînes/commentaires.
            clean = current.split('#',1)[0]
            depth += clean.count('[') - clean.count(']')
            if depth <= 0:
                prefix = clean.rsplit(']',1)[0]
                if prefix.strip(): body.append(prefix)
                return before.strip(), body, i
            body.append(current)
            i += 1
        raise CDError("Bloc non fermé : ']' manquant")

    def execute(self, lines, env=None, in_function=False):
        if env is None: env = self.globals
        i = 0
        while i < len(lines):
            self.tick()
            raw = lines[i].strip()
            i += 1
            if not raw or raw.startswith('#'): continue
            if raw.startswith('if['):
                close = raw.find(']')
                if close < 0: raise CDError("Crochet ']' manquant après if")
                condition = raw[3:close].strip()
                if i >= len(lines) or lines[i].strip() != '[':
                    raise CDError("Bloc '[' attendu après if[condition]")
                _, yes, end = self._extract_block(lines, i)
                i = end + 1
                if self.expr(condition, env):
                    ret, val = self.execute(yes, env, in_function)
                    if ret: return True, val
                if i < len(lines) and lines[i].strip().startswith('else'):
                    _, no, end = self._extract_block(lines, i)
                    i = end + 1
                    if not self.expr(condition, env):
                        ret, val = self.execute(no, env, in_function)
                        if ret: return True, val
                continue
            if raw.startswith('if '):
                condition = raw[3:].strip()
                if i >= len(lines) or lines[i].strip() != '[':
                    raise CDError("Bloc '[' attendu après if")
                _, yes, end = self._extract_block(lines, i); i=end+1
                if self.expr(condition, env):
                    ret, val = self.execute(yes, env, in_function)
                    if ret: return True, val
                if i < len(lines) and lines[i].strip().startswith('else'):
                    _, no, end = self._extract_block(lines, i); i=end+1
                    if not self.expr(condition, env):
                        ret, val = self.execute(no, env, in_function)
                        if ret: return True, val
                continue
            if raw.startswith('repeat '):
                header, body, end = self._extract_block(lines, i-1); i = end+1
                bits = header.split()
                if len(bits) != 4: raise CDError("Syntaxe : repeat variable start stop [")
                var = bits[1]; start = int(self.expr(bits[2],env)); stop = int(self.expr(bits[3],env))
                for value in range(start, stop+1):
                    env[var] = value
                    ret, val = self.execute(body, env, in_function)
                    if ret: return True, val
                continue
            if raw.startswith('while '):
                header, body, end = self._extract_block(lines, i-1); i=end+1
                condition = header[len('while '):].strip()
                while self.expr(condition, env):
                    self.tick()
                    ret, val = self.execute(body, env, in_function)
                    if ret: return True, val
                continue
            if raw.startswith('else'):
                continue
            if raw.startswith('return'):
                if not in_function: raise CDError("return utilisable uniquement dans une fonction")
                value = raw[6:].strip()
                return True, self.expr(value, env) if value else None
            # Déclaration de fonction : nom(args) [ ... ]
            match = re.match(r'^([A-Za-z_]\w*)\s*\((.*?)\)\s*\[$', raw)
            if match:
                name, argtext = match.groups()
                params = [x.strip() for x in argtext.split(',') if x.strip()]
                _, body, end = self._extract_block(lines, i-1); i=end+1
                if not any(x.strip().startswith('return') for x in body):
                    raise CDError(f"La fonction {name} doit contenir un return")
                self.functions[name] = (params, body)
                continue
            # Affectation (en respectant ==)
            assign = re.match(r'^([A-Za-z_]\w*(?:\[[^]]+\])?)\s*=\s*(?!=)(.+)$', raw)
            if assign:
                target, value = assign.groups(); result = self.expr(value, env)
                if '[' in target:
                    name, index = target.split('[',1); env[name][self.expr(index[:-1],env)] = result
                else: env[target] = result
                continue
            # Appel de fonction autonome, par exemple print(variable).
            if re.match(r'^[A-Za-z_]\w*\s*\(.*\)$', raw):
                self.expr(raw, env)
                continue
            # Commande du terminal : expansion des arguments CD.
            self.command_runner(raw, env, self)
        return False, None

    def run(self, source):
        self.steps = 0
        self.globals = {}
        self.functions = {}
        lines = source.splitlines()
        self.execute(lines)

# Operators are explicitly whitelisted.
import operator as _op
_BINOPS = {ast.Add:_op.add, ast.Sub:_op.sub, ast.Mult:_op.mul, ast.Div:_op.truediv, ast.FloorDiv:_op.floordiv, ast.Mod:_op.mod, ast.Pow:_op.pow}
_UNARY = {ast.USub:_op.neg, ast.UAdd:_op.pos, ast.Not:_op.not_}
_CMPS = {ast.Eq:_op.eq, ast.NotEq:_op.ne, ast.Lt:_op.lt, ast.LtE:_op.le, ast.Gt:_op.gt, ast.GtE:_op.ge, ast.In:_op.contains, ast.NotIn:lambda a,b:not _op.contains(a,b)}

class CDEditor:
    def __init__(self, master, interpreter_factory):
        self.master = master
        self.interpreter_factory = interpreter_factory
        self.path = None
        self.window = tk.Toplevel(master)
        self.window.title(f"{EDITOR_NAME} — Nouveau fichier.cd")
        self.window.geometry('1050x720')
        self.window.configure(bg='#101018')
        self._build()
        self._bind_shortcuts()

    def _build(self):
        bar = tk.Frame(self.window, bg='#181824', height=48); bar.pack(fill='x')
        tk.Label(bar, text='CLEM EDITOR', bg='#181824', fg='#f2f2ff', font=('Consolas',12,'bold')).pack(side='left', padx=16)
        for label, fn in [('Nouveau',self.new_file),('Ouvrir',self.open_file),('Enregistrer',self.save_file),('▶ Exécuter',self.run_file)]:
            tk.Button(bar,text=label,command=fn,bg='#29293a',fg='white',activebackground='#41415a',relief='flat',padx=12,pady=7).pack(side='right',padx=5,pady=7)
        self.name = tk.Label(self.window,text='Nouveau fichier.cd',bg='#101018',fg='#9ca3af',anchor='w',font=('Consolas',10)); self.name.pack(fill='x',padx=14,pady=(8,3))
        area = tk.Frame(self.window,bg='#101018'); area.pack(fill='both',expand=True,padx=12,pady=8)
        self.numbers = tk.Text(area,width=4,bg='#171722',fg='#687084',font=('Consolas',11),state='disabled',relief='flat',padx=6); self.numbers.pack(side='left',fill='y')
        self.text = tk.Text(area,bg='#11111b',fg='#e5e7eb',insertbackground='white',font=('Consolas',11),undo=True,relief='flat',padx=12,pady=10,tabs=('36p',)); self.text.pack(side='left',fill='both',expand=True)
        self.text.tag_configure('comment',foreground='#727c8f'); self.text.tag_configure('keyword',foreground='#c4a7ff'); self.text.tag_configure('string',foreground='#a5df9b'); self.text.tag_configure('command',foreground='#7dcfff'); self.text.tag_configure('number',foreground='#f5bd75')
        self.text.bind('<KeyRelease>',self.highlight)
        self.output = tk.Text(self.window,height=8,bg='#09090e',fg='#b8c2d8',font=('Consolas',10),relief='flat',state='disabled'); self.output.pack(fill='x',padx=12,pady=(0,12))
        self.refresh_numbers(); self.highlight()

    def _bind_shortcuts(self):
        self.window.bind('<Control-s>',lambda e:self.save_file()); self.window.bind('<Control-o>',lambda e:self.open_file()); self.window.bind('<F5>',lambda e:self.run_file())

    def refresh_numbers(self):
        count=int(self.text.index('end-1c').split('.')[0]); self.numbers.configure(state='normal'); self.numbers.delete('1.0','end'); self.numbers.insert('1.0','\n'.join(map(str,range(1,count+1)))); self.numbers.configure(state='disabled')

    def highlight(self,event=None):
        content=self.text.get('1.0','end-1c')
        for tag in ('comment','keyword','string','command','number'): self.text.tag_remove(tag,'1.0','end')
        patterns={'comment':r'#[^\n]*','string':r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'','keyword':r'\b(?:if|else|repeat|while|return|true|false|and|or|not)\b','number':r'\b\d+(?:\.\d+)?\b','command':r'\b(?:cresce|gen_image|gen_video|save_img|delflow|cinit|copen|tik|print)\b'}
        for tag,pattern in patterns.items():
            for m in re.finditer(pattern,content):
                start=f'1.0+{m.start()}c'; end=f'1.0+{m.end()}c'; self.text.tag_add(tag,start,end)
        self.refresh_numbers()

    def new_file(self):
        if self.text.edit_modified() and not messagebox.askyesno('Nouveau','Abandonner les modifications non enregistrées ?'): return
        self.text.delete('1.0','end'); self.path=None; self.name.configure(text='Nouveau fichier.cd'); self.text.edit_modified(False)

    def open_file(self):
        path=filedialog.askopenfilename(parent=self.window,filetypes=[('Scripts CD','*.cd'),('Tous les fichiers','*.*')])
        if not path:return
        self.path=Path(path); self.text.delete('1.0','end'); self.text.insert('1.0',self.path.read_text(encoding='utf-8')); self.name.configure(text=self.path.name); self.text.edit_modified(False); self.highlight()

    def save_file(self):
        """Enregistre le script. Retourne True si réussi, False sinon.

        Toute erreur est affichée (console du Clem Editor + boîte de dialogue) :
        avant, une exception dans un callback Tk n'apparaissait nulle part, et
        un enregistrement réussi sur un fichier existant ne montrait rien.
        """
        try:
            if self.path is None:
                chosen = filedialog.asksaveasfilename(
                    parent=self.window,
                    title='Enregistrer le script CD',
                    initialdir=str(Path.cwd()),
                    initialfile='script.cd',
                    defaultextension='.cd',
                    filetypes=[('Scripts CD', '*.cd'), ('Tous les fichiers', '*.*')]
                )
                if not chosen:
                    return False
                self.path = Path(chosen)
            if self.path.suffix.lower() != '.cd':
                self.path = self.path.with_name(self.path.name + '.cd')

            # Garde-fou : ne jamais écraser un fichier non vide par un éditeur vide.
            new_text = self.text.get('1.0', 'end-1c')
            if not new_text.strip() and self.path.exists() and self.path.stat().st_size > 0:
                if not messagebox.askyesno(
                    'Enregistrer',
                    f"L'éditeur est vide mais {self.path.name} contient déjà du texte.\n"
                    "Écraser le fichier avec un contenu vide ?",
                    parent=self.window
                ):
                    self.log('Enregistrement annulé (éditeur vide).')
                    return False

            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(self.text.get('1.0', 'end-1c'), encoding='utf-8')
        except Exception as exc:
            self.log(f'ERREUR enregistrement : {type(exc).__name__}: {exc}')
            messagebox.showerror('Enregistrer', f"Impossible d'enregistrer :\n{exc}", parent=self.window)
            return False

        self.name.configure(text=self.path.name)
        self.window.title(f'{EDITOR_NAME} — {self.path.name}')
        self.text.edit_modified(False)
        self.log(f'✓ Enregistré : {self.path.resolve()}')
        return True

    def log(self,message):
        self.output.configure(state='normal'); self.output.insert('end',str(message)+'\n'); self.output.see('end'); self.output.configure(state='disabled')

    def run_file(self):
        if not self.save_file(): return
        self.output.configure(state='normal'); self.output.delete('1.0','end'); self.output.configure(state='disabled')
        try:
            interpreter=self.interpreter_factory(self.log)
            interpreter.run(self.text.get('1.0','end-1c'))
            self.log('✓ Script terminé.')
        except Exception as exc: self.log(f'ERREUR : {exc}')