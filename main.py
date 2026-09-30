"""
Курсовая работа: резервное копирование картинок кошек
с сайта cataas.com на Яндекс.Диск.

Токен Яндекс.Диска читается из переменной окружения YANDEX_TOKEN.
"""

import json
import os
import sys
from urllib.parse import quote

import requests
from tqdm import tqdm

YANDEX_API = "https://cloud-api.yandex.net/v1/disk/resources"
CATAAS_API = "https://cataas.com/cat/says"


class YandexDiskClient:
    """Клиент для работы с REST API Яндекс.Диска."""

    def __init__(self, token: str) -> None:
        self.headers = {"Authorization": f"OAuth {token}"}

    def create_folder(self, folder: str) -> None:
        """Создаёт папку на Диске. Если существует — ничего не делает."""
        params = {"path": f"/{folder}"}
        response = requests.put(
            YANDEX_API,
            headers=self.headers,
            params=params,
            timeout=30,
        )
        if response.status_code not in (201, 409):
            response.raise_for_status()

    def get_upload_url(self, remote_path: str) -> str:
        """Возвращает временный URL для загрузки файла."""
        params = {"path": remote_path, "overwrite": "true"}
        response = requests.get(
            f"{YANDEX_API}/upload",
            headers=self.headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["href"]

    def upload_bytes(self, data: bytes, remote_path: str) -> None:
        """Загружает файл на Диск из памяти (без локального файла)."""
        upload_url = self.get_upload_url(remote_path)
        response = requests.put(
            upload_url, data=data, timeout=120
        )
        response.raise_for_status()


class CatBackup:
    """Резервное копирование картинок кошек с текстом на Яндекс.Диск."""

    def __init__(self, token: str, folder: str) -> None:
        self.client = YandexDiskClient(token)
        self.folder = folder
        self.report = []

    def fetch_cat(self, text: str) -> bytes:
        """Получает картинку кота с текстом и возвращает её байты."""
        url = f"{CATAAS_API}/{quote(text)}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content

    def run(self, texts) -> None:
        self.client.create_folder(self.folder)

        for text in tqdm(texts, desc="Загрузка котиков", unit="шт"):
            data = self.fetch_cat(text)
            filename = f"{text}.jpg"
            remote_path = f"/{self.folder}/{filename}"

            self.client.upload_bytes(data, remote_path)

            self.report.append(
                {
                    "name": filename,
                    "path": remote_path,
                    "source": f"{CATAAS_API}/{text}",
                }
            )

        with open("results.json", "w", encoding="utf-8") as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)

        print(f"\nГотово! Загружено файлов: {len(self.report)}")
        print("Отчёт сохранён в results.json")


def main() -> None:
    token = os.getenv("YANDEX_TOKEN")
    if not token:
        print("Ошибка: не задан токен Яндекс.Диска.")
        print("Установите переменную окружения YANDEX_TOKEN.")
        sys.exit(1)

    folder = input("Введите название папки (группа в Нетологии): ").strip()
    text = input("Введите текст для картинок: ").strip()

    if not folder or not text:
        print("Папка и текст не могут быть пустыми.")
        sys.exit(1)

    backup = CatBackup(token=token, folder=folder)
    backup.run([text])


if __name__ == "__main__":
    main()