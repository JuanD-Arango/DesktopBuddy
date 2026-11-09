# Hackmon Desktop Buddy 🐉

A virtual companion that hangs out on your screen to keep you company, walking around, talking occasionally, sleeping, eating, and letting you play with it—while occasionally trying to troll you. It will gradually get updates to learn new tricks!

Built with **Python**, **PyQt6**, and **Win32 API**.

---

## ✨ Features & Capabilities

- **Always-on-top & Transparent:** Borderless transparent window that seamlessly lives on top of your desktop and applications.
- **Physics Engine & Real Window Detection:**
  - Gravity simulation with terminal velocity and landing impacts.
  - Detects active Windows application boundaries (Teams, Excel, Chrome, browser windows, taskbar) so Hackmon can land and walk on top of your actual open windows.
- **Dynamic Behavioral States:**
  - `Idle`: Breathes and observes your desktop.
  - `Walk Left / Right`: Wanders around the desktop and screen edges.
  - `Sitting & Sleeping`: Takes naps periodically or on demand.
  - `Hunt Mouse`: Active real-time cursor tracking, turning, speed bursts, and failure recognition.
  - `Jump`: Vertical leap to catch high-altitude targets in mid-air.
  - `Carrying Mouse`: Holds the Windows cursor in his jaws and physically drags it along the screen!
  - `Eating & Drinking`: Custom animations for meals and drinks.
  - `Petted`: Responds happily to love and attention.
  - `Dizzy`: Gets dizzy if shaken or if the cursor spins rapidly in circles around him.
  - `Angry`: Reacts if held up too high near the top of the screen.
- **Rich Mouse Interactions:**
  - **Real Cursor Chase & Catch:** Hackmon actively chases your cursor, jumps if it flies overhead, and clamps down on it when caught.
  - **Cursor Swirl Dizziness:** Circling the cursor around Hackmon will make him dizzy.
  - **Drag & Drop:** Pick up Hackmon and drop him anywhere; watch him fall with gravity.
  - **Shake Detection:** Shaking Hackmon rapidly while dragging triggers the dizzy animation and dialogue.
  - **High-altitude Detection:** Holding him too high makes him grumpy.
  - **Double Click:** Double-click on Hackmon to pet him and hear him purr.
- **Context Menu (Right Click):**
  - **Feed:** Offer Digimon meat on the bone, delicious hamburger, or sweet candy.
  - **Drink:** Serve fresh water, hot tea, or energizing coffee.
  - **Rest Controls:** Put Hackmon to sleep or wake him up.
  - **Chase Mouse:** Activate the cursor-hunting mode.
  - **Email Alerts (Outlook):** Check for new incoming emails manually or toggle email notification alerts.
  - **Drop from Top:** Fun action to drop Hackmon from the top of the monitor.
  - **Sound Toggle:** Enable or mute sound effects.
- **📬 Email Notification Assistant (Outlook Classic):**
  - Lightweight background watcher querying Outlook's local Inbox every 25 seconds via `pywin32` COM without dropping GUI framerates.
  - Zero cloud credentials or app passwords needed: automatically syncs with your desktop Outlook email.
  - Hackmon jumps with excitement, plays an alert sound, and displays the sender and subject in a customized speech bubble whenever an unread email arrives.
- **Speech Bubble & Audio Effects:**
  - Interactive speech bubbles showing Hackmon's thoughts, reactions, and dialogue.
  - Procedural sound effects for landings, purrs, snacks, and emotions.

---

## 🚀 Requirements

- Python 3.10+
- Dependencies in `requirements.txt`:
  - `PyQt6` (GUI framework)
  - `Pillow` (Image processing)
  - `pynput` (Input tracking)
  - `pywin32` (Windows desktop and window detection)

---

## 🛠️ Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/JuanD-Arango/DesktopBuddy.git
   cd DesktopBuddy
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   ```

3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

---

## ▶️ Running

Run the main script:

```bash
python main.py
```

Or run using the provided Windows batch files (`ejecutar_hackmon.bat` or `ejecutar_con_consola.bat`).
