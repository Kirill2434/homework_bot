import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    'my_logger.log', 
    maxBytes=50000000, 
    backupCount=5
    )
logger.addHandler(handler)


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Невозможно отправить сообщение {error}')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    error_message = 'Возникли проблемы с запросом API'
    try:
        logging.info('Запрос отправлен')
        homework_status = requests.get(
            ENDPOINT, 
            headers=HEADERS, 
            params=params
        )
    except ValueError as error:
        logging.error(f'Не был получен ответ. {error}')
        raise error
    if homework_status.status_code == 200:
        return homework_status.json()
    else:
        logging.error(error_message)
        raise TypeError(error_message)


def check_response(response):
    if type(response) != dict:
        raise TypeError('Ошибка. Ответ не явялется словарем!')
    try:
        homework_main = response['homeworks']
    except KeyError:
        logger.error('Ошибка. Неверный ключ')
        raise KeyError('Ошибка. Неверный ключ')
    try:
        homework_main[0]
    except IndexError:
        logger.error('Ошибка. Домашнего задания нет')
        raise IndexError('Ошибка. Домашнего задания нет')
    return homework_main[0]


def parse_status(homework):
    if 'homework_name' not in homework:
        raise KeyError('homework_name отсутствует в homework')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception('Неизвестный статус')
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for key, value in tokens.items():
        if not value:
            return False
        return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Критическая ошбика в переменных')
        return None
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    none = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            check_homework = check_response(response)
            if check_homework != none:
                message = parse_status(check_homework)
                send_message(bot, message)
            else:
                logger.debug('Обновлений по статусу ревью нет.')
                current_timestamp = check_homework.get('current timestamp')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
