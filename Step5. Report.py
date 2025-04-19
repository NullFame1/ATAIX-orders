import re
from datetime import datetime

# Функция для парсинга строки с данными
def parse_order_line(line):
    """Парсим строку из history.txt для извлечения данных."""
    # Обновленное регулярное выражение для извлечения данных из строки
    pattern = r"([А-ЯЁа-яёA-Za-z\s\-]+):\s*OrderID\s+(\S+),\s*цена\s+([\d\.,]+),\s*кол-во\s+([\d\.,]+),\s*символ\s+(\S+),\s*время\s+([0-9T\-\:\.Z]+),\s*originalID\s+(\S+),\s*комиссия\s+([\d\.,]+)"


    match = re.search(pattern, line)
    
    if match:
        commission_str = match.group(8).replace(',', '.')  # Заменяем запятую на точку
        order_data = {
            "событие": match.group(1),  # Тип события
            "OrderID": match.group(2),
            "цена": float(match.group(3)),
            "кол-во": float(match.group(4)),
            "символ": match.group(5),
            "время": datetime.strptime(match.group(6), "%Y-%m-%dT%H:%M:%S.%fZ"),
            "originalID": match.group(7),
            "комиссия": float(commission_str)  # Теперь можно безопасно конвертировать
        }
        return order_data
    return None

# Обработка данных из файла
def process_history_file(file_path):
    """Обрабатываем файл history.txt и генерируем отчет в HTML формате."""
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # Парсим данные из строк
    orders = []
    for line in lines:
        order_data = parse_order_line(line.strip())
        if order_data:
            orders.append(order_data)
    
    # Группируем данные по originalID
    grouped_data = {}
    for order in orders:
        originalID = order["originalID"]
        if originalID not in grouped_data:
            grouped_data[originalID] = []
        grouped_data[originalID].append(order)

    # Генерируем HTML отчет
    generate_html_report(grouped_data)

# Генерация HTML отчета
def generate_html_report(grouped_data):
    """Генерирует HTML отчет для каждого блока данных по originalID."""
    html_content = """
    <html>
    <head>
        <title>Отчет по Ордерам</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
            }
            .report-section {
                margin-bottom: 40px;
            }
            .report-section h2 {
                color: #4CAF50;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }
            table, th, td {
                border: 1px solid #ddd;
            }
            th, td {
                padding: 10px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
            .profit-loss {
                font-weight: bold;
            }
            .event-type {
                font-weight: bold;
                color: #FF5733;
            }
        </style>
    </head>
    <body>
    <h1>Отчет по Ордеру</h1>
    """

    # Обрабатываем каждый блок с одинаковым originalID
    for originalID, orders in grouped_data.items():
        html_content += f'<div class="report-section"><h2>OriginalID: {originalID}</h2>'
        
        # Сортируем заказы по времени
        orders_sorted = sorted(orders, key=lambda x: x['время'])
        
        # Генерируем таблицу для каждого блока
        html_content += '<table><thead><tr><th>Тип события</th><th>OrderID</th><th>Цена</th><th>Кол-во</th><th>Символ</th><th>Время</th><th>Комиссия</th></tr></thead><tbody>'
        
        for order in orders_sorted:
            html_content += f"""
                <tr>
                    <td class="event-type">{order['событие']}</td>
                    <td>{order['OrderID']}</td>
                    <td>{order['цена']}</td>
                    <td>{order['кол-во']}</td>
                    <td>{order['символ']}</td>
                    <td>{order['время']}</td>
                    <td>{order['комиссия']}</td>
                </tr>
            """
        
        html_content += '</tbody></table>'

        # Вычисляем доход/расход для каждой группы
        buy_orders = [o for o in orders if 'покупка' in o["событие"].lower()]
        sell_orders = [o for o in orders if 'продажа' in o["событие"].lower()]

        # Проверяем, что количество покупок и продаж совпадает
        if len(buy_orders) != len(sell_orders):
            html_content += '<p class="profit-loss">Ошибка: количество покупок и продаж не совпадает.</p>'
        else:
            total_income = 0
            total_spent = 0
            
            # Допустим, что продажи идут после покупок
            for buy, sell in zip(buy_orders, sell_orders):
                # Выводим для диагностики
                html_content += f"<p>Покупка: Цена={buy['цена']}, Кол-во={buy['кол-во']}, Комиссия={buy['комиссия']}</p>"
                html_content += f"<p>Продажа: Цена={sell['цена']}, Кол-во={sell['кол-во']}, Комиссия={sell['комиссия']}</p>"
                
                total_spent += buy['цена'] * buy['кол-во'] + buy['комиссия']
                total_income += sell['цена'] * sell['кол-во'] - sell['комиссия']

            profit_loss = total_income - total_spent
            
            # Округляем до 5 знаков после запятой
            profit_loss_rounded = round(profit_loss, 5)
            
            # Выводим результат
            html_content += f'<p class="profit-loss">Доход/Расход: {profit_loss_rounded:.5f} USD</p>'

        
        html_content += '</div>'

    html_content += """
    </body>
    </html>
    """
    
    # Сохраняем HTML в файл
    with open('report.html', 'w', encoding='utf-8') as report_file:
        report_file.write(html_content)

# Запуск программы
file_path = 'history.txt'  # Укажите путь к вашему файлу history.txt
process_history_file(file_path)
