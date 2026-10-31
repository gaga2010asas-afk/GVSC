import os
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QComboBox, QMessageBox
)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt

class TilemapCanvas(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_w = 20
        self.grid_h = 15
        self.tile_size = 32
        self.setFixedSize(self.grid_w * self.tile_size, self.grid_h * self.tile_size)
        self.setStyleSheet("background-color: #121212; border: 2px solid #3E3E42;")
        
        self.colors = {
            1: QColor(139, 69, 19),   # Земля
            2: QColor(105, 105, 105), # Камень
            3: QColor(30, 144, 255),  # Вода
            4: QColor(255, 69, 0),    # Лава
            5: QColor(255, 215, 0)    # Спавн игрока
        }
        
        self.map_data = [[0 for _ in range(self.grid_w)] for _ in range(self.grid_h)]
        self.current_tile = 1
        
        # --- ЗАГРУЖАЕМ КРАСИВЫЙ ШАБЛОН УРОВНЯ ---
        self.generate_default_map()

    def generate_default_map(self):
        # Заполняем стенами по краям
        for x in range(self.grid_w):
            self.map_data[0][x] = 2
            self.map_data[self.grid_h-1][x] = 2
        for y in range(self.grid_h):
            self.map_data[y][0] = 2
            self.map_data[y][self.grid_w-1] = 2
            
        # Делаем пол
        for y in range(1, self.grid_h-1):
            for x in range(1, self.grid_w-1):
                self.map_data[y][x] = 1

        # Добавляем немного декораций (вода и лава)
        self.map_data[3][4] = 3; self.map_data[3][5] = 3
        self.map_data[4][4] = 3; self.map_data[4][5] = 3
        
        self.map_data[10][15] = 4; self.map_data[10][16] = 4

        # Ставим точку спавна
        self.map_data[7][10] = 5

    def mousePressEvent(self, event):
        x = int(event.position().x() // self.tile_size)
        y = int(event.position().y() // self.tile_size)
        if 0 <= x < self.grid_w and 0 <= y < self.grid_h:
            if event.button() == Qt.MouseButton.RightButton:
                self.map_data[y][x] = 0 
            else:
                self.map_data[y][x] = self.current_tile 
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton or event.buttons() == Qt.MouseButton.RightButton:
            self.mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Рисуем сетку
        painter.setPen(QPen(QColor(50, 50, 60), 1))
        for i in range(self.grid_w + 1):
            painter.drawLine(i * self.tile_size, 0, i * self.tile_size, self.height())
        for j in range(self.grid_h + 1):
            painter.drawLine(0, j * self.tile_size, self.width(), j * self.tile_size)

        # Рисуем тайлы
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                tile_id = self.map_data[y][x]
                if tile_id > 0:
                    painter.fillRect(x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size, self.colors[tile_id])
                    painter.setPen(QPen(QColor(0,0,0, 100), 1))
                    painter.drawRect(x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size)
                    
                    # Если это спавн, рисуем смайлик игрока
                    if tile_id == 5:
                        painter.setPen(QColor(0,0,0))
                        painter.setFont(QFont("Segoe UI", 16))
                        painter.drawText(x * self.tile_size, y * self.tile_size + 24, "🙂")

class TilemapEditor(QDialog):
    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🗺 Конструктор Уровней (Tilemap)")
        self.project_root = project_root
        self.resize(850, 700)
        self.setStyleSheet("background-color: #252526; color: #CCCCCC;")

        layout = QVBoxLayout(self)
        
        # Подсказка
        lbl_help = QLabel("Нарисуй уровень мышкой! Это карта, по которой будет ходить персонаж.")
        lbl_help.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(lbl_help)

        # Панель инструментов
        top = QHBoxLayout()
        top.addWidget(QLabel("Кисть:"))
        
        self.combo = QComboBox()
        self.combo.addItem("🟫 Земля (Пол)", 1)
        self.combo.addItem("⬜ Камень (Стена)", 2)
        self.combo.addItem("🟦 Вода", 3)
        self.combo.addItem("🟥 Лава", 4)
        self.combo.addItem("🙂 Спавн (Игрок)", 5)
        self.combo.currentIndexChanged.connect(self.change_tile)
        top.addWidget(self.combo)
        
        btn_clear = QPushButton("🗑 Очистить")
        btn_clear.setStyleSheet("background: #4d0000; color: #ff5555; padding: 6px;")
        btn_clear.clicked.connect(self.clear_canvas)
        top.addWidget(btn_clear)

        btn_save = QPushButton("💾 Сохранить в JSON")
        btn_save.setStyleSheet("background: #004d00; color: #00ff88; padding: 6px; font-weight: bold;")
        btn_save.clicked.connect(self.save_map)
        top.addWidget(btn_save)
        
        layout.addLayout(top)

        self.canvas = TilemapCanvas(self)
        layout.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)

    def change_tile(self):
        self.canvas.current_tile = self.combo.currentData()

    def clear_canvas(self):
        self.canvas.map_data = [[0 for _ in range(self.canvas.grid_w)] for _ in range(self.canvas.grid_h)]
        self.canvas.update()

    def save_map(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Сохранить карту", os.path.join(self.project_root, "level.json"), "JSON Files (*.json)")
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump({
                        "width": self.canvas.grid_w, 
                        "height": self.canvas.grid_h, 
                        "data": self.canvas.map_data
                    }, f, indent=4)
                QMessageBox.information(self, "Успех", "Карта сохранена!\nТеперь ИИ может написать код, который её загрузит.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))