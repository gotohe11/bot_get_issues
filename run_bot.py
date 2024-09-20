import telebot
from environs import Env
from threading import Timer
from logic import cli


env = Env()  # Создаем экземпляр класса Env
env.read_env()  # Методом read_env() читаем файл .env и загружаем из него переменные в окружение
API_TOKEN = env('API_TOKEN')
bot = telebot.TeleBot(API_TOKEN)


def bot_print_func(id, obj):
    if isinstance(obj, str):
        bot.send_message(id, f'<b>{obj}</b>', parse_mode='HTML')
    elif isinstance(obj, tuple):
        bot.send_message(id, ' • '.join(str(i) for i in obj))
    elif isinstance(obj, list):
        for item in obj:
            bot_print_func(id, item)
    else:
        print('print mistake')


def bot_check_updates():
    for id in cli.users_command():
        user = cli.login_command(id)
        result = cli.check_updates(user)
        if result:    # посылать уведомление пользователю
            bot_print_func(id, result)


def repeater(interval, function):
    Timer(interval, repeater, [interval, function]).start()
    function()



def main():
    @bot.message_handler(commands = ['start'])
    def start_cmd(message):
        cli.login_command(str(message.from_user.id), message.from_user.first_name)
        bot.send_message(message.chat.id, f'Hi, {message.from_user.first_name}! '
                                          f'I am a bot that brings issues from github by your request.\n'
                                          f'Use </help> command to understand what can i do.')


    @bot.message_handler(commands=['exit', 'stop'])
    def exit_cmd(message):
        bot.send_message(message.chat.id, f'Bye-bye, {message.from_user.first_name}!')
        bot.stop_polling()


    @bot.message_handler(content_types=['text'])
    def handler_cmd(message):
        if not cli.USER:
            cli.login_command(str(message.from_user.id), message.from_user.first_name)
        try:
            result = cli._run_one(message.text)
        except Exception as er:
            print(er)
            bot.send_message(message.chat.id, f'Something went wrong: "{er}".\n'
                                              f'Try again!')
            return
        if isinstance(result, str):
            bot.send_message(message.chat.id, result)
        else:
            bot_print_func(message.chat.id, result)


    repeater(600, bot_check_updates)     # повторение каждые 10мин и при загрузке

    bot.polling(none_stop = True)



if __name__ == "__main__":
    main()