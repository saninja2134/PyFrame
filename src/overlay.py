import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QLineEdit, QScrollArea, QFrame, QTabWidget, QTextEdit, QTextBrowser, QHBoxLayout, QPushButton
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QUrl
from config import ConfigManager

class WarframeOverlay(QMainWindow):
    search_triggered = pyqtSignal(str)
    exit_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config = ConfigManager.load_config()
        self.initUI()
        self.load_state()

    def initUI(self):
        # Set window flags for transparency and stay on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Position the overlay from config
        geo = self.config.get("window", {})
        self.setGeometry(
            geo.get("x", 50), 
            geo.get("y", 50), 
            geo.get("width", 400), 
            geo.get("height", 600)
        )

        # Central widget
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(20, 20, 30, 240);
                border: 1px solid #444;
                border-radius: 10px;
                color: #ddd;
            }
            QTabWidget::pane {
                border: 0;
            }
            QTabBar::tab {
                background: #333;
                color: #aaa;
                padding: 8px 15px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #444;
                color: #00d2ff;
                font-weight: bold;
            }
        """)
        self.setCentralWidget(self.container)
        
        main_layout = QVBoxLayout(self.container)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("PyFrame Overlay")
        header.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 16px; border: none; margin-bottom: 5px;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #ff5555;
            }
        """)
        close_btn.clicked.connect(self.exit_triggered.emit)
        header_layout.addWidget(close_btn)

        main_layout.addLayout(header_layout)

        # Global Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Item / Warframe...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #222;
                color: white;
                border: 1px solid #555;
                padding: 6px;
                border-radius: 4px;
                margin-bottom: 5px;
            }
        """)
        self.search_input.returnPressed.connect(self.handle_search)
        main_layout.addWidget(self.search_input)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # --- Tab 1: Cycles (World State) ---
        self.tab_cycles = QWidget()
        self.tabs.addTab(self.tab_cycles, "Cycles")
        self.layout_cycles = QVBoxLayout(self.tab_cycles)
        
        self.cycles_label = QLabel("Loading Cycles...")
        self.cycles_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cycles_label.setWordWrap(True)
        self.cycles_label.setStyleSheet("font-size: 13px; line-height: 1.4; border: none;")
        self.layout_cycles.addWidget(self.cycles_label)
        
        # --- Tab 2: Activities (Sortie, Void Trader, Invasions) ---
        self.tab_activities = QWidget()
        scroll_act = QScrollArea()
        scroll_act.setWidgetResizable(True)
        scroll_act.setStyleSheet("background: transparent; border: none;")
        self.tabs.addTab(scroll_act, "Activities")
        
        self.content_activities = QWidget()
        self.layout_activities = QVBoxLayout(self.content_activities)
        self.layout_activities.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.activities_label = QLabel("Loading Activities...")
        self.activities_label.setWordWrap(True)
        self.activities_label.setStyleSheet("font-size: 12px; border: none;")
        self.layout_activities.addWidget(self.activities_label)
        scroll_act.setWidget(self.content_activities)

        # --- Tab 3: Search (Market, Wiki, Builds) ---
        self.tab_search = QWidget()
        self.tabs.addTab(self.tab_search, "Search")
        self.layout_search = QVBoxLayout(self.tab_search)
        self.layout_search.setContentsMargins(0, 0, 0, 0)
        self.layout_search.setSpacing(0)

        # Top Section: Search Summary
        self.search_results_label = QTextBrowser()
        self.search_results_label.setOpenExternalLinks(True)
        self.search_results_label.setStyleSheet("background: transparent; border-bottom: 1px solid #444; color: #ddd; font-size: 13px; padding: 10px;")
        self.search_results_label.setHtml("Enter item name above...")
        self.search_results_label.setMaximumHeight(200)
        self.layout_search.addWidget(self.search_results_label)
        
        # Bottom Section: Build (Web View)
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.layout_search.addWidget(self.web_view)

        # --- Tab 4: Reference (Static Info) ---
        self.tab_ref = QWidget()
        self.tabs.addTab(self.tab_ref, "Info")
        self.layout_ref = QVBoxLayout(self.tab_ref)
        
        self.ref_text = QTextBrowser()
        self.ref_text.setStyleSheet("background: transparent; color: #ddd; font-size: 12px; border: none;")
        self.ref_text.setOpenExternalLinks(True)
        self.layout_ref.addWidget(self.ref_text)

        # --- Tab 5: Notes ---
        self.tab_notes = QWidget()
        self.tabs.addTab(self.tab_notes, "Notes")
        self.layout_notes = QVBoxLayout(self.tab_notes)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Type your farming list here...")
        self.notes_input.setStyleSheet("""
            QTextEdit {
                background-color: #222;
                border: 1px solid #444;
                color: #ddd;
                border-radius: 4px;
            }
        """)
        self.layout_notes.addWidget(self.notes_input)

        # Footer
        footer = QLabel("Ctrl+Alt+O = Toggle | Ctrl+Alt+X = Exit")
        footer.setStyleSheet("color: #666; font-size: 10px; border: none; margin-top: 5px;")
        main_layout.addWidget(footer)

    def load_build_url(self, url):
        self.web_view.load(QUrl(url))
        self.web_view.loadFinished.connect(self._inject_cleanup_script)
        # Switch to Search tab which now holds the view
        self.tabs.setCurrentWidget(self.tab_search)

    def _inject_cleanup_script(self, success):
        if not success: return
        
        # CSS to isolate the build calculator
        css = """
            ::-webkit-scrollbar { display: none; }
            body { overflow: hidden !important; background: #14141e !important; }
            
            /* Hide everything initially */
            body > * { visibility: hidden; }
            
            /* Make the build content visible and positioned */
            div[class*="BuildCalculator_buildContents"] {
                visibility: visible !important;
                display: block !important;
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100% !important;
                height: 100% !important;
                z-index: 99999;
                background-color: #14141e;
                overflow-y: auto;
                padding: 10px;
            }
            
            /* Ensure parents are visible for the child to see */
            #__next { visibility: visible !important; }

            /* Remove the big background image */
            div[class*="BuildCalculator_buildBackground"] { display: none !important; }
        """
        
        js = f"var style = document.createElement('style'); style.innerHTML = `{css}`; document.head.appendChild(style);"
        self.web_view.page().runJavaScript(js)

        # Scroll to top just in case
        self.web_view.page().runJavaScript("window.scrollTo(0,0);")

    def handle_search(self):
        query = self.search_input.text()
        if query:
            self.search_triggered.emit(query)

    def update_cycles_tab(self, text):
        self.cycles_label.setText(text)

    def update_activities_tab(self, text):
        self.activities_label.setText(text)

    def update_search_results(self, text):
        self.search_results_label.setHtml(text)

    def set_reference_text(self, text):
        self.ref_text.setHtml(text)
        self.ref_text.show() # Ensure visible if hidden
        
    def hide_reference_text(self):
        self.ref_text.hide() # Optional utility

    def load_state(self):
        """Restore UI state from config."""
        notes = self.config.get("notes", "")
        self.notes_input.setPlainText(notes)

    def closeEvent(self, event):
        """Save state on close."""
        # Save geometry
        geo = self.geometry()
        data = {
            "window": {
                "x": geo.x(),
                "y": geo.y(),
                "width": geo.width(),
                "height": geo.height()
            },
            "notes": self.notes_input.toPlainText()
        }
        ConfigManager.save_config(data)
        super().closeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            if hasattr(self, "drag_pos"):
                self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
                self.drag_pos = event.globalPosition().toPoint()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = WarframeOverlay()
    overlay.show()
    sys.exit(app.exec())
