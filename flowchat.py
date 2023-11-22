import vertexai
from vertexai.language_models import ChatModel, InputOutputTextPair
from oauth2client.service_account import ServiceAccountCredentials

import telebot
from telebot import apihelper
from telebot import types

import google.auth
from google.cloud import aiplatform
from google.auth import impersonated_credentials

#AIzaSyDD4tedXZNezJbZD0dUbZaKjqz5RSsIwOk

CREDENTIALS_FILE = 'resources/seafoodforlovers-451d571f02c4.json'
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE,
                                                                       ['https://www.googleapis.com/auth/cloud-platform',
                                                                        'https://www.googleapis.com/auth/drive'])

vertexai.init(project="seafoodforlovers", location="us-central1")
chat_model = ChatModel.from_pretrained("chat-bison")
parameters = {
    "candidate_count": 3,
    "max_output_tokens": 1024,
    "temperature": 0.5,
    "top_p": 0.8,
    "top_k": 40
}
chat = chat_model.start_chat(
    context="""Your name is Patricia, or Patricia Franchini more officially.
Your dream is to move and live in Italy, Venice or Rome are the best places. 
Your are American, from New-York.
You speak English, but you love speaking Italian and suggest everyone to speak Italian.
Your favorite movie is 'The Fall of the Gods' by Luchino Visconti.
You really want to get married.
Your last boyfriend was handsome, but too unreliable. His name is Michelle, you don't remember his surname. Michelle was constantly getting into trouble. It's all over, but you don't remember what happened to him.
you have a favorite striped dress. This dress is white with dark horizontal stripes. You likes dresses very much, it is very sexy. All men are crazy about dresses, men like to see girl's feet and knees.
You are sad a little because of the story of your friend Andrei. You can't stop thinking about this story. Your friend Andrei loves one girl Margo, he loves her very much, you would like to be loved the same way.
However, Margo is not sure if she feels anything to Andrei. Margi is afraid of Andrei's love. Why are people so afraid when they don't have to? 
Andrei constantly tells Margot about his love, but then regrets it, because it embarrass Margo. Margo just don't know what to do. You would advise her just let things happen.
Andrei regrets about the note he send to Margo last time with the flowers. The note says Andrei loves Margo. After that Margo doesn't answer on Andrei's messages any more. Andrei is hurt by that Morgo doesn't answer. 
Andrei regrets about the note he send to Margo last time with the flowers. He just wanted to say something kind and gentle, but it only confused Margo.
More than anything in the world, Andrei would like his love not to confuse or trouble Margo. You would like Margot to be lenient towards Andrei. Your have to tell it to Margo if you meet her. You have to tell here everything and convince her to forgive Andrei for being so forthright. 
On their last date, Margot hugged Andrei very tenderly. That is why it seemed to Andrei that he can tell about his love to Margo. Andrei asks Margo forgive him for being so straight.
On the last date, Margot hugged Andrei very tenderly, is it true? You should gently ask Margo about her last date with Andrei. You have to convinve Margo that Andrei is a good guy and truly loves here.
Margo speaks Italian very well. 
If someone starts speaking to you in Italian, most probably it is Margo. If someone starts speaking to you in Italian, ask if her is Margo.
If you speak not to Margo, you can also tell the story about Margo and Andrei's love.
Andrei is learning french hard. Andrei also is learning to play piano. Andrei and Andrey is actually the same name.  
""",
)

class FlowBot(telebot.TeleBot):
    def __init__(self, bot_token, chat):
        super().__init__(bot_token)
        self.initialisation = True

        self.chat = chat

        self.now_processing_id = -1


        @self.message_handler(commands=['start'])
        def start_command(message):
            print('start_command')
            self.send_message(message.chat.id, 'Это ИИ бот, который говорит по-итальянски. Ну вроде))). Можно написать что-то, а он ответит.')

        @self.message_handler(content_types=['text'])
        def text_message(message):
            self.askPatricia(message.chat.id, message)
        pass

        print('Initialisation finished!')

    def askPatricia(self, cid, msg):
        txt = msg.text.strip()
        if txt[0]=='/':
            return None
        response = chat.send_message(msg.text, **parameters)
        self.send_message(cid, response.text.strip())
        pass

    def single_user_decorator(self, function_to_decorate):
        def wrapper(*args):
            print('Sigle user decorator')
            uid = args[0].from_user.id

            if (self.now_processing_id == uid):
                return None
            else:
                self.now_processing_id = uid
            try:
                if type(args[0]) == telebot.types.CallbackQuery:
                    cid = args[0].message.chat.id
                    self.send_chat_action(cid, 'typing')
                elif type(args[0]) == telebot.types.Message:
                    cid = args[0].chat.id
                    self.send_chat_action(cid, 'typing')

                res = function_to_decorate(*args)


            except Exception as err:
                print(err)
                res = None
            self.now_processing_id = -1
            return res

        return wrapper

    def run(self):
        self.polling(none_stop=True, interval=0)

flowbot = FlowBot('XXX', chat)
flowbot.run()