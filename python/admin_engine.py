"""
ai.play admin engine
Controlled shell access for the AI with permission levels.

Modes:
  ask         — ask before every command
  destructive — ask only for dangerous commands, run others silently
  full        — run everything without asking (use with caution)
"""

import os
import subprocess
import re

# Patterns that are always considered destructive
DESTRUCTIVE = [
    r'rm\s+-[rf]', r'rmdir', r'del\s+/[fqs]', r'format\s+[a-z]:',
    r'mkfs', r'dd\s+if=', r'shutdown', r'reboot', r'halt', r'poweroff',
    r'DROP\s+TABLE', r'DROP\s+DATABASE', r'TRUNCATE\s+TABLE',
    r'chmod\s+[0-7]*7[0-7][0-7]', r'chown\s+root', r'sudo\s+rm',
    r'>\s*/dev/', r':\(\)\{.*\}', r'fork\s+bomb',
    r'reg\s+delete', r'sc\s+delete', r'net\s+user.*\/delete',
    r'wipe', r'shred', r'cipher\s+/w',
]

DESTRUCTIVE_RE = [re.compile(p, re.IGNORECASE) for p in DESTRUCTIVE]


def is_destructive(command):
    for pattern in DESTRUCTIVE_RE:
        if pattern.search(command):
            return True
    return False


class AdminEngine:
    def __init__(self, mode='ask'):
        self.mode = mode  # ask | destructive | full

    def _ask_permission(self, command, reason=''):
        prompt = f"\n[ai.play admin] Command: {command}"
        if reason:
            prompt += f"\n  Reason: {reason}"
        prompt += "\n  Allow? (yes/no): "
        try:
            answer = input(prompt).strip().lower()
            return answer in ('yes', 'y', '1')
        except (EOFError, KeyboardInterrupt):
            return False

    def run(self, command, reason=''):
        """Run a shell command with permission checking."""
        destructive = is_destructive(command)

        if self.mode == 'ask':
            if not self._ask_permission(command, reason):
                return AdminResult('', 'Permission denied by user.', 1)

        elif self.mode == 'destructive':
            if destructive:
                print(f"[ai.play admin] ⚠ Destructive command detected: {command}")
                if not self._ask_permission(command, reason or 'This command may cause irreversible changes.'):
                    return AdminResult('', 'Permission denied by user.', 1)
            else:
                print(f"[ai.play admin] Running: {command}")

        elif self.mode == 'full':
            print(f"[ai.play admin] Running: {command}")

        try:
            result = subprocess.run(
                command, shell=True,
                capture_output=True, text=True, timeout=60
            )
            return AdminResult(result.stdout, result.stderr, result.returncode)
        except subprocess.TimeoutExpired:
            return AdminResult('', 'Command timed out after 60s', 1)
        except Exception as e:
            return AdminResult('', str(e), 1)

    def install(self, package, manager='pip'):
        """Install a package via pip or system package manager."""
        if manager == 'pip':
            return self.run(f"pip install {package}", reason=f"AI wants to install Python package: {package}")
        elif manager in ('apt', 'apt-get'):
            return self.run(f"sudo apt-get install -y {package}", reason=f"AI wants to install system package: {package}")
        elif manager in ('npm',):
            return self.run(f"npm install -g {package}", reason=f"AI wants to install npm package: {package}")
        else:
            return AdminResult('', f"Unknown package manager: {manager}", 1)

    def read_file(self, path):
        """Read a file — always allowed, no permission needed."""
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            return f"Error reading {path}: {e}"

    def write_file(self, path, content, reason=''):
        """Write a file — asks permission in ask mode."""
        command = f"write to {path}"
        if self.mode == 'ask':
            if not self._ask_permission(command, reason or f"AI wants to write to {path}"):
                return AdminResult('', 'Permission denied by user.', 1)
        elif self.mode == 'destructive':
            print(f"[ai.play admin] Writing: {path}")

        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return AdminResult(f"Written to {path}", '', 0)
        except Exception as e:
            return AdminResult('', str(e), 1)


class AdminResult:
    def __init__(self, stdout, stderr, returncode):
        self.stdout     = stdout
        self.stderr     = stderr
        self.returncode = returncode
        self.success    = returncode == 0

    def __str__(self):
        if self.success:
            return self.stdout or '(done)'
        return f"Error: {self.stderr or self.stdout or '(unknown error)'}"
