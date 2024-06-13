import * as vscode from 'vscode';
import { execFile } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

function getVirtualEnvPython(workspaceRoot: string): string | null {
    const potentialDirs = ["venv", "env", ".venv", ".env"];
    for (const dir of potentialDirs) {
        const venvPython = path.join(workspaceRoot, dir, 'Scripts', 'python.exe');
        if (fs.existsSync(venvPython)) {
            return venvPython;
        }
        const venvPythonUnix = path.join(workspaceRoot, dir, 'bin', 'python');
        if (fs.existsSync(venvPythonUnix)) {
            return venvPythonUnix;
        }
    }
    return null;
}

function identifyUnusedPackages() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }

    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const pythonScriptPath = path.join(vscode.extensions.getExtension('akeemmckenzie.python-package-manager-pro')!.extensionPath, 'src', 'check_packages.py');
    const outputFilePath = path.join(workspaceRoot, 'unusedpackages.txt');

    const venvPython = getVirtualEnvPython(workspaceRoot);
    if (!venvPython) {
        vscode.window.showErrorMessage('No virtual environment found in the workspace.');
        return;
    }

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "Checking Python packages...",
        cancellable: false
    }, (progress) => {
        return new Promise<void>((resolve, reject) => {
            execFile(venvPython, [pythonScriptPath, workspaceRoot], (error, stdout, stderr) => {
                if (error) {
                    vscode.window.showErrorMessage(`Error executing Python script: ${error.message}`);
                    reject();
                    return;
                }

                if (stderr) {
                    console.warn(`Python script warning: ${stderr}`);
                }

                let unusedPackages = stdout.trim().split('\n').filter(pkg => pkg.startsWith('Unused package: ')).map(pkg => pkg.replace('Unused package: ', ''));

                if (unusedPackages.length > 0) {
                    console.log('Unused Packages:', unusedPackages);
                    fs.writeFile(outputFilePath, unusedPackages.join('\n'), 'utf16le', (err) => {
                        if (err) {
                            vscode.window.showErrorMessage(`Error writing to file: ${err.message}`);
                            reject();
                            return;
                        }
                        vscode.window.showInformationMessage(`Unused packages found and written to unusedpackages.txt`);
                        // Open the file in VSCode
                        vscode.workspace.openTextDocument(outputFilePath).then(doc => {
                            vscode.window.showTextDocument(doc);
                        });
                        unusedPackages = []; // Reset the variable
                        resolve();
                    });
                } else {
                    vscode.window.showInformationMessage('All packages are used.');
                    resolve();
                }
            });
        });
    });
}

function removeUnusedPackages() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }

    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const pythonScriptPath = path.join(vscode.extensions.getExtension('akeemmckenzie.python-package-manager-pro')!.extensionPath, 'src', 'check_packages.py');

    const venvPython = getVirtualEnvPython(workspaceRoot);
    if (!venvPython) {
        vscode.window.showErrorMessage('No virtual environment found in the workspace.');
        return;
    }

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "Identifying and removing unused Python packages...",
        cancellable: false
    }, (progress) => {
        return new Promise<void>((resolve, reject) => {
            execFile(venvPython, [pythonScriptPath, workspaceRoot], (error, stdout, stderr) => {
                if (error) {
                    vscode.window.showErrorMessage(`Error executing Python script: ${error.message}`);
                    reject();
                    return;
                }

                if (stderr) {
                    console.warn(`Python script warning: ${stderr}`);
                }

                let unusedPackages = stdout.trim().split('\n').filter(pkg => pkg.startsWith('Unused package: ')).map(pkg => pkg.replace('Unused package: ', ''));

                if (unusedPackages.length > 0) {
                    const terminal = vscode.window.createTerminal('Python Package Manager');
                    unusedPackages.forEach(pkg => {
                        const uninstallCommand = `${venvPython} -m pip uninstall -y ${pkg}`;
                        terminal.sendText(uninstallCommand, true);
                    });
                    terminal.show();
                    unusedPackages = [];
                    resolve();
                } else {
                    vscode.window.showInformationMessage('No unused packages to remove.');
                    resolve();
                }
            });
        });
    });
}

export function activate(context: vscode.ExtensionContext) {
    let identifyDisposable = vscode.commands.registerCommand('extension.identifyUnusedPackages', identifyUnusedPackages);
    let removeDisposable = vscode.commands.registerCommand('extension.removeUnusedPackages', removeUnusedPackages);

    context.subscriptions.push(identifyDisposable);
    context.subscriptions.push(removeDisposable);
}

export function deactivate() {}
