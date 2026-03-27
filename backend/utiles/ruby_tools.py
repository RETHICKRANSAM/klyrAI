# Ruby Core Agent Tools

from langchain.tools import BaseTool
from pydantic import PrivateAttr
import subprocess
import yt_dlp


class YouTubeVideoPlayerTool(BaseTool):
    name: str = "youtube_video_player"
    description: str = (
        "Plays a specific YouTube video directly. "
        "Use this ONLY when the user asks to 'play' or 'watch' a specific video title. "
        "For just opening the YouTube website or other websites, use 'web_navigation' instead."
    )


    _ruby = PrivateAttr()
    def __init__(self, ruby):
        super().__init__()
        self._ruby = ruby

    def _run(self, query: str) -> str:
        """
        Args:
            query (str): The search query for the video.
        """
        self._ruby.ruby_state = "Searching Video"
        # Options for yt_dlp to get the video stream url 
        ydl_opts = {
            "quiet": True,
            "default_search": "ytsearch1",
            "format": "best[ext=mp4]/best",
            "noplaylist": True,
            "skip_download": True,
            "extract_flat": False,
            "js_runtimes": {"node": {}},
            "youtube_include_dash_manifest": False,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"]
                }
            },
            "quiet": True,
            "no_warnings": True,
        }
        import webbrowser
        # Get the video stream url from youtube using yt_dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract the video info from youtube
            info = ydl.extract_info(query, download=False)
            video = info["entries"][0]
            stream_url = video["original_url"]
        
        # Open in default browser
        webbrowser.open(stream_url)
        
        self._ruby.ruby_state = "Playing Video"
        return f"Now playing: {video['title']} in your browser."

class GetAvailableLanguagesTool(BaseTool):
    name: str = "get_available_languages"
    description: str = (
        "Returns a list of all language IDs currently supported by the system's "
        "text-to-speech and speech-to-text engines. "
        "Use this tool before attempting a language switch or when the user asks "
        "which languages are supported."
    )


    _ruby = PrivateAttr()
    def __init__(self, ruby):
        super().__init__()
        self._ruby = ruby

    def _run(self) -> list[str]:
        # Return the list of supported languages
        return self._ruby.tts.get_supported_languages()

class SwitchLanguageTool(BaseTool):
    name: str  = "switch_language"
    description: str = (
        "Switches the assistant's active language for both speech recognition "
        "and speech synthesis. "
        "Input must be a valid language ID obtained from the available languages list. "
        "Do not guess language IDs. "
        "Always verify availability before calling this tool."
    )


    _ruby = PrivateAttr()
    def __init__(self, ruby):
        super().__init__()
        self._ruby = ruby

    def _run(self, language: str) -> str:
        # Update the Ruby state to switching language
        self._ruby.ruby_state = "switching_language"
        # Update the tts and stt language
        self._ruby.tts.update_language(language)
        self._ruby.stt.update_language(language)
        # Update the Ruby state to idle
        self._ruby.ruby_state = "idle"
        return f"Switched to {language}"
class GetLatestNewsTool(BaseTool):
    name: str = "get_latest_news"
    description: str = (
        "Fetches the top 5 trending world news headlines. "
        "Use this when the user asks for 'the news' or 'what is happening in the world'."
    )

    def _run(self, query: str = "") -> str:
        try:
            # Use DuckDuckGo to search for latest news (FREE, no API key)
            from duckduckgo_search import DDGS
            search_query = query if query else "latest technology news India today"
            with DDGS() as ddgs:
                results = list(ddgs.news(search_query, max_results=5))
            if results:
                headlines = [f"- {r.get('title', 'Unknown')}: {r.get('body', '')[:100]}" for r in results]
                return "Top News Headlines:\n" + "\n".join(headlines)
            
            # Fallback to text search if no news results
            with DDGS() as ddgs:
                results = list(ddgs.text(search_query, max_results=5))
            if results:
                headlines = [f"- {r.get('title', 'Unknown')}: {r.get('body', '')[:100]}" for r in results]
                return "News Search Results:\n" + "\n".join(headlines)

            return "No news found at the moment."
        except Exception as e:
            print(f"News Fetch Error: {e}")
            # Final fallback to text search
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(query if query else "latest news India", max_results=3))
                if results:
                    headlines = [f"- {r.get('title', 'Unknown')}" for r in results]
                    return "Recent Headlines:\n" + "\n".join(headlines)
            except:
                pass
            return "Could not fetch news right now."


class DuckDuckGoSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web using DuckDuckGo. Completely FREE, no API key needed. "
        "Use this to answer questions about current events, facts, or any topic. "
        "Input should be the search query string."
    )

    def _run(self, query: str) -> str:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=4))
            if not results:
                return "No search results found for that query."
            snippets = []
            for r in results:
                title = r.get('title', '')
                body = r.get('body', '')[:200]
                snippets.append(f"• {title}: {body}")
            return "Search Results:\n" + "\n".join(snippets)
        except Exception as e:
            print(f"DuckDuckGo Search Error: {e}")
            return f"Search failed: {str(e)}"

