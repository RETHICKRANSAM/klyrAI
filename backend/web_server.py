from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import os
import sys
import time
import io

# Fix Windows charmap encoding issue for Unicode output
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path to import Ruby
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ruby.ruby_mainframe import Ruby
from utiles.stt import RubySTT
from utiles.tts import RubyTTS

import base64

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True, max_payload=50_000_000)

# Global state for echo prevention
_last_speak_finish_time = 0

# Initialize Ruby instance
ruby = Ruby()

# Sync Ruby's state with Web UI
def update_web_state(state):
    socketio.emit('state_change', {'state': state})

# Wrap Ruby's methods to emit events
original_speak = ruby.speak
original_listen = ruby.listen

def web_speak(user_input, play_audio=True):
    update_web_state('Thinking')
    # Returns the text response ONLY — audio is handled by the caller via _emit_audio
    res = original_speak(user_input, play_audio=False)
    update_web_state('Ready')
    return res

def web_listen():
    update_web_state('Listening')
    transcript = original_listen()
    update_web_state('Idle')
    if transcript:
        socketio.emit('new_message', {'sender': 'User', 'text': transcript})
    return transcript

ruby.speak = web_speak
ruby.listen = web_listen

def _emit_audio(text: str):
    """Generate TTS and emit speak_audio EXACTLY ONCE. Always call this instead of emitting manually."""
    if not text:
        return
    try:
        audio_b64 = ruby.tts.get_speech_base64(text)
        if audio_b64:
            socketio.emit('speak_audio', {'audio': audio_b64})
    except Exception as e:
        print(f"TTS emit error: {e}")

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Removed after_request hook

@app.route('/health')
def health():
    return jsonify({"status": "ok", "assistant": "KLYRA"})

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('state_change', {'state': ruby.ruby_state})

@socketio.on('init_session')
def handle_init_session():
    print('Session Initialized by user')
    greeting = "Hello! Klyra AI is online. How can I assist you today?"
    emit('new_message', {'sender': 'Ruby', 'text': greeting})
    # Single audio emit for the greeting
    _emit_audio(greeting)

@socketio.on('set_gender')
def handle_set_gender(data):
    gender = data.get('gender')
    if gender:
        ruby.tts.set_user_gender(gender)
        print(f"Server: Received gender configuration: User is {gender}")
        confirm = "Voice configured."
        emit('new_message', {'sender': 'Ruby', 'text': confirm})
        # Single audio emit for confirmation
        _emit_audio(confirm)

@socketio.on('text_input')
def handle_text_input(data):
    global _last_speak_finish_time
    text = data.get('text')
    print(f"Server: Received text command: {text}")
    if text:
        try:
            socketio.emit('new_message', {'sender': 'User', 'text': text})
            socketio.emit('state_change', {'state': 'Thinking'})

            # web_speak returns text only — does NOT emit audio internally
            response = ruby.speak(text, play_audio=False)

            if response:
                socketio.emit('new_message', {'sender': 'Ruby', 'text': response})
                socketio.emit('state_change', {'state': 'Speaking'})
                # Emit audio ONCE here — the one and only place
                _emit_audio(response)
                
                # Update cooldown timer
                _last_speak_finish_time = time.time()

            socketio.emit('state_change', {'state': 'Ready'})
        except Exception as e:
            import traceback
            error_msg = f"Klyra AI Error: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            socketio.emit('new_message', {'sender': 'Ruby', 'text': error_msg})
            socketio.emit('state_change', {'state': 'Error'})

@socketio.on('mobile_audio')
def handle_mobile_audio(data):
    global _last_speak_finish_time
    try:
        audio_b64 = data.get('audio')
        if not audio_b64: return
        audio_bytes = base64.b64decode(audio_b64)
        print(f"Processing mobile audio ({len(audio_bytes)} bytes)...")
        # Cooldown check: Ignore audio if it arrives too soon after KLYRA stops speaking (echo)
        now = time.time()
        if now - _last_speak_finish_time < 0.8:  # 800ms "Mute Window"
            print("STT: Ignoring potential echo audio packet")
            return

        # Transcribe directly via Sarvam REST (supports webm natively)
        transcript = _sarvam_transcribe_raw(audio_bytes, fmt='webm')
        
        # Fallback: try Google via wav conversion
        if not transcript:
            transcript = _google_transcribe_raw(audio_bytes)
        
        if not transcript:
            print("STT: No speech detected")
            socketio.emit('state_change', {'state': 'Ready'})
            return

        socketio.emit('new_message', {'sender': 'User', 'text': transcript})

        # web_speak returns text only — does NOT emit audio internally
        response_text = ruby.speak(transcript, play_audio=False)

        if response_text:
            socketio.emit('new_message', {'sender': 'Ruby', 'text': response_text})
            socketio.emit('state_change', {'state': 'Speaking'})
            # Emit audio ONCE here
            _emit_audio(response_text)
            
            # Update cooldown timer
            _last_speak_finish_time = time.time()

        socketio.emit('state_change', {'state': 'Ready'})
    except Exception as e:
        import traceback
        print(f"Error processing mobile audio: {e}")
        traceback.print_exc()
        socketio.emit('state_change', {'state': 'Error'})

