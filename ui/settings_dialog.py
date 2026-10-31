from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, 
    QMessageBox, QTabWidget, QWidget, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, settings_manager, locale, parent=None):
        super().__init__(parent)
        self.settings = settings_manager
        self.locale = locale
        self.setWindowTitle(self.locale.get("settings_title", "Настройки GVSC"))
        self.resize(450, 350)

        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # --- Вкладка: Общие ---
        tab_general = QWidget()
        layout_gen = QVBoxLayout(tab_general)
        
        lbl_lang = QLabel(self.locale.get("language", "Язык интерфейса"))
        layout_gen.addWidget(lbl_lang)

        self.combo_lang = QComboBox()
        self.combo_lang.addItem("Русский", "ru")
        self.combo_lang.addItem("English", "en")
        current_lang = self.settings.get("language")
        idx = self.combo_lang.findData(current_lang)
        if idx >= 0: self.combo_lang.setCurrentIndex(idx)
        layout_gen.addWidget(self.combo_lang)
        
        self.chk_hidden = QCheckBox(self.locale.get("show_hidden", "Показывать скрытые файлы"))
        self.chk_hidden.setChecked(self.settings.get("show_hidden"))
        layout_gen.addWidget(self.chk_hidden)
        
        layout_gen.addStretch()
        self.tabs.addTab(tab_general, self.locale.get("tab_general", "Общие"))

        # --- Вкладка: Редактор ---
        tab_editor = QWidget()
        layout_ed = QVBoxLayout(tab_editor)
        
        lbl_font = QLabel(self.locale.get("font_size", "Размер шрифта"))
        layout_ed.addWidget(lbl_font)
        
        self.spin_font = QSpinBox()
        self.spin_font.setRange(10, 24)
        self.spin_font.setValue(self.settings.get("font_size"))
        layout_ed.addWidget(self.spin_font)
        
        self.chk_auto_save = QCheckBox(self.locale.get("auto_save", "Автосохранение при переключении вкладок"))
        self.chk_auto_save.setChecked(self.settings.get("auto_save"))
        layout_ed.addWidget(self.chk_auto_save)
        
        layout_ed.addStretch()
        self.tabs.addTab(tab_editor, self.locale.get("tab_editor", "Редактор"))

        # --- Вкладка: VIBE ---
        tab_vibe = QWidget()
        layout_vibe = QVBoxLayout(tab_vibe)
        
        self.chk_vibe_scroll = QCheckBox(self.locale.get("vibe_auto_scroll", "Авто-прокрутка логов VIBE"))
        self.chk_vibe_scroll.setChecked(self.settings.get("vibe_auto_scroll"))
        layout_vibe.addWidget(self.chk_vibe_scroll)
        
        layout_vibe.addStretch()
        self.tabs.addTab(tab_vibe, self.locale.get("tab_vibe", "VIBE"))
        
        layout.addWidget(self.tabs)

        self.btn_save = QPushButton(self.locale.get("save_settings", "Сохранить настройки"))
        self.btn_save.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_save)

    def save_settings(self):
        self.settings.set("language", self.combo_lang.currentData())
        self.settings.set("show_hidden", self.chk_hidden.isChecked())
        self.settings.set("font_size", self.spin_font.value())
        self.settings.set("auto_save", self.chk_auto_save.isChecked())
        self.settings.set("vibe_auto_scroll", self.chk_vibe_scroll.isChecked())
        
        QMessageBox.information(
            self, 
            "GVSC", 
            self.locale.get("restart_needed", "Пожалуйста, перезапустите GVSC, чтобы применить изменения.")
        )
        self.accept()