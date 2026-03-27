# Ruby Utils Folder

This directory contains the core utility modules and tools that power the Ruby agent. These modules handle everything from speech processing to tool execution and system prompting.

## Module Overview

### 1. `ruby_tools.py` vs `toolbox.py`
We distinguish between two types of tools in Ruby to maintain clean architecture:

*   **`ruby_tools.py`**: Contains **Complex Tools** that need to interact directly with the `Ruby` instance state.
    *   Use this when a tool needs to change Ruby's status (e.g., `searching_video`, `switching_language`) or access internal components like the TTS/STT engines.
    *   *Examples*: `YouTubeVideoPlayerTool` (updates state to "Playing Video"), `SwitchLanguageTool` (updates TTS/STT configurations).

*   **`toolbox.py`**: Contains **Simple Tools** that are standalone and stateless.
    *   Use this for functional tools that take an input and return an output without needing to know about Ruby's internal state.
    *   *Examples*: `calculator`, `arduino_serial_communication`, `query_document`.

### 2. Speech Services
*   **`stt.py` (Speech-to-Text)**:
    *   Implements the `RubySTT` class using **Google Cloud Speech-to-Text**.
    *   Handles real-time audio streaming from the microphone and returns transcribed text.
    *   Supports dynamic language switching.

*   **`tts.py` (Text-to-Speech)**:
    *   Implements the `RubyTTS` class using **Google Cloud Text-to-Speech**.
    *   Converts text responses into audio and plays them using `pygame`.
    *   Manages voice selection and caching of audio files.

### 3. RAG System
*   **`rag_utiles.py`**:
    *   Implements the `RubyRAG` class for **Retrieval Augmented Generation**.
    *   Uses **FAISS** for vector storage and **OpenAI Embeddings**.
    *   Allows Ruby to ingest PDF/Text documents and answer questions based on their content.

    #### How to Create and Update the RAG Dataset
    1.  **Prepare Documents**: Collect your knowledge base files (PDFs or `.txt` files).
    2.  **Initialize RAG**:
        ```python
        from utiles.rag_utiles import RubyRAG
        rag = RubyRAG()
        ```
    3.  **Ingest Data**:
        Pass the path of each file to the `add_documents` method. This will parse, chunk, embed, and store the data in the local vector database (`ruby_rag/db`).
        ```python
        # Add a single file
        rag.add_documents("path/to/your/document.pdf")
        ```
    4.  **Persistence**: The database is automatically saved to disk after adding documents. New documents are appended to the existing database.

### 4. Configuration
*   **`prompt.py`**:
    *   Stores the `system_prompt` string.
    *   Defines Ruby's persona, operational rules, and multilingual behavior instructions.
