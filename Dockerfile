FROM python:3.12-slim

COPY . /opt/bot_get_issues
WORKDIR /opt

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /opt/bot_get_issues/requirements.txt

CMD [ "python3", "-m", "bot_get_issues"]
