"""Тёмная тема (неоновый акцент) для GVSC."""

DARK_QSS = """
* { 
    font-family: 'Consolas', 'Courier New', monospace; 
    font-size: 13px; 
}
QMainWindow, QWidget { 
    background-color: #1E1E1E; 
    color: #D4D4D4; 
}
QPushButton {
    background-color: #2D2D2D; 
    color: #00ff88;
    border: 1px solid #3E3E42; 
    border-radius: 4px;
    padding: 6px 12px; 
    min-height: 30px;
    font-weight: bold;
}
QPushButton:hover { 
    background-color: #00ff88; 
    color: #000; 
}
QTextEdit, QPlainTextEdit, QLineEdit {
    background-color: #1e1e1e; 
    color: #d4d4d4;
    border: 1px solid #3E3E42; 
    selection-background-color: #264F78;
}
QTreeWidget {
    background-color: #252526; 
    color: #CCCCCC;
    border: none;
    outline: none;
}
QTreeWidget::item { padding: 4px; }
QTreeWidget::item:selected { 
    background-color: #04395E; 
    color: #FFFFFF; 
}
QTreeWidget::item:hover { 
    background-color: #2A2D2E; 
}
QTabWidget::pane { 
    border: 1px solid #3E3E42; 
    background-color: #1E1E1E;
}
QTabBar::tab {
    background-color: #2D2D2D;
    color: #888;
    padding: 8px 15px;
    border: 1px solid #3E3E42;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1E1E1E;
    color: #00ff88;
    border-top: 2px solid #00ff88;
}
QTabBar::tab:hover {
    background-color: #3E3E42;
    color: #FFF;
}
QSplitter::handle { 
    background-color: #3E3E42; 
    width: 2px; 
    height: 2px; 
}
QScrollBar:vertical { 
    background: #1E1E1E; 
    width: 14px; 
}
QScrollBar::handle:vertical { 
    background: #424242; 
    border-radius: 4px; 
    min-height: 20px; 
}
QScrollBar::handle:vertical:hover { 
    background: #4F4F4F; 
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { 
    border: none; background: none; 
}
"""