def _sarvam_transcribe_raw(audio_bytes: bytes, fmt: str = 'webm') -> str:
    """Transcribe raw audio bytes using Sarvam REST API."""
    try:
        from sarvamai import SarvamAI
        import io as _io
        key = os.environ.get("SARVAM_API_KEY", "")
        if not key or "your_" in key:
            return ""
        client = SarvamAI(api_subscription_key=key)
        mime_map = {
            'webm': 'audio/webm',
            'wav': 'audio/wav',
            'mp3': 'audio/mp3',
            'ogg': 'audio/ogg',
        }
        mime = mime_map.get(fmt, 'audio/webm')
        fname = f"audio.{fmt}"
        resp = client.speech_to_text.transcribe(
            file=(fname, _io.BytesIO(audio_bytes), mime),
            model='saaras:v3',
            mode='transcribe',
            language_code='en-IN',
        )
        text = getattr(resp, 'transcript', '') or ''
        if text:
            print(f"STT (Sarvam REST webm): {text}")
        return text.strip()
    except Exception as e:
        print(f"Sarvam webm STT error: {e}")
        return ""

def _google_transcribe_raw(audio_bytes: bytes) -> str:
    """Try Google STT with WAV format. Returns empty string on failure."""
    try:
        import speech_recognition as sr
        import io as _io
        recognizer = sr.Recognizer()
        with sr.AudioFile(_io.BytesIO(audio_bytes)) as src:
            audio_data = recognizer.record(src)
        return recognizer.recognize_google(audio_data, language='en-IN')
    except Exception as e:
        print(f"Google STT fallback error: {e}")
        return ""


@socketio.on('batch_stt_files')
def handle_batch_stt(data):
    try:
        files = data.get('files', [])
        if not files: return

        save_dir = os.path.join(os.getcwd(), "temp_batch_stt")
        os.makedirs(save_dir, exist_ok=True)
        
        file_paths = []
        for f in files:
            file_name = f.get('name')
            file_data = f.get('data')
            if not file_name or not file_data: continue
            
            p = os.path.join(save_dir, file_name)
            with open(p, "wb") as wb:
                wb.write(base64.b64decode(file_data))
            file_paths.append(p)

        if not file_paths:
            socketio.emit('new_message', {'sender': 'Ruby', 'text': "No valid files received."})
            socketio.emit('state_change', {'state': 'Ready'})
            return

        socketio.emit('new_message', {'sender': 'Ruby', 'text': f"Starting batch transcription for {len(file_paths)} files..."})
        
        from utiles.ruby_tools import SarvamBatchSTTTool
        tool = SarvamBatchSTTTool()
        result = tool._run(file_paths)
        
        socketio.emit('new_message', {'sender': 'Ruby', 'text': result})
        socketio.emit('state_change', {'state': 'Ready'})
        
        # Cleanup
        for p in file_paths:
            try: os.remove(p)
            except: pass
            
    except Exception as e:
        print(f"Error in batch STT: {e}")
        socketio.emit('new_message', {'sender': 'Ruby', 'text': f"Batch STT Error: {str(e)}"})
        socketio.emit('state_change', {'state': 'Error'})

class RubyWorker(threading.Thread):
    def __init__(self, ruby):
        super().__init__(daemon=True)
        self.ruby = ruby
        self.running = True

    def run(self):
        print("Ruby Worker Thread Started")
        while self.running:
            try:
                user_input = self.ruby.listen()
                if user_input:
                    # web_speak returns text only — does NOT emit audio internally
                    response = self.ruby.speak(user_input, play_audio=False)
                    if response:
                        socketio.emit('new_message', {'sender': 'Ruby', 'text': response})
                        socketio.emit('state_change', {'state': 'Speaking'})
                        _emit_audio(response)  # Emit audio ONCE
            except Exception as e:
                try:
                    print(f"Ruby Thread Error: {e}")
                except Exception:
                    pass
                time.sleep(1)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    
    @app.route('/')
    def root():
        return jsonify({"status": "running", "engine": "KLYRA AI API"})

    print(f"Starting server on port {port} with DEBUG=True...")
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"Startup Error: {e}")
