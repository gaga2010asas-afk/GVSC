from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt
import importlib
import pai_studio.vector_2d as v2d

class PaiRenderWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(800, 600)
        self.render_image()

    def render_image(self):
        pixmap = QPixmap(800, 600)
        pixmap.fill(QColor(20, 20, 30))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        try:
            # Перезагружаем модуль, чтобы подтянуть свежие изменения из файла
            importlib.reload(v2d)
            if hasattr(v2d, 'generate_vector_2d'):
                v2d.generate_vector_2d(painter)
        except Exception as e:
            painter.setPen(QColor(255, 0, 0))
            painter.drawText(50, 50, f"Ошибка рендера PAI:\n{str(e)}")
        finally:
            painter.end()
        
        self.setPixmap(pixmap)

class PaiStudioDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PAI Studio (Vector 2D Preview)")
        self.resize(820, 680)
        layout = QVBoxLayout(self)
        
        self.canvas = PaiRenderWidget(self)
        layout.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)
        
        btn_refresh = QPushButton("🔄 Обновить рендер (если изменил код в vector_2d.py)")
        btn_refresh.setStyleSheet("background-color: #2D2D2D; color: #00ff88; padding: 10px; font-weight: bold;")
        btn_refresh.clicked.connect(self.canvas.render_image)
        layout.addWidget(btn_refresh)