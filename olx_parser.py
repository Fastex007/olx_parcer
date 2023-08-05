import csv
import datetime
import logging
import os
import pprint
import sys
from http import HTTPStatus

import requests
from bs4 import BeautifulSoup, Tag
from furl import furl


class OlxParser:
    BASE_URL = "https://www.olx.pl"
    OFERTY_URL = "https://www.olx.pl/oferty/?search%5Border%5D=created_at:desc"

    def __init__(self, goods_count: int = 200, print_result: bool = False) -> None:
        self.goods_count = goods_count
        self.card_data = []
        self.print_result = print_result

    def handle(self) -> None:
        """
        Обработчик.
        """
        self.get_cards()
        if self.card_data and self.print_result:
            pprint.pprint(self.card_data)

    @staticmethod
    def get_url(base_url, path: str = None, params: dict = None) -> str:
        """
        Формирует необходимый  url для запроса.
        Args:
            base_url: базовый url.
            path: путь.
            params: параметры запроса.

        Returns:
            подготовленный url.
        """
        f_url = furl(url=base_url)
        if path:
            f_url.set(path=path)
        if params:
            f_url.add(args=params)
        return f_url.url

    @staticmethod
    def is_url(url: str) -> bool:
        """
        Проверяет является ли строка ссылкой.
        Args:
            url: вероятная ссылка

        Returns:
            признак того, является ли строка ссылкой или нет.
        """

        return furl(url=url).host

    def get_cards(self) -> None:
        """
        Получает данные и записывает результат
        """
        current_page = 0
        while len(self.card_data) < self.goods_count:
            current_page += 1
            params = None
            if current_page > 1:
                params = {"page": current_page}
            url = self.get_url(base_url=self.OFERTY_URL, params=params)
            response = requests.get(url=url)
            if response.status_code != HTTPStatus.OK:
                logging.error(f"Can't get response from url: {self.OFERTY_URL}, "
                              f"status code: {response.status_code}, {response.text}")
                return None

            bs = BeautifulSoup(response.text, "html.parser")
            cards = bs.findAll("div", class_="css-1sw7q4x")
            if not cards:
                logging.error("Can't find any cards")
                return None
            for card in cards:
                if len(self.card_data) == self.goods_count:
                    break
                data = self.prepare_card_data(card=card)
                if data:
                    self.check_data(data=data)
                    self.card_data.append(data)
                    logging.info(f"Amount collected data: {len(self.card_data)}, page: {current_page}")
        self.write_results()

    @staticmethod
    def check_data(data: dict) -> None:
        """
        Проверяет состав полученных данных.
        Args:
            data: полученные данные.

        Returns:
            None
        """
        if not all(data.values()):
            logging.warning("Not all data received")

    def prepare_card_data(self, card: Tag) -> dict | None:
        """
        Подготавливает данные карточки товара.
        Args:
            card: Tag объект страницы.

        Returns: словарь с данными.

        """
        card_id = card.get("id")
        card_url = card.find("a")
        if card_url:
            card_url = card_url.get("href")
            if not self.is_url(url=card_url):
                card_url = self.get_url(base_url=self.BASE_URL, path=card_url)
        img_url = card.find("img")

        if img_url:
            img_url = img_url.get("src")
            if not self.is_url(url=img_url):
                return None

        name_price_div = card.find("div", class_="css-u2ayx9")
        if not name_price_div:
            return None
        name = name_price_div.find("h6", class_="css-16v5mdi er34gjf0")
        if name:
            name = name.get_text()
        price = name_price_div.find("p", class_="css-10b0gli er34gjf0")
        if price:
            if price == "Zadarmo":
                price = 0
            else:
                price = float(price.get_text().replace(" ", "").replace(",", ".").split("zł")[0])
        state = card.find("span", class_="css-3lkihg")
        if state:
            state = state.get_text()

        return {
            "card_id": card_id,
            "card_url": card_url,
            "img_url": img_url,
            "name": name,
            "price": price,
            "currency_unit": "zł",
            "state": state,
        }

    def write_results(self) -> None:
        """
        Записывает результат парсинга в файл.
        """
        result_folder = "results"
        if not os.path.exists(result_folder):
            os.makedirs(result_folder)
        filename = f"{result_folder}/{str(datetime.datetime.now())}.csv"
        fieldnames = self.card_data[0].keys()
        with open(filename, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.card_data)
        logging.info("CSV file has been created")


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s [%(levelname)s] - '
            '(%(filename)s).%(funcName)s:%(lineno)d - %(message)s'
        ),
        handlers=[
            logging.FileHandler(f'{BASE_DIR}/output.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    OlxParser(print_result=True).handle()
