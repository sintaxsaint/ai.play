from lexer import TT, Token
from ast_nodes import *

class ParseError(Exception):
    pass

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos    = 0

    def peek(self, offset=0):
        return self.tokens[self.pos + offset]

    def advance(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, tt):
        t = self.advance()
        if t.type != tt:
            raise ParseError(f"Expected {tt} but got {t.type} ({t.value!r}) at line {t.line}")
        return t

    def skip_newlines(self):
        while self.peek().type == TT.NEWLINE:
            self.advance()

    def parse(self):
        stmts = []
        self.skip_newlines()
        while self.peek().type != TT.EOF:
            s = self.parse_stmt()
            if s is not None:
                stmts.append(s)
            self.skip_newlines()
        return Program(stmts)

    def parse_block(self):
        """Parse indented block — stmts until we hit a top-level keyword or EOF."""
        stmts = []
        self.skip_newlines()
        while self.peek().type not in (TT.EOF,):
            try:
                s = self.parse_stmt()
                stmts.append(s)
                self.skip_newlines()
            except ParseError:
                break
        return stmts

    def parse_indented_block(self):
        """
        Parse a def or while body. Lines must be indented (start with spaces/tab).
        Ends when we see a non-indented line or EOF.
        """
        stmts = []
        while True:
            # Peek at next meaningful token — if it's at column 0 it's outside the block
            # Since we don't track indentation in the token stream, we use a simpler rule:
            # block ends at EOF or when we see a top-level keyword (def, while, ai, train, out, test)
            # at the start of a line (no preceding NEWLINE consumed yet)
            self.skip_newlines()
            t = self.peek()
            if t.type == TT.EOF:
                break
            if t.type in (TT.DEF, TT.AI, TT.TRAIN, TT.OUT, TT.TEST):
                break
            # Check if next token after newlines looks like a top-level statement
            # For simplicity: collect until we can't parse a stmt
            try:
                s = self.parse_stmt()
                stmts.append(s)
            except ParseError:
                break
        return stmts

    def parse_stmt(self):
        t = self.peek()

        # def name(): body
        if t.type == TT.DEF:
            return self.parse_def()

        # ai.xxx(...)
        if t.type == TT.AI:
            return self.parse_ai_stmt()

        # train.embed(...)
        if t.type == TT.TRAIN:
            return self.parse_train_stmt()

        # test.ui(...)
        if t.type == TT.TEST:
            return self.parse_test_stmt()

        # out.in(...)
        if t.type == TT.OUT:
            return self.parse_out_stmt()

        # print(...)
        if t.type == TT.PRINT:
            self.advance()
            self.expect(TT.LPAREN)
            expr = self.parse_expr()
            self.expect(TT.RPAREN)
            return Print(expr)

        # while(yes):
        if t.type == TT.WHILE:
            self.advance()
            self.expect(TT.LPAREN)
            self.advance()  # condition value
            self.expect(TT.RPAREN)
            self.expect(TT.COLON)
            body = self.parse_indented_block()
            return WhileLoop(body)

        # custom.module(name)
        if t.type == TT.CUSTOM:
            self.advance()
            self.expect(TT.DOT)
            directive = self.advance().value
            if directive == 'module':
                self.expect(TT.LPAREN)
                name_tok = self.advance()
                name = str(name_tok.value)
                self.expect(TT.RPAREN)
                return CustomModule(name)
            raise ParseError(f"Unknown custom directive: {directive!r} at line {t.line}")

        # make.module(name) — create a blank template
        if t.type == TT.MAKE:
            self.advance()
            self.expect(TT.DOT)
            directive = self.advance().value
            if directive == 'module':
                self.expect(TT.LPAREN)
                name_tok = self.advance()
                name = str(name_tok.value)
                self.expect(TT.RPAREN)
                return MakeModule(name)
            raise ParseError(f"Unknown make directive: {directive!r} at line {t.line}")

        # IDENT — assignment or def call
        if t.type == TT.IDENT:
            next_t = self.tokens[self.pos + 1]
            # Assignment: name = expr
            if next_t.type == TT.EQUALS:
                name = self.advance().value
                self.advance()  # =
                expr = self.parse_expr()
                return Assign(name, expr)
            # Def call: name()
            if next_t.type == TT.LPAREN:
                name = self.advance().value
                self.expect(TT.LPAREN)
                self.expect(TT.RPAREN)
                return CallDef(name)

        raise ParseError(f"Unexpected token {t.type} ({t.value!r}) at line {t.line}")

    def parse_def(self):
        self.expect(TT.DEF)
        name_tok = self.advance()
        name = name_tok.value
        self.expect(TT.LPAREN)
        self.expect(TT.RPAREN)
        self.expect(TT.COLON)
        body = self.parse_indented_block()
        return DefBlock(name, body)

    def parse_ai_stmt(self):
        self.expect(TT.AI)
        self.expect(TT.DOT)
        t = self.advance()

        if t.value == 'enable':
            self.expect(TT.LPAREN)
            self.expect(TT.RPAREN)
            return AIEnable()

        if t.value == 'model':
            self.expect(TT.LPAREN)
            name_tok = self.advance()
            name = name_tok.value
            path = None
            if self.peek().type == TT.COMMA:
                self.advance()
                path_tok = self.advance()
                path = path_tok.value
            self.expect(TT.RPAREN)
            return AIModel(name, path)

        if t.value == 'persona':
            self.expect(TT.LPAREN)
            text_tok = self.advance()
            text = text_tok.value
            self.expect(TT.RPAREN)
            return AIPersona(text)

        if t.value == 'skills':
            self.expect(TT.LPAREN)
            path_tok = self.advance()
            path = path_tok.value
            self.expect(TT.RPAREN)
            return AISkills(path)

        if t.value in ('web', 'memory', 'vision', 'diffusion', 'video', 'voice'):
            cap = t.value
            self.expect(TT.LPAREN)
            val_tok = self.advance()
            value = val_tok.value
            self.expect(TT.RPAREN)
            return AICapability(cap, value)

        raise ParseError(f"Unknown ai directive: {t.value!r} at line {t.line}")

    def parse_train_stmt(self):
        self.expect(TT.TRAIN)
        self.expect(TT.DOT)
        t = self.advance()
        if t.value == 'embed':
            self.expect(TT.LPAREN)
            path_tok = self.advance()
            path = path_tok.value
            self.expect(TT.RPAREN)
            return TrainEmbed(path)
        raise ParseError(f"Unknown train directive: {t.value!r} at line {t.line}")

    def parse_test_stmt(self):
        self.expect(TT.TEST)
        self.expect(TT.DOT)
        t = self.advance()
        if t.value == 'ui':
            self.expect(TT.LPAREN)
            val_tok = self.advance()
            value = val_tok.value
            self.expect(TT.RPAREN)
            return TestUI(value)
        raise ParseError(f"Unknown test directive: {t.value!r} at line {t.line}")

    def parse_out_stmt(self):
        self.expect(TT.OUT)
        self.expect(TT.DOT)
        t = self.advance()
        if t.value == 'in' or t.type == TT.IN:
            self.expect(TT.LPAREN)
            key_tok = self.advance()
            key = key_tok.value
            user = None
            storage = None
            upload = None
            # Parse named params: user=auto, storage=./path, upload=https://...
            while self.peek().type == TT.COMMA:
                self.advance()  # ,
                param_name = self.advance().value  # param name
                self.advance()  # =
                # Value can be string, ident, bool, path, or number
                val_tok = self.advance()
                param_val = val_tok.value
                # For upload= URLs: consume extra tokens until comma/rparen
                # since https://... gets split at : by the lexer
                if param_name == 'upload':
                    # Re-read raw — peek and accumulate until ) or ,
                    parts = [str(param_val)]
                    while self.peek().type not in (TT.RPAREN, TT.COMMA, TT.EOF, TT.NEWLINE):
                        parts.append(str(self.advance().value))
                    param_val = ''.join(parts)
                if param_name == 'user':
                    user = str(param_val)
                elif param_name == 'storage':
                    storage = str(param_val)
                elif param_name == 'upload':
                    upload = param_val
            self.expect(TT.RPAREN)
            return OutIn(key, user=user, storage=storage, upload=upload)
        raise ParseError(f"Unknown out directive: {t.value!r} at line {t.line}")

    def parse_expr(self):
        t = self.peek()

        if t.type == TT.INPUT:
            self.advance()
            self.expect(TT.LPAREN)
            self.expect(TT.RPAREN)
            return InputExpr()

        if t.type == TT.EMBED:
            self.advance()
            self.expect(TT.LPAREN)
            inner = self.parse_expr()
            self.expect(TT.RPAREN)
            return EmbedExpr(inner)

        if t.type == TT.TOKENIZE:
            self.advance()
            self.expect(TT.LPAREN)
            inner = self.parse_expr()
            self.expect(TT.RPAREN)
            return TokenizeExpr(inner)

        if t.type == TT.SIMILARIZE:
            self.advance()
            self.expect(TT.LPAREN)
            inner = self.parse_expr()
            self.expect(TT.RPAREN)
            return SimilarizeExpr(inner)

        if t.type == TT.RESPOND:
            self.advance()
            self.expect(TT.LPAREN)
            inner = self.parse_expr()
            self.expect(TT.RPAREN)
            return RespondExpr(inner)

        if t.type == TT.STRING:
            self.advance()
            return StringLit(t.value)

        if t.type == TT.NUMBER:
            self.advance()
            return NumberLit(t.value)

        if t.type == TT.PATH:
            self.advance()
            return PathLit(t.value)

        if t.type == TT.IDENT:
            self.advance()
            return VarRef(t.value)

        raise ParseError(f"Unexpected token in expression: {t.type} ({t.value!r}) at line {t.line}")
