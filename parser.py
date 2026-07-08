import json
import os
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings()

MAIN_URL = "https://abiturient.manas.edu.kg/page/index.php?r=site%2Fmonitoring-all-deps"
OUTPUT_FILE = Path("data.json")
REQUEST_TIMEOUT = 30
PAUSE_SECONDS = 0.3
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def build_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_soup(session, url):
    response = session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_department_links(soup):
    department_links = []
    seen_urls = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        name = link.get_text(strip=True)

        if "r=site" not in href or "monitoring-all-deps" in href or not name:
            continue

        full_url = urljoin(MAIN_URL, href)
        if full_url in seen_urls:
            continue

        seen_urls.add(full_url)
        department_links.append({"name": name, "url": full_url})

    return department_links


def extract_faculty_name(soup):
    for heading in soup.find_all(["h1", "h2", "h3"]):
        heading_text = heading.get_text(" ", strip=True)
        if "ФАКУЛЬТЕТ" in heading_text.upper():
            return heading_text
    return "ОБЩИЙ СПИСОК"


def extract_applicants(soup):
    applicants = []
    table = soup.find("table")

    if not table:
        return applicants

    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 5:
            continue

        reg_num = cells[1].get_text(" ", strip=True)
        if "Регистрационный" in reg_num or "Номер" in reg_num or not reg_num:
            continue

        number = cells[0].get_text(" ", strip=True)
        score = cells[2].get_text(" ", strip=True)
        lang_score = cells[3].get_text(" ", strip=True)
        reg_date = cells[4].get_text(" ", strip=True)
        clean_id = "".join(char for char in reg_num if char.isdigit())

        if not clean_id:
            continue

        applicants.append(
            {
                "id": number,
                "regNum": reg_num,
                "score": score,
                "langScore": lang_score,
                "regDate": reg_date,
                "photoUrl": (
                    "https://abiturient.manas.edu.kg/page/uploads/photo/"
                    f"{clean_id}.jpg"
                ),
            }
        )

    return applicants


def write_json_atomically(payload, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=output_path.parent,
            prefix=f"{output_path.stem}.",
            suffix=".tmp",
            encoding="utf-8",
        ) as temp_file:
            json.dump(payload, temp_file, ensure_ascii=False, indent=2)
            temp_name = temp_file.name

        os.replace(temp_name, output_path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)


def parse_all_manas_data():
    print("Шаг 1: собираем список всех направлений...")
    session = build_session()
    department_links = extract_department_links(fetch_soup(session, MAIN_URL))
    print(f"Успешно найдено направлений: {len(department_links)}")

    all_data = {}
    errors = []

    print("\nШаг 2: начинаем обход каждого направления...")
    for index, department in enumerate(department_links, 1):
        print(f"[{index}/{len(department_links)}] Загружаем данные: {department['name']}...")

        try:
            department_soup = fetch_soup(session, department["url"])
            faculty_name = extract_faculty_name(department_soup)
            applicants = extract_applicants(department_soup)

            if applicants:
                all_data.setdefault(faculty_name, {})[department["name"]] = applicants
                print(f"   -> Успешно: {len(applicants)} записей")
            else:
                print("   -> Таблица пустая или данные не найдены.")

            time.sleep(PAUSE_SECONDS)
        except Exception as exc:
            message = f"Ошибка при парсинге направления {department['name']}: {exc}"
            print(message)
            errors.append(message)

    if errors:
        raise RuntimeError(
            "Парсинг завершился с ошибками, поэтому data.json не был перезаписан."
        )

    write_json_atomically(all_data, OUTPUT_FILE)
    print("\n[ГОТОВО] Скрипт завершил работу. Файл data.json обновлен атомарно.")


if __name__ == "__main__":
    parse_all_manas_data()
