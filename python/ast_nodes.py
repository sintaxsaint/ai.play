"""
AST node definitions for ai.play
"""

class Node:
    pass

# --- Top level ---
class Program(Node):
    def __init__(self, stmts):
        self.stmts = stmts

# --- Statements ---
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

class TrainEmbed(Node):
    """train.embed(path)"""
    def __init__(self, path):
        self.path = path

class TestUI(Node):
    """test.ui(yes/no)"""
    def __init__(self, value):
        self.value = value

class AISkills(Node):
    """ai.skills(path)"""
    def __init__(self, path):
        self.path = path

class OutIn(Node):
    """out.in(key, user=auto, storage=./path/, upload=https://url)"""
    def __init__(self, key, user=None, storage=None, upload=None):
        self.key     = key
        self.user    = user      # None | 'auto' | username string
        self.storage = storage   # shared storage directory
        self.upload  = upload    # remote URL for memory upload

class Assign(Node):
    """name = expr"""
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

class Print(Node):
    """print(expr)"""
    def __init__(self, expr):
        self.expr = expr

class WhileLoop(Node):
    """while(yes): body"""
    def __init__(self, body):
        self.body = body

class DefBlock(Node):
    """def name(): body"""
    def __init__(self, name, body):
        self.name = name
        self.body = body

class CustomModule(Node):
    """custom.module(name_or_path)"""
    def __init__(self, name):
        self.name = name

class MakeModule(Node):
    """make.module(name) — creates a blank .aimod template"""
    def __init__(self, name):
        self.name = name

class CallDef(Node):
    """name()  — call a user-defined def block"""
    def __init__(self, name):
        self.name = name

# --- Expressions ---
class InputExpr(Node):
    """input()"""
    pass

class EmbedExpr(Node):
    def __init__(self, expr):
        self.expr = expr

class TokenizeExpr(Node):
    def __init__(self, expr):
        self.expr = expr

class SimilarizeExpr(Node):
    def __init__(self, expr):
        self.expr = expr

class RespondExpr(Node):
    def __init__(self, expr):
        self.expr = expr

class VarRef(Node):
    def __init__(self, name):
        self.name = name

class StringLit(Node):
    def __init__(self, value):
        self.value = value

class NumberLit(Node):
    def __init__(self, value):
        self.value = value

class PathLit(Node):
    def __init__(self, value):
        self.value = value
