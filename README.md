# ai.play

A programming language for building AI systems. Write `.aip` files. Run them with `aip yourfile.aip`.

No build step. No config. Live-compiled — edit the file, run again, changes apply instantly.

**Version:** 0.5 (Python reference implementation)  
**Repo:** github.com/sintaxsaint/ai.play  
**Modules:** sintaxsaint.pages.dev  
**Community:** https://github.com/sintaxsaint/ai.play/issues

---

## Install (Windows)

Run `aiplay-setup.exe`. It will:
- Install to `C:\Program Files\aiplay\`
- Add `aip` to your PATH
- Register `.aip` files so you can double-click them to run
- Add right-click menu options: Run / Syntax Check / Edit

To build the installer yourself:
```
build_windows.bat
```
Requires Python 3.10+, PyInstaller, and NSIS.

---

## Quick Start

```
ai.enable()
ai.model(factual)

train.embed(./data.data)

Input = input()
use = embed(Similaritize(tokenize(Input)))
Response = respond(use)
print(Response)
```

Save as `hello.aip`. Run with `aip hello.aip`.

---

## Language Reference

### Required first line

```
ai.enable()
```

Every `.aip` file must start with this.

---

### Model

```
ai.model(factual)       # accurate, grounded responses
ai.model(fun)           # more creative responses
ai.model(thinking)      # slower, more reasoned responses
ai.model(custom, ./spec) # custom model from a spec file
```

---

### Capabilities

```
ai.web(yes)             # web search via DuckDuckGo (no API key needed)
ai.vision(normal)       # single image input
ai.vision(live)         # live webcam input
ai.diffusion(yes)       # image generation output
ai.video(yes)           # text-to-video output
ai.voice(yes)           # speech input + speech output (phone call mode)
ai.persona("text")      # system prompt / personality
```

---

### Memory

```
ai.memory(rule)         # pattern-matched memory, persists to JSON
ai.memory(generative)   # Generative Memory architecture — concepts extracted,
                        # weighted, decayed over time, evolved not appended
ai.memory(upload)       # persistent memory that survives user disconnects,
                        # designed for website deployments
```

Generative Memory is based on the architecture published at  
`github.com/sintaxsaint/generative-AI-memory`

---

### Skills

```
ai.skills(./skills/)
```

Loads a folder of `.skill` files. The AI auto-selects the right skill per query.

`.skill` file format:
```
name: Customer Support
keywords: help, problem, issue, broken, refund, complaint
tone: friendly and patient
priority: 10
---
how do I return an item:Submit a return request within 30 days via the returns page
what are your opening hours:We are open Monday to Friday, 9am to 5pm
```

---

### Custom Modules

```
custom.module(python)                         # loads from system modules dir
custom.module(./mymodules/stripe.aimod)       # loads from explicit path
custom.module(javascript)
custom.module(myapi)
```

Stack as many as you want. Each module adds specialised knowledge to the responder. The intent engine picks the right module per query automatically.

To create a blank module template:
```
make.module(javascript)
```
This generates `javascript.aimod` in the current directory. Fill in the pairs and drop it in your system modules folder.

**System modules directory:**
- Windows: `C:\Program Files\aiplay\modules\`
- Linux / Mac: `~/.aiplay/modules/`

**Module not found?** Find and share modules at:
- https://sintaxsaint.pages.dev
- https://github.com/sintaxsaint/ai.play/issues

`.aimod` file format:
```
name: Python
version: 1.0
type: language
trigger: python, write code, function, script, def, class
output: code
description: Teaches the AI to write and explain Python code
---
Training.data(pairs):
how do I write a for loop in python:for i in range(10): print(i)
what is a list comprehension:[x for x in items if condition]
```

---

### Training Data

```
train.embed(./data.data)
```

Auto-detects format. Supported: ai.play native pairs, OpenAI JSONL, JSON pairs, CSV, PDF, DOCX, plain text, code files.

Native format:
```
Training.data(pairs):
question:answer
what is gravity:The force that attracts objects toward each other
```

---

### Pipeline

```
Input = input()
use = embed(Similaritize(tokenize(Input)))
Response = respond(use)
print(Response)
```

- `tokenize()` — converts text, image, or audio to tokens automatically
- `Similaritize()` — retrieves the original prompt plus semantically similar training pairs from all enabled sources (training data, web, memory, skills, modules, live camera)
- `embed()` — TF-IDF sparse vector embedding
- `respond()` — retrieval-based response; intent engine decides which modalities to activate

---

### Loops and Definitions

```
while(yes):
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)
```

```
def myPipeline():
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)

