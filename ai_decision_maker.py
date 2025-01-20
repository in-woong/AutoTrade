import openai
from typing import Dict, Any, List
from config import Config


class AIDecisionMaker:
    def __init__(self, api_key: str = Config.OPENAI_API_KEY):
        self.api_key = api_key

    def get_decision(self, user_preferences: List[str], market_data: Dict[str, Any], reflection: Dict[str, Any]) -> Dict[str, Any]:
        # OpenAI GPT를 활용한 결정 로직
        try:
            messages = [
                {"role": "system", "content": "You are a Bitcoin trading expert. Analyze the provided data."},
                {"role": "user", "content": f"Market Data: {market_data}\nReflection: {reflection}"}
            ]
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=500
            )
            return response.choices[0].message["content"]
        except Exception as e:
            print(f"Error in AI decision: {e}")
            return {"decision": "hold", "reason": "Error during decision process"}
