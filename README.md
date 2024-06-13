# Python Package Manager README

This extension helps you identify and remove unused Python packages in your projects.

## Features

- **Identify Unused Packages**: Scan your project to find Python packages listed in your `requirements.txt` file that are not used in your codebase.
- **Remove Unused Packages**: Easily remove unused Python packages directly from VS Code.

### Identify Unused Packages

Use the command `Identify Unused Python Packages` to scan your project and list unused packages.

![Identify Unused Packages]

### Remove Unused Packages

Use the command `Remove Unused Python Packages` to uninstall unused packages directly from your virtual environment.

![Remove Unused Packages]

## Requirements

- A virtual environment in your project (`venv`, `env`, `.venv`, `.env`).
- Python and pip installed in the virtual environment.
- VS Code installed.

## Extension Settings

This extension does not contribute any settings.

## Known Issues

- The extension currently supports virtual environments with common names only (`venv`, `env`, `.venv`, `.env`). If your virtual environment has a different name, the extension may not detect it.
- The extension may not work correctly if there are multiple virtual environments in the project.

## Release Notes

### 1.0.0

- Initial release of Python Package Manager.
- Added feature to identify unused Python packages.
- Added feature to remove unused Python packages.

