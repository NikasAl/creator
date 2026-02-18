import requests
import socket
import json
import urllib.request
from dotenv import load_dotenv
import os

def check_current_ip():
    print("=== Текущий IP из Python ===")
    try:
        # Проверка через requests
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        print(f"requests: {response.json()['ip']}")
        
        # Проверка через urllib (другой HTTP клиент)
        with urllib.request.urlopen('https://api.ipify.org?format=json', timeout=10) as f:
            data = json.loads(f.read().decode())
            print(f"urllib: {data['ip']}")
            
    except Exception as e:
        print(f"Ошибка при проверке IP: {e}")

def check_dns_resolution():
    print("\n=== Проверка DNS разрешения ===")
    domains = ['google.com', 'facebook.com', 'yandex.ru']
    
    for domain in domains:
        try:
            ip_addresses = socket.getaddrinfo(domain, None)
            ips = list(set([ip[4][0] for ip in ip_addresses]))
            print(f"{domain} -> {', '.join(ips)}")
        except Exception as e:
            print(f"Ошибка при разрешении {domain}: {e}")

def test_gemini_api():
    print("\n=== Тест Gemini API ===")
    try:
        # Загружаем переменные окружения
        load_dotenv("config.env")
        # Получаем API ключ из переменных окружения
        API_KEY_GEMINI = os.getenv('API_KEY_GEMINI')
        # url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent?key={API_KEY}"
        API_KEY=""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={API_KEY}"
        
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [{
                    "text": "say hello on hindi"
                }]
            }]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=15)
        print(f"Статус код: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            text = response_data['candidates'][0]['content']['parts'][0]['text']
            print(f"Ответ Gemini: {text[:100]}...")
        else:
            print(f"Тело ответа: {response.text}")
            
    except Exception as e:
        print(f"Ошибка при запросе к Gemini: {e}")

if __name__ == "__main__":
    # check_current_ip()
    # check_dns_resolution()
    
    # Раскомментируйте для теста Gemini API (когда будете готовы)
    test_gemini_api()