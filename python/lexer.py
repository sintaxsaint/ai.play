"""
ai.play lexer v0.6 — clean rewrite
Handles: keywords, identifiers, paths, emails, URLs, numbers, strings.
Dot is always punctuation except inside paths (./  ../)
Equals inside bare values (user=auto) is kept as one token for named params.
"""
from enum import Enum, auto

class TT(Enum):
    STRING    = auto()
    NUMBER    = auto()
    IDENT     = auto()
    PATH      = auto()
    BOOL      = auto()
    NAMEDPARAM= auto()   # user=auto  storage=./path
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
    ON        = auto()
    VISION_KW = auto()
    NOTIFY_KW = auto()
    LOG_KW    = auto()
    IF        = auto()
    ELSE      = auto()
    TRANSFER  = auto()

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
    'on':           TT.ON,
    'vision':       TT.VISION_KW,
    'notify':       TT.NOTIFY_KW,
    'log':          TT.LOG_KW,
    'if':           TT.IF,
    'else':         TT.ELSE,
    'transfer':     TT.TRANSFER,
    'yes':          TT.BOOL,
    'no':           TT.BOOL,
}

class Token:
    def __init__(self, type, value, line):
        self.type  = type
        self.value = value
        self.line  = line
    def __repr__(self):
        return f'Token({self.type.name}, {self.value!r})'

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
        ch = self.src[self.pos]; self.pos += 1
        if ch == '\n': self.line += 1
        return ch

    def skip_ws(self):
        while self.pos < len(self.src) and self.src[self.pos] in ' \t\r':
            self.pos += 1

    def skip_comment(self):
        while self.pos < len(self.src) and self.src[self.pos] != '\n':
            self.pos += 1

    def read_quoted(self):
        q = self.advance()
        buf = []
        while self.pos < len(self.src) and self.src[self.pos] != q:
            if self.src[self.pos] == '\\':
                self.advance()
                esc = self.advance()
                buf.append({'n':'\n','t':'\t','r':'\r'}.get(esc, esc))
            else:
                buf.append(self.advance())
        if self.pos >= len(self.src):
            raise LexError(f"Unterminated string at line {self.line}")
        self.advance()
        return ''.join(buf)

    def read_word(self):
        """Read alphanumeric + underscore — no dots, no special chars."""
        buf = []
        while self.pos < len(self.src) and (self.src[self.pos].isalnum() or self.src[self.pos] == '_'):
            buf.append(self.advance())
        return ''.join(buf)

    def read_value_token(self):
        """
        Read a bare value that stops at ( ) , whitespace newline.
        Handles: paths ./foo  emails x@y.com  URLs https://...  numbers  plain words.
        Does NOT include = so named params like user=auto are read whole then split.
        """
        buf = []
        STOP = set(' \t\r\n(),')
        while self.pos < len(self.src) and self.src[self.pos] not in STOP:
            # Stop at # (comment)
            if self.src[self.pos] == '#':
                break
            # Stop at : only if NOT part of a URL (i.e. not followed by //)
            if self.src[self.pos] == ':':
                if self.peek(1) == '/' and self.peek(2) == '/':
                    buf.append(self.advance())  # include : for URL
                else:
                    break
            else:
                buf.append(self.advance())
        return ''.join(buf)

    def emit_word(self, word):
        """Classify a plain word (no dots, no special) and emit the right token."""
        if word == 'yes':
            self.tokens.append(Token(TT.BOOL, True, self.line))
        elif word == 'no':
            self.tokens.append(Token(TT.BOOL, False, self.line))
        elif word in KEYWORDS:
            self.tokens.append(Token(KEYWORDS[word], word, self.line))
        else:
            # try int
            try:
                self.tokens.append(Token(TT.NUMBER, int(word), self.line)); return
            except Exception: pass
            # try float
            try:
                self.tokens.append(Token(TT.NUMBER, float(word), self.line)); return
            except Exception: pass
            self.tokens.append(Token(TT.IDENT, word, self.line))

    def tokenize(self):
        src = self.src
        while self.pos < len(src):
            self.skip_ws()
            if self.pos >= len(src): break
            ch = src[self.pos]

            # Comment
            if ch == '#': self.skip_comment(); continue

            # Newline
            if ch == '\n':
                self.advance()
                self.tokens.append(Token(TT.NEWLINE, '\n', self.line))
                continue

            # Quoted string
            if ch in ('"', "'"):
                s = self.read_quoted()
                self.tokens.append(Token(TT.STRING, s, self.line))
                continue

            # Single-char punctuation — always their own token
            if ch == '(': self.tokens.append(Token(TT.LPAREN,'(',self.line)); self.advance(); continue
            if ch == ')': self.tokens.append(Token(TT.RPAREN,')',self.line)); self.advance(); continue
            if ch == ',': self.tokens.append(Token(TT.COMMA, ',',self.line)); self.advance(); continue
            if ch == ':': self.tokens.append(Token(TT.COLON, ':',self.line)); self.advance(); continue

            # Equals — standalone unless part of named param (word=value)
            # We handle named params by reading the whole value token and splitting on =
            if ch == '=':
                self.tokens.append(Token(TT.EQUALS,'=',self.line)); self.advance(); continue

            # Dot — always DOT punctuation unless starting a path (./ or ../)
            if ch == '.':
                next1 = self.peek(1)
                if next1 in ('/', '\\') or (next1 == '.' and self.peek(2) in ('/', '\\')):
                    # It's a path — read as value token
                    val = self.read_value_token()
                    self.tokens.append(Token(TT.PATH, val, self.line))
                else:
                    self.tokens.append(Token(TT.DOT, '.', self.line))
                    self.advance()
                continue

            # Paths starting with / ~ or drive letter C:
            if ch == '/' or ch == '~':
                val = self.read_value_token()
                self.tokens.append(Token(TT.PATH, val, self.line))
                continue
            if ch.isalpha() and self.peek(1) == ':' and self.peek(2) in ('/', '\\'):
                val = self.read_value_token()
                self.tokens.append(Token(TT.PATH, val, self.line))
                continue

            # Number starting with digit or -digit
            if ch.isdigit() or (ch == '-' and self.peek(1).isdigit()):
                val = self.read_value_token()
                try:
                    n = float(val) if '.' in val else int(val)
                    self.tokens.append(Token(TT.NUMBER, n, self.line))
                except Exception:
                    self.tokens.append(Token(TT.IDENT, val, self.line))
                continue

            # Word starting with + (phone numbers like +44...)
            if ch == '+':
                val = self.read_value_token()
                self.tokens.append(Token(TT.STRING, val, self.line))
                continue

            # Alpha/underscore — read full word, then check for dot chains
            if ch.isalpha() or ch == '_':
                word = self.read_word()

                # Check if followed by . (like ai.model, on.detect, notify.email)
                # Emit the keyword/ident, then let the loop handle the dot next iteration
                self.emit_word(word)

                # But first check: is what follows = (named param like user=auto)?
                # If so, read the = and value as well
                if self.pos < len(src) and src[self.pos] == '=':
                    # Check there's no space — user=auto not user = auto
                    self.advance()  # consume =
                    val = self.read_value_token()
                    # Replace the last ident token with a NAMEDPARAM token
                    last = self.tokens.pop()
                    self.tokens.append(Token(TT.NAMEDPARAM, (str(last.value), val), self.line))
                continue

            # Bare value containing special chars (email, URL etc) — read until delimiter
            val = self.read_value_token()
            if val:
                if '@' in val:
                    self.tokens.append(Token(TT.STRING, val, self.line))
                elif '://' in val:
                    self.tokens.append(Token(TT.STRING, val, self.line))
                else:
                    self.tokens.append(Token(TT.IDENT, val, self.line))
            else:
                self.advance()  # skip unknown single char

        self.tokens.append(Token(TT.EOF, None, self.line))
        return self.tokens
