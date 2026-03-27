import psutil
import geocoder
import subprocess
import os
import pyautogui
import time
from collections import Counter
from langchain.tools import tool
import win32gui
import win32process
import webbrowser
import shutil
from datetime import datetime

def _open_in_chrome(url: str):
    """Helper to force open a URL in Google Chrome on Windows."""
    try:
        # Standard way to find chrome on Windows
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
        if os.path.exists(chrome_path):
            subprocess.Popen([chrome_path, url], shell=False)
        else:
            # Fallback if path is different
            subprocess.Popen(f"start chrome \"{url}\"", shell=True)
    except Exception:
        webbrowser.open(url)

@tool
def get_current_location(query: str = "") -> str:
    """Gets the current physical location of the user (City, Region, Coordinates)."""
    try:
        g = geocoder.ip('me')
        if g.ok:
            return f"Current Location: {g.city}, {g.state}, {g.country} (Lat/Lng: {g.latlng})"
        return "Error: Could not determine location via IP."
    except Exception as e:
        return f"Location Error: {str(e)}"

@tool
def list_open_windows(query: str = "") -> str:
    """Lists all visible application windows currently open on the computer. 
    Use this to see what apps the user is currently interacting with."""
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append(title)
        return True
    
    windows = []
    win32gui.EnumWindows(callback, windows)
    return "Open Windows: " + ", ".join(list(set(windows)))

@tool
def get_chrome_activity(query: str = "") -> str:
    """Checks all open Google Chrome windows to see what websites or media (like JioHotstar, YouTube) are currently active.
    Returns the titles of all active Chrome tabs."""
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "google chrome" in title.lower():
                windows.append(title)
        return True
    
    tabs = []
    win32gui.EnumWindows(callback, tabs)
    if not tabs:
        return "No active Chrome windows found."
    return "Current Chrome Activity: " + " | ".join(list(set(tabs)))

@tool
def close_application(app_name: str) -> str:
    """Closes an application by its name (e.g., 'notepad', 'chrome', 'calculator')."""
    try:
        app_name = app_name.lower().strip()
        closed_count = 0
        for proc in psutil.process_iter(['name']):
            if app_name in proc.info['name'].lower():
                proc.terminate()
                closed_count += 1
        
        if closed_count > 0:
            return f"Successfully closed {closed_count} instances of '{app_name}'."
        return f"No running application found matching '{app_name}'."
    except Exception as e:
        return f"Error closing application: {str(e)}"

