import json
import requests
from bs4 import BeautifulSoup


def parse_manas_rating():
    # URL страницы мониторинга (замени на актуальный, если нужно)
    url = "https://abiturient.manas.edu.kg/page/index.php?r=site%2Fmonitoring-all-deps"

    # Добавляем User-Agent, чтобы сервер не думал, что мы подозрительный бот
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("Скачиваем страницу...")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Ошибка загрузки сайта: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    applicants = []

    # Находим все строки таблицы внутри tbody
    # (Если на сайте таблиц несколько, возможно придется уточнить селектор)
    rows = soup.select("table tbody tr")

    print("Парсим данные абитуриентов...")
    for row in rows:
        cells = row.find_all("td")

        # Проверяем, что в строке достаточно колонок (минимум 5, как на скрине)
        if len(cells) >= 5:
            num = cells[0].text.strip()  # № п/п
            reg_num = cells[1].text.strip()  # Регистрационный номер (например, 26009067)
            score = cells[2].text.strip()  # Баллы
            lang_score = cells[3].text.strip()  # Иностранный язык
            reg_date = cells[4].text.strip()  # Дата регистрации

            # Формируем структуру для каждого челика
            applicants.append(
                {
                    "id": num,
                    "regNum": reg_num,
                    "score": score,
                    "langScore": lang_score,
                    "regDate": reg_date,
                    # Генерируем прямую ссылку на фото, которую мы нашли на скрине image_10a6d5.png
                    "photoUrl": f"https://abiturient.manas.edu.kg/page/uploads/photo/{reg_num}.jpg",
                }
            )

    # Сохраняем результат в data.json с поддержкой UTF-8 (чтобы кириллица не ломалась)
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(applicants, f, ensure_ascii=False, indent=2)

    print(f"Готово! Успешно сохранено {len(applicants)} абитуриентов в data.json")


if __name__ == "__main__":
    parse_manas_rating()