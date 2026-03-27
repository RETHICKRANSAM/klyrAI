"""
KLYRA AI - Unified Backend Entry Point
"""
import os
import sys

# Fix path to allow local imports from 'web_server'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:    
    from web_server import app, socketio
except Exception as e:
    import traceback
    print(f"CRITICAL BOOT ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    print(f"🚀 KLYRA Backend launching on port {port}...")
    try:
        # Disable reloader to prevent port-binding issues on Windows
        socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True, debug=True, use_reloader=False)
    except Exception as e:
        print(f"CRITICAL RUNTIME ERROR: {e}")
        import traceback
        traceback.print_exc()
