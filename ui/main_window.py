"""Главное окно GVSC."""
import os
import sys
import shutil
import glob
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QSplitter, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
    QFileDialog, QLineEdit, QTabWidget, QLabel, QScrollArea,
    QInputDialog, QMessageBox, QMenu, QApplication, QToolBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QProcess, QProcessEnvironment, QSize, QFileSystemWatcher, QUrl
from PyQt6.QtGui import QShortcut, QKeySequence, QColor, QFont, QTextCursor, QPixmap, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.Qsci import (
    QsciScintilla, QsciLexerPython, QsciLexerCSharp,
    QsciLexerJavaScript, QsciLexerCPP, QsciAPIs
)

from core.snapshot import SnapshotManager
from core.macros import MacrosAPI
from core.linter import Linter
from ui.vibe_extructor import VibeExtructor
from ui.search_dialog import SearchDialog
from ui.quick_open_dialog import QuickOpenDialog
from core.settings import SettingsManager
from ui.settings_dialog import SettingsDialog
# ИМПОРТ ИИ УДАЛЕН

DEFAULT_PROJECT_ROOT = os.path.abspath("projects")
SNAPSHOTS_DIR = os.path.abspath("snapshots")

HELP_TEXT = """
<h3 style='color: #00ff88;'>📖 Справка GVSC</h3>
<p style='color: #ccc;'>Кнопки и их назначение:</p>
<h4 style='color: #00d4ff;'>🤖 ИИ и Код</h4>
<ul>
    <li><b>⚡ VIBE (F6)</b> — Окно для скриптов ИИ.</li>
    <li><b>🔍 Поиск</b> — Глобальный поиск.</li>
    <li><b>Ctrl+P</b> — Быстрый переход к файлу.</li>
</ul>
<h4 style='color: #ffcc00;'>📦 Создание</h4>
<ul>
    <li><b>📦 Создать</b> — Каркас проекта.</li>
    <li><b>🗺 Тайлмап</b> — 2D-редактор уровней.</li>
    <li><b>🎬 Редактор сцен</b> — Визуальный UI.</li>
</ul>
<h4 style='color: #ff55ff;'>🛡️ Безопасность</h4>
<ul>
    <li><b>📸 Снапшот</b> — Бэкап проекта.</li>
    <li><b>🔄 Откатить</b> — Откат из бэкапа.</li>
</ul>
"""


