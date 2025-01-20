import openai
from typing import Dict, Any, List
from config import Config
from utils.logger import setup_logger

logger = setup_logger("AIDecisionMaker", "AIDecisionMaker.log")


class AIDecisionMaker:
    def __init__(self, api_key: str = Config.OPENAI_API_KEY):
        self.api_key = api_key

    def get_decision(self, user_preferences: List[str], market_data: Dict[str, Any], additional_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI 분석을 통해 트레이딩 결정을 내림
        """
        try:
            # OpenAI GPT 호출
            messages = [
                {
                    "role": "system",
                    "content": """You are a Bitcoin trading expert. You analyze the data provided to you and make decisions that will maximize your profitability.:
                                        - Recent price trends and volume
                                        - Technical indicators (RSI, MACD, BB)
                                        - Order book depth
                                        - Fear and Greed Index (not much important)
                                        - Use the provided chart image for reference
                                        - Past trade reflections
                                        - recent news headlines about btc
                                        
                                        Consider these important contextual factors:
                                        - Regular trading checks occur every 1 hours
                                        - Consider both the technical indicators and the timing of trades                                    
                        """
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                                    Market Data: {market_data}\n
                                    Technical Indicators: {additional_data.get('technical_indicators')}\n
                                    Trading Data (Daily): {additional_data.get('trading_data').get('daily')}\n
                                    Trading Data (Hourly): {additional_data.get('trading_data').get('hourly')}\n
                                    News: {additional_data.get('news')}\n
                                    Fear and Greed Index: {additional_data.get('fear_greed_index')}\n
                                    """
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{additional_data.chart_image}"
                            }
                        }
                    ]
                }
            ]

            response = openai.ChatCompletion.create(
                model="gpt-4o-2024-08-06",
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "trading_decision",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "decision": {"type": "string", "enum": ["buy", "sell", "hold"]},
                                "percentage": {"type": "number"},
                                "reason": {"type": "string"},
                                "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                                "confidence": {"type": "integer"}
                            },
                            "required": ["decision", "percentage", "reason", "risk_level", "confidence"],
                            "additionalProperties": False
                        }
                    }
                },
                max_tokens=500
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error in AI decision-making: {e}")
            return {"decision": "hold", "reason": "Error in decision-making process"}
