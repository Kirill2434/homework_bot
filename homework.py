import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv
from telegram import TelegramError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
handler = RotatingFileHandler('my_logger.log',
                              maxBytes=50000000,
                              backupCount=5
                              )
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения ботом."""
    try:
        logging.info('Сообщение отправлено')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise TelegramError(f'Сообщение не было отправлено {error}')


def get_api_answer(current_timestamp):
    """Отправка запроса API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    error_message = 'Возникли проблемы с запросом API'
    error_text = 'Отсутствует соединение с интернетом'
    try:
        logging.info('Запрос отправлен')
        homework_status = requests.get(ENDPOINT,
                                       headers=HEADERS,
                                       params=params)
    except Exception:
        raise requests.exceptions.ConnectionError(error_text)
    if homework_status.status_code == 200:
        return homework_status.json()
    else:
        raise TypeError(error_message)


def check_response(response):
    """Проверка запроса."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка. Ответ не явялется словарем!')
    try:
        homework_main = response['homeworks']
    except KeyError:
        logger.error('Ошибка. Неверный ключ')
        raise KeyError('Ошибка. Неверный ключ')
    return homework_main[0]


def parse_status(homework):
    """Проверка статуса домашней работы."""
    keys = ['homework_name', 'status']
    for key in keys:
        if key not in homework:
            raise KeyError(f'Отсутсвует ключ: {key}')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in VERDICTS:
        raise KeyError('Неизвестный статус')
    verdict = VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Критическая ошбика в переменных')
        return sys.exit('Ошибка в переменных окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    empty_response = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            check_homework = check_response(response)
            if check_homework != empty_response:
                message = parse_status(check_homework)
                send_message(bot, message)
            else:
                logger.debug('Обновлений по статусу ревью нет.')
                current_timestamp = check_homework.get('current timestamp')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            error_send_messeg = 'Ошибка отправки сообщения'
            if error == TelegramError(error_send_messeg):
                logger.error(error_send_messeg)
            logger.error(message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
