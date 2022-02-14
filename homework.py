import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename="main.log",
    format="%(asctime)s, %(levelname)s, %(message)s, %(name)s",
    filemode="w",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    "my_logger.log",
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
"5205587614:AAG4pLjf2NS9RauE9QP7s08sGilNDBp7vNY"

HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
    )
    logger.info(f"Сообщение отправлено: {message}")


def get_api_answer(current_timestamp):
    """Запрос к единственному к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != HTTPStatus.OK:
        error_msg = "Сервис API недоступен"
        logger.error(error_msg)
        raise Exception(error_msg)
    logger.info(f"Выполнен запрос к эндпоинту {timestamp}")
    logger.debug(f"Ответ по эндпоинту {homework_statuses.json()}")
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на корректность и возвращает список д/р."""
    if type(response) != dict:
        error_msg = f"Не верный формат данных (dict): {response}"
        logger.error(error_msg)
        raise TypeError(error_msg)
    homework_list = response.get("homeworks")
    if type(homework_list) != list:
        error_msg = f"Не верный формат данных (list): {homework_list}"
        logger.error(error_msg)
        raise TypeError(error_msg)
    if len(homework_list) < 1:
        raise Exception("Нет домашних работ, уточните эндпоинт")
    logger.info("Выполнен проверка ответа API по списку homeworks")
    logger.debug(f"Список домашних работ: {homework_list}")
    return homework_list


def parse_status(homework):
    """Извлекает статус конкретной домашней работы."""
    logger.debug(f"Принят пакет: {homework}")
    homework_name = homework.get("homework_name")
    if not homework_name:
        error_msg = "Отсутсвует имя домашней работы"
        logger.error(error_msg)
        raise KeyError(error_msg)

    homework_status = homework.get("status")
    if not homework_status:
        error_msg = "Отсутсвует статус домашней работы"
        logger.error(error_msg)
        raise KeyError(error_msg)

    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        error_msg = "Не верный статус домашней работы"
        logger.error(error_msg)
        raise KeyError(error_msg)

    logger.info(f"Получен статуc {verdict}")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности окружения."""
    tokens_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if None in tokens_list:
        logger.critical("Недоступны переменные окружения")
        return False
    logger.info("Все переменные окружения доступны")
    return True


def main():
    """Основная логика работы бота."""
    last_error_msg = ""
    last_message = ""
    if not check_tokens():
        last_error_msg = "Не хватает глобальных переменных"
        logger.critical(last_error_msg)
        raise Exception(last_error_msg)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1549962000

    info_msg = "Старт работы бота"
    logger.info(info_msg)
    send_message(bot, info_msg)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            message = parse_status(homeworks[0])
        except Exception as error:
            error_message = f"Сбой в работе программы: {error}"
            if last_error_msg != error_message:
                last_error_msg = error_message
                send_message(bot, last_error_msg)
            time.sleep(RETRY_TIME)
        else:
            if homeworks and last_message != message:
                last_message = message
                send_message(bot, message)
            else:
                logger.debug("Статус работы не изменился")
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
