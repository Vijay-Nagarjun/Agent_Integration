import google.generativeai as genai
import os
from dotenv import load_dotenv

def list_available_models():
    load_dotenv()
    
    # Configure the Gemini API
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    # List available models
    print("Available Models:")
    for m in genai.list_models():
        print(f"Name: {m.name}")
        print(f"Display Name: {m.display_name}")
        print(f"Description: {m.description}")
        print(f"Version: {m.version}")
        print("-" * 50)

if __name__ == "__main__":
    list_available_models()
