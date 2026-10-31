import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QFileDialog, QMessageBox, QSplitter, QWidget
)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt

class PaiStudioWindow(QDialog):
    def __init__(self, project_root: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PAI Studio — Редактор графики")
        self.resize(1100, 700)
        self.project_root = project_root
        
        self._build_ui()
        self.render_preview()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая часть: Код
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("Код отрисовки (Python + QPainter):"))
        self.code_editor = QTextEdit()
        self.code_editor.setStyleSheet("background-color: #1E1E1E; color: #D4D4D4; font-family: Consolas; font-size: 13px;")
        self.code_editor.setPlainText("""def generate_vector_2d(painter):
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QColor, QPen, QBrush
    
    # Твой код рисования тут:
    painter.setBrush(QBrush(QColor(0, 255, 140)))
    painter.setPen(QPen(QColor(255, 255, 255), 4))
    painter.drawEllipse(QRectF(200, 200, 400, 200))
""")
        left_layout.addWidget(self.code_editor)
        
        btn_render = QPushButton("▶ Обновить превью")
        btn_render.setStyleSheet("background-color: #2D2D2D; color: #00ff88; padding: 10px; font-weight: bold;")
        btn_render.clicked.connect(self.render_preview)
        left_layout.addWidget(btn_render)
        
        splitter.addWidget(left_widget)
        
        # Правая часть: Холст
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel("Предпросмотр (800x600):"))
        self.canvas = QLabel()
        self.canvas.setFixedSize(800, 600)
        self.canvas.setStyleSheet("background-color: #14141E; border: 1px solid #333;")
        right_layout.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)
        
        btn_save = QPushButton("💾 Сохранить как PNG в проект")
        btn_save.setStyleSheet("background-color: #00ff88; color: black; padding: 12px; font-weight: bold; font-size: 14px;")
        btn_save.clicked.connect(self.save_image)
        right_layout.addWidget(btn_save)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 800])
        layout.addWidget(splitter)

    def render_preview(self):
        pixmap = QPixmap(800, 600)
        pixmap.fill(QColor(20, 20, 30))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        code = self.code_editor.toPlainText()
        
        try:
            env = {}
            exec(code, env)
            if "generate_vector_2d" in env:
                env["generate_vector_2d"](painter)
            else:
                raise ValueError("В коде нет функции generate_vector_2d(painter)")
        except Exception as e:
            painter.setPen(QColor(255, 100, 100))
            painter.setFont(QFont("Consolas", 12))
            painter.drawText(50, 50, f"Ошибка в коде:\n{str(e)}")
        finally:
            painter.end()
            
        self.canvas.setPixmap(pixmap)

    def save_image(self):
        default_dir = os.path.join(self.project_root, "assets", "2d")
        os.makedirs(default_dir, exist_ok=True)
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Сохранить ассет", 
            os.path.join(default_dir, "new_asset.png"), 
            "PNG Images (*.png)"
        )
        
        if filepath:
            if self.canvas.pixmap():
                self.canvas.pixmap().save(filepath, "PNG")
                QMessageBox.information(self, "Успех", f"Файл успешно сохранен:\n{filepath}")