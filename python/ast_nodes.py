"""
AST node definitions for ai.play
"""

class Node:
    pass

# ─── nodes ────────────────────────────────────────────────

class AIEnable(Node):
    """ai.enable()"""
    pass

class AIModel(Node):
    """ai.model(name) or ai.model(custom, path)"""
    def __init__(self, name, path=None):
        self.name = name
        self.path = path

class AICapability(Node):
    """ai.web/memory/vision/diffusion/video/voice(value)"""
    def __init__(self, cap, value):
        self.cap   = cap
        self.value = value

class AIPersona(Node):
    """ai.persona("system prompt text")"""
    def __init__(self, text):
        self.text = text

class AISkills(Node):
    """ai.skills(path)"""
    def __init__(self, path):
        self.path = path

class OutIn(Node):
    """out.in(key, user=auto, storage=./path/, upload=https://url)"""
    def __init__(self, key, user=None, storage=None, upload=None):
        self.key     = key
        self.user    = user
        self.storage = storage
        self.upload  = upload

class CustomModule(Node):
    """custom.module(name_or_path)"""
    def __init__(self, name):
        self.name = name

class MakeModule(Node):
    """make.module(name)"""
    def __init__(self, name):
        self.name = name

class AINotify(Node):
    """ai.notify(channel, target)"""
    def __init__(self, channel, target):
        self.channel = channel
        self.target  = target

class AIYesNode(Node):
    """ai.yes(target)"""
    def __init__(self, target):
        self.target = target

class VisionTrain(Node):
    """vision.train(label, path)"""
    def __init__(self, label, path):
        self.label = label
        self.path  = path

class OnEvent(Node):
    """on.connect() / on.disconnect() / on.silence(N) / on.keyword(word) / on.detect(label)"""
    def __init__(self, event, param, body):
        self.event = event   # connect | disconnect | silence | keyword | detect
        self.param = param   # seconds for silence, word for keyword, label for detect
        self.body  = body    # list of statements

class IfStmt(Node):
    """if(condition): body"""
    def __init__(self, condition, body, else_body=None):
        self.condition = condition
        self.body      = body
        self.else_body = else_body or []

class AIFallback(Node):
    """ai.fallback(message)"""
    def __init__(self, message):
        self.message = message

class AILog(Node):
    """ai.log(path)"""
    def __init__(self, path):
        self.path = path

class LogCall(Node):
    """log(value)"""
    def __init__(self, value):
        self.value = value

class NotifyCall(Node):
    """notify.email(...) / notify.sms(...) / notify.discord(...) / notify.webhook(...)"""
    def __init__(self, channel, message, attachment=None):
        self.channel    = channel
        self.message    = message
        self.attachment = attachment

class TransferCall(Node):
    """ai.transfer(number)"""
    def __init__(self, number):
        self.number = number

class AIMemory(Node):
    """ai.memory(mode[, url])"""
    def __init__(self, mode, url=None):
        self.mode = mode
        self.url  = url

class TrainEmbed(Node):
    """train.embed(path)"""
    def __init__(self, path):
        self.path = path

class TestUI(Node):
    """test.ui(yes)"""
    def __init__(self, val):
        self.val = val

class WhileLoop(Node):
    """while(condition): body"""
    def __init__(self, condition, body):
        self.condition = condition
        self.body      = body

class DefBlock(Node):
    """def name(): body"""
    def __init__(self, name, body):
        self.name = name
        self.body = body

class CallDef(Node):
    """name()"""
    def __init__(self, name):
        self.name = name

class Assign(Node):
    """Name = expr"""
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

class PrintStmt(Node):
    """print(val)"""
    def __init__(self, val):
        self.val = val

class InputExpr(Node):
    """input()"""
    pass

class EmbedExpr(Node):
    def __init__(self, inner): self.inner = inner

class TokenizeExpr(Node):
    def __init__(self, inner): self.inner = inner

class SimilarizeExpr(Node):
    def __init__(self, inner): self.inner = inner

class RespondExpr(Node):
    def __init__(self, inner): self.inner = inner

class Literal(Node):
    def __init__(self, value): self.value = value

class Program(Node):
    def __init__(self, stmts): self.stmts = stmts

class AIName(Node):
    """ai.name(text)"""
    def __init__(self, name): self.name = name

class AIVersion(Node):
    """ai.version(text)"""
    def __init__(self, version): self.version = version

class AICreator(Node):
    """ai.creator(text)"""
    def __init__(self, creator): self.creator = creator

class AITrain(Node):
    """ai.train(url) — download and embed training data from URL"""
    def __init__(self, url): self.url = url

class AILanguage(Node):
    """ai.language(lang) — set response language, default english"""
    def __init__(self, lang): self.lang = lang

class AISchedule(Node):
    """ai.schedule(interval, event) — run on schedule"""
    def __init__(self, interval, event): self.interval = interval; self.event = event

class AIEncrypt(Node):
    """ai.encrypt(yes/no) — encrypt memory/storage at rest"""
    def __init__(self, val): self.val = val

class AILanguage(Node):
    """ai.language(english)"""
    def __init__(self, lang): self.lang = lang

class AISchedule(Node):
    """ai.schedule(interval, ./script.aip) or ai.schedule(09:00, ./morning.aip)"""
    def __init__(self, when, path): self.when = when; self.path = path

class AIEncrypt(Node):
    """ai.encrypt(yes/key)"""
    def __init__(self, key): self.key = key

class TechniqueAdd(Node):
    """technique.add(name, path_or_text)"""
    def __init__(self, name, source): self.name = name; self.source = source

class ArtifactsOn(Node):
    """artifacts.on(yes)"""
    def __init__(self, val): self.val = val

class AIMcp(Node):
    """ai.mcp(url)"""
    def __init__(self, url): self.url = url

class SandboxStart(Node):
    """sandbox.start(venv/docker)"""
    def __init__(self, mode): self.mode = mode

class SandboxRun(Node):
    """sandbox.run(command)"""
    def __init__(self, command): self.command = command

class SandboxInstall(Node):
    """sandbox.install(package)"""
    def __init__(self, package): self.package = package

class AIAdmin(Node):
    """ai.admin(ask/destructive/full)"""
    def __init__(self, mode): self.mode = mode

class OutputDeny(Node):
    """output.deny() — suppress AI output (enforcement in v1)"""
    pass

# ── compatibility aliases ─────────────────────────────────────────────────────
# The interpreter uses these old names — keep them pointing at the new classes

Print     = PrintStmt

class VarRef(Node):
    def __init__(self, name): self.name = name

class StringLit(Node):
    def __init__(self, value): self.value = value

class NumberLit(Node):
    def __init__(self, value): self.value = value

class PathLit(Node):
    def __init__(self, value): self.value = value
