# ui/vibe_extructor.py
# VIBE Extructor — чистый исполнитель VIBE-скриптов (без локального ИИ).

import re
import os
import time
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QProgressBar, QLabel, QApplication
)
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtCore import Qt
from PyQt6.Qsci import QsciScintilla, QsciLexerPython
from core.executor import Executor
from core.linter import Linter

# Тот самый промпт для нейросети
MASTER_PROMPT = """# ROLE: GVSC SENIOR AI DEVELOPER
You are the core AI developer for "Gaga Vibe Studio Code" (GVSC), an AI-First IDE for game development. You do not have direct file access. You write Python scripts (VIBE Scripts) that the user pastes into the GVSC VIBE Extructor.

# CORE PROTOCOLS
1. SAVEcode: Always start complex scripts with `# SAVEcode: <name>`. If asked to revert, output ONLY `UPcode: <name>`.
2. INSTALL: If using external libs (Pillow, requests), start with `# INSTALL: <lib>`.
3. TOKEN OPTIMIZATION: Use multiple assignments, list comprehensions, and loops. NEVER write boilerplate.
4. DEBUG: End scripts with `Debug on!` to trigger linting.
5. LANGUAGE: Write Python scripts to generate files in ANY language (C#, GDScript, C++, JS). Use `# LINT: <lang> <filepath>` for validation.

# MACROS API (Use these instead of standard code)
- app_create_file(filepath, content) 
- app_read_file(filepath) / app_read_lines(filepath, start, end)
- app_replace_in_file(filepath, old, new) / app_search_in_file(filepath, query)
- app_batch_replace(folder, ext, old, new)
- app_download(url, save_path) / app_unzip(zip_path, extract_path)
- app_move_file(src, dst) / app_copy_file(src, dst) / app_check_exists(filepath)
- app_run_terminal(command) / app_run_game(engine="godot")
- app_get_project_tree()
- app_generate_scene(engine="godot", scene_name="UI", ui_type="vbox")
- app_create_meta_file(filepath, engine="godot")
- app_append_file(filepath, text) -> For updating project_state.md
- app_save_code(name) / app_restore_code(name)

# 6GB VRAM LIMIT (CRITICAL)
- NEVER read whole large files. Use `app_search_in_file` first, then `app_read_lines`.
- NEVER read binary files (images/audio) as text.
- Break complex tasks into smaller scripts (Chunking).

# GRAPHICS ENGINE (PAI STUDIO v3.4)
If generating 2D/3D visuals, output Python code with:
`# PAI_MODE: pixel_2d` | `# PAI_MODE: vector_2d` | `# PAI_MODE: voxel_3d` | `# PAI_MODE: polygon_3d`
- BLACKLIST: NO `QColor("#HEX", alpha)`, use `QColor(r,g,b,a)`. NO `.RoundLine`, use `Qt.PenCapStyle.RoundCap`. `drawLine` coordinates MUST be `int()`.

# WORKFLOW
1. Analyze user request.
2. Write a Python script (VIBE Script) following all rules.
3. Include progress updates: `print("PROGRESS: 50%")`.
4. Output ONLY the code. No markdown. No explanations."""

# ---------- Парсер триггеров VIBE-скрипта ----------
TRIGGER_RE = {
    "savecode": re.compile(r"^\s*#\s*SAVEcode\s*:\s*(\S+)", re.MULTILINE),
    "install":  re.compile(r"^\s*#\s*INSTALL\s*:\s*(.+)$", re.MULTILINE),
    "lint":     re.compile(r"^\s*#\s*LINT\s*:\s*(\S+)\s+(.+)$", re.MULTILINE),
    "debug":    re.compile(r"^\s*Debug on!\s*$", re.MULTILINE),
    "upcode":   re.compile(r"^\s*UPcode\s*:\s*(\S+)\s*$", re.MULTILINE),
    "progress": re.compile(r"PROGRESS:\s*([\d.]+)(?:\s*/\s*([\d.]+))?"),
}

