# ai.play

A programming language for building AI systems. Write `.aip` files. Run them with `aip yourfile.aip`.

No build step. No config. Live-compiled — edit the file, run again, changes apply instantly.

**Version:** 0.6  
**Repo:** github.com/sintaxsaint/ai.play  
**Modules:** sintaxsaint.pages.dev  
**Community:** https://github.com/sintaxsaint/ai.play/issues

---

## Install (Windows)

Run `aiplay-setup.exe`. Installs to `C:\Program Files\aiplay\`, adds `aip` to PATH, registers `.aip` file associations.

To build the installer yourself: run `build_windows.bat` (requires Python 3.10+, PyInstaller, NSIS).

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
ai.persona("You are a helpful assistant.")
```

---

### Memory
```
ai.memory(rule)
ai.memory(generative)
ai.memory(upload)
ai.memory(upload, https://memory.yoursite.com)
```

---

### ai.yes — one-line AI clone
Finds the best open-licence equivalent on HuggingFace, checks licence (MIT/Apache 2.0 only), downloads weights, auto-configures capabilities.

```
ai.yes(chatgpt)
ai.yes(claude)
ai.yes(copilot)
ai.yes(gemini)
ai.yes(sora)
ai.yes(midjourney)
ai.yes(whisper)
ai.yes(elevenlabs)
```

Full local ChatGPT equivalent:
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
custom.module(javascript)
```

Create a blank template:
```
make.module(javascript)
```

System modules directory:
- Windows: `C:\Program Files\aiplay\modules\`
- Linux/Mac: `~/.aiplay/modules/`

Find and share modules:
- https://sintaxsaint.pages.dev
- https://github.com/sintaxsaint/ai.play/issues

`.aimod` format:
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

Auto-detects: ai.play native pairs, OpenAI JSONL, JSON, CSV, PDF, DOCX, plain text, code files.

Native format:
```
Training.data(pairs):
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

- `tokenize()` — converts text, image, or audio to tokens
- `Similaritize()` — retrieves semantically similar training pairs from all enabled sources
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

Supported conditions:
- `Input contains "word"`
- `Variable == "value"`
- `Variable != "value"`
- `count > 5`  `count < 10`  `count >= 3`

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

### Error Handling
```
ai.fallback(Sorry, I do not know the answer to that)
```

When `respond()` has no good answer, returns the fallback message instead.

---

### Logging
```
ai.log(./output.log)

while(yes):
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)
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

Then inside event hooks:
```
on.detect(stranger):
    notify.discord(Unknown person detected)
    notify.email(Intruder alert)
    notify.sms(Check camera)
```

Email uses env vars: `AIPLAY_SMTP_HOST`, `AIPLAY_SMTP_USER`, `AIPLAY_SMTP_PASS`, `AIPLAY_SMTP_FROM`.  
SMS uses `AIPLAY_SMS_GATEWAY` (any HTTP SMS provider URL).

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

Built-in labels without training: `motion`, `face`, `person`.

Requires `pip install opencv-python` for real detection. Runs in stub mode otherwise.

---

### Phone Call Lifecycle
```
ai.voice(yes)

on.connect():
    print(Thank you for calling, how can I help?)

on.disconnect():
    print(Goodbye)
    log(session)

on.silence(10):
    print(Are you still there?)

on.keyword(speak to human):
    print(Transferring you now)
    ai.transfer(+441234567890)

while(yes):
    myPipeline()
```

---

### Output Control
```
output.deny(large_numbers)
output.deny(code)
output.deny(explicit)
```

Lets deployers restrict certain output types. Useful for child-safe deployments, corporate restrictions, or matching the limits of a specific product.

---

### Server
```
out.in(1234)
out.in(1234, user=auto)
out.in(1234, user=auto, storage=./shared/)
out.in(1234, user=auto, storage=./shared/, upload=https://memory.yoursite.com)
```

API endpoints:
```
POST /input        — {"input": "hello", "user": "elliot"}
POST /disconnect   — signal user disconnect
GET  /users        — list all known users
GET  /health       — status check
```

Headers: `X-AIP-Key: 1234`  `X-AIP-User: username`

Tunnel fallback: Cloudflare Tunnel → ngrok → bore.pub → localhost.run

---

### Test UI
```
test.ui(yes)
```

Opens a local browser chat interface.

---

## Full Examples

### Website deployment
```
ai.enable()
ai.model(factual)
ai.memory(upload, https://memory.mysite.com)
ai.skills(./skills/)
ai.notify(email, admin@mysite.com)
ai.notify(discord, https://discord.com/api/webhooks/...)
ai.fallback(I am not sure about that, please contact support)
ai.log(./logs/chat.log)
ai.persona("You are a helpful assistant for MyShop.")
custom.module(customer_support)
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

### Security camera
```
ai.enable()
ai.model(factual)
ai.vision(live)
ai.notify(email, elliot@example.com)
ai.notify(discord, https://discord.com/api/webhooks/...)
ai.log(./security.log)

vision.train(elliot, ./known/elliot/)
vision.train(car, ./known/mycar/)

on.detect(elliot):
    print(Welcome home)

on.detect(motion):
    notify.discord(Motion detected)
    log(motion)

on.detect(stranger):
    notify.email(Unknown person detected)
    notify.discord(Intruder alert)
    log(intruder)
```

### Phone assistant
```
ai.enable()
ai.model(factual)
ai.voice(yes)
ai.memory(generative)
ai.log(./calls.log)
custom.module(customer_support)

train.embed(./faq.data)

on.connect():
    print(Thank you for calling, how can I help you today?)

on.disconnect():
    log(call ended)

on.silence(15):
    print(Are you still there?)

on.keyword(speak to human):
    print(Connecting you to a team member now)
    ai.transfer(+441234567890)

def pipeline():
    Input = input()
    use = embed(Similaritize(tokenize(Input)))
    Response = respond(use)
    print(Response)

while(yes):
    pipeline()
```

### Local dev tool
```
ai.enable()
ai.yes(chatgpt)
ai.memory(generative)
ai.log(./dev.log)
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
  aiplay.py           CLI entry point, live-compile loop
  lexer.py            tokeniser
  parser.py           recursive descent parser
  ast_nodes.py        AST node classes
  interpreter.py      tree-walk interpreter
  runtime.py          embedder, cosine similarity, respond(), web_search()
  format_detector.py  auto-detects training file formats
  memory_engine.py    RuleMemory + GenerativeMemory
  skills_engine.py    .skill file loader and query routing
  module_engine.py    .aimod loader, make.module() template generator
  user_memory.py      per-user session memory manager
  server.py           out.in() HTTP server + tunnel fallback chain
  ui_server.py        test.ui() browser chat interface
  intent_engine.py    intent analysis and modality routing
  voice_engine.py     STT + TTS with fallback chains
  video_engine.py     text-to-video with fallback chain
  notify_engine.py    email, SMS, webhook, Discord notifications
  vision_trainer.py   trainable object/face detection, live vision loop
  ai_yes.py           HuggingFace model finder with licence checker
  call_handler.py     phone call lifecycle event hooks
  build_windows.bat   builds aip.exe then runs NSIS
  installer.nsi       NSIS installer script
  aip.ico             file type icon
```

---

## Roadmap

- **v0.7** — `pip install aiplay`, Google Colab support, `aiplay.run()` Python API
- **ai.play fast** — LLVM/native compiled interpreter, same `.aip` files, full speed

---

## Licence

Free. No ads. No data collection.  
Built by sintaxsaint — github.com/sintaxsaint  
Modules: sintaxsaint.pages.dev  
Community: https://github.com/sintaxsaint/ai.play/issues
