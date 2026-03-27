from langchain_core.tools import tool
import serial
import time
from utiles import rag_utiles

@tool
def calculator(query: str) -> str:
    """Evaluates a basic mathematical expression provided as a string. 
    Supports arithmetic operations like addition, subtraction, multiplication, division, and parentheses."""
    try:
        return str(eval(query))
    except Exception as e:
        return str(e)

@tool
def arduino_serial_communication(query: str) -> str:
    """Communicates with an Arduino device via serial connection."""
    import platform
    try:
        # Check OS for default port
        port = 'COM3' if platform.system() == 'Windows' else '/dev/ttyUSB0'
        ser = serial.Serial(port, 9600, timeout=1)
        time.sleep(2)
        ser.write(query.encode())
        ser.close()
        return f"Arduino Serial Communication Successful on {port}"
    except Exception as e:
        return f"Serial Error on {port if 'port' in locals() else 'unknown port'}: {str(e)}"

@tool
def query_document(query: str) -> str:
    """Queries a document using the RubyRAG class."""
    try:
        return rag_utiles.RubyRAG().query(query)
    except Exception as e:
        return str(e)