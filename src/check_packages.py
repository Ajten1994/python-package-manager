import sys
import os
import ast
import warnings
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor

# Suppress specific warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Base critical packages that should not be uninstalled
BASE_CRITICAL_PACKAGES = {
    "setuptools",
    "pip",
    "wheel",
    "virtualenv",
    "distribute",
    "pkg_resources",
    "ensurepip",
    "pip-tools",
}

EXCEPTION_PACKAGES = ["azure", "django"]

# Done
def find_top_level_imports(filepath):
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
                    imports.add((import_name, filepath, n.lineno))
            elif isinstance(n, ast.ImportFrom):
                if n.module:
                    import_name = n.module.split('.')[0].lower()
                    imports.add((import_name, filepath, n.lineno))
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                parts = n.value.split('.')
                if parts:
                    import_name = parts[0].lower()
                    imports.add((import_name, filepath, n.lineno))
        return imports
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return set()

def find_top_level_imports_venv(filepath):
    try:
        with open(filepath, "r", errors="ignore") as file:
            try:
                node = ast.parse(file.read(), filename=filepath)
            except SyntaxError:
                return set()
        imports = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Import):
                for alias in n.names:
                    import_name = alias.name.split(".")[0].lower()
                    imports.add((import_name, filepath, n.lineno))
            elif isinstance(n, ast.ImportFrom):
                if n.level > 0:
                    import_name = f"{'.' * n.level}{n.module or ''}".rstrip(".")
                else:
                    import_name = n.module.split(".")[0].lower()
                imports.add((import_name, filepath, n.lineno))
        return imports
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return set()

# Done
def find_used_packages(project_root, installed_import_names, venv_path):
    used_packages = set()
    for root, _, files in os.walk(project_root):
        # Exclude virtual environment directories
        if venv_path and root.startswith(venv_path):
            continue
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                imports = find_top_level_imports(filepath)
                for imp, _, _ in imports:
                    if not imp.startswith("."):
                        if imp in installed_import_names:
                            used_packages.add(installed_import_names[imp])
    print(f"Used packages from project files: {used_packages}")
    return used_packages

# Done
def find_used_packages_in_venv(venv_path, used_packages):
    used_packages_in_venv = set()
    for package in used_packages:
        package_path = os.path.join(venv_path, "lib", "site-packages", package)
        if os.path.exists(package_path):
            for root, _, files in os.walk(package_path):
                for file in files:
                    if file.endswith(".py"):
                        filepath = os.path.join(root, file)
                        imports = find_top_level_imports_venv(filepath)
                        for imp, _, _ in imports:
                            if not imp.startswith("."):
                                used_packages_in_venv.add(imp)
    print(f"Used packages from venv files: {used_packages_in_venv}")
    return used_packages_in_venv


# Done
def get_import_names(distributions, package_name):
    try:
        normalized_package_name = package_name.replace("-", "_").lower()
        if normalized_package_name in distributions:
            import_names = [name.lower() for name in distributions[normalized_package_name]]
            print(import_names)
            return import_names
        return [package_name.lower()]
    except Exception as e:
        print(f"Error retrieving import names for {package_name}: {e}")
        return [package_name.lower()]


