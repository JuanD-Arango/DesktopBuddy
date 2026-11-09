"""
Módulo de monitorización y notificación de correos electrónicos vía Outlook (Classic).
Utiliza automatización COM local en un hilo en segundo plano para no afectar el bucle a 60 fps.
"""
import threading
from typing import Set
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class OutlookMailWatcher(QObject):
    # Señales para comunicación con la interfaz principal
    new_email = pyqtSignal(str, str)             # (remitente, asunto)
    manual_check_result = pyqtSignal(int, str)  # (cantidad_no_leidos, mensaje_explicativo)

    def __init__(self, check_interval_sec: int = 25, parent: QObject = None):
        super().__init__(parent)
        self.check_interval_ms = check_interval_sec * 1000
        self.enabled = True
        self._initialized = False
        self._seen_entry_ids: Set[str] = set()
        self._is_checking = False

        # Temporizador para comprobación periódica
        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: self.check_mail_async(is_manual=False))

    def start(self):
        """Inicia el monitoreo automático."""
        if not self._timer.isActive():
            # Realizar primera comprobación de inicialización
            self.check_mail_async(is_manual=False)
            self._timer.start(self.check_interval_ms)

    def stop(self):
        """Detiene el monitoreo automático."""
        if self._timer.isActive():
            self._timer.stop()

    def toggle_enabled(self) -> bool:
        """Alterna el estado de activación de notificaciones."""
        self.enabled = not self.enabled
        return self.enabled

    def check_mail_async(self, is_manual: bool = False):
        """Dispara una consulta asíncrona a Outlook en un hilo independiente."""
        if not self.enabled and not is_manual:
            return

        if self._is_checking:
            if is_manual:
                self.manual_check_result.emit(-2, "Ya hay una comprobación de correo en curso.")
            return

        thread = threading.Thread(
            target=self._query_outlook_thread,
            args=(is_manual,),
            daemon=True
        )
        thread.start()

    def _query_outlook_thread(self, is_manual: bool):
        """Ejecuta la consulta COM de Outlook en un hilo de trabajo seguro."""
        self._is_checking = True
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            mapi = outlook.GetNamespace("MAPI")
            inbox = mapi.GetDefaultFolder(6)  # 6 = olFolderInbox (Bandeja de entrada)

            unread_items = inbox.Items.Restrict("[UnRead] = True")
            unread_items.Sort("[ReceivedTime]", True)
            unread_count = unread_items.Count

            # Procesar correos no leídos recientes (máximo los últimos 10)
            new_mails_to_notify = []
            for i in range(min(10, unread_count)):
                try:
                    item = unread_items.Item(i + 1)
                    entry_id = getattr(item, "EntryID", None)
                    if not entry_id:
                        continue

                    if self._initialized:
                        # Si ya habíamos inicializado y este correo no estaba en el registro previo
                        if entry_id not in self._seen_entry_ids:
                            self._seen_entry_ids.add(entry_id)
                            sender = getattr(item, "SenderName", "Desconocido")
                            subject = getattr(item, "Subject", "(Sin asunto)")
                            if len(subject) > 48:
                                subject = subject[:45] + "..."
                            new_mails_to_notify.append((sender, subject))
                    else:
                        # En el arranque inicial, registrar los que ya estaban para no saturar con alertas viejas
                        self._seen_entry_ids.add(entry_id)
                except Exception:
                    continue

            # Marcar como inicializado tras el primer barrido
            if not self._initialized:
                self._initialized = True

            # Emitir notificaciones de los correos nuevos encontrados
            for sender, subject in new_mails_to_notify:
                if self.enabled:
                    self.new_email.emit(sender, subject)

            # Respuesta para comprobación manual
            if is_manual:
                if unread_count == 0:
                    msg = "📬 Bandeja al día: No tienes correos nuevos sin leer."
                else:
                    msg = f"📬 Tienes {unread_count} correo(s) sin leer en la bandeja."
                self.manual_check_result.emit(unread_count, msg)

        except Exception as e:
            if is_manual:
                self.manual_check_result.emit(-1, "No se pudo comunicar con Outlook. Verifica que la aplicación esté abierta.")
        finally:
            pythoncom.CoUninitialize()
            self._is_checking = False
