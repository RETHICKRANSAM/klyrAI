import os
from dotenv import load_dotenv

load_dotenv()


class GeminiBrain:
    """
    Hugging Face Llama-3.1 Brain (Replaced Gemini).
    Uses Llama-3.1-8B-Instruct:novita via Hugging Face Router.
    """
    def __init__(self, model_name="meta-llama/Llama-3.1-8B-Instruct:novita", thinking=False):
        from openai import OpenAI
        hf_token = os.environ.get("HF_TOKEN")
        self.client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=hf_token,
        )
        self.model = model_name
        self.thinking = thinking

    def invoke(self, messages):
        # Build full conversation context
        history = messages.get("messages", [])
        
        # Build messages for the router
        formatted_messages = []
        for msg in history:
            role = "user"
            cls_name = msg.__class__.__name__
            if "System" in cls_name:
                role = "system"
            elif "AI" in cls_name:
                role = "assistant"
            formatted_messages.append({"role": role, "content": msg.content})

        try:
            # Using streaming as per user snippet for performance logic
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                stream=True,
                temperature=0.7,
                max_tokens=1024,
            )
            
            response_text = ""
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content
                    if content:
                        response_text += content
            
            if not response_text:
                return self._wrap_response("I received an empty response from the Hugging Face router. Please try again.")

            return self._wrap_response(response_text)

        except Exception as e:
            error_str = str(e)
            print(f"HF Llama Error: {error_str}")
            return self._wrap_response(f"Hugging Face Router error: {error_str}. Ensure HF_TOKEN is valid in .env")

    def _wrap_response(self, content):
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content=content)]}


class OpenAIResponseBrain:
    """
    Experimental brain using the OpenAI 'Responses' API pattern.
    """
    def __init__(self, model_name="gpt-4.1-mini"):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model_name

    def invoke(self, messages):
        history = messages.get("messages", [])
        user_text = history[-1].content if history else ""
        
        try:
            # Exact pattern requested by user
            resp = self.client.responses.create(
                model=self.model,
                input=user_text
            )
            return self._wrap_response(resp.output_text)
        except Exception as e:
            print(f"OpenAI Responses Error: {e}")
            return self._wrap_response(f"OpenAI Responses API error: {e}. Check your model name and API key.")

    def _wrap_response(self, content):
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content=content)]}


class MistralInferenceBrain:
    """
    Brain using the Hugging Face InferenceClient (Mistral).
    """
    def __init__(self, model_name="mistralai/Mistral-7B-Instruct-v0.2"):
        from huggingface_hub import InferenceClient
        self.client = InferenceClient(
            model=model_name,
            token=os.getenv("HF_TOKEN")
        )
        self.model = model_name

    def invoke(self, messages):
        history = messages.get("messages", [])
        user_text = history[-1].content if history else ""
        
        try:
            # Simple text generation as per user snippet
            response = self.client.text_generation(user_text, max_new_tokens=512)
            return self._wrap_response(response)
        except Exception as e:
            print(f"Mistral Inference Error: {e}")
            return self._wrap_response(f"Mistral Inference API error: {e}. Check your HF_TOKEN.")

    def _wrap_response(self, content):
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content=content)]}


