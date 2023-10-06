import telebot
from telebot import apihelper
from telebot import types
import re
import calendar
import datetime
import itertools
import logging
import json
import requests

import googleSheetTest
import spectialKeys

'''
@bot.channel_post_handler(content_types=["text", "audio", "photo", "video"])
def greeting(message):
    print("!!!!!!!!!")
    print(message)
    bot.send_message(message.from_user.id, 'Привет, добро пожаловать в наш канал!')
'''


class SurveyBot(telebot.TeleBot):
    introduction_dict = {}
    survey_dict       = {}
    pupils            = []

    data_table = None

    intro_msgs = []
    user_status  = {}
    user_expected_info    = {}
    #user_last_msg = {}

    mystate = {}

    def __init__(self, bot_token, data_table):
        super().__init__(bot_token)

        self.bot_state_filepath = 'resources\\' + self.user.username + '.json'

        try:
            state_f = open(self.bot_state_filepath, 'r')
            self.mystate = json.load(state_f)
        except:
            pass

        self.survey_dict = {}
        self.data_dstn   = {}
        #self.pupils      = pupils

        self.data_table = data_table
        self.survey_dict = self.data_table.getPupilStruct(sheetName='pupils')
        self.__invert_datasource_link(self.survey_dict)

        @self.message_handler(commands=['trial'])
        def try_command(message):
            markup = types.InlineKeyboardMarkup(row_width=2)  # , one_time_keyboard=True, resize_keyboard=True)
            key_b = types.InlineKeyboardButton('Text of btn', switch_inline_query_current_chat='Text to edit')
            markup.add(key_b)
            self.send_message(message.from_user.id, 'Bla-bla-bla', reply_markup=markup)
            #self.register_next_step_handler(message, callback_button)

            #msg = self.send_message(message.chat.id, 'Text')
            #self.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text='Edited text')
            pass

        @self.message_handler(commands=['vai_lezioni'])
        def try_command(message):
            markup = types.InlineKeyboardMarkup(row_width=2)  # , one_time_keyboard=True, resize_keyboard=True)
            #self.send_message(message.from_user.id, 'A.... зто... уроки еще не готовы. Спокойно, целая ночь впереди!', reply_markup=markup)

            if not ('chefid' in self.mystate) or int(self.mystate['chefid']) < 0:
                self.send_message(message.from_user.id, "Не могу создать урок, учитель не активировал опцию, поробуйте позже")
            else:
                if(self.__check_user_info(message.from_user.id)):
                    self.create_lesson_chat(message.from_user)
                else:
                    self.send_message(message.from_user.id,"Вы не закончили опрос")
                    self.send_message(message.from_user.id, '/start', reply_markup=markup)
            pass

        @self.message_handler(commands=['imyourchief'])
        def try_command(message):
            if message.from_user.username=='roro_tmp':
                self.send_message(message.from_user.id, "Your are chief, I was waiting for you!")
                self.mystate['chefid']   = message.from_user.id
                self.mystate['chiefname'] = message.from_user.username
            else:
                self.send_message(message.from_user.id, "Your username is wrong, you are not a chief")

            state_f = open(self.bot_state_filepath, 'w')
            json.dump(self.mystate, state_f)
            state_f.close()

        @self.message_handler(commands=['start'])
        def start_command(message):
            user = self.__check_user(message.from_user.id)
            if (user==None):
                self.user_status[message.from_user.id] = 'intro!A1'
            else:
                self.user_status = {**self.user_status, **user}

            self.say_hello(message)

        pass

        '''
        @self.inline_handler(func=lambda c: True)
        def process_update(inline_query):
            accept = types.InlineQueryResultArticle('Принять изменения', 'Принять изменения', types.InputTextMessageContent('hi'))
            r2 = types.InlineQueryResultArticle('2', 'Result2', types.InputTextMessageContent('hi'))
            self.answer_inline_query(inline_query.id, [accept] ,cache_time = 1)        
            print(inline_query)
            pass
        '''

        @self.callback_query_handler(func=lambda c: c.data.startswith('saveuser'))
        def newuser_callback_button(callback_query: types.CallbackQuery):
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
        def goback_callback_button(callback_query: types.CallbackQuery):
            print(callback_query)
            self.answer_callback_query(callback_query.id)
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

    def goahead(self, message, dptr, address):
        #print(message)
        print('goahead')

        uid = message.from_user.id
        if (not(self.user_status[uid] == dptr)):
            return None

        try:
            self.edit_message_reply_markup(message.chat.id, message_id=message.message_id-(message.from_user.username!=self.user.username), reply_markup='')
        except:
            pass

        message.text = message.text.replace('@'+self.user.username, '')
        message.text = message.text.strip()

        if self.user_status[uid] in self.data_dstn and message.from_user.is_bot == False:
            field_name = self.data_dstn[self.user_status[uid]]
            self.data_table.setFieldValue(message.text, uid, field_name)
            print('Message to be logged: ' + message.text)

        #if uid in self.user_expected_info and message.from_user.is_bot == False:
        #    field_name = self.data_dstn[self.user_expected_info.pop(uid)['source']]
        #    self.data_table.setFieldValue(message.text, uid, field_name)
        #    print('Message to be logged: ' + message.text)



        self.user_status[uid] = address
        self.__savestatus(uid, self.user_status[uid])
        self.say_hello(message)
        pass

    def say_hello(self, message):
        print('sayhello')
        uid = message.from_user.id
        markup = types.InlineKeyboardMarkup(row_width=2)#, one_time_keyboard=True, resize_keyboard=True)
        question_text = ['']
        try:
            msg = self.data_table.getValueFromStr(self.user_status[uid])[0][0]
        except Exception as err:
            self.send_message(uid, 'Что-то сломалось(( Для перезапуска наребирте /start', reply_markup=markup)
            if uid in self.user_status:
                print('Error in table reading, desired range: ' + self.user_status[uid])
            else:
                print('Key error in table reading: ' + str(uid))
            print(err)
            return None

        past_answer=''
        if(self.user_status[uid] in self.data_dstn):
            k = self.data_dstn[self.user_status[uid]]
            self.user_expected_info[uid] = self.survey_dict[k]
            fieldname = self.data_dstn[self.user_expected_info[uid]['source']]
            content = self.data_table.getFieldValue(uid, fieldname)
            if not(content is None):
                past_answer = '\n' + '<i>' + content + '</i>'


        content = self.__messageParser(msg)
        btns = self.__createKeyFromContent(uid, content)
        for i in range(len(btns)):
            if btns[i] is None:
                self.register_next_step_handler(message, self.goahead, self.user_status[uid], content[2][i])
            else:
                markup.add(btns[i])
                pass
        msgs = content[0]

        for m in reversed(msgs):
            if m[1]=='txt':
                m[0] = m[0] + past_answer

        for i in range(len(msgs)):
            m = msgs[i]
            mrk = None
            if i==len(msgs)-1:
                mrk = markup
            if m[1]=='txt':
                self.send_message(message.from_user.id, m[0], reply_markup=mrk, parse_mode='html')
                continue
            if 'image' in m[1]:
                self.send_photo(message.from_user.id, m[0], reply_markup=mrk)
                continue
            pass

        pass

    def create_lesson_chat(self, pupil_user):
        participants = [self.user.username, self.mystate['chiefname'], pupil_user.username]
        txt = '/create_a_channal;'+';'.join(participants)
        self.send_message(self.mystate['chefid'], txt)
        pass

    def run(self):
        self.polling(none_stop=True, interval=0)

    def __savestatus(self, id, status):

        pupils = self.data_table.getAllPupilColumns(['id'])[0]
        if str(id) in pupils:
            self.data_table.setFieldValue(status, id, 'status', sheetName='pupils')

    def __createKeyFromContent(self, id, content):
        btns = []
        user_status = self.user_status[id]
        open_input_flad = 0
        for b, addr, sp in zip(*content[1:]):
            if sp == '/input' and open_input_flad == 0:
                btns.append(None)
                open_input_flad += 1
                continue
            if sp == '/saveuser':
                callback = 'saveuser;' + '' + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(b, callback_data=callback))
                continue
            if sp == '/edit':
                if(id in self.user_expected_info):
                    fieldname = self.data_dstn[self.user_expected_info[id]['source']]
                    content   = self.data_table.getFieldValue(id, fieldname)
                    if content is None:
                        pass
                    else:
                        callback = 'unch;' + 'Ок' + ';' + user_status + ';' + addr
                        btns.append(types.InlineKeyboardButton(b, switch_inline_query_current_chat=content))
                        btns.append(types.InlineKeyboardButton('Ок', callback_data=callback))
                    pass
                pass
            if sp == '/delete_me':
                pass
            if sp == '/back':
                callback = 'unch;' + b + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(b, callback_data=callback))
            if sp is None or sp=='':
                callback = 'chng;' + b + ';' + user_status + ';' + addr
                btns.append(types.InlineKeyboardButton(b, callback_data=callback))
        return btns

    def __check_user(self, id):
        pupils = self.data_table.getAllPupilColumns(['id','status'])
        id = str(id)
        if id in str(pupils[0]):
            j = pupils[0].index(id)
            return {int(id): pupils[1][j]}
        else:
            return None

    def __check_user_info(self, id): #TODO Add checking of fullness of the user info
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
        user_dict['status'] = self.user_status[user_dict['id']]
        return user_dict

    def __invert_datasource_link(self, data_structure):
        for k in data_structure.keys():
            f = data_structure[k]
            result = re.match("(\w+![AZ]\d)", f['source'])
            if not(result is None):
                self.data_dstn[result.group(1)] = k
            pass

    def __messageParser(self, msg):
        texts = []
        text = msg
        urls = re.findall('https:\S+', msg)
        for url in urls:
            text = text.replace(url, '')
            r = requests.head(url, allow_redirects=True)
            ctype = r.headers['content-type']
            texts.append((url,ctype))

        buttons = re.findall("\[\[[^\]]+\]\]", text)
        next_step = []
        special = []
        for i in range(len(buttons)):
            text = text.replace(buttons[i], '')
            buttons[i] = buttons[i][2:-2]
            buttons[i].strip()

        text = text.strip()
        text = text.replace('\n', '%0A')
        text = ' '.join(text.split())
        text = text.replace('%0A', '\n')
        texts.append([text, 'txt'])
        for i in range(len(buttons)):
            b = buttons[i]
            details = b.split(';')
            next_step.append(details[1].strip())
            if len(details) > 2:
                special.append(details[2])
            else:
                special.append(None)
            buttons[i] = details[0]

        return [texts, buttons, next_step, special]