def parse_vibe_triggers(code: str):
    return {
        "savecode": (TRIGGER_RE["savecode"].findall(code) or [None])[0],
        "install":  TRIGGER_RE["install"].findall(code),
        "lints":    TRIGGER_RE["lint"].findall(code),
        "debug":    bool(TRIGGER_RE["debug"].search(code)),
        "upcode":   (TRIGGER_RE["upcode"].findall(code) or [None])[0],
    }


class VibeExtructor(QDialog):
    def __init__(self, macros, project_root, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VIBE Extructor — GVSC Executor")
        self.resize(900, 750)

        self.macros = macros
        self.project_root = project_root
        self.parent_main = parent

        self.executor = None
        self.start_time = 0
        self.last_progress = 0
        self.triggers = {}

        icon_path = os.path.join("assets", "ui", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        # Верхняя панель
        top = QHBoxLayout()
        top.addWidget(QLabel("VIBE-скрипт (Python + макросы GVSC). Нажми GO:"))

        btn_clear = QPushButton("Очистить")
        btn_clear.clicked.connect(self._clear_all)
        top.addWidget(btn_clear)

        # ВОЗВРАЩАЕМ КНОПКУ КОПИРОВАНИЯ ПРОМПТА
        btn_copy_prompt = QPushButton("📋 Скопировать промпт для ИИ")
        btn_copy_prompt.setStyleSheet("background-color: #2b1b4d; color: #d4b5ff; border: 1px solid #d4b5ff; padding: 4px 8px; border-radius: 3px;")
        btn_copy_prompt.clicked.connect(self.copy_prompt)
        top.addWidget(btn_copy_prompt)

        top.addStretch()
        lay.addLayout(top)

        # Редактор кода
        self.code = QsciScintilla()
        self._style_editor(self.code, read_only=False)
        self.code.setText(self._default_snippet())
        lay.addWidget(self.code, 3)

        # Прогресс + ETA
        prow = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.eta_label = QLabel("ETA: --")
        self.eta_label.setStyleSheet("color: #00ff88; font-weight: bold;")
        prow.addWidget(self.progress)
        prow.addWidget(self.eta_label)
        lay.addLayout(prow)

        # Лог
        self.log = QsciScintilla()
        self._style_editor(self.log, read_only=True, log_theme=True)
        lay.addWidget(self.log, 2)

        # Кнопки внизу
        btns = QHBoxLayout()

        self.btn_go = QPushButton("GO (Execute)")
        self.btn_go.setStyleSheet("""
            QPushButton { background:#00ff88; color:#000; font-weight:bold; padding:12px; min-height:44px; border-radius:4px; }
            QPushButton:disabled { background:#004422; color:#008844; }
        """)
        self.btn_go.clicked.connect(self.run_script)
        btns.addWidget(self.btn_go)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setStyleSheet("""
            QPushButton { background:#4d0000; color:#ff5555; font-weight:bold; padding:12px; min-height:44px; border-radius:4px; }
            QPushButton:disabled { background:#2a0000; color:#662222; }
        """)
        self.btn_stop.clicked.connect(self.stop_script)
        self.btn_stop.setEnabled(False)
        btns.addWidget(self.btn_stop)

        self.btn_copy = QPushButton("📋 Копировать лог для ИИ")
        self.btn_copy.clicked.connect(self.copy_log)
        btns.addWidget(self.btn_copy)

        lay.addLayout(btns)

    def _style_editor(self, widget: QsciScintilla, read_only=False, log_theme=False):
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        widget.setFont(font)
        widget.setUtf8(True)
        widget.setMarginsFont(font)
        widget.setMarginWidth(0, "0000")
        widget.setMarginLineNumbers(0, True)

        bg = QColor("#000" if log_theme else "#1E1E1E")
        fg = QColor("#00ff88" if log_theme else "#D4D4D4")
        gutter_bg = QColor("#000" if log_theme else "#1E1E1E")
        gutter_fg = QColor("#555" if log_theme else "#858585")

        widget.setMarginsBackgroundColor(gutter_bg)
        widget.setMarginsForegroundColor(gutter_fg)
        widget.setPaper(bg)
        widget.setColor(fg)
        widget.setReadOnly(read_only)

        if not log_theme:
            lexer = QsciLexerPython(widget)
            lexer.setDefaultFont(font)
            lexer.setDefaultPaper(bg)
            lexer.setDefaultColor(fg)
            for i in range(128):
                lexer.setFont(font, i)
            lexer.setColor(QColor("#569CD6"), QsciLexerPython.Keyword)
            lexer.setColor(QColor("#CE9178"), QsciLexerPython.DoubleQuotedString)
            lexer.setColor(QColor("#6A9955"), QsciLexerPython.Comment)
            widget.setLexer(lexer)

    def _default_snippet(self) -> str:
        return (
            "# ========================================================\n"
            "# ДОБРО ПОЖАЛОВАТЬ В VIBE EXTRUCTOR!\n"
            "# Сюда ты вставляешь Python-скрипты от нейросети.\n"
            "# Код управляет GVSC через встроенные макросы.\n"
            "# ========================================================\n"
            "#\n"
            "# ТРИГГЕРЫ (в начале строки):\n"
            "#   # SAVEcode: my_backup  - сделать бэкап\n"
            "#   # INSTALL: Pillow      - установить библиотеку\n"
            "#   # LINT: csharp file.cs - проверить синтаксис\n"
            "#   Debug on!             - запустить линтер в конце\n"
            "#\n"
            "# ПРОГРЕСС-БАР:\n"
            "#   print('PROGRESS: 50')  - заполнит шкалу до 50%\n"
            "#\n"
            "# ФАЙЛЫ И КОД:\n"
            "#   app_create_file('src/main.py', 'code...')\n"
            "#   app_replace_in_file('src/main.py', 'old', 'new')\n"
            "#   app_search_in_file('src/main.py', 'query')\n"
            "#\n"
            "# АССЕТЫ, МУЗЫКА И ЗВУКИ:\n"
            "#   app_download('url', 'assets/audio/bgm.mp3')\n"
            "#   app_create_meta_file('assets/audio/bgm.mp3')\n"
            "#\n"
            "# ГРАФИКА 2D И 3D (PAI STUDIO):\n"
            "#   # PAI_MODE: pixel_2d     (32x32, 64x64 пиксель-арт)\n"
            "#   # PAI_MODE: vector_2d    (QPainter 800x600)\n"
            "#   # PAI_MODE: voxel_3d     (32x32x32 воксели)\n"
            "#   # PAI_MODE: polygon_3d   (Вершины и полигоны)\n"
            "#   app_save_canvas('assets/2d/hero.png')\n"
            "# ========================================================\n"
            "\n"
            "# Пример (удали это и вставь свой):\n"
            "print('PROGRESS: 50')\n"
            "app_create_file('hello.txt', 'Привет из VIBE!')\n"
            "print('PROGRESS: 100')\n"
            "Debug on!\n"
        )

    def _clear_all(self):
        self.code.setText("")
        self.log.setText("")
        self.progress.setValue(0)
        self.eta_label.setText("ETA: --")

    # Метод копирования промпта
    def copy_prompt(self):
        QApplication.clipboard().setText(MASTER_PROMPT)
        self.append_log("📋 Промпт для ИИ скопирован в буфер обмена! Вставь его в ChatGPT/DeepSeek перед запросом.")

    def run_script(self):
        code = self.code.text().strip()
        if not code:
            self.append_log("⚠ Пусто.")
            return

        self.triggers = parse_vibe_triggers(code)

        if self.triggers["upcode"] and len(code.splitlines()) <= 3:
            snap = self.triggers["upcode"]
            self.append_log(f"↺ UPcode: откат к снапшоту '{snap}'...")
            if self.parent_main and hasattr(self.parent_main, "restore_snapshot"):
                self.parent_main.restore_snapshot(snap)
                self.append_log("✔ Откат выполнен.")
            else:
                self.append_log("⚠ parent_main.restore_snapshot не найден. Откат пропущен.")
            return

        self.progress.setValue(0)
        self.eta_label.setText("ETA: расчет...")
        self.start_time = time.time()
        self.last_progress = 0
        self.btn_go.setEnabled(False)
        self.btn_stop.setEnabled(True)

        if self.triggers["savecode"]:
            self.append_log(f"📌 SAVEcode: {self.triggers['savecode']}")
        if self.triggers["install"]:
            self.append_log(f"📦 INSTALL: {', '.join(self.triggers['install'])}")
        if self.triggers["lints"]:
            for lang, path in self.triggers["lints"]:
                self.append_log(f"🔎 LINT: {lang} {path.strip()}")

        self.append_log("▶ Запуск VIBE-скрипта...")

        self.executor = Executor(code, self.macros, self.project_root)
        self.executor.log.connect(self.append_log)
        self.executor.progress.connect(self.on_progress)
        self.executor.finished_ok.connect(self.on_done)
        self.executor.failed.connect(self.on_fail)
        self.executor.start()

    def stop_script(self):
        if self.executor and self.executor.isRunning():
            self.executor.stop()
            self.append_log("⏹ Остановка...")

    def on_progress(self, msg: str):
        m = TRIGGER_RE["progress"].search(msg)
        if not m:
            return
        try:
            cur = float(m.group(1))
            total = float(m.group(2)) if m.group(2) else 100.0
            percent = int(min(100, cur * 100 / total if total else cur))
        except Exception:
            return

        self.progress.setValue(percent)

        if percent > self.last_progress and percent > 0:
            elapsed = time.time() - self.start_time
            total_time = elapsed / (percent / 100.0)
            eta = total_time - elapsed
            if eta > 60:
                self.eta_label.setText(f"ETA: {int(eta // 60)} мин {int(eta % 60)} сек")
            elif eta > 0:
                self.eta_label.setText(f"ETA: {int(eta)} сек")
            else:
                self.eta_label.setText("ETA: завершение...")

        self.last_progress = percent

    def on_done(self):
        self.progress.setValue(100)
        self.eta_label.setText("ETA: 0 сек")
        self.btn_go.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.append_log("✔ VIBE-скрипт завершён.")

        if self.triggers.get("debug"):
            self._run_lints()

        if self.parent_main and hasattr(self.parent_main, "_refresh_tree"):
            self.parent_main._refresh_tree()

    def on_fail(self, err: str):
        self.btn_go.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.append_log("❌ Ошибка исполнения:\n" + err)
        self.append_log("— Кнопка 'Копировать лог для ИИ' отправит этот трейс обратно нейросети.")

    def _run_lints(self):
        lints = self.triggers.get("lints") or []
        if not lints:
            self.append_log("⚠ Debug on! активен, но директив '# LINT: <lang> <path>' не найдено.")
            return

        self.append_log("--- АВТО-ЛИНТЕР ---")
        l = Linter()
        for lang, path in lints:
            path = path.strip()
            try:
                ok, msg = l.check(lang, path)
            except Exception as e:
                self.append_log(f"❌ LINT CRASH ({lang}) {path}: {e}")
                continue
            if ok:
                self.append_log(f"✅ LINT OK: {path}")
            else:
                self.append_log(f"❌ LINT FAIL ({lang}):\n{msg}")

    def append_log(self, text: str):
        self.log.append(text)
        auto = False
        if self.parent_main and hasattr(self.parent_main, "settings"):
            auto = bool(self.parent_main.settings.get("vibe_auto_scroll"))
        if auto:
            self.log.verticalScrollBar().setValue(
                self.log.verticalScrollBar().maximum()
            )

    def copy_log(self):
        QApplication.clipboard().setText(self.log.text())
        self.append_log("📋 Лог скопирован в буфер.")