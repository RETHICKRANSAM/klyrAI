import threading

class RubyIntentClassifier:
    """
    Classifier for determining user intent using the qnlbnsl/ai_voice_assistant model.
    """
    def __init__(self, model_name="qnlbnsl/ai_voice_assistant"):
        self.pipe = None
        self.loading = True
        self.model_name = model_name
        # Start loading in a background thread
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self):
        try:
            from transformers import pipeline
            print(f"Loading Intent Classifier: {self.model_name}...")
            self.pipe = pipeline("text-classification", model=self.model_name)
            self.loading = False
            print("✅ Intent Classifier Loaded.")
        except Exception as e:
            print(f"❌ Failed to load Intent Classifier: {e}")
            self.loading = False

    def predict(self, text):
        if self.loading or not self.pipe:
            return "unknown"
        try:
            results = self.pipe(text)
            if results:
                return results[0]['label']
            return "unknown"
        except Exception:
            return "unknown"

# Singleton instance
_classifier = None

def get_intent(text):
    global _classifier
    if _classifier is None:
        _classifier = RubyIntentClassifier()
    return _classifier.predict(text)
