import logging.config
import yaml

from . import run_bot


with open('bot_get_issues/logging_config.yaml', 'rt') as f:
    config = yaml.safe_load(f.read())

logging.config.dictConfig(config)


def main():
    run_bot.main()


if __name__ == '__main__':
    main()
