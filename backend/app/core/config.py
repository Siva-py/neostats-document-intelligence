import os

from dotenv import load_dotenv


load_dotenv()


OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY")

GEMINI_API_KEYS = [
    key
    for key in [
        os.getenv("GEMINI_API_KEY_1"),
        os.getenv("GEMINI_API_KEY_2"),
        os.getenv("GEMINI_API_KEY_3"),
        os.getenv("GEMINI_API_KEY_4"),
        os.getenv("GEMINI_API_KEY_5"),
    ]
    if key
]