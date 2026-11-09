"""
Motor de física: gravedad, detección de plataformas en ventanas de Windows y límites de pantalla.
"""
from typing import Tuple, Optional, List
import win32gui
import win32con

class PhysicsEngine:
    def __init__(self, gravity: float = 1.4, terminal_velocity: float = 24.0):
        self.gravity = gravity
        self.terminal_velocity = terminal_velocity
        self.velocity_y = 0.0
        self.current_platform_hwnd = None

    def get_platforms(self, buddy_hwnd: int, buddy_x: int, buddy_w: int) -> List[Tuple[int, int, int, int]]:
        """
        Encuentra plataformas válidas (bordes superiores de ventanas activas como Teams, Excel, Chrome, etc.).
        Retorna lista de (top_y, left_x, right_x, hwnd).
        """
        platforms = []

        def enum_cb(hwnd, _):
            if hwnd == buddy_hwnd or not win32gui.IsWindowVisible(hwnd):
                return True
            if win32gui.IsIconic(hwnd): # minimizada
                return True
            # Ignorar ventanas transparentes o sin título
            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return True
            
            # Obtener rectángulo de la ventana
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top

            # Filtrar ventanas diminutas o invisibles
            if width > 150 and height > 80 and top >= 0:
                # Comprobar si el buddy está alineado horizontalmente con la ventana
                center_x = buddy_x + buddy_w // 2
                if left <= center_x <= right:
                    platforms.append((top, left, right, hwnd))
            return True

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass

        # Ordenar por coordenada Y descendente (más arriba primero)
        platforms.sort(key=lambda p: p[0])
        return platforms

    def find_nearest_floor(self, current_y: int, buddy_x: int, buddy_w: int, buddy_h: int, taskbar_floor_y: int, buddy_hwnd: int = 0) -> int:
        """Determina el suelo más cercano debajo de Hackmon (ya sea una ventana o la barra de tareas)."""
        platforms = self.get_platforms(buddy_hwnd, buddy_x, buddy_w)
        target_floor = taskbar_floor_y
        self.current_platform_hwnd = None

        for top, left, right, hwnd in platforms:
            plat_floor = top - buddy_h
            # Si el suelo de la plataforma está debajo de nuestra posición actual (o apenas debajo)
            if plat_floor >= current_y - 2 and plat_floor < target_floor:
                target_floor = plat_floor
                self.current_platform_hwnd = hwnd
                break

        return target_floor

    def jump(self, power: float = 16.0):
        """Aplica un impulso vertical hacia arriba para saltar."""
        self.velocity_y = -abs(power)

    def is_in_air(self, current_y: int, floor_y: int) -> bool:
        """Indica si Hackmon está suspendido o en movimiento vertical en el aire."""
        return current_y < floor_y or self.velocity_y < 0

    def apply_gravity(self, current_y: int, floor_y: int) -> Tuple[int, bool]:
        """
        Aplica gravedad y retorna (nueva_posicion_y, ha_aterrizado).
        """
        if current_y < floor_y or self.velocity_y < 0:
            self.velocity_y = min(self.velocity_y + self.gravity, self.terminal_velocity)
            new_y = current_y + int(self.velocity_y)
            if new_y >= floor_y and self.velocity_y >= 0:
                self.velocity_y = 0.0
                return floor_y, True
            return new_y, False
        
        self.velocity_y = 0.0
        return floor_y, False

    def check_screen_bounds(self, current_x: int, buddy_w: int, screen_left: int, screen_right: int) -> Tuple[int, Optional[str]]:
        """
        Evita que Hackmon corra contra las paredes.
        Retorna (nuevo_x, borde_golpeado: 'left' | 'right' | None).
        """
        if current_x <= screen_left:
            return screen_left + 1, 'left'
        if current_x + buddy_w >= screen_right:
            return screen_right - buddy_w - 1, 'right'
        return current_x, None

    def reset(self):
        self.velocity_y = 0.0
        self.current_platform_hwnd = None
