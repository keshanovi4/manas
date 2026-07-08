import json
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# Отключаем предупреждения об SSL
requests.packages.urllib3.disable_warnings()


def parse_all_manas_data():
    main_url = "https://abiturient.manas.edu.kg/page/index.php?r=site%2Fmonitoring-all-deps"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("Шаг 1: Собираем список всех направлений...")
    try:
        response = requests.get(main_url, headers=headers, verify=False)
    except Exception as e:
        print(f"Не удалось загрузить главную страницу: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    dep_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.text.strip()

        if "r=site" in href and "monitoring-all-deps" not in href and text:
            full_url = urljoin(main_url, href)
            if full_url not in [d["url"] for d in dep_links]:
                dep_links.append({"name": text, "url": full_url})

    print(f"Успешно найдено направлений: {len(dep_links)}")

    all_data = {}

    print("\nШаг 2: Начинаем обход каждого направления...")
    for index, dep in enumerate(dep_links, 1):
        print(
            f"[{index}/{len(dep_links)}] Скачиваем данные: {dep['name']}..."
        )

        try:
            dep_response = requests.get(dep["url"], headers=headers, verify=False)
            dep_soup = BeautifulSoup(dep_response.text, "html.parser")

            # Ищем название факультета
            faculty_name = "ОБЩИЙ СПИСОК"
            for heading in dep_soup.find_all(["h1", "h2", "h3"]):
                if "ФАКУЛЬТЕТ" in heading.text.upper():
                    faculty_name = heading.text.strip()
                    break

            applicants = []

            # Ищем ПЕРВУЮ попавшуюся таблицу на странице направления
            table = dep_soup.find("table")
            if table:
                # Берем вообще все строки таблицы (и с tbody, и без него)
                rows = table.find_all("tr")

                for row in rows:
                    cells = row.find_all(["td", "th"])

                    if len(cells) >= 5:
                        reg_num = cells[1].text.strip()

                        # Пропускаем строку заголовков таблицы, если она попалась
                        if (
                            "Регистрационный" in reg_num
                            or "Номер" in reg_num
                            or not reg_num
                        ):
                            continue

                        num = cells[0].text.strip()
                        score = cells[2].text.strip()
                        lang_score = cells[3].text.strip()
                        reg_date = cells[4].text.strip()

                        # Очищаем номер: оставляем ТОЛЬКО цифры для названия файла фото
                        # (Например, из '10As26009067' или ' 26009067 ' сделает '26009067')
                        clean_id = "".join(filter(str.isdigit, reg_num))

                        if clean_id:  # Если нашли хоть какие-то цифры номера
                            applicants.append(
                                {
                                    "id": num,
                                    "regNum": reg_num,  # В таблицу выводим оригинальный номер
                                    "score": score,
                                    "langScore": lang_score,
                                    "regDate": reg_date,
                                    # Ссылку генерируем по чистой цифровой части
                                    "photoUrl": f"https://abiturient.manas.edu.kg/page/uploads/photo/{clean_id}.jpg",
                                }
                            )

            if applicants:
                if faculty_name not in all_data:
                    all_data[faculty_name] = {}
                all_data[faculty_name][dep["name"]] = applicants
                print(f"   -> УСПЕШНО! Спарсено абитуриентов: {len(applicants)}")
            else:
                print("   -> Таблица пустая (нет строк с данными).")

            time.sleep(0.3)  # Небольшая пауза между запросами

        except Exception as e:
            print(f"Ошибка при парсинге направления {dep['name']}: {e}")

    # Перезаписываем data.json
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print("\n[ГОТОВО] Скрипт завершил работу. Проверь файл data.json!")


if __name__ == "__main__":
    parse_all_manas_data()