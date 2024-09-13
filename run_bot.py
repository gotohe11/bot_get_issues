import telebot
from environs import Env
from logic import cli


env = Env()  # Создаем экземпляр класса Env
env.read_env()  # Методом read_env() читаем файл .env и загружаем из него переменные в окружение
API_TOKEN = env('API_TOKEN')
bot = telebot.TeleBot(API_TOKEN)


def main():
    @bot.message_handler(commands = ['start'])
    def start_cmd(message):
      bot.send_message(message.chat.id, 'Hi! I am a bot that brings issues from github by your request.\n'
                                        'Use </help> command to understand what can i do.')


    @bot.message_handler(commands=['exit', 'stop'])
    def exit_cmd(message):
        bot.send_message(message.chat.id, 'Bye-bye!')
        bot.stop_polling()


    @bot.message_handler(content_types=['text'])
    def handler_cmd(message):
        try:
            result = cli._run_one(message.text)

        except Exception as er:
            print(er)
            bot.send_message(message.chat.id, f'Something went wrong: "{er}".\n'
                                              f'Try again!')
            return
        if isinstance(result, str):
            bot.send_message(message.chat.id, result)
        elif isinstance(result, list):
            for item in result:
                bot.send_message(message.chat.id, ', '.join(str(i) for i in item))




    bot.polling(none_stop = True)



if __name__ == "__main__":
    main()