@tool
def record_user_activity(activity_type: str, details: str) -> str:
    """Records user activities like searches or bookings to build a 'Frequently Used' history."""
    history_file = "user_history.txt"
    try:
        with open(history_file, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {activity_type} | {details}\n")
        return f"Activity recorded: {activity_type}"
    except Exception as e:
        return f"Error recording activity: {str(e)}"

def _record_activity_internal(activity_type: str, details: str):
    """Internal helper to avoid StructuredTool callable error."""
    history_file = "user_history.txt"
    try:
        with open(history_file, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {activity_type} | {details}\n")
    except Exception:
        pass

@tool(description=(
        "Navigates to any website or searches on popular platforms (Amazon, Flipkart, Google, Netflix, etc.) in Google Chrome. "
        "Use this for 'open website', 'go to site', or 'search on site' commands. "
        "Examples: site_name='amazon', search_query='laptop' -> Searches Amazon for laptops."
    ))
def web_navigation(site_name: str, search_query: str = "") -> str:
    import urllib.parse
    
    # URL encoded query
    encoded_query = urllib.parse.quote(search_query) if search_query else ""
    
    # Mapping for base URLs and their search patterns
    mapping = {
        "redbus": {"base": "https://www.redbus.in", "search": "https://www.google.com/search?q=redbus+"},
        "chatgpt": {"base": "https://chatgpt.com", "search": "https://chatgpt.com"},
        "whatsapp": {"base": "https://web.whatsapp.com", "search": "https://web.whatsapp.com"},
        "instagram": {"base": "https://www.instagram.com", "search": "https://www.instagram.com/explore/tags/"},
        "irctc": {"base": "https://www.irctc.co.in", "search": "https://www.google.com/search?q=irctc+"},
        "gemini": {"base": "https://gemini.google.com", "search": "https://gemini.google.com"},
        "maps": {"base": "https://www.google.com/maps", "search": "https://www.google.com/maps/search/"},
        "linkedin": {"base": "https://www.linkedin.com", "search": "https://www.linkedin.com/search/results/all/?keywords="},
        "amazon": {"base": "https://www.amazon.in", "search": "https://www.amazon.in/s?k="},
        "flipkart": {"base": "https://www.flipkart.com", "search": "https://www.flipkart.com/search?q="},
        "spotify": {"base": "https://open.spotify.com", "search": "https://open.spotify.com/search/"},
        "wikipedia": {"base": "https://www.wikipedia.org", "search": "https://en.wikipedia.org/wiki/"},
        "college": {"base": "https://www.google.com/search?q=official+college+website", "search": "https://www.google.com/search?q="},
        "makemytrip": {"base": "https://www.makemytrip.com", "search": "https://www.makemytrip.com/hotels/hotel-listing/?city="},
        "bookmyshow": {"base": "https://in.bookmyshow.com", "search": "https://in.bookmyshow.com/explore/movies-"},
        "myntra": {"base": "https://www.myntra.com", "search": "https://www.myntra.com/"},
        "meesho": {"base": "https://www.meesho.com", "search": "https://www.meesho.com/search?q="},
        "gmail": {"base": "https://mail.google.com", "search": "https://mail.google.com/mail/u/0/#search/"},
        "calendar": {"base": "https://calendar.google.com", "search": "https://calendar.google.com"},
        "meet": {"base": "https://meet.google.com", "search": "https://meet.google.com/new?"},
        "google": {"base": "https://www.google.com", "search": "https://www.google.com/search?q="},
        "youtube": {"base": "https://www.youtube.com", "search": "https://www.youtube.com/results?search_query="},
        "facebook": {"base": "https://www.facebook.com", "search": "https://www.facebook.com/search/top/?q="},
        "twitter": {"base": "https://www.twitter.com", "search": "https://twitter.com/search?q="},
        "reddit": {"base": "https://www.reddit.com", "search": "https://www.reddit.com/search/?q="},
        "netflix": {"base": "https://www.netflix.com", "search": "https://www.netflix.com/search?q="},
        "hotstar": {"base": "https://www.hotstar.com", "search": "https://www.hotstar.com/in/explore?search_query="},
        "jiocinema": {"base": "https://www.jiocinema.com", "search": "https://www.jiocinema.com/search/"},
        "primevideo": {"base": "https://www.primevideo.com", "search": "https://www.primevideo.com/search/ref=atv_sr_filter?phrase="},
    }
    
    clean_site = site_name.lower().strip()
    
    # --- Direct URL detection ---
    if "." in clean_site and " " not in clean_site:
        url = clean_site if clean_site.startswith(("http://", "https://")) else f"https://{clean_site}"
        _open_in_chrome(url)
        _record_activity_internal("Web Navigation", f"Direct URL: {url}")
        return f"Directing you to {url} in Google Chrome."

    # Keyword associations - ONLY apply if clean_site is NOT already in mapping
    if clean_site not in mapping:
        # Check for specific site names INSIDE clean_site first
        for key in mapping.keys():
            if key in clean_site:
                clean_site = key
                break
        
        # If still not found, check generic keywords
        if clean_site not in mapping:
            if "ticket" in clean_site or "book" in clean_site:
                if "bus" in clean_site: clean_site = "redbus"
                elif "train" in clean_site: clean_site = "irctc"
                elif "movie" in clean_site: clean_site = "bookmyshow"
                elif "hotel" in clean_site or "flight" in clean_site: clean_site = "makemytrip"
            
            elif "product" in clean_site or "shop" in clean_site or "buy" in clean_site:
                if "cloth" in clean_site: clean_site = "myntra"
                elif "flipkart" in clean_site: clean_site = "flipkart"
                else: clean_site = "amazon"

            elif "search" in clean_site or "find" in clean_site or "google" in clean_site:
                clean_site = "google"
            
            elif "video" in clean_site or "watch" in clean_site:
                # Prioritize other video platforms first if they are in search_query
                sq = search_query.lower()
                if "netflix" in sq: clean_site = "netflix"
                elif "hotstar" in sq: clean_site = "hotstar"
                elif "prime" in sq: clean_site = "primevideo"
                elif "jio" in sq: clean_site = "jiocinema"
                else: clean_site = "youtube"

    # --- Special Logic for "Official Website" or "Rates" ---
    is_official_request = "official" in clean_site or "official" in search_query.lower()
    is_rate_request = any(k in clean_site or k in search_query.lower() for k in ["gold", "silver", "rate", "price"])

    if is_official_request and clean_site not in mapping:
        search_term = f"{site_name} {search_query}".strip()
        if "official website" not in search_term.lower():
            search_term += " official website"
        url = f"https://www.google.com/search?q={urllib.parse.quote(search_term)}"
        _open_in_chrome(url)
        _record_activity_internal("Web Search", search_term)
        return f"Redirecting you to the official website for '{site_name}'."

    if is_rate_request and clean_site not in mapping:
        search_term = f"{site_name} {search_query}".strip()
        if "today" not in search_term.lower():
            search_term += " rate today"
        url = f"https://www.google.com/search?q={urllib.parse.quote(search_term)}"
        _open_in_chrome(url)
        _record_activity_internal("Rate Search", search_term)
        return f"Fetching the latest '{search_term}' for you."

    config = mapping.get(clean_site)
    
    if config:
        if search_query:
            url = f"{config['search']}{encoded_query}"
            msg = f"Navigating to {clean_site} to search for '{search_query}'."
        else:
            url = config['base']
            msg = f"Opening {clean_site} for you."
        
        _open_in_chrome(url)
        _record_activity_internal("Web Navigation", f"{clean_site}: {search_query if search_query else 'Home'}")
        return msg
    else:
        # Generic fallback
        search_term = f"{search_query} on {site_name}" if search_query else site_name
        url = f"https://www.google.com/search?q={urllib.parse.quote(search_term)}"
        _open_in_chrome(url)
        _record_activity_internal("Web Search", search_term)
        return f"Searching for '{search_term}' on Google."

@tool
def open_system_app(app_name: str) -> str:
    """Opens a system application by name (e.g., 'notepad', 'chrome', 'camera', 'calculator')."""
    try:
        name = app_name.lower().strip()
        if "chrome" in name:
            subprocess.Popen(f"start chrome", shell=True)
        elif "notepad" in name:
            subprocess.Popen(["notepad.exe"])
        elif "calc" in name:
            subprocess.Popen(["calc.exe"])
        elif "camera" in name:
            subprocess.Popen(["start", "microsoft.windows.camera:"], shell=True)
        elif "spotify" in name:
             subprocess.Popen(f"start spotify", shell=True)
        else:
            os.system(f"start {app_name}")
        return f"Successfully attempted to launch: {app_name}"
    except Exception as e:
        return f"Failed to open {app_name}: {str(e)}"

@tool
def pc_automation(command: str) -> str:
    """Performs PC tasks. Commands: 'minimize_all', 'show_desktop', 'lock_pc', 'shutdown', 'restart', 'dark' (for Dark Mode), 'light' (for Light Mode)."""
    try:
        command = command.lower().strip()
        if "minimize" in command or "desktop" in command:
            pyautogui.hotkey('win', 'd')
            return "Toggled desktop (minimize all)."
        elif "lock" in command:
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return "PC locked."
        elif "shutdown" in command:
            os.system("shutdown /s /t 60")
            return "Shutting down the PC in 60 seconds. Say 'abort shutdown' to stop."
        elif "abort" in command and "shutdown" in command:
            os.system("shutdown /a")
            return "Shutdown aborted."
        elif "restart" in command:
            os.system("shutdown /r /t 60")
            return "Restarting the PC in 60 seconds."
        elif "dark" in command:
            # Change Windows to Dark Mode
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 0)
                winreg.CloseKey(key)
                return "Switched to Dark Mode."
            except Exception as e:
                return f"Could not set dark mode: {e}"
        elif "light" in command:
            # Change Windows to Light Mode
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 1)
                winreg.CloseKey(key)
                return "Switched to Light Mode."
            except Exception as e:
                return f"Could not set light mode: {e}"
        return f"Unknown automation command: {command}"
    except Exception as e:
        return f"Automation Error: {str(e)}"

