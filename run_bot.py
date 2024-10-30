import logging
import logging.config
import os
import redis
import telebot
import time
import threading
import yaml
from collections.abc import Callable
from environs import Env
from typing import Any

from .logic import cli
from .logic.database import Database
from .logic.github import GithubError


logger = logging.getLogger(__name__)

env = Env()  # создаем экземпляр класса Env
env.read_env()  # м-м read_env() читаем .env и загружаем переменные в окр-е
API_TOKEN = env('API_TOKEN')
bot = telebot.TeleBot(API_TOKEN)


def get_redis_connection(max_retries=5, delay=2):
    """Проверяет подключение к redis.
    :param max_retries: максимальное количество попыток подключения.
    :param delay: задержка между попытками подключения (в сек.).
    :raises: redis.ConnectionError.
    """
    for attempt in range(max_retries):
        try:
            r = redis.Redis(host='redis', port=6379, db=0, socket_connect_timeout=2)
            r.ping()
            logger.debug("Successful connection to Redis.")
        except redis.ConnectionError:
            logger.warning(f"Redis error connection. Attempt {attempt + 1}/{max_retries}.")
            time.sleep(delay)
    logger.error("Failed to connect to Redis after several attempts.")


def load_log_settings():
    """Подгружает настройки логирования из yml-файла,
    создает необходимые папки для логов.
    """
    os.makedirs(os.path.dirname('bot_get_issues/logs/bot_logs.log'), exist_ok=True)
    os.makedirs(os.path.dirname('bot_get_issues/bot_logs/bot_logs.log'), exist_ok=True)
    with open('bot_get_issues/logging_config.yaml', 'rt') as f:
        config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)


def bot_print_func(user_id: str, item: Any):
    """Печатает сообщения в чате в зависимости от типа данных.
    :param user_id: id пользователя тг.
    :param item: последовательность, которую нужно отправить
        пользователю в тг-боте в том или ином виде.
    """
    if isinstance(item, str):
        bot.send_message(user_id, f'<b>{item}</b>', parse_mode='HTML')
    elif isinstance(item, tuple):
        bot.send_message(user_id, ' • '.join(str(i) for i in item))
    elif isinstance(item, list):
        for i in item:
            bot_print_func(user_id, i)
    else:
        logger.error('Here is an error with printing')


def bot_check_updates(repeater_: Callable):
    """Периодически проверяет новые исусы у пользователей в подписках.
    :param repeater_: функция-планировщик, выполняющая ф-ию
        bot_check_updates через определенный промежуток времени.
    """
    logger.info('Checking updates for users')
    for user in Database.get_all_users():
        try:
            result = cli.check_updates(user)
            if result:  # посылать уведомление пользователю
                bot_print_func(user.user_id, result)
        except GithubError as er:
            bot_print_func(user.user_id,
                           'Error communication with GitHub. Try later!')
    repeater_()


def repeater():
    """Запускает ф-ию через заданный период времени в секундах.
    """
    t = threading.Timer(interval=1200, function=bot_check_updates, args=(repeater,))
    t.start()
    logger.info(f'Timer has started in {threading.current_thread().name}')


def main():
    @bot.message_handler(commands=['start'])
    def start_cmd(message):
        cli.login_command(str(message.from_user.id), message.from_user.first_name)
        bot.send_message(message.chat.id, (
            f'Hi, {message.from_user.first_name}! '
            f'I am a bot that brings issues from github by your request.\n'
            f'Use </help> command to understand what can i do.'
        ))


    @bot.message_handler(content_types=['text'])
    def handler_cmd(message):
        """Обработчик любой текстовой команды тг-бота.
        :param message: сообщение в тг-боте.
        :raises: любая ошибка модуля cli.
        """
        cli.login_command(str(message.from_user.id), message.from_user.first_name)
        try:
            result = cli.run_one(message.text)
        except Exception as er:
            logger.exception(er)
            bot.send_message(message.chat.id,
                             f'Something went wrong: "{er}".\nTry again!')
            return

        if isinstance(result, str):
            bot.send_message(message.chat.id, result)
        else:
            bot_print_func(message.chat.id, result)


    load_log_settings()  # подгружаем настройки логгирования
    get_redis_connection()  # проверяем подключение к redis
    bot_check_updates(repeater)  # запускаем проверку обновлений подписок у юзеров
    bot.infinity_polling(timeout=10, long_polling_timeout=5)


if __name__ == '__main__':
    main()
