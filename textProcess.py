import json
import requests
import re
from  datetime import datetime, date

class MSG_TYPE:
    text = 'text'
    image = 'image'
    audio = 'audio'
    video = 'video'
    audionote = 'audionote'

    knowntypes={text: 'text/html; charset=UTF-8', video: 'video/', image: 'image', audio: 'audio', audionote: 'audio/ogg'}

    ext_to_type={'mp4': video, 'mov': video, 'avi': video, 'mkv': video, 'ogg': audionote, 'mp3': audio, 'jpg': image, 'png': image}

    @staticmethod
    def getType(sometype):
        bestmatch = list([MSG_TYPE.compare(sometype, t) for t in MSG_TYPE.knowntypes.values()])
        return list(MSG_TYPE.knowntypes.keys())[bestmatch.index(max(bestmatch))]

    @staticmethod
    def guessExtension(str):
        z = re.findall('https://[a-zA-Z0-9.-_@/]+/([a-zA-Z0-9.-_]+.[a-zA-Z0-9])\?\S+', str)
        if len(z) == 0:
            return None,None
        filename = z[0]
        ext = filename.split('.')[-1].lower()

        return filename, MSG_TYPE.ext_to_type[ext]
    @staticmethod
    def compare(str1, str2):#
      #  print(str1 + '=?' + str2)
        l=min([len(str1),len(str2)])
        for s1,s2,i in zip(str1,str2,range(l)):
            if s1!=s2:
                return i

        return l

def parseCommand(msg):
    msg_list = msg.split(';')
    command = {}
    command['request'] = msg_list[0]
    command['args']    = msg_list[1:]
    return  command

def cleanMessage(msg, username_template='\S+'):
    z = re.match('(@'+username_template + ').*', msg)
    if z:
        username = z.groups()[0]
        msg = msg.replace(username, '')
    msg = msg.strip()
    return msg

def parseMessageFast(msg, past_answer=''): #TODO implement a class message, keeping info like results here, methods to add buttons and msges to markup, sending of msg, etc.
    result = {'content': [], 'buttons': []}
    text = msg
    text = text.split('--new-message--')

    for txt in text:
        txt = txt.strip()

        buttons = re.findall("\[\[[^\]]+\]\]", txt)

        for i in range(len(buttons)):
            txt = txt.replace(buttons[i], '')
            buttons[i] = buttons[i][2:-2]
            buttons[i].strip()

        result['content'].append([txt.strip() + past_answer, MSG_TYPE.text])
        for i in range(len(buttons)):
            b = buttons[i]
            details = b.split(';')
            details.append(None)
            result['buttons'].append([details[0],details[1].strip(),details[2]])

    return result

def parseMessage(msg, past_answer=''): #TODO implement a class message, keeping info like results here, methods to add buttons and msges to markup, sending of msg, etc.
    result = {'content': [], 'buttons': []}
    text = msg
    text = text.split('--new-message--')

    for txt in text:
        txt = txt.strip()
        url    = re.match('(https:\S+)'     , txt)
        if url:
            url = url.groups()[0]
            url = url.strip()
            try:
                req = requests.get(url)
                r = req.headers['content-type']
                r = MSG_TYPE.getType(r)
                result['content'].append((url, r))
            except:
                result['content'].append((url, 'text/html; charset=UTF-8'))
            #text = text[url_pos + len(url) + 1:]
            continue

        txt = txt.strip()
        buttons = re.findall("\[\[[^\]]+\]\]", txt)

        for i in range(len(buttons)):
            txt = txt.replace(buttons[i], '')
            buttons[i] = buttons[i][2:-2]
            buttons[i].strip()

        result['content'].append([txt.strip() + past_answer, MSG_TYPE.text])
        for i in range(len(buttons)):
            b = buttons[i]
            details = b.split(';')
            details.append(None)
            result['buttons'].append([details[0],details[1].strip(),details[2]])

    return result

def correct_time(record):
    for k, val in record.items():
        if isinstance(val, dict):
            record[k] = correct_time(val)
        else:
            if k == 'time':
                record[k]==datetime.fromisoformat(val)
                return record[k]
    return record

class JSONCoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return { "__class__": "datetime",
                     "y": obj.year,
                     "month": obj.month,
                     "d": obj.day,
                     "h": obj.hour,
                     "minute": obj.minute,
                     "s": obj.second }

        return json.JSONEncoder.default(self, obj)
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return int(o.timestamp())
        return json.JSONEncoder.default(self, o)

class JSONDCoder(json.JSONDecoder):
    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=JSONDCoder.from_dict)

    @staticmethod
    def from_dict(d):
        if d.get("__class__") == "datetime":
            return datetime(d["y"], d["month"], d["d"],
                            d["h"], d["minute"], d["s"])
        return d