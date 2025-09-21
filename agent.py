# agent.py

import time
import requests
import threading
from pynput import mouse, keyboard

# --- Configuration ---
# Make sure your Flask app is running and accessible at this address
FLASK_SERVER_URL = "http://127.0.0.1:5000"
# This ID should be dynamically set after a user logs in. For now, we hardcode it for testing.
# Replace 'testuser' with a username you registered in the web app.
USER_ID = "test1"
# How often to send data to the server (in seconds)
SEND_INTERVAL = 10

# --- Data Buffers ---
# A thread-safe way to store events
mouse_events = []
keyboard_events = []
lock = threading.Lock()

# --- Event Listeners ---
def on_move(x, y):
    with lock:
        mouse_events.append({'type': 'move', 'x': x, 'y': y, 'time': time.time()})

def on_click(x, y, button, pressed):
    action = 'pressed' if pressed else 'released'
    with lock:
        mouse_events.append({'type': 'click', 'x': x, 'y': y, 'button': str(button), 'action': action, 'time': time.time()})

def on_scroll(x, y, dx, dy):
    with lock:
        mouse_events.append({'type': 'scroll', 'x': x, 'y': y, 'dx': dx, 'dy': dy, 'time': time.time()})

def on_press(key):
    try:
        # Record character keys
        with lock:
            keyboard_events.append({'type': 'press', 'key': key.char, 'time': time.time()})
    except AttributeError:
        # Record special keys (e.g., Shift, Ctrl)
        with lock:
            keyboard_events.append({'type': 'press', 'key': str(key), 'time': time.time()})

def on_release(key):
    try:
        with lock:
            keyboard_events.append({'type': 'release', 'key': key.char, 'time': time.time()})
    except AttributeError:
        with lock:
            keyboard_events.append({'type': 'release', 'key': str(key), 'time': time.time()})

# --- Data Sending Function ---
def send_data_periodically():
    global mouse_events, keyboard_events
    while True:
        # Wait for the specified interval
        time.sleep(SEND_INTERVAL)

        # Safely copy and clear the buffers
        with lock:
            if not mouse_events and not keyboard_events:
                continue # Don't send empty data
            
            mouse_data_to_send = list(mouse_events)
            keyboard_data_to_send = list(keyboard_events)
            mouse_events.clear()
            keyboard_events.clear()
        
        # Prepare the payload
        payload = {
            'user_id': USER_ID,
            'mouse_events': mouse_data_to_send,
            'keyboard_events': keyboard_data_to_send
        }

        # Send the data to the Flask server
        try:
            print(f"Sending {len(mouse_data_to_send)} mouse events and {len(keyboard_data_to_send)} keyboard events...")
            response = requests.post(f"{FLASK_SERVER_URL}/api/authenticate", json=payload)
            if response.status_code == 200:
                print("Data sent successfully. Server response:", response.json())
            else:
                print(f"Error sending data: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Could not connect to the server: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting IGRIS Data Collection Agent...")
    print(f"Target Server: {FLASK_SERVER_URL}")
    print(f"User ID: {USER_ID}")

    # Start the data sending thread
    sender_thread = threading.Thread(target=send_data_periodically, daemon=True)
    sender_thread.start()

    # Start the listeners in the main thread
    # Using 'with' ensures listeners are properly stopped when the script exits
    with mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll) as m_listener, \
         keyboard.Listener(on_press=on_press, on_release=on_release) as k_listener:
        print("Listeners started. Collecting data...")
        m_listener.join()
        k_listener.join()