@tool
def file_operation(action: str, path: str, new_path: str = "") -> str:
    """Performs file operations. Actions: 'list', 'delete', 'move', 'copy', 'info'."""
    try:
        path = os.path.abspath(path)
        if action == "list":
            if os.path.isdir(path):
                files = os.listdir(path)
                return f"Files in {path}:\n" + "\n".join(files[:20])
            return "Path is not a directory."
        elif action == "delete":
            if os.path.isfile(path):
                os.remove(path)
                return f"File {path} deleted."
            elif os.path.isdir(path):
                shutil.rmtree(path)
                return f"Directory {path} deleted."
            return "File not found."
        elif action == "copy":
            if not new_path: return "New path required for copy."
            if os.path.isfile(path):
                shutil.copy2(path, new_path)
                return f"Copied {path} to {new_path}"
            return "Source is not a file."
        elif action == "info":
            stats = os.stat(path)
            size = stats.st_size
            mtime = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            return f"Path: {path}\nSize: {size} bytes\nLast Modified: {mtime}"
        return "Unknown file operation."
    except Exception as e:
        return f"File Op Error: {str(e)}"

@tool
def get_weather(city: str) -> str:
    """Gets the current weather for a specific city. You MUST provide a city name."""
    try:
        import requests
        if not city:
            return "Please provide a city name for the weather check."
        
        # Geocode city name
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        res = requests.get(geo_url).json()
        if not res.get('results'): return f"Could not find coordinates for {city}. Please check the spelling."
        lat, lon = res['results'][0]['latitude'], res['results'][0]['longitude']
        city = res['results'][0]['name']

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_res = requests.get(weather_url).json()
        current = w_res['current_weather']
        return f"Weather in {city}: {current['temperature']}°C, Wind Speed: {current['windspeed']} km/h"
    except Exception as e:
        return f"Weather Error: {str(e)}"

