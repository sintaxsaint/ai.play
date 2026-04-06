# ai.play

A programming language for building AI systems. Write `.aip` files. Run them with `aip yourfile.aip`.

No build step. No config. Live-compiled — edit the file, run again, changes apply instantly. Runs entirely on your device. No cloud. No API key. No data leaving your machine.

**Version:** 0.8  
**Repo:** github.com/sintaxsaint/ai.play  
**Modules:** sintaxsaint.pages.dev  
**Community:** https://github.com/sintaxsaint/ai.play/issues

---

## Install

**Windows**

Download and run `aiplay-setup.exe` from the latest release.

Installs to `C:\Program Files\aiplay\`, adds `aip` to PATH, registers `.aip` file associations.

**Linux / Mac / Raspberry Pi**

```bash
curl -sSL https://raw.githubusercontent.com/sintaxsaint/ai.play/main/install.sh | bash
```

Or via pip:

```bash
pip install aiplay
```

**Chrome OS**

Not supported. Possibly never. If you're reading this on a Chromebook — genuinely, why? Open an issue and tell us. We're not judging. We're a little judging. We want to know.

**Python / Google Colab**

```python
import aiplay
aiplay.run("""
ai.enable()
ai.web(yes)
test.ui(yes)
""")
```

---

## Quick Start

```
ai.enable()
ai.model(factual)
ai.web(yes)
test.ui(yes)

def pipeline():
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)

while(yes):
    pipeline()
