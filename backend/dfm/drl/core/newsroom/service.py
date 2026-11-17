import os
import json
from google import genai
from google.genai import types

class NewsroomAIService:
    @staticmethod
    async def generate_h2h_matchup_article(
        home_franchise: str, 
        away_franchise: str, 
        home_projected_score: float, 
        away_projected_score: float,
        round_number: int
    ) -> dict:
        """
        Uses Gemini to generate broadcast-quality sports journalism for an H2H match preview.
        """
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
        prompt = (
            f"Write an energetic, high-stakes broadcast-style sports journalism preview article for Digital Franchise Manager (DFM). "
            f"Round {round_number} Head-to-Head clash: '{home_franchise}' vs '{away_franchise}'. "
            f"Projected scores: {home_franchise} ({home_projected_score}) vs {away_franchise} ({away_projected_score}). "
            f"Include tactical expectations, finals race implications, and potential trade talk or squad pressure. "
            f"Return a strict JSON object with keys: 'title', 'summary', and 'content'."
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        
        return json.loads(response.text)
