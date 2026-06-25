const vscode = require('vscode');
const path = require('path');
const { spawn } = require('child_process');

let terminal = null;

function getAipPath() {
    const config = vscode.workspace.getConfiguration('aiplay');
    return config.get('executablePath') || 'aip';
}

function runFile(filePath, checkOnly = false) {
    const aip = getAipPath();
    const args = checkOnly ? ['check', filePath] : [filePath];
    const cwd = path.dirname(filePath);
    const label = checkOnly ? 'ai.play Syntax Check' : 'ai.play';

    // Reuse or create terminal
    if (!terminal || terminal.exitStatus !== undefined) {
        terminal = vscode.window.createTerminal({
            name: label,
            cwd: cwd
        });
    }

    terminal.show(true);

    if (process.platform === 'win32') {
        terminal.sendText(`${aip} ${args.join(' ')}`);
    } else {
        terminal.sendText(`${aip} ${args.join(' ')}`);
    }
}

// Debug config provider — intercepts F5 and runs in terminal instead of debugger
class AipConfigProvider {
    provideDebugConfigurations(folder, token) {
        return [{
            name: 'Run ai.play',
            type: 'aiplay',
            request: 'launch',
            file: '${file}'
        }];
    }
    resolveDebugConfiguration(folder, config, token) {
        // If F5 pressed with no config, build one from active file
        if (!config.type && !config.request && !config.name) {
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document.fileName.endsWith('.aip')) {
                config.type = 'aiplay';
                config.request = 'launch';
                config.name = 'Run ai.play';
                config.file = editor.document.fileName;
            }
        }
        if (config.type === 'aiplay') {
            // Run in terminal instead of debugger
            const filePath = config.file || (vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.fileName);
            if (filePath) {
                vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.save().then(function() {
                    runFile(filePath, false);
                });
            }
            return undefined; // returning undefined cancels the debug session
        }
        return config;
    }
}

function activate(context) {

    // Run command
    const runCmd = vscode.commands.registerCommand('aiplay.run', function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active file to run.');
            return;
        }

        const filePath = editor.document.fileName;
        if (!filePath.endsWith('.aip')) {
            vscode.window.showErrorMessage('This is not an .aip file.');
            return;
        }

        // Save before running
        editor.document.save().then(function () {
            runFile(filePath, false);
        });
    });

    // Syntax check command
    const checkCmd = vscode.commands.registerCommand('aiplay.check', function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const filePath = editor.document.fileName;
        if (!filePath.endsWith('.aip')) return;

        editor.document.save().then(function () {
            runFile(filePath, true);
        });
    });

    // Status bar run button
    const statusBtn = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBtn.text = '$(play) Run ai.play';
    statusBtn.command = 'aiplay.run';
    statusBtn.tooltip = 'Run this .aip file (F5)';

    // Show/hide status bar button based on active file
    function updateStatusBar() {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.fileName.endsWith('.aip')) {
            statusBtn.show();
        } else {
            statusBtn.hide();
        }
    }

    // Register debug config provider to intercept F5
    const debugProvider = vscode.debug.registerDebugConfigurationProvider(
        'aiplay',
        new AipConfigProvider(),
        vscode.DebugConfigurationProviderTriggerKind.Dynamic
    );

    context.subscriptions.push(
        runCmd,
        checkCmd,
        statusBtn,
        debugProvider,
        vscode.window.onDidChangeActiveTextEditor(updateStatusBar)
    );

    updateStatusBar();
}

function deactivate() {
    if (terminal) terminal.dispose();
}

module.exports = { activate, deactivate };
