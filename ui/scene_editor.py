import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QGraphicsScene, QGraphicsView, QGraphicsRectItem, 
    QGraphicsTextItem, QMessageBox, QGraphicsItem
)
from PyQt6.QtGui import QBrush, QColor, QPen, QFont
from PyQt6.QtCore import Qt

class NodeItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h, node_type, text, color, font_size=12):
        super().__init__(0, 0, w, h)
        self.node_type = node_type
        self.node_name = text.replace(" ", "_")
        
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor(0, 0, 0), 2))
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setPos(x, y)
        
        self.text_item = QGraphicsTextItem(text, self)
        self.text_item.setFont(QFont("Consolas", font_size, QFont.Weight.Bold))
        self.text_item.setDefaultTextColor(QColor(0, 0, 0))
        text_rect = self.text_item.boundingRect()
        self.text_item.setPos((w - text_rect.width()) / 2, (h - text_rect.height()) / 2)

class SceneEditor(QDialog):
    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎬 Визуальный Редактор Меню (Godot UI)")
        self.project_root = project_root
        self.resize(950, 750)
        self.setStyleSheet("background-color: #1E1E1E; color: #CCCCCC;")

        layout = QVBoxLayout(self)
        
        lbl_help = QLabel("Перетаскивай элементы мышкой! Так будет выглядеть твое меню в игре.")
        lbl_help.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(lbl_help)

        top = QHBoxLayout()
        top.addWidget(QLabel("Добавить:"))
        
        btn_add_btn = QPushButton("🔲 Кнопка")
        btn_add_btn.setStyleSheet("background: #1a3b5c; color: #00d4ff; padding: 6px;")
        btn_add_btn.clicked.connect(lambda: self.add_node("Button", QColor(100, 150, 250)))
        top.addWidget(btn_add_btn)

        btn_add_lbl = QPushButton("📝 Текст")
        btn_add_lbl.setStyleSheet("background: #333; color: #eee; padding: 6px;")
        btn_add_lbl.clicked.connect(lambda: self.add_node("Label", QColor(220, 220, 220)))
        top.addWidget(btn_add_lbl)

        top.addStretch()

        btn_save = QPushButton("💾 Экспорт в .tscn (Godot)")
        btn_save.setStyleSheet("background: #004d00; color: #00ff88; padding: 6px; font-weight: bold;")
        btn_save.clicked.connect(self.save_scene)
        top.addWidget(btn_save)

        layout.addLayout(top)

        self.scene = QGraphicsScene(self)
        # Делаем фон похожим на игру (темный градиент)
        self.scene.setBackgroundBrush(QBrush(QColor(20, 20, 30)))
        self.scene.setSceneRect(0, 0, 800, 600)
        
        # Рамка экрана
        self.scene.addRect(0, 0, 800, 600, QPen(QColor(100, 100, 100), 2), QBrush(Qt.BrushStyle.NoBrush))
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(self.view.renderHints())
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setStyleSheet("border: none;")
        layout.addWidget(self.view)

        self.item_counter = 0
        
        # --- ЗАГРУЖАЕМ ШАБЛОН МЕНЮ ---
        self.generate_template()

    def generate_template(self):
        # Заголовок игры
        title = NodeItem(250, 100, 300, 60, "Label", "MY COOL GAME", QColor(0, 255, 200), font_size=24)
        title.node_name = "GameTitle"
        self.scene.addItem(title)
        
        # Кнопка Играть
        play_btn = NodeItem(300, 250, 200, 50, "Button", "PLAY", QColor(100, 200, 100))
        play_btn.node_name = "PlayButton"
        self.scene.addItem(play_btn)
        
        # Кнопка Выход
        exit_btn = NodeItem(300, 350, 200, 50, "Button", "EXIT", QColor(200, 100, 100))
        exit_btn.node_name = "ExitButton"
        self.scene.addItem(exit_btn)

        self.item_counter = 3

    def add_node(self, node_type, color):
        self.item_counter += 1
        x = 350
        y = 450 
        
        if node_type == "Button":
            text = f"Button_{self.item_counter}"
            item = NodeItem(x, y, 120, 40, "Button", text, color)
        else:
            text = f"Label_{self.item_counter}"
            item = NodeItem(x, y, 120, 30, "Label", text, color)

        self.scene.addItem(item)

    def save_scene(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Сохранить сцену", 
            os.path.join(self.project_root, "MainMenu.tscn"), 
            "Godot Scene (*.tscn)"
        )
        if not filepath: return

        tscn_content = '[gd_scene format=3]\n\n[node name="MainMenu" type="Control"]\nlayout_mode = 3\nanchors_preset = 15\noffset_right = 800.0\noffset_bottom = 600.0\n\n'
        
        for item in self.scene.items():
            if isinstance(item, NodeItem):
                pos = item.scenePos()
                w = item.rect().width()
                h = item.rect().height()
                name = item.node_name
                ntype = item.node_type
                text = item.text_item.toPlainText()
                
                tscn_content += f'[node name="{name}" type="{ntype}" parent="."]\n'
                tscn_content += f'offset_left = {pos.x()}.0\n'
                tscn_content += f'offset_top = {pos.y()}.0\n'
                tscn_content += f'offset_right = {pos.x() + w}.0\n'
                tscn_content += f'offset_bottom = {pos.y() + h}.0\n'
                tscn_content += f'text = "{text}"\n\n'

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(tscn_content)
            QMessageBox.information(self, "Успех", f"Меню сохранено!\n{filepath}\nТеперь оно выглядит точно так же, как ты его расставил.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")