import telebot
from telebot import apihelper
from telebot import types
import re
import calendar
from datetime import datetime, date
import datetime as dt
import time
import itertools
import commands
import textProcess as tp
import threading
from random import randrange, uniform
import sys
import os

import googleSheetTest
import json

# -------------------------------------------------------#
# ----created by Andrey Svitenkov, Undresaid, 10.2023----#
# -------------------------------------------------------#

'''
@bot.channel_post_handler(content_types=["text", "audio", "photo", "video"])
def greeting(message):
    print("!!!!!!!!!")
    print(message)
    bot.send_message(message.from_user.id, 'Привет, добро пожаловать в наш канал!')
'''


class SurveyBot(telebot.TeleBot):
    data_table = None

    user_cell_position = {}
    user_chat_id = {}
    user_command = {}
    conditions = {}
    teacher_command = {}
    tmp_msg_await = {}
    tmp_msg_kill = {}

    bot_state = {}
    schedule = {}

    now_processing_id = -1

    PRICE_1 = types.LabeledPrice(label="3 месяца обучения", amount=49000 * 100)  # в копейках (руб)
    PRICE_2 = types.LabeledPrice(label="6 месяцев обучения", amount=92000 * 100)  # в копейках (руб)
    PRICE_3 = types.LabeledPrice(label="12 месяцев обучения", amount=179000 * 100)  # в копейках (руб)
    PRICE_4 = types.LabeledPrice(label="1 неделя обучения", amount=3900 * 100)  # в копейках (руб)
    PAYMENT_TOCKEN = ''

    initialisation = False

    def __init__(self, bot_token, data_table, pay_tocken):
        super().__init__(bot_token, threaded=False)
        self.initialisation = True
        self.bot_state_filepath = 'resources\\' + self.user.username + '.json'
        try:
            state_f = open(self.bot_state_filepath, 'r')
            self.bot_state = json.load(state_f)
        except:
            pass

        self.PAYMENT_TOCKEN = pay_tocken

        self.now_processing_id = -1

        self.data_dstn = {}
        self.schedule = {}
        self.user_frozen = {}

        self.data_table = data_table

        self.survey_dict = self.data_table.getPupilStruct(sheetName='pupils')
        self.__invert_datasource_link(self.survey_dict)

        threading.Timer(30.0, self.checkSchedule).start()

        self.init_state()

        self.initialisation = False

        # pre checkout  (must be answered in 10 seconds)
        @self.pre_checkout_query_handler(lambda query: True)
        def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
            self.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
            print('Preliminary test')

        @self.message_handler(content_types=['successful_payment'])
        def successful_payment(message: types.Message):
            print("SUCCESSFUL PAYMENT:")
            payment_info = message.successful_payment
            cid = self.user_chat_id[message.from_user.id]
            try:
                link = self.create_chat_invite_link(int(cid)).invite_link
                self.send_message(self.bot_state['chiefid'], '!!!ОПЛАТА В ЧАТЕ, ГУЛЯЙ РВАНИНА!!!: \n' + link)
            except:
                self.send_message(self.bot_state['chiefid'],
                                  '!!!' + str(message.from_user.username) + ' ОПЛАТИЛ КУРС, ПРОВЕРЬ ТАБЛИЦУ!!!: \n')
            uid = message.from_user.id
            if message.successful_payment.invoice_payload == 'mounth3':
                self.data_table.setFieldValues(uid, ['0', str(message.successful_payment),
                                                     str(datetime.utcnow().isoformat()), 90, 60, 0],
                                               ['score', 'payment_info', 'payment_date', 'period', 'lesson_num',
                                                'curr_lesson'])
            if message.successful_payment.invoice_payload == 'mounth6':
                self.data_table.setFieldValues(uid, ['0', str(message.successful_payment),
                                                     str(datetime.utcnow().isoformat()), 180, 120, 0],
                                               ['score', 'payment_info', 'payment_date', 'period', 'lesson_num',
                                                'curr_lesson'])
            if message.successful_payment.invoice_payload == 'mounth12':
                self.data_table.setFieldValues(uid, ['0', str(message.successful_payment),
                                                     str(datetime.utcnow().isoformat()), 360, 240, 0],
                                               ['score', 'payment_info', 'payment_date', 'period', 'lesson_num',
                                                'curr_lesson'])
            if message.successful_payment.invoice_payload == 'week':
                self.data_table.setFieldValues(uid, ['0', str(message.successful_payment),
                                                     str(datetime.utcnow().isoformat()), 8, 4, 0],
                                               ['score', 'payment_info', 'payment_date', 'period', 'lesson_num',
                                                'curr_lesson'])
            # self.user_cell_position[uid] = 'teacher!A6'
            self.__savestatus(uid, self.user_cell_position[uid])
            self.say_hello(uid, cid)
            print(payment_info)

        @self.message_handler(func=lambda m: tp.MSG_TYPE.compare('/cheat42', m.text) == len('/cheat42'))
        @self.single_user_decorator
        def chat_command(message):
            print('cheat_command')
            if not (message.from_user.id in self.bot_state['chiefid']):
                return None
            cell = message.text.split(';')[-1]
            self.show_cell(message.chat.id, cell)

        @self.message_handler(func=lambda m: tp.MSG_TYPE.compare('/moveto', m.text) == len('/moveto'))
        @self.single_user_decorator
        def moveto_command(message):
            print('moveto_command')
            if not (message.from_user.id in self.bot_state['chiefid']):
                return None
            cid = message.chat.id
            cell = message.text.split(';')[-1]
            self.user_cell_position[message.from_user.id] = cell
            uid = self.__find_keys(self.user_chat_id, cid)
            self.say_hello(uid, cid)

        @self.message_handler(
            func=lambda m: tp.MSG_TYPE.compare('/savechannel', m.text) == len('/savechannel'))  # TODO: move to commads

        @self.single_user_decorator
        def new_chat_event(message):
            print('new_chat_event')
            if not (message.from_user.id in self.bot_state['chiefid']):
                self.send_message(message.from_user.id,
                                  "Только администратор бота может отдавать комманду на создание обучающего чата")
                return None

            cmd = tp.parseCommand(message.text)
            uid = cmd['args'][0]
            cid = cmd['args'][1]
            ch_date = cmd['args'][2]
            try:
                uid = int(uid)
                cid = int(cid)
            except Exception as err:
                print('Wrong chat id: not a number ' + str(err))

            if uid in self.bot_state['chiefid']:
                return None

            if not (int(uid) in self.user_chat_id.keys()):
                self.kick_chat_member(chat_id=cid, user_id=uid, until_date=None)
                print('Попытка добавить неизвестного пользователя + ' + str(uid) + ' to ' + str(cid))
                return None
            if cid in self.user_chat_id.values():
                self.kick_chat_member(chat_id=cid, user_id=uid, until_date=None)
                print('Попытка добавить лишнего пользователя + ' + str(uid) + ' to ' + str(cid))
                return None

            try:
                data_table.setFieldValues(int(uid), [cid, ch_date], ['chat_id', 'date_start'])
                self.user_chat_id[int(uid)] = cid
                self.start_lesson(int(uid), cid, message)
            except Exception as err:
                self.data_table.critical_flag = False
                self.send_message(uid,
                                  "Что-то пошло не так. Наберите /call чтоб сообщить об этом преподавателю")
                print('new_chat_event: ' + str(err))
            pass

        @self.message_handler(
            func=lambda m: tp.MSG_TYPE.compare('/tunnelmsg', m.text) == len('/tunnelmsg'))  # TODO: move to commands
        #    @self.single_user_decorator
        def tunnel_msg(message):
            print('tunnel_msg')
            try:
                cmd = tp.parseCommand(message.text)
                print('Parsing')
                id_u = data_table.getAllPupilColumns(['id', 'username'])
                print('User id')
                _id = id_u[0][id_u[1].index(cmd['args'][0])]
                print('Chat id')
                self.send_message(_id, cmd['args'][1])
                print('MSG to user')
            except Exception as err:
                print('Err in tunnel_msg: ' + str(err))
                pass

        @self.message_handler(commands=['imyourchief'])
        def chief_command(message):
            print('chief_command')
            if message.from_user.username == 'roro_tmp' or message.from_user.username == 'fille_soleil' or message.from_user.username == 'photo_mascha':
                self.send_message(message.from_user.id, "Да, моя госпожа!!")
                if not (message.from_user.id in self.bot_state):
                    if not (message.from_user.id in self.bot_state['chiefid']):
                        self.bot_state['chiefid'].append(message.from_user.id)
                        self.bot_state['chiefname'].append(message.from_user.username)
            else:
                self.send_message(message.from_user.id, "Your username is wrong, you are not a chief")

            state_f = open(self.bot_state_filepath, 'w')
            json.dump(self.bot_state, state_f)
            state_f.close()

        @self.message_handler(commands=['start'])
        @self.single_user_decorator
        def start_command(message):
            print('start_command')
            uid = message.from_user.id
            cid = message.chat.id
            if 'chiefid' in self.bot_state and uid in self.bot_state['chiefid']:
                self.send_message(cid, 'Вы учитель.')
                if cid == uid:
                    self.send_message(cid, 'Нельзя быть учителем и учеником одновременно.')
                return None

            if uid in self.user_chat_id:
                if self.user_chat_id[uid] != -1 and self.user_chat_id[uid] != cid:
                    try:
                        link = self.create_chat_invite_link(int(cid)).invite_link
                        self.send_message(cid, 'Перейдите в обучающий чат: ' + link)
                        return None
                    except:
                        self.user_chat_id[uid] = -1
                        self.data_table.setFieldValue(uid, -1, 'chat_id')
                        pass

            self.data_table.refresh()
            user = self.__check_user(message.from_user.id)
            if (user == None):
                uid = message.from_user.id
                self.user_cell_position.pop(uid, None)
                self.user_chat_id.pop(uid, None)
                self.user_command[uid] = []  # .pop(uid, None)
                self.teacher_command[uid] = []
                self.schedule.pop(uid, None)
                self.user_cell_position[message.from_user.id] = 'intro!A1'
            else:
                self.init_state(message.from_user.id)
                self.user_cell_position = {**self.user_cell_position, **user[0]}
                self.user_chat_id = {**self.user_chat_id, **user[1]}
            if message.from_user.id in self.user_chat_id:
                self.say_hello(message.from_user.id, chat_id=self.user_chat_id[message.from_user.id])
            else:
                self.say_hello(message.from_user.id, chat_id=-1)

        pass

        @self.message_handler(commands=['nonfunziona'])
        @self.single_user_decorator
        def call_command(message):
            uid = message.from_user.id
            cid = message.chat.id
            if not (uid in self.user_chat_id):
                return None
            if cid != self.user_chat_id[uid]:
                return None

            link = self.create_chat_invite_link(int(cid)).invite_link
            result = self.send_message(self.bot_state['chiefid'], 'СБОЙ В ЧАТЕ: \n' + link)

            now = datetime.utcnow()
            all_chat_ids = ','.join([str(res.chat.id) for res in result])
            all_msg_ids = ','.join([str(res.message_id) for res in result])

            self.data_table.setFieldValue(uid,
                                          str(all_chat_ids) + ';' + str(all_msg_ids) + ';' + str(
                                              now.isoformat()), 'tech_call')

            result = self.send_message(cid, 'Запрос отправлен!')
            pass

        @self.message_handler(commands=['aiuto'])
        @self.single_user_decorator
        def call_command(message):
            uid = message.from_user.id
            cid = message.chat.id
            if not (uid in self.user_chat_id):
                return None
            if cid != self.user_chat_id[uid]:
                return None

            link = self.create_chat_invite_link(int(cid)).invite_link
            result = self.send_message(self.bot_state['chiefid'], 'Вопрос в чате: \n' + link)

            now = datetime.utcnow()
            all_chat_ids = ','.join([str(res.chat.id) for res in result])
            all_msg_ids = ','.join([str(res.message_id) for res in result])

            self.data_table.setFieldValue(uid,
                                          str(all_chat_ids) + ';' + str(all_msg_ids) + ';' + str(
                                              now.isoformat()), 'question')

            result = self.send_message(cid, 'Запрос отправлен!')
            pass

        @self.message_handler(commands=['funziona'])
        @self.single_user_decorator
        def solved_command(message):
            tid = message.from_user.id
            cid = message.chat.id

            call_msg = self.data_table.getFieldValue(cid, 'tech_call', key_column='chat_id')
            if call_msg is None:
                self.send_message(cid, "Нет активного запроса, проверьте /status")
            call_chat_id, call_msg_id, when = call_msg.split(';')
            try:
                chat_ids = call_chat_id.split(',')
                msg_ids = call_msg_id.split(',')
                for c_id, m_id in zip(chat_ids, msg_ids):
                    self.edit_message_text('Запрос снят', chat_id=int(c_id), message_id=int(m_id))
            except Exception as err:
                print('edit_message_text(Запрос снят' + str(err))
                pass
            self.data_table.setFieldValue(cid, None, 'tech_call', key_column='chat_id')

            self.send_message(cid, 'Запрос о сбое в чате снят')
            pass

        @self.message_handler(commands=['risolto'])
        @self.single_user_decorator
        def solved_command(message):
            tid = message.from_user.id
            cid = message.chat.id

            call_msg = self.data_table.getFieldValue(cid, 'question', key_column='chat_id')
            if call_msg is None:
                self.send_message(cid, "Нет активного запроса, проверьте /status")
            call_chat_id, call_msg_id, when = call_msg.split(';')
            try:
                chat_ids = call_chat_id.split(',')
                msg_ids = call_msg_id.split(',')
                for c_id, m_id in zip(chat_ids, msg_ids):
                    self.edit_message_text('Запрос снят', chat_id=int(c_id), message_id=int(m_id))
            except Exception as err:
                print('edit_message_text(Запрос снят' + str(err))
                pass
            self.data_table.setFieldValue(cid, None, 'question', key_column='chat_id')

            self.send_message(cid, 'Вопрос в чате снят')
            pass

        @self.message_handler(commands=['delete'])
        @self.single_user_decorator
        def delete_command(message):
            uid = message.from_user.id
            cid = message.chat.id
            if (uid in self.user_chat_id) and self.user_chat_id[uid] != -1:
                self.send_message(cid, 'Нельзя удалить пользователя после создания чата.')
                return None
            #  self.data_table.deletePupil(uid)
            pass

        @self.message_handler(commands=['scongelare'])
        @self.single_user_decorator
        def unfreeze_command(message):
            uid = message.from_user.id
            cid = message.chat.id

            if not (uid in self.bot_state['chiefid']):
                if cid != self.user_chat_id[uid]:
                    return None

            freeze_info = self.data_table.getFieldValue(cid, key_column='chat_id', fieldname='freeze')
            schedule, txt = tp.parseFreeze(freeze_info)

            if schedule[-1][1].strip() == 'nowadays':
                cell_txt = tp.encodeFreeze(schedule, datetime.utcnow().date())
                self.data_table.setFieldValue(cid, cell_txt, 'freeze', key_column='chat_id')
                self.send_message(cid, 'Курс раморожен\n')
            else:
                self.send_message(cid, 'Курс не заморожен\n')
            pass

        @self.message_handler(commands=['congelare'])
        @self.single_user_decorator
        def freeze_command(message):
            uid = message.from_user.id
            cid = message.chat.id

            if not (uid in self.bot_state['chiefid']):
                if cid != self.user_chat_id[uid]:
                    return None

            freeze_info = self.data_table.getFieldValue(cid, key_column='chat_id', fieldname='freeze')
            schedule, txt = tp.parseFreeze(freeze_info)
            if len(schedule) > 0 and schedule[-1][1] == 'nowadays':
                self.send_message(cid, 'Курс уже заморожен\n')
            if uid in self.bot_state['chiefid']:
                txt = tp.encodeFreeze(schedule, datetime.utcnow().date())
                self.data_table.setFieldValue(cid, txt, 'freeze', key_column='chat_id')
                self.send_message(cid, 'Курс заморожен\n')
                schedule, txt = tp.parseFreeze(txt)
                self.send_message(cid, txt)
            else:
                link = self.create_chat_invite_link(int(cid)).invite_link
                for ii in self.bot_state['chiefid']:
                    self.send_message(ii, 'Запрос заморозки чата: \n' + link)
                self.send_message(cid, 'Запрос отправлен!')
            pass

        @self.message_handler(commands=['levers'])
        @self.single_user_decorator
        def levers_command(message):
            cid = message.chat.id
            self.send_message(cid, "Позабыты хлопоты\nОстанoвлен бег\nВкалывают роботы\nСчастлив человек!")

        @self.message_handler(commands=['status'])
        @self.single_user_decorator
        def status_command(message):
            print('status_command')
            uid = message.from_user.id
            cid = message.chat.id

            self.send_chat_action(cid, 'typing')

            teacher = False

            hard_commands = {}

            if 'chiefid' in self.bot_state and uid in self.bot_state['chiefid']:
                self.send_message(cid, 'Вы учитель. Статус ученика:')
                uid = self.__find_keys(self.user_chat_id, cid)[0]
                commands_guru = commands.cmdGuru(commands.TCOMMANDS)
                teacher = True
            else:
                commands_guru = commands.cmdGuru(commands.UCOMMANDS)

            user_status = self.data_table.getPupilStatus(uid)
            if (user_status is None):
                self.send_message(cid, 'Вы новый ученик: \n /start чтоб перейти к обучению.')
                return None

            elif int(user_status['chat_id']) == -1:
                self.send_message(cid, "Вы проходите опрос.")
                self.send_message(cid, "\n/start чтоб перейти к последнему вопросу;")
                return None

            txt = ''
            chat_id = int(self.user_chat_id[uid])
            if cid != chat_id:
                try:
                    link = self.create_chat_invite_link(int(cid)).invite_link
                    self.send_message(cid, "Перейдите в обучающий чат: " + link)
                except:
                    pass
            when = datetime.fromisoformat(user_status['date_start'])
            txt += "Начало обучения " + str(when.date())
            if 'curr_lesson' in user_status.keys() and user_status['curr_lesson'] != '':
                curr_lesson = int(user_status['curr_lesson'])
                txt += '\n<b>Текущий урок: ' + str(curr_lesson) + '</b>'
            self.send_message(cid, txt, parse_mode='html')
            txt = ''
            if chat_id != cid:
                link = self.create_chat_invite_link(chat_id).invite_link
                self.send_message(cid, "Ваш чат для обучения: " + link)
                return None
            if 'call_message_id' in user_status.keys() and user_status['call_message_id'] != '':
                r1, r2, when = user_status['call_message_id'].split(';')
                when = datetime.fromisoformat(when)
                self.send_message(cid, "Отправлен запрос на проверку " +
                                  str(when.date()) + ' в ' +
                                  str(when.hour) + ':' + str(when.minute) + 'GMT;')

            if 'tech_call' in user_status.keys() and user_status['tech_call'] != '':
                r1, r2, when = user_status['tech_call'].split(';')
                when = datetime.fromisoformat(when)
                self.send_message(cid, "Отправлено уведомление о сбое " +
                                  str(when.date()) + ' в ' +
                                  str(when.hour) + ':' + str(when.minute) + 'GMT;')
                commands_guru.setMask('nonfunziona', False)
                commands_guru.setMask('funziona', True)
                # txt += "\n/funziona - снять запрос на вызов преподавателя;\n"

            if 'question' in user_status.keys() and user_status['question'] != '':
                r1, r2, when = user_status['question'].split(';')
                when = datetime.fromisoformat(when)
                self.send_message(cid, "Отправлено уведомление о вопросе " +
                                  str(when.date()) + ' в ' +
                                  str(when.hour) + ':' + str(when.minute) + 'GMT;')
                commands_guru.setMask('aiuto', False)
                commands_guru.setMask('risolto', True)
                # txt += "\n/risolto - снять запрос на вызов преподавателя;\n"

            if 'delayed_event' in user_status.keys() and user_status['delayed_event'] != '':
                when, cell = user_status['delayed_event'].split(';')
                when = datetime.fromisoformat(when)
                self.send_message(cid, "Следующий урок будет выслан: " +
                                  str(when.date()) + ' в ' +
                                  str(when.hour) + ':' + str(when.minute) + 'GMT;')
            if 'score' in user_status.keys() and user_status['score'] != '':
                score = int(user_status['score'])
                self.send_message(cid, "На вашем счету: " + str(score) + ' баллов.')

            if 'payment_date' in user_status.keys() and user_status['payment_date'] != '':
                when = datetime.fromisoformat(user_status['payment_date'])
                period = int(user_status['period'])
                l_num = int(user_status['lesson_num'])
                self.send_message(cid, 'Оплата произведена: ' +
                                  str(when.date()) + '\nВы оплатили курс на ' + str(period) + ' дней, ' + str(
                    l_num) + ' уроков.')
                rest = (datetime.utcnow().date() - when.date()).days
                schedule, txt_sc = tp.parseFreeze(user_status['freeze'])
                for s in schedule:
                    rest += s[2]

                txt += 'История заморозок курса: \n' + txt_sc
                if len(schedule) > 0:
                    if schedule[-1][1] == 'nowadays':
                        txt += "<b>Сейчас курс заморожен с " + str(schedule[-1][0]) + '</b>'
                        commands_guru.setMask('congelare', False)

                txt += "\nДо конца курса осталось " + str(period - rest) + ' дней;\n'
                txt += "Можно получить уроков <b>вне очереди: " + str(
                    3 - int(user_status['lessons_at_once'])) + '</b>\n'
            else:
                commands_guru.setMask('congelare', False)
                commands_guru.setMask('scongelare', False)

            if not (self.user_frozen[uid]):
                if uid in self.user_command:
                    for c in self.user_command[uid]:
                        try:
                            txt += '\n//' + str(c[0]) + ' - ' + commands.UCOMMANDS.soft_commands[str(c[0])]
                        except Exception as e:
                            print('Error in status_command: ' + str(e))

            if (teacher):
                txt += '\nКомманды учителя:'
                if cid in self.teacher_command:
                    for c in self.teacher_command[cid]:
                        try:
                            txt += '\n//' + str(c[0]) + ' - ' + commands.TCOMMANDS.soft_commands[str(c[0])]
                        except Exception as e:
                            print('Error in status_command: ' + str(e))

            h_commands = commands_guru.getHardCommands()
            for cmd in h_commands:
                txt += '\n/' + cmd + ' ' + h_commands[cmd] + ';'
            txt = txt[:-1] + '.'

            self.send_message(cid, txt, parse_mode='html')

        pass

        @self.message_handler(content_types=['text'])
        @self.single_user_decorator
        def text_message(message):
            self.read_commands(message)

        pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('pay'))
        @self.single_user_decorator
        def pay_hendler(callback_query: types.CallbackQuery):
            self.answer_callback_query(callback_query.id)
            msg = callback_query.data
            cmd = tp.parseCommand(msg)
            dptr = cmd['args'][0]
            addr = cmd['args'][1]
            subscr_id = cmd['args'][2]
            self.pay_command(callback_query.message.chat.id, dptr, addr, int(subscr_id))
            try:
                self.edit_message_reply_markup(callback_query.message.chat.id,
                                               message_id=callback_query.message.message_id - (
                                                       callback_query.message.from_user.username != self.user.username),
                                               reply_markup='')
            except:
                pass
            pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('to_lsn'))
        @self.single_user_decorator
        def lesson_command(callback_query: types.CallbackQuery):
            message = callback_query.message
            print('lesson_command')
            self.send_chat_action(message.from_user.id, 'typing')
            self.answer_callback_query(callback_query.id)
            if not ('chiefid' in self.bot_state) or len(self.bot_state['chiefid']) == 0:
                self.send_message(message.from_user.id,
                                  "Не могу создать урок, учитель не активировал опцию, поробуйте позже")
            else:
                if (self.__check_user_info(callback_query.from_user.id)):
                    self.create_lesson_chat(callback_query.from_user)
                elif self.user_chat_id[callback_query.from_user.id] != -1:
                    chat_id = int(self.user_chat_id[callback_query.from_user.id])
                    link = self.create_chat_invite_link(chat_id).invite_link
                    self.send_message(callback_query.from_user.id, "Вы уже создали чат для урока: " + link)
                else:
                    self.send_message(callback_query.from_user.id,
                                      "Похоже вы не закончили опрос, наберите /start для продолжения")

            try:
                self.edit_message_reply_markup(callback_query.message.chat.id,
                                               message_id=callback_query.message.message_id, reply_markup='')
            except:
                pass

            pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('tomorrow'))
        @self.single_user_decorator
        def next_step_delay(callback_query: types.CallbackQuery):
            print('next_step_delay')
            self.answer_callback_query(callback_query.id)
            cid = callback_query.message.chat.id
            uid = self.__find_keys(self.user_chat_id, cid)[0]

            if not (self.check_paymant(uid)):
                return None

            _today = datetime(datetime.today().year, datetime.today().month, datetime.today().day)
            rand_m = randrange(0, 30)
            _tomorrow = _today + dt.timedelta(days=1) + dt.timedelta(hours=4) + dt.timedelta(minutes=rand_m)
            _tomorrow_test = datetime.utcnow() + dt.timedelta(minutes=1)
            # _tomorrow_test = _tomorrow #TODO comment here for debug
            event_stamp = str(_tomorrow_test.isoformat()) + ';' + callback_query.data.split(';')[-1]
            self.data_table.setFieldValues(uid, [event_stamp, 0], ['delayed_event', 'lessons_at_once'])
            self.schedule[uid] = {'time': _tomorrow_test, 'cell': callback_query.data.split(';')[-1]}
            txt = '🤖 Следующий урок будет выслан ' + str(_tomorrow.date()) + ' в ' + str(_tomorrow.hour) + ':' + str(
                _tomorrow.minute) + ' GMT.'

            self.send_message(callback_query.message.chat.id, txt)
            try:
                self.edit_message_reply_markup(callback_query.message.chat.id,
                                               message_id=callback_query.message.message_id, reply_markup='')
            except:
                pass
            pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('saveuser'))
        @self.single_user_decorator
        def newuser_callback_button(callback_query: types.CallbackQuery):
            print('newuser_callback_button')
            self.answer_callback_query(callback_query.id)
            print(callback_query)
            print('Sending request to save user')
            uid = callback_query.message.from_user.id
            if (callback_query.message.from_user.username == ''):
                self.send_message(callback_query.message.chat.id,
                                  'У вас не задано имя пользователя в Telegram. Пожалуйста задайте имя пользователя, потом наберите /start, чтоб продолжить\n')
                return None
            try:
                pupil_info = self.__create_user(self.survey_dict,
                                                callback_query.from_user)  # TODO change to save next state, not current
            except Exception as err:
                self.data_table.critical_flag = False
                print("__create_user: " + str(err))
                return None

            self.data_table.addPupil(pupil_info)
            callback_query.message.from_user.id = callback_query.from_user.id
            try:
                self.goahead(callback_query.message, *callback_query.data.split(';')[2:])
            except Exception as err:
                print("goahead: " + str(err))
                pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('chk'))
        def check_callback_button(callback_query: types.CallbackQuery):
            print('check_callback_button')
            callback_query.message.from_user.is_bot = False
            try:
                self.answer_callback_query(callback_query.id)
            except:
                pass
            cid = callback_query.message.chat.id
            data = callback_query.data.split(';')
            cell = self.data_dstn[data[2]]
            try:
                self.edit_message_reply_markup(cid, message_id=callback_query.message.message_id, reply_markup='')
            except:
                pass
            self.send_message(cid, '<b>' + data[1] + '</b>', parse_mode='html')
            goback_callback_button(callback_query)
            pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('unch'))
        @self.single_user_decorator
        def goback_callback_button(callback_query: types.CallbackQuery):
            print('goback_callback_button')
            try:
                self.answer_callback_query(callback_query.id)
            except:
                pass
            callback_query.message.from_user.id = callback_query.from_user.id
            callback_query.message.text = callback_query.data.split(';')[1]
            try:
                self.goahead(callback_query.message, *callback_query.data.split(';')[2:])
            except Exception as err:
                print('self.goahead(callback_query.message, *callback_query.data.split... ' + str(err))
                pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('chng'))
        def goahead_callback_button(callback_query: types.CallbackQuery):
            callback_query.message.from_user.is_bot = False
            goback_callback_button(callback_query)

        @self.callback_query_handler(func=lambda c: c.data.startswith('tch'))
        def goahead_callback_button(callback_query: types.CallbackQuery):
            callback_query.message.from_user.is_bot = False
            try:
                self.answer_callback_query(callback_query.id)
            except:
                pass
            if callback_query.from_user.id in self.bot_state['chiefid']:
                pupil_id = self.__find_keys(self.user_chat_id, callback_query.message.chat.id)
                if pupil_id != []:
                    self.data_table.setFieldValue(pupil_id[0], callback_query.data.split(';')[1], 'level')
                    goback_callback_button(callback_query)

    def send_message(self, *args, **kwargs):
        chat_ids = args[0]
        print('My send message')
        results = []
        if isinstance(chat_ids, list):
            for cid in chat_ids:
                res = super().send_message(cid, *args[1:], **kwargs)
                results.append(res)
        else:
            results = super().send_message(chat_ids, *args[1:], **kwargs)

        return results

    def single_user_decorator(self, function_to_decorate):
        def wrapper(*args):
            print('Sigle user decorator')
            uid = args[0].from_user.id
            if self.initialisation:
                return None
            if (self.now_processing_id == uid):
                return None
            else:
                self.now_processing_id = uid
            try:
                if type(args[0]) == telebot.types.CallbackQuery:
                    cid = args[0].message.chat.id
                    # self.send_chat_action(cid, 'typing')
                elif type(args[0]) == telebot.types.Message:
                    cid = args[0].chat.id
                    # self.send_chat_action(cid, 'typing')

                res = function_to_decorate(*args)

            except Exception as err:
                print(err)
                res = None
            self.now_processing_id = -1
            return res

        return wrapper

    def show_cell(self, cid, cell):
        print('show cell')
        _id = cid
        msg = self.data_table.getValueFromStr(cell)[0][0]
        content = tp.parseMessage(msg, '')
        msgs = content['content']
        for i in range(len(msgs)):
            m = msgs[i]
            mrk = None

            mtype = m[1]
            if m[0] == '':
                continue
            print('Sending part of message')
            try:
                if mtype == tp.MSG_TYPE.text:
                    self.send_message(_id, m[0], reply_markup=mrk,
                                      parse_mode='html')  # TODO define abstract class MSG sending an apppropriate type of msg (method send())
                elif mtype == tp.MSG_TYPE.image:
                    self.send_photo(_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.video:
                    try:
                        self.send_video(_id, m[0], reply_markup=mrk)
                    except:
                        m[0] = m[0].replace('https://dl.dropboxusercontent.com/', 'https://www.dropbox.com/')
                        self.send_message(_id, m[0])
                elif mtype == tp.MSG_TYPE.audio:
                    self.send_audio(_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.audionote:
                    self.send_voice(_id, m[0])
            except Exception as err:
                print('Err in msg sending: ' + str(err))
                self.send_message(_id, m[0], reply_markup=mrk)

        pass

    def init_state(self, _id=-1):
        print('init_state')
        all_pupils = self.data_table.getAllValue('pupils')
        id_index = all_pupils[0].index('id')
        chat_id_index = all_pupils[0].index('chat_id')
        cell_index = all_pupils[0].index('status')
        schedule_index = all_pupils[0].index('delayed_event')
        frozen_index = all_pupils[0].index('freeze')

        ids = [int(row[id_index]) for row in all_pupils[4:]]
        chat_ids = [int(row[chat_id_index]) for row in all_pupils[4:]]
        cell_ids = [row[cell_index] for row in all_pupils[4:]]
        schedule = [row[schedule_index] for row in all_pupils[4:]]
        frozen = [row[frozen_index] for row in all_pupils[4:]]

        for i in range(len(ids)):
            if ids[i] != _id and _id != -1:
                continue
            self.user_cell_position[ids[i]] = cell_ids[i]
            try:
                self.user_chat_id[ids[i]] = int(chat_ids[i])
            except:
                self.user_chat_id[ids[i]] = -1

            self.user_frozen[ids[i]] = False
            try:
                f_sch = tp.parseFreeze(frozen[i])
                if f_sch[-1][1] == 'nowadays':
                    self.user_frozen[ids[i]] = True
            except:
                self.user_frozen[ids[i]] = False

            try:
                sch_data = schedule[i].split(';')
                if not (sch_data[0] == ''):
                    self.schedule[ids[i]] = {'time': datetime.fromisoformat(sch_data[0]), 'cell': sch_data[1]}
            except Exception as err:
                print('Err in time decoding: init_state:' + str(err))
                pass

        for uid in ids:
            if _id == -1 or uid == _id:
                self.read_from_cell(uid)

    def checkFast(self):
        for ch in self.tmp_msg_kill:
            self.delete_message(chat_id=ch, message_id=self.tmp_msg_kill[ch])
        self.tmp_msg_kill = {}

    pass

    def checkSchedule(self):
        threading.Timer(300.0, self.checkSchedule).start()
        print('checkSchedule')
        for uid in list(self.schedule.keys()):
            if not (uid in self.schedule):
                continue
            evnt = self.schedule[uid]
            if evnt is None:
                continue
            if evnt['time'] <= datetime.utcnow():
                if self.user_frozen[uid]:
                    continue

                self.user_cell_position[uid] = evnt['cell']
                if uid in self.user_chat_id:
                    chat_id = self.user_chat_id[uid]
                else:
                    chat_id = uid

                self.say_hello(uid, chat_id)
                curr_lsn = int(self.data_table.getFieldValue(uid, 'curr_lesson')) + 1
                self.__savestatus(uid, self.user_cell_position[uid], [curr_lsn, 1], ['curr_lesson', 'lessons_at_once'])
                self.cleanSchedule(uid)
        pass

    def cleanSchedule(self, uid):
        self.data_table.setFieldValue(uid, None, 'delayed_event')
        self.schedule.pop(uid)

    def start_lesson(self, uid, chat_id, message):
        print('start_lesson')

        answers = self.data_table.getPupilStatus(uid, sheetName='test_results')
        reference = self.data_table.getPupilStruct(sheetName='test_results', rng='C1:BZ4')

        result_A1 = answers.pop('result_A1', 0)
        result_A2 = answers.pop('result_A2', 0)
        result_B1 = answers.pop('result_B1', 0)
        result_B2 = answers.pop('result_B2', 0)

        mistakes = []
        saitpas  = []

        for a in answers:
            if answers[a].strip() == 'не знаю':
                qst = tp.getMessageText(self.data_table.getValueFromStr(reference[a]['source'])[0][0])[0]
                saitpas.append(qst + '\n' + reference[a]['regex'])
                answers[a] = ''

        for a in answers:
            r = reference.pop(a,'')
            if r=='':
                continue
            if re.match(r['regex'], answers[a]) is None and answers[a] != '':
                qst = tp.getMessageText(self.data_table.getValueFromStr(r['source'])[0][0])[0]
                mistakes.append(
                    qst + '\n' + '<strike>' + answers[a] + '</strike> '  + '\n' + r['regex'])

        txt = '🤖 это наш чат для обучения итальянскому от <b>Langusto!</b>\n'
        if int(result_A1) <= 7:
            self.data_table.setFieldValue(uid, 'A1', 'level')

        self.data_table.setFieldValues(uid, [1, 1], ['curr_lesson', 'lessons_at_once'])
        level = self.data_table.getFieldValue(uid, 'level')
        if level is None or level == '':
            txt += 'Сейчас мы посмотрим ваш тест, и преподаватель предложит, с чего лучше начать!\n'
            txt += 'Результат теста: \n'
            txt += 'A1: ' + result_A1 + '/11\n'
            txt += 'A2: ' + result_A2 + '/13\n'
            txt += 'B1: ' + result_B1 + '/13\n'
            txt += 'B2: ' + result_B2 + '/11\n'
            self.send_message(chat_id, txt, parse_mode='html')
            txt = ''
            if len(mistakes)>0:
                self.send_message(chat_id, '🔶Ошибки:🔶 ', parse_mode='html')
                for m in mistakes:
                    self.send_message(chat_id, m, parse_mode='html')

            if len(saitpas)>0:
                self.send_message(chat_id, '🔷Вопросы без ответов:🔷 ', parse_mode='html')
                for m in saitpas:
                    self.send_message(chat_id, m, parse_mode='html')

            txt += '\nЭти кнопки для преподавателя, исли их нажимать, ничего не произойдет.'
            txt += '\n'
            markup = types.InlineKeyboardMarkup(row_width=2)
            callback = 'tch;' + 'A1' + ';' + self.user_cell_position[uid] + ';' + 'lezione_A1!A1'
            markup.add(types.InlineKeyboardButton('A1', callback_data=callback))
            callback = 'tch;' + 'A2' + ';' + self.user_cell_position[uid] + ';' + 'lezione_A2!A1'
            markup.add(types.InlineKeyboardButton('A2', callback_data=callback))
            callback = 'tch;' + 'B1' + ';' + self.user_cell_position[uid] + ';' + 'lezione_B1!A1'
            markup.add(types.InlineKeyboardButton('B1', callback_data=callback))
            callback = 'tch;' + 'B2' + ';' + self.user_cell_position[uid] + ';' + 'lezione_B2!A1'
            markup.add(types.InlineKeyboardButton('B2', callback_data=callback))
            self.send_message(chat_id, txt, parse_mode='html', reply_markup=markup)
        elif level == 'A1':
            message.from_user.id = uid
            message.chat.id = chat_id

            addr = 'lezione_A1!A1'
            txt += 'Через минуту, здесь появится первый урок...\n'
            txt += 'Да, не через секунду, а именно через МИНУТУ!\n'
            txt += '\n'
            self.send_message(chat_id, txt, parse_mode='html')
            try:
                self.goahead(message, self.user_cell_position[uid], addr)
            except Exception as err:
                print(str(uid) + ': Error in start_lesson: ' + str(err))
                self.user_cell_position[uid] = addr
                self.__savestatus(uid, self.user_cell_position[uid])
            pass

        pass

    def check_paymant(self, uid):
        print('check_paymant')
        stat = self.data_table.getPupilStatus(uid)
        overdue = False
        if 'payment_date' in stat and stat['payment_date'] != '':
            when = datetime.fromisoformat(stat['payment_date'])
            period = int(stat['period'])
            overdue = (period - ((datetime.utcnow().date() - when.date()).days)) <= 0

        if overdue:
            self.send_message(self.user_chat_id[uid], 'Срок прохождения курса истек.')
            self.data_table.setFieldValue(uid, stat['curr_lesson'], 'lesson_num')

        if stat['curr_lesson'] >= stat['lesson_num']:
            self.send_message(self.user_chat_id[uid], 'Для перехода к следующему уроку нужно оплатить курс.')
            self.pay_request(uid, stat['score'])
            return False
        return True

    def pay_request(self, uid, score=0):
        print('pay_request')
        markup = types.InlineKeyboardMarkup(row_width=2)
        user_status = self.user_cell_position[uid]
        cid = self.user_chat_id[uid]
        txt = 'Есть несколько курсов на выбор, цена указана <b>без учета скидки</b>.\n'
        txt += 'У вас на счету <b>' + str(score) + ' баллов</b>\n'
        txt += 'Скидка равна <b>' + str(int(score) * 10) + ' рублей</b>\n'

        titles = ['3 месяца за 49000р;',
                  '6 месяцев за 91000р',
                  '12 месяцев за 179000р',
                  '1 неделя за 3900р']
        for i in range(1, 5):
            callback = 'pay;' + user_status + ';' + user_status + ';' + str(i)
            markup.add((types.InlineKeyboardButton(titles[i - 1], callback_data=callback)))

        self.send_message(cid, txt, reply_markup=markup, parse_mode='html')

        return True

    def conditon_processor(self, message, addr):
        chat_id = message.chat.id
        conditions = []
        if chat_id in self.conditions:
            conditions = self.conditions[chat_id]
        for uc in conditions:
            if (uc[0][:5] == 'check'):
                cnt = uc[0]
                ref = re.findall('check:\?\?\?(.+)\?\?\?', cnt)[0]
                val = self.data_table.getFieldValue(message.from_user.id, ref)
                result = eval(cnt[6:].replace('???' + ref + '???', val).strip())
                if result:
                    return None
                else:
                    addr[0] = uc[1]
            pass
        pass

        for uc in conditions:
            if (uc[0][:3] == 'set'):
                pass
            pass
        pass

    def user_command_processor(self, message, addr):
        uid = message.from_user.id
        chat_id = message.chat.id
        cmd = self.__extract_command(message.text)

        cmd_is_found = False
        for uc in self.user_command[uid]:
            if cmd == uc[0]:
                addr[0] = uc[1]
                cmd_is_found = True
                break

        if not (cmd_is_found) and message.text[0] != '/':
            return True

        if not (cmd_is_found):
            return False

        if cmd == 'le_risposte':
            pass

        if cmd == 'controlla':
            link = self.create_chat_invite_link(int(self.user_chat_id[uid])).invite_link
            result = self.send_message(self.bot_state['chiefid'], 'Запрос на проверку урока: \n' + link)
            print(result)
            now = datetime.utcnow()
            all_chat_ids = ','.join([str(res.chat.id) for res in result])
            all_msg_ids = ','.join([str(res.message_id) for res in result])
            self.data_table.setFieldValue(uid, all_chat_ids + ';' + all_msg_ids + ';' + str(
                now.isoformat()), 'call_message_id')

        if cmd == 'prossima':
            if not (self.check_paymant(uid)):
                addr[0] = None
                return True

            stat = self.data_table.getPupilStatus(uid)
            extra_lesson_num = int(stat['lessons_at_once'])
            curr_lsn = int(stat['curr_lesson'])
            if extra_lesson_num < 3:
                extra_lesson_num += 1
                self.data_table.setFieldValues(uid, [curr_lsn + 1, extra_lesson_num, ''],
                                               ['curr_lesson', 'lessons_at_once', 'delayed_event'])
            else:
                self.send_message(chat_id, 'Нельзы получить больше уроков вне очереди.')
                addr[0] = None
                return True
            self.send_message(chat_id, 'Получено уроков <b>вне очереди: ' + str(extra_lesson_num) + '</b>',
                              parse_mode='html')
        return True

    def teacher_command_processor(self, message, addr):
        tid = message.from_user.id
        chat_id = message.chat.id
        cmd = self.__extract_command(message.text)

        if cmd == '' and message.text[0] != '/':
            return True

        if message.text[0] != '':
            for tc in self.teacher_command[chat_id]:
                if cmd == tc[0]:
                    addr[0] = tc[1]
        else:
            return False

        try:
            if cmd == 'controllato':
                if tid in self.bot_state['chiefid']:
                    call_msg = self.data_table.getFieldValue(chat_id, 'call_message_id', key_column='chat_id')
                    if not (call_msg is None):
                        call_chat_id, call_msg_id, when = call_msg.split(';')
                        chat_ids = call_chat_id.split(',')
                        msg_ids = call_msg_id.split(',')
                        for c_id, m_id in zip(chat_ids, msg_ids):
                            self.edit_message_text('Урок проверен', chat_id=int(c_id), message_id=int(m_id))
                    self.data_table.setFieldValue(chat_id, None, 'call_message_id', key_column='chat_id')
                else:
                    return False

            if cmd == 'le_risposte':
                try:
                    msg = self.data_table.getValueFromStr(addr[0])[0][0]
                    content = tp.parseMessage(msg)
                    msgs = content['content'][0][0]
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(types.InlineKeyboardButton('***', switch_inline_query_current_chat=msgs))
                    result = self.send_message(chat_id, '***', reply_markup=markup)
                    addr[0] = None
                    self.tmp_msg_await[chat_id] = tid
                    self.tmp_msg_kill[chat_id] = result.message_id
                    threading.Timer(3.0, self.checkFast).start()
                    return True
                except:
                    addr[0] = None
                    return True

                pass
        except Exception as e:
            print('Error in teacher_command_processor: ' + str(e))
            return False

        return True

    def wrong_command_report(self, msg):
        cmd = self.__extract_command(msg.text)
        self.send_message(msg.chat.id, 'Неизвестная команда ' + str(
            cmd))  # TODO define abstract class MSG sending an apppropriate type of msg (method send())

    def read_commands(self, message):
        uid = message.from_user.id
        chat_id = message.chat.id
        cmd = ''

        if chat_id in self.tmp_msg_await:
            if self.tmp_msg_await[chat_id] == uid:
                self.delete_message(chat_id=chat_id, message_id=message.message_id)
                self.tmp_msg_await.pop(chat_id)

        addr = [None]

        if uid in self.user_command and len(self.user_command[uid]) > 0:
            if not (self.user_command_processor(message, addr)):  # reading of next cell address here
                self.wrong_command_report(message)
                self.read_from_cell(uid)
                return None

        if chat_id in self.teacher_command and len(self.teacher_command[chat_id]) > 0:
            if not (self.teacher_command_processor(message, addr)):  # reading of next cell address here
                self.wrong_command_report(message)
                self.read_from_cell(uid)
                return None

        if addr[0] == None:
            return None

        self.send_chat_action(chat_id, 'typing')
        if chat_id == uid and self.user_chat_id[uid] != -1:
            self.send_message(chat_id,
                              "Перейдите у групповой чат, чтоб продолжить обучение. \n/status чтоб получить ссылку на чат.")
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

    def goahead(self, message, dptr, addr):  # processing of an incoming message
        print('goahead')
        uid = message.from_user.id
        chat_id = message.chat.id

        addrl = [addr]
        self.conditon_processor(message, addrl)
        addr = addrl[0]

        if 'chiefid' in self.bot_state and message.from_user.id in self.bot_state['chiefid']:
            pupil_id = self.__find_keys(self.user_chat_id, chat_id)
            if not pupil_id:
                pass
            else:
                uid = pupil_id[0]

        self.send_chat_action(chat_id, 'typing')
        cmd = ''
        if not (uid in self.user_cell_position):
            self.user_cell_position[uid] = dptr
        if (not (self.user_cell_position[uid] == dptr)):
            return None

        # update user status in the chat
        if self.user_cell_position[uid] in self.data_dstn and message.from_user.is_bot == False:
            field_name = self.data_dstn[self.user_cell_position[uid]]
            self.data_table.setFieldValue(uid, tp.cleanMessage(message.text, self.user.username), field_name)
            print('Message to be logged: ' + message.text)

        # update user status in the chat
        self.user_cell_position[uid] = addr  # jumping to the next cell in user status
        try:
            self.__savestatus(uid, self.user_cell_position[uid])  # saving status (cell id where the user is)
        except Exception as err:
            print('Errr in __savestatus: ' + str(err))
        self.say_hello(uid, chat_id)  # sending a reply (content of the message froma cell)

        try:
            self.edit_message_reply_markup(message.chat.id, message_id=message.message_id - (
                    message.from_user.username != self.user.username), reply_markup='')
        except:
            pass
        pass

    def read_from_cell(self, user_id):  # sending of a reply message
        print('read from cell')
        _id = user_id
        uid = user_id
        if _id in self.user_chat_id:
            if self.user_chat_id[_id] != -1:
                try:
                    _id = int(self.user_chat_id[_id])
                except:
                    pass
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

        content = tp.parseMessageFast(msg)
        self.__createKeyFromContent(uid, _id, content['buttons'])

    def say_hello(self, user_id, chat_id=-1):  # sending of a reply message
        print('sayhello')

        if chat_id == -1:
            chat_id = user_id
        uid = user_id
        _id = chat_id
        self.send_chat_action(_id, 'typing')

        markup = types.InlineKeyboardMarkup(row_width=2)  # , one_time_keyboard=True, resize_keyboard=True)
        question_text = ['']
        try:
            msg = self.data_table.getValueFromStr(self.user_cell_position[uid])[0][0]
        except Exception as err:
            self.data_table.critical_flag = False
            self.send_message(_id, 'Что-то сломалось(( Для перезапуска наребирте /start', reply_markup=markup)
            if _id in self.user_cell_position:
                print('Error in table reading, desired range: ' + self.user_cell_position[_id])
            else:
                print('Key error in table reading: ' + str(_id))
            print(err)
            return None

        past_answer = ''
        if (self.user_cell_position[uid] in self.data_dstn):
            fieldname = self.data_dstn[self.user_cell_position[uid]]
            content = self.data_table.getFieldValue(_id, fieldname)
            if not (content is None):
                past_answer = '\n<i>' + content.strip() + '</i>'

        content = tp.parseMessage(msg, past_answer)
        btns = self.__createKeyFromContent(uid, _id, content['buttons'])
        for i in range(len(btns)):
            if not (btns[i] is None):
                markup.add(btns[i])
                pass

        msgs = content['content']
        for i in range(len(msgs)):
            m = msgs[i]
            mrk = markup if i == len(msgs) - 1 else None

            mtype = m[1]
            if m[0] == '':
                continue
            print('Sending part of message')
            try:
                if mtype == tp.MSG_TYPE.text:
                    corr_m = m[0]
                    field = re.findall('\?\?\?(\S+)\?\?\?', corr_m)
                    for f in field:
                        val = self.data_table.getFieldValue(uid, f.strip())
                        corr_m = corr_m.replace('???' + f + '???', str(val))
                    self.send_message(_id, corr_m, reply_markup=mrk,
                                      parse_mode='html')  # TODO define abstract class MSG sending an apppropriate type of msg (method send())
                elif mtype == tp.MSG_TYPE.image:
                    self.send_photo(_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.video:
                    try:
                        self.send_video(_id, m[0], reply_markup=mrk)
                    except:
                        corr_url = m[0].replace('https://dl.dropboxusercontent.com/', 'https://www.dropbox.com/')
                        self.send_message(_id, corr_url)
                elif mtype == tp.MSG_TYPE.audio:
                    self.send_audio(_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.audionote:
                    self.send_voice(_id, m[0])
            except Exception as err:
                self.send_message(_id, m[0], reply_markup=mrk)
                print('Err in sayhello: ' + str(err))
        pass

    def create_lesson_chat(self, pupil_user):
        participants = [self.user.username, *self.bot_state['chiefname'], pupil_user.username]
        txt = commands.SCOMMANDS.create_a_chat + ';' + ';'.join(participants)
        self.send_message(self.bot_state['chiefid'], txt)
        pass

    def pay_command(self, chat_id, dptr, addr, subscribe_id):
        print('pay_command')

        _markup = types.InlineKeyboardMarkup(row_width=2)
        callback = 'unch;' + 'Назад' + ';' + dptr + ';' + dptr

        discont = self.data_table.getFieldValue(chat_id, 'score', key_column='chat_id')
        discont = int(discont) * 100

        if subscribe_id == 1:
            special_price = self.PRICE_1
            special_price.amount = special_price.amount - discont * 10
            _markup.add(
                types.InlineKeyboardButton('Оплатить ' + str(int(special_price.amount / 100)) + ' руб', pay=True))
            _markup.add(types.InlineKeyboardButton('Назад', callback_data=callback))
            self.send_invoice(chat_id,
                              title="3 месяца обучения",
                              description="Любой уровень на ваш выбор. Идеально подойдет тем, кому нужно говорить уже вчера, нет системных знаний и хочется почувствовать прогресс в обучении.",
                              provider_token=self.PAYMENT_TOCKEN,
                              currency="rub",
                              is_flexible=False,
                              prices=[special_price],
                              start_parameter="three-month-subscription",
                              invoice_payload="mounth3",
                              photo_url='https://dl.dropboxusercontent.com/scl/fi/g9zlqj85vit74ymrjpsg0/logo_langusto.png?rlkey=2qd8i57bmz6tt20x0c2fzyeml&dl=0',
                              photo_height=478,
                              photo_width=512,
                              photo_size=512,
                              reply_markup=_markup)
        elif subscribe_id == 2:
            special_price = self.PRICE_2
            special_price.amount = special_price.amount - discont * 10
            _markup.add(
                types.InlineKeyboardButton('Оплатить ' + str(int(special_price.amount / 100)) + ' руб', pay=True))
            _markup.add(types.InlineKeyboardButton('Назад', callback_data=callback))
            self.send_invoice(chat_id,
                              title="6 месяцев обучения",
                              description="Любые два уровня на ваш выбор. Можно начать с нуля или продолжить обучение. Мощное погружение в язык со значительными результатами.",
                              provider_token=self.PAYMENT_TOCKEN,
                              currency="rub",
                              is_flexible=False,
                              prices=[special_price],
                              start_parameter="six-month-subscription",
                              invoice_payload="mounth6",
                              photo_url='https://dl.dropboxusercontent.com/scl/fi/g9zlqj85vit74ymrjpsg0/logo_langusto.png?rlkey=2qd8i57bmz6tt20x0c2fzyeml&dl=0',
                              photo_height=478,
                              photo_width=512,
                              photo_size=512,
                              reply_markup=_markup)
        elif subscribe_id == 3:
            special_price = self.PRICE_3
            special_price.amount = special_price.amount - discont * 10
            _markup.add(
                types.InlineKeyboardButton('Оплатить ' + str(int(special_price.amount / 100)) + ' руб', pay=True))
            _markup.add(types.InlineKeyboardButton('Назад', callback_data=callback))
            self.send_invoice(chat_id,
                              title="12 месев обучения",
                              description="Полный курс обучения. С нуля и до уверенного владения итальянским. Через год можно покупать билеты и уезжать в Италию!",
                              provider_token=self.PAYMENT_TOCKEN,
                              currency="rub",
                              is_flexible=False,
                              prices=[special_price],
                              start_parameter="one-year-subscription",
                              invoice_payload="mounth12",
                              photo_url='https://dl.dropboxusercontent.com/scl/fi/g9zlqj85vit74ymrjpsg0/logo_langusto.png?rlkey=2qd8i57bmz6tt20x0c2fzyeml&dl=0',
                              photo_height=478,
                              photo_width=512,
                              photo_size=512,
                              reply_markup=_markup)
        elif subscribe_id == 4:
            special_price = self.PRICE_4
            special_price.amount = special_price.amount - discont * 10
            _markup.add(
                types.InlineKeyboardButton('Оплатить ' + str(int(special_price.amount / 100)) + ' руб', pay=True))
            _markup.add(types.InlineKeyboardButton('Назад', callback_data=callback))
            self.send_invoice(chat_id,
                              title="1 неделя обучения",
                              description="Для скупых.",
                              provider_token=self.PAYMENT_TOCKEN,
                              currency="rub",
                              is_flexible=False,
                              prices=[special_price],
                              start_parameter="one-week-subscription",
                              invoice_payload="week",
                              photo_url='https://dl.dropboxusercontent.com/scl/fi/g9zlqj85vit74ymrjpsg0/logo_langusto.png?rlkey=2qd8i57bmz6tt20x0c2fzyeml&dl=0',
                              photo_height=478,
                              photo_width=512,
                              photo_size=512,
                              reply_markup=_markup)
        pass

    def run(self):
        while True:
            try:
                self.polling(none_stop=True, interval=0, skip_pending=True)
            except Exception as e:
                print(str(e))
                time.sleep(15)

    def __find_keys(self, d, value):
        return [key for key, x in d.items() if str(x) == str(value)]

    def __extract_command(self, msg):
        z = re.match('//([a-zA-Z0-9-_]+)@?\.*', msg)
        if not (z):
            return ''
        return z.groups()[0]
        pass

    def __savestatus(self, id, status, more_val=[], more_fields=[]):
        self.data_table.setFieldValues(id, [status, str(datetime.utcnow().isoformat()), *more_val],
                                       ['status', 'last_activity_date', *more_fields])

    def __createKeyFromContent(self, id, chat_id, content):

        self.user_command[id] = []  # .pop(id, None)
        self.teacher_command[chat_id] = []  # .pop(chat_id, None)
        self.conditions[chat_id] = []

        btns = []
        user_status = self.user_cell_position[id]
        open_input_flad = 0
        for b in content:
            title, addr, sp = b
            title = title.strip()
            # if sp == '/input' and open_input_flad == 0:
            #    btns.append(None)
            #    open_input_flad += 1
            #    continue
            if sp == '/to_lsn':
                callback = 'to_lsn;' + '' + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
                continue
            if sp == '/saveuser':
                callback = 'saveuser;' + '' + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
                continue
            if sp == '/pay1':
                callback = 'pay;' + user_status + ';' + addr + ';1'
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
                pass
            if sp == '/pay2':
                callback = 'pay;' + user_status + ';' + addr + ';2'
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
                pass
            if sp == '/pay3':
                callback = 'pay;' + user_status + ';' + addr + ';3'
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
                pass
            if sp == '/pay4':
                callback = 'pay;' + user_status + ';' + addr + ';4'
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
                pass
            if sp == '/edit':
                if (self.user_cell_position[id] in self.data_dstn):
                    fieldname = self.data_dstn[self.user_cell_position[id]]
                    content = self.data_table.getFieldValue(id, fieldname)
                    if content is None:
                        pass
                    else:
                        callback = 'unch;' + 'Ок' + ';' + user_status + ';' + addr  # TODO consider if possible to use "user status" token and take out the method to textProcessor since no id and status is needed
                        btns.append(types.InlineKeyboardButton(title, switch_inline_query_current_chat=content))
                        btns.append(types.InlineKeyboardButton('Ок', callback_data=callback))
                    pass
                pass
            if sp == '/delete_me':
                pass
            if sp == '/break':
                btns.append(None)
                self.conditions[chat_id].append(['check:' + title, addr])
                pass

            if sp == '/set':
                btns.append(None)
                self.conditions[chat_id].append(['set;' + title, addr])
                pass

            if sp == '/ucommand':
                cmd = self.__extract_command(title)
                btns.append(None)
                self.user_command[id].append([cmd, addr])
            if sp == '/tcommand':
                cmd = self.__extract_command(title)
                btns.append(None)
                self.teacher_command[chat_id].append([cmd, addr])
            if sp == '/tomorrow':
                callback = 'tomorrow;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
            if sp == '/back':
                callback = 'unch;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
            if sp == '/check':
                callback = 'chk;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
            if sp is None or sp == '':
                callback = 'chng;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
        return btns

    def __check_user(self, id):
        pupils = self.data_table.getAllPupilColumns(['id', 'status', 'chat_id'])
        id = str(id)
        if id in str(pupils[0]):
            j = pupils[0].index(id)
            return {int(id): pupils[1][j]}, {int(id): int(pupils[2][j])}
        else:
            return None

    def __check_user_info(self, id):  # TODO Add checking of fullness of the user info
        record = self.data_table.getAllFieldValue(id)
        for h, u in zip(record[2], record[-1]):
            if int(h) == 1:
                if u == '':
                    return False
        ind = record[0].index('chat_id')
        try:
            if int(record[-1][ind]) != -1:
                self.user_chat_id[id] = int(record[-1][ind])
                return False
        except:
            pass
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
        user_dict['status'] = self.user_cell_position[user_dict['id']]
        user_dict['chat_id'] = -1
        user_dict['score'] = 100
        user_dict['lesson_num'] = 2
        user_dict['lessons_at_once'] = 0
        self.user_chat_id[int(user_dict['id'])] = -1
        self.user_frozen[int(user_dict['id'])] = False
        return user_dict

    def __invert_datasource_link(self, data_structure):
        for k in data_structure.keys():
            f = data_structure[k]
            result = re.match("(\w+![A-Z]+\d+)", f['source'])
            if not (result is None):
                self.data_dstn[result.group(1)] = k
            pass


# bot.send_poll(message.chat.id, 'вопрос', options=['1', '2', '3'])

state_f = open('resources/tokens.json', 'r')
tokens = json.load(state_f)
state_f.close()

survey_table = googleSheetTest.GoogleTableReader(tokens['gsheet'])

try:
    survey_bot = SurveyBot(tokens['bot_token'], survey_table, tokens['p_tocken'])  # new testing bot with working shop
    survey_bot.run()
except Exception as err:
    print('General error, rebooting ' + str(err))
    os.abort()
