from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import threading
import os
import sys
import time
import io
import base64

# Fix Windows charmap encoding issue for Unicode output
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path to import Ruby
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from ruby.ruby_mainframe import Ruby

# Serve static files from the 'static' folder
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False, max_payload=50_000_000)

# Initialize Ruby instance
ruby = Ruby()

# --- SERVE FRONTEND ---
@app.route('/')
def serve_index():
    return send_from_directory(STATIC_DIR, 'index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('state_change', {'state': ruby.ruby_state})

@socketio.on('init_session')
def handle_init_session():
    print('Session Initialized by user')
    greeting = "Hello! Klyra AI is online. How can I assist you today?"
    emit('new_message', {'sender': 'Ruby', 'text': greeting})
    try:
        audio_b64 = ruby.tts.get_speech_base64(greeting)
        if audio_b64:
            emit('speak_audio', {'audio': audio_b64})
    except Exception as e:
        print(f"TTS error: {e}")

@socketio.on('text_input')
def handle_text(data):
    text = data.get('text')
    if not text: return
    emit('new_message', {'sender': 'User', 'text': text})
    emit('state_change', {'state': 'Thinking'})
    response = ruby.speak(text, play_audio=False)
    emit('new_message', {'sender': 'Ruby', 'text': response})
    emit('state_change', {'state': 'Ready'})
    try:
        audio_b64 = ruby.tts.get_speech_base64(response)
        if audio_b64: emit('speak_audio', {'audio': audio_b64})
    except Exception as e: print(f"TTS error: {e}")

@socketio.on('mobile_audio')
def handle_audio(data):
    audio_b64 = data.get('audio')
    if not audio_b64: return
    audio_bytes = base64.b64decode(audio_b64)
    transcript, response, audio_res_b64 = ruby.speech_to_respond(audio_bytes)
    if transcript:
        emit('new_message', {'sender': 'User', 'text': transcript})
        emit('new_message', {'sender': 'Ruby', 'text': response})
        if audio_res_b64: emit('speak_audio', {'audio': audio_res_b64})

@socketio.on('set_gender')
def handle_gender(data):
    gender = data.get('gender')
    if gender:
        from utiles.tts import RubyTTS
        ruby.tts = RubyTTS(language="en-IN" if gender=='Boy' else "en-US")
        print(f"Gender changed to {gender}")