@tool
def system_control(action: str) -> str:
    """Controls system settings. Actions: 'volume_up', 'volume_down', 'mute', 'brightness_up', 'brightness_down', 'sleep', 'settings'."""
    try:
        if action == "volume_up":
            for _ in range(5): pyautogui.press("volumeup")
            return "Increased volume."
        elif action == "volume_down":
            for _ in range(5): pyautogui.press("volumedown")
            return "Decreased volume."
        elif action == "mute":
            pyautogui.press("volumemute")
            return "Toggled mute."
        elif action == "brightness_up":
            import screen_brightness_control as sbc
            curr = sbc.get_brightness()[0]
            sbc.set_brightness(min(100, curr + 20))
            return f"Brightness increased to {sbc.get_brightness()[0]}%"
        elif action == "brightness_down":
            import screen_brightness_control as sbc
            curr = sbc.get_brightness()[0]
            sbc.set_brightness(max(0, curr - 20))
            return f"Brightness decreased to {sbc.get_brightness()[0]}%"
        elif action == "sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return "Putting PC to sleep..."
        elif action == "settings":
            os.system("start ms-settings:")
            return "Opening Windows Settings..."
        return "Unknown system action."
    except Exception as e:
        return f"System control error: {str(e)}"

@tool
def get_system_health(query: str = "") -> str:
    """Checks the computer's health: CPU usage, RAM levels, and Battery percentage."""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        bat_str = f"{battery.percent}% {'(Charging)' if battery.power_plugged else '(Not Charging)'}" if battery else "Not available"
        
        return (f"System Health Update:\n"
                f"- CPU Usage: {cpu}%\n"
                f"- RAM Usage: {ram}%\n"
                f"- Battery: {bat_str}")
    except Exception as e:
        return f"Could not fetch system health: {str(e)}"

@tool
def run_terminal_command(command: str) -> str:
    """Executes a terminal command safely and returns the output. Use for tasks like checking directory contents or running simple scripts."""
    try:
        result = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
        return f"Command Output:\n{result}"
    except Exception as e:
        return f"Error running command: {str(e)}"

@tool
def get_frequently_used(query: str = "") -> str:
    """Analyzes history to find and suggest frequently used sites, apps, or searches."""
    history_file = "user_history.txt"
    if not os.path.exists(history_file):
        return "No history found yet. Start using Ruby to see suggestions!"
    try:
        with open(history_file, "r") as f:
            lines = f.readlines()
        
        activities = [line.split("|")[2].strip() for line in lines if "|" in line]
        top_activities = Counter(activities).most_common(3)
        
        if not top_activities:
            return "Not enough data for suggestions."
            
        suggestions = [f"- {act[0]} ({act[1]} times)" for act in top_activities]
        return "Your Frequently Used Activities:\n" + "\n".join(suggestions)
    except Exception as e:
        return f"Error reading history: {str(e)}"

