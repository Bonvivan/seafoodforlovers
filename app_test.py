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
import os
#Margo
'''
api_id = 28814841
api_hash = 'aab0023515492e361473e53644c7413b'
'''

#-------------------------------------------------------#
#----created by Andrey Svitenkov, Undresaid, 10.2023----#
#-------------------------------------------------------#

api_id = 27619730 # roro
#api_id = 29453964
api_hash = 'cca9443429ddb73be66dd446ddfbb2ec'
#api_hash = '9b19a5222a26d36b8d0a38f4278dac44'

#client = TelegramClient('MargoSuperSession', api_id, api_hash, system_version="4.16.30-vxCUSTOM", device_model="MyHomeServer", app_version="myPythonApp")
client = TelegramClient('MySuperSession', api_id, api_hash, system_version="4.16.30-vxCUSTOM", device_model="MyHomeServer", app_version="myPythonApp")

superbot_state_filepath = 'resources/superbot_state.json'
superbot_state = {'tmp_chat_id':[]}

self_id = 6604084268

def decodeLinkEvent(event):
    event = str(event)
    z = re.match('.*user_id=(\d+).*', event)
    try:
        uid = int(z.groups()[0])
        z = re.match('.*chat_id=(\d+).*', event)
        cid = int(z.groups()[0])
        z = re.match('.*date=(datetime.datetime\(.+tzinfo=\S+\)),.*', event)
        time = evalTime.evaltime(z.groups()[0])
        z = re.match('.*action=(\w+)\(inviter_id=(\d+)\).*', event)
        action = z.groups()[0]
        inviter_id = z.groups()[1]
    except:
        print('Error in event decoding: ' + str(event))
        return None
    return {'user_id': uid, 'chat_id': cid, 'time': time, 'inviter_id': inviter_id}

def decodeAddEvent(event):
    event = str(event)
    z = re.match('.*user_id=(\d+).*', event)
    try:
        uid = int(z.groups()[0])
        z = re.match('.*chat_id=(\d+).*', event)
        cid = int(z.groups()[0])
        z = re.match('.*date=(datetime.datetime\(.+tzinfo=\S+\)),.*', event)
        time = evalTime.evaltime(z.groups()[0])
        z = re.match('.*action=(\w+)\(users=\[(\W+)\]\).*', event)
        action = z.groups()[0]
        users_id = z.groups()[1].split(',')
    except:
        print('Error in event decoding: ' + str(event))
        return None
    return {'user_id': uid, 'chat_id': cid, 'time': time}

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
                if ch['time'] + dt.timedelta(minutes=1) < datetime.utcnow():
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
        print('General error in message read: ' + str(err))

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
    if (event.user_joined or event.user_added):
        state_f = open(superbot_state_filepath, 'r')
        superbot_state = json.load(state_f)
        superbot_state = tp.correct_time(superbot_state)

        if event.user_added:
            if self_id != event.user_id:
                for uid in event.input_users:
                   msg = await client.kick_participant(event.chat_id, event.user_id)
            return None

        for ch in superbot_state['tmp_chat_id']:
            if -int(ch['id'])==int(event.chat_id):
                await client.send_message(ch['botuser'], '/savechannel;' + str(event.user.id) + ';' + str(event.chat_id) + ';' + event.action_message.date.isoformat())
                superbot_state['tmp_chat_id'].remove(ch)
        pass

@client.on(events.NewMessage(incoming=True))
async def normal_handler(event):
    global superbot_state
    print('!!!!!!!!!!!!!!New messega resiceved 1')
    result = None
    msg_txt = event.message.to_dict()['message']
    print('New messega resiceved: ' + str(msg_txt))
    command = tp.parseCommand(msg_txt)
    if command['request']==cm.SCOMMANDS.create_a_chat:
        try:
            admin_users = command['args'][1:-1]
            pupil       = command['args'][-1]
            addr        = command['args'][ 0]
            botuser     = command['args'][ 1]
            result = await client(functions.messages.CreateChatRequest(users=admin_users,title= 'Langusto italiano per ' + pupil))
            txt = 'Это чат для обучения итальянскому с Langusto! \n\n Если ничего не происходит наберите /start для продолжения.'
            await client.send_message(result.chats[0].id, txt)
            for bu in admin_users:
                try:
                    await client.edit_admin(result.chats[0], bu, is_admin=True, add_admins=False)
                except:
                    pass

            invite_link = await client(ExportChatInviteRequest(result.chats[0]))

            z = re.match(r'.*link=\'(https:\S+)\'.*', str(invite_link))
            if z.groups()[0]:
                invite_link = z.groups()[0]
                txt = '/tunnelmsg;' + str(
                    pupil) + ';Это приглашение в чат для обучения итальянскому. Переходи в группу и начни свой первый урок!' + invite_link
                txt += ';' + addr + ';1'
                await client.send_message(admin_users[0], txt, parse_mode='html')  # sending a link to a user.
                superbot_state['tmp_chat_id'].append({'id': result.chats[0].id, 'pid': pupil,'botuser': botuser, 'admin': admin_users,
                                                      'time': result.chats[0].date.isoformat()})
                state_f = open(superbot_state_filepath, 'w')
                json.dump(superbot_state, state_f, indent=4)
                state_f.close()

                for au in admin_users:
                    try:
                        await client.send_message(au, 'Создан новый обучающий чат: \n' + invite_link)
                    except:
                        pass
            else:
                raise Exception(f"Empty link on chat, chat was not created")

        except Exception as err:
            txt = '/tunnelmsg;' + str(pupil) + ';Не удалось создать чать, <b>ссылка придет чуть позже.</b>'
            txt += ';' + addr + ';0'
            await client.send_message(botuser, txt, parse_mode='html')  # sending a link to a user.
            await client(functions.messages.DeleteChatRequest(chat_id=result.chats[0].id))

    try:
        state_f = open(superbot_state_filepath, 'r')
        superbot_state = json.load(state_f)
    except:
        state_f = open(superbot_state_filepath, 'w')
        json.dump(superbot_state, state_f, indent=4)
        state_f.close()


client.start()
print(client.get_me().stringify())

for dialog in client.iter_dialogs():
    print('Dialog entity: ' + str(dialog.entity.id))
try:
    client.run_until_disconnected()
except Exception as err:
    print('General error, rebooting ' + str(err))
    os.abort()