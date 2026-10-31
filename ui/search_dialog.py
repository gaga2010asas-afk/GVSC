import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QListWidget, QListWidgetItem, QLabel
)
from PyQt6.QtCore import Qt

class SearchDialog(QDialog):
    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Поиск по проекту")
        self.resize(600, 400)
        self.project_root = project_root
        self.selected_file = None
        self.selected_line = -1
        self.main_window = parent

        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите текст для поиска...")
        self.search_input.returnPressed.connect(self.perform_search)
        top_layout.addWidget(self.search_input)

        self.btn_search = QPushButton("🔍 Искать")
        self.btn_search.setStyleSheet("background-color: #00ff88; color: black; font-weight: bold; padding: 5px;")
        self.btn_search.clicked.connect(self.perform_search)
        top_layout.addWidget(self.btn_search)

        layout.addLayout(top_layout)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.go_to_result)
        layout.addWidget(self.results_list)

        self.status_label = QLabel("Введите запрос и нажмите Искать")
        layout.addWidget(self.status_label)

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        self.results_list.clear()
        self.status_label.setText("Поиск...")
        count = 0

        # Расширения файлов, которые мы не ищем (бинарники)
        skip_exts = [".exe", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".zip", ".pyc", ".dll"]

        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("snapshots", "__pycache__", ".venv", "node_modules")]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in skip_exts:
                    continue
                
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, self.project_root)
                
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            if query in line:
                                item_text = f"[{rel_path}:{line_num}] {line.strip()}"
                                item = QListWidgetItem(item_text)
                                item.setData(Qt.ItemDataRole.UserRole, (filepath, line_num))
                                self.results_list.addItem(item)
                                count += 1
                except Exception:
                    pass # Игнорируем файлы, которые не читаются как текст

        self.status_label.setText(f"Найдено совпадений: {count}")

    def go_to_result(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            filepath, line_num = data
            if self.main_window:
                self.main_window.open_file_and_goto(filepath, line_num)
                self.accept() # Закрываем диалог поиска