class AudioPlayerWidget(QWidget):
    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        layout = QVBoxLayout(self)

        lbl = QLabel(f"🎵 Аудиофайл: {os.path.basename(filepath)}")
        lbl.setStyleSheet("font-size: 18px; color: #00ffcc; font-weight: bold;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        layout.addStretch()

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(filepath))

        btn_layout = QHBoxLayout()
        btn_play = QPushButton("▶ Воспроизвести")
        btn_play.setStyleSheet("background: #004d00; color: #00ff88; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_play.clicked.connect(self.player.play)

        btn_stop = QPushButton("⏹ Стоп")
        btn_stop.setStyleSheet("background: #4d0000; color: #ff5555; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_stop.clicked.connect(self.player.stop)

        btn_layout.addWidget(btn_play)
        btn_layout.addWidget(btn_stop)
        layout.addLayout(btn_layout)
        layout.addStretch()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gaga Vibe Studio Code (GVSC)")
        self.resize(1280, 800)

        self.settings = SettingsManager()
        self.locale = self.settings.load_locale()

        saved_project = self.settings.get("last_project")
        if saved_project and os.path.exists(saved_project):
            self.current_project = saved_project
        else:
            self.current_project = DEFAULT_PROJECT_ROOT

        os.makedirs(self.current_project, exist_ok=True)

        self.snapshot = SnapshotManager(self.current_project, SNAPSHOTS_DIR)
        self.linter = Linter()
        self.macros = MacrosAPI(self.current_project, self.snapshot, self.linter)

        self.term_process = QProcess(self)
        self.term_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        self.term_process.setProcessEnvironment(env)
        self.term_process.readyReadStandardOutput.connect(self.read_term_stdout)
        self.term_process.finished.connect(self.term_finished)

        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self._on_dir_changed)

        self._build_ui()
        self._refresh_tree()
        self._setup_watcher()

        self.setWindowTitle(f"GVSC - {os.path.basename(self.current_project)}")

    def _setup_watcher(self):
        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())
        for root, dirs, _ in os.walk(self.current_project):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("snapshots", "__pycache__", ".venv")]
            if root not in self.watcher.directories():
                self.watcher.addPath(root)

    def _on_dir_changed(self, path):
        self._refresh_tree()
        self._setup_watcher()

    def closeEvent(self, event):
        if self.term_process.state() == QProcess.ProcessState.Running:
            self.term_process.kill()
            self.term_process.waitForFinished()
        event.accept()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        logo_path = os.path.join("assets", "ui", "GVSC.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        # --- ПАНЕЛЬ ИНСТРУМЕНТОВ ---
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setStyleSheet("""
            QToolBar { background-color: #252526; border-bottom: 1px solid #3E3E42; padding: 2px; spacing: 3px; }
            QPushButton { background-color: transparent; color: #CCCCCC; border: none; padding: 6px 12px; border-radius: 4px; font-size: 13px; }
            QPushButton:hover { background-color: #3E3E42; color: #FFFFFF; }
            QPushButton:pressed { background-color: #007ACC; color: #FFFFFF; }
        """)
        self.addToolBar(toolbar)

        def add_toolbar_btn(text, slot):
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)

        add_toolbar_btn("⚡ VIBE (F6)", self.open_vibe)
        # Кнопка ИИ УДАЛЕНА
        add_toolbar_btn("🔍 Поиск", self.open_search)
        add_toolbar_btn("📦 Создать", self.scaffold_project)
        add_toolbar_btn("🗺 Тайлмап", self.open_tilemap_editor)
        add_toolbar_btn("🎬 Редактор сцен", self.open_scene_editor)
        add_toolbar_btn("▶ Запустить Godot", self.launch_godot)
        add_toolbar_btn("📦 Собрать в EXE", self.build_exe)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        add_toolbar_btn("📸 Снапшот", self.save_snapshot)
        add_toolbar_btn("🔄 Откатить", self.load_snapshot)
        add_toolbar_btn("📂 Открыть", self.open_folder)
        add_toolbar_btn("💾 Сохранить", self.save_current_file)
        add_toolbar_btn("⚙ Настройки", self.open_settings)

        # --- РАБОЧАЯ ОБЛАСТЬ ---
        split = QSplitter(Qt.Orientation.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Проводник")
        self.tree.itemClicked.connect(self.on_tree_click)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_tree_menu)
        split.addWidget(self.tree)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        split.addWidget(self.tabs)

        # --- ПРАВАЯ ПАНЕЛЬ ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(8)

        self.btn_run_side = QPushButton("▶ ЗАПУСТИТЬ ФАЙЛ\n(Ctrl+R)")
        self.btn_run_side.setStyleSheet("""
            QPushButton {
                background-color: #004d00;
                color: #00ff88;
                border: 2px solid #00ff88;
                border-radius: 6px;
                padding: 15px;
                font-weight: bold;
                font-size: 15px;
                font-family: Consolas;
            }
            QPushButton:hover { background-color: #006600; color: #FFFFFF; }
            QPushButton:disabled { background-color: #333; color: #666; border-color: #444; }
        """)
        self.btn_run_side.clicked.connect(self.run_current_file)
        right_layout.addWidget(self.btn_run_side)

        self.btn_copy_context = QPushButton("🤖 Контекст (Дерево)")
        self.btn_copy_context.setStyleSheet("background-color: #1a3b5c; color: #00d4ff; border-radius: 3px; padding: 10px; font-weight: bold;")
        self.btn_copy_context.clicked.connect(self.copy_ai_context)
        right_layout.addWidget(self.btn_copy_context)

        self.instructions = QTextEdit()
        self.instructions.setReadOnly(True)
        self.instructions.setHtml(HELP_TEXT)
        self.instructions.setStyleSheet("background-color: #1E1E1E; border: none; font-family: Segoe UI;")
        right_layout.addWidget(self.instructions)

        right_layout.addStretch()
        right_panel.setMaximumWidth(240)
        split.addWidget(right_panel)

        split.setSizes([250, 800, 240])
        root.addWidget(split)

        # --- ТЕРМИНАЛ ---
        term_layout = QVBoxLayout()
        term_layout.setContentsMargins(0, 0, 0, 0)
        term_layout.setSpacing(0)

        self.term_output = QTextEdit()
        self.term_output.setReadOnly(True)
        self.term_output.setStyleSheet("background-color:#1E1E1E; color:#d4d4d4; font-family:Consolas; border: none; border-top: 1px solid #3E3E42;")

        self.term_input = QLineEdit()
        self.term_input.setPlaceholderText("Введите команду или ответ для запущенного скрипта...")
        self.term_input.setStyleSheet("background-color:#252526; color:#00ff88; font-family:Consolas; padding: 5px; border: none; border-top: 1px solid #3E3E42;")
        self.term_input.returnPressed.connect(self.execute_terminal_command)

        term_layout.addWidget(self.term_output)
        term_layout.addWidget(self.term_input)

        term_widget = QWidget()
        term_widget.setLayout(term_layout)
        term_widget.setMaximumHeight(200)
        root.addWidget(term_widget)

        # --- ПАНЕЛЬ ИИ (DOCK) ПОЛНОСТЬЮ УДАЛЕНА ---

        QShortcut(QKeySequence("F6"), self, activated=self.open_vibe)
        # QShortcut ИИ УДАЛЕН
        QShortcut(QKeySequence("Ctrl+Shift+F"), self, activated=self.open_search)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_current_file)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.run_current_file)
        QShortcut(QKeySequence("Ctrl+P"), self, activated=self.open_quick_open)

    # ================== МЕТОДЫ ИИ УДАЛЕНЫ ==================

    # ================== ИНСТРУМЕНТЫ ==================
    def launch_godot(self):
        if not shutil.which("godot"):
            self.term_output.append("<span style='color:#ff5555;'>❌ Godot не найден в PATH.</span>")
            return
        self.term_output.append("🚀 Запуск Godot...")
        self.execute_terminal_command(f'godot -e --path "{self.current_project}"')

    def build_exe(self):
        self.term_output.append("📦 Сборка EXE (PyInstaller)...")
        cmd = f"{sys.executable} -m PyInstaller --noconsole --onefile main.py"
        self.execute_terminal_command(cmd)

    def open_quick_open(self):
        dlg = QuickOpenDialog(self.current_project, self)
        dlg.exec()

    def open_tilemap_editor(self):
        from ui.tilemap_editor import TilemapEditor
        dlg = TilemapEditor(self.current_project, self)
        dlg.exec()

    def open_scene_editor(self):
        from ui.scene_editor import SceneEditor
        dlg = SceneEditor(self.current_project, self)
        dlg.exec()

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self.locale, self)
        dlg.exec()

    def open_search(self):
        dlg = SearchDialog(self.current_project, self)
        dlg.exec()
    # =================================================

    def get_file_icon(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".py": return "🐍"
        elif ext in (".cpp", ".c", ".h", ".hpp"): return "⚙️"
        elif ext == ".cs": return "🎮"
        elif ext in (".js", ".ts"): return "🌐"
        elif ext == ".gd": return "👾"
        elif ext in (".png", ".jpg", ".jpeg", ".bmp"): return "🖼️"
        elif ext in (".wav", ".mp3", ".ogg"): return "🎵"
        elif ext in (".md", ".txt"): return "📝"
        elif ext == ".json": return "⚙️"
        elif ext == ".exe": return "🚀"
        else: return "📄"

    def scaffold_project(self):
        engines = ["Godot 4", "Unity", "Python", "Web"]
        engine, ok = QInputDialog.getItem(self, "Новый проект", "Выберите движок/платформу:", engines, 0, False)
        if not ok: return
        name, ok = QInputDialog.getText(self, "Новый проект", "Введите название папки проекта:")
        if not ok or not name.strip(): return

        name = name.strip()
        project_path = os.path.join(self.current_project, name)

        if os.path.exists(project_path):
            QMessageBox.warning(self, "Ошибка", "Папка с таким именем уже существует!")
            return

        try:
            os.makedirs(project_path, exist_ok=True)
            if engine == "Python":
                os.makedirs(os.path.join(project_path, "src"), exist_ok=True)
                os.makedirs(os.path.join(project_path, "assets"), exist_ok=True)
                os.makedirs(os.path.join(project_path, "data"), exist_ok=True)
                with open(os.path.join(project_path, "main.py"), "w", encoding="utf-8") as f:
                    f.write('def main():\n    print("Hello GVSC!")\n\nif __name__ == "__main__":\n    main()\n')
            elif engine == "Godot 4":
                os.makedirs(os.path.join(project_path, "scripts"), exist_ok=True)
                os.makedirs(os.path.join(project_path, "scenes"), exist_ok=True)
                os.makedirs(os.path.join(project_path, "assets/2d"), exist_ok=True)
                os.makedirs(os.path.join(project_path, "assets/audio"), exist_ok=True)
                with open(os.path.join(project_path, "project.godot"), "w", encoding="utf-8") as f:
                    f.write(f'config_version=4\n\n[application]\nconfig/name="{name}"\nrun/main_scene="res://scenes/main.tscn"\n')
                with open(os.path.join(project_path, "scenes/main.tscn"), "w", encoding="utf-8") as f:
                    f.write('[gd_scene format=3]\n\n[node name="Main" type="Node2D"]\n')
                with open(os.path.join(project_path, "scripts/player.gd"), "w", encoding="utf-8") as f:
                    f.write('extends CharacterBody2D\n\nfunc _ready():\n\tprint("Player ready!")\n')
            elif engine == "Unity":
                os.makedirs(os.path.join(project_path, "Assets/Scripts"), exist_ok=True)
                os.makedirs(os.path.join(project_path, "Assets/Prefabs"), exist_ok=True)
                os.makedirs(os.path.join(project_path, "Assets/Textures"), exist_ok=True)
                os.makedirs(os.path.join(project_path, "Assets/Audio"), exist_ok=True)
                with open(os.path.join(project_path, "Assets/Scripts/Player.cs"), "w", encoding="utf-8") as f:
                    f.write('using UnityEngine;\n\npublic class Player : MonoBehaviour {\n    void Start() {\n        Debug.Log("Player started!");\n    }\n}\n')
            elif engine == "Web":
                os.makedirs(os.path.join(project_path, "css"), exist_ok=True)
                os.makedirs(os.path.join(project_path, "js"), exist_ok=True)
                os.makedirs(os.path.join(project_path, "assets"), exist_ok=True)
                with open(os.path.join(project_path, "index.html"), "w", encoding="utf-8") as f:
                    f.write('<!DOCTYPE html>\n<html>\n<head>\n    <title>My Game</title>\n</head>\n<body>\n    <h1>Hello GVSC!</h1>\n</body>\n</html>\n')

            self.term_output.append(f"📦 Проект '{name}' ({engine}) успешно создан!")
            self._refresh_tree()
        except Exception as e:
            self.term_output.append(f"❌ Ошибка создания проекта: {e}")

    def copy_ai_context(self):
        tree_str = f"Project: {os.path.basename(self.current_project)}\n"
        for root, dirs, files in os.walk(self.current_project):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("snapshots", "__pycache__", ".venv")]
            rel_path = os.path.relpath(root, self.current_project)

            if rel_path != ".":
                indent = "  " * rel_path.count(os.sep)
                tree_str += f"{indent}📁 {os.path.basename(root)}/\n"
            else:
                indent = ""

            for f in files:
                if not f.endswith(".pyc"):
                    icon = self.get_file_icon(f)
                    tree_str += f"{indent}  {icon} {f}\n"

        QApplication.clipboard().setText(tree_str)
        self.term_output.append("🤖 Дерево проекта скопировано! Вставь его ИИ.")

    def open_tree_menu(self, position):
        menu = QMenu()
        action_new_file = menu.addAction("📄 Создать файл")
        action_new_folder = menu.addAction("📁 Создать папку")
        menu.addSeparator()
        action_rename = menu.addAction("✏ Переименовать")
        action_delete = menu.addAction("🗑 Удалить")

        item = self.tree.itemAt(position)
        target_path = self.current_project
        if item:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data: target_path = data

        action = menu.exec(self.tree.viewport().mapToGlobal(position))

        if action == action_new_file: self.create_new_file(target_path)
        elif action == action_new_folder: self.create_new_folder(target_path)
        elif action == action_rename and item: self.rename_item(item, target_path)
        elif action == action_delete and item: self.delete_item(target_path)

    def create_new_file(self, base_path):
        if not os.path.isdir(base_path): base_path = os.path.dirname(base_path)
        name, ok = QInputDialog.getText(self, "Новый файл", "Имя файла (с расширением):")
        if ok and name:
            filepath = os.path.join(base_path, name)
            if os.path.exists(filepath):
                QMessageBox.warning(self, "Ошибка", "Файл уже существует!")
                return
            try:
                with open(filepath, "w", encoding="utf-8") as f: f.write("")
                self.term_output.append(f"📄 Создан файл: {name}")
                self._refresh_tree()
            except Exception as e: self.term_output.append(f"❌ Ошибка: {e}")

    def create_new_folder(self, base_path):
        if not os.path.isdir(base_path): base_path = os.path.dirname(base_path)
        name, ok = QInputDialog.getText(self, "Новая папка", "Имя папки:")
        if ok and name:
            folderpath = os.path.join(base_path, name)
            if os.path.exists(folderpath):
                QMessageBox.warning(self, "Ошибка", "Папка уже существует!")
                return
            try:
                os.makedirs(folderpath, exist_ok=True)
                self.term_output.append(f"📁 Создана папка: {name}")
                self._refresh_tree()
            except Exception as e: self.term_output.append(f"❌ Ошибка: {e}")

    def rename_item(self, item, path):
        old_name = os.path.basename(path)
        name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя:", text=old_name)
        if ok and name and name != old_name:
            new_path = os.path.join(os.path.dirname(path), name)
            try:
                os.rename(path, new_path)
                self.term_output.append(f"✏ Переименовано: {old_name} -> {name}")
                self._refresh_tree()
            except Exception as e: self.term_output.append(f"❌ Ошибка: {e}")

    def delete_item(self, path):
        if not path or path == self.current_project: return
        name = os.path.basename(path)
        confirm = QMessageBox.question(self, "Удаление", f"Удалить '{name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                if os.path.isdir(path): shutil.rmtree(path)
                else: os.remove(path)
                self.term_output.append(f"🗑 Удалено: {name}")
                self._refresh_tree()
            except Exception as e: self.term_output.append(f"❌ Ошибка: {e}")

    def _create_editor(self, filepath, content):
        editor = QsciScintilla()
        font_size = self.settings.get("font_size")
        font = QFont("Consolas", font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        editor.setFont(font)
        editor.setUtf8(True)
        editor.setMarginsFont(font)
        editor.setMarginWidth(0, "0000")
        editor.setMarginLineNumbers(0, True)
        editor.setMarginsBackgroundColor(QColor("#1E1E1E"))
        editor.setMarginsForegroundColor(QColor("#858585"))
        editor.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        editor.setCaretLineVisible(True)
        editor.setCaretLineBackgroundColor(QColor("#2A2D2E"))
        editor.setPaper(QColor("#1E1E1E"))
        editor.setColor(QColor("#D4D4D4"))
        editor.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        editor.setIndentationsUseTabs(False)
        editor.setTabWidth(4)
        editor.setText(content)

        editor.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        editor.setAutoCompletionThreshold(2)

        # Живой линтер
        editor.markerDefine(QsciScintilla.MarkerSymbol.Rectangle, 0)
        editor.setMarkerBackgroundColor(QColor("red"), 0)
        timer = QTimer(editor)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda ed=editor: self._check_syntax(ed))
        editor.setProperty("lint_timer", timer)
        editor.textChanged.connect(lambda ed=editor: ed.property("lint_timer").start(1000))

        ext = os.path.splitext(filepath)[1].lower()
        lexer = None
        if ext == ".py": lexer = QsciLexerPython(editor)
        elif ext == ".cs": lexer = QsciLexerCSharp(editor)
        elif ext in (".cpp", ".c", ".h", ".hpp"): lexer = QsciLexerCPP(editor)
        elif ext in (".gd", ".js", ".ts"): lexer = QsciLexerJavaScript(editor)

        if lexer:
            lexer.setDefaultFont(font)
            lexer.setDefaultPaper(QColor("#1E1E1E"))
            lexer.setDefaultColor(QColor("#D4D4D4"))
            for i in range(128): lexer.setFont(font, i)
            if ext == ".py":
                lexer.setColor(QColor("#569CD6"), QsciLexerPython.Keyword)
                lexer.setColor(QColor("#CE9178"), QsciLexerPython.DoubleQuotedString)
                lexer.setColor(QColor("#6A9955"), QsciLexerPython.Comment)
            elif ext in (".cs", ".cpp", ".c", ".h", ".hpp"):
                lexer.setColor(QColor("#569CD6"), QsciLexerCSharp.Keyword)
                lexer.setColor(QColor("#CE9178"), QsciLexerCSharp.DoubleQuotedString)
                lexer.setColor(QColor("#6A9955"), QsciLexerCSharp.Comment)
                if ext in (".cpp", ".c", ".h", ".hpp"):
                    lexer.setColor(QColor("#569CD6"), QsciLexerCPP.Keyword)
                    lexer.setColor(QColor("#CE9178"), QsciLexerCPP.DoubleQuotedString)
                    lexer.setColor(QColor("#6A9955"), QsciLexerCPP.Comment)
            editor.setLexer(lexer)
            editor.setMarginsBackgroundColor(QColor("#1E1E1E"))
            editor.setMarginsForegroundColor(QColor("#858585"))

            api = QsciAPIs(lexer)
            for word in ["print", "def", "class", "import", "from", "return", "if", "else", "elif", "for", "while", "try", "except", "True", "False", "None"]:
                api.add(word)
            api.prepare()

        editor.setProperty("filepath", filepath)
        try: editor.setProperty("last_loaded_mtime", os.path.getmtime(filepath))
        except: pass
        return editor

    def _check_syntax(self, editor):
        filepath = editor.property("filepath")
        if not filepath or not os.path.exists(filepath): return

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in (".py", ".gd"): return

        temp_path = filepath + ".tmp_lint"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(editor.text())

        lang = "python" if ext == ".py" else "gdscript"
        ok, errors = self.linter.check(lang, temp_path)

        editor.markerDeleteAll(0)

        if not ok:
            for line, msg in errors:
                if line > 0:
                    editor.markerAdd(line - 1, 0)
                    self.term_output.append(f"<span style='color:#ff5555;'>🔴 Linter: строка {line} — {str(msg).splitlines()[0]}</span>")

        if os.path.exists(temp_path):
            os.remove(temp_path)

    def _refresh_tree(self):
        selected_path = None
        if self.tree.currentItem():
            selected_path = self.tree.currentItem().data(0, Qt.ItemDataRole.UserRole)

        expanded_paths = set()
        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            if it.value().isExpanded():
                expanded_paths.add(it.value().data(0, Qt.ItemDataRole.UserRole))
            it += 1

        show_hidden = self.settings.get("show_hidden")

        self.tree.blockSignals(True)
        self.tree.clear()
        base = QTreeWidgetItem(self.tree, [os.path.basename(self.current_project) or "Проект"])
        base.setData(0, Qt.ItemDataRole.UserRole, self.current_project)

        for root, dirs, files in os.walk(self.current_project):
            if show_hidden:
                dirs[:] = [d for d in dirs if d not in ("snapshots", "__pycache__")]
            else:
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("snapshots", "__pycache__", ".venv")]

            rel_path = os.path.relpath(root, self.current_project)

            if rel_path == ".": parent = base
            else:
                parts = rel_path.split(os.sep)
                parent = self._find_item(base, parts)

            for d in dirs:
                item = QTreeWidgetItem(parent, [f"📁 {d}"])
                item.setData(0, Qt.ItemDataRole.UserRole, os.path.join(root, d))
            for f in files:
                if not f.endswith(".pyc"):
                    icon = self.get_file_icon(f)
                    item = QTreeWidgetItem(parent, [f"{icon} {f}"])
                    item.setData(0, Qt.ItemDataRole.UserRole, os.path.join(root, f))

        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            path = it.value().data(0, Qt.ItemDataRole.UserRole)
            if path in expanded_paths: it.value().setExpanded(True)
            if path == selected_path: self.tree.setCurrentItem(it.value())
            it += 1
        self.tree.blockSignals(False)

    def _find_item(self, root_item, parts):
        cur = root_item
        for p in parts:
            for i in range(cur.childCount()):
                ch = cur.child(i)
                if ch.text(0) == f"📁 {p}":
                    cur = ch
                    break
        return cur

    def on_tree_click(self, item, column):
        filepath = item.data(0, Qt.ItemDataRole.UserRole)
        if not filepath or not os.path.isfile(filepath): return

        for i in range(self.tabs.count()):
            if self.tabs.widget(i).property("filepath") == filepath:
                self.tabs.setCurrentIndex(i)
                editor = self.tabs.widget(i)
                try:
                    disk_mtime = os.path.getmtime(filepath)
                    if disk_mtime > editor.property("last_loaded_mtime"):
                        with open(filepath, "r", encoding="utf-8") as f: content = f.read()
                        editor.setText(content)
                        editor.setProperty("last_loaded_mtime", disk_mtime)
                        self.term_output.append(f"🔄 Файл {os.path.basename(filepath)} обновлен с диска.")
                except: pass
                return

        ext = os.path.splitext(filepath)[1].lower()

        if ext in [".wav", ".mp3", ".ogg"]:
            player = AudioPlayerWidget(filepath)
            player.setProperty("filepath", filepath)
            idx = self.tabs.addTab(player, os.path.basename(filepath))
            self.tabs.setCurrentIndex(idx)
            return

        if ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                if pixmap.width() > 1000 or pixmap.height() > 800:
                    pixmap = pixmap.scaled(1000, 800, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(pixmap)
            else: label.setText("❌ Не удалось загрузить изображение")
            label.setProperty("filepath", filepath)
            scroll = QScrollArea()
            scroll.setWidget(label)
            scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll.setWidgetResizable(True)
            scroll.setProperty("filepath", filepath)
            idx = self.tabs.addTab(scroll, os.path.basename(filepath))
            self.tabs.setCurrentIndex(idx)
            return

        valid_exts = [".py", ".cpp", ".c", ".h", ".hpp", ".cs", ".js", ".ts", ".gd", ".txt", ".md", ".json", ".xml", ".html", ".css", ".tscn", ".godot"]
        if ext in valid_exts:
            try:
                with open(filepath, "r", encoding="utf-8") as f: content = f.read()
                if content.count('\n') > 1000:
                    self.term_output.append(f"⚠️ <span style='color:#e5c07b;'>Файл {os.path.basename(filepath)} очень большой (>1000 строк). Не отправляй его ИИ целиком!</span>")
                editor = self._create_editor(filepath, content)
                idx = self.tabs.addTab(editor, os.path.basename(filepath))
                self.tabs.setCurrentIndex(idx)
            except Exception as e: self.term_output.append(f"❌ Ошибка чтения: {e}")
        else:
            self.term_output.append(f"<span style='color:#ff5555;'>⚠ Файл {os.path.basename(filepath)} не поддерживается.</span>")

    def close_tab(self, index): self.tabs.removeTab(index)

    def on_tab_changed(self, index):
        if index == -1: self.setWindowTitle("Gaga Vibe Studio Code (GVSC)")
        else:
            filepath = self.tabs.widget(index).property("filepath")
            if filepath: self.setWindowTitle(f"GVSC - {os.path.basename(filepath)}")

    def save_current_file(self):
        widget = self.tabs.currentWidget()
        if not widget: return
        filepath = widget.property("filepath")
        if not filepath: return
        if isinstance(widget, QsciScintilla):
            try:
                with open(filepath, "w", encoding="utf-8") as f: f.write(widget.text())
                widget.setProperty("last_loaded_mtime", os.path.getmtime(filepath))
                self.term_output.append(f"💾 Сохранено: {os.path.basename(filepath)}")
            except Exception as e: self.term_output.append(f"❌ Ошибка сохранения: {e}")

    def stop_process(self):
        if self.term_process.state() == QProcess.ProcessState.Running:
            self.term_process.kill()
            self.term_output.append("<span style='color:#ff5555;'>🛑 Процесс принудительно остановлен.</span>")

    def execute_terminal_command(self, cmd=None, working_dir=None):
        if not cmd:
            cmd = self.term_input.text().strip()
            working_dir = self.current_project

        if not cmd: return
        self.term_input.clear()

        if working_dir is None:
            working_dir = self.current_project

        if self.term_process.state() == QProcess.ProcessState.Running:
            self.term_output.moveCursor(QTextCursor.MoveOperation.End)
            self.term_output.insertPlainText(f"\n{cmd}\n")
            self.term_process.write((cmd + "\n").encode('utf-8'))
        else:
            self.term_output.moveCursor(QTextCursor.MoveOperation.End)
            self.term_output.insertHtml(f"<br><span style='color:#00ff88;'>PS {os.path.basename(working_dir)}> {cmd}</span><br>")
            self.term_process.setWorkingDirectory(working_dir)
            ps_cmd = f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; {cmd}"
            self.term_process.start("powershell", ["-Command", ps_cmd])
            self.btn_run_side.setEnabled(False)
            self.btn_run_side.setText("🛑 РАБОТАЕТ...")
            self.btn_run_side.setStyleSheet("""
                QPushButton {
                    background-color: #4d0000;
                    color: #ff5555;
                    border: 2px solid #ff5555;
                    border-radius: 6px;
                    padding: 15px;
                    font-weight: bold;
                    font-size: 15px;
                    font-family: Consolas;
                }
            """)

    def read_term_stdout(self):
        data = self.term_process.readAllStandardOutput().data()
        if data:
            try: text = data.decode('utf-8')
            except UnicodeDecodeError: text = data.decode('cp866', errors='replace')
            text = text.replace('\r', '')
            self.term_output.moveCursor(QTextCursor.MoveOperation.End)
            self.term_output.insertPlainText(text)
            if not text.endswith('\n'): self.term_output.insertPlainText('\n')
            self.term_output.ensureCursorVisible()

    def term_finished(self):
        self.term_output.append("<span style='color:#888;'>--- Процесс завершен ---</span>")
        self.btn_run_side.setEnabled(True)
        self.btn_run_side.setText("▶ ЗАПУСТИТЬ ФАЙЛ\n(Ctrl+R)")
        self.btn_run_side.setStyleSheet("""
            QPushButton {
                background-color: #004d00;
                color: #00ff88;
                border: 2px solid #00ff88;
                border-radius: 6px;
                padding: 15px;
                font-weight: bold;
                font-size: 15px;
                font-family: Consolas;
            }
            QPushButton:hover { background-color: #006600; color: #FFFFFF; }
        """)

    def save_snapshot(self):
        text, ok = QInputDialog.getText(self, "Снапшот", "Имя снапшота (SAVEcode):")
        if ok and text.strip():
            try:
                self.snapshot.save(text.strip())
                self.term_output.append(f"📸 Снапшот сохранен: {text.strip()}")
            except Exception as e: self.term_output.append(f"❌ Ошибка снапшота: {e}")

    def load_snapshot(self):
        snaps = self.snapshot.list()
        if not snaps:
            self.term_output.append("⚠ Нет доступных снапшотов.")
            return
        item, ok = QInputDialog.getItem(self, "Восстановление", "Откатить к снапшоту:", snaps, 0, False)
        if ok and item:
            confirm = QMessageBox.question(self, "Подтверждение", f"Откатить проект к '{item}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                if self.snapshot.restore(item):
                    self.term_output.append(f"🔄 Проект откачен к: {item}")
                    self._refresh_tree()
                else: self.term_output.append(f"❌ Не удалось восстановить.")

    # --- НОВЫЙ МЕТОД ДЛЯ VIBE UPcode ---
    def restore_snapshot(self, name):
        """Вызывается из VIBE Extructor при триггере UPcode"""
        if self.snapshot.restore(name):
            self.term_output.append(f"🔄 VIBE: Проект откачен к снапшоту: {name}")
            self._refresh_tree()
        else:
            self.term_output.append(f"❌ VIBE: Не удалось восстановить снапшот: {name}")

    def _find_tool(self, tool_name, paths):
        p = shutil.which(tool_name)
        if p: return p
        for path in paths:
            if os.path.exists(path): return path
        return None

    def run_current_file(self):
        widget = self.tabs.currentWidget()
        if not widget or not isinstance(widget, QsciScintilla):
            self.term_output.append("⚠ Откройте файл с кодом для запуска!")
            return

        filepath = widget.property("filepath")
        if not filepath or not os.path.exists(filepath):
            return

        disk_mtime = os.path.getmtime(filepath)
        editor_mtime = widget.property("last_loaded_mtime")

        if editor_mtime is None or disk_mtime > editor_mtime + 0.1:
            try:
                with open(filepath, "r", encoding="utf-8") as f: new_content = f.read()
                widget.setText(new_content)
                widget.setProperty("last_loaded_mtime", disk_mtime)
                self.term_output.append(f"🔄 Обнаружено обновление от ИИ. Загружена свежая версия {os.path.basename(filepath)}.")
            except Exception as e:
                self.term_output.append(f"❌ Ошибка обновления: {e}")
        else:
            self.save_current_file()
            widget.setProperty("last_loaded_mtime", os.path.getmtime(filepath))

        working_dir = os.path.dirname(filepath)
        ext = os.path.splitext(filepath)[1].lower()
        filename = os.path.basename(filepath)
        cmd = ""

        if ext == ".py": cmd = f"python {filename}"
        elif ext == ".js":
            if not shutil.which("node"):
                self.term_output.append("<span style='color:#ff5555;'>❌ Node.js не найден.</span>")
                return
            cmd = f"node {filename}"
        elif ext in (".cpp", ".c"):
            gpp = self._find_tool("g++", [r"C:\msys64\ucrt64\bin\g++.exe", r"C:\msys64\mingw64\bin\g++.exe", r"C:\Program Files\WinLibs\mingw64\bin\g++.exe", r"C:\TDM-GCC-64\bin\g++.exe"])
            if not gpp:
                user_profile = os.path.expanduser("~")
                winget_pattern = os.path.join(user_profile, r"AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs*\**\bin\g++.exe")
                found = glob.glob(winget_pattern, recursive=True)
                if found: gpp = found[0]
            if gpp: cmd = f'& "{gpp}" {filename} -o out.exe; .\\out.exe'
            else:
                self.term_output.append("<span style='color:#ff5555;'>❌ MinGW не найден.</span>")
                return
        elif ext == ".cs":
            user_profile = os.path.expanduser("~")
            ds_path = os.path.join(user_profile, r".dotnet\tools\dotnet-script.exe")
            if os.path.exists(ds_path): cmd = f'& "{ds_path}" {filename}'
            else:
                dotnet = self._find_tool("dotnet", [r"C:\Program Files\dotnet\dotnet.exe"])
                if dotnet: cmd = f'& "{dotnet}" script {filename}'
                else:
                    self.term_output.append("<span style='color:#ff5555;'>❌ .NET SDK не найден.</span>")
                    return
        elif ext == ".gd":
            if not shutil.which("godot"):
                self.term_output.append("<span style='color:#ff5555;'>❌ Godot не найден в PATH.</span>")
                return
            cmd = f"godot --headless {filename}"
        else:
            self.term_output.append(f"⚠ Запуск {ext} не поддерживается.")
            return

        self.execute_terminal_command(cmd, working_dir)

    def open_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Выбери папку проекта")
        if path:
            self.current_project = path
            self.settings.set("last_project", path)

            self.snapshot = SnapshotManager(self.current_project, SNAPSHOTS_DIR)
            self.macros = MacrosAPI(self.current_project, self.snapshot, self.linter)
            self._refresh_tree()
            self._setup_watcher()
            self.term_output.append(f"📂 Открыт проект: {path}")
            self.setWindowTitle(f"GVSC - {os.path.basename(path)}")

    def open_vibe(self):
        dlg = VibeExtructor(self.macros, self.current_project, self)
        dlg.exec()