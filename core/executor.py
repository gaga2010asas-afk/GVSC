"""Исполнитель VIBE-скриптов: запускает Python-код с макросами в globals()."""
import io
import contextlib
import re
import subprocess
import sys
from PyQt6.QtCore import QThread, pyqtSignal

class Executor(QThread):
    progress = pyqtSignal(str)
    finished_ok = pyqtSignal()
    failed = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, code: str, macros, project_root: str):
        super().__init__()
        self.code = code
        self.macros = macros
        self.project_root = project_root
        self._stop = False

    def stop(self):
        self._stop = True

    def _make_stdout(self):
        parent = self
        class Stream(io.TextIOBase):
            def write(self, s):
                if s.strip():
                    parent.log.emit(s.rstrip())
                    if "PROGRESS:" in s:
                        parent.progress.emit(s.strip())
                return len(s)
            def flush(self):
                pass
        return Stream()

    def run(self):
        # 1. Авто-установка зависимостей (# INSTALL)
        install_matches = re.findall(r"#\s*INSTALL:\s*(.+)", self.code)
        if install_matches:
            libs = []
            for line in install_matches:
                libs.extend(line.strip().split())
            if libs:
                self.log.emit(f"📦 Обнаружены зависимости: {', '.join(libs)}. Установка...")
                try:
                    subprocess.run([sys.executable, "-m", "pip", "install"] + libs, capture_output=True, text=True)
                    self.log.emit("✔ Зависимости установлены.")
                except Exception as e:
                    self.log.emit(f"❌ Ошибка установки: {e}")

        # 2. Очистка кода от служебных команд GVSC (Debug on!, # LINT)
        clean_lines = []
        for line in self.code.splitlines():
            stripped = line.strip()
            # Убираем строку "Debug on!" и комментарии "# LINT:"
            if stripped == "Debug on!" or stripped.startswith("# LINT:"):
                continue
            clean_lines.append(line)
        
        exec_code = "\n".join(clean_lines)

        # 3. Подготовка окружения (инъекция макросов app_*)
        env = {"__name__": "__vibe__", "__file__": self.project_root}
        for name in dir(self.macros):
            if name.startswith("app_"):
                env[name] = getattr(self.macros, name)

        out = self._make_stdout()
        
        try:
            # Запускаем очищенный код
            with contextlib.redirect_stdout(out):
                exec(compile(exec_code, "<vibe>", "exec"), env)
            self.finished_ok.emit()
        except Exception as e:
            import traceback
            self.failed.emit(traceback.format_exc())