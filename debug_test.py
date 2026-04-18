import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def test():
    print("Testing Gemini API directly...")
    print(f"Model: {os.getenv('LLM_MODEL')}")
    print(f"Key starts with: {os.getenv('GEMINI_API_KEY', '')[:8]}")
    print()

    try:
        response = client.models.generate_content(
            model=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
            contents="Write a 3-sentence cover letter for a Python developer applying to Google.",
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=500,
            ),
        )
        print("SUCCESS — Response received:")
        print(response.text)
        print()
        print(f"Length: {len(response.text)} characters")
    except Exception as e:
        print(f"FAILED — Error: {e}")
        print(f"Error type: {type(e).__name__}")

asyncio.run(test())