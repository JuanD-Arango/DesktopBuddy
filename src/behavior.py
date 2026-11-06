"""
Controlador de estados, inteligencia artificial y comportamiento de Hackmon.
"""
from enum import Enum, auto
import random
import math

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
        self.current_item_type = None # 'food' o 'drink'

        # Frase o mensaje pendiente para el bocadillo de diálogo
        self.pending_message = None

    def update(self, mouse_x: int, mouse_y: int, buddy_x: int, buddy_y: int) -> BuddyState:
        """Actualiza el estado periódicamente y reacciona al ratón y al entorno."""
        self.state_timer += 1

        # Estados especiales con duración fija
        if self.state in (BuddyState.DRAGGED, BuddyState.FALLING):
            return self.state

        if self.state == BuddyState.DIZZY:
            if self.state_timer >= 100:
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
            # Duerme profundamente hasta que expire o se le despierte
            if self.state_timer >= self.state_duration:
                self.set_state(BuddyState.SIT)
                self.pending_message = "*(Bostezo)*... Buenos días."
            return self.state

        # Modo Caza de ratón
        if self.state == BuddyState.HUNT_MOUSE:
            dist_x = mouse_x - buddy_x
            dist_y = mouse_y - buddy_y
            dist = math.hypot(dist_x, dist_y)

            # Orientar hacia el ratón
            self.facing_left = (dist_x < 0)

            # Si el ratón está cerca, 'atraparlo'
            if dist < 45 or self.state_timer >= 120:
                self.set_state(BuddyState.PETTED)
                self.pending_message = "¡Te atrapé! ¡Mis reflejos de dragón nunca fallan!"
            return self.state

        # Actualización de estados normales (IDLE, WALK, SIT)
        if self.state_timer >= self.state_duration:
            self.state_timer = 0
            self.state_duration = random.randint(70, 200)

            # Posibilidad aleatoria de cazar el ratón si está en pantalla
            dist_to_mouse = math.hypot(mouse_x - buddy_x, mouse_y - buddy_y)
            if dist_to_mouse < 300 and random.random() < 0.12:
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
                self.facing_left = (mouse_x < buddy_x)

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
