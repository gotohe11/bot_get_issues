import logging
import telebot
import threading
from collections.abc import Callable
from environs import Env
from typing import Any

from logic import cli


logger = logging.getLogger(__name__)

env = Env()  # создаем экземпляр класса Env
env.read_env()  # м-м read_env() читаем .env и загружаем переменные в окр-е
API_TOKEN = env('API_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

FLAG_TIMER = True  # переключатель для ф-ии bot_check_updates


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
    """Периодически проверяет новые исусы у пользователя в подписках.
    :param repeater_: функция-планировщик, выполняющая ф-ию
        bot_check_updates через определенный промежуток времени.
    """
    if FLAG_TIMER:  # если юзер еще не ввел команду stop/exit
        logger.info('Checking updates for users')
        for user_id in cli.users_command():
            user = cli.login_command(user_id)
            result = cli.check_updates(user)
            if result:  # посылать уведомление пользователю
                bot_print_func(user_id, result)
        repeater_()


def repeater():
    """Запускает ф-ию через заданный период времени.
    """
    # interval=600 - заданный период - 600сек.
    t = threading.Timer(interval=600, function=bot_check_updates, args=(repeater,))
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


    @bot.message_handler(commands=['exit', 'stop'])
    def exit_cmd(message):
        bot.send_message(message.chat.id, f'Bye-bye, {message.from_user.first_name}!')
        bot.stop_polling()
        global FLAG_TIMER
        FLAG_TIMER = False


    @bot.message_handler(content_types=['text'])
    def handler_cmd(message):
        """Обработчик любой текстовой команды тг-бота.
        :param message: сообщение в тг-боте.
        :raises: любая ошибка модуля cli.
        """
        if not cli.USER:
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

    bot_check_updates(repeater)  # запускаем проверку обновлений подписок юзера
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
