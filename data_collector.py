from email import feedparser
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import base64
import os
import pandas as pd
import time
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice
from typing import Optional
import pyupbit
import requests
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("DataCollector")

class DataCollector:
    def collect_fear_greed_index(self) -> str:
        try:
            response = requests.get("https://api.alternative.me/fng/")  # 공포와 탐욕 지수 API
            if response.status_code == 200:
                data = response.json()
                return data["data"][0]["value_classification"]
            return "Unknown"
        except Exception as e:
            print(f"Error fetching fear and greed index: {e}")
            return "Error"

    def fetch_google_news(self) -> List[Dict[str, str]]:
        """
        Fetch the latest BTC news headlines from Google News RSS
        """
        rss_url = "https://news.google.com/rss/search?q=btc+when:1d&hl=en-US&gl=US&ceid=US:en"

        try:
            # RSS 피드 파싱
            feed = feedparser.parse(rss_url)

            # 최신 뉴스 5개만 추출
            news_results = []
            for entry in feed.entries[:5]:
                news_results.append({
                    "title": entry.title,
                    "date": entry.published
                })

            return news_results
        except Exception as e:
            logger.error(f"Error fetching Google News: {e}")
            return []

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators (RSI, MACD, Bollinger Bands, Stochastic) to the DataFrame.
        """
        # 기본 지표들
        bb = BollingerBands(close=df['close'])
        macd = MACD(close=df['close'])
        rsi = RSIIndicator(close=df['close'])
        stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'])
        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'])
        obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume'])
        vwap = VolumeWeightedAveragePrice(high=df['high'], low=df['low'], close=df['close'],
                                          volume=df['volume'])

        # 이동평균선
        df['ma5'] = SMAIndicator(close=df['close'], window=5).sma_indicator()
        df['ma20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
        df['ma60'] = SMAIndicator(close=df['close'], window=60).sma_indicator()
        df['ma120'] = SMAIndicator(close=df['close'], window=120).sma_indicator()

        # 볼린저 밴드
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_width'] = bb.bollinger_wband()

        # MACD
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()

        # RSI
        df['rsi'] = rsi.rsi()

        # Stochastic
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()

        # ATR
        df['atr'] = atr.average_true_range()

        # OBV
        df['obv'] = obv.on_balance_volume()

        # VWAP
        df['vwap'] = vwap.volume_weighted_average_price()

        return df

    def get_trading_data(self) -> Dict[str, Any]:
        """
        Collect all trading-related data including OHLCV and technical indicators.
        """
        try:
            # 현재 상태 조회
            krw_balance = self.upbit.get_balance("KRW")
            btc_balance = self.upbit.get_balance("KRW-BTC")
            avg_buy_price = self.upbit.get_avg_buy_price("KRW-BTC")
            current_price = pyupbit.get_current_price("KRW-BTC")
            orderbook = pyupbit.get_orderbook("KRW-BTC")["orderbook_units"]

            # 총 자산 계산
            total_assets = krw_balance + (btc_balance * current_price)
            btc_ratio = (btc_balance * current_price) / total_assets if total_assets > 0 else 0
            profit_loss = ((current_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0

            # 기본 투자 상태
            investment_status = {
                "krw_balance": krw_balance,
                "btc_balance": btc_balance,
                "avg_buy_price": avg_buy_price,
                "current_price": current_price,
                "total_assets": total_assets,
                "btc_ratio": btc_ratio,
                "profit_loss": profit_loss
            }

            # OHLCV 데이터 가져오기
            daily_data = pyupbit.get_ohlcv("KRW-BTC", count=200, interval="day")
            hourly_data = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=200)

            if daily_data is not None and hourly_data is not None:
                # 컬럼 이름을 소문자로 변환
                daily_data.columns = [col.lower() for col in daily_data.columns]
                hourly_data.columns = [col.lower() for col in hourly_data.columns]

                # 기술적 지표 추가
                daily_data = self.add_technical_indicators(daily_data)
                hourly_data = self.add_technical_indicators(hourly_data)

                return {
                    "investment_status": investment_status,
                    "orderbook": orderbook,
                    "daily_data": daily_data.tail(30).to_dict('records'),
                    "hourly_data": hourly_data.tail(24).to_dict('records'),
                    "technical_summary": {
                        "daily": {
                            "rsi": daily_data['rsi'].iloc[-1],
                            "macd": daily_data['macd'].iloc[-1],
                            "macd_signal": daily_data['macd_signal'].iloc[-1],
                            "bb_width": daily_data['bb_width'].iloc[-1],
                            "stoch_k": daily_data['stoch_k'].iloc[-1],
                            "stoch_d": daily_data['stoch_d'].iloc[-1],
                        },
                        "hourly": {
                            "rsi": hourly_data['rsi'].iloc[-1],
                            "macd": hourly_data['macd'].iloc[-1],
                            "macd_signal": hourly_data['macd_signal'].iloc[-1],
                            "bb_width": hourly_data['bb_width'].iloc[-1],
                            "stoch_k": hourly_data['stoch_k'].iloc[-1],
                            "stoch_d": hourly_data['stoch_d'].iloc[-1],
                        }
                    }
                }
            else:
                logger.error("Failed to fetch OHLCV data.")
                return {"investment_status": investment_status, "orderbook": orderbook}
        except Exception as e:
            logger.error(f"Error fetching trading data: {e}")
            return {}

    def capture_chart(self) -> Optional[str]:
        """
        Capture and encode chart image based on environment
        """
        # Chrome WebDriver 설정
        if self.config.ENVIRONMENT == 'EC2':
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--remote-debugging-port=9222')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument(f"--window-size={self.config.CHART_WIDTH},{self.config.CHART_HEIGHT}")

            chromedriver_path = "/home/ubuntu/.wdm/drivers/chromedriver/linux64/128.0.6613.137/chromedriver-linux64/chromedriver"
            service = Service(executable_path=chromedriver_path)
        else:
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument(f"--window-size={self.config.CHART_WIDTH},{self.config.CHART_HEIGHT}")
            service = Service(ChromeDriverManager().install())

        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(10)
            driver.get("https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC")

            # 명시적 대기
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(self.config.CHART_LOAD_WAIT)

            # 3분 간격 설정
            if not self.select_3min_interval(driver):
                logger.error("Failed to select 3-minute interval.")

            # 볼린저 밴드 설정
            if not self.select_bollinger_band(driver):
                logger.error("Failed to select Bollinger Band.")

            # 디버깅 디렉토리 설정
            if self.config.ENVIRONMENT == 'EC2':
                debug_dir = "/home/ubuntu/bitcoin_chart_debug"
            else:
                debug_dir = os.path.join(os.path.expanduser("~"), "bitcoin_chart_debug")

            os.makedirs(debug_dir, exist_ok=True)

            # 타임스탬프 기반 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(debug_dir, f"chart_screenshot_{timestamp}.png")

            # 스크린샷 저장
            driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")

            # Base64로 인코딩
            encoded_image = self.encode_image(screenshot_path)

            return encoded_image
        except Exception as e:
            logger.error(f"Error capturing chart: {e}")
            return None
        finally:
            driver.quit()

    def encode_image(self, file_path: str) -> str:
        """
        Encode the image file to Base64
        """
        try:
            with open(file_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image to Base64: {e}")
            return ""

    def select_bollinger_band(self, driver):
        """
        볼린저 밴드 설정을 위한 함수.
        """
        menu_xpath = "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[3]"
        option_xpath = '//*[@id="fullChartiq"]/div/div/div[1]/div/div/cq-menu[3]/cq-menu-dropdown/cq-scroll/cq-studies/cq-studies-content/cq-item[15]'
        return self.click_option_with_scroll(driver, menu_xpath, option_xpath)

    def select_3min_interval(self, driver):
        """
        3분 간격 설정을 위한 함수.
        """
        menu_xpath = "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[1]/span/cq-clickable"
        option_xpath = "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[1]/cq-menu-dropdown/cq-item[3]"
        return self.click_option_with_scroll(driver, menu_xpath, option_xpath)

    def click_option_with_scroll(self, driver, menu_xpath: str, option_xpath: str, wait_time: int = 10):
        """
        Selenium WebDriver를 사용하여 특정 옵션을 클릭하며, 화면에 표시되지 않은 경우 스크롤로 접근.

        Args:
            driver: Selenium WebDriver 객체.
            menu_xpath: 메뉴 버튼의 XPath.
            option_xpath: 선택할 옵션의 XPath.
            wait_time: 대기 시간 (초 단위, 기본값: 10).

        Returns:
            성공 여부 (True/False).
        """
        try:
            # 메뉴 버튼 클릭
            menu_button = WebDriverWait(driver, wait_time).until(
                EC.element_to_be_clickable((By.XPATH, menu_xpath))
            )
            menu_button.click()
            time.sleep(0.5)  # 메뉴 로딩 대기

            # 옵션 버튼 찾기
            option_button = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, option_xpath))
            )

            # 강제 스크롤로 옵션 버튼 노출
            driver.execute_script("arguments[0].scrollIntoView(true);", option_button)
            time.sleep(0.5)  # 스크롤 후 대기

            # 옵션 버튼 클릭
            WebDriverWait(driver, wait_time).until(
                EC.element_to_be_clickable((By.XPATH, option_xpath))
            ).click()
            logger.info(f"Successfully clicked option: {option_xpath}")
            return True

        except Exception as e:
            logger.error(f"Error in click_option_with_scroll: {e}")
            return False