#bot.send_poll(message.chat.id, 'вопрос', options=['1', '2', '3'])



logger = telebot.logger
#telebot.logger.setLevel(logging.DEBUG)
#id = -1001911551721
#CHANNEL_NAME = '@tmp_langusto_channel'
#bot.send_message(id, "Как тебя зовут?")
print("Starting the program")

#bot = telebot.TeleBot("6490762220:AAGvcyX_YvSmeDkYcZw6oDSD0FjK4ayxlpc")

'''
chefid   = -1
pupil_id = -1


state_f = None
state_dict = {}
state_dict['pupils'] = []

try:
    state_f = open('teacherbot_statefile.json', 'r')
    state_dict = json.load(state_f)
    print("1")
except:
    state_f = open('teacherbot_statefile.json', 'w')
    json.dump(state_dict, state_f)

state_f.close()
'''

'''
@bot.message_handler(content_types=['text'])
def start(message):    
    if message.text == '/imchief':
        bot.send_message(message.from_user.id, "Your are cheif, ok");
        state_dict['chefid'] = message.from_user.id
        print("New chief_id: " + str(state_dict['chefid']))
    if message.text == '/reg':
        bot.send_message(message.from_user.id, "I don't have a chief yet, ask later");
    if message.text == '/createclass':
        if not('chefid' in state_dict) or int(state_dict['chefid'])<0:
            bot.send_message(message.from_user.id, "I don't have a chief yet, ask later");
        else:
            state_dict['pupils'].append(message.from_user.id)
            print("Pupils_id: " + str(state_dict['pupils']))
            bot.send_message(message.from_user.id, "Ok, I've sent a request")
            bot.send_message(state_dict['chefid'], "/create_group:" + message.from_user.username)
            #bot.register_next_step_handler(message, get_name); #следующий шаг – функция get_name

    state_f = open('teacherbot_statefile.json', 'w')
    json.dump(state_dict, state_f)
    state_f.close()
'''



