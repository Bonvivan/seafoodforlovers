import telebot
from telebot import apihelper
from telebot import types
import re
import calendar
from   datetime import datetime, date
import datetime as dt
import itertools
import commands
import textProcess as tp
import threading

import googleSheetTest
import json

'''
@bot.channel_post_handler(content_types=["text", "audio", "photo", "video"])
def greeting(message):
    print("!!!!!!!!!")
    print(message)
    bot.send_message(message.from_user.id, 'Привет, добро пожаловать в наш канал!')
'''


class SurveyBot(telebot.TeleBot):
    data_table = None

    user_cell_position  = {}
    user_chat_id        = {}
    user_command        = {}
    teacher_command     = {}

    bot_state           = {}
    schedule            = {}

    now_processing_id = -1

    PRICE_1 = types.LabeledPrice(label=  "3 месяца обучения", amount=1010 * 100)  # в копейках (руб)
    PRICE_2 = types.LabeledPrice(label= "6 месяцев обучения", amount=92000 * 100)  # в копейках (руб)
    PRICE_3 = types.LabeledPrice(label="12 месяцев обучения", amount=179000 * 100)  # в копейках (руб)
    PAYMENT_TOCKEN = ''


    def __init__(self, bot_token, data_table, pay_tocken):
        super().__init__(bot_token)
        self.bot_state_filepath = 'resources\\' + self.user.username + '.json'
        try:
            state_f = open(self.bot_state_filepath, 'r')
            self.bot_state = json.load(state_f)
        except:
            pass

        self.PAYMENT_TOCKEN = pay_tocken

        self.now_processing_id = -1

        self.data_dstn   = {}
        self.schedule    = {}

        self.data_table = data_table
        self.survey_dict = self.data_table.getPupilStruct(sheetName='pupils')
        self.__invert_datasource_link(self.survey_dict)

        threading.Timer(30.0, self.checkSchedule).start()

        self.init_state()

        @self.message_handler(commands=['trial_chat'])
        def try_command(message):
            uid = message.from_user.id
            self.create_chat_invite_link(-4070680015)
            pass


        @self.message_handler(commands=['trial_1'])
        def try_command(message):
            print('try_command')
            self.send_invoice(message.chat.id,
                           title="3 месяца обучения",
                           description="Любой уровень на ваш выбор. Идеально подойдет тем, кому нужно говорить уже вчера, нет системных знаний и хочется почувствовать прогресс в обучении.",
                           provider_token=self.PAYMENT_TOCKEN,
                           currency="rub",
                           is_flexible=False,
                           prices=[self.PRICE_1],
                           start_parameter="one-month-subscription",
                           invoice_payload="test-invoice-payload",
                           photo_url='https://dl.dropboxusercontent.com/scl/fi/g9zlqj85vit74ymrjpsg0/logo_langusto.png?rlkey=2qd8i57bmz6tt20x0c2fzyeml&dl=0',
                           photo_height=478,
                           photo_width=512,
                           photo_size=512)

            pass

        @self.message_handler(commands=['trial_2'])
        def try_command(message):
            print('try_command')
            self.send_invoice(message.chat.id,
                              title="6 месяцев обучения",
                              description="Любые два уровня на ваш выбор. Можно начать с нуля или продолжить обучение. Мощное погружение в язык со значительными результатами.",
                              provider_token=self.PAYMENT_TOCKEN,
                              currency="rub",
                              is_flexible=False,
                              prices=[self.PRICE_2],
                              start_parameter="one-month-subscription",
                              invoice_payload="test-invoice-payload",
                              photo_url='https://dl.dropboxusercontent.com/scl/fi/g9zlqj85vit74ymrjpsg0/logo_langusto.png?rlkey=2qd8i57bmz6tt20x0c2fzyeml&dl=0',
                              photo_height=478,
                              photo_width=512,
                              photo_size=512)

            pass

        @self.message_handler(commands=['trial_3'])
        def try_command(message):
            print('try_command')
            self.send_invoice(message.chat.id,
                              title="12 месев обучения",
                              description="Полный курс обучения. С нуля и до уверенного владения итальянским. Через год можно покупать билеты и уезжать в Италию!",
                              provider_token=self.PAYMENT_TOCKEN,
                              currency="rub",
                              is_flexible=False,
                              prices=[self.PRICE_3],
                              start_parameter="one-month-subscription",
                              invoice_payload="test-invoice-payload",
                              photo_url='https://dl.dropboxusercontent.com/scl/fi/g9zlqj85vit74ymrjpsg0/logo_langusto.png?rlkey=2qd8i57bmz6tt20x0c2fzyeml&dl=0',
                              photo_height=478,
                              photo_width=512,
                              photo_size=512)

            pass


        # pre checkout  (must be answered in 10 seconds)
        @self.pre_checkout_query_handler(lambda query: True)
        def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
            self.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
            print('Preliminary test')
            

        @self.message_handler(content_types=['successful_payment'])
        def successful_payment(message: types.Message):
            print("SUCCESSFUL PAYMENT:")
            payment_info = message.successful_payment
            print(payment_info)


        @self.message_handler(func=lambda m: tp.MSG_TYPE.compare('//vai_lezioni',m.text)==len('//vai_lezioni')) #TODO: move to commands
        @self.single_user_decorator
        def lesson_command(message):
            print('lesson_command')
            if not ('chefid' in self.bot_state) or int(self.bot_state['chefid']) < 0:
                self.send_message(message.from_user.id, "Не могу создать урок, учитель не активировал опцию, поробуйте позже")
            else:
                if(self.__check_user_info(message.from_user.id)):
                    self.create_lesson_chat(message.from_user)
                elif self.user_chat_id[message.from_user.id]!=-1:
                    chat_id = int(self.user_chat_id[message.from_user.id])
                    link = self.create_chat_invite_link(chat_id).invite_link
                    self.send_message(message.from_user.id, "Вы уже создали чат для урока: " + link)
                else:
                    self.send_message(message.from_user.id, "Вы не закончили опрос.")
            pass

        @self.message_handler(func=lambda m: tp.MSG_TYPE.compare('/savechannel',m.text)==len('/savechannel')) #TODO: move to commads
        @self.single_user_decorator
        def new_chat_event(message):
            print('new_chat_event')
            if message.from_user.id != self.bot_state['chefid']:
                self.send_message(message.from_user.id,
                                  "Только администратор бота может отдавать комманду на создание обучающего чата")

            cmd     = tp.parseCommand(message.text)
            uid     = cmd['args'][0]
            cid     = cmd['args'][1]
            ch_date = cmd['args'][2]
            try:
                cid = -int(cid)
                data_table.setFieldValue(cid, int(uid), 'chat_id'  )
                data_table.setFieldValue(ch_date , int(uid), 'date_start')
                self.user_chat_id[int(uid)]=cid
                self.start_lesson(int(uid), cid, message)
            except Exception as err:
                self.send_message(uid,
                                  "Вас не в базе учеников, вероятно вы не прошли опрос. Наберите /start")
            pass

        @self.message_handler(func=lambda m: tp.MSG_TYPE.compare('/tunnelmsg', m.text) == len('/tunnelmsg')) #TODO: move to commands
        @self.single_user_decorator
        def tunnel_msg(message):
            print('tunnel_msg')
            try:
                cmd = tp.parseCommand(message.text)
                id_u = data_table.getAllPupilColumns(['id','username'])
                _id = id_u[0][id_u[1].index(cmd['args'][0])]
                self.send_message(_id,cmd['args'][1])
            except:
                pass

        @self.message_handler(commands=['imyourchief'])
        def chief_command(message):
            print('chief_command')
            if message.from_user.username=='roro_tmp':
                self.send_message(message.from_user.id, "Your are chief, I was waiting for you!")
                self.bot_state['chefid']   = message.from_user.id
                self.bot_state['chiefname'] = message.from_user.username
            else:
                self.send_message(message.from_user.id, "Your username is wrong, you are not a chief")

            state_f = open(self.bot_state_filepath, 'w')
            json.dump(self.bot_state, state_f)
            state_f.close()

        @self.message_handler(commands=['start'])
        @self.single_user_decorator
        def start_command(message):
            print('start_command')
            user = self.__check_user(message.from_user.id)
            if (user==None):
                self.user_cell_position[message.from_user.id] = 'intro!A1'
            else:
                self.user_cell_position  = {**self.user_cell_position, **user[0]}
                self.user_chat_id = {**self.user_cell_position, **user[1]}
            self.say_hello(message.from_user.id, chat_id=message.chat.id)
        pass

        @self.message_handler(commands=['call'])
        @self.single_user_decorator
        def status_command(message):
            uid = message.from_user.id
            cid = message.chat.id
            if not (uid in self.user_chat_id):
                return None
            if cid!=self.user_chat_id[uid]:
                return None

            link = self.create_chat_invite_link(int(cid)).invite_link
            result = self.send_message(self.bot_state['chefid'], 'ВОПРОС ИЛИ СБОЙ В ЧАТЕ: \n' + link)
            now = datetime.now(dt.UTC)
            self.data_table.setFieldValue(
                str(result.chat.id) + ';' + str(result.message_id) + ';' + str(now.isoformat()), uid, 'extra_call')
            pass

        @self.message_handler(commands=['solved'])
        @self.single_user_decorator
        def status_command(message):
            tid = message.from_user.id
            cid = message.chat.id
            if tid != int(self.bot_state['chefid']):
                self.send_message(cid, 'Запрос на вызов преподавателя снят')

            call_msg = self.data_table.getFieldValue(cid, 'extra_call', key_column='chat_id')
            call_chat_id, call_msg_id, when = call_msg.split(';')
            try:
                self.edit_message_text('Запрос снят', chat_id=int(call_chat_id), message_id=int(call_msg_id))
            except:
                pass
            self.data_table.setFieldValue(None, cid, 'extra_call', key_column='chat_id')

            pass

        @self.message_handler(commands=['delete'])
        @self.single_user_decorator
        def status_command(message):
            uid = message.from_user.id
            cid = message.chat.id
            if (uid in self.user_chat_id) and self.user_chat_id[uid] != -1:
                self.send_message(cid, 'Нельзя удалить пользователя после создания чата.')
                return None
          #  self.data_table.deletePupil(uid)
            pass

        @self.message_handler(commands=['status'])
        @self.single_user_decorator
        def status_command(message):
            uid = message.from_user.id
            cid = message.chat.id
            wait_command = False
            print('status_command')
            user_status = self.data_table.getPupilStatus(uid)
            if (user_status is None):
                self.send_message(cid, 'Вы новый ученик: \n /start чтоб перейти к обучению.')
                return None
            elif int(user_status['chat_id']) == -1:
                self.send_message(cid, "Вы проходите опрос.")
                self.send_message(cid, "\n/start чтоб перейти к последнему вопросу;" +
                                       "\n/delete чтоб удалить свои данные и закончить.")
                return None
            txt = ''
            chat_id = int(self.user_chat_id[uid])
            when = datetime.fromisoformat(user_status['date_start'])
            self.send_message(cid, "Вы начали обучение " + str(when.date()))
            if chat_id != cid:
                link = self.create_chat_invite_link(chat_id).invite_link
                self.send_message(cid, "Ваш чат для обучения: " + link)
            if 'call_message_id' in user_status.keys() and user_status['call_message_id'] != '':
                r1, r2, when = user_status['call_message_id'].split(';')
                when = datetime.fromisoformat(when)
                self.send_message(cid, "Отправлен запрос на проверку " +
                                  str(when.date())  + ' в ' +
                                  str(when.hour)  + ':' + str(when.minute) + 'GMT;')
            else:
                wait_command = True
            if 'extra_call' in user_status.keys() and user_status['extra_call'] != '':
                r1, r2, when = user_status['extra_call'].split(';')
                when = datetime.fromisoformat(when)
                self.send_message(cid, "Отправлено уведомление о вопросе или сбое " +
                                  str(when.date())  + ' в ' +
                                  str(when.hour)  + ':' + str(when.minute) + 'GMT;')
                txt += "\n/solved - снять запрос на вызов преподавателя;"
            if 'delayed_event' in user_status.keys() and user_status['delayed_event'] != '':
                when, cell = user_status['delayed_event'].split(';')
                when = datetime.fromisoformat(when)
                self.send_message(cid, "Следующий урок будет выслан: " +
                                  str(when.date())  + ' в ' +
                                  str(when.hour)  + ':' + str(when.minute) + 'GMT;')
            if 'score' in user_status.keys() and user_status['score'] != '':
                score = int(user_status['score'])
                self.send_message(cid, "На вашем счету: " + str(score) + ' баллов.')

            txt += "\n/start - повторно выслать последнее сообщение и в случае сбоя;"
            txt += "\n/call  - уведомить преподавателя о вопросе или сбое."

            if wait_command:
                c = self.user_command[uid]
                txt += '\n//' + str(c[0]) + ' - ' + commands.COMMANDS.soft_commands[str(c[0])]
            self.send_message(cid, txt)
        pass

        @self.message_handler(content_types=['text'])
        @self.single_user_decorator
        def text_message(message):
            self.read_commands(message)
        pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('tomorrow'))
        @self.single_user_decorator
        def next_step_delay(callback_query: types.CallbackQuery):
            print('next_step_delay')
            self.answer_callback_query(callback_query.id)
            uid = callback_query.from_user.id
            ####
            _today = datetime(datetime.today().year, datetime.today().month, datetime.today().day)
            _tomorrow = _today + dt.timedelta(days=1) + dt.timedelta(hours=4)
            _tomorrow_test  = datetime.now(dt.UTC) + dt.timedelta(minutes=5)
            #TODO: change  tomorrow_test to tomorrow
            event_stamp = str(_tomorrow_test.isoformat()) + ';' + callback_query.data.split(';')[-1]
            self.data_table.setFieldValue(event_stamp, uid, 'delayed_event')
            self.schedule[uid] = {'time': _tomorrow_test,  'cell': callback_query.data.split(';')[-1]}
            txt = 'Следующий урок будет выслан ' + str(_tomorrow.date()) + ' в ' + str(_tomorrow.hour) + ':' + str(_tomorrow.minute) + ' GMT.'
            self.send_message(callback_query.message.chat.id, txt)
            pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('saveuser'))
        @self.single_user_decorator
        def newuser_callback_button(callback_query: types.CallbackQuery):
            print('newuser_callback_button')
            self.answer_callback_query(callback_query.id)
            print(callback_query)
            print('Sending request to save user')
            try:
                pupil_info = self.__create_user(self.survey_dict, callback_query.from_user)  # TODO change to save next state, not current
            except:
                return None

            self.data_table.addPupil(pupil_info)
            callback_query.message.from_user.id = callback_query.from_user.id
            try:
                self.goahead(callback_query.message, *callback_query.data.split(';')[2:])
            except:
                pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('unch'))
        @self.single_user_decorator
        def goback_callback_button(callback_query: types.CallbackQuery):
            print('goback_callback_button')
            try: self.answer_callback_query(callback_query.id)
            except: pass
            callback_query.message.from_user.id = callback_query.from_user.id
            callback_query.message.text = callback_query.data.split(';')[1]
            try:
                self.goahead(callback_query.message, *callback_query.data.split(';')[2:])
            except:
                pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('chng'))
        def goahead_callback_button(callback_query: types.CallbackQuery):
            callback_query.message.from_user.is_bot = False
            goback_callback_button(callback_query)

        '''
        @self.single_user_decorator
        @self.message_handler(func=lambda m: tp.MSG_TYPE.compare('channal_deleted',m.text)==len('/channal_deleted'))
        def deleted_chat_event(message):
            print('deleted_chat_event')
            try:
                cmd = tp.parseCommand(message.text)
                uid = cmd['args'][1]
                self.send_message(uid, 'Чат был удален из-за того, что пользователь не присоеденился вовремя.\n /vai_lezioni чтоб создать новый чат.')
            except:
                pass
            print('Chat was deleted due to outdue joining: ' + message.text)
            pass
        '''

    def single_user_decorator(self, function_to_decorate):
        def wrapper(*args):
            print('Sigle user decorator')
            uid = args[0].from_user.id
            if (self.now_processing_id == uid):
                return None
            else:
                self.now_processing_id = uid
            try:
                res = function_to_decorate(*args)
            except: res = None
            self.now_processing_id = -1
            return res

        return wrapper

    def init_state(self):
        all_pupils = self.data_table.getAllValue('pupils')
        id_index      = all_pupils[0].index('id')
        chat_id_index = all_pupils[0].index('chat_id')
        cell_index    = all_pupils[0].index('status')
        schedule_index = all_pupils[0].index('delayed_event')

        ids          = [ int(row[id_index])      for row in all_pupils[4:]]
        chat_ids     = [ int(row[chat_id_index]) for row in all_pupils[4:]]
        cell_ids     = [ row[cell_index]         for row in all_pupils[4:]]
        schedule     = [ row[schedule_index]     for row in all_pupils[4:]]

        for i in range(len(ids)):
            self.user_cell_position[ids[i]] = cell_ids[i]
            try:
                self.user_chat_id[ids[i]] = int(chat_ids[i])
            except:
                self.user_chat_id[ids[i]] = -1

            try:
                sch_data = schedule[i].split(';')
                self.schedule[ids[i]] = {'time': datetime.fromisoformat(sch_data[0]), 'cell': sch_data[1]}
            except:
                pass

        for uid in ids:
            self.read_from_cell(uid)

    def checkSchedule(self):
        threading.Timer(300.0, self.checkSchedule).start()
        print('checkSchedule')
        for uid in list(self.schedule.keys()):
            evnt = self.schedule[uid]
            if evnt is None:
                continue
            if evnt['time'] <= datetime.now(dt.UTC):
                    self.user_cell_position[uid] = evnt['cell']
                    if uid in self.user_chat_id:
                        chat_id = self.user_chat_id[uid]
                    else:
                        chat_id = uid

                    self.say_hello(uid, chat_id)
                    self.__savestatus(uid, self.user_cell_position[uid])
                    self.cleanSchedule(uid)
        pass

    def cleanSchedule(self, uid):
        self.data_table.setFieldValue(None, uid, 'delayed_event')
        self.schedule.pop(uid)
    def start_lesson(self, uid, chat_id, message):
        print('start_lesson')
        level = self.data_table.getFieldValue(uid, 'level')
        self.user_chat_id[uid] = int(chat_id)
        dptr = self.user_cell_position[uid]
        addr = dptr
        if level == 'A1':
            addr = 'lezione_A1!A1'
        elif level == 'A2':
            addr = 'lezione_A2!A1'
        elif level == 'B1':
            addr = 'lezione_B1!A1'
        elif level == 'B2':
            addr = 'lezione_B2!A1'
        else:
            return None
        message.from_user.id = uid
        message.chat.id      = chat_id
        self.goahead(message, dptr, addr)
        pass

    def user_command_processor(self, message, addr):
        uid = message.from_user.id
        chat_id = message.chat.id
        cmd = self.__extract_command(message.text)
        if message.text[0]!='/':
            if cmd == self.user_command[uid][0]:
                addr[0] = self.user_command.pop(uid)[1]
            return True
        else:
            pass
        # cmd[0]=='/':
        if cmd != self.user_command[uid][0]:
            return False

        addr[0] = self.user_command.pop(uid)[1]
        if cmd == 'le_risposte':
            pass

        if cmd == 'checkme':
            link = self.create_chat_invite_link(int(self.user_chat_id[uid])).invite_link
            result = self.send_message(self.bot_state['chefid'], 'Запрос на проверку урока: \n' + link)
            print(result)
            now = datetime.now(dt.UTC)
            self.data_table.setFieldValue(str(result.chat.id) + ';' + str(result.message_id) + ';' + str(now.isoformat()), uid, 'call_message_id')

        return True

    def teacher_command_processor(self, message, addr):
        tid = message.from_user.id
        chat_id = message.chat.id
        cmd = self.__extract_command(message.text)

        if message.text[0] != '/':
            if cmd == self.teacher_command[tid][0]:
                addr[0] = self.teacher_command.pop(tid)[1]
            return True
        else:
            pass

        # cmd[0]=='/':
        if cmd != self.teacher_command[chat_id][0]:
            return False

        addr[0] = self.teacher_command.pop(chat_id)[1]
        if cmd == 'checked':
            if tid == int(self.bot_state['chefid']):
                call_msg = self.data_table.getFieldValue(chat_id, 'call_message_id', key_column='chat_id')
                call_chat_id, call_msg_id, when = call_msg.split(';')
                print('!!!')
                try: self.edit_message_text('Урок проверен', chat_id=int(call_chat_id), message_id=int(call_msg_id))
                except: pass
                self.data_table.setFieldValue(None, chat_id, 'call_message_id', key_column='chat_id')
                print('!!!')
            else:
                return False

        return True

    def wrong_command_report(self, msg):
        cmd = self.__extract_command(msg.text)
        self.send_message(msg.chat.id, 'Неизвестная команда ' + str(cmd))  # TODO define abstract class MSG sending an apppropriate type of msg (method send())
    def read_commands(self, message):
        uid = message.from_user.id
        chat_id = message.chat.id
        cmd = ''
       # if uid in self.user_cell_position.keys():
       #     addr = [self.user_cell_position[uid]]
       # else:
        addr = [None]

        if chat_id in self.teacher_command.keys():
            if not (self.teacher_command_processor(message, addr)):  # reading of next cell address here
                self.wrong_command_report(message)
               # self.read_from_cell(uid)
                return None

        elif uid in self.user_command:
            if not (self.user_command_processor(message, addr)):  # reading of next cell address here
                self.wrong_command_report(message)
                self.read_from_cell(uid)
                return None

        if addr[0]==None:
            return None

        if uid in self.user_cell_position:
            dptr = self.user_cell_position[uid]
        else:
            pupil_id = self.__find_keys(self.user_chat_id, chat_id)
            if not pupil_id:
                return None
            dptr = self.user_cell_position[pupil_id[0]]

        self.goahead(message, dptr, addr[0])
        pass

    def goahead(self, message, dptr, addr): #processing of an incoming message
        print('goahead')

        uid = message.from_user.id
        chat_id = message.chat.id
        if message.from_user.id == int(self.bot_state['chefid']):
            pupil_id = self.__find_keys(self.user_chat_id, chat_id)
            if not pupil_id:
                pass
            else:
                uid = pupil_id[0]

        cmd = ''
        if not(uid in self.user_cell_position):
            self.user_cell_position[uid] = dptr
        if (not(self.user_cell_position[uid] == dptr)):
            return None

        try:
            self.edit_message_reply_markup(message.chat.id, message_id=message.message_id-(message.from_user.username!=self.user.username), reply_markup='')
        except:
            pass

        #update user status in the chat
        if self.user_cell_position[uid] in self.data_dstn and message.from_user.is_bot == False:
            field_name = self.data_dstn[self.user_cell_position[uid]]
            self.data_table.setFieldValue(tp.cleanMessage(message.text, self.user.username), uid, field_name)
            print('Message to be logged: ' + message.text)

        # update user status in the chat
        self.user_cell_position[uid] = addr # jumping to the next cell in user status
        try:
            self.__savestatus(uid, self.user_cell_position[uid]) #saving status (cell id where the user is)
        except Exception as err:
            print(err)
        self.say_hello(uid, chat_id) # sending a reply (content of the message froma cell)
        pass

    def read_from_cell(self, user_id): #sending of a reply message
        print('read from cell')
        _id = user_id
        uid = user_id
        if _id in self.user_chat_id:
            if self.user_chat_id[_id]!=-1:
                try:
                    _id = int(self.user_chat_id[_id])
                except: pass
        try:
            msg = self.data_table.getValueFromStr(self.user_cell_position[uid])[0][0]
        except Exception as err:
            self.send_message(uid, 'Что-то сломалось(( Когда починят, придет уведомление')
            if uid in self.user_cell_position:
                print('Error in table reading, desired range: ' + self.user_cell_position[uid])
            else:
                print('Key error in table reading: ' + str(uid))
            print(err)
            return None

        content = tp.parseMessage(msg)
        self.__createKeyFromContent(uid, _id, content['buttons'])
        pass

    def say_hello(self, user_id, chat_id=None): #sending of a reply message
        print('sayhello')

        if chat_id is None:
            chat_id = user_id
        uid = user_id
        _id = chat_id

        '''
        if _id in self.user_chat_id.keys():
            if self.user_chat_id[_id]!=-1:
                try:
                    _id = int(self.user_chat_id[_id])
                except: pass
        else:
            pupil_id = self.__find_keys(self.user_chat_id, chat_id)
            if not pupil_id:
                pass
            else:
                uid = pupil_id[0]
        '''

        markup = types.InlineKeyboardMarkup(row_width=2)#, one_time_keyboard=True, resize_keyboard=True)
        question_text = ['']
        try:
            msg = self.data_table.getValueFromStr(self.user_cell_position[uid])[0][0]
        except Exception as err:
            self.send_message(_id, 'Что-то сломалось(( Для перезапуска наребирте /start', reply_markup=markup)
            if _id in self.user_cell_position:
                print('Error in table reading, desired range: ' + self.user_cell_position[_id])
            else:
                print('Key error in table reading: ' + str(_id))
            print(err)
            return None

        past_answer=''
        if(self.user_cell_position[uid] in self.data_dstn):
            fieldname = self.data_dstn[self.user_cell_position[uid]]
            content = self.data_table.getFieldValue(_id, fieldname)
            if not(content is None):
                past_answer = '\n<i>' + content.strip() + '</i>'

        content = tp.parseMessage(msg, past_answer)
        btns = self.__createKeyFromContent(uid, _id, content['buttons'])
        for i in range(len(btns)):
            if not(btns[i] is None):
                markup.add(btns[i])
                pass

        msgs = content['content']
        for i in range(len(msgs)):
            m = msgs[i]
            mrk = markup if i==len(msgs)-1 else None

            mtype = m[1]
            if m[0]=='':
                continue
            print('Sending part of message')
            try:
                if mtype==tp.MSG_TYPE.text:
                    self.send_message(_id, m[0], reply_markup=mrk, parse_mode='html') #TODO define abstract class MSG sending an apppropriate type of msg (method send())
                elif mtype==tp.MSG_TYPE.image:
                    self.send_photo(_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.video:
                    self.send_video(_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.audio:
                    self.send_audio(_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.audionote:
                    self.send_voice(_id, m[0])
            except:
                self.send_message(_id, m[0], reply_markup=mrk)
        pass

    def create_lesson_chat(self, pupil_user):
        participants = [self.user.username, self.bot_state['chiefname'], pupil_user.username]
        txt = '/create_a_channal;'+';'.join(participants)
        self.send_message(self.bot_state['chefid'], txt)
        pass

    def run(self):
        self.polling(none_stop=True, interval=0)

    def __find_keys(self, d, value):
        return [key for key, x in d.items() if str(x) == str(value)]
    def __extract_command(self, msg):
        z = re.match('//([a-zA-Z0-9-_]+)@?\.*', msg)
        if not(z):
            return ''
        return z.groups()[0]
        pass

    def __savestatus(self, id, status):
        pupils = self.data_table.getAllPupilColumns(['id'])[0]
        if str(id) in pupils:
            self.data_table.setFieldValue(status, id, 'status', sheetName='pupils')
            self.data_table.setFieldValue(str(datetime.now(dt.UTC).isoformat()), id, 'last_activity_date', sheetName='pupils')

    def __createKeyFromContent(self, id, chat_id, content):

        self.user_command   .pop(id     , None)
        self.teacher_command.pop(chat_id, None)

        btns = []
        user_status = self.user_cell_position[id]
        open_input_flad = 0
        for b in content:
            title, addr, sp = b
            title = title.strip()
            #if sp == '/input' and open_input_flad == 0:
            #    btns.append(None)
            #    open_input_flad += 1
            #    continue
            if sp == '/saveuser':
                callback = 'saveuser;' + '' + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
                continue
            if sp == '/edit':
                if(self.user_cell_position[id] in self.data_dstn):
                    fieldname = self.data_dstn[self.user_cell_position[id]]
                    content   = self.data_table.getFieldValue(id, fieldname)
                    if content is None:
                        pass
                    else:
                        callback = 'unch;' + 'Ок' + ';' + user_status + ';' + addr #TODO consider if possible to use "user status" token and take out the method to textProcessor since no id and status is needed
                        btns.append(types.InlineKeyboardButton(title, switch_inline_query_current_chat=content))
                        btns.append(types.InlineKeyboardButton('Ок', callback_data=callback))
                    pass
                pass
            if sp == '/delete_me':
                pass

            if sp == '/ucommand':
                cmd = self.__extract_command(title)
                btns.append(None)
                self.user_command[id] = [cmd, addr]
            if sp == '/tcommand':
                cmd = self.__extract_command(title)
                btns.append(None)
                self.teacher_command[chat_id] = [cmd, addr]
            if sp == '/tomorrow':
                callback = 'tomorrow;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
            if sp == '/back':
                callback = 'unch;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
            if sp is None or sp == '':
                callback = 'chng;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
        return btns

    def __check_user(self, id):
        pupils = self.data_table.getAllPupilColumns(['id','status','chat_id'])
        id = str(id)
        if id in str(pupils[0]):
            j = pupils[0].index(id)
            return {int(id): pupils[1][j]},{int(id): int(pupils[2][j])}
        else:
            return None

    def __check_user_info(self, id): #TODO Add checking of fullness of the user info
        record = self.data_table.getAllFieldValue(id)
        for h, u in zip(record[2],record[-1]):
            if int(h)==1:
                if u=='':
                    return False
        ind = record[0].index('chat_id')
        try:
            if int(record[-1][ind]) != -1:
                self.user_chat_id[id] = int(record[-1][ind])
                return False
        except: pass
        return True

    def __create_user(self, pupil_dict, user_dscr):
        user_dict = {}
        user_tmp_dict = eval(str(user_dscr))
        for k in pupil_dict.keys():
            if k in user_tmp_dict.keys():
                user_dict[k] = user_tmp_dict[k]
            else:
                user_dict[k] = ''
            pass
        user_dict['status' ] = self.user_cell_position[user_dict['id']]
        user_dict['chat_id'] = -1
        return user_dict

    def __invert_datasource_link(self, data_structure):
        for k in data_structure.keys():
            f = data_structure[k]
            result = re.match("(\w+![AZ]\d)", f['source'])
            if not(result is None):
                self.data_dstn[result.group(1)] = k
            pass

#bot.send_poll(message.chat.id, 'вопрос', options=['1', '2', '3'])

state_f = open('resources/tokens.json', 'r')
tokens = json.load(state_f)
state_f.close()


logger = telebot.logger

print("Starting the program")

survey_table = googleSheetTest.GoogleTableReader(tokens['gsheet'])
survey_bot = SurveyBot(tokens['bot_token'], survey_table, tokens['p_tocken']) #new testing bot with working shop

survey_bot.run()

