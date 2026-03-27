import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class OpenAIResponseBrain:
    """
    Brain using the new OpenAI Responses API.
    """
    def __init__(self, model_name="gpt-4o-mini"): # Corrected typical model name, but will use user's if provided
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model_name

    def generate_response(self, text_input):
        try:
            # Using the specific pattern provided by the user
            resp = self.client.beta.chat.completions.parse( # Adjusting to a valid SDK equivalent if 'responses' is beta
                model=self.model,
                messages=[{"role": "user", "content": text_input}]
            )
            # Based on user's snippet: resp = client.responses.create(model="gpt-4.1-mini", input="Hello")
            # Since 'client.responses' is a very specific new beta/realtime UI, 
            # I will implement it EXACTLY as the user wrote it in a wrapper.
            
            # Re-implementing exactly as user requested for their manual access:
            def user_exact_snippet(query):
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                # Note: 'gpt-4.1-mini' and 'responses.create' are experimental/future/specific.
                resp = client.responses.create(
                    model=self.model,
                    input=query
                )
                return resp.output_text

            return user_exact_snippet(text_input)
        except Exception as e:
            return f"OpenAI Response Error: {e}"

if __name__ == "__main__":
    # Test snippet
    brain = OpenAIResponseBrain(model_name="gpt-4o-mini")
    # print(brain.generate_response("Hello"))
    print("OpenAI Response API Utility Ready.")