def get_userstruct(user_dict):
    pass

def checkuser(uid, user_dict):
    return False
    pass
'''
@bot.message_handler(content_types=['text'])
def start(message):
    user_dict = {}
    if message.text == '/pupil':
        user_dict = get_userstruct(user_dict)
        uid = message.from_user.id
        if checkuser(uid):
            pass #process if user is existing
        else:
            user_dict['user_id'] = uid
            if(get_user_info.get_info(message, user_dict)):
                pass # if it is ok
            else:
                pass # user cancel or error
        pass
'''

def get_name(message): #получаем фамилию
    global name
    name = message.text
    bot.send_message(message.from_user.id, 'Какая у тебя фамилия?')
    bot.register_next_step_handler(message, get_surname)

def get_surname(message):
    global surname
    surname = message.text
    bot.send_message(message.from_user.id, 'Сколько тебе лет?')
    bot.register_next_step_handler(message, get_age)

def get_age(message):
    global age
    while age == 0: #проверяем что возраст изменился
        try:
             age = int(message.text) #проверяем, что возраст введен корректно
        except Exception:
             bot.send_message(message.from_user.id, 'Цифрами, пожалуйста')
        keyboard = types.InlineKeyboardMarkup() #наша клавиатура
        key_yes = types.InlineKeyboardButton(text='Да', callback_data='yes') #кнопка «Да»
        keyboard.add(key_yes) #добавляем кнопку в клавиатуру
        key_no= types.InlineKeyboardButton(text='Нет', callback_data='no')
        keyboard.add(key_no)
        question = 'Тебе '+str(age)+' лет, тебя зовут '+name+' '+surname+'?'
        bot.send_message(message.from_user.id, text=question, reply_markup=keyboard)
'''
@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    if call.data == "yes": #call.data это callback_data, которую мы указали при объявлении кнопки
        pass #код сохранения данных, или их обработки
        bot.send_message(call.message.chat.id, 'Запомню : )')
    elif call.data == "no":
        pass #переспрашиваем
'''

#bot.send_message(6604084268, "/create_group:" )

#print("My state:\n" + str(state_dict))

survey_table = googleSheetTest.GoogleTableReader('1A_s-2vCoTmf9ElTCPg9inH1FbuwIHp0JbIAPcrCnYdA')


survey_bot = SurveyBot("6490762220:AAGvcyX_YvSmeDkYcZw6oDSD0FjK4ayxlpc", survey_table)
survey_bot.run()

#marquer = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
#text = ''
#markupFromMessage(msg1, marquer, [text])

#state_f.close()

