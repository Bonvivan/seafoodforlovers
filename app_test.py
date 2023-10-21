from telethon import TelegramClient, sync
from telethon import functions, types
from telethon import events

from telethon.tl.functions.messages import ExportChatInviteRequest

import asyncio

import commands as cm
import re
import json
import threading
import time
import datetime as dt
from  datetime import datetime, date
import textProcess as tp
import evalTime


api_id = 27619730
api_hash = 'cca9443429ddb73be66dd446ddfbb2ec'

client = TelegramClient('roro_trial_session', api_id, api_hash, system_version="4.16.30-vxCUSTOM", device_model="MyHomeServer", app_version="myPythonApp")

superbot_state_filepath = 'resources/superbot_state.json'
superbot_state = {'tmp_chat_id':[]}

def decodeEvent(event):
    event = str(event)
    z = re.match('.*user_id=(\d+).*', event)
    uid = int(z.groups()[0])
    z = re.match('.*chat_id=(\d+).*', event)
    cid = int(z.groups()[0])
    z = re.match('.*date=(datetime.datetime\(.+tzinfo=\S+\)),.*', event)
    time = evalTime.evaltime(z.groups()[0])
    z = re.match('.*action=(\w+)\(inviter_id=(\d+)\).*', event)
    action = z.groups()[0]
    inviter_id = z.groups()[1]
    return {'user_id': uid, 'chat_id': cid, 'time': time, 'action': action, 'inviter_id': inviter_id}


async def channel_inspector():
    print('channel_inspector')
    try:
        state_f = open(superbot_state_filepath, 'r')
        superbot_state = json.load(state_f)
        superbot_state = tp.correct_time(superbot_state)
        state_f.close()
        for ch in superbot_state['tmp_chat_id']:
            try:
                if isinstance(ch['time'], str):
                    ch['time'] = datetime.fromisoformat(ch['time'])
                    pass
                if ch['time'] + dt.timedelta(minutes=1) < datetime.now(dt.UTC):
                    try:
                        await client(functions.messages.DeleteChatRequest(chat_id=ch['id']))
                    except:
                        continue
                    botuser = ch['botuser']
                    id = ch['id']
                    superbot_state['tmp_chat_id'].remove(ch)
                    try:
                        await client.send_message(botuser, '/channal_deleted;' + str(id) + ';' + str(ch['pid']))
                    except:
                        continue
            except Exception as ch_error:
                print(ch_error)
                print('Error in reading of superbot state record, deleting the problem record: ' + str(ch))
                if ch in superbot_state['tmp_chat_id']:
                    superbot_state['tmp_chat_id'].remove(ch)
                continue
            pass
    except Exception as err:
        print(err)

    state_f = open(superbot_state_filepath, 'w')
    json.dump(superbot_state, state_f, indent=4)
    state_f.close()

    time.sleep(600)
    await channel_inspector()

def timer_control():
    asyncio.run(channel_inspector())
    threading.Timer(10.0, timer_control).start()

@client.on(events.ChatAction())
async def normal_handler(event):
    if event.user_joined:
        state_f = open(superbot_state_filepath, 'r')
        superbot_state = json.load(state_f)
        superbot_state = tp.correct_time(superbot_state)

        event_dict = decodeEvent(event) # reading of the event string to create a dictionary

        for ch in superbot_state['tmp_chat_id']:
            if ch['id']==event_dict['chat_id']:
                await client.send_message(ch['botuser'], '/savechannel;' + str(event_dict['user_id']) + ';' + str(ch['id']) + ';' + event_dict['time'].isoformat())
                superbot_state['tmp_chat_id'].remove(ch)
        pass

@client.on(events.NewMessage(incoming=True))
async def normal_handler(event):
    global superbot_state
    result = None
    msg_txt = event.message.to_dict()['message']
    command = tp.parseCommand(msg_txt)
    if command['request']==cm.COMMANDS.create_a_channal:
        try:
            admin_users = command['args'][:-1]
            pupil       = command['args'][ -1]
            botuser     = command['args'][0]
            result = await client(functions.messages.CreateChatRequest(users=admin_users,title= 'Langusto italiano per ' + pupil))
            await client.edit_admin(result.chats[0], botuser, is_admin=True, add_admins=False)
            invite_link = await client(ExportChatInviteRequest(result.chats[0]))
            z = re.match(r'.*link=\'(https:\S+)\'.*', str(invite_link))
            invite_link = z.groups()[0]
            print('Invite link = ' + str(invite_link))
            txt = '!Это чат для обучения итальянскому от Langusto!\n Он создан спеициально для пользователя ' + '@' + command['args'][-1] + '\n'
            txt += 'Вот другие его участники:\n'
            txt += '@' + command['args'][0] + ' - это трудолюбивый робот, который будет выдaвать тебе задания\n'
            txt += '@' + command['args'][1] + ' - это я, Марго, твой преподаватель. Я буду проверять задания и помогать в обучении\n'
            await client.send_message(result.chats[0].id, txt) # sending message to a chat
            txt = '/tunnelmsg;' + str(pupil) + ';Это приглашение в чат для обучения итальянскому. Переходи в группу и начни свой первый урок! \n\n<b>Этот чат можете удалить, он больше не пригодится.</b>\n\n' + invite_link
            await client.send_message(botuser, txt, parse_mode='html') # sending a link to a user.
            superbot_state['tmp_chat_id'].append({'id': result.chats[0].id, 'pid': pupil, 'botuser': botuser, 'time': result.chats[0].date.isoformat()})
            state_f = open(superbot_state_filepath, 'w')
            json.dump(superbot_state, state_f, indent=4)
            state_f.close()
        except Exception as err:
            await client(functions.messages.DeleteChatRequest(chat_id=result.chats[0].id))
            print(err)
    if command['request'] == cm.COMMANDS.delete_channal:
        try:
            chat_id = command['args'][:-1]
            user_list = client.get_participants(entity=chat_id)
            print('Deleting chat for users: ')
            for _user in user_list:
                print(_user)
            await client(functions.messages.DeleteChatRequest(chat_id))
            print('Chat is deleted')
        except Exception as err:
            print('Chat was not deleted')
            print(err)

    print(event.message.to_dict()['message'])

    try:
        state_f = open(superbot_state_filepath, 'r')
        superbot_state = json.load(state_f)
    except:
        state_f = open(superbot_state_filepath, 'w')
        json.dump(superbot_state, state_f, indent=4)
        state_f.close()


client.start()
for dialog in client.iter_dialogs():
    print('Dialog entity: ' + str(dialog.entity.id))

client.run_until_disconnected()