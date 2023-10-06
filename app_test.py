from telethon import TelegramClient, sync
from telethon import functions, types
from telethon import events

from telethon.tl.functions.messages import ExportChatInviteRequest

import commands as cm

api_id = 27619730
api_hash = 'cca9443429ddb73be66dd446ddfbb2ec'

client = TelegramClient('roro_trial_session', api_id, api_hash, system_version="4.16.30-vxCUSTOM", device_model="MyHomeServer", app_version="myPythonApp")



def parse_message(msg):
    msg_list = msg.split(';')
    command = {}
    command['request'] = msg_list[0]
    command['args']    = msg_list[1:]
    return  command

@client.on(events.NewMessage(incoming=True))
async def normal_handler(event):
    ### usefull commands example
    # result.chats[0].id
    # result.chats[0].title
    #
    #destination_channel_username = 'test_ali3'
    #entity = client.get_entity(destination_channel_username)
    #client.send_message(entity=entity, message="Hi")

    #chat = InputPeerChat(desired_chat_id)

    msg_txt = event.message.to_dict()['message']
    command = parse_message(msg_txt)
    if command['request']==cm.COMMANDS.create_a_channal:
        try:
            result = await client(functions.messages.CreateChatRequest(users=command['args'],title='Italian class chat'))
            #destination_channel =
            print(result)
            invite_link = await client(ExportChatInviteRequest(result.chats[0]))
            txt = 'Это чат для обучения итальянскому от Langusto!\n Он создан спеициально для пользователя ' + '@' + command['args'][-1] + '\n'
            txt += 'Вот другие его участники:\n'
            txt += '@' + command['args'][0] + ' - это трудолюбивый робот, который будет выдaвать тебе задания\n'
            txt += '@' + command['args'][1] + ' - это я, Марго, твой преподаватель. Я буду проверять задания и помогать в обучении\n'
            await client.send_message(result.chats[0].id, txt) # sending message to a chat
        except Exception as err:
            print(err)

    print(event.message.to_dict()['message'])


client.start()

for dialog in client.iter_dialogs():
    print(dialog.entity.id)


client.run_until_disconnected()


#result = client(functions.messages.CreateChatRequest(
#        users=['undresaid','langusto_personal_teacher_bot', 'roro_tmp'],
#        title='Italian class chat'
#    ))


#print(result.stringify())
