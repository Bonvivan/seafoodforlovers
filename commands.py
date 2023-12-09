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
        'cheat42[лист!ячейка]': ['посмотреть ячейку (для отладки, кнопки не активны', False],
        'moveto[лист!ячейка]' : ['перейти к другому уроку', True],
        'levers' : ['немного стихов', False]
    }
    rel_commands = {}
    pass
