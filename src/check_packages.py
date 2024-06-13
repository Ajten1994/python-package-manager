import sys
import os
import ast
import warnings
import subprocess
from importlib import metadata

# Suppress specific warnings
warnings.filterwarnings('ignore', category=SyntaxWarning)

def find_imports_in_file(filepath):
    try:
        with open(filepath, 'r', errors='ignore') as file:
            try:
                node = ast.parse(file.read(), filename=filepath)
            except SyntaxError:
                return set()
        imports = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Import):
                for alias in n.names:
                    imports.add(alias.name.split('.')[0].lower())
            elif isinstance(n, ast.ImportFrom) and n.module:
                imports.add(n.module.split('.')[0].lower())
        return imports
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return set()

def find_used_packages(project_root):
    used_packages = set()
    for root, _, files in os.walk(project_root):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                used_packages.update(find_imports_in_file(filepath))
    return used_packages

def get_import_names(package_name):
    try:
        distribution = metadata.distribution(package_name)
        if 'top_level.txt' in {file.name for file in distribution.files}:
            import_names = distribution.read_text('top_level.txt').splitlines()
            return [name.lower() for name in import_names]
        else:
            return [package_name.lower()]
    except Exception as e:
        print(f"Error getting import names for {package_name}: {e}")
        return [package_name.lower()]

def get_pip_installed_packages(venv_python):
    try:
        result = subprocess.run([venv_python, '-m', 'pip', 'list', '--format=freeze'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error executing pip list: {result.stderr}")
            return set()
        installed_packages = set(line.split('==')[0].lower() for line in result.stdout.strip().split('\n'))
        return installed_packages
    except Exception as e:
        print(f"Error getting installed pip packages: {e}")
        return set()

def find_virtualenv(project_root):
    potential_dirs = ["venv", "env", ".venv", ".env"]
    for d in potential_dirs:
        venv_path = os.path.join(project_root, d, 'Scripts', 'python.exe' if os.name == 'nt' else 'bin/python')
        if os.path.exists(venv_path):
            return venv_path
    return None

def main(project_root):
    try:
        venv_python = find_virtualenv(project_root)
        if not venv_python:
            print(f"No virtual environment found in {project_root}")
            return

        used_packages = find_used_packages(project_root)
        installed_packages = get_pip_installed_packages(venv_python)
        unused_packages = []

        for pkg in installed_packages:
            import_names = get_import_names(pkg)
            if not any(name in used_packages for name in import_names):
                unused_packages.append(pkg)

        unused_packages.sort()

        for pkg in unused_packages:
            print(f"Unused package: {pkg}")
    except Exception as e:
        print(f"Error finding unused packages: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python check_packages.py <project_root>")
    else:
        main(sys.argv[1])
