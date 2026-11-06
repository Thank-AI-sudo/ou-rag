
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("Khong tim thay GEMINI_API_KEY trong file .env")

client = genai.Client(api_key=API_KEY)

print("Cac model co kha nang ho tro generateContent:\n")

for model in client.models.list():
    supported_methods = getattr(model, "supported_actions", []) or []

    if "generateContent" in supported_methods:
        print(model.name)
