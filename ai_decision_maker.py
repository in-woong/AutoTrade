import openai
from typing import Dict, Any
from config import Config

class AIDecisionMaker:
    def __init__(self, api_key: str = Config.OPENAI_API_KEY):
        self.api_key = api_key

    def get_decision(self, user_preferences: List[str], market_data: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder for GPT decision-making
        return {
            "decision": "hold",
            "percentage": 0,
            "reason": "Sample reason"
        }
