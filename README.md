# Telegram chatbot with Python and Docker

This is a [Telegram chatbot](https://core.telegram.org/bots) I created as a learning experience back in 2015, based on the [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) library. It mantains a simple control of who is the next person to pay for coffee.

It was initially hosted on a Raspberry Pi at home. More recently, all its dependencies have been packed in a [Docker](https://docs.docker.com/get-docker/) container, and hosting has been moved to the cloud.

## Requirements

 * A [Telegram Messenger](https://telegram.org/) account.
 * [SQLite](https://www.sqlite.org/) to create the database structure.
 * Port forwarding set on your router (if hosted at home) or on the network security of your cloud provider. We use the standard Telegram chatbot port 8443 on this project.

The following dependencies will be downloaded when building the Dockerfile:

 * [Alpine Linux Docker image](https://hub.docker.com/_/alpine)
 * [Python 3](https://www.python.org/)
 * [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
 * [Flask](https://palletsprojects.com/p/flask/)

## How to install

1. Create a [Telegram Messenger](https://telegram.org/) account.
2. Create a new bot with [BotFather](https://core.telegram.org/bots#6-botfather), using the `/newbot` command. The bot name and token string will be used later.
3. Set the bot commands with `/setcommands`, using the contents of the `src/commands.txt` file.
4. Change the `src/local_config.py` file to reflect the bot name, the token string, the host external IP address and the bot port to communicate with the Telegram Bot API.
5. At the `src/` directory, set a new SSL key pair.
```
openssl req -new -x509 -nodes -newkey rsa:1024 -keyout server.key -out server.crt -days 3650
```
6. At the bot home directory, build the Docker container. This may take a while.
```
sudo docker build -t telegram-bot .
```
7. Create the database structure.
```
sqlite3 vol/db-schema.sql > vol/cafe.db
```
8. Run the docker image.
```
sudo docker run --rm -d -v $(pwd)/vol:/app/vol -p 8443:8443 telegram-bot
```
9. You can check that the bot is running by checking its execution log.
```
sudo docker logs telegram-bot
```

## How to use the bot
Warning: non-english commands below:

This chatbot is designed to run in a group chat.
1. Create a new Telegram group chat.
2. Invite your bot to the group chat.
3. Register a sample payment with `/pagou`. For example, `/pagou Alice Bob Charlie` means Alice paid for Bob's and Charlie's coffees. Alice now has two coffee credits (+2), while Bob and Charlie both own a coffee credit (-1) to the group.
4. You can list the last payments with `/pagamentos` and revert the last one with `/apague 1`, assuming that the last payment is payment #1.

The following bot commands are available - currently in Porguese - see [Localization](#localization) below:
 * `/quem` - show the current group balance, and who's the next one to pay.
 * `/pagou` - record a new payment. `/pagou Alice Bob Charlie` means that Aplice payd for Bob's and Charlie's coffee.
 * `/pontos` - list the balance of members of the group.
 * `/nomes` - list the group member's names.
 * `/zerados` - list the group members with zero balance.
 * `/todos` - list all active group members, including the ones with zero balances.
 * `/pagamentos` - show the last payments.
 * `/apague` - revert one of the payments shown with `/pagamentos`.
 * `/mescle` - merge two group members, their balance and payment history. Used to fix member names incorrectly created by mistake. `/mescle Alice Allice` will merge all "Allice" payments into Alice's history and balance.
 * `/inative` - Inactivate a user who won't participate for a while. Useful if a group member goes on vacation. Inactive users will be shown with an `*` next to its name.
* `/inativos` - List inactive members.
 * `/reative` - Reactivate an inactive user.
 * `/audita` - Experimental feature, usually not shown to the users. Show the last iteractions of a specific user.

## Localization
The bot commands (and even most of the database structure) are written in Portuguese, but shouldn't be too complicated to port to another language.
