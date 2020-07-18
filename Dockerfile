,# Python Telegram bot Dockerfile

# build with: sudo docker build . -t python-telegram-bot
# run with:   sudo docker run -d -v $(pwd)/vol:/vol python-telegram-bot

FROM alpine

RUN apk add --update \
  python3 \
  python3-dev \
  alpine-sdk \
  libffi-dev \
  openssl-dev \
  py3-pip

RUN pip3 install \
  Flask \
  python-telegram-bot

WORKDIR /app

RUN mkdir /app/src

COPY ./src/* ./src/

EXPOSE 8443

CMD /usr/bin/python3 ./src/telegram-bot.py