# Done
def get_pip_installed_packages(venv_python):
    try:
        result = subprocess.run(
            [venv_python, "-m", "pip", "list", "--format=freeze"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"Error executing pip list: {result.stderr}")
            return set()
        installed_packages = set(
            line.split("==")[0].lower() for line in result.stdout.strip().split("\n")
        )
        print(f"Installed packages: {installed_packages}")
        return installed_packages
    except Exception as e:
        print(f"Error getting installed pip packages: {e}")
        return set()


# Done
def find_virtualenv(project_root):
    potential_dirs = ["venv", "env", ".venv", ".env"]
    for d in potential_dirs:
        venv_path = os.path.join(project_root, d)
        python_executable = os.path.join(
            venv_path, "Scripts", "python.exe" if os.name == "nt" else "bin/python"
        )
        if os.path.exists(python_executable):
            return python_executable
    return None


# Done
def remove_from_requirements(unused_packages, project_root):
    requirements_path = os.path.join(project_root, "requirements.txt")
    if not os.path.exists(requirements_path):
        return
    with open(requirements_path, "r", encoding="utf-16le") as file:
        lines = file.readlines()
    with open(requirements_path, "w", encoding="utf-16le") as file:
        for line in lines:
            package_name = line.split("==")[0].lower().strip()
            if package_name not in unused_packages:
                file.write(line)


# Done
def generate_requirements(venv_python, project_root):
    try:
        result = subprocess.run(
            [venv_python, "-m", "pip", "freeze"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"Error executing pip freeze: {result.stderr}")
            return
        requirements_path = os.path.join(project_root, "requirements.txt")
        with open(requirements_path, "w", encoding="utf-16le") as file:
            file.write(result.stdout)
        print(f"Generated requirements.txt at {requirements_path}")
    except Exception as e:
        print(f"Error generating requirements.txt: {e}")


# Done
def get_package_dependencies(package_name, venv_python):
    try:
        result = subprocess.run(
            [venv_python, "-m", "pip", "show", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"Error executing pip show for {package_name}: {result.stderr}")
            return []
        dependencies = []
        for line in result.stdout.strip().split("\n"):
            if line.startswith("Requires:"):
                dependencies = [
                    dep.strip().lower()
                    for dep in line.split(":", 1)[1].split(",")
                    if dep.strip()
                ]
                break
        return dependencies
    except Exception as e:
        print(f"Error getting dependencies for {package_name}: {e}")
        return []


# Done
def find_package_usage(package_name, project_root, venv_path):
    def search_in_files(root_path):
        for root, _, files in os.walk(root_path):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    imports = find_top_level_imports(filepath)
                    for imp, file_path, lineno in imports:
                        if imp == package_name:
                            print(
                                f"{package_name} found in {file_path} on line {lineno}"
                            )

    print(f"Searching for usage of {package_name} in project files:")
    search_in_files(project_root)

    if venv_path:
        print(f"Searching for usage of {package_name} in venv files:")
        search_in_files(venv_path)


# Done
def main(action, project_root, package_to_check=None):
    try:
        venv_python = find_virtualenv(project_root)
        if not venv_python:
            print(f"No virtual environment found in {project_root}")
            return
        print(f"Found virtual environment Python executable at: {venv_python}")

        installed_packages = get_pip_installed_packages(venv_python)
        # Create a script to fetch the metadata from the virtual environment
        script = """
import importlib.metadata as metadata
import json

result = {}
for dist in metadata.distributions():
    name = dist.metadata['Name'].replace('-', '_').lower()
    files = [f.name for f in dist.files]
    if 'top_level.txt' in files:
        with open(next(f.locate() for f in dist.files if f.name == 'top_level.txt')) as f:
            result[name] = f.read().splitlines()
print(json.dumps(result))
"""

        # Run the script in the context of the virtual environment
        cmd = [venv_python, "-c", script]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Error executing command: {result.stderr}")

        distributions = json.loads(result.stdout)

        package_import_names = {
            pkg: get_import_names(distributions, pkg) for pkg in installed_packages
        }
        installed_import_names = {
            name: pkg for pkg, names in package_import_names.items() for name in names
        }

        if action == "identify" or action == "remove":
            venv_path = os.path.dirname(os.path.dirname(venv_python))

            # Find used packages in project files
            used_packages = find_used_packages(
                project_root, installed_import_names, venv_path
            )

            # Find used packages in venv files
            used_packages_in_venv = find_used_packages_in_venv(venv_path, used_packages)

            # Combine both sets of used packages
            all_used_packages = used_packages.union(used_packages_in_venv)

            # Get dependencies for each used package within the venv
            with ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(get_package_dependencies, pkg, venv_python)
                    for pkg in used_packages
                ]
                for future in futures:
                    all_used_packages.update(future.result())

            # Ensure that if any "azure" or "django" package is used, all related packages are also considered used
            for exception in EXCEPTION_PACKAGES:
                if any(exception in pkg for pkg in all_used_packages):
                    all_used_packages.update(
                        pkg for pkg in installed_packages if exception in pkg
                    )

            unused_packages = []
            for pkg, names in package_import_names.items():
                if pkg not in all_used_packages and not any(
                    name in all_used_packages for name in names
                ):
                    unused_packages.append(pkg)

            # Ensure critical packages and their dependencies are not marked as unused
            critical_packages = set(BASE_CRITICAL_PACKAGES)
            all_dependencies = set()
            with ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(get_package_dependencies, pkg, venv_python)
                    for pkg in installed_packages
                ]
                for future in futures:
                    all_dependencies.update(future.result())
            critical_packages.update(all_dependencies)

            unused_packages = [
                pkg for pkg in unused_packages if pkg not in critical_packages
            ]
            print(f"Number of unused packages: {len(unused_packages)}")
            unused_packages.sort()

            if action == "identify":
                for pkg in unused_packages:
                    print(f"Unused package: {pkg}")
            elif action == "remove":
                remove_from_requirements(unused_packages, project_root)
                for pkg in unused_packages:
                    print(f"Removing package: {pkg}")
                    subprocess.run(["pip", "uninstall", "-y", pkg])

        elif action == "generate":
            generate_requirements(venv_python, project_root)

        elif action == "check_usage" and package_to_check:
            venv_path = os.path.dirname(os.path.dirname(venv_python))
            find_package_usage(package_to_check, project_root, venv_path)

    except Exception as e:
        print(f"Error executing {action} action: {e}")


if __name__ == "__main__":
    if len(sys.argv) not in [3, 4]:
        print(
            "Usage: python check_packages.py <action> <project_root> [<package_to_check>]"
        )
    else:
        main(*sys.argv[1:])
