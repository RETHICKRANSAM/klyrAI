from utiles.api_brain import get_brain
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from dotenv import load_dotenv
import sys
import os

# Ensure utils can be imported by adding parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utiles.tts import RubyTTS
from utiles.stt import RubySTT
from utiles.prompt import system_prompt
from utiles.ruby_tools import (
    YouTubeVideoPlayerTool,
    GetAvailableLanguagesTool,
    SwitchLanguageTool,
    GetLatestNewsTool,
    DuckDuckGoSearchTool,
    SarvamBatchSTTTool,
    TwilioReminderTool,
    SummarizeTextTool,
    GhostCursorTool,
)
from utiles.toolbox import (
    calculator,
    query_document,
    arduino_serial_communication,
)
from utiles.pc_tools import (
    get_current_location,
    list_open_windows,
    open_system_app,
    system_control,
    web_navigation,
    get_system_health,
    run_terminal_command,
    record_user_activity,
    get_frequently_used,
    close_application,
    pc_automation,
    file_operation,
    get_weather,
    get_chrome_activity,
)
load_dotenv()


class Ruby:
    """
    Ruby Mainframe Class.

    This class serves as the central brain of the Ruby assistant. 
    It integrates Speech-to-Text (STT), Text-to-Speech (TTS), and the AI
    brain logic to handle user interactions and tool execution.
    """
    def __init__(self, tts=None, model=None, system_prompt=system_prompt, tools=[], stt=None):
        """
        Initialize the Ruby agent.

        Args:
            tts: RubyTTS instance (optional).
            model: Optional model name override.
            system_prompt: System instructions for the agent.
            tools: List of additional tools.
            stt: RubySTT instance (optional).
        """
        self.ruby_state = "Idle"
        self.system_prompt = system_prompt
        
        # Combine default built-in tools with any extra tools provided
        self.tools = [
                        web_navigation,                 # Navigate to websites (Chrome Focus)
                        YouTubeVideoPlayerTool(self),   # Tool for playing YouTube videos
                        GetAvailableLanguagesTool(self), # Tool to check supported languages
                        SwitchLanguageTool(self),       # Tool to switch active language
                        GetLatestNewsTool(),            # Tool to fetch latest news (DuckDuckGo)
                        DuckDuckGoSearchTool(),         # FREE web search engine (no key needed)
                        calculator,                     # Basic calculator
                        query_document,                 # RAG document query tool
                        arduino_serial_communication,   # Hardware control tool
                        get_current_location,           # Get IP-based location
                        list_open_windows,              # See open apps
                        open_system_app,                # Start apps
                        system_control,                 # Volume/System control
                        get_system_health,              # Check CPU/Battery
                        run_terminal_command,           # Execute terminal commands
                        record_user_activity,           # Log user actions
                        get_frequently_used,            # Suggest popular actions
                        close_application,              # Close running apps
                        pc_automation,                  # System automation (Minimize, Lock, etc.)
                        file_operation,                 # File management (List, Info, Copy)
                        get_weather,                    # Weather info
                        get_chrome_activity,            # NEW: Identify what is playing in Chrome/JioHotstar
                        SarvamBatchSTTTool(),           # NEW: Batch Speech-to-Text
                        TwilioReminderTool(),           # Twist Reminder
                        SummarizeTextTool(),            # Text Summarization Tool
                        GhostCursorTool(),              # PyAutoGUI Ghost Cursor Action
                    ] + tools

        # Initialize TTS (Text-to-Speech) — uses Edge-TTS (FREE, no key)
        if tts is None:
            self.tts = RubyTTS(language="en-IN")
        else:
            self.tts = tts
            
        # Initialize STT (Speech-to-Text)
        if stt is None:
            self.stt = RubySTT(language_code="en")
        else:
            self.stt = stt

        self.system_prompt = system_prompt
        # Initialize conversation history with the system prompt
        self.chat_history = {"messages": [SystemMessage(content=self.system_prompt)]}
        
        # Create the brain (Groq/Gemini/DuckDuckGo — all free options)
        self.model = get_brain()
        print(f"✅ Klyra Brain loaded: {type(self.model).__name__}")

    def _run_tool(self, user_lower, user_input):
        return None


    def speak(self, user_input, play_audio=True):
        """
        Process user input and generate a response.
        """
        if not user_input:
            return ""

        # FORCE IDENTITY OVERRIDE
        creator_keywords = ["who created you", "who developed you", "who is your creator", "who made you"]
        hod_aiml_keywords = ["who is the hod of aiml", "head of aiml", "hod of ai and ml"]
        
        user_lower = user_input.lower()
        response_text = None

        if any(keyword in user_lower for keyword in creator_keywords):
            response_text = "I was developed by MR. DR. SIVA PRAKASH at Mensch Robotics, Coimbatore."
        elif any(keyword in user_lower for keyword in hod_aiml_keywords):
            response_text = "The HOD of AIML is MR. DR. SIVA PRAKASH."

        if response_text:
            self.chat_history["messages"].append(HumanMessage(content=user_input))
            self.chat_history["messages"].append(AIMessage(content=response_text))
            if play_audio:
                self.ruby_state = "Speaking"
                self.tts.text_to_speech(response_text)
                self.ruby_state = "Idle"
            return response_text

        # --- AI BRAIN (Groq / Gemini / DuckDuckGo) ---
        self.ruby_state = "Thinking"
        self.chat_history["messages"].append(HumanMessage(content=user_input))
        
        try:
            # Pass BOTH messages and tools to the brain
            response = self.model.invoke({
                "messages": self.chat_history["messages"],
                "tools": self.tools
            })
            
            ai_message = response["messages"][-1]
            self.chat_history["messages"].append(ai_message)
            
            res_content = ai_message.content
            if play_audio:
                self.ruby_state = "Speaking"
                self.tts.text_to_speech(res_content)
                self.ruby_state = "Idle"
            
            return res_content
        except Exception as e:
            self.ruby_state = "Idle"
            if "quota" in str(e).lower() or "429" in str(e):
                err_msg = "API limit reached. Get a free Groq key at console.groq.com and add it to your .env file!"
            elif "401" in str(e) or "invalid" in str(e).lower():
                err_msg = "API key is invalid. Please check your .env file and add a valid key."
            else:
                err_msg = f"I encountered an error: {str(e)}"
            
            if play_audio:
                self.tts.text_to_speech(err_msg)
            return err_msg
    
    def listen(self):
        """
        Listen for user audio input using the microphone.
        """
        self.ruby_state = "Listening"
        transcript = self.stt.listen()
        if transcript:
            print(f"User: {transcript}")
        self.ruby_state = "Idle"
        return transcript

    def speech_to_respond(self, audio_bytes):
        """
        Complete Voice-to-Voice pipeline: Audio -> Text -> AI -> Text -> Audio
        """
        # 1. Transcribe
        self.ruby_state = "Hearing You"
        transcript = self.stt.transcribe_audio(audio_bytes)
        if not transcript:
            return None, None, None
            
        # 2. Process via AI
        self.ruby_state = "Thinking"
        response_text = self.speak(transcript, play_audio=False)
        
        # 3. Generate Speech Audio
        self.ruby_state = "Responding"
        audio_b64 = self.tts.get_speech_base64(response_text)
        
        self.ruby_state = "Ready"
        return transcript, response_text, audio_b64

    def reset(self):
        """Reset the conversation history to the initial system prompt."""
        self.chat_history = {"messages": [SystemMessage(content=self.system_prompt)]}
        self.ruby_state = "Idle"

    def run(self):
        """
        Main loop for Ruby with Wake Word and Keyboard Shortcut support.
        """
        try:
            import keyboard
            has_keyboard = True
        except ImportError:
            has_keyboard = False
            
        print("\n--- Klyra is in Standby Mode ---")
        print("Say 'HELLO KLYRA' to start or press 'Ctrl+Shift+R'")
        
        is_active = False

        def set_active():
            nonlocal is_active
            is_active = True
            print("\n[Shortcut Triggered] Klyra is now Listening!")
            self.tts.text_to_speech("How can I help you?")

        if has_keyboard:
            keyboard.add_hotkey('ctrl+shift+r', set_active)

        while True:
            try:
                if not is_active:
                    self.ruby_state = "Standby"
                    transcript = self.listen()
                    if transcript and "hello klyra" in transcript.lower():
                        is_active = True
                        print("--- Klyra Activated ---")
                        self.tts.text_to_speech("Hello! I am Klyra. How can I assist you today?")
                    continue

                user_input = self.listen()
                if user_input:
                    user_lower = user_input.lower()
                    
                    if "bye klyra" in user_lower or "go to sleep" in user_lower:
                        print("--- Klyra Going to Sleep ---")
                        self.tts.text_to_speech("Goodbye! Say hello klyra whenever you need me.")
                        is_active = False
                        continue
                        
                    self.speak(user_input)
                    
            except KeyboardInterrupt:
                print("\nShutting down Klyra...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
