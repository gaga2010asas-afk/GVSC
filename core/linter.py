import subprocess
import shutil
import py_compile
import re

class Linter:
    def check(self, language: str, filepath: str):
        lang = language.lower()
        if lang in ("python", "py"):
            return self._check_python(filepath)
        elif lang in ("csharp", "c#", "cs"):
            return self._check_csharp(filepath)
        elif lang in ("gdscript", "gd"):
            return self._check_gdscript(filepath)
        return True, []

    def _check_python(self, filepath):
        try:
            py_compile.compile(filepath, doraise=True)
            return True, []
        except py_compile.PyCompileError as e:
            # Достаем номер строки из ошибки
            match = re.search(r"line (\d+)", str(e))
            line = int(match.group(1)) if match else 1
            return False, [(line, str(e))]

    def _check_csharp(self, filepath):
        if not shutil.which("dotnet"):
            return True, []
        return True, []

    def _check_gdscript(self, filepath):
        if not shutil.which("godot"):
            return True, []
        try:
            r = subprocess.run(
                ["godot", "--headless", "--check-only", "--script", filepath],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0:
                return True, []
            else:
                lines = []
                # Ищем строки с ошибками в выводе Godot
                for m in re.finditer(r"SCRIPT ERROR:.*at line (\d+)", r.stderr):
                    lines.append((int(m.group(1)), r.stderr))
                return False, lines
        except Exception:
            return True, []