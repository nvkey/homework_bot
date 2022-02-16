import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv
# from requests.exceptions import HTTPError

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename="main.log",
    format="%(asctime)s, %(levelname)s, %(funcName)s , %(message)s, %(name)s",
    filemode="w",
    encoding="UTF-8",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    "my_logger.log",
    maxBytes=50000000,
    backupCount=5,
    encoding="UTF-8",
)
logger.addHandler(handler)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 60
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    logger.debug(f"Принята отправка боту: {bot}")
    logger.debug(f"Принято сообщение: {message}")
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.info(f"Сообщение отправлено: {message}")
    except Exception as error:
        logger.exception(f"Сбой отправки, ошибка: {error}")
        raise error


def get_api_answer(current_timestamp):
    """Запрос к единственному к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params)
        status = homework_statuses.status_code
        if status != HTTPStatus.OK:
            logger.exception(f"HTTP ошибка: {status}")
            raise Exception
        # homework_statuses.raise_for_status() тест не работает с этим методом
    # except HTTPError as http_error:
        # logger.exception(f"HTTP ошибка: {http_error}")
        # raise http_error
    except Exception as error:
        logger.exception(f"Ошибка: {error}")
        raise error
    logger.info(f"Выполнен запрос к эндпоинту {timestamp}")
    logger.debug(f"Ответ по эндпоинту {homework_statuses.json()}")
    if homework_statuses is None:
        raise Exception
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на корректность и возвращает список д/р."""
    if not isinstance(response, dict):
        error_msg = f"Не верный формат данных (dict): {response}"
        logger.error(error_msg)
        raise TypeError(error_msg)
    homework_list = response.get("homeworks")
    if not isinstance(homework_list, list):
        error_msg = f"Не верный формат данных (list): {homework_list}"
        logger.error(error_msg)
        raise TypeError(error_msg)
    if len(homework_list) < 1:
        error_msg = "Нет домашних работ, уточните эндпоинт"
        logger.error(error_msg)
        raise Exception(error_msg)
    logger.info("Выполнен проверка ответа API по списку homeworks")
    logger.debug(f"Список домашних работ: {homework_list}")
    return homework_list


def parse_status(homework):
    """Извлекает статус конкретной домашней работы."""
    logger.debug(f"Принят пакет: {homework}")
    homework_name = homework.get("homework_name")
    if homework_name is None:
        error_msg = "Отсутсвует имя домашней работы"
        logger.error(error_msg)
        raise KeyError(error_msg)

    homework_status = homework.get("status")
    if homework_status is None:
        error_msg = "Отсутсвует статус домашней работы"
        logger.error(error_msg)
        raise KeyError(error_msg)

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        error_msg = "Не верный статус домашней работы"
        logger.error(error_msg)
        raise KeyError(error_msg)

    logger.info(f"Получен статуc {verdict}")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности окружения."""
    tokens_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    check = all(tokens_list)
    if check:
        logger.info("Переменные окружения доступны")
        return check
    logger.critical("Недоступны переменные окружения")
    return check


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
            logger.exception(error_message)
            if last_error_msg != error_message:
                send_message(bot, last_error_msg)
                last_error_msg = error_message
            time.sleep(RETRY_TIME)
        else:
            if homeworks and last_message != message:
                send_message(bot, message)
                last_message = message
            else:
                logger.debug("Статус работы не изменился")
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
