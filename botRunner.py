import telebot
from telebot import apihelper
from telebot import types
import re
import calendar
from datetime import datetime, date, timezone
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

#-------------------------------------------------------#
#----created by Andrey Svitenkov, Undresaid, 10.2023----#
#-------------------------------------------------------#

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
    reminders = {}
    user_chat_id  = {}
    user_command  = {}
    conditions    = {}
    teacher_command = {}
    tmp_msg_await   = {}
    tmp_msg_kill    = {}
    tmp_addr        = {}

    bot_state = {}
    schedule = {}

    now_processing_id = -1


    PAYMENT_TOCKEN = ''

    initialisation = False

    logfile = ''

    spam_message = None

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

        threading.Timer(60.0, self.checkSchedule).start()

        self.init_state()
        self.initialisation = False
        #str(datetime.utcnow())
        self.logfile = open('resources\\LOGS\\LOG_' + '.txt', 'a', encoding="utf-8")

        self.log_list = {}

        pass

        # pre checkout  (must be answered in 10 seconds)
        @self.pre_checkout_query_handler(lambda query: True)
        def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
            self.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
            print('Preliminary test')

        @self.message_handler(content_types=['successful_payment'])
        def successful_payment(message: types.Message):
            print("SUCCESSFUL PAYMENT:")
            self.__add_to_log(message.from_user.id, {'command': 'successful_payment', 'exit': 'Failed'})
            payment_info = message.successful_payment
            cid = self.user_chat_id[message.from_user.id]
            try:
                link = self.create_chat_invite_link(int(cid)).invite_link
                self.send_message(self.bot_state['chiefid'], '!!!ОПЛАТА В ЧАТЕ, ГУЛЯЙ РВАНИНА!!!: \n' + link)
            except:
                self.send_message(self.bot_state['chiefid'], '!!!' + str(message.from_user.username) + ' ОПЛАТИЛ КУРС, ПРОВЕРЬ ТАБЛИЦУ!!!: \n')

            uid = message.from_user.id
            for opt in commands.PAY_OPTIONS.options:
                if message.successful_payment.invoice_payload == opt['invoice_payload']:
                    self.data_table.setFieldValues(uid, ['0',str(message.successful_payment),
                                                         str(datetime.utcnow().isoformat()), opt['period'], opt['num'], 0],
                                                        ['score','payment_info', 'payment_date', 'period', 'lesson_num', 'curr_lesson'])

            self.__savestatus(uid,self.user_cell_position[uid])
            self.say_hello(uid, cid)
            print(payment_info)

        @self.message_handler(func=lambda m: tp.MSG_TYPE.compare('/cheat42', m.text) == len('/cheat42'))
        @self.single_user_decorator
        def chat_command(message):
            print('cheat_command')
            if not(message.from_user.id in self.bot_state['chiefid']):
                return None
            cell = message.text.split(';')[-1]
            self.show_cell(message.chat.id, cell)

        @self.message_handler(func=lambda m: tp.MSG_TYPE.compare('/moveto', m.text) == len('/moveto'))
        @self.single_user_decorator
        def moveto_command(message):
            print('moveto_command')
            if not(message.from_user.id in self.bot_state['chiefid']):
                return None
            cid = message.chat.id
            cell = message.text.split(';')[-1]
            uid = self.__find_keys(self.user_chat_id, cid)[0]
            self.__add_to_log(uid, {'command': '/moveto', 'dest': cell, 'status': self.user_cell_position[uid],
                                    'teacher': message.from_user.id})
            self.user_cell_position[uid] = cell
            self.say_hello(uid, cid)
            self.__savestatus(uid, self.user_cell_position[uid], more_fields=['delayed_event'], more_val=[''])

        @self.message_handler(func=lambda m: tp.MSG_TYPE.compare('/paid', m.text) == len('/paid'))
        @self.single_user_decorator
        def paid_command(message):
            print('paid_command')
            if not (message.from_user.id in self.bot_state['chiefid']):
                return None
            cid = message.chat.id
            info = message.text.split(';')

            period = 365
            lnum = int(message.text.split(';')[1])
            if len(info)>2:
                period = int(message.text.split(';')[2])

            uid = self.__find_keys(self.user_chat_id, cid)[0]
            self.data_table.setFieldValues(uid,
                                           ['0', 'online_payment', str(datetime.utcnow().isoformat()), period,
                                            lnum, 0],
                                           ['score', 'payment_info', 'payment_date', 'period', 'lesson_num',
                                            'curr_lesson'])
            call_msg = self.data_table.getFieldValue(cid, 'paid_call', key_column='chat_id')
            if call_msg=='' or call_msg is None:
                self.send_message(cid,'Оплата проверена! \n/status чтоб узнать подробности. \n/start чтоб продолжить.')
                return None

            call_chat_id, call_msg_id, when = call_msg.split(';')
            try:
                chat_ids = call_chat_id.split(',')
                msg_ids  = call_msg_id .split(',')
                uname = self.data_table.getFieldValue(uid, 'username')
                for c_id, m_id in zip(chat_ids, msg_ids):
                    self.edit_message_text('Оплата произведена: ' + str(uid) + ' username:' + str(uname) +
                                           '; lessons: ' + str(lnum) + '; preiod: ' + str(period),
                                           chat_id=int(c_id), message_id=int(m_id))
                self.send_message(c_id,'Оплата проверена! \n/status чтоб узнать подробности. \n/start чтоб продолжить.')
                #self.say_hello(c_id, self.__find_keys(self.user_chat_id, cid)[0])
            except Exception as err:
                print('ERROR: edit_message_text(Оплата произведена...' + str(err))
                pass
            self.__add_to_log(uid, {'command': '/paid', 'exit': 'Success','teacher':message.from_user.id})
            self.say_hello(uid, cid)

        @self.message_handler(
            func=lambda m: tp.MSG_TYPE.compare('/savechannel', m.text) == len('/savechannel'))  # TODO: move to commads
        @self.single_user_decorator
        def new_chat_event(message):
            print('new_chat_event')
            if not(message.from_user.id in self.bot_state['chiefid']):
                self.send_message(message.from_user.id,
                                  "Только администратор бота может отдавать команду на создание обучающего чата")
                return None

            cmd = tp.parseCommand(message.text)
            uid = cmd['args'][0]
            cid = cmd['args'][1]
            ch_date = cmd['args'][2]

            self.__add_to_log(uid, {'command':'/savechannel', 'exit':'Success'})
            try:
                uid = int(uid)
                cid = int(cid)
            except Exception as err:
                print('Wrong chat id: not a number ' + str(err))

            if uid in self.bot_state['chiefid']:
                return None
            
            if not(int(uid) in self.user_chat_id.keys()):
                self.kick_chat_member(chat_id=cid, user_id=uid, until_date=None)
                print('Попытка добавить неизвестного пользователя + ' + str(uid) + ' to ' + str(cid))
                self.__add_to_log(uid, {'command': '/savechannel', 'exit': 'Failed', 'error': 'UnknownUser'})
                return None
            if cid in self.user_chat_id.values():
                self.kick_chat_member(chat_id=cid, user_id=uid, until_date=None)
                print('Попытка добавить лишнего пользователя + ' + str(uid) + ' to ' + str(cid))
                self.__add_to_log(uid, {'command': '/savechannel', 'exit': 'Failed', 'error': 'ExtraUser'})
                return None

            try:
                data_table.setFieldValues(int(uid), [cid, ch_date], ['chat_id', 'date_start'])
                self.user_chat_id[int(uid)] = cid
                link = self.create_chat_invite_link(cid).invite_link
                data_table.setFieldValue(int(uid), link, 'chat_link')

               # p_message = self.send_message(cid, '<b>/status</b> чтоб посмотреть доступные команды;\n<b>/start</b> если ничего не происходит или кажется, что что-то сломалось.',
               #                               parse_mode='html')
               # self.pin_chat_message(chat_id=p_message.chat.id, message_id=p_message.message_id)

                self.start_lesson(int(uid), cid, message)
                self.cleanReminders(int(uid))
            except Exception as err:
                self.data_table.critical_flag = False
                self.send_message(cid,
                                  "Что-то пошло не так. Наберите /nonfunziona чтоб сообщить об этом преподавателю")
                print('new_chat_event: ' + str(err))
                self.__add_to_log(uid, {'command': '/savechannel', 'exit': 'Failed', 'error':str(err)})
            pass

        @self.message_handler(
            func=lambda m: tp.MSG_TYPE.compare('/tunnelmsg', m.text) == len('/tunnelmsg'))  # TODO: move to commands
    #    @self.single_user_decorator
        def tunnel_msg(message):
            print('tunnel_msg')
            try:
                cmd = tp.parseCommand(message.text)
                _id = int(cmd['args'][0])
                try:
                    addr = cmd['args'][-2]
                    flag = int(cmd['args'][-1])
                except:
                    flag = False

                try:
                    self.send_message(_id, cmd['args'][1])
                except Exception as err:
                    print('Cant tunnel msg ot ' + str(_id) + ' due to: ' + str(err))

                if bool(flag):
                    self.user_cell_position[_id] = addr
                    self.data_table.setFieldValue(_id, addr, 'status')
                    print('MSG to user: ' + str(_id) + '; msg: ' + str(message.text))


            except Exception as err:
                print('Err in tunnel_msg: ' + str(err))
                pass

        @self.message_handler(commands=['imyourchief'])
        def chief_command(message):
            print('chief_command')
            if message.from_user.username == 'roro_tmp' or message.from_user.username == 'fille_soleil' or message.from_user.username == 'photo_mascha':
                self.send_message(message.from_user.id, "Да, моя госпожа!!")
                if not(message.from_user.id in self.bot_state):
                    if not(message.from_user.id in self.bot_state['chiefid']):
                        self.bot_state['chiefid'  ].append(message.from_user.id      )
                        self.bot_state['chiefname'].append(message.from_user.username)
            else:
                self.send_message(message.from_user.id, "Your username is wrong, you are not a chief")

            state_f = open(self.bot_state_filepath, 'w')
            json.dump(self.bot_state, state_f)
            state_f.close()

        @self.message_handler(func=lambda m: tp.MSG_TYPE.compare('/sendcold', m.text) == len('/sendcold'))
        @self.single_user_decorator
        def sendtocold_command(message):
            print('send_to_cold')
            tid = message.from_user.id

            if not('chiefid' in self.bot_state and tid in self.bot_state['chiefid']):
                self.send_message(tid, 'Вы не учитель. Команда доступна только для учителя.')
                return None

            if (self.spam_message is None):
                cell = message.text.split(';')[-1]
                msg = self.data_table.getValueFromStr(cell)[0][0]
                content = tp.parseMessage(msg, '')
                for i in range(len(content)):
                    content[i]['buttons'] = self.__anonKeyFromContent(content[i]['buttons'], cell)
                self.spam_message = [content,None]
                self.anonMessageSend(tid, tid, self.spam_message[0])
                markup = types.InlineKeyboardMarkup(row_width=2)
                callback = 'clearspam;;;'
                markup.add(types.InlineKeyboardButton('No, arret!', callback_data=callback))
                self.spam_message[1] = self.send_message(tid, "👆Ce message sera envoye.👆\nPour continuer repeter la command.", reply_markup=markup)
                return None

            cold_users = self.data_table.getAllValue(sheetName='cold', range='A1:C999')
            dest = []
            for row in cold_users[1:]:
                try:
                    dest.append([int(row[0]), row[2],False,'UnknownFilter'])
                except:
                    dest.append([0, row[2],False,''])

            succes_counter = 0
            total_counter = 0
            for ent in dest:
                uid = ent[0]
                if uid==0:
                    continue
                total_counter+=1
                cid = uid
                if ent[1] == 'nochat':
                    if uid in self.user_chat_id and int(self.user_chat_id[uid]) < -1:
                        ent[2], ent[3] = False, 'Filtered'
                    else:
                        ent[2], ent[3] = self.anonMessageSend(uid, uid, self.spam_message[0])
                if ent[1] == 'chat':
                    if int(cid)!=int(uid):
                        ent[2], ent[3] = self.anonMessageSend(cid, uid, self.spam_message[0])
                    else:
                        ent[2], ent[3] = False,'Filtered'
                if ent[1] == 'bot':
                    ent[2], ent[3] = self.anonMessageSend(uid, uid, self.spam_message[0])
                if ent[1] == 'auto' or ent[1] == '':
                    ent[2], ent[3] = self.anonMessageSend(cid, uid, self.spam_message[0])
                pass
                if ent[2]:
                    succes_counter+=1


            self.send_message(tid, 'Le message a été envoye: <b>' + str(succes_counter) + ' of '
                              + str(total_counter) + '</b> avec success.\n\nEt vous Margo, vous ete la femme de rêve!🐇🐇🐇',
                              parse_mode='html')
            try:
                self.edit_message_reply_markup(tid,
                                               message_id=self.spam_message[1].message_id, reply_markup='')
            except:
                pass
            self.spam_message = None
            result = [[x[3]] for x in dest]
            self.data_table.setValue(result, 'cold', 'D2')
            pass

        @self.message_handler(commands=['start'])
        @self.single_user_decorator
        def start_command(message):
            print('start_command')
            uid = message.from_user.id
            cid = message.chat.id

            if not(message.text.strip()=='/start'):
                return None

            print('START from: ' + str(uid) + ' ' + str(message.from_user.username))
            print('Chat id: ' + str(cid))

            #self.data_table.forceRead()

            if 'chiefid' in self.bot_state and uid in self.bot_state['chiefid']:
                self.send_message(cid, 'Вы учитель.')
                if cid == uid:
                    self.send_message(cid, 'Нельзя быть учителем и учеником одновременно.')
                    self.data_table.allUpdate()
                    self.send_message(cid, 'Синхронизация таблицы проведена!')
                return None
            else:
                if uid in self.user_chat_id:
                    self.user_chat_id[uid] = self.data_table.getFieldValue(uid, 'chat_id')

            if uid in self.user_chat_id:
                if int(self.user_chat_id[uid])!=-1 and int(self.user_chat_id[uid])!=cid:
                    try:
                        link = self.create_chat_invite_link(int(self.user_chat_id[uid])).invite_link
                        self.send_message(cid, 'Перейдите в обучающий чат: ' + link)
                        self.data_table.setFieldValue(uid, link, 'chat_id')
                        return None
                    except:
                        self.user_chat_id[uid] = -1
                        self.data_table.setFieldValue(uid, -1, 'chat_id')
                        pass
                elif uid!=cid and int(self.user_chat_id[uid])==-1: #TODO: make by /savechannel route, not by lesson
                    try:
                        self.get_chat_member(cid, uid)
                        now = datetime.utcnow().date()
                        link = self.create_chat_invite_link(cid).invite_link
                        self.data_table.setFieldValue(uid, link, 'chat_id')
                        data_table.setFieldValues(int(uid), [cid, now.isoformat()], ['chat_id', 'date_start'])
                        self.user_chat_id[int(uid)] = cid
                        p_message = self.send_message(cid,
                                                      '<b>/status</b> чтоб помотреть доступные команды;\n<b>/start</b> если ничего не происходит или кажется, что что-то сломалось.',
                                                      parse_mode='html')
                        self.pin_chat_message(chat_id=cid, message_id=p_message.message_id)
                        self.start_lesson(int(uid), cid, message)
                    except:
                        print('Error at /start for: ' + str(uid) + ' at chat: '+ str(cid)+'. User not a member of the chat.')
                        return None
                        pass

            self.data_table.allUpdate()
            user = self.__check_user(message.from_user.id)
            if (user == None):
                self.__add_to_log(uid, {'command': 'newuser', 'exit': 'Failed'})
                uid = message.from_user.id
                self.user_cell_position.pop(uid,None)
                self.user_chat_id.pop(uid, None)
                self.user_command[uid]=[]
                self.teacher_command[uid]=[]
                self.schedule.pop(uid, None)
                self.reminders.pop(uid, None)
                pupil_info = self.__create_user(self.survey_dict,
                                                message.from_user)  # TODO change to save next state, not current
                self.data_table.addPupil(pupil_info)
                self.__add_to_log(uid, {'exit': 'Success'})

            else:
                self.__add_to_log(uid, {'command': 'start', 'exit': 'Failed'})
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
            result = self.send_message(self.bot_state['chiefid'], '🔴 СБОЙ В ЧАТЕ: 🔴 \n' + link)

            now = datetime.utcnow()
            all_chat_ids = ','.join([str(res.chat.id)    for res in result])
            all_msg_ids  = ','.join([str(res.message_id) for res in result])

            self.data_table.setFieldValue(uid,
                                          str(all_chat_ids) + ';' + str(all_msg_ids) + ';' + str(
                                              now.isoformat()), 'tech_call')
            self.data_table.setFieldValue(uid, link, 'chat_link')
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
            result = self.send_message(self.bot_state['chiefid'], '🟡 Вопрос в чате: \n' + link)

            now = datetime.utcnow()
            all_chat_ids = ','.join([str(res.chat.id) for res in result])
            all_msg_ids = ','.join([str(res.message_id) for res in result])

            self.data_table.setFieldValue(uid,
                                          str(all_chat_ids) + ';' + str(all_msg_ids) + ';' + str(
                                              now.isoformat()), 'question')
            self.data_table.setFieldValue(uid, link, 'chat_link')
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
                link = self.data_table.getFieldValue(int(cid), 'chat_link', key_column='chat_id')
                for c_id, m_id in zip(chat_ids, msg_ids):
                    self.edit_message_text('✅ Запрос о сбое в чате <b>снят</b>: \т' + str(link), chat_id=int(c_id), message_id=int(m_id), parse_mode='html')
            except Exception as err:
                print('edit_message_text(Запрос снят' + str(err))
                pass
            self.data_table.setFieldValue(cid, '', 'tech_call', key_column='chat_id')
            self.send_message(cid, 'Запрос о сбое снят')
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
                link = self.data_table.getFieldValue(int(cid), 'chat_link', key_column='chat_id')
                for c_id, m_id in zip(chat_ids, msg_ids):
                    self.edit_message_text('✅ Вопрос в чате <b>снят:</b>' + str(link), chat_id=int(c_id), message_id=int(m_id), parse_mode='html')
            except Exception as err:
                print('edit_message_text(Запрос снят' + str(err))
                pass
            self.data_table.setFieldValue(cid, '', 'question', key_column='chat_id')
            self.send_message(cid, 'Вопрос снят')



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

            self.__add_to_log(uid, {'command': 'scongelare', 'exit': 'Failed'})

            if not(uid in self.bot_state['chiefid']):
                if cid != self.user_chat_id[uid]:
                    return None

            freeze_info = self.data_table.getFieldValue(cid, key_column='chat_id', fieldname='freeze')
            schedule, txt = tp.parseFreeze(freeze_info)

            if schedule[-1][1].strip() == 'nowadays':
                cell_txt = tp.encodeFreeze(schedule, datetime.utcnow().date())
                self.data_table.setFieldValue(cid, cell_txt, 'freeze', key_column='chat_id')
                self.send_message(cid, 'Курс раморожен\n')
                self.__add_to_log(uid, {'command': 'scongelare', 'exit': 'Success'})
            else:
                self.send_message(cid, 'Курс не заморожен\n')
                self.__add_to_log(uid, {'error': 'NotFrosen'})
            pass

        @self.message_handler(commands=['congelare'])
        @self.single_user_decorator
        def freeze_command(message):
            uid = message.from_user.id
            cid = message.chat.id

            if not(uid in self.bot_state['chiefid']):
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
                self.__add_to_log(self.__find_keys(self.user_chat_id, cid)[0], {'command': 'congelare', 'teacher':uid ,'exit': 'Success'})
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

            if not(message.text.strip()=='/status'):
                return None

            self.send_chat_action(cid, 'typing')

            teacher = False
            bot_control = False
            hard_commands = {}
            txt = ''

            commands_guru = commands.cmdGuru(commands.UCOMMANDS)
            if 'chiefid' in self.bot_state and uid in self.bot_state['chiefid']:
                uid_list = self.__find_keys(self.user_chat_id, cid)
                if uid_list:
                    uid = uid_list[0]
                    self.send_message(cid, 'Вы учитель. Статус ученика:')
                    commands_guru = commands.cmdGuru(commands.TCOMMANDS)
                    teacher = True
                else:
                    self.send_message(cid, 'Вы учитель. Управление ботом:')
                    commands_guru = commands.cmdGuru(commands.GCOMMANDS)
                    bot_control = True

            if not(bot_control):
                user_status = self.data_table.getPupilStatus(uid)
                if not(user_status):
                    self.send_message(cid, 'Вы новый ученик: \n /start чтоб выбрать курс и перейти к обучению.')
                    return None
                elif int(user_status['chat_id']) == -1:
                    self.send_message(cid, 'Вы новый ученик: \n /start чтоб выбрать курс и перейти к обучению.')
                    return None

                chat_id = int(self.user_chat_id[uid])
                if cid != chat_id:
                    try:
                        link = self.create_chat_invite_link(int(cid)).invite_link
                        self.send_message(cid, "Перейдите в обучающий чат: " + link)
                    except:
                        pass
                when = datetime.fromisoformat(user_status['date_start'])
                txt += "Начало обучения " + str(when.date())
                if 'curr_lesson' in user_status.keys() and user_status['curr_lesson'] != '' and not(user_status['curr_lesson'] is None):
                    curr_lesson = int(user_status['curr_lesson'])
                    txt += '\n<b>Текущий урок: ' + str(curr_lesson) +'</b>'
                self.send_message(cid, txt, parse_mode='html')
                txt = ''
                if chat_id != cid:
                    link = self.create_chat_invite_link(chat_id).invite_link
                    self.send_message(cid, "Ваш чат для обучения: " + link)
                    return None
                if 'call_message_id' in user_status.keys() and user_status['call_message_id'] != '' and not(user_status['call_message_id'] is None):
                    r1, r2, when = user_status['call_message_id'].split(';')
                    when = datetime.fromisoformat(when)
                    self.send_message(cid, "Отправлен запрос на проверку " +
                                      str(when.date()) + ' в ' +
                                      str(when.hour) + ':' + str(when.minute) + 'GMT;')

                if 'tech_call' in user_status.keys() and user_status['tech_call'] != '' and not(user_status['tech_call'] is None):
                    r1, r2, when = user_status['tech_call'].split(';')
                    when = datetime.fromisoformat(when)
                    self.send_message(cid, "Отправлено уведомление о сбое " +
                                      str(when.date()) + ' в ' +
                                      str(when.hour) + ':' + str(when.minute) + 'GMT;')
                    commands_guru.setMask('nonfunziona', False)
                    commands_guru.setMask('funziona', True)
                    #txt += "\n/funziona - снять запрос на вызов преподавателя;\n"

                if 'question' in user_status.keys() and user_status['question'] != '' and not(user_status['question'] is None):
                    r1, r2, when = user_status['question'].split(';')
                    when = datetime.fromisoformat(when)
                    self.send_message(cid, "Отправлено уведомление о вопросе " +
                                      str(when.date()) + ' в ' +
                                      str(when.hour) + ':' + str(when.minute) + 'GMT;')
                    commands_guru.setMask('aiuto'  , False)
                    commands_guru.setMask('risolto', True)
                    #txt += "\n/risolto - снять запрос на вызов преподавателя;\n"

                if 'delayed_event' in user_status.keys() and user_status['delayed_event'] != '' and not(user_status['delayed_event'] is None):
                    when, cell = user_status['delayed_event'].split(';')
                    when = datetime.fromisoformat(when)
                    self.send_message(cid, "Следующий урок будет выслан: " +
                                      str(when.date()) + ' в ' +
                                      str(when.hour) + ':' + str(when.minute) + 'GMT;')
                if 'score' in user_status.keys() and user_status['score'] != '':
                    score = int(user_status['score'])
                    self.send_message(cid, "На вашем счету: " + str(score) + ' баллов.')

                if 'payment_date' in user_status.keys() and user_status['payment_date'] != '' and not(user_status['payment_date'] is None):
                    when = datetime.fromisoformat(user_status['payment_date'])
                    period = int(user_status['period'])
                    l_num = int(user_status['lesson_num'])
                    self.send_message(cid, 'Оплата произведена: ' +
                                      str(when.date()) + '\nВы оплатили курс на ' + str(period) + ' дней, ' + str(l_num) + ' уроков.')
                    rest = (datetime.utcnow().date() - when.date()).days
                    schedule, txt_sc = tp.parseFreeze(user_status['freeze'])
                    for s in schedule:
                        rest += s[2]

                    txt += 'История заморозок курса: \n' + txt_sc
                    if len(schedule)>0:
                        if schedule[-1][1]=='nowadays':
                            txt += "<b>Сейчас курс заморожен с " + str(schedule[-1][0]) + '</b>'
                            commands_guru.setMask('congelare', False)

                    txt += "\nДо конца курса осталось " + str(period - rest) + ' дней;\n'
                    txt += "Можно получить уроков <b>вне очереди: " + str(3-int(user_status['lessons_at_once'])) + '</b>\n'
                else:
                    commands_guru.setMask('congelare', False)
                    commands_guru.setMask('scongelare', False)

                if not(self.user_frozen[uid]):
                    txt += '\nКоманды ученика:'
                    if uid in self.user_command:
                        for c in self.user_command[uid]:
                            try:
                                txt += '\n//' + str(c[0]) + ' - ' + commands.UCOMMANDS.soft_commands[str(c[0])]
                            except Exception as e:
                                print('Error in status_command: ' + str(e))

            if (teacher):
                txt += '\n\nКоманды учителя:'
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

        @self.callback_query_handler(func=lambda c: c.data.startswith('r_pay'))
        @self.single_user_decorator
        def pay_hendler(callback_query: types.CallbackQuery):
            self.answer_callback_query(callback_query.id)
            stat = self.data_table.getPupilStatus(callback_query.from_user.id)
            self.pay_request(callback_query.from_user.id, stat.get('score', 0))
            try:
                self.edit_message_reply_markup(callback_query.message.chat.id,
                                               message_id=callback_query.message.message_id, reply_markup='')
            except:
                pass
            pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('clearspam'))
        @self.single_user_decorator
        def clear_spam(callback_query: types.CallbackQuery):
            self.answer_callback_query(callback_query.id)
            self.spam_message = None
            try:
                self.edit_message_reply_markup(callback_query.message.chat.id,
                                               message_id=callback_query.message.message_id, reply_markup='')
            except:
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
            if subscr_id=='onl':
                self.pay_online_request(callback_query.from_user.id)
                return None

            self.pay_command(callback_query.message.chat.id, dptr, addr, subscr_id)
            try:
                self.edit_message_reply_markup(callback_query.message.chat.id, message_id=callback_query.message.message_id - (
                        callback_query.message.from_user.username != self.user.username), reply_markup='')
            except:
                pass
            pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('paid'))
        @self.single_user_decorator
        def paid_hendler(callback_query: types.CallbackQuery):
            self.answer_callback_query(callback_query.id)
            uid = callback_query.from_user.id
            cid = callback_query.message.chat.id
            if uid in self.bot_state.get('chiefid',[]):
                pass

            link = self.create_chat_invite_link(int(cid)).invite_link
            result = self.send_message(self.bot_state['chiefid'], '💃🕺 ОПЛАТА В ЧАТЕ, ГУЛЯЙ РВАНИНА! 💃🕺\n' + link)

            now = datetime.utcnow()
            all_chat_ids = ','.join([str(res.chat.id) for res in result])
            all_msg_ids  = ','.join([str(res.message_id) for res in result])

            self.data_table.setFieldValue(uid,
                                          str(all_chat_ids) + ';' + str(all_msg_ids) + ';' + str(
                                              now.isoformat()), 'paid_call')

            try:
                self.edit_message_reply_markup(callback_query.message.chat.id,
                                               message_id=callback_query.message.message_id, reply_markup='')
            except:
                pass

            result = self.send_message(cid, 'Уведомление отправлено, cейчас преподаватель проверит оплату и активирует курс!')
            pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('to_lsn'))
        @self.single_user_decorator
        def lesson_command(callback_query: types.CallbackQuery):
            message = callback_query.message
            print('lesson_command')
            try:
                self.send_chat_action(message.from_user.id, 'typing')
                self.answer_callback_query(callback_query.id)
            except:
                pass

            if not ('chiefid' in self.bot_state) or len(self.bot_state['chiefid']) == 0:
                self.send_message(callback_query.from_user.id,
                                  "Не могу создать урок, учитель не активировал опцию, поробуйте позже")
            else:
                chat_id = -1
                addr = callback_query.data.split(';')[-1]
                self.__add_to_log(callback_query.from_user.id,
                                  {#'status':self.user_cell_position[callback_query.from_user.id],
                                        'command': 'to_lsn',
                                        'dest':addr, 'exit':'Success'})
                if (self.user_chat_id[callback_query.from_user.id] == -1):
                    self.create_lesson_chat(addr, callback_query.from_user)#check if the chat was created
                else:
                    chat_id = int(self.user_chat_id[callback_query.from_user.id])
                    try:
                        link = self.create_chat_invite_link(chat_id).invite_link
                        self.send_message(callback_query.from_user.id, "Вы уже создали чат для урока: " + link)
                        self.__add_to_log(callback_query.from_user.id,{'exit': 'Failed', 'error':'Chat already created'})
                    except:
                        self.user_chat_id[callback_query.from_user.id] = -1
                        data_table.setFieldValue(callback_query.from_user.id, -1, 'chat_id')
                        self.create_lesson_chat(addr, callback_query.from_user)
            pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('tomorrow'))
        @self.single_user_decorator
        def next_step_delay(callback_query: types.CallbackQuery):
            print('next_step_delay')
            self.answer_callback_query(callback_query.id)
            cid = callback_query.message.chat.id
            uid = self.__find_keys(self.user_chat_id, cid)[0]

            if not(self.check_paymant(uid)):
                return None

            _today = datetime(datetime.today().year, datetime.today().month, datetime.today().day)
            rand_m = randrange(0, 30)
            _tomorrow = _today + dt.timedelta(days=1) + dt.timedelta(hours=4) + dt.timedelta(minutes=rand_m)
            _tomorrow_test = datetime.utcnow() + dt.timedelta(minutes=1)
            _tomorrow_test = _tomorrow #TODO comment here for debug
            event_stamp = str(_tomorrow_test.isoformat()) + ';' + callback_query.data.split(';')[-1]
            self.data_table.setFieldValues(uid, [event_stamp, 0], ['delayed_event','lessons_at_once'])
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

        @self.callback_query_handler(func=lambda c: c.data.startswith('saveuser')) #TODO: not needed method now, all users are saved from the begining
        @self.single_user_decorator
        def newuser_callback_button(callback_query: types.CallbackQuery):
            print('newuser_callback_button')
            self.answer_callback_query(callback_query.id)
            print(callback_query)
            print('Sending request to save user')

            try:
                pupil_info = self.__create_user(self.survey_dict,
                                                callback_query.from_user)  # TODO change to save next state, not current
                self.data_table.addPupil(pupil_info)
                if(not(self.data_table.forceWrite())):
                    print("!!!!ERROR1 __create_user: !!!!!" )
                    return None
            except Exception as err:
                self.data_table.critical_flag = False
                print("!!!!ERROR2 __create_user: !!!!!" + str(err))
                return None


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
        def goback_callback_button(callback_query: types.CallbackQuery, demo=False):
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

        @self.callback_query_handler(func=lambda c: c.data.startswith('demo'))
        @self.single_user_decorator
        def demo_callback_button(callback_query: types.CallbackQuery, demo=False):
            print('goback_callback_button')
            try:
                self.answer_callback_query(callback_query.id)
            except:
                pass
            callback_query.message.from_user.id = callback_query.from_user.id
            callback_query.message.text = callback_query.data.split(';')[1]
            try:
                self.goahead(callback_query.message, *callback_query.data.split(';')[2:], demo = True)
            except Exception as err:
                print('self.goahead(callback_query.message, *callback_query.data.split... ' + str(err))
                pass

        @self.callback_query_handler(func=lambda c: c.data.startswith('chng'))
        def goahead_callback_button(callback_query: types.CallbackQuery):
            callback_query.message.from_user.is_bot = False
            goback_callback_button(callback_query)

        @self.callback_query_handler(func=lambda c: c.data.startswith('url'))
        def goahead_callback_button(callback_query: types.CallbackQuery):
            callback_query.message.from_user.is_bot = False
            goback_callback_button(callback_query)

        @self.callback_query_handler(func=lambda c: c.data.startswith('nextl'))
        def goahead_callback_button(callback_query: types.CallbackQuery):
            callback_query.message.from_user.is_bot = False
            try:
                self.answer_callback_query(callback_query.id)
            except:
                pass
            cid = callback_query.message.chat.id
            uid = self.__find_keys(self.user_chat_id, cid)[0]
            self.__add_to_log(uid, {'command': 'nextl', 'exit': 'Failed'})
            if not(self.check_paymant(uid)):
                try:
                    self.edit_message_reply_markup(message_id=callback_query.message.chat.id, reply_markup='')
                except:
                    pass
                return None
            self.__add_to_log(uid, {'command': 'nextl'})

            curr_lesson = int(self.data_table.getFieldValue(uid, 'curr_lesson'))
            self.data_table.setFieldValues(uid, [curr_lesson+1, 1], ['curr_lesson', 'lessons_at_once'])

            goback_callback_button(callback_query)

        @self.callback_query_handler(func=lambda c: c.data.startswith('tch'))
        def startlsn_callback_button(callback_query: types.CallbackQuery):
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
                res = None
                try:
                    res = super().send_message(cid, *args[1:], **kwargs)
                    results.append(res)
                except:
                    results.append(res)
        else:
            results=super().send_message(chat_ids, *args[1:], **kwargs)

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

            cid = uid
            command = ''
            try:
                try:
                    self.logfile.write(str(uid) + ': ' + '; does: ' + str(args[0].data) + '.')
                except:
                    self.logfile.write(str(uid) + ': ' + '; does: ' + str(args[0].text) + '.')
                if type(args[0]) == telebot.types.CallbackQuery:
                    cid = args[0].message.chat.id
                    command = args[0].data.split(';')[0]

                elif type(args[0]) == telebot.types.Message:
                    cid = args[0].chat.id
                    command = args[0].text.split(';')[0]

                #if uid in self.bot_state['chiefid']:
                #    self.log_list[uid]['role'] = 'teacher'
                #    self.log_list[uid]['username'] = args[0].from_user.username

                res = function_to_decorate(*args)
                #self.log_list[uid]['result'] = 'Success'

            except Exception as err:
                print(err)
                self.spam_message = None
                if cid in self.user_chat_id:
                    self.__add_to_log(self.__find_keys(self.user_chat_id, cid), {'exit': 'Failed', 'error':err, 'command': command})
                else:
                    self.__add_to_log(uid, {'exit': 'Failed', 'error': err, 'command': command})
                #self.logfile.write('Error! ' + str(err) + '\n')
                #self.log_list[uid]['error'] = str(err)
                res = None

            self.logfile.flush()
            self.now_processing_id = -1
            try:
                self.data_table.addLogEntity(self.log_list)
            except Exception as e:
                pass
            self.log_list = {}
            return res
        return wrapper

    def show_cell(self, cid, cell):
        print('show cell')
        _id = cid
        msg = self.data_table.getValueFromStr(cell)[0][0]
        content = tp.parseMessage(msg, '')
        #msgs = content['content']
        for i in range(len(content)):
            m = content[i]['content']
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
                        m[0] = m[0].replace('https://dl.dropboxusercontent.com/','https://www.dropbox.com/')
                        self.send_message(_id, m[0])
                elif mtype == tp.MSG_TYPE.audio:
                    self.send_audio(_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.audionote:
                    self.send_voice(_id, m[0])
            except Exception as err:
                print('Err in msg sending: ' + str(err))
                self.send_message(_id, m[0], reply_markup=mrk)

        pass

    def anonMessageSend(self, dst_id, uid, content):
        markup = []
        for i in range(len(content)):
            if len(content[i]['buttons']) > 0:
                markup.append(types.InlineKeyboardMarkup(row_width=2))
                for b in content[i]['buttons']:
                    markup[-1].add(b)
            else:
                markup.append(None)

        for i in range(len(content)):
            m = content[i]['content']
            mrk = markup[i]

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
                    self.send_message(dst_id, corr_m, reply_markup=mrk,
                                      parse_mode='html')  # TODO define abstract class MSG sending an apppropriate type of msg (method send())
                elif mtype == tp.MSG_TYPE.gallery:
                    gal = [telebot.types.InputMediaPhoto(p) for p in content[i]['content'][0]]
                    self.send_media_group(dst_id, gal)
                elif mtype == tp.MSG_TYPE.image:
                    self.send_photo(dst_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.video:
                    try:
                        self.send_video(dst_id, m[0], reply_markup=mrk)
                    except:
                        corr_url = m[0].replace('https://dl.dropboxusercontent.com/', 'https://www.dropbox.com/')
                        self.send_message(dst_id, corr_url)
                elif mtype == tp.MSG_TYPE.audio:
                    self.send_audio(dst_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.audionote:
                    self.send_voice(dst_id, m[0])
            except Exception as err:
                if err.description == "Forbidden: bot was blocked by the user":
                    return False, 'Blocked'
                try:
                    self.send_message(dst_id, m[0], reply_markup=mrk)
                except:
                    print('Err in sendcold: ' + str(dst_id) + ': ' + str(err) + '. Continue spam sending...')
        return True, 'Success'
        pass
    def init_state(self, _id=-1):
        print('init_state')
        all_pupils = self.data_table.getAllValue('pupils')
        id_index = all_pupils[0].index('id')
        chat_id_index = all_pupils[0].index('chat_id')
        cell_index = all_pupils[0].index('status')
        schedule_index = all_pupils[0].index('delayed_event')
        reminder_index = all_pupils[0].index('reminder')
        frozen_index = all_pupils[0].index('freeze')

        ids = [int(row[id_index]) for row in all_pupils[4:]]
        chat_ids = [int(row[chat_id_index]) for row in all_pupils[4:]]
        cell_ids = [row[cell_index] for row in all_pupils[4:]]
        schedule = [row[schedule_index] for row in all_pupils[4:]]
        frozen   = [row[frozen_index] for row in all_pupils[4:]]
        reminders = [row[reminder_index] for row in all_pupils[4:]]

        for i in range(len(ids)):
            if ids[i]!=_id and _id!=-1:
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
                if not(sch_data[0] == ''):
                    self.schedule[ids[i]] = {'time': datetime.fromisoformat(sch_data[0]), 'cell': sch_data[1]}
            except Exception as err:
                print('Err in time decoding: init_state:' + str(err))
                pass

            try:
                sch_data = reminders[i].split(';')
                if not(sch_data[0] == ''):
                    self.reminders[ids[i]] = {'time': datetime.fromisoformat(sch_data[0]), 'cell': sch_data[1]}
            except Exception as err:
                print('Err in time decoding: init_state:' + str(err))
                pass

        for uid in ids:
            if _id == -1 or uid == _id:
                tmp_rem = self.reminders.pop(uid, None)
                self.read_from_cell(uid)
                if not(tmp_rem is None):
                    self.reminders[uid] = tmp_rem
                    self.data_table.setFieldValue(uid, str(tmp_rem['time'].isoformat()) + ';' + tmp_rem['cell'], 'reminder')
        pass

    def checkFast(self):
        for ch in self.tmp_msg_kill:
            self.delete_message(chat_id=ch, message_id=self.tmp_msg_kill[ch])
        self.tmp_msg_kill={}
    pass

    def checkSchedule(self):
        threading.Timer(60.0, self.checkSchedule).start()
        print('checkSchedule')
        for uid in list(self.schedule.keys()):
            if not(uid in self.schedule):
                continue
            evnt = self.schedule[uid]
            if evnt is None:
                continue
            if evnt['time'] <= datetime.utcnow():
                if self.user_frozen[uid]:
                    continue

                chat_id = uid
                if uid in self.user_chat_id and self.user_chat_id[uid] < -1:
                    chat_id = self.user_chat_id[uid]

                self.__add_to_log(uid, {'dptr':self.user_cell_position[uid], 'dest': evnt['cell'],
                                           'status':self.user_cell_position[uid], 'exit': 'Failed'})#TODO replace by goahead

                self.user_cell_position[uid] = evnt['cell']
                try:
                    self.say_hello(uid, chat_id)
                except:
                    pass
                curr_lsn = int(self.data_table.getFieldValue(uid, 'curr_lesson')) + 1
                self.__savestatus(uid, self.user_cell_position[uid], [curr_lsn, 1], ['curr_lesson', 'lessons_at_once'])
                self.data_table.setFieldValue(uid, '', 'reminder')
                self.reminders.pop(uid, '')
                self.cleanSchedule(uid)
                self.data_table.forceWrite()
                self.__add_to_log(uid, {'exit': 'Success'})
                try:
                    self.data_table.addLogEntity(self.log_list)
                except:
                    pass

        for uid in list(self.reminders.keys()):
            evnt = self.reminders.get(uid, None)
            if evnt is None:
                continue
            if evnt['time'] <= datetime.utcnow():
                if self.user_frozen[uid]:
                    continue

                chat_id = uid
                if uid in self.user_chat_id and int(self.user_chat_id[uid]) < -1:
                    chat_id = self.user_chat_id[uid]

                try:
                    self.show_cell(chat_id, evnt['cell'])
                except:
                    pass

                self.data_table.setFieldValue(uid, '', 'reminder')
                self.reminders.pop(uid, None)
        pass

    def cleanSchedule(self, uid):
        self.data_table.setFieldValue(uid, '', 'delayed_event')
        self.schedule.pop(uid, '')

    def cleanReminders(self, uid):
        self.reminders.pop(int(uid), None)
        self.data_table.setFieldValue(int(uid), '', 'reminder')

    def start_lesson(self, uid, chat_id, message):
        print('start_lesson')
        self.__add_to_log(uid, {'command':'/savechannel', 'exit':'Success'})
        self.data_table.allUpdate()

        record   = self.data_table.getPupilStatus(uid)
        reference = self.data_table.getPupilStruct(sheetName='test_results', rng='C1:BZ4')

        result_A1 = record.pop('result_A1', 0)
        result_A2 = record.pop('result_A2', 0)
        result_B1 = record.pop('result_B1', 0)
        result_B2 = record.pop('result_B2', 0)

        if result_A1 =='' or result_A1 is None:
            result_A1 = 0
        if result_A2 =='' or result_A2 is None:
            result_A2 = 0
        if result_B1 =='' or result_B1 is None:
            result_B1 = 0
        if result_B2 =='' or result_B2 is None:
            result_B2 = 0

        mistakes = []
        saitpas = []

        answers = {}

        for f in reference.keys():
            if re.match('[A|B][1|2]_\d+', f):
                answers[f] = record.get(f,'')

        questions_addr = []
        for a in answers:
            questions_addr.append(reference[a]['source'])

        questions = self.data_table.getValuesFromStr(questions_addr)

        for i in range(len(questions)):
            questions[i] =  tp.getMessageText(questions[i])[0]


        for a,q in zip(answers, questions):
            if answers[a].strip() == 'не знаю':
                saitpas.append(q + '\n' + reference[a]['regex'])
                answers[a] = ''

        for a,q in zip(answers, questions):
            r = reference.pop(a, '')
            if r == '':
                continue
            if re.match(r['regex'], answers[a]) is None and answers[a] != '':
                mistakes.append(
                    q + '\n' + '<strike>' + answers[a] + '</strike> ' + '\n' + r['regex'])


        txt = '🤖 это наш чат для обучения итальянскому от <b>Langusto!</b>\n'
        if int(result_A1) == 0:
            self.data_table.setFieldValue(uid, 'A1', 'level')

        #self.data_table.setFieldValues(uid, [1, 1], ['curr_lesson', 'lessons_at_once'])
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
            if len(mistakes) > 0:
                self.send_message(chat_id, '🔶Ошибки:🔶 ', parse_mode='html')
                txt = '\n\n'.join(mistakes)
                self.send_message(chat_id, txt, parse_mode='html')

            if len(saitpas) > 0:
                self.send_message(chat_id, '🔷Вопросы без ответов:🔷 ', parse_mode='html')
                txt = '\n\n'.join(saitpas)
                self.send_message(chat_id, txt, parse_mode='html')

            txt = ''

            txt += '\nЭти кнопки для преподавателя, если их нажимать, ничего не произойдет.'
            txt += '\n'
            markup = types.InlineKeyboardMarkup(row_width=2)
            callback = 'tch;' + 'A1' + ';' + self.user_cell_position[uid] + ';' + 'intro!A7'
            markup.add(types.InlineKeyboardButton('A1', callback_data=callback))
            callback = 'tch;' + 'A2' + ';' + self.user_cell_position[uid] + ';' + 'intro!B7'
            markup.add(types.InlineKeyboardButton('A2', callback_data=callback))
            callback = 'tch;' + 'B1' + ';' + self.user_cell_position[uid] + ';' + 'intro!C7'
            markup.add(types.InlineKeyboardButton('B1', callback_data=callback))
            callback = 'tch;' + 'B2' + ';' + self.user_cell_position[uid] + ';' + 'intro!D7'
            markup.add(types.InlineKeyboardButton('B2', callback_data=callback))
            self.send_message(chat_id, txt, parse_mode='html', reply_markup=markup)
        elif level == 'A1':
            message.from_user.id = uid
            message.chat.id = chat_id

            addr = self.user_cell_position[uid]
            '''
            txt += 'Через минуту, здесь появится первый урок...\n'
            txt += 'Да, не через секунду, а именно через МИНУТУ!\n'
            txt += '\n'
            '''
            self.send_message(chat_id, txt, parse_mode='html')
            try:
                self.goahead(message, self.user_cell_position[uid], addr)
            except Exception as err:
                print(str(uid) + ': Error in start_lesson: ' + str(err))
                self.user_cell_position[uid] = addr
                self.__add_to_log(uid, {'exit': 'Failed', 'error':err})
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
            overdue = ((period - ((datetime.utcnow().date() - when.date()).days))<=0)

        if overdue:
            self.send_message(self.user_chat_id[uid], 'Срок прохождения курса истек.')
            self.data_table.setFieldValue(uid, stat['curr_lesson'], 'lesson_num')

        if int(stat['curr_lesson'])>=int(stat['lesson_num']):
            self.send_message(self.user_chat_id[uid], 'Для перехода к следующему уроку нужно оплатить курс.')
            self.pay_request(uid, stat.get('score',0))
            return False
        return True

    def pay_online_request(self, uid, score = 0):
        print('pay_online_request')
        markup = types.InlineKeyboardMarkup(row_width=2)
        user_status = self.user_cell_position[uid]
        cid = self.user_chat_id[uid]
        txt  = 'Для оплаты перейдите по ссылке:'
        url = 'https://langusto.online/zapis2024'
        markup.add((types.InlineKeyboardButton('Оплатить курс 🤑', url=url)))
        callback = 'paid;' + 'Оплачено;' + user_status + ';' + user_status
        markup.add((types.InlineKeyboardButton('Оплачено👌', callback_data=callback)))
        callback = 'unch;' + 'Назад;' + user_status + ';' + user_status
        markup.add((types.InlineKeyboardButton('Назад', callback_data=callback)))
        self.send_message(cid, txt, reply_markup=markup, parse_mode='html')
        return True

    def pay_request(self, uid, score = 0):
        print('pay_request')
        markup = types.InlineKeyboardMarkup(row_width=2)
        user_status = self.user_cell_position[uid]
        cid = self.user_chat_id[uid]
        txt  = 'Есть несколько опций на выбор: '
        '''
        txt += 'цена указана <b>без учета скидки</b>.\n'
        txt += 'У вас на счету <b>' + str(score) + ' баллов</b>\n'
        txt += 'Скидка равна <b>' + str(int(score)*10) + ' рублей</b>\n'
        '''

        for k_opt in commands.PAY_OPTIONS.options.keys():
            if not (commands.PAY_OPTIONS.options[k_opt]['active']):
                continue
            callback = 'pay;' + user_status + ';' + user_status + ';' + k_opt
            markup.add(types.InlineKeyboardButton(commands.PAY_OPTIONS.options[k_opt]['button'], callback_data=callback))

        callback = 'pay;' + user_status + ';' + user_status + ';' + 'onl'
        markup.add(types.InlineKeyboardButton('Больше опций', callback_data=callback))

        self.send_message(cid, txt, reply_markup=markup, parse_mode='html')

        return True

    def conditon_processor(self, message, addr):
        chat_id = message.chat.id
        conditions = []
        if chat_id in self.conditions:
            conditions = self.conditions[chat_id]
        for uc in conditions:
            self.data_table.forceWrite()
            if(uc[0][:5] == 'check'):
                cnt = uc[0]
                ref = re.findall('check:\?\?\?(.+)\?\?\?', cnt)[0]
                val = self.data_table.getFieldValue(message.from_user.id, ref, force=True)
                result = eval(cnt[6:].replace('???' + ref + '???', val).strip())
                if result:
                    return None
                else:
                    addr[0] = uc[1]
        pass

        for uc in conditions:
            if(uc[0][:3] == 'set'):
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

        if not(cmd_is_found) and message.text[0] != '/':
            return True

        self.__add_to_log(uid, {'command': cmd})
        if not(cmd_is_found):
            self.__add_to_log(uid, {'error': 'WrongCommand', 'exit': 'Failed'})
            return False

        if cmd == 'le_risposte':
            pass

        if cmd == 'controlla':
            link = self.create_chat_invite_link(int(self.user_chat_id[uid])).invite_link
            result = self.send_message(self.bot_state['chiefid'], '🟡 Запрос на проверку урока: \n' + link)
            print(result)
            now = datetime.utcnow()
            all_chat_ids = ','.join([str(res.chat.id) for res in result])
            all_msg_ids  = ','.join([str(res.message_id) for res in result])
            self.data_table.setFieldValue(uid, all_chat_ids + ';' + all_msg_ids + ';' + str(
                now.isoformat()), 'call_message_id')
            self.data_table.setFieldValue(uid, link, 'chat_link')

        if cmd == 'prossima':
            if not(self.check_paymant(uid)):
                addr[0] = None
                return True

            payment_info = self.data_table.getFieldValue(uid, 'payment_info')
            if payment_info == '' or payment_info is None:
                self.send_message(chat_id, '🤖 Опция недоступна на ознакомительном периоде.')
                addr[0] = None
                return True

            stat = self.data_table.getPupilStatus(uid)
            extra_lesson_num = int(stat['lessons_at_once'])
            curr_lsn         = int(stat[    'curr_lesson'])
            if extra_lesson_num<3:
                extra_lesson_num += 1
                self.data_table.setFieldValues(uid, [curr_lsn+1, extra_lesson_num, ''], ['curr_lesson','lessons_at_once','delayed_event'])
                self.cleanSchedule(uid)
            else:
                self.send_message(chat_id, 'Нельзы получить больше уроков вне очереди.')
                self.__add_to_log(uid, {'error': 'TooManyProssima'})
                addr[0] = None
                return True
            self.send_message(chat_id, 'Получено уроков <b>вне очереди: ' + str(extra_lesson_num) + '</b>', parse_mode='html')
        self.__add_to_log(uid, {'exit': 'Succes'})
        return True

    def teacher_command_processor(self, message, addr):
        tid = message.from_user.id
        chat_id = message.chat.id
        uid = self.__find_keys(self.user_chat_id, chat_id)[0]
        cmd = self.__extract_command(message.text)

        if cmd=='' and message.text[0]!='/':
            return True

        if message.text[0] != '':
            for tc in self.teacher_command[chat_id]:
                if cmd == tc[0]:
                    addr[0] = tc[1]
        else:
            return False

        self.__add_to_log(uid, {'command': cmd})
        self.__add_to_log(uid, {'teacher': tid})

        try:
            if cmd == 'controllato':
                if tid in self.bot_state['chiefid']:
                    call_msg = self.data_table.getFieldValue(chat_id, 'call_message_id', key_column='chat_id')
                    if not(call_msg is None or call_msg==''):
                        call_chat_id, call_msg_id, when = call_msg.split(';')
                        chat_ids = call_chat_id.split(',')
                        msg_ids  = call_msg_id .split(',')
                        for c_id, m_id in zip(chat_ids, msg_ids):
                            try:
                                link = self.data_table.getFieldValue(uid, 'chat_link')
                                self.edit_message_text('✅ Урок <b>проверен</b> в чате:\n' + str(link), chat_id=int(c_id), message_id=int(m_id), parse_mode='html')
                            except:
                                pass

                    self.data_table.setFieldValue(chat_id, '', 'call_message_id', key_column='chat_id')
                else:
                    return False

            if cmd == 'le_risposte':
                try:
                    self.log_list.pop(uid,None)
                    msg = self.data_table.getValueFromStr(addr[0])[0][0]
                    content = tp.parseMessage(msg)
                    msgs = content[0]['content'][0]
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(types.InlineKeyboardButton('***', switch_inline_query_current_chat=msgs))
                    result = self.send_message(chat_id, '***', reply_markup=markup)
                    addr[0] = None
                    self.tmp_msg_await[chat_id]=tid
                    self.tmp_msg_kill [chat_id]=result.message_id
                    threading.Timer(3.0, self.checkFast).start()
                    return True
                except:
                    addr[0] = None
                    return True

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
                    self.cleanSchedule(uid)
                else:
                    self.send_message(chat_id, 'Нельзы получить больше уроков вне очереди.')
                    self.__add_to_log(uid, {'error': 'TooManyProssima'})
                    addr[0] = None
                    return True
                self.send_message(chat_id, 'Получено уроков <b>вне очереди: ' + str(extra_lesson_num) + '</b>',
                                  parse_mode='html')
            self.__add_to_log(uid, {'exit': 'Success'})
            return True

        except Exception as e:
            print('Error in teacher_command_processor: ' + str(e))
            self.__add_to_log(uid, {'error': str(e), 'exit': 'Success'})
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

        role = None
        if uid in self.user_cell_position:
            role = 'pupil'
        elif uid in self.bot_state['chiefid']:
            role = 'teacher'


        if chat_id in self.tmp_msg_await:
            if self.tmp_msg_await[chat_id] == uid:
                self.delete_message(chat_id=chat_id, message_id=message.message_id)
                self.tmp_msg_await.pop(chat_id)

        addr = [None]

        if uid in self.user_command and len(self.user_command[uid])>0 and role == 'pupil':
            if not (self.user_command_processor(message, addr)):  # reading of next cell address here
                self.wrong_command_report(message)
                self.read_from_cell(uid)
                return None

        if chat_id in self.teacher_command and len(self.teacher_command[chat_id])>0 and role == 'teacher':
            if not (self.teacher_command_processor(message, addr)):  # reading of next cell address here
                self.wrong_command_report(message)
                self.read_from_cell(uid)
                return None

        if addr[0] == None:
            return None

        self.send_chat_action(chat_id, 'typing')
        if chat_id==uid and self.user_chat_id[uid]!=-1:
            self.send_message(chat_id, "Перейдите у групповой чат, чтоб продолжить обучение. \n/status чтоб получить ссылку на чат.")
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

    def goahead(self, message, dptr, addr, demo=False):  # processing of an incoming message
        print('goahead')

        uid = message.from_user.id
        chat_id = message.chat.id

        if not(addr):
            addr = dptr

        if 'chiefid' in self.bot_state and message.from_user.id in self.bot_state['chiefid']:
            pupil_id = self.__find_keys(self.user_chat_id, chat_id)
            if not pupil_id:
                pass
            else:
                uid = pupil_id[0]

        self.__add_to_log(uid, {
                                     'status': self.user_cell_position[uid],
                                     'dptr':dptr,
                                     'dest': addr,
                                     'last_activity_date': str(datetime.now(timezone.utc).isoformat()),
                                     'exit': 'Failed'
                                    })

        self.send_chat_action(chat_id, 'typing')
        cmd = ''

        if not (uid in self.user_cell_position):
            self.user_cell_position[uid] = dptr
        if (not (self.user_cell_position[uid] == dptr) and not(demo)):
            self.__add_to_log(uid, {'exit': 'WrongLink'})
            return None

        # update user status in the chat
        if self.user_cell_position[uid] in self.data_dstn and message.from_user.is_bot == False:
            field_name = self.data_dstn[self.user_cell_position[uid]]
            self.data_table.setFieldValue(uid, tp.cleanMessage(message.text, self.user.username), field_name)
            print('Message to be logged: ' + message.text)

        addrl = [addr]
        self.conditon_processor(message, addrl)
        addr = addrl[0]

        # update user status in the chat
        self.user_cell_position[uid] = addr  # jumping to the next cell in user status

        self.__add_to_log(uid, {'dest': addr})
        try:
            if not demo:
                self.__savestatus(uid, self.user_cell_position[uid])  # saving status (cell id where the user is)
        except Exception as err:
            print('Errr in __savestatus: ' + str(err))

        self.cleanReminders(uid)
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
            #self.send_message(_id, 'Что-то сломалось(( Когда починят, придет уведомление')
            if uid in self.user_cell_position:
                print('Error in table reading, desired range: ' + self.user_cell_position[uid])
            else:
                print('Key error in table reading: ' + str(uid))
            print(err)
            return None

        content = tp.parseMessageFast(msg)
        for c in content:
            self.__createKeyFromContent(uid, _id, c['buttons'], passive = True)


    def say_hello(self, user_id, chat_id=-1):  # sending of a reply message
        print('sayhello')

        if int(chat_id) == -1:
            chat_id = user_id
        uid = int(user_id)
        _id = int(chat_id)
        self.send_chat_action(_id, 'typing')

        markup = []  # , one_time_keyboard=True, resize_keyboard=True)
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
        for i in range(len(content)):
            content[i]['buttons'] = self.__createKeyFromContent(uid, _id, content[i]['buttons'])

        for i in range(len(content)):
            if len(content[i]['buttons'])>0:
                markup.append(types.InlineKeyboardMarkup(row_width=2))
                for b in content[i]['buttons']:
                    markup[-1].add(b)
            else:
                markup.append(None)

        for i in range(len(content)):
            m   = content[i]['content']
            mrk = markup[i]

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
                elif mtype == tp.MSG_TYPE.gallery:
                    gal = [telebot.types.InputMediaPhoto(p) for p in content[i]['content'][0]]
                    self.send_media_group(_id, gal)
                elif mtype == tp.MSG_TYPE.image:
                    self.send_photo(_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.video:
                    try:
                        self.send_video(_id, m[0], reply_markup=mrk)
                    except:
                        corr_url = m[0].replace('https://dl.dropboxusercontent.com/','https://www.dropbox.com/')
                        self.send_message(_id, corr_url)
                elif mtype == tp.MSG_TYPE.audio:
                    self.send_audio(_id, m[0], reply_markup=mrk)
                elif mtype == tp.MSG_TYPE.audionote:
                    self.send_voice(_id, m[0])
            except Exception as err:
                self.send_message(_id, m[0], reply_markup=mrk)
                self.__add_to_log(uid, {'exit': 'Warning', 'error':str(err)})
                print('Err in sayhello: ' + str(err))

        self.__add_to_log(uid,{'exit':'Success'})
        try:
            self.data_table.addLogEntity(self.log_list)
        except:
            pass
        self.log_list = {}
        pass

    def create_lesson_chat(self, addr, pupil_user):
        participants = [self.user.username, *self.bot_state['chiefname'], str(pupil_user.id)]
        txt = commands.SCOMMANDS.create_a_chat + ';' + str(addr) +';' +';'.join(participants)
        tmp_msg = self.send_message(self.bot_state['chiefid'], txt)
        for tm in tmp_msg:
            #time.sleep(3)
            self.delete_message(chat_id=tm.chat.id, message_id=tm.id)
        pass

    def pay_command(self, chat_id, dptr, addr, subscribe_id):
        print('pay_command')

        _markup = types.InlineKeyboardMarkup(row_width=2)
        callback = 'unch;' + 'Назад' + ';' + dptr + ';' + dptr

        #discont = self.data_table.getFieldValue(chat_id, 'score', key_column='chat_id')
        #discont = int(discont)*100

        payment_info = commands.PAY_OPTIONS.options[subscribe_id]

        _markup.add(types.InlineKeyboardButton('Оплатить ' + str(int(payment_info['price'].amount / 100)) + ' руб', pay=True))
        _markup.add(types.InlineKeyboardButton('Назад', callback_data=callback))

        self.send_invoice(chat_id,
                          title=payment_info['price'].label,
                          description=payment_info['dscr'],
                          provider_token=self.PAYMENT_TOCKEN,
                          currency="rub",is_flexible=False,
                          prices=[payment_info['price']],
                          start_parameter=payment_info['start_parameter'],
                          invoice_payload=payment_info['invoice_payload'],
                          photo_url=payment_info['photo_url'],
                          photo_height=payment_info['photo_height'],
                          photo_width=payment_info['photo_width'],
                          photo_size=payment_info['photo_size'],
                          reply_markup=_markup)
        pass

    def run(self):
        while True:
            try:
                self.polling(none_stop=True, interval=1, skip_pending=True)
            except Exception as e:
                print(str(e))
                time.sleep(15)

    def __add_to_log(self, uid, dict):
        uid = int(uid)
        if not(uid in self.log_list):
            self.log_list[uid] = {}
        self.log_list[uid] = {**self.log_list[uid], **dict}
        pass
    def __find_keys(self, d, value):
        return [key for key, x in d.items() if str(x) == str(value)]

    def __extract_command(self, msg):
        z = re.match('//([a-zA-Z0-9-_]+)@?\.*', msg)
        if not (z):
            return ''
        return z.groups()[0]
        pass

    def __savestatus(self, id, status, more_val=[], more_fields=[]):
        self.data_table.setFieldValues(id, [status, str(datetime.utcnow().isoformat()), *more_val], ['status', 'last_activity_date', *more_fields])


    def __createKeyFromContent(self, id, chat_id, content, passive = False):

        self.user_command[id] = []#.pop(id, None)
        self.teacher_command[chat_id] = []#.pop(chat_id, None)
        self.conditions[chat_id] = []

        btns = []
        user_status = self.user_cell_position[id]
        open_input_flad = 0
        for b in content:
            cond = True
            title, addr, sp = b[:3]
            if len(b)>3 and not(b[3] is None) and b[3]>'':
                cond = tp.parseExecValue(b[3], lambda x: self.data_table.getFieldValue(id, x))
            try:
                if not(eval(str(cond))):
                    continue
            except:
                print('Error in reading command ' + str(content) + ' for ' + str(id))
                pass

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
                #btns.append(None)
                self.conditions[chat_id].append(['check:' + title, addr])
                pass
            if sp.split(':')[0] == '/reminder' and not(passive):
                if id in self.reminders:
                    continue
                _when = datetime.utcnow() + dt.timedelta(minutes=3)
                _when = datetime.utcnow() + dt.timedelta(minutes=int(sp.split(':')[1]))  # TODO comment here for debug
                event_stamp = str(_when.isoformat()) + ';' + addr
                self.data_table.setFieldValue(id, event_stamp, 'reminder')
                self.reminders[id] = {'time': _when, 'cell': addr}
                pass
            if sp == '/set':
                #btns.append(None)
                self.conditions[chat_id].append(['set;' + title, addr])
                pass

            if sp == '/ucommand':
                cmd = self.__extract_command(title)
                #btns.append(None)
                self.user_command[id].append([cmd, addr])
            if sp == '/tcommand':
                cmd = self.__extract_command(title)
                #btns.append(None)
                self.teacher_command[chat_id].append([cmd, addr])
            if sp == '/tomorrow':
                callback = 'tomorrow;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
            if sp == '/back':
                callback = 'unch;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
            if sp == '/nextl':
                callback = 'nextl;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
            if sp == '/check':
                callback = 'chk;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
            if sp == '/url':
                btns.append(types.InlineKeyboardButton(title, url=addr))
            if sp is None or sp == '':
                callback = 'chng;' + title + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
        return btns

    def __anonKeyFromContent(self, content, targetCell):
        btns = []
        #user_status = self.user_cell_position[uid]
        #self.user_cell_position[uid] = targetCell
        open_input_flad = 0
        for b in content:
            title, addr, sp = b[:3]
            title = title.strip()
            if sp == '/url':
                btns.append(types.InlineKeyboardButton(title, url=addr))
            if sp is None or sp == '':
                callback = 'demo;' + title + ';' + targetCell + ';' + addr
                btns.append(types.InlineKeyboardButton(title, callback_data=callback))
        return btns

    def __check_user(self, id):
        pupils = self.data_table.getAllPupilColumns(['id', 'status', 'chat_id'])
        id = str(id)
        if id in pupils[0]:
            j = pupils[0].index(id)
            return {int(id): pupils[1][j]}, {int(id): int(pupils[2][j])}
        else:
            return None

    def __check_user_info(self, id):  # TODO Add checking of fullness of the user info
        header, record = self.data_table.getAllFieldValue(id)
        for h, u in zip(header[2], record):
            try:
                if int(h) == 1:
                    pass
                    if u == '' or u == None:
                        return False
            except:
                continue

        ind = header[0].index('chat_id')
        try:
            if int(record[ind]) != -1:
                self.user_chat_id[id] = int(record[ind])
                return False
        except:
            pass
        return True

    def __create_user(self, pupil_dict, user_dscr):
        user_dict = {}
        user_tmp_dict = eval(str(user_dscr))
        for k in pupil_dict.keys():
            if pupil_dict[k]['defval']:
                user_dict[k] = pupil_dict[k]['defval']
        user_dict['last_activity_date'] = str(datetime.now(timezone.utc).isoformat())

        for k in pupil_dict.keys():
            if pupil_dict[k]['source'] in user_tmp_dict.keys():
                user_dict[k] = user_tmp_dict[pupil_dict[k]['source']]

        if user_dict['id'] in self.user_cell_position:
            user_dict['status'] = self.user_cell_position[user_dict['id']]

        self.user_chat_id[int(user_dict['id'])] = user_dict['chat_id']
        self.user_frozen [int(user_dict['id'])] = False
        self.user_cell_position[int(user_dict['id'])] = user_dict['status']
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

