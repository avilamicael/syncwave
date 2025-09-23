import os
import json
from pathlib import Path

def get_directory_structure(root_dir, max_depth=None, exclude_dirs=None):
    """
    Gera a estrutura de diretórios em formato de dicionário
    
    Args:
        root_dir (str): Diretório raiz para escanear
        max_depth (int): Profundidade máxima de recursão (None para ilimitado)
        exclude_dirs (list): Lista de diretórios para excluir
    
    Returns:
        dict: Estrutura do diretório em formato de dicionário
    """
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', '.vscode', 'venv', 'env', 'node_modules', '.idea', 'migrations']
    
    root_path = Path(root_dir)
    
    def build_tree(path, current_depth=0):
        if max_depth is not None and current_depth >= max_depth:
            return None
        
        if not path.exists() or not path.is_dir():
            return None
        
        # Pula diretórios excluídos
        if path.name in exclude_dirs or any(exclude in str(path) for exclude in exclude_dirs):
            return None
        
        structure = {
            'name': path.name,
            'type': 'directory',
            'path': str(path),
            'contents': []
        }
        
        try:
            items = list(path.iterdir())
            # Ordena: diretórios primeiro, depois arquivos
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            for item in items:
                if item.is_dir():
                    sub_tree = build_tree(item, current_depth + 1)
                    if sub_tree:
                        structure['contents'].append(sub_tree)
                else:
                    # Inclui apenas alguns tipos de arquivo comuns em projetos Django
                    if item.suffix in ['.py', '.html', '.css', '.js', '.json', '.txt', '.md', '.yml', '.yaml']:
                        structure['contents'].append({
                            'name': item.name,
                            'type': 'file',
                            'path': str(item),
                            'extension': item.suffix
                        })
        
        except PermissionError:
            # Ignora diretórios sem permissão
            pass
        
        return structure
    
    return build_tree(root_path)

def save_structure_to_json(structure, output_file='project_structure.json'):
    """Salva a estrutura em um arquivo JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structure, f, indent=2, ensure_ascii=False)
    
    print(f"Estrutura salva em: {output_file}")

def print_structure_summary(structure):
    """Imprime um resumo da estrutura"""
    def count_items(tree):
        files = 0
        dirs = 0
        if tree['type'] == 'directory':
            dirs += 1
            for item in tree['contents']:
                if item['type'] == 'directory':
                    sub_files, sub_dirs = count_items(item)
                    files += sub_files
                    dirs += sub_dirs
                else:
                    files += 1
        return files, dirs
    
    files, dirs = count_items(structure)
    print(f"📁 Diretórios: {dirs}")
    print(f"📄 Arquivos: {files}")
    print(f"📍 Diretório raiz: {structure['path']}")

# Exemplo de uso para um projeto Django
if __name__ == "__main__":
    # Define o diretório raiz do seu projeto Django
    project_root = '.'  # Diretório atual, ajuste conforme necessário
    
    # Gera a estrutura
    structure = get_directory_structure(
        root_dir=project_root,
        max_depth=5,  # Limita a profundidade para não ficar muito grande
        exclude_dirs=['__pycache__', '.git', 'venv', 'env', 'migrations', '.vscode', '.idea']
    )
    
    if structure:
        # Salva em JSON
        save_structure_to_json(structure, 'django_project_structure.json')
        
        # Imprime resumo
        print_structure_summary(structure)
        
        # Mostra um preview da estrutura
        print("\n📋 Preview da estrutura:")
        print(json.dumps(structure, indent=2, ensure_ascii=False)[:1000] + "...")
    else:
        print("❌ Não foi possível gerar a estrutura. Verifique o caminho do diretório.")