while(yes):
    myPipeline()
```

---

### Server

```
out.in(1234)
out.in(1234, user=auto)
out.in(1234, user=auto, storage=./shared/)
out.in(1234, user=auto, storage=./shared/, upload=https://memory.yoursite.com)
```

Starts an HTTP server on port 7731. The number is the API key.

**User persistence** — the website passes a username in the request. The AI looks up that user's memory in the storage directory. If found, it loads it. If not, it creates a new memory for that user. On disconnect, memory is saved locally and optionally uploaded to the remote URL.

**Shared storage** — point multiple AI instances at the same `storage=` directory (NFS mount, network share, etc). All instances share user memories. Data centre ready.

API endpoints:
```
POST /input          — send a message, get a response
  Headers: X-AIP-Key: 1234
           X-AIP-User: username   (optional)
  Body:    {"input": "hello", "user": "elliot"}

POST /disconnect     — signal user disconnect, triggers memory save + upload
POST /users          — list all known users in storage
GET  /health         — status check
```

Tunnel fallback chain (tried in order):
1. Direct port forward (best performance)
2. Cloudflare Tunnel
3. ngrok
4. bore.pub
5. localhost.run

---

### Test UI

```
test.ui(yes)
```

Opens a local browser chat interface for testing. Dark, modern. No external dependencies.

---

## Full Example — Website Deployment

```
ai.enable()
ai.model(factual)
ai.memory(upload, https://memory.mysite.com)
ai.skills(./skills/)
ai.persona("You are a helpful assistant for MyShop.")
custom.module(customer_support)
custom.module(returns_policy)
out.in(9999, user=auto, storage=/mnt/shared/aiplay/)

train.embed(./knowledge.data)

def pipeline():
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)

while(yes):
    pipeline()
```

Ten machines running this same `.aip` file, all pointing at `/mnt/shared/aiplay/` — any user connects to any machine and their memory follows them.

---

## Full Example — Local Dev Tool

```
ai.enable()
ai.model(thinking)
ai.memory(generative)
custom.module(python)
custom.module(javascript)
custom.module(git)
test.ui(yes)

train.embed(./my_codebase_docs.data)

while(yes):
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)
```

---

## File Structure

```
aiplay/
  aiplay.py           entry point — CLI, live-compile loop
  lexer.py            tokeniser
  parser.py           recursive descent parser → AST
  ast_nodes.py        AST node classes
  interpreter.py      tree-walk interpreter
  runtime.py          embedder, cosine similarity, respond(), web_search()
  format_detector.py  auto-detects training file formats
  memory_engine.py    RuleMemory + GenerativeMemory
  skills_engine.py    .skill file loader and query routing
  module_engine.py    .aimod file loader, make.module() template generator
  user_memory.py      per-user session memory manager
  server.py           out.in() HTTP server + tunnel fallback chain
  ui_server.py        test.ui() browser chat interface
  intent_engine.py    intent analysis and modality routing
  voice_engine.py     STT (faster-whisper → SpeechRecognition → fallback)
                      TTS (pyttsx3 → espeak → SAPI → say)
  video_engine.py     text-to-video (ModelScope → Zeroscope → AnimateDiff → stub)
  build_windows.bat   builds aip.exe via PyInstaller then runs NSIS
  installer.nsi       NSIS installer script
  aip.ico             file type icon
```

---

## Roadmap

- **ai.play fast** — LLVM/native compiled interpreter. Same `.aip` files, zero syntax changes, full CPU+GPU speed. Planned after the Python reference implementation is complete and stable. The Python version is the spec.
- **Module registry** — browse and submit modules at sintaxsaint.pages.dev
- **GitHub Actions** — auto-deploy workflow

---

## Licence

Free. No ads. No data collection.  
Built by sintaxsaint — github.com/sintaxsaint
