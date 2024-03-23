import os
import re
from telebot import types
from datetime import datetime, date, timezone
import threading
import datetime as dt

def find(name, path):
    found_files = []
    for root, dirs, files in os.walk(path):
        for f in files:
            res = re.match(name, f)
            if res:
                found_files.append(os.path.join(root, f))
    return found_files


class ChatLog():
    logs = {}
    updates = {}
    log_files = {}
    fname_prefix = ''
    def __init__(self, filename_prefix):
        self.fname_prefix  = filename_prefix
        #filelist = find(filename_prefix + r'-?\d +\.txt', 'chatlog')
        filelist = find(filename_prefix + r'-?\d+\.txt', 'chatlog')
        if (filelist is None):
            filelist = []

        for f in filelist:
            z = re.match(r'chatlog\\'+self.fname_prefix+'(.+)\.txt', f)
            if not (z):
                continue
            cid = int(z.groups()[0])
            self.log_files[cid] = open(f, 'r', encoding='utf-8')
            self.log_files[cid].seek(0)
            log = self.log_files[cid].read()
            messages = log.split('msg::')
            self.logs[cid] = []
            for m in messages:
                if m.strip()!= '':
                    self.logs[cid].append(m.split(';'))
            self.log_files[cid].close()
            self.log_files[cid] = open(f, 'a', encoding='utf-8')

        for cid in self.logs.keys():
            self.logs[cid] = list(reversed(self.logs[cid]))

        threading.Timer(30, self.__refreshFiles).start()
        pass

    def __refreshFiles(self):
        for cid in self.updates:
            try:
                if not(cid in self.log_files):
                    self.log_files[int(cid)] = open('chatlog/' + self.fname_prefix + str(cid) + '.txt', 'w', encoding='utf-8')
                for m in self.updates.pop(cid, []):
                    self.log_files[int(cid)].write('\nmsg::' + ';'.join(m))
            except Exception as e:
                print("Error during writing to message logfiles: " + str(e))

        for cid in self.log_files:
            self.log_files[cid].close()
        self.log_files = {}
        filelist = find(self.fname_prefix + r'-?\d+\.txt', 'chatlog')
        if filelist is None:
            filelist = []

        for f in filelist:
            try:
                z = re.match(r'chatlog\\' + self.fname_prefix + '(.+)\.txt', f)
                if not (z):
                    continue
                cid = int(z.groups()[0])
                self.log_files[cid] = open(f, 'a', encoding='utf-8')
            except Exception as e:
                print("Error during reopening logfiles: " + str(e))

        threading.Timer(60, self.__refreshFiles).start()
        pass

    def getMessage(self, chat_id, index):
        for m in self.logs[chat_id]:
            try:
                return m[int(index)]
            except:
                return None
        pass

    def findReply(self, chat_id, index, depth=15):
        index = [int(x) for x in index]
        log = self.logs[chat_id]
        count = 0
        for m in log:
            try:
                if (str(m[-2]) != 'None') and (int(m[-2]) >= int(min(index)) and int(m[-2]) <= int(max(index))):
                    return m
            except:
                pass
            count += 1
            if (count > depth):
                break
        return None
        pass

    def addMessage(self, msg):
        if msg is None:
            return None
        try:
            if not(int(msg.chat.id) in self.logs):
                self.logs[int(msg.chat.id)] = []
            log = self.logs[int(msg.chat.id)]
            time = dt.datetime.utcfromtimestamp(msg.date).isoformat()
            if msg.reply_to_message is None:
                log.insert(0, [time, str(msg.message_id), str(msg.from_user.id), str(msg.content_type), str(msg.reply_to_message)           , str(msg.text)])
            else:
                log.insert(0 ,[time, str(msg.message_id), str(msg.from_user.id), str(msg.content_type), str(msg.reply_to_message.message_id), str(msg.text)])
        except:
            return None

        try:
            if int(msg.chat.id) in self.log_files:
                self.log_files[int(msg.chat.id)].write('\nmsg::' + ';'.join(log[0]))
            else:
                self.log_files[int(msg.chat.id)] = open('chatlog/' + self.fname_prefix + str(msg.chat.id) + '.txt', 'w')
                self.log_files[int(msg.chat.id)].write('\nmsg::' + ';'.join(log[0]))
        except Exception as e:
            if not(int(msg.chat.id) in self.updates):
                self.updates[int(msg.chat.id)] = []
            self.updates[int(msg.chat.id)].append(log[0])
        pass

    def getLastMessage(self, chat_id, from_user, span = 1):
        log = self.logs[chat_id]
        count = span
        for m in log:
            if int(m[2]) == int(from_user):
                count -= 1
                if count<=0:
                    return m
        pass
    def findMessageByText(self, chat_id, pattern, depth=15, from_user = -1):
        log = self.logs[chat_id]
        count = 0
        for m in log:
            try:
                if int(m[2]) == int(from_user) or int(from_user)==-1:
                    if re.match(pattern, m[-1]):
                        return m
            except:
                pass
            count += 1
            if (count > depth):
                break
        return None
    pass