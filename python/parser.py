"""
ai.play parser v0.6 — clean rewrite
Recursive descent parser producing an AST from token stream.
"""

from lexer import TT, Token, KEYWORDS
from ast_nodes import *

class ParseError(Exception):
    pass

class Parser:
    def __init__(self, tokens):
        self.tokens = [t for t in tokens if t.type != TT.NEWLINE] + \
                      [Token(TT.EOF, None, 0)]
        self.pos = 0

    # ─── helpers ──────────────────────────────────────────

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        t = self.tokens[self.pos]
        if t.type != TT.EOF:
            self.pos += 1
        return t

    def expect(self, tt):
        t = self.advance()
        if t.type != tt:
            raise ParseError(f"Expected {tt} but got {t.type} ({t.value!r}) at line {t.line}")
        return t

    def match(self, *tts):
        return self.peek().type in tts

    def eat_dot(self):
        self.expect(TT.DOT)

    def read_value(self):
        """Read one value token — string, number, bool, path, ident — as a string."""
        t = self.advance()
        if t.type == TT.BOOL:
            return 'yes' if t.value else 'no'
        return str(t.value) if t.value is not None else ''

    def read_until_rparen(self):
        """Read all tokens until ) — returns joined string. Handles nested parens."""
        parts = []
        depth = 1
        while True:
            t = self.advance()
            if t.type == TT.EOF:
                break
            if t.type == TT.LPAREN:
                depth += 1
                parts.append(str(t.value))
            elif t.type == TT.RPAREN:
                depth -= 1
                if depth == 0:
                    break
                parts.append(str(t.value))
            else:
                parts.append(str(t.value) if t.value is not None else '')
        return ' '.join(parts)

    def read_value_greedy(self):
        """
        Read a value that may span multiple tokens until , or )
        Joins them with no separator — handles emails, URLs, messages.
        """
        parts = []
        while not self.match(TT.RPAREN, TT.COMMA, TT.EOF):
            t = self.advance()
            if t.type == TT.COLON:
                parts.append(':')
            elif t.value is not None:
                parts.append(str(t.value))
        return ''.join(parts)

    def parse_indented_block(self):
        """
        Parse an indented block by consuming tokens until we hit
        something that looks like a new top-level statement.
        We detect this by looking for known top-level keywords.
        """
        TOP_LEVEL = {TT.AI, TT.TRAIN, TT.TEST, TT.OUT, TT.WHILE, TT.DEF,
                     TT.CUSTOM, TT.MAKE, TT.ON, TT.VISION_KW, TT.IF, TT.EOF}
        stmts = []
        while not self.match(*TOP_LEVEL):
            s = self.parse_stmt()
            if s is not None:
                stmts.append(s)
        return stmts

    # ─── top-level parse ──────────────────────────────────

    def parse(self):
        stmts = []
        while not self.match(TT.EOF):
            s = self.parse_stmt()
            if s is not None:
                stmts.append(s)
        return Program(stmts)

    def parse_stmt(self):
        t = self.peek()

        if t.type == TT.AI:         return self.parse_ai_stmt()
        if t.type == TT.TRAIN:      return self.parse_train_stmt()
        if t.type == TT.TEST:       return self.parse_test_stmt()
        if t.type == TT.OUT:        return self.parse_out_stmt()
        if t.type == TT.WHILE:      return self.parse_while_stmt()
        if t.type == TT.DEF:        return self.parse_def_stmt()
        if t.type == TT.CUSTOM:     return self.parse_custom_stmt()
        if t.type == TT.MAKE:       return self.parse_make_stmt()
        if t.type == TT.ON:         return self.parse_on_stmt()
        if t.type == TT.VISION_KW:  return self.parse_vision_stmt()
        if t.type == TT.NOTIFY_KW:  return self.parse_notify_call()
        if t.type == TT.LOG_KW:     return self.parse_log_call()
        if t.type == TT.IF:         return self.parse_if_stmt()
        if t.type == TT.PRINT:      return self.parse_print_stmt()
        if t.type == TT.INPUT:      return self.parse_input_expr()

        # IDENT — assignment or def call
        if t.type == TT.IDENT:
            return self.parse_ident_stmt()

        # skip unknown
        self.advance()
        return None

    # ─── ai. statements ───────────────────────────────────

    def parse_ai_stmt(self):
        self.advance()   # consume 'ai'
        self.eat_dot()
        name = self.advance()
        # 'yes' tokenises as BOOL True — map it back to the string 'yes'
        if name.type == TT.BOOL and name.value == True:
            directive = 'yes'
        elif name.type == TT.BOOL and name.value == False:
            directive = 'no'
        else:
            directive = str(name.value)

        # ai.enable()
        if directive == 'enable':
            self.expect(TT.LPAREN)
            self.expect(TT.RPAREN)
            return AIEnable()

        # ai.model(mode) or ai.model(custom, path)
        if directive == 'model':
            self.expect(TT.LPAREN)
            mode = self.read_value()
            path = None
            if self.match(TT.COMMA):
                self.advance()
                path = self.read_value()
            self.expect(TT.RPAREN)
            return AIModel(mode, path)

        # ai.web(yes/no)  ai.vision(normal/live)  ai.diffusion(yes)
        # ai.video(yes)   ai.voice(yes)
        if directive in ('web', 'vision', 'diffusion', 'video', 'voice'):
            self.expect(TT.LPAREN)
            val = self.read_value()
            self.expect(TT.RPAREN)
            return AICapability(directive, val)

        # ai.persona("text")
        if directive == 'persona':
            self.expect(TT.LPAREN)
            if not self.match(TT.STRING):
                raise ParseError(
                    f"ai.persona() requires quoted text at line {self.peek().line}. "
                    f'Example: ai.persona("You are a helpful assistant.")'
                )
            text = self.read_value()
            self.expect(TT.RPAREN)
            return AIPersona(text)

        # ai.memory(rule/generative/upload[, url])
        if directive == 'memory':
            self.expect(TT.LPAREN)
            mode = self.read_value()
            url  = None
            if self.match(TT.COMMA):
                self.advance()
                url = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AIMemory(mode, url)

        # ai.skills(path)
        if directive == 'skills':
            self.expect(TT.LPAREN)
            path = self.read_value()
            self.expect(TT.RPAREN)
            return AISkills(path)

        # ai.yes(target)
        if directive == 'yes':
            self.expect(TT.LPAREN)
            target = self.read_value()
            self.expect(TT.RPAREN)
            return AIYesNode(target)

        # ai.notify(channel, target)
        if directive == 'notify':
            self.expect(TT.LPAREN)
            channel = self.read_value()
            self.expect(TT.COMMA)
            target = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AINotify(channel, target)

        # ai.fallback(message)
        if directive == 'fallback':
            self.expect(TT.LPAREN)
            msg = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AIFallback(msg)

        # ai.log(path)
        if directive == 'log':
            self.expect(TT.LPAREN)
            path = self.read_value()
            self.expect(TT.RPAREN)
            return AILog(path)

        # ai.train(url)
        if directive == 'train':
            self.expect(TT.LPAREN)
            url = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AITrain(url)

        # ai.language(lang)
        if directive == 'language':
            self.expect(TT.LPAREN)
            lang = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AILanguage(lang)

        # ai.schedule(interval, event)
        if directive == 'schedule':
            self.expect(TT.LPAREN)
            interval = self.read_value()
            self.expect(TT.COMMA)
            event = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AISchedule(interval, event)

        # ai.encrypt(yes/key)
        if directive == 'encrypt':
            self.expect(TT.LPAREN)
            key = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AIEncrypt(key)

        # ai.mcp(url)
        if directive == 'mcp':
            self.expect(TT.LPAREN)
            url = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AIMcp(url)

        # ai.admin(mode)
        if directive == 'admin':
            self.expect(TT.LPAREN)
            mode = self.read_value()
            self.expect(TT.RPAREN)
            return AIAdmin(mode)

        # ai.name(text)
        if directive == 'name':
            self.expect(TT.LPAREN)
            text = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AIName(text)

        # ai.version(text)
        if directive == 'version':
            self.expect(TT.LPAREN)
            text = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AIVersion(text)

        # ai.creator(text)
        if directive == 'creator':
            self.expect(TT.LPAREN)
            text = self.read_value_greedy()
            self.expect(TT.RPAREN)
            return AICreator(text)

        # ai.transfer(number)
        if directive == 'transfer':
            self.expect(TT.LPAREN)
            number = self.read_value()
            self.expect(TT.RPAREN)
            return TransferCall(number)

        raise ParseError(f"Unknown ai directive: {directive!r} at line {name.line}")

    # ─── train.embed ──────────────────────────────────────

    def parse_train_stmt(self):
        self.advance()
        self.eat_dot()
        directive = self.advance().value
        if directive == 'embed':
            self.expect(TT.LPAREN)
            path = self.read_value()
            self.expect(TT.RPAREN)
            return TrainEmbed(path)
        raise ParseError(f"Unknown train directive: {directive!r}")

    # ─── test.ui ──────────────────────────────────────────

    def parse_test_stmt(self):
        self.advance()
        self.eat_dot()
        directive = self.advance().value
        if directive == 'ui':
            self.expect(TT.LPAREN)
            val = self.read_value()
            self.expect(TT.RPAREN)
            return TestUI(val)
        raise ParseError(f"Unknown test directive: {directive!r}")

    # ─── out.in ───────────────────────────────────────────

    def parse_out_stmt(self):
        self.advance()
        self.eat_dot()
        directive = str(self.advance().value)
        if directive == 'in':
            self.expect(TT.LPAREN)
            key = self.read_value()
            user = None
            storage = None
            upload  = None
            while self.match(TT.COMMA):
                self.advance()
                t = self.advance()
                if t.type == TT.NAMEDPARAM:
                    param_name, param_val = t.value
                else:
                    param_name = str(t.value)
                    self.expect(TT.EQUALS)
                    param_val  = self.read_value_greedy()
                if param_name == 'user':      user    = param_val
                elif param_name == 'storage': storage = param_val
                elif param_name == 'upload':  upload  = param_val
            self.expect(TT.RPAREN)
            return OutIn(key, user=user, storage=storage, upload=upload)
        raise ParseError(f"Unknown out directive: {directive!r}")

    # ─── while ────────────────────────────────────────────

    def parse_while_stmt(self):
        self.advance()
        self.expect(TT.LPAREN)
        cond = self.read_until_rparen()
        self.expect(TT.COLON)
        body = self.parse_indented_block()
        return WhileLoop(cond, body)

    # ─── def ──────────────────────────────────────────────

    def parse_def_stmt(self):
        self.advance()
        name = str(self.advance().value)
        self.expect(TT.LPAREN)
        self.expect(TT.RPAREN)
        self.expect(TT.COLON)
        body = self.parse_indented_block()
        return DefBlock(name, body)

    # ─── custom.module ────────────────────────────────────

    def parse_custom_stmt(self):
        self.advance()
        self.eat_dot()
        directive = str(self.advance().value)
        if directive == 'module':
            self.expect(TT.LPAREN)
            name = self.read_value()
            self.expect(TT.RPAREN)
            return CustomModule(name)
        raise ParseError(f"Unknown custom directive: {directive!r}")

    # ─── make.module ──────────────────────────────────────

    def parse_make_stmt(self):
        self.advance()
        self.eat_dot()
        directive = str(self.advance().value)
        if directive == 'module':
            self.expect(TT.LPAREN)
            name = self.read_value()
            self.expect(TT.RPAREN)
            return MakeModule(name)
        raise ParseError(f"Unknown make directive: {directive!r}")

    # ─── on.event ─────────────────────────────────────────

    def parse_on_stmt(self):
        self.advance()
        self.eat_dot()
        _ev = self.advance()
        event = str(_ev.value) if _ev.value is not None else ''  
        self.expect(TT.LPAREN)
        param = None
        if not self.match(TT.RPAREN):
            param = self.read_value_greedy()
        self.expect(TT.RPAREN)
        self.expect(TT.COLON)
        body = self.parse_indented_block()
        return OnEvent(event, param, body)

    # ─── vision.train ─────────────────────────────────────

    def parse_vision_stmt(self):
        self.advance()
        self.eat_dot()
        directive = str(self.advance().value or '')
        if directive == 'train':
            self.expect(TT.LPAREN)
            label = self.read_value()
            self.expect(TT.COMMA)
            path  = self.read_value()
            self.expect(TT.RPAREN)
            return VisionTrain(label, path)
        raise ParseError(f"Unknown vision directive: {directive!r}")

    # ─── notify.channel ───────────────────────────────────

    def parse_notify_call(self):
        self.advance()
        self.eat_dot()
        channel = str(self.advance().value)
        self.expect(TT.LPAREN)
        message = self.read_value_greedy()
        attachment = None
        if self.match(TT.COMMA):
            self.advance()
            attachment = self.read_value()
        self.expect(TT.RPAREN)
        return NotifyCall(channel, message, attachment)

    # ─── log() ────────────────────────────────────────────

    def parse_log_call(self):
        self.advance()
        self.expect(TT.LPAREN)
        val = self.read_value()
        self.expect(TT.RPAREN)
        return LogCall(val)

    # ─── if / else ────────────────────────────────────────

    def parse_if_stmt(self):
        self.advance()
        self.expect(TT.LPAREN)
        condition = self.read_until_rparen()
        self.expect(TT.COLON)
        body = self.parse_indented_block()
        else_body = []
        if self.match(TT.ELSE):
            self.advance()
            self.expect(TT.LPAREN)
            self.expect(TT.RPAREN)
            self.expect(TT.COLON)
            else_body = self.parse_indented_block()
        return IfStmt(condition, body, else_body)

    # ─── print ────────────────────────────────────────────

    def parse_print_stmt(self):
        self.advance()
        self.expect(TT.LPAREN)
        val = self.read_value_greedy()
        self.expect(TT.RPAREN)
        return PrintStmt(val)

    # ─── input() ──────────────────────────────────────────

    def parse_input_expr(self):
        self.advance()
        self.expect(TT.LPAREN)
        self.expect(TT.RPAREN)
        return InputExpr()

    # ─── IDENT — assignment or def call ───────────────────

    def parse_ident_stmt(self):
        name_tok = self.advance()
        name = str(name_tok.value)

        # Assignment: Name = expr
        if self.match(TT.EQUALS):
            self.advance()
            expr = self.parse_expr()
            return Assign(name, expr)

        # sandbox.start/run/install
        if name == 'sandbox' and self.match(TT.DOT):
            self.advance()
            directive = str(self.advance().value)
            if directive == 'start':
                self.expect(TT.LPAREN)
                mode = self.read_value() if not self.match(TT.RPAREN) else 'venv'
                self.expect(TT.RPAREN)
                return SandboxStart(mode)
            if directive == 'run':
                self.expect(TT.LPAREN)
                cmd = self.read_value_greedy()
                self.expect(TT.RPAREN)
                return SandboxRun(cmd)
            if directive == 'install':
                self.expect(TT.LPAREN)
                pkg = self.read_value_greedy()
                self.expect(TT.RPAREN)
                return SandboxInstall(pkg)

        # artifacts.on(yes)
        if name == 'artifacts' and self.match(TT.DOT):
            self.advance()  # consume dot
            directive = str(self.advance().value)
            if directive == 'on':
                self.expect(TT.LPAREN)
                val = self.read_value()
                self.expect(TT.RPAREN)
                return ArtifactsOn(val)

        # technique.add(name, source)
        if name == 'technique' and self.match(TT.DOT):
            self.advance()  # consume dot
            directive = str(self.advance().value)
            if directive == 'add':
                self.expect(TT.LPAREN)
                tname = self.read_value()
                source = None
                if self.match(TT.COMMA):
                    self.advance()
                    source = self.read_value_greedy()
                self.expect(TT.RPAREN)
                return TechniqueAdd(tname, source)

        # output.deny()
        if name == 'output' and self.match(TT.DOT):
            self.advance()
            directive = str(self.advance().value)
            if directive == 'deny':
                self.expect(TT.LPAREN)
                self.expect(TT.RPAREN)
                return OutputDeny()

        # Def call: myFunc()
        if self.match(TT.LPAREN):
            self.advance()
            self.expect(TT.RPAREN)
            return CallDef(name)

        return None

    # ─── expressions ──────────────────────────────────────

    def parse_expr(self):
        t = self.peek()

        if t.type == TT.INPUT:
            return self.parse_input_expr()

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

        # Bare value — variable name or literal
        tok = self.advance()
        return Literal(tok.value)
