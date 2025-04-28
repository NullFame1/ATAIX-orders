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
            .profit-percentage {
                font-weight: bold;
                color: #007BFF;
            }
        </style>
    </head>
    <body>
    <h1>Отчет по Ордеру</h1>
    """

    for originalID, orders in grouped_data.items():
        html_content += f'<div class="report-section"><h2>OriginalID: {originalID}</h2>'
        
        orders_sorted = sorted(orders, key=lambda x: x['время'])
        
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

        buy_orders = [o for o in orders if 'покупка' in o["событие"].lower()]
        sell_orders = [o for o in orders if 'продажа' in o["событие"].lower()]

        if len(buy_orders) != len(sell_orders):
            html_content += '<p class="profit-loss">Ошибка: количество покупок и продаж не совпадает.</p>'
        else:
            total_income = 0
            total_spent = 0
            
            for buy, sell in zip(buy_orders, sell_orders):
                html_content += f"<p>Покупка: Цена={buy['цена']}, Кол-во={buy['кол-во']}, Комиссия={buy['комиссия']}</p>"
                html_content += f"<p>Продажа: Цена={sell['цена']}, Кол-во={sell['кол-во']}, Комиссия={sell['комиссия']}</p>"
                
                total_spent += buy['цена'] * buy['кол-во'] + buy['комиссия']
                total_income += sell['цена'] * sell['кол-во'] - sell['комиссия']

            profit_loss = total_income - total_spent
            profit_loss_rounded = round(profit_loss, 5)

            # Вычисляем процент прибыли относительно total_spent
            if total_spent != 0:
                profit_percent = (profit_loss / total_spent) * 100
            else:
                profit_percent = 0

            profit_percent_rounded = round(profit_percent, 2)

            # Выводим результат дохода/убытка
            profit_color = "blue" if profit_loss_rounded >= 0 else "red"
            html_content += f'<p class="profit-loss">Доход/Убыток: <span style="color: {profit_color};">{profit_loss_rounded:.5f} USD</span></p>'

            # Выводим процент дохода/убытка
            profit_percent = (profit_loss / total_spent) * 100 if total_spent != 0 else 0
            profit_percent_rounded = round(profit_percent, 2)
            percent_color = "blue" if profit_percent_rounded >= 0 else "red"
            html_content += (
                '<p class="profit-percentage" style="color: black;">'
                'Процент дохода/убытка: '
                f'<span style="color: {percent_color};">{profit_percent_rounded:.2f}%</span>'
                '</p>'
            )

        
        html_content += '</div>'

    html_content += """
    </body>
    </html>
    """
    
    with open('report.html', 'w', encoding='utf-8') as report_file:
        report_file.write(html_content)


# Запуск программы
file_path = 'history.txt'  # Укажите путь к вашему файлу history.txt
process_history_file(file_path)
