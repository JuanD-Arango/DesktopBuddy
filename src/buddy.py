"""
Ventana principal transparente, animaciones y control interactivo de Hackmon.
"""
from pathlib import Path
import math
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtWidgets import QWidget, QLabel, QMenu, QApplication
from PyQt6.QtGui import QMouseEvent, QAction, QPixmap, QCursor, QTransform, QIcon
from .physics import PhysicsEngine
from .behavior import BehaviorController, BuddyState
from .bubble import SpeechBubble, SoundManager

class DesktopBuddy(QWidget):
    def __init__(self):
        super().__init__()
        self.physics = PhysicsEngine()
        self.behavior = BehaviorController()
        self.sounds = SoundManager()
        self.speech_bubble = SpeechBubble()

        self._drag_active = False
        self._drag_pos = QPoint()
        self._prev_drag_pos = QPoint()
        self._shake_count = 0
        self._prev_drag_dx = 0
        self._high_drag_ticks = 0

        # Almacén de sprites y control de animación
        self.sprites = {}
        self.current_frame = 0
        self.anim_counter = 0

        self._load_sprites()
        self._init_window()
        self._init_ui()
        self._init_loop()

    def _load_sprites(self):
        """Carga los fotogramas para cada estado desde assets/sprites."""
        base_dir = Path(__file__).resolve().parent.parent / "assets" / "sprites"
        mapping = {
            BuddyState.IDLE: base_dir / "idle",
            BuddyState.WALK_LEFT: base_dir / "walk_left",
            BuddyState.WALK_RIGHT: base_dir / "walk_right",
            BuddyState.DRAGGED: base_dir / "dragged",
            BuddyState.FALLING: base_dir / "fall",
            BuddyState.SIT: base_dir / "sit",
            BuddyState.SLEEP: base_dir / "sleep",
            BuddyState.DIZZY: base_dir / "dizzy",
            BuddyState.ANGRY: base_dir / "angry",
            BuddyState.HUNT_MOUSE: base_dir / "hunt",
            BuddyState.EATING: base_dir / "eat",
            BuddyState.DRINKING: base_dir / "drink",
            BuddyState.PETTED: base_dir / "petted",
        }

        for state, folder in mapping.items():
            self.sprites[state] = []
            if folder.exists():
                png_files = sorted(folder.glob("*.png"))
                for file_path in png_files:
                    pixmap = QPixmap(str(file_path))
                    if not pixmap.isNull():
                        self.sprites[state].append(pixmap)

    def _init_window(self):
        self.setWindowTitle("Hackmon Desktop Buddy")
        # Ventana sin bordes, siempre visible sobre las demás y con fondo transparente
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Dimensiones basadas en el sprite estándar
        sample = self._get_current_pixmap()
        if sample:
            self.resize(sample.size())
        else:
            self.resize(104, 86)

        # Posicionar en el centro de la pantalla al iniciar
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            start_x = geom.center().x() - self.width() // 2
            start_y = geom.center().y() - self.height() // 2
            self.move(start_x, start_y)

    def _init_ui(self):
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_display_sprite()

    def _init_loop(self):
        # Bucle de actualización a 60 fps
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    def _get_current_pixmap(self) -> QPixmap | None:
        frames = self.sprites.get(self.behavior.state, [])
        if not frames:
            # Fallback a IDLE si no hay frames en el estado
            frames = self.sprites.get(BuddyState.IDLE, [])
        if frames:
            pixmap = frames[self.current_frame % len(frames)]
            # Reflejo horizontal si está mirando a la izquierda (excepto WALK_LEFT que ya está reflejado)
            if self.behavior.facing_left and self.behavior.state != BuddyState.WALK_LEFT:
                return pixmap.transformed(QTransform().scale(-1, 1))
            return pixmap
        return None

    def _update_display_sprite(self):
        pixmap = self._get_current_pixmap()
        if pixmap:
            self.resize(pixmap.size())
            self.label.resize(pixmap.size())
            self.label.setPixmap(pixmap)

    def _tick(self):
        cursor_pos = QCursor.pos()
        mouse_x = cursor_pos.x()
        mouse_y = cursor_pos.y()

        # 1. Velocidad de animación según el estado
        self.anim_counter += 1
        speed_map = {
            BuddyState.IDLE: 14,
            BuddyState.WALK_LEFT: 6,
            BuddyState.WALK_RIGHT: 6,
            BuddyState.SIT: 16,
            BuddyState.SLEEP: 18,
            BuddyState.DIZZY: 8,
            BuddyState.ANGRY: 10,
            BuddyState.HUNT_MOUSE: 8,
            BuddyState.EATING: 10,
            BuddyState.DRINKING: 10,
            BuddyState.PETTED: 10,
        }
        anim_speed = speed_map.get(self.behavior.state, 10)
        if self.anim_counter >= anim_speed:
            self.anim_counter = 0
            frames = self.sprites.get(self.behavior.state, [])
            if frames:
                self.current_frame = (self.current_frame + 1) % len(frames)
            self._update_display_sprite()

        # 2. Mensajes y sonidos pendientes
        if self.behavior.pending_message:
            self.speech_bubble.show_message(
                self.behavior.pending_message,
                self.x(), self.y(), self.width()
            )
            self.behavior.pending_message = None

        # 3. Física y plataformas
        screen = self.screen().availableGeometry()
        taskbar_floor_y = screen.bottom() - self.height()
        hwnd = int(self.winId())

        # Encontrar el suelo más cercano (barra de tareas o techo de ventanas como Teams/Excel)
        floor_y = self.physics.find_nearest_floor(
            self.y(), self.x(), self.width(), self.height(), taskbar_floor_y, hwnd
        )

        if not self._drag_active:
            if self.y() < floor_y:
                if self.behavior.state != BuddyState.FALLING:
                    self.behavior.set_state(BuddyState.FALLING)
                    self.current_frame = 0
                new_y, landed = self.physics.apply_gravity(self.y(), floor_y)
                self.move(self.x(), new_y)
                if landed:
                    self.sounds.play("thud")
                    self.behavior.set_state(BuddyState.IDLE)
                    self.current_frame = 0
            else:
                if self.behavior.state == BuddyState.FALLING:
                    self.sounds.play("thud")
                    self.behavior.set_state(BuddyState.IDLE)
                    self.physics.reset()
                    self.current_frame = 0

                prev_state = self.behavior.state
                state = self.behavior.update(mouse_x, mouse_y, self.x(), self.y())
                if state != prev_state:
                    self.current_frame = 0
                    self._update_display_sprite()

                # Movimiento horizontal
                move_speed = 3 if state == BuddyState.HUNT_MOUSE else 2
                if state in (BuddyState.WALK_LEFT, BuddyState.HUNT_MOUSE) and self.behavior.facing_left:
                    new_x = self.x() - move_speed
                    new_x, hit = self.physics.check_screen_bounds(new_x, self.width(), screen.left(), screen.right())
                    if hit:
                        self.behavior.turn_around(hit)
                    self.move(new_x, self.y())
                elif state in (BuddyState.WALK_RIGHT, BuddyState.HUNT_MOUSE) and not self.behavior.facing_left:
                    new_x = self.x() + move_speed
                    new_x, hit = self.physics.check_screen_bounds(new_x, self.width(), screen.left(), screen.right())
                    if hit:
                        self.behavior.turn_around(hit)
                    self.move(new_x, self.y())
        else:
            # Mientras se arrastra: calcular sacudida y altura
            screen_top = screen.top()
            screen_h = screen.height()
            if self.y() < screen_top + screen_h * 0.25:
                self._high_drag_ticks += 1
            else:
                self._high_drag_ticks = max(0, self._high_drag_ticks - 1)

    # Eventos de interacción con el ratón
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._prev_drag_pos = event.globalPosition().toPoint()
            self._shake_count = 0
            self._prev_drag_dx = 0
            self._high_drag_ticks = 0
            self.behavior.set_state(BuddyState.DRAGGED)
            self.current_frame = 0
            self.physics.reset()
            self._update_display_sprite()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_active and event.buttons() & Qt.MouseButton.LeftButton:
            curr_pos = event.globalPosition().toPoint()
            self.move(curr_pos - self._drag_pos)

            # Detector de sacudidas de ratón
            dx = curr_pos.x() - self._prev_drag_pos.x()
            if abs(dx) > 18:
                if (dx > 0 and self._prev_drag_dx < 0) or (dx < 0 and self._prev_drag_dx > 0):
                    self._shake_count += 1
                self._prev_drag_dx = dx
            self._prev_drag_pos = curr_pos
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False
            # Determinar si se mareó o se enojó
            if self._shake_count >= 5:
                self.behavior.set_state(BuddyState.DIZZY)
                self.sounds.play("dizzy")
                self.speech_bubble.show_message("¡Ay! ¡Qué mareo... todo gira!", self.x(), self.y(), self.width())
            elif self._high_drag_ticks >= 60:
                self.behavior.set_state(BuddyState.ANGRY)
                self.sounds.play("angry")
                self.speech_bubble.show_message("¡Bájame! ¡No me gusta estar tan alto!", self.x(), self.y(), self.width())
            else:
                self.behavior.set_state(BuddyState.FALLING)

            self.current_frame = 0
            self._update_display_sprite()
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Doble clic para acariciar a Hackmon."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.behavior.pet()
            self.sounds.play("purr")
            self.current_frame = 0
            self._update_display_sprite()
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        # Encabezado
        title_action = QAction("🐉 Hackmon Desktop Buddy", self)
        title_action.setEnabled(False)
        menu.addAction(title_action)
        menu.addSeparator()

        # Menú de Alimentación
        food_menu = menu.addMenu("🍖 Alimentar...")
        meat_act = food_menu.addAction("🍖 Carne con hueso (Digimon)")
        meat_act.triggered.connect(lambda: self._feed_item("carne con hueso"))
        burger_act = food_menu.addAction("🍔 Hamburguesa deliciosa")
        burger_act.triggered.connect(lambda: self._feed_item("hamburguesa"))
        candy_act = food_menu.addAction("🍬 Caramelo dulce")
        candy_act.triggered.connect(lambda: self._feed_item("caramelo"))

        # Menú de Bebidas
        drink_menu = menu.addMenu("☕ Dar bebida...")
        water_act = drink_menu.addAction("💧 Vaso de agua fresca")
        water_act.triggered.connect(lambda: self._give_drink_item("agua fresca"))
        tea_act = drink_menu.addAction("🍵 Té caliente")
        tea_act.triggered.connect(lambda: self._give_drink_item("té caliente"))
        coffee_act = drink_menu.addAction("☕ Café energizante")
        coffee_act.triggered.connect(lambda: self._give_drink_item("café"))

        menu.addSeparator()

        # Acciones de descanso
        if self.behavior.state == BuddyState.SLEEP:
            wake_act = menu.addAction("⏰ Despertar")
            wake_act.triggered.connect(self.behavior.wake_up)
        else:
            sleep_act = menu.addAction("💤 Echar siesta")
            sleep_act.triggered.connect(lambda: self.behavior.set_state(BuddyState.SLEEP))

        # Acción Cazar Ratón
        hunt_act = menu.addAction("🐾 Cazar el cursor")
        hunt_act.triggered.connect(self._trigger_hunt)

        menu.addSeparator()

        # Alternar Sonidos
        sound_text = "🔇 Silenciar sonidos" if not self.sounds.muted else "🔊 Activar sonidos"
        sound_act = menu.addAction(sound_text)
        sound_act.triggered.connect(self.sounds.toggle_mute)

        # Soltar desde arriba
        drop_act = menu.addAction("⬆ Soltar desde arriba")
        drop_act.triggered.connect(self._drop_from_top)

        menu.addSeparator()

        # Salir
        exit_act = menu.addAction("❌ Salir")
        exit_act.triggered.connect(self.close)

        menu.exec(event.globalPos())

    def _feed_item(self, item_name: str):
        self.sounds.play("eat")
        self.behavior.feed(item_name)
        self.current_frame = 0
        self._update_display_sprite()

    def _give_drink_item(self, drink_name: str):
        self.sounds.play("drink")
        self.behavior.give_drink(drink_name)
        self.current_frame = 0
        self._update_display_sprite()

    def _trigger_hunt(self):
        self.behavior.set_state(BuddyState.HUNT_MOUSE)
        self.speech_bubble.show_message("¡Allá voy! ¡Voy a cazar tu ratón!", self.x(), self.y(), self.width())

    def _drop_from_top(self):
        screen = self.screen().availableGeometry()
        self.move(self.x(), screen.top() + 50)
        self.behavior.set_state(BuddyState.FALLING)
        self.physics.reset()