```

---

## Language Reference

### Required first line
```
ai.enable()
```

---

### Model
```
ai.model(factual)
ai.model(fun)
ai.model(thinking)
ai.model(custom, ./spec)
```

---

### Capabilities
```
ai.web(yes)
ai.vision(normal)
ai.vision(live)
ai.diffusion(yes)
ai.video(yes)
ai.voice(yes)
```

---

### Persona
```
ai.persona("You are a helpful assistant.")
```

---

### Identity
```
ai.name(Aria)
ai.version(1.0)
ai.creator(sintaxsaint)
```

Automatically teaches the AI its name, version, and creator. Ask it "what are you" and it answers correctly.

---

### Language
```
ai.language(english)
ai.language(french)
ai.language(spanish)
ai.language(japanese)
```

All responses are automatically translated. Supports any language Google Translate supports. Default is English.

---

### Memory
```
ai.memory(rule)
ai.memory(generative)
ai.memory(upload)
ai.memory(upload, https://memory.yoursite.com)
```

---

### Artifacts
```
artifacts.on(yes)
```

Enables the artifact system. The AI can now produce full files as artifacts — rendered in the test UI with Code and Preview tabs and a download button.

AI produces artifacts using:
```
<artifact type="py" name="script.py">
def hello():
    print("Hello!")
hello()
</artifact>
```

Supported preview types: `.html`, `.htm`, `.svg` (live iframe preview). All other types show code with a download button.

Auto-detection: responses of 5+ lines that look like code are automatically treated as artifacts even without the explicit tag.

---

### Error Handling
```
ai.fallback(Sorry, I do not know the answer to that)
```

---

### Logging
```
ai.log(./output.log)

log(Response)
```

---

### Notifications
```
ai.notify(email, you@example.com)
ai.notify(sms, +441234567890)
ai.notify(webhook, https://yoursite.com/alert)
ai.notify(discord, https://discord.com/api/webhooks/...)
```

Inside event hooks:
```
on.detect(stranger):
    notify.discord(Unknown person detected)
```

---

### Remote Training Data
```
ai.train(https://yoursite.com/data.json)
```

Downloads and embeds training data from a URL on startup. Supports the same formats as `train.embed()`.

---

### Scheduling
```
ai.schedule(30m, ./task.aip)
ai.schedule(09:00, ./morning.aip)
ai.schedule(1h, ./hourly.aip)
```

Intervals: `s` seconds, `m` minutes, `h` hours. Clock time: `HH:MM`.

---

### Encryption
```
ai.encrypt(yes)
```

Encrypts memory and storage at rest.

---

### MCP Connector
```
ai.mcp(https://your-mcp-server.com)
```

Connects to an MCP server, fetches its tool list, and injects the tools as training knowledge so the AI knows how to use them.

---

### Admin Access
```
ai.admin(ask)
ai.admin(destructive)
ai.admin(full)
```

Gives the AI shell access to the host machine.

- `ask` — prompts for approval before every command
- `destructive` — runs normal commands silently, prompts only for dangerous ones
- `full` — runs everything without asking (use with caution)

---

### Sandbox
```
sandbox.start(venv)
sandbox.start(docker)
sandbox.install(numpy)
sandbox.run(python script.py)
```

Runs code in an isolated environment. `venv` creates a temporary Python virtualenv. `docker` uses a locked-down container with no network, 512MB RAM cap, and falls back to venv if Docker isn't available.

---

### Output Deny
```
output.deny()
```

Suppresses AI output. Full enforcement in v1.

---

### ai.yes — one-line AI clone
```
ai.yes(chatgpt)
ai.yes(claude)
ai.yes(copilot)
ai.yes(gemini)
ai.yes(whisper)
ai.yes(elevenlabs)
```

Finds the best MIT or Apache 2.0 licensed equivalent on HuggingFace, checks the licence, downloads weights, auto-configures capabilities.

Full local ChatGPT equivalent in 3 lines:
```
ai.enable()
ai.yes(chatgpt)
test.ui(yes)
```

---

### Skills
```
ai.skills(./skills/)
```

`.skill` file format:
```
name: Customer Support
keywords: help, problem, issue, broken, refund
tone: friendly and patient
priority: 10
---
how do I return an item:Submit a return request within 30 days
```

---

### Custom Modules
```
custom.module(python)
custom.module(./mymodules/stripe.aimod)
```

Create a blank template:
```
make.module(javascript)
```

System modules directory:
- Windows: `C:\Program Files\aiplay\modules\`
- Linux/Mac: `~/.aiplay/modules/`

Find and share modules: https://sintaxsaint.pages.dev

---

### Training Data
```
train.embed(./data.data)
```

Auto-detects: ai.play native pairs, OpenAI JSONL, JSON, CSV, PDF, DOCX, plain text, code files.

Native format:
```
Training.data(pairs):
what is gravity:The force that attracts objects toward each other
```

---

### Techniques
```
technique.add(sql_injection, ./techniques/sqli.txt)
technique.add(xss, The XSS payload is <script>alert(1)</script>)
```

Persistent across sessions. In chat, type `save this as a technique: name` to save the last response.

---

### Pipeline
```
Input = input()
use = embed(Similaritize(tokenize(Input)))
Response = respond(use)
print(Response)
```

- `tokenize()` — converts text, image, or audio to tokens
- `Similaritize()` — retrieves semantically similar training pairs
- `embed()` — TF-IDF sparse vector embedding
- `respond()` — retrieval-based response with intent routing

---

### Conditionals
```
if(Input contains help):
    print(Here is the help section)
else():
    print(I will do my best)
```

Conditions: `contains`, `==`, `!=`, `>`, `<`, `>=`, `<=`

---

### Loops and Definitions
```
def pipeline():
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)

while(yes):
    pipeline()
```

---

### Trainable Vision
```
ai.vision(live)

vision.train(elliot, ./known/elliot/)
vision.train(stranger, ./known/strangers/)

on.detect(elliot):
    print(Welcome home)

on.detect(stranger):
    notify.discord(Unknown person at door)
```

---

### Phone Call Lifecycle
```
ai.voice(yes)

on.connect():
    print(Thank you for calling)

on.disconnect():
    log(call ended)

on.silence(15):
    print(Are you still there?)

on.keyword(speak to human):
    ai.transfer(+441234567890)
```

---

### Server
```
out.in(1234)
out.in(1234, user=auto)
out.in(1234, user=auto, storage=./shared/)
out.in(1234, user=auto, storage=./shared/, upload=https://memory.yoursite.com)
```

API:
```
POST /input    {"input": "hello", "user": "elliot"}
GET  /health
```

Headers: `X-AIP-Key: 1234`  `X-AIP-User: username`

---

### Test UI
```
test.ui(yes)
```

Opens a local browser chat interface. Supports artifacts — code and HTML preview with download.

---

## Full Examples

### Coding assistant
```
ai.enable()
ai.model(thinking)
ai.persona("You are an expert Python developer.")
ai.memory(generative)
ai.web(yes)
artifacts.on(yes)
custom.module(./python.aimod)
test.ui(yes)

def pipeline():
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)

while(yes):
    pipeline()
```

### Home assistant (Raspberry Pi)
```
ai.enable()
ai.model(factual)
ai.name(Aria)
ai.version(1.0)
ai.creator(sintaxsaint)
ai.memory(generative)
ai.voice(yes)
ai.language(english)
ai.fallback(I am not sure about that)
ai.log(./aria.log)
out.in(9999, user=auto, storage=./shared/)

train.embed(./home.data)

def pipeline():
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)

while(yes):
    pipeline()
```

### Security research assistant
```
ai.enable()
ai.model(thinking)
ai.web(yes)
ai.memory(generative)
artifacts.on(yes)
custom.module(./kali.aipmcp)
test.ui(yes)

technique.add(recon, ./techniques/recon.txt)

def pipeline():
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)

while(yes):
    pipeline()
```

### Website chatbot
```
ai.enable()
ai.model(factual)
ai.memory(upload, https://memory.mysite.com)
ai.skills(./skills/)
ai.notify(discord, https://discord.com/api/webhooks/...)
ai.fallback(I am not sure, please contact support)
ai.log(./chat.log)
ai.persona("You are a helpful assistant for MyShop.")
out.in(9999, user=auto, storage=/mnt/shared/aiplay/)

train.embed(./knowledge.data)

def pipeline():
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)
    log(Response)

while(yes):
    pipeline()
```

---

## File Structure

```
aiplay/
  aiplay.py           CLI entry point
  lexer.py            tokeniser
  parser.py           recursive descent parser
  ast_nodes.py        AST node classes
  interpreter.py      tree-walk interpreter
  runtime.py          embedder, cosine similarity, respond(), web_search()
  format_detector.py  auto-detects training file formats
  memory_engine.py    RuleMemory + GenerativeMemory
  skills_engine.py    .skill file loader and query routing
  module_engine.py    .aimod loader
  user_memory.py      per-user session memory manager
  server.py           out.in() HTTP server
  ui_server.py        test.ui() browser chat interface with artifact support
  intent_engine.py    intent analysis and modality routing
  voice_engine.py     STT + TTS
  video_engine.py     text-to-video
  notify_engine.py    email, SMS, webhook, Discord
  vision_trainer.py   trainable detection, live vision loop
  ai_yes.py           HuggingFace model finder with licence checker
  call_handler.py     phone call lifecycle hooks
  admin_engine.py     shell access with permission levels
  mcp_engine.py       MCP server connector
  sandbox_engine.py   isolated code execution (venv or Docker)
  build_windows.bat   builds aip.exe then runs NSIS
  installer.nsi       NSIS installer
  install.sh          Linux one-line installer
  pyproject.toml      pip package definition
  aip.ico             file type icon
```

---

## Roadmap

- **v0.8** — Artifact system, MCP connector, sandbox engine, admin access, `output.deny()` stub ✓
- **v1.0** — Self AI multi-network ensemble, `.apicuz` multi-AI routing, `.aipmcp` MCP server modules, `ai.language()`, `technique.add()`, LLVM compiled runtime, AI5 device spec

---

## Licence

Free. No ads. No data collection. The creator accepts no responsibility for content generated by systems built with this software. All generated content is the sole responsibility of the operator and end user.

Built by sintaxsaint  
github.com/sintaxsaint  
sintaxsaint.pages.dev
