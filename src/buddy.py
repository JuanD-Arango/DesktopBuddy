"""
Ventana principal transparente, animaciones y control interactivo de Hackmon.
"""
from pathlib import Path
import math
import win32api
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtWidgets import QWidget, QLabel, QMenu, QApplication
from PyQt6.QtGui import QMouseEvent, QAction, QPixmap, QCursor, QTransform, QIcon
from .physics import PhysicsEngine
from .behavior import BehaviorController, BuddyState
from .bubble import SpeechBubble, SoundManager
from .mail import OutlookMailWatcher

class DesktopBuddy(QWidget):
    def __init__(self):
        super().__init__()
        self.physics = PhysicsEngine()
        self.behavior = BehaviorController()
        self.sounds = SoundManager()
        self.speech_bubble = SpeechBubble()

        # Monitor de correos vía Outlook
        self.mail_watcher = OutlookMailWatcher(check_interval_sec=25, parent=self)
        self.mail_watcher.new_email.connect(self._on_new_email)
        self.mail_watcher.manual_check_result.connect(self._on_mail_manual_check)
        self.mail_watcher.start()

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
            BuddyState.JUMP: base_dir / "jump",
            BuddyState.CARRYING_MOUSE: base_dir / "hunt",
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
            BuddyState.HUNT_MOUSE: 7,
            BuddyState.JUMP: 8,
            BuddyState.CARRYING_MOUSE: 6,
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

        # 2. Mensajes pendientes
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

        # Encontrar el suelo más cercano (barra de tareas o ventanas abiertas)
        floor_y = self.physics.find_nearest_floor(
            self.y(), self.x(), self.width(), self.height(), taskbar_floor_y, hwnd
        )
        is_in_air = self.physics.is_in_air(self.y(), floor_y)

        if not self._drag_active:
            prev_state = self.behavior.state

            # Disparar salto físico si la IA lo requiere
            if self.behavior.wants_jump:
                self.physics.jump(16.5)
                self.behavior.wants_jump = False
                self.current_frame = 0

            # Actualizar comportamiento con datos en tiempo real
            state = self.behavior.update(
                mouse_x, mouse_y,
                self.x(), self.y(),
                self.width(), self.height(),
                is_in_air=is_in_air
            )

            # Efectos de sonido y reinicio de animación al cambiar de estado
            if state != prev_state:
                self.current_frame = 0
                if state == BuddyState.DIZZY:
                    self.sounds.play("dizzy")
                elif state == BuddyState.CARRYING_MOUSE:
                    self.sounds.play("eat")
                self._update_display_sprite()

            # --- MANEJO DE MOVIMIENTO SEGÚN ESTADO ---

            # A. Sujetando el ratón con la boca y llevándoselo
            if state == BuddyState.CARRYING_MOUSE:
                move_speed = 3
                carry_dx = -move_speed if self.behavior.facing_left else move_speed
                new_x = self.x() + carry_dx
                new_x, hit = self.physics.check_screen_bounds(new_x, self.width(), screen.left(), screen.right())
                if hit:
                    self.behavior.facing_left = not self.behavior.facing_left
                self.move(new_x, self.y())

                # Fijar físicamente el cursor de Windows en la boca de Hackmon
                mouth_x, mouth_y = self.behavior.get_mouth_position(
                    self.x(), self.y(), self.width(), self.height()
                )
                try:
                    win32api.SetCursorPos((int(mouth_x), int(mouth_y)))
                except Exception:
                    pass

            # B. En pleno salto parabólico hacia el cursor
            elif state == BuddyState.JUMP:
                # Desplazamiento horizontal del salto
                new_x = int(self.x() + self.behavior.jump_vx)
                new_x, _ = self.physics.check_screen_bounds(new_x, self.width(), screen.left(), screen.right())
                
                # Desplazamiento vertical por gravedad
                new_y, landed = self.physics.apply_gravity(self.y(), floor_y)
                self.move(new_x, new_y)

                if landed:
                    self.sounds.play("thud")
                    self.behavior.set_state(BuddyState.HUNT_MOUSE)
                    self.current_frame = 0

            # C. Caída libre normal
            elif state == BuddyState.FALLING or (self.y() < floor_y and state not in (BuddyState.JUMP, BuddyState.CARRYING_MOUSE)):
                if self.behavior.state != BuddyState.FALLING:
                    self.behavior.set_state(BuddyState.FALLING)
                    self.current_frame = 0
                new_y, landed = self.physics.apply_gravity(self.y(), floor_y)
                self.move(self.x(), new_y)
                if landed:
                    self.sounds.play("thud")
                    self.behavior.set_state(BuddyState.IDLE)
                    self.physics.reset()
                    self.current_frame = 0

            # D. En el suelo (Caza o paseo)
            else:
                if state == BuddyState.HUNT_MOUSE:
                    # Velocidad dinámica según la distancia al cursor
                    dist_to_mouse_x = abs(mouse_x - (self.x() + self.width() // 2))
                    move_speed = 5 if dist_to_mouse_x > 180 else 3

                    if self.behavior.facing_left:
                        new_x = self.x() - move_speed
                    else:
                        new_x = self.x() + move_speed

                    new_x, hit = self.physics.check_screen_bounds(new_x, self.width(), screen.left(), screen.right())
                    if hit:
                        self.behavior.turn_around(hit)
                    self.move(new_x, self.y())

                elif state in (BuddyState.WALK_LEFT, BuddyState.WALK_RIGHT):
                    move_speed = 2
                    if state == BuddyState.WALK_LEFT:
                        new_x = self.x() - move_speed
                    else:
                        new_x = self.x() + move_speed

                    new_x, hit = self.physics.check_screen_bounds(new_x, self.width(), screen.left(), screen.right())
                    if hit:
                        self.behavior.turn_around(hit)
                    self.move(new_x, self.y())
        else:
            # Mientras se arrastra con el ratón: calcular sacudida y altura
            screen_top = screen.top()
            screen_h = screen.height()
            if self.y() < screen_top + screen_h * 0.25:
                self._high_drag_ticks += 1
            else:
                self._high_drag_ticks = max(0, self._high_drag_ticks - 1)

    # Eventos de interacción con el ratón
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Si estaba sujetando el cursor, liberarlo de inmediato al hacer clic
            if self.behavior.is_holding_mouse:
                self.behavior.is_holding_mouse = False
                self.behavior.set_state(BuddyState.PETTED)
                self.sounds.play("purr")
                self._update_display_sprite()
                event.accept()
                return

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

            # Detector de sacudidas de ratón al arrastrarlo
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
            # Determinar si se mareó o se enojó al soltarlo
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

        # Menú de Notificaciones de Correo
        mail_menu = menu.addMenu("📬 Correo Outlook...")
        check_mail_act = mail_menu.addAction("🔄 Comprobar correo ahora")
        check_mail_act.triggered.connect(lambda: self.mail_watcher.check_mail_async(is_manual=True))

        mail_toggle_text = "🔔 Notificaciones: Activadas" if self.mail_watcher.enabled else "🔕 Notificaciones: Silenciadas"
        toggle_mail_act = mail_menu.addAction(mail_toggle_text)
        toggle_mail_act.triggered.connect(self._toggle_mail_notifications)

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

    def _on_new_email(self, sender: str, subject: str):
        """Reacción alegre y alerta al recibir un nuevo correo."""
        self.physics.jump(13.0)
        self.sounds.play("purr")
        self.speech_bubble.show_message(
            f"📬 ¡Nuevo correo de {sender}!\n\"{subject}\"",
            self.x(), self.y(), self.width(),
            duration_ms=6500
        )

    def _on_mail_manual_check(self, count: int, message: str):
        """Muestra el resultado tras solicitar comprobación manual de correo."""
        if count > 0:
            self.physics.jump(10.0)
            self.sounds.play("purr")
        self.speech_bubble.show_message(
            message,
            self.x(), self.y(), self.width(),
            duration_ms=4500
        )

    def _toggle_mail_notifications(self):
        """Activa o desactiva las alertas de correo."""
        enabled = self.mail_watcher.toggle_enabled()
        status_msg = "🔔 Notificaciones de correo activadas." if enabled else "🔕 Notificaciones de correo silenciadas."
        self.speech_bubble.show_message(status_msg, self.x(), self.y(), self.width(), duration_ms=2500)

    def closeEvent(self, event):
        """Detiene servicios en segundo plano al cerrar."""
        self.mail_watcher.stop()
        super().closeEvent(event)

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
