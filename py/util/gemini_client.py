# gemini_client.py
import google.generativeai as genai
import const

class GeminiClient():
    def __init__(self, apikey=1, model_name=None):
        if(apikey==0):
            self.api_key = const.apikey1
        elif(apikey==1):
            self.api_key = const.apikey2
        elif(apikey==2):
            self.api_key = const.apikey3
        elif(apikey==3):
            self.api_key = const.apikey4

        self.model_name = model_name or const.gemini_model
        self.configure_client()

    def configure_client(self):
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def generate_content(self, prompt):
        response = self.model.generate_content(prompt)
        return response.text.strip()
