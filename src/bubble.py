"""
Bocadillo de diálogo visual y gestor de efectos de sonido para Hackmon.
"""
from pathlib import Path
import winsound
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QFont

class SpeechBubble(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(26, 26, 36, 230);
                color: #FFF8E7;
                border: 2px solid #E63946;
                border-radius: 12px;
                padding: 6px 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.label)

        # Temporizador para ocultar automáticamente el bocadillo
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_message(self, text: str, buddy_x: int, buddy_y: int, buddy_w: int, duration_ms: int = 3500):
        if not text:
            return
        self.label.setText(text)
        self.adjustSize()

        # Posicionar centrado encima de la cabeza de Hackmon
        bubble_x = buddy_x + (buddy_w - self.width()) // 2
        bubble_y = max(10, buddy_y - self.height() - 6)
        self.move(bubble_x, bubble_y)
        self.show()
        self.raise_()

        self.hide_timer.stop()
        self.hide_timer.start(duration_ms)


class SoundManager:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent / "assets" / "sounds"
        self.muted = False

    def play(self, sound_name: str):
        if self.muted:
            return
        sound_file = self.base_dir / f"{sound_name}.wav"
        if sound_file.exists():
            try:
                winsound.PlaySound(str(sound_file), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted
