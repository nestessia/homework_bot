import telegram
import os
from dotenv import load_dotenv
import requests
import time
import logging

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка токенов."""
    variables = [TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN]
    if not all(variables):
        logging.critical('Нет переменных окружения!!!')
        raise ValueError("Отсутствуют переменные окружения")
    return all(variables)


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение в Telegram успешно отправлено.')
    except Exception as error:
        logging.error(f'Сообщение не отправлено. Ошибка {error}')


def get_api_answer(timestamp):
    """Запрос к API."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS,
                                params=payload)
    except Exception as error:
        logging.exception(f'Ошибка при запросе: {error}')

    if response.status_code != 200:
        raise requests.RequestException(f'Ошибка кода статуса: '
                                        f'{response.status_code} '
                                        f'{response.text}.')
    return response.json()


def check_response(response):
    """Проверка ответка от API."""
    try:
        response = response['homeworks']
    except KeyError:
        raise KeyError('Нет ключа "homeworks"')
    if not isinstance(response, list):
        raise TypeError('Данные не в виде списка. Текущий тип данных - '
                        f'{type(response)}')
    return True


def parse_status(homework):
    """Парсинг статуса."""
    sections = ['status', 'homework_name']

    for section in sections:
        if section not in homework:
            logging.error(f'Отсутствуют данные {section}')
            raise KeyError(f'Отсутствуют данные {section}')
    status = homework['status']
    homework_name = homework['homework_name']
    if status not in HOMEWORK_VERDICTS:
        logging.debug('Финальный проект не проверен')
        raise KeyError('Такого статуса нет в перечне.')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            timestamp = int(time.time())
            response = get_api_answer(timestamp)
            check_response(response)
            if response['homeworks']:
                message = parse_status(response['homeworks'][0])
                logging.debug('Значение не изменилось')
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        filemode='w',
        format='%(asctime)s, %(levelname)s, %(message)s')
    console_handler = logging.StreamHandler()
    main()
