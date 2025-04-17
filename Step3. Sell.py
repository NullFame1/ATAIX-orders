import json
import requests
import sys

# Константы
CONFIG_FILE = "config.json"
ORDERS_FILE = "orders_data.json"
BASE_URL = "https://api.ataix.kz"

# Загрузка API-ключа
def load_config():
    """Загружает API-ключ из config.json и выводит отладочную информацию."""
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            api_key = config.get("api_key")
            if not api_key:
                print("Ошибка: API-ключ не найден в config.json")
                sys.exit(1)
            print("[DEBUG] API-ключ успешно загружен")
            return api_key
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        sys.exit(1)

API_KEY = load_config()

# Класс для работы с API
class AtaixAPI:
    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY
    }

    @staticmethod
    def get(endpoint):
        """Выполняет GET-запрос к API и выводит отладочную информацию."""
        try:
            print(f"[DEBUG] GET-запрос к {BASE_URL}{endpoint}")
            response = requests.get(f"{BASE_URL}{endpoint}", headers=AtaixAPI.headers, timeout=20)
            if response.status_code == 200:
                print(f"[DEBUG] Успешный ответ от API: {response.json()}")
                return response.json()
            else:
                print(f"[ERROR] Ошибка API: {response.status_code}, {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ошибка запроса: {e}")
            return None

    @staticmethod
    def post(endpoint, data):
        """Выполняет POST-запрос для создания нового ордера."""
        try:
            print(f"[DEBUG] POST-запрос к {BASE_URL}{endpoint} с данными: {data}")
            response = requests.post(f"{BASE_URL}{endpoint}", headers=AtaixAPI.headers, json=data, timeout=20)
            if response.status_code == 200:
                print(f"[DEBUG] Успешный ответ от API: {response.json()}")
                return response.json()
            else:
                print(f"[ERROR] Ошибка API: {response.status_code}, {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ошибка запроса на создание ордера: {e}")
            return None

# Функция для удаления ордера и записи в history.txt
def delete_purchase_order_and_log(order_id, related_sell_order=None):
    """Удаляет ордер на покупку и записывает его вместе с ордером продажи в history.txt."""
    try:
        # Чтение данных из order_data.json
        with open(ORDERS_FILE, "r") as file:
            orders = json.load(file)

        # Находим ордер на покупку
        order_to_delete = None
        for order in orders:
            if order["orderID"] == order_id:
                order_to_delete = order
                break

        if order_to_delete:
            # Удаляем ордер из списка
            orders = [order for order in orders if order["orderID"] != order_id]

            # Записываем измененные данные обратно
            with open(ORDERS_FILE, "w") as file:
                json.dump(orders, file, indent=4)

            # Подготовка записи в историю
            buy_order_info = f"OrderID {order_to_delete['orderID']}, цена {order_to_delete['price']}, кол-во {order_to_delete['quantity']}, символ {order_to_delete['symbol']}, время {order_to_delete['created']}"

            if related_sell_order:
                sell_order_info = f"OrderID {related_sell_order['orderID']}, цена {related_sell_order['price']}, кол-во {related_sell_order['quantity']}, символ {related_sell_order['symbol']}, время {related_sell_order['created']}"
                history_entry = f"ПОКУПКА: {buy_order_info}, Продажа: {sell_order_info}"
            else:
                history_entry = f"ПОКУПКА: {buy_order_info}"

            # Открытие файла с явным указанием кодировки
            with open("history.txt", "a", encoding="utf-8") as history_file:
                history_file.write(history_entry + "\n")

            print(f"[DEBUG] Ордер {order_id} удален и записан в history.txt.")
        else:
            print(f"[INFO] Ордер с ID {order_id} не найден.")

    except Exception as e:
        print(f"[ERROR] Ошибка при удалении ордера и записи в history.txt: {e}")



# Функция для обновления статуса ордера
def update_order_status(order_id, status, file_path=ORDERS_FILE):
    """Обновляет статус ордера."""
    try:
        with open(file_path, "r") as file:
            orders = json.load(file)

        for order in orders:
            if order["orderID"] == order_id:
                order["status"] = status
                print(f"[DEBUG] Обновлен статус ордера {order_id} на {status}")
                break

        with open(file_path, "w") as file:
            json.dump(orders, file, indent=4)
        print(f"[DEBUG] Статус ордера {order_id} успешно обновлен в файле.")
    except Exception as e:
        print(f"[ERROR] Ошибка при обновлении статуса ордера: {e}")

# Функция для создания ордера на продажу
def create_sell_order(pair, price):
    """Создает ордер на продажу"""
    print(f"[DEBUG] Создание ордера на продажу -> пара: {pair}, цена: {price}")

    order_data = {
        "symbol": pair,
        "side": "sell",
        "type": "limit",
        "quantity": 1,
        "price": price
    }

    response = AtaixAPI.post("/api/orders", order_data)

    if isinstance(response, dict) and "result" in response:
        return {
            "orderID": response["result"]["orderID"],
            "price": response["result"]["price"],
            "quantity": response["result"]["quantity"],
            "symbol": response["result"]["symbol"],
            "created": response["result"]["created"],
            "status": response["result"].get("status", "NEW"),
            "side": "sell"
        }

    else:
        print("[ERROR] Ошибка при создании ордера на продажу.")
        return None

# Функция для сканирования ордеров
def scan_orders():
    """Сканирует ордера, проверяет их статус и создает ордер на продажу при выполнении, удаляя обработанные покупки."""
    try:
        with open(ORDERS_FILE, "r") as file:
            orders = json.load(file)

        remaining_orders = []

        for order in orders:
            order_id = order["orderID"]
            print(f"[INFO] Проверяем ордер с ID: {order_id}")

            if order["status"] == "filled":
                print(f"[INFO] Ордер {order_id} выполнен, создаем ордер на продажу.")

                # Создаем ордер на продажу +2%
                price = float(order["price"])
                # Запрашиваем процент увеличения у пользователя
                try:
                    percent_increase = float(input(f"Введите на сколько процентов увеличить цену покупки {price} для ордера {order_id}: "))
                except ValueError:
                    print("[ERROR] Некорректный ввод, устанавливаю 2% по умолчанию.")
                    percent_increase = 2.0

                sell_price = round(price * (1 + percent_increase / 100), 4)


                sell_order = create_sell_order(order["symbol"], sell_price)

                if sell_order:
                    # Сохраняем ордер на продажу
                    remaining_orders.append(sell_order)

                    # Удаляем ордер покупки и записываем его в history.txt вместе с продажей
                    delete_purchase_order_and_log(order["orderID"], related_sell_order=sell_order)

                    print(f"[INFO] Ордер на продажу {sell_order['orderID']} создан.")
                else:
                    print(f"[ERROR] Ошибка при создании ордера на продажу для ордера {order_id}")
                    remaining_orders.append(order)  # Если ошибка — оставляем покупку в списке
            else:
                # Ордер не выполнен — оставляем в списке
                remaining_orders.append(order)

        # Сохраняем только актуальные ордера
        with open(ORDERS_FILE, "w") as file:
            json.dump(remaining_orders, file, indent=4)

    except Exception as e:
        print(f"[ERROR] Ошибка при сканировании ордеров: {e}")


# Точка входа
if __name__ == "__main__":
    while True:
        scan_orders()
        user_input = input('Введите "start" чтобы запустить снова или "exit" чтобы выйти: ').strip().lower()
        if user_input == "exit":
            print("Выход из программы.")
            break
        elif user_input == "start":
            print("Перезапуск сканирования...")
        else:
            print('Неверный ввод. Ожидалось "start" или "exit". Выход из программы.')
            break

