import json
import requests

with open("config.json", "r") as f:
    config = json.load(f)

API_KEY = config["api_key"]
BASE_URL = "https://api.ataix.kz"

def get_request(endpoint):
    """Функция для выполнения GET-запросов к API"""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return f"Ошибка: {response.status_code}, {response.text}"
    except requests.exceptions.Timeout:
        return "Ошибка: Превышено время ожидания ответа от сервера"
    except requests.exceptions.RequestException as e:
        return f"Ошибка запроса: {e}"

def get_currencies():
    """Список всех валют"""
    return get_request("/api/currencies")

def get_symbols():
    """Список всех торговых пар"""
    return get_request("/api/symbols")

def get_prices():
    """Цены всех монет и токенов"""
    return get_request("/api/prices")

# Запуск интерактивного режима
if __name__ == "__main__":
    while True:
        print("\nВыберите действие:")
        print("1 - Список всех валют")
        print("2 - Список всех торговых пар")
        print("3 - Цены всех монет и токенов")
        print("exit - Выход")
        
        command = input("Введите команду: ").strip().lower()
        
        if command == "1":
            print("\nСписок всех валют:")
            print(get_currencies())
        elif command == "2":
            print("\nСписок всех торговых пар:")
            print(get_symbols())
        elif command == "3":
            print("\nЦены всех монет и токенов:")
            print(get_prices())
        elif command == "exit":
            print("Выход из программы.")
            break
        else:
            print("Неизвестная команда. Попробуйте снова.")
