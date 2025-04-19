# gemini_client.py
import google.generativeai as genai
import const

class GeminiClient:
    def __init__(self, api_key=None, model_name=None):
        self.api_key = api_key or const.apikey
        self.model_name = model_name or const.gemini_model
        self.configure_client()

    def configure_client(self):
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def generate_content(self, prompt):
        response = self.model.generate_content(prompt)
        return response.text.strip()
