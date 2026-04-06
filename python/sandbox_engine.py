"""
ai.play sandbox engine
Provides an isolated execution environment for the AI to run and test code.
Supports venv (lightweight) and Docker (full isolation).
"""

import os
import sys
import subprocess
import tempfile
import threading
import shutil

DESTRUCTIVE_PATTERNS = [
    'rm -rf', 'rmdir', 'del /f', 'format', 'mkfs',
    'shutdown', 'reboot', 'halt', 'dd if=',
    'DROP TABLE', 'DROP DATABASE', 'TRUNCATE',
    '> /dev/', 'chmod 777', 'chown root',
]

class SandboxResult:
    def __init__(self, stdout, stderr, returncode):
        self.stdout     = stdout
        self.stderr     = stderr
        self.returncode = returncode
        self.success    = returncode == 0

    def __str__(self):
        if self.success:
            return self.stdout or '(no output)'
        return f"Error (code {self.returncode}):\n{self.stderr or self.stdout or '(no output)'}"


class VenvSandbox:
    def __init__(self):
        self.path    = tempfile.mkdtemp(prefix='aiplay_sandbox_')
        self.venv    = os.path.join(self.path, 'venv')
        self.python  = None
        self.pip     = None
        self._ready  = False

    def setup(self):
        try:
            subprocess.run(
                [sys.executable, '-m', 'venv', self.venv],
                capture_output=True, timeout=30
            )
            if os.name == 'nt':
                self.python = os.path.join(self.venv, 'Scripts', 'python.exe')
                self.pip    = os.path.join(self.venv, 'Scripts', 'pip.exe')
            else:
                self.python = os.path.join(self.venv, 'bin', 'python')
                self.pip    = os.path.join(self.venv, 'bin', 'pip')
            self._ready = True
            print(f"[sandbox] venv ready at {self.path}")
            return True
        except Exception as e:
            print(f"[sandbox] venv setup failed: {e}")
            return False

    def install(self, package):
        if not self._ready:
            return SandboxResult('', 'Sandbox not ready', 1)
        result = subprocess.run(
            [self.pip, 'install', package, '--quiet'],
            capture_output=True, text=True, timeout=120
        )
        return SandboxResult(result.stdout, result.stderr, result.returncode)

    def run_command(self, command, timeout=30):
        if not self._ready:
            return SandboxResult('', 'Sandbox not ready', 1)
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=self.path,
            env={**os.environ, 'PATH': os.path.dirname(self.python) + os.pathsep + os.environ.get('PATH', '')}
        )
        return SandboxResult(result.stdout, result.stderr, result.returncode)

    def run_python(self, code, timeout=30):
        if not self._ready:
            return SandboxResult('', 'Sandbox not ready', 1)
        script = os.path.join(self.path, '_run.py')
        with open(script, 'w', encoding='utf-8') as f:
            f.write(code)
        result = subprocess.run(
            [self.python, script],
            capture_output=True, text=True, timeout=timeout, cwd=self.path
        )
        return SandboxResult(result.stdout, result.stderr, result.returncode)

    def write_file(self, name, content):
        path = os.path.join(self.path, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def cleanup(self):
        try:
            shutil.rmtree(self.path, ignore_errors=True)
        except Exception:
            pass


class DockerSandbox:
    def __init__(self):
        self.container_id = None
        self.image = 'python:3.11-slim'
        self._ready = False

    def setup(self):
        try:
            # Check Docker is available
            result = subprocess.run(['docker', '--version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                print("[sandbox] Docker not available, falling back to venv")
                return False

            # Start a container
            result = subprocess.run(
                ['docker', 'run', '-d', '--rm', '--network', 'none',
                 '--memory', '512m', '--cpus', '1',
                 self.image, 'sleep', '3600'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return False

            self.container_id = result.stdout.strip()
            self._ready = True
            print(f"[sandbox] Docker container ready: {self.container_id[:12]}")
            return True
        except Exception as e:
            print(f"[sandbox] Docker setup failed: {e}")
            return False

    def install(self, package):
        if not self._ready:
            return SandboxResult('', 'Sandbox not ready', 1)
        result = subprocess.run(
            ['docker', 'exec', self.container_id, 'pip', 'install', package, '--quiet'],
            capture_output=True, text=True, timeout=120
        )
        return SandboxResult(result.stdout, result.stderr, result.returncode)

    def run_command(self, command, timeout=30):
        if not self._ready:
            return SandboxResult('', 'Sandbox not ready', 1)
        result = subprocess.run(
            ['docker', 'exec', self.container_id, 'sh', '-c', command],
            capture_output=True, text=True, timeout=timeout
        )
        return SandboxResult(result.stdout, result.stderr, result.returncode)

    def run_python(self, code, timeout=30):
        # Write to container and run
        write_result = subprocess.run(
            ['docker', 'exec', '-i', self.container_id, 'sh', '-c', 'cat > /tmp/_run.py'],
            input=code, text=True, capture_output=True, timeout=10
        )
        result = subprocess.run(
            ['docker', 'exec', self.container_id, 'python', '/tmp/_run.py'],
            capture_output=True, text=True, timeout=timeout
        )
        return SandboxResult(result.stdout, result.stderr, result.returncode)

    def cleanup(self):
        if self.container_id:
            subprocess.run(['docker', 'stop', self.container_id], capture_output=True, timeout=10)


class SandboxEngine:
    def __init__(self):
        self.sandbox = None
        self.mode    = None

    def start(self, mode='venv'):
        self.mode = mode
        if mode == 'docker':
            sb = DockerSandbox()
            if sb.setup():
                self.sandbox = sb
                return True
            # Fall back to venv
            print("[sandbox] Falling back to venv")

        sb = VenvSandbox()
        if sb.setup():
            self.sandbox = sb
            return True

        print("[sandbox] Failed to start any sandbox")
        return False

    def install(self, package):
        if not self.sandbox:
            return SandboxResult('', 'No sandbox running. Use sandbox.start() first.', 1)
        print(f"[sandbox] Installing {package}...")
        result = self.sandbox.install(package)
        print(f"[sandbox] {'OK' if result.success else 'FAILED'}: {package}")
        return result

    def run(self, command):
        if not self.sandbox:
            return SandboxResult('', 'No sandbox running. Use sandbox.start() first.', 1)
        return self.sandbox.run_command(command)

    def run_python(self, code):
        if not self.sandbox:
            return SandboxResult('', 'No sandbox running. Use sandbox.start() first.', 1)
        return self.sandbox.run_python(code)

    def is_ready(self):
        return self.sandbox is not None

    def cleanup(self):
        if self.sandbox:
            self.sandbox.cleanup()
            self.sandbox = None