class GroqBrain:
    """
    Groq Brain — 100% FREE. Sign up at console.groq.com
    Provides ultra-fast LLM inference with llama-3.3-70b.
    No credit card needed.
    """
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        self.model_name = model_name
        self.groq_key = os.getenv("GROQ_API_KEY", "")

    def invoke(self, data):
        from langchain_core.messages import AIMessage
        import json
        
        history = data.get("messages", [])
        tools = data.get("tools", [])
        user_text = history[-1].content if history else ""

        # Check if Groq key is available
        if not self.groq_key or "your_" in self.groq_key:
            return self._g4f_chat_response(user_text)

        try:
            from groq import Groq
            client = Groq(api_key=self.groq_key)

            # Convert tools to Groq format
            groq_tools = []
            for t in tools:
                # Handle both langchain Tools and BaseTools
                try:
                    name = t.name
                    description = t.description
                    properties = {}
                    required = []
                    
                    if hasattr(t, "args_schema") and t.args_schema:
                        schema = t.args_schema.schema()
                        properties = schema.get("properties", {})
                        required = schema.get("required", [])
                    elif hasattr(t, "args") and t.args:
                        # Fallback for simpler tools
                        properties = {k: {"type": "string"} for k in t.args}
                    
                    groq_tools.append({
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": description,
                            "parameters": {
                                "type": "object",
                                "properties": properties,
                                "required": required
                            }
                        }
                    })
                except Exception as te:
                    print(f"Tool Schema Error ({t.name}): {te}")

            # Build messages
            groq_messages = []
            for msg in history:
                role = "user"
                if hasattr(msg, '__class__'):
                    cls_name = msg.__class__.__name__
                    if "System" in cls_name: role = "system"
                    elif "AI" in cls_name: role = "assistant"
                groq_messages.append({"role": role, "content": msg.content})

            # 1. Initial Call
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=groq_messages,
                tools=groq_tools,
                tool_choice="auto"
            )

            response_message = completion.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                groq_messages.append(response_message)
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute tool
                    tool_to_use = next((t for t in tools if t.name == function_name), None)
                    if tool_to_use:
                        print(f"DEBUG BRAIN: Executing Tool -> {function_name}({function_args})")
                        observation = tool_to_use.invoke(function_args)
                        groq_messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(observation),
                        })

                # 2. Final Response
                final_completion = client.chat.completions.create(
                    model=self.model_name,
                    messages=groq_messages
                )
                return self._wrap_response(final_completion.choices[0].message.content)
            
            return self._wrap_response(response_message.content)

        except Exception as e:
            error_str = str(e)
            print(f"Groq Error: {error_str}")
            # Try g4f as fallback
            try:
                return self._g4f_chat_response(user_text)
            except Exception as g4f_e:
                print(f"g4f fallback also failed: {g4f_e}")
                # Try DuckDuckGo as last resort
                try:
                    return self._ddg_chat_response(user_text)
                except Exception:
                    pass
            return self._wrap_response(f"Groq error: {error_str}")

    def _g4f_chat_response(self, query):
        """Use g4f (GPT4Free) as a high-quality FREE fallback."""
        try:
            import g4f
            import nest_asyncio
            nest_asyncio.apply() # Required for some environments

            response = g4f.ChatCompletion.create(
                model=g4f.models.gpt_4o_mini,
                messages=[{"role": "user", "content": query}],
            )
            if response:
                # Clean up response if it's very long or contains markdown code blocks
                return self._wrap_response(response)
        except Exception as e:
            print(f"g4f Chat Error: {e}")
            raise e

    def _ddg_chat_response(self, query):
        """Use DuckDuckGo AI Chat as a completely FREE LLM fallback (No API key needed)."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                # model: 'gpt-4o-mini', 'claude-3-haiku', 'llama-3.1-70b', 'mixtral-8x7b'
                # gpt-4o-mini is standard and fast
                response = ddgs.chat(query, model='gpt-4o-mini')
            if response:
                return self._wrap_response(response)
            
            # If chat fails, fall back to raw search
            return self._ddg_search_response(query)
        except Exception as e:
            print(f"DDG Chat Error: {e}")
            return self._ddg_search_response(query)

    def _ddg_search_response(self, query):
        """Use DuckDuckGo search as a secondary fallback."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
            if results:
                snippets = []
                for r in results:
                    snippets.append(f"• {r.get('title', '')}: {r.get('body', '')[:200]}")
                answer = "Here is what I found on the web:\n" + "\n".join(snippets)
            else:
                answer = "I'm sorry, I couldn't find an answer to that even with a web search. Please check your internet connection or try again."
            return self._wrap_response(answer)
        except Exception as e:
            print(f"DDG Search Internal Error: {e}")
            return self._wrap_response(f"I'm sorry, I'm having trouble connecting to my brain systems. Error: {str(e)}")

    def _wrap_response(self, content):
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content=content)]}


class OpenRouterBrain:
    """
    Brain using OpenRouter API. Supports tool calling.
    """
    def __init__(self, model_name="google/gemini-2.0-flash-001"): # Fast and supports tools
        from openai import OpenAI
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = model_name

    def invoke(self, data):
        from langchain_core.messages import AIMessage
        import json
        
        history = data.get("messages", [])
        tools = data.get("tools", [])
        
        # Convert tools to OpenAI format
        openai_tools = []
        for t in tools:
            try:
                name = t.name
                description = t.description
                properties = {}
                required = []
                
                if hasattr(t, "args_schema") and t.args_schema:
                    schema = t.args_schema.schema()
                    properties = schema.get("properties", {})
                    required = schema.get("required", [])
                elif hasattr(t, "args") and t.args:
                    properties = {k: {"type": "string"} for k in t.args}
                
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required
                        }
                    }
                })
            except Exception as te:
                print(f"Tool Schema Error ({t.name}): {te}")

        # Build messages
        formatted_messages = []
        for msg in history:
            role = "user"
            cls_name = msg.__class__.__name__
            if "System" in cls_name: role = "system"
            elif "AI" in cls_name: role = "assistant"
            formatted_messages.append({"role": role, "content": msg.content})

        try:
            # 1. Initial Call
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                tools=openai_tools if openai_tools else None,
                tool_choice="auto" if openai_tools else None
            )

            response_message = completion.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                formatted_messages.append(response_message)
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute tool
                    tool_to_use = next((t for t in tools if t.name == function_name), None)
                    if tool_to_use:
                        print(f"DEBUG OPENROUTER: Executing Tool -> {function_name}({function_args})")
                        observation = tool_to_use.invoke(function_args)
                        formatted_messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(observation),
                        })

                # 2. Final Response
                final_completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=formatted_messages
                )
                return self._wrap_response(final_completion.choices[0].message.content)
            
            return self._wrap_response(response_message.content)

        except Exception as e:
            print(f"OpenRouter Error: {e}")
            return self._wrap_response(f"OpenRouter error: {e}")

    def _wrap_response(self, content):
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content=content)]}


def get_brain():
    """
    Returns the LLM brain based on .env configuration.
    """
    provider = os.getenv("AI_PROVIDER", "groq").lower()
    model_name = os.getenv("AI_MODEL", "")

    if "openrouter" in provider:
        return OpenRouterBrain(model_name=model_name or "google/gemini-2.0-flash-001")

    if "groq" in provider:
        return GroqBrain(model_name=model_name or "llama-3.3-70b-versatile")

    if "gemini" in provider or "thinking" in provider:
        return GeminiBrain(
            model_name=model_name or "gemini-2.0-flash",
            thinking="thinking" in provider
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name or "gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

    if provider == "openai_responses":
        return OpenAIResponseBrain(model_name=model_name or "gpt-4.1-mini")

    if provider == "mistral_inference":
        return MistralInferenceBrain(model_name=model_name or "mistralai/Mistral-7B-Instruct-v0.2")

    return GroqBrain(model_name="llama-3.3-70b-versatile")
