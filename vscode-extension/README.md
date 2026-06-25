# ai.play — VSCode Extension

Syntax highlighting and run support for `.aip`, `.aimod`, `.aipmcp`, and `.apicuz` files.

**Marketplace:** https://marketplace.visualstudio.com/items?itemName=sintaxsaint.aiplay  
**Repo:** https://github.com/sintaxsaint/ai.play

---

## Install

**From the Marketplace (recommended)**

Open VSCode → Extensions (Ctrl+Shift+X) → search `ai.play` → Install.

Or from the command line:
```
code --install-extension sintaxsaint.aiplay
```

**From a .vsix file**

Extensions panel → `...` menu → Install from VSIX → select `aiplay-X.X.X.vsix`.

---

## Requirements

`aip` must be installed and on your PATH.

- **Windows:** Download `aiplay-setup.exe` from https://github.com/sintaxsaint/ai.play/releases
- **Linux/Mac/Pi:** `pip install aiplay` or `curl -sSL https://raw.githubusercontent.com/sintaxsaint/ai.play/main/install.sh | bash`

---

## Features

### Syntax Highlighting

| Element | Example | Colour |
|---|---|---|
| Directives | `ai.enable()` `ai.model()` | keyword (purple) |
| Pipeline functions | `tokenize()` `embed()` `respond()` | function (yellow) |
| Control flow | `while` `if` `def` | control (orange) |
| Event hooks | `on.connect()` `on.detect()` | tag (teal) |
| Strings | `"text here"` | string (green) |
| Comments | `# comment` | comment (grey) |
| Paths | `./skills/` | path (light green) |
| Booleans | `yes` `no` | constant (blue) |
| Module sections | `Training.data(pairs):` | class (teal) |

### Run Button

Play button in the editor title bar. Click to run in the integrated terminal.

- **F5** — run
- **Ctrl+Shift+C** — syntax check

### Auto-indent

Enter after `:` auto-indents for `while():`, `if():`, `def name():`, `on.connect():` etc.

---

## Settings

`aiplay.executablePath` — path to `aip` if not on PATH. Default: `aip`.

```json
{
  "aiplay.executablePath": "C:\\Program Files\\aiplay\\aip.exe"
}
```

---

## Publishing (maintainer notes)

The extension auto-publishes to the VSCode Marketplace via GitHub Actions on every push to main.

**One-time setup:**

1. Go to https://marketplace.visualstudio.com/manage — sign in, create publisher `sintaxsaint`
2. Go to https://dev.azure.com → User Settings → Personal Access Tokens
3. Create a token with `Marketplace (Manage)` scope
4. Add it as GitHub Actions secret `VSCE_PAT`

The `release.yml` workflow handles packaging and publishing automatically after that.

**Manual publish:**
```bash
npm install -g @vscode/vsce
vsce publish --pat YOUR_PAT_HERE
```

---

## Changelog

### 0.1.0
- Syntax highlighting for `.aip` `.aimod` `.aipmcp` `.apicuz`
- Run button and F5 support
- Syntax check command (Ctrl+Shift+C)
- Auto-indent and bracket auto-close
- Debug config provider

---

## Licence

Free. No telemetry. No data collection.  
Built by sintaxsaint — github.com/sintaxsaint
