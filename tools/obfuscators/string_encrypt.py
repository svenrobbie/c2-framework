import ast
import os
import random
import string


def _rand_name(prefix='_', length=8):
    return prefix + ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


def obfuscate_file(filepath: str, key: bytes | None = None, key_name: str | None = None, func_name: str | None = None) -> str:
    if key is None:
        key = bytes(random.randint(0, 255) for _ in range(256))
    if key_name is None:
        key_name = _rand_name('_k')
    if func_name is None:
        func_name = _rand_name('_d')

    with open(filepath) as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source

    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node

    joinedstr_ancestors = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            for child in ast.walk(node):
                if child is not node:
                    joinedstr_ancestors.add(id(child))

    replacements = []
    offset = 0
    protected_names = {'__name__', '__main__'}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if node.value == '' or node.value in protected_names:
            continue
        if id(node) in joinedstr_ancestors:
            continue

        parent = parents.get(id(node))
        if parent is None:
            continue

        if isinstance(parent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = parent.body
            if body and body[0] is node:
                continue

        if isinstance(parent, (ast.Import, ast.ImportFrom)):
            continue

        original = node.value
        encoded = original.encode('utf-8')
        encrypted = bytes(
            b ^ key[(offset + i) % len(key)]
            for i, b in enumerate(encoded)
        )
        replacements.append((node, encrypted, offset))
        offset += len(encoded)

    if not replacements:
        return source

    class Replacer(ast.NodeTransformer):
        def __init__(self, repl_map):
            self.repl_map = repl_map

        def visit_Constant(self, node):
            if node in self.repl_map:
                encrypted, off = self.repl_map[node]
                return ast.Call(
                    func=ast.Name(id=func_name, ctx=ast.Load()),
                    args=[
                        ast.List(
                            elts=[ast.Constant(value=b) for b in encrypted],
                            ctx=ast.Load()
                        ),
                        ast.Constant(value=off),
                    ],
                    keywords=[]
                )
            return node

    repl_map = {node: (enc, off) for node, enc, off in replacements}
    tree = Replacer(repl_map).visit(tree)
    ast.fix_missing_locations(tree)
    modified = ast.unparse(tree)

    header = (
        f"{key_name} = {list(key)}\n"
        f"def {func_name}(d, o):\n"
        f"    return ''.join(chr(b ^ {key_name}[(o + i) % len({key_name})]) for i, b in enumerate(d))\n\n"
    )
    return header + modified


def obfuscate_tree(root_dir: str, key: bytes | None = None) -> int:
    if key is None:
        key = bytes(random.randint(0, 255) for _ in range(256))

    count = 0
    seen_names = set()

    for dirpath, _dirs, files in os.walk(root_dir):
        for fname in files:
            if not fname.endswith('.py'):
                continue
            fpath = os.path.join(dirpath, fname)

            kn = _rand_name('_k')
            while kn in seen_names:
                kn = _rand_name('_k')
            fn = _rand_name('_d')
            while fn in seen_names:
                fn = _rand_name('_d')
            seen_names.update([kn, fn])

            result = obfuscate_file(fpath, key, kn, fn)
            if result:
                with open(fpath, 'w') as f:
                    f.write(result)
                count += 1

    return count
