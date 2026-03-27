import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()

class MistralInferenceBrain:
    """
    Brain using the Hugging Face InferenceClient for Mistral models.
    """
    def __init__(self, model_name="mistralai/Mistral-7B-Instruct-v0.2"):
        self.client = InferenceClient(
            model=model_name,
            token=os.getenv("HF_TOKEN")
        )
        self.model = model_name

    def generate_response(self, text_input):
        try:
            # Exact pattern requested by user
            response = self.client.text_generation(text_input)
            return response
        except Exception as e:
            return f"Mistral Inference Error: {e}"

if __name__ == "__main__":
    # Test snippet
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token or "ENTER_YOUR" in hf_token:
        print("Please set your HF_TOKEN in .env first.")
    else:
        brain = MistralInferenceBrain()
        print(f"Testing Mistral ({brain.model})...")
        print(f"Response: {brain.generate_response('Hello')}")
