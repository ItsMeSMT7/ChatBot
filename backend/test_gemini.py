import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def test_gemini():
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content("Say hello")
        print(f"✅ Gemini API working: {response.text}")
        return True
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return False

if __name__ == "__main__":
    test_gemini()