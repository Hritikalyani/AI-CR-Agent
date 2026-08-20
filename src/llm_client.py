"""
This MOdule  talks to the LLM. Swap providers here, nowhere else.
"""
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, GEMINI_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)

def ask_llm(system_prompt: str, user_content: str, max_tokens: int = 1500) -> str:
    """
    Sends code to gemini and returns the LLM's review text.
    """
    response = _client.models.generate_content(
        model = GEMINI_MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
        )
    )
    return response.text