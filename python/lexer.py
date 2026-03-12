import re
from enum import Enum, auto

class TT(Enum):
    STRING    = auto()
    NUMBER    = auto()
    IDENT     = auto()
    PATH      = auto()
    BOOL      = auto()
    LPAREN    = auto()
    RPAREN    = auto()
    EQUALS    = auto()
    DOT       = auto()
    COMMA     = auto()
    COLON     = auto()
    NEWLINE   = auto()
    EOF       = auto()
    # Keywords
    AI        = auto()
    TRAIN     = auto()
    TEST      = auto()
    OUT       = auto()
    IN        = auto()
    PRINT     = auto()
    INPUT     = auto()
    EMBED     = auto()
    TOKENIZE  = auto()
    SIMILARIZE= auto()
    RESPOND   = auto()
    MODEL     = auto()
    WHILE     = auto()
    DEF       = auto()
    CUSTOM    = auto()
    MAKE      = auto()

KEYWORDS = {
    'ai':           TT.AI,
    'train':        TT.TRAIN,
    'test':         TT.TEST,
    'out':          TT.OUT,
    'in':           TT.IN,
    'print':        TT.PRINT,
    'input':        TT.INPUT,
    'embed':        TT.EMBED,
    'tokenize':     TT.TOKENIZE,
    'Similaritize': TT.SIMILARIZE,
    'respond':      TT.RESPOND,
    'model':        TT.MODEL,
    'while':        TT.WHILE,
    'def':          TT.DEF,
    'custom':       TT.CUSTOM,
    'make':         TT.MAKE,
    'yes':          TT.BOOL,
    'no':           TT.BOOL,
}

class Token:
    def __init__(self, type, value, line):
        self.type  = type
        self.value = value
        self.line  = line
    def __repr__(self):
        return f'Token({self.type}, {self.value!r}, line={self.line})'

class LexError(Exception):
    pass

class Lexer:
    def __init__(self, source):
        self.src    = source
        self.pos    = 0
        self.line   = 1
        self.tokens = []

    def peek(self, offset=0):
        p = self.pos + offset
        return self.src[p] if p < len(self.src) else '\0'

    def advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
        return ch

    def skip_whitespace(self):
        while self.pos < len(self.src) and self.src[self.pos] in ' \t\r':
            self.pos += 1

    def skip_comment(self):
        while self.pos < len(self.src) and self.src[self.pos] != '\n':
            self.pos += 1

    def read_string(self):
        quote = self.advance()
        buf = []
        while self.pos < len(self.src) and self.src[self.pos] != quote:
            buf.append(self.advance())
        if self.pos >= len(self.src):
            raise LexError(f"Unterminated string at line {self.line}")
        self.advance()
        return ''.join(buf)

    def read_path(self):
        buf = []
        while self.pos < len(self.src) and self.src[self.pos] not in ' \t\r\n,)':
            buf.append(self.advance())
        return ''.join(buf)

    def read_number(self):
        buf = []
        while self.pos < len(self.src) and (self.src[self.pos].isdigit() or self.src[self.pos] == '.'):
            buf.append(self.advance())
        s = ''.join(buf)
        return float(s) if '.' in s else int(s)

    def read_ident(self):
        buf = []
        while self.pos < len(self.src) and (self.src[self.pos].isalnum() or self.src[self.pos] in '_'):
            buf.append(self.advance())
        return ''.join(buf)

    def tokenize(self):
        while self.pos < len(self.src):
            self.skip_whitespace()
            if self.pos >= len(self.src):
                break
            ch = self.src[self.pos]

            if ch == '#':
                self.skip_comment()
                continue
            if ch == '\n':
                self.advance()
                self.tokens.append(Token(TT.NEWLINE, '\n', self.line))
                continue
            if ch in ('"', "'"):
                s = self.read_string()
                self.tokens.append(Token(TT.STRING, s, self.line))
                continue
            if ch == '.' and self.peek(1) == '/':
                p = self.read_path()
                self.tokens.append(Token(TT.PATH, p, self.line))
                continue
            if ch in ('/', '~'):
                p = self.read_path()
                self.tokens.append(Token(TT.PATH, p, self.line))
                continue
            if ch.isdigit():
                n = self.read_number()
                self.tokens.append(Token(TT.NUMBER, n, self.line))
                continue
            if ch.isalpha() or ch == '_':
                word = self.read_ident()
                tt  = KEYWORDS.get(word, TT.IDENT)
                val = True if word == 'yes' else (False if word == 'no' else word)
                self.tokens.append(Token(tt, val, self.line))
                continue
            simple = {'(': TT.LPAREN, ')': TT.RPAREN, '=': TT.EQUALS,
                      '.': TT.DOT, ',': TT.COMMA, ':': TT.COLON}
            if ch in simple:
                self.tokens.append(Token(simple[ch], ch, self.line))
                self.advance()
                continue
            raise LexError(f"Unknown character {ch!r} at line {self.line}")
        self.tokens.append(Token(TT.EOF, None, self.line))
        return self.tokens
