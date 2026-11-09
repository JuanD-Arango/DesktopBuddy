"""
Controlador de estados, inteligencia artificial y comportamiento de Hackmon.
"""
from enum import Enum, auto
import random
import math
from typing import Tuple, Optional

class BuddyState(Enum):
    IDLE = auto()
    WALK_LEFT = auto()
    WALK_RIGHT = auto()
    SIT = auto()
    SLEEP = auto()
    DRAGGED = auto()
    FALLING = auto()
    DIZZY = auto()
    ANGRY = auto()
    HUNT_MOUSE = auto()
    JUMP = auto()
    CARRYING_MOUSE = auto()
    EATING = auto()
    DRINKING = auto()
    PETTED = auto()

class BehaviorController:
    def __init__(self):
        self.state = BuddyState.FALLING
        self.state_timer = 0
        self.state_duration = 60
        self.facing_left = False

        # Alimento o bebida actual
        self.current_item = None
        self.current_item_type = None  # 'food' o 'drink'

        # Frase o mensaje pendiente para el bocadillo de diálogo
        self.pending_message = None

        # Variables para la mecánica de caza y salto
        self.wants_jump = False
        self.jump_vx = 0.0
        self.hunt_jump_cooldown = 0
        self.is_holding_mouse = False
        self.carry_timer = 0
        self.carry_duration = 150  # ~2.5 segundos a 60 fps
        self.carry_target_x = None

        # Variables para detección de mareo por círculos del ratón (swirl)
        self._prev_mouse_angle = None
        self._swirl_angle_acc = 0.0

    def get_mouth_position(self, buddy_x: int, buddy_y: int, buddy_w: int, buddy_h: int) -> Tuple[float, float]:
        """Calcula las coordenadas exactas de la boca según la orientación de Hackmon."""
        if self.facing_left:
            mouth_x = buddy_x + buddy_w * 0.20
        else:
            mouth_x = buddy_x + buddy_w * 0.80
        mouth_y = buddy_y + buddy_h * 0.45
        return mouth_x, mouth_y

    def check_swirl(self, mouse_x: int, mouse_y: int, center_x: float, center_y: float) -> bool:
        """
        Detecta si el usuario está haciendo girar el ratón en círculos rápidos alrededor de Hackmon.
        Si completa ~2.5 vueltas continuas, retorna True para marearlo.
        """
        dist = math.hypot(mouse_x - center_x, mouse_y - center_y)
        # Solo evaluar si el cursor orbita a una distancia coherente (entre 25px y 350px)
        if dist < 25 or dist > 350:
            self._prev_mouse_angle = None
            self._swirl_angle_acc *= 0.95
            return False

        current_angle = math.atan2(mouse_y - center_y, mouse_x - center_x)
        if self._prev_mouse_angle is not None:
            delta = current_angle - self._prev_mouse_angle
            # Normalizar al intervalo [-pi, pi]
            while delta > math.pi:
                delta -= 2 * math.pi
            while delta < -math.pi:
                delta += 2 * math.pi

            # Filtrar brincos exagerados
            if abs(delta) < 1.4:
                # Si invierte el sentido de giro, amortiguar en lugar de sumar
                if (delta > 0 and self._swirl_angle_acc < 0) or (delta < 0 and self._swirl_angle_acc > 0):
                    self._swirl_angle_acc = delta
                else:
                    self._swirl_angle_acc += delta

        self._prev_mouse_angle = current_angle

        # ~2.4 vueltas continuas acumuladas en rad (2.4 * 2*pi ≈ 15.0 rad)
        if abs(self._swirl_angle_acc) >= 15.0:
            self._swirl_angle_acc = 0.0
            self._prev_mouse_angle = None
            return True

        # Decaimiento natural en cada tick si reduce la velocidad
        self._swirl_angle_acc *= 0.97
        return False

    def update(
        self,
        mouse_x: int,
        mouse_y: int,
        buddy_x: int,
        buddy_y: int,
        buddy_w: int = 104,
        buddy_h: int = 86,
        is_in_air: bool = False
    ) -> BuddyState:
        """Actualiza el estado periódicamente y reacciona al ratón y al entorno."""
        self.state_timer += 1
        if self.hunt_jump_cooldown > 0:
            self.hunt_jump_cooldown -= 1

        center_x = buddy_x + buddy_w / 2.0
        center_y = buddy_y + buddy_h / 2.0

        # 1. Estados especiales protegidos
        if self.state in (BuddyState.DRAGGED, BuddyState.FALLING):
            self._prev_mouse_angle = None
            return self.state

        # 2. Detección de mareo por círculos (activo en reposo, paseo o caza)
        if self.state in (BuddyState.IDLE, BuddyState.SIT, BuddyState.WALK_LEFT, BuddyState.WALK_RIGHT, BuddyState.HUNT_MOUSE):
            if self.check_swirl(mouse_x, mouse_y, center_x, center_y):
                self.is_holding_mouse = False
                self.set_state(BuddyState.DIZZY)
                self.pending_message = "¡Ay! ¡Demasiadas vueltas... qué mareo!"
                return self.state

        if self.state == BuddyState.DIZZY:
            if self.state_timer >= 110:
                self.set_state(BuddyState.SIT)
                self.pending_message = "¡Uff... ya no veo estrellitas!"
            return self.state

        if self.state == BuddyState.ANGRY:
            if self.state_timer >= 80:
                self.set_state(BuddyState.IDLE)
                self.pending_message = "¡No me vuelvas a subir tan alto!"
            return self.state

        if self.state in (BuddyState.EATING, BuddyState.DRINKING):
            if self.state_timer >= 90:
                item_name = self.current_item or "algo rico"
                self.set_state(BuddyState.PETTED)
                self.pending_message = f"¡Qué delicia! Muchas gracias por el {item_name}."
            return self.state

        if self.state == BuddyState.PETTED:
            if self.state_timer >= 70:
                self.set_state(BuddyState.IDLE)
            return self.state

        if self.state == BuddyState.SLEEP:
            if self.state_timer >= self.state_duration:
                self.set_state(BuddyState.SIT)
                self.pending_message = "*(Bostezo)*... Buenos días."
            return self.state

        # 3. Estado: Sujetando y Llevándose el Cursor
        if self.state == BuddyState.CARRYING_MOUSE:
            self.carry_timer += 1
            if self.carry_timer >= self.carry_duration:
                self.is_holding_mouse = False
                self.set_state(BuddyState.PETTED)
                self.pending_message = "¡Jajaja! ¡Buen juego, te dejo libre por ahora!"
            return self.state

        # 4. Estado: En pleno salto de caza
        if self.state == BuddyState.JUMP:
            mouth_x, mouth_y = self.get_mouth_position(buddy_x, buddy_y, buddy_w, buddy_h)
            dist_to_mouth = math.hypot(mouse_x - mouth_x, mouse_y - mouth_y)
            # Detección de captura en el aire
            if dist_to_mouth < 32:
                self.is_holding_mouse = True
                self.carry_timer = 0
                self.set_state(BuddyState.CARRYING_MOUSE)
                self.pending_message = "¡Te atrapé en el aire! ¡Toma ya!"
                return self.state

            # Si ya aterrizó y no atrapó el cursor
            if not is_in_air:
                self.set_state(BuddyState.HUNT_MOUSE)
            return self.state

        # 5. Modo Caza de ratón real
        if self.state == BuddyState.HUNT_MOUSE:
            # Orientación inmediata hacia el cursor
            self.facing_left = (mouse_x < center_x)

            mouth_x, mouth_y = self.get_mouth_position(buddy_x, buddy_y, buddy_w, buddy_h)
            dist_to_mouth = math.hypot(mouse_x - mouth_x, mouse_y - mouth_y)

            # ¡Atrapado real! La boca hace contacto con el cursor
            if dist_to_mouth < 28:
                self.is_holding_mouse = True
                self.carry_timer = 0
                self.set_state(BuddyState.CARRYING_MOUSE)
                self.pending_message = random.choice([
                    "¡Te atrapé! ¡Ahora eres mi presa!",
                    "¡Ñam! ¡Tengo el cursor en mis mandíbulas!",
                    "¡Mis reflejos de dragón nunca fallan!"
                ])
                return self.state

            # Detección de salto si el cursor está elevado
            if not is_in_air and self.hunt_jump_cooldown <= 0:
                if mouse_y < buddy_y - 45 and abs(mouse_x - center_x) < 280:
                    self.wants_jump = True
                    self.hunt_jump_cooldown = 80
                    dx = mouse_x - center_x
                    self.jump_vx = max(-6.0, min(6.0, dx * 0.05))
                    self.set_state(BuddyState.JUMP)
                    return self.state

            # Tiempo límite de caza: Si no lo atrapa en ~8 segundos, reconoce el fallo
            if self.state_timer >= 480:
                self.set_state(BuddyState.SIT)
                self.pending_message = random.choice([
                    "¡Rayos, eres muy rápido!",
                    "¡Uff, se me escapó el cursor!",
                    "¡Casi lo tenía... a la próxima no te escaparás!"
                ])
                return self.state

            return self.state

        # 6. Actualización de estados normales (IDLE, WALK, SIT)
        if self.state_timer >= self.state_duration:
            self.state_timer = 0
            self.state_duration = random.randint(70, 200)

            # Ocasionalmente iniciar caza espontánea si el ratón está cerca
            dist_to_mouse = math.hypot(mouse_x - center_x, mouse_y - center_y)
            if dist_to_mouse < 350 and random.random() < 0.15:
                self.set_state(BuddyState.HUNT_MOUSE)
                self.pending_message = "¡Veo una presa! ¡A por el cursor!"
                return self.state

            # Posibilidad de aperitivo espontáneo
            if random.random() < 0.05:
                item = random.choice(["trozo de carne", "hamburguesa", "caramelo"])
                self.feed(item, auto_message=False)
                self.pending_message = f"Tenía algo de hambre... comeré un {item}."
                return self.state

            # Posibilidad de descansar profundamente (1 a 5 minutos)
            if random.random() < 0.08:
                self.put_to_sleep()
                return self.state

            # Elegir entre caminar o descansar sentado
            next_action = random.choice([
                BuddyState.IDLE,
                BuddyState.SIT,
                BuddyState.WALK_LEFT,
                BuddyState.WALK_RIGHT
            ])
            self.set_state(next_action)

            # Orientación
            if next_action == BuddyState.WALK_LEFT:
                self.facing_left = True
            elif next_action == BuddyState.WALK_RIGHT:
                self.facing_left = False
            elif next_action in (BuddyState.IDLE, BuddyState.SIT):
                # En reposo, mirar hacia donde esté el ratón
                self.facing_left = (mouse_x < center_x)

        return self.state

    def set_state(self, new_state: BuddyState):
        self.state = new_state
        self.state_timer = 0

    def feed(self, item_name: str, auto_message: bool = True):
        self.current_item = item_name
        self.current_item_type = 'food'
        self.set_state(BuddyState.EATING)
        if auto_message:
            self.pending_message = f"¡Ñam! ¡Comiendo {item_name}!"

    def give_drink(self, drink_name: str, auto_message: bool = True):
        self.current_item = drink_name
        self.current_item_type = 'drink'
        self.set_state(BuddyState.DRINKING)
        if auto_message:
            self.pending_message = f"¡Glup! Tomando {drink_name}."

    def pet(self):
        self.set_state(BuddyState.PETTED)
        self.pending_message = random.choice([
            "¡Purr! ¡Eso se siente genial!",
            "¡Jejeje, me hace cosquillas!",
            "¡El compañero de un Royal Knight siempre agradece cariño!"
        ])

    def put_to_sleep(self, duration_ticks: int = None):
        if duration_ticks is None:
            # Entre 1 y 5 minutos (3600 a 18000 ticks a 60 fps)
            duration_ticks = random.randint(3600, 18000)
        self.set_state(BuddyState.SLEEP)
        self.state_duration = duration_ticks
        self.pending_message = "Zzz... me echo una buena siesta."

    def wake_up(self):
        self.set_state(BuddyState.SIT)
        self.pending_message = "¡*(Sobresalto)*! Ya desperté... ¿qué misión tenemos?"

    def turn_around(self, hit_edge: str):
        """Reacciona a los bordes de la pantalla cambiando inmediatamente de dirección."""
        self.state_timer = 0
        self.state_duration = random.randint(80, 180)
        if hit_edge == 'left':
            self.facing_left = False
            self.state = BuddyState.WALK_RIGHT
        else:
            self.facing_left = True
            self.state = BuddyState.WALK_LEFT
