# -*- coding: utf-8 -*-
"""
ماژول جستجوی اینترنتی وینا
استفاده از DuckDuckGo بدون نیاز به API Key
"""

import re
import urllib.parse
import json


class VinaSearch:
    """کلاس جستجوی اینترنتی"""

    def __init__(self):
        self.search_url = "https://html.duckduckgo.com/html/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        }

    def search(self, query):
        """جستجو در اینترنت"""
        if not query:
            return "عبارت جستجو مشخص نیست."

        try:
            return self._search_ddg(query)
        except Exception as e:
            return f"خطا در جستجو: {str(e)[:100]}"

    def _search_ddg(self, query):
        """جستجو با DuckDuckGo"""
        try:
            import requests
            from bs4 import BeautifulSoup

            encoded_query = urllib.parse.quote(query)
            url = f"{self.search_url}?q={encoded_query}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            results = []
            result_divs = soup.find_all('div', class_='result')

            for div in result_divs[:5]:
                title_elem = div.find('a', class_='result__a')
                snippet_elem = div.find('a', class_='result__snippet')

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    link = title_elem.get('href', '')

                    if link.startswith('//duckduckgo.com/l/'):
                        link = urllib.parse.unquote(link.split('uddg=')[1].split('&')[0]) if 'uddg=' in link else link

                    results.append({
                        'title': title,
                        'snippet': snippet,
                        'link': link
                    })

            if not results:
                return self._search_fallback(query)

            response_text = f"نتایج جستجو برای «{query}»:\n\n"
            for i, r in enumerate(results, 1):
                response_text += f"{i}. {r['title']}\n"
                if r['snippet']:
                    response_text += f"   {r['snippet']}\n"
                response_text += "\n"

            return response_text.strip()

        except ImportError:
            return self._search_fallback(query)
        except requests.exceptions.Timeout:
            return "خطا: زمان جستجو تمام شد. اتصال اینترنت را بررسی کنید."
        except requests.exceptions.ConnectionError:
            return "خطا: اتصال اینترنت برقرار نیست."
        except Exception as e:
            return self._search_fallback(query)

    def _search_fallback(self, query):
        """روش جایگزین جستجو"""
        try:
            import requests

            encoded_query = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"

            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()

            results = []

            if data.get('Abstract'):
                results.append({
                    'title': data.get('Heading', query),
                    'snippet': data.get('Abstract', ''),
                    'link': data.get('AbstractURL', '')
                })

            for topic in data.get('RelatedTopics', [])[:5]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append({
                        'title': topic.get('Text', '')[:80],
                        'snippet': topic.get('Text', ''),
                        'link': topic.get('FirstURL', '')
                    })

            if results:
                response_text = f"نتایج جستجو برای «{query}»:\n\n"
                for i, r in enumerate(results, 1):
                    response_text += f"{i}. {r['title']}\n"
                    if r['snippet']:
                        response_text += f"   {r['snippet'][:200]}\n"
                    response_text += "\n"
                return response_text.strip()

            return (f"نتیجه‌ای برای «{query}» یافت نشد.\n\n"
                    "پیشنهادات:\n"
                    "- کلمات کلیدی را تغییر دهید\n"
                    "- اتصال اینترنت را بررسی کنید\n"
                    "- عبارت ساده‌تری استفاده کنید")

        except Exception:
            return (f"جستجو برای «{query}» امکان‌پذیر نیست.\n"
                    "لطفاً اتصال اینترنت خود را بررسی کنید.")

    def get_weather(self, city=""):
        """دریافت آب و هوا"""
        query = f"آب و هوا {city}" if city else "آب و هوا تهران"
        return self.search(query)

    def get_news(self, topic=""):
        """دریافت اخبار"""
        query = f"اخبار {topic} امروز" if topic else "اخبار امروز"
        return self.search(query)

    def get_price(self, item=""):
        """دریافت قیمت"""
        query = f"قیمت {item}" if item else "قیمت دلار"
        return self.search(query)

    def is_online(self):
        """بررسی اتصال اینترنت"""
        try:
            import requests
            response = requests.get("https://www.google.com", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
