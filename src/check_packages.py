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
                    import_name = alias.name.split('.')[0].lower()
                    imports.add(import_name)
            elif isinstance(n, ast.ImportFrom) and n.module:
                import_name = n.module.split('.')[0].lower()
                imports.add(import_name)
        return imports
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return set()

def find_used_packages(project_root, installed_import_names, venv_path):
    used_packages = set()
    for root, _, files in os.walk(project_root):
        # Exclude virtual environment directories
        if venv_path and root.startswith(venv_path):
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                imports = find_imports_in_file(filepath)
                used_packages.update(imports.intersection(installed_import_names))
    print(f"used packages: {used_packages}")
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
        print(f"Installed packages : {installed_packages}")
        return installed_packages
    except Exception as e:
        print(f"Error getting installed pip packages: {e}")
        return set()

def find_virtualenv(project_root):
    potential_dirs = ["venv", "env", ".venv", ".env"]
    for d in potential_dirs:
        venv_path = os.path.join(project_root, d)
        python_executable = os.path.join(venv_path, 'Scripts', 'python.exe' if os.name == 'nt' else 'bin/python')
        if os.path.exists(python_executable):
            return python_executable
    return None

def remove_from_requirements(unused_packages, project_root):
    requirements_path = os.path.join(project_root, 'requirements.txt')
    if not os.path.exists(requirements_path):
        return
    with open(requirements_path, 'r') as file:
        lines = file.readlines()
    with open(requirements_path, 'w') as file:
        for line in lines:
            package_name = line.split('==')[0].lower().strip()
            if package_name not in unused_packages:
                file.write(line)

def generate_requirements(venv_python, project_root):
    try:
        result = subprocess.run([venv_python, '-m', 'pip', 'freeze'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error executing pip freeze: {result.stderr}")
            return
        requirements_path = os.path.join(project_root, 'requirements.txt')
        with open(requirements_path, 'w') as file:
            file.write(result.stdout)
        print(f"Generated requirements.txt at {requirements_path}")
    except Exception as e:
        print(f"Error generating requirements.txt: {e}")

def main(action, project_root):
    try:
        venv_python = find_virtualenv(project_root)
        if not venv_python:
            print(f"No virtual environment found in {project_root}")
            return
        print(f"Found virtual environment Python executable at: {venv_python}")

        installed_packages = get_pip_installed_packages(venv_python)
        installed_import_names = set()

        for pkg in installed_packages:
            installed_import_names.update(get_import_names(pkg))

        if action == "identify" or action == "remove":
            venv_path = os.path.dirname(os.path.dirname(venv_python))  # Get the virtual env directory
            used_packages = find_used_packages(project_root, installed_import_names, venv_path)
            unused_packages = [pkg for pkg in installed_packages if not any(name in used_packages for name in get_import_names(pkg))]

            unused_packages.sort()

            if action == "identify":
                for pkg in unused_packages:
                    print(f"Unused package: {pkg}")
            elif action == "remove":
                remove_from_requirements(unused_packages, project_root)
                for pkg in unused_packages:
                    print(f"Removing package: {pkg}")
                    subprocess.run([venv_python, '-m', 'pip', 'uninstall', '-y', pkg])

        elif action == "generate":
            generate_requirements(venv_python, project_root)

    except Exception as e:
        print(f"Error executing {action} action: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python check_packages.py <action> <project_root>")
    else:
        main(sys.argv[1], sys.argv[2])
