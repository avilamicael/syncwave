# llm_file_reader_v3.py
import os
import json
import hashlib
from pathlib import Path
import ast

# --------------------------------------------------------
# Caminho raiz do projeto Django
# --------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent / "djangoapp"

# --------------------------------------------------------
# Funções utilitárias
# --------------------------------------------------------
def hash_file(filepath):
    """Gera hash md5 de um arquivo"""
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# --------------------------------------------------------
# Funções AST para extrair informações
# --------------------------------------------------------
def parse_class_fields(node):
    """Extrai campos de uma classe com tipo e argumentos"""
    fields = []
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    field_info = {"name": target.id, "type": None, "args": {}}
                    if isinstance(stmt.value, ast.Call):
                        # tenta identificar o tipo de campo (CharField, IntegerField, etc.)
                        if isinstance(stmt.value.func, ast.Attribute):
                            field_info["type"] = stmt.value.func.attr
                        elif isinstance(stmt.value.func, ast.Name):
                            field_info["type"] = stmt.value.func.id
                        # pega argumentos da chamada
                        for kw in stmt.value.keywords:
                            try:
                                field_info["args"][kw.arg] = ast.literal_eval(kw.value)
                            except Exception:
                                field_info["args"][kw.arg] = str(ast.dump(kw.value))
                    fields.append(field_info)
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name):
                field_info = {"name": stmt.target.id, "type": None, "args": {}}
                if isinstance(stmt.value, ast.Call):
                    if isinstance(stmt.value.func, ast.Attribute):
                        field_info["type"] = stmt.value.func.attr
                    elif isinstance(stmt.value.func, ast.Name):
                        field_info["type"] = stmt.value.func.id
                    for kw in stmt.value.keywords:
                        try:
                            field_info["args"][kw.arg] = ast.literal_eval(kw.value)
                        except Exception:
                            field_info["args"][kw.arg] = str(ast.dump(kw.value))
                fields.append(field_info)
    return fields

def parse_classes_functions(file_path):
    """Extrai classes e funções de um arquivo Python"""
    classes = []
    functions = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "fields": parse_class_fields(node)
                }
                classes.append(class_info)
            elif isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "docstring": ast.get_docstring(node),
                    "body": [ast.unparse(stmt) for stmt in node.body] if hasattr(ast, "unparse") else []
                }
                functions.append(func_info)
    except Exception:
        pass  # ignora erros de parsing
    return classes, functions

def extract_urls(file_path):
    """Extrai possíveis URLs de arquivos urls.py como texto"""
    urls = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line_strip = line.strip()
                if line_strip.startswith("path(") or line_strip.startswith("re_path("):
                    urls.append(line_strip)
    except Exception:
        pass
    return urls

# --------------------------------------------------------
# Função de scan de arquivo
# --------------------------------------------------------
def scan_file(file_path):
    info = {
        "path": str(file_path.relative_to(PROJECT_ROOT)),
        "hash": hash_file(file_path),
        "type": "python" if file_path.suffix == ".py" else "other",
    }
    if file_path.suffix == ".py":
        info["classes"], info["functions"] = parse_classes_functions(file_path)
        if file_path.name == "urls.py":
            info["urls"] = extract_urls(file_path)
    return info

# --------------------------------------------------------
# Função de scan da pasta
# --------------------------------------------------------
def scan_folder(root_path):
    """Percorre a pasta e extrai informações de todos os arquivos, ignorando cache e migrations"""
    all_files = []
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "migrations")]
        for file in files:
            path = Path(root) / file
            all_files.append(scan_file(path))
    return all_files

# --------------------------------------------------------
# Função principal
# --------------------------------------------------------
def generate_project_metadata():
    metadata = {
        "project_root": str(PROJECT_ROOT),
        "files": scan_folder(PROJECT_ROOT)
    }
    output_file = PROJECT_ROOT.parent / "informacoes_sistema.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)
    print(f"Metadata completa gerada em {output_file}")

# --------------------------------------------------------
# Executa
# --------------------------------------------------------
if __name__ == "__main__":
    generate_project_metadata()
