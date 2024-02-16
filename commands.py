from telebot import types

class SCOMMANDS:
    create_a_chat = '/create_a_chat'
    pass


class cmdGuru:
    def __init__(self, set):
        self.soft = set.soft_commands
        self.hard = set.hard_commands
        self.rel  = set.rel_commands

    def setMask(self, cmd, value):
        if cmd in self.hard:
            self.hard[cmd][1] = value
        else:
            if cmd in self.rel:
                self.rel[cmd][1] = lambda X: value

    def getHardCommands(self):
        cmds = {}
        for c in self.hard:
            if self.hard[c][1]:
                cmds[c] =  self.hard[c][0]

        for c in self.rel:
            try:
                if (self.rel[c][1](cmds)):
                    cmds[c] = self.rel[c][0]
            except:
                cmds[c] = self.rel[c][0]

        return cmds

class UCOMMANDS:
    soft_commands = {
                     'le_risposte': 'прислать ответы к последнему уроку',
                     'controlla'  : 'проверка урока преподавателем',
                     'prossima'   : 'получить еще один урок без очереди'
                     }

    hard_commands = {
                     'start': ['повторить последнее сообщение и в случае сбоя', True],
                     'status':['показать информацию и статус ученика', True],
                     'aiuto': ['уведомить учителя о вопросе',True],
                     'nonfunziona': ['уведомить о техническом сбое или если кажется, что что-то не так', True],
                     'congelare': ['отправить запрос на заморозку', True]
                    }

    rel_commands = {
                     'risolto' :['cнять вызов учителя',lambda X: not(X['aiuto'])],
                     'funziona':['отмена сигнала о сбое', lambda X: not(X['nonfunziona'])],
                     'scongelare': ['разморозить курс', lambda X: not(X['congelare'])]
                   }

class TCOMMANDS:
    soft_commands = {'le_risposte': 'посмотреть ответы к уроку',
                     'controllato': 'проверка урока преподавателем',
                     'prossima'   : 'получить еще один урок без очереди'}
    hard_commands = {
        'status': ['доступные команды и статус ученика', True],
        'risolto': ['вопрсо ученика решен, (снять вызов учителя)', False],
        'funziona': ['сбой исправлен, (снять вызов)', False],
        'congelare': ['замарозить курс', False],
        'cheat42;[лист!ячейка]': ['посмотреть ячейку (для отладки, кнопки не активны)', True],
        'moveto;[лист!ячейка]' : ['перейти к другому уроку', True],
        'paid;[уроков;дней]' : ['Подтвердить оплату ученика', True]
    }
    rel_commands = {}
    pass

class GCOMMANDS:
    soft_commands = {}

    hard_commands = {
        'sendcold;[лист!ячейка]': ['рассылка адресатам со вкладке cold', True],
        'cheat42;[лист!ячейка]': ['посмотреть ячейку (для отладки, кнопки не активны)', True],
        'start': ['Cинхронизировать таблицы: записать все из кэша, потом прочитать из таблицы', True]
    }
    rel_commands = {}
    pass

class PAY_OPTIONS:

    PRICE_1 = types.LabeledPrice(label="3 месяца обучения", amount=54990 * 100)  # в копейках (руб)
    PRICE_2 = types.LabeledPrice(label="1 неделя обучения", amount=5900 * 100)  # в копейках (руб)
    PRICE_3 = types.LabeledPrice(label="2 урока", amount=2000 * 100)  # в копейках (руб)

    options={'pr_1':{
              'active': True,
              'price': PRICE_1,
              'button': '3 месяца за ' + str(PRICE_1.amount/100) + ' рублей',
              'dscr': 'Идеально подойдет тем, кому нужно говорить уже вчера, нет системных знаний и хочется почувствовать прогресс в обучении.',
              'invoice_payload':'mounth3', 'start_parameter':'three-month-subscription',
              'photo_url': 'https://dl.dropboxusercontent.com/scl/fi/g9zlqj85vit74ymrjpsg0/logo_langusto.png?rlkey=2qd8i57bmz6tt20x0c2fzyeml&dl=0',
              'photo_height': 239, 'photo_width': 256, 'photo_size': 256, 'period':100, 'num':60
              },
              'pr_2':{'price': PRICE_2,
                      'button': '1 неделя ' + str(PRICE_2.amount / 100) + ' рублей',
              'active': True,
              'dscr': 'Включает 5 уроков.',
              'invoice_payload': 'week1', 'start_parameter': 'one-week-subscription',
              'photo_url': 'https://dl.dropboxusercontent.com/scl/fi/g9zlqj85vit74ymrjpsg0/logo_langusto.png?rlkey=2qd8i57bmz6tt20x0c2fzyeml&dl=0',
              'photo_height': 239, 'photo_width': 256, 'photo_size': 256, 'period':14, 'num':5
              },
              'pr_3':{'price': PRICE_3,
              'active': False,
              'button': '2 урока за ' + str(PRICE_3.amount / 100) + ' рублей',
              'dscr': 'Для очень скупых.',
              'invoice_payload': '2-lessons', 'start_parameter': 'two-lessons-subscription',
              'photo_url': 'https://dl.dropboxusercontent.com/scl/fi/g9zlqj85vit74ymrjpsg0/logo_langusto.png?rlkey=2qd8i57bmz6tt20x0c2fzyeml&dl=0',
              'photo_height': 239, 'photo_width': 256, 'photo_size': 256, 'period':7, 'num':2
              }
    }
    pass