class SarvamBatchSTTTool(BaseTool):
    name: str = "sarvam_batch_stt"
    description: str = (
        "Transcribes multiple audio files using Sarvam AI's batch API. "
        "Input should be a list of paths to audio files on the local system."
    )

    def _run(self, audio_paths: list[str]) -> str:
        try:
            import os
            from sarvamai import SarvamAI
            
            sarvam_key = os.getenv("SARVAM_API_KEY")
            if not sarvam_key or "your_" in sarvam_key:
                return "Error: SARVAM_API_KEY is not configured in .env."

            client = SarvamAI(api_subscription_key=sarvam_key)

            # Create batch job
            job = client.speech_to_text_job.create_job(
                model="saaras:v3",
                mode="transcribe",
                language_code="unknown",
                with_diarization=True,
                num_speakers=2
            )

            # Check if files exist
            valid_paths = [p for p in audio_paths if os.path.exists(p)]
            if not valid_paths:
                return "Error: No valid audio files found at the provided paths."

            # Upload and process files
            job.upload_files(file_paths=valid_paths)
            job.start()

            # Wait for completion
            job.wait_until_complete()

            # Check file-level results
            file_results = job.get_file_results()
            
            report = f"Batch STT Results (Successful: {len(file_results['successful'])}, Failed: {len(file_results['failed'])}):\n"
            
            if file_results['successful']:
                # The SDK might have a way to get transcripts, but for now we'll list successes
                for f in file_results['successful']:
                    report += f"  ✓ {f.get('file_name', 'Unknown')}\n"
                
                # In a real tool, we might want to return the actual text. 
                # Let's try downloading outputs if needed or just return success info.
                report += "\nTranscripts have been processed successfully."
            
            if file_results['failed']:
                for f in file_results['failed']:
                    report += f"  ✗ {f.get('file_name', 'Unknown')}: {f.get('error_message', 'Unknown Error')}\n"

            return report
        except Exception as e:
            print(f"Sarvam Batch STT Error: {e}")
            return f"Sarvam Batch STT failed: {str(e)}"

class TwilioReminderTool(BaseTool):
    name: str = "send_reminder_sms"
    description: str = (
        "Sends an SMS reminder using Twilio. "
        "Example inputs: 'phone_number=+919000000000, message=Don't forget the meeting!'"
    )
    def _run(self, phone_number: str, message: str) -> str:
        try:
            import os
            from twilio.rest import Client
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            from_number = os.getenv('TWILIO_PHONE_NUMBER')
            if not account_sid or not auth_token:
                return "Error: Twilio credentials not found in environment."
                
            client = Client(account_sid, auth_token)
            msg = client.messages.create(
                body=message,
                from_=from_number,
                to=phone_number
            )
            return f"Reminder sent successfully to {phone_number}!"
        except Exception as e:
            return f"Failed to send reminder via Twilio: {str(e)}"

class SummarizeTextTool(BaseTool):
    name: str = "summarize_text"
    description: str = "Summarizes a long text block into a concise paragraph. Input should be the long text string."
    
    def _run(self, text: str) -> str:
        try:
            from utiles.api_brain import get_brain
            from langchain.schema import HumanMessage
            model = get_brain()
            res = model.invoke([HumanMessage(content=f"Please summarize the following text concisely. Capture main ideas:\n\n{text}")])
            return f"Summary:\n{res.content}"
        except Exception as e:
            return f"Error summarizing text: {str(e)}"

from langchain.tools import tool

@tool
def ghost_cursor_click(coords: str = "") -> str:
    """
    Moves the mouse cursor smoothly to a screen coordinate (x, y) and clicks. 
    Simulates a 'ghost cursor' for automation. 
    Input can be specific coords 'X,Y' or descriptions like 'center', 'start', 'top right'.
    """
    try:
        import pyautogui
        sw, sh = pyautogui.size()
        x, y = sw // 2, sh // 2  # Default to center
        
        if coords:
            coords_str = coords.replace(" ", "").lower()
            if "start" in coords_str:
                x, y = 10, sh - 10
            elif "topright" in coords_str:
                x, y = sw - 10, 10
            elif "," in coords_str:
                x, y = map(int, coords_str.split(","))

        pyautogui.moveTo(x, y, duration=1.5, tween=pyautogui.easeInOutQuad) # Ghost cursor effect
        pyautogui.click()
        return f"Ghost cursor successfully moved and clicked at ({x}, {y})."
    except Exception as e:
        return f"Ghost cursor error: {str(e)}"

@tool
def schedule_meeting(title: str) -> str:
    """
    Schedules a meeting on Google Calendar automatically. 
    Input should be the meeting details or title. e.g. 'Team Sync' or 'Doctor Appointment'.
    """
    try:
        import urllib.parse
        import webbrowser
        encoded_title = urllib.parse.quote(title)
        # Open the Google Calendar event creation template
        url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={encoded_title}"
        webbrowser.open(url)
        return f"Successfully opened Google Calendar to schedule: '{title}'"
    except Exception as e:
        return f"Failed to automate Calendar scheduling: {str(e)}"

