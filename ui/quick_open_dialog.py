import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt

class QuickOpenDialog(QDialog):
    def __init__(self, project_root, main_window):
        super().__init__(main_window)
        self.project_root = project_root
        self.main_window = main_window
        self.setWindowTitle("Быстрый переход (Ctrl+P)")
        self.resize(600, 400)
        self.setStyleSheet("background-color: #1E1E1E; color: white;")

        layout = QVBoxLayout(self)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Начни вводить имя файла...")
        self.search_input.setStyleSheet("padding: 10px; font-size: 16px; background: #252526; border: 1px solid #444; color: #00ff88;")
        self.search_input.textChanged.connect(self.filter_files)
        layout.addWidget(self.search_input)

        self.results_list = QListWidget()
        self.results_list.setStyleSheet("background: #252526; color: #ccc; font-size: 14px; border: none;")
        self.results_list.itemDoubleClicked.connect(self.open_selected)
        layout.addWidget(self.results_list)

        self.all_files = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("snapshots", "__pycache__", ".venv")]
            for f in files:
                if not f.endswith(".pyc"):
                    self.all_files.append(os.path.join(root, f))

        self.filter_files("")

    def filter_files(self, text):
        self.results_list.clear()
        text = text.lower()
        for filepath in self.all_files:
            rel_path = os.path.relpath(filepath, self.project_root)
            if text in rel_path.lower():
                item = QListWidgetItem(rel_path)
                item.setData(Qt.ItemDataRole.UserRole, filepath)
                self.results_list.addItem(item)
        
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def open_selected(self, item):
        filepath = item.data(Qt.ItemDataRole.UserRole)
        self.main_window.open_file_and_goto(filepath, 1)
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_item = self.results_list.currentItem()
            if current_item:
                self.open_selected(current_item)
        else:
            super().keyPressEvent(event)