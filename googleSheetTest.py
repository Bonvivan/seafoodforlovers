#seafoodforlovers@seafoodforlovers.iam.gserviceaccount.com

import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
import threading
import time
import random
import re
import google.type

import json

#-------------------------------------------------------#
#----created by Andrey Svitenkov, Undresaid, 10.2023----#
#-------------------------------------------------------#

def flatten(l):
    return [item for sublist in l for item in sublist]
class GoogleTableReader():
    CREDENTIALS_FILE = 'resources/seafoodforlovers-451d571f02c4.json'
    credentials = None

    read_counter = 0
    write_counter = 0

    header = None
    pupils_id = None

    critical_flag = False

    pupilsData    = {}
    fieldsIndexer = {}
    pupilRowIndex = {}

    updateQueue      = {}
    logQueue         = [] # TODO: make it a separate class
    logHeader        = {}



    def __init__(self, spreadsheetId):
        self.alphabet = list(map(chr, range(ord('A'), ord('Z')+1)))
        tmp_alphabet = self.alphabet
        for cc in tmp_alphabet :
            self.alphabet = self.alphabet + [cc+c for c in tmp_alphabet]

        self.credentials = ServiceAccountCredentials.from_json_keyfile_name(self.CREDENTIALS_FILE,
                                                                       ['https://www.googleapis.com/auth/spreadsheets',
                                                                        'https://www.googleapis.com/auth/drive'])
        self.httpAuth = self.credentials.authorize(httplib2.Http())  # Авторизуемся в системе
        self.service  = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)  # Выбираем работу с таблицами и 4 версию API
        self.spreadsheetId = spreadsheetId

        self.header = self.__readHeader()
        self.initPupilsDatabase()
        self.short_header = self.__readHeaderShort()

        print('Created reader for:' + 'https://docs.google.com/spreadsheets/d/' + spreadsheetId)

        threading.Timer(60.0, self.__resetAccessCounter).start()
        threading.Timer(313.0, self.__reconnect).start()
        pass


    def my_shiny_new_decorator(function_to_decorate):
        def wrapper(self, *args, **kwargs):
            access_count = 0
            r = random.random()
            if self.read_counter > 130:
                time.sleep(2+r)
                print('Too many requests 1')
            if self.read_counter > 180:
                time.sleep(3+r)
                print('Too many requests 2')
            if self.read_counter > 230:
                time.sleep(4+r)
                print('Too many requests 3')
            if self.read_counter > 250:
                time.sleep(30+r)
                print('Too many requests 4')

            while self.critical_flag:
                access_count += 1
                time.sleep(1 + r)
                print('Access is closed, wait for ' + str(1+r) + ' count = ' + str(access_count))
                if access_count > 20:
                    self.critical_flag = False

            self.critical_flag = True
            res = None
            try:
                res = function_to_decorate(self, *args, **kwargs)
            except Exception as err:
                self.critical_flag = False
                print('Error in google sheet access: ' + str(err))

            self.critical_flag = False
            return res
        return wrapper

    @my_shiny_new_decorator
    def allUpdate(self):
        self.__updateRemoteSpreadsheet()
        self.pupilsData, self.fieldsIndexer = self.getPupilsDatabase()

    @my_shiny_new_decorator
    def forceRead(self):
        self.pupilsData, self.fieldsIndexer = self.getPupilsDatabase()

    @my_shiny_new_decorator
    def __resetAccessCounter(self):
        threading.Timer(60.0, self.__resetAccessCounter).start()
        print('Access counter, read: ' + str(self.read_counter))
        self.read_counter  = 0
        self.write_counter = 0
        #self.header = self.__readHeader()
        self.__updateRemoteSpreadsheet()
    @my_shiny_new_decorator
    def __reconnect(self):
        threading.Timer(300.0, self.__reconnect).start()
        self.httpAuth = self.credentials.authorize(httplib2.Http())  # Авторизуемся в системе
        self.service = apiclient.discovery.build('sheets', 'v4',
                                                 http=self.httpAuth)  # Выбираем работу с таблицами и 4 версию API

    def __readHeaderShort(self, sheet='pupils', rng='A1:AZ1'):
        self.read_counter += 1
        header = []
        content = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                           range=sheet + '!' + rng).execute()['values']
        header = content[0]

        return header

    def __readHeader(self, sheet = 'pupils', rng = 'A1:BZ4'):
        self.read_counter+=1
        header = [[],[],[],[],[]]
        content = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                               range=sheet + '!' + rng).execute()['values']
        nested_len = len(content[0])
        content[0] = content[0] + [''  ] * (nested_len - len(content[0]))
        content[1] = content[1] + [''  ] * (nested_len - len(content[1]))
        content[2] = content[2] + [''  ] * (nested_len - len(content[2]))
        content[3] = content[3] + ['.*'] * (nested_len - len(content[3]))

        header[0] = content[0] + ['']
        header[1] = content[1] + ['']
        header[2] = content[2] + ['']
        header[3] = content[3] + ['.*']
        addr = re.match('(\w+)(\d+):(\w+)(\d+)', rng)
        count = self.alphabet.index(addr[1])
        for h in header[0][:-1]:
            header[-1].append(sheet + '!' + self.alphabet[count])
            count+=1
        header[-1].append('')

        for i in range(len(header[0])):
            r = re.match("(\w+)!([A-Z]+\d+:[A-Z]+\d+)", header[0][i])
            if not (r is None):
                tmp = self.__readHeader(sheet=r[1], rng=r[2])
                header[0]  = header[ 0][:i] + tmp[ 0][:-1] + header[ 0][i + 1:]
                header[-1] = header[-1][:i] + tmp[-1][:-1] + header[-1][i + 1:]
                header[1]  = header[ 1][:i] + tmp[ 1][:-1] + header[ 1][i + 1:]
                header[2]  = header[ 2][:i] + tmp[ 2][:-1] + header[ 2][i + 1:]
                header[3]  = header[ 3][:i] + tmp[ 3][:-1] + header[ 3][i + 1:]

        return header

    def __initLog(self, sheet = 'heaplog'):

        content = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                           range=sheet + '!' + 'A1:M').execute()['values']
        col_names = content[0]
        next_row = len(content)

        log_header = {}
        for i in range(len(col_names)):
            if col_names[i]:
                log_header[col_names[i]] = i
        return log_header, next_row

    def giveAccess(self, email, role='writer'):
        access = self.service.permissions().create(
            fileId=self.spreadsheetId,
            body={'type': 'user', 'role': role, 'emailAddress': email},
            # Открываем доступ на редактирование
            fields='id'
        ).execute()

    def addLogEntity(self, entities):
        for _id in entities:
            entity = entities[_id]
            uid = _id
            record = {}
            for h in entity.keys():
                if h in self.logHeader['header']:
                    record[h] = entity[h]

            self.logQueue.append({'id':uid, **record})
            for h in self.logHeader['header']:
                if not(h in self.logQueue[-1]):
                    if uid in self.pupilsData:
                        self.logQueue[-1][h] = self.pupilsData[uid][self.fieldsIndexer.get(h, -1)]
            pass
    @my_shiny_new_decorator
    def initPupilsDatabase(self):
        self.pupilsData, self.fieldsIndexer = self.getPupilsDatabase()
        pass

    def getPupilsDatabase(self):
        head, data = self.__initVitrualTable()
        id_ind = head[0].index('id')
        allPupilsDict = {}

        id_column = [int(row[id_ind]) for row in data]

        self.pupilRowIndex = {id_column[c]: c + len(head) for c in range(len(data))}

        count = 0
        for id in id_column:
            allPupilsDict[int(id)] = data[count]
            allPupilsDict[int(id)].append(None)
            count+=1

        allFieldsIndexer = {}
        count = 0
        for f in head[0]:
            allFieldsIndexer[f] = count
            count+=1

        return allPupilsDict, allFieldsIndexer

    def __initVitrualTable(self):#TODO: make reading form adresses from headers
        print('initVirtualTable')

        self.read_counter += 1
        header = self.__readHeader()
        self.logHeader['header'], self.logHeader['next_row']= self.__initLog(sheet='heaplog')
        self.logHeader['sheet'] = 'heaplog'

        readings = [h + str(len(header)) + ':' + h.split('!')[1] + '999' for h in header[-1][:-1]]

        resp = self.service.spreadsheets().values().batchGet(spreadsheetId=self.spreadsheetId,
                                                                   ranges=readings).execute()['valueRanges']
        data_table = []
        for row in range(len(resp[0]['values'])):
            data_table.append([])
            for c in resp:
                if 'values' in c and row < len(c['values']) and len(c['values'][row])>0:
                    data_table[-1].append(c['values'][row][0])
                else:
                    data_table[-1].append('')

        return header, data_table

    def getFieldValue(self, id, fieldname, key_column='id', force=False):
        print('getFieldValue')

        if self.header is None:
            self.header = self.__readHeader()

        result = None

        if key_column=='id':
            if id in self.pupilsData:
                if force:
                    rng = self.__addRowToAddres(self.header[-1][self.fieldsIndexer.get(fieldname, -2)], self.pupilRowIndex[id])
                    result = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                       range=rng).execute()['values'][0][0]
                else:
                    result = self.pupilsData[id][self.fieldsIndexer.get(fieldname, -1)]
        else:
            for p in self.pupilsData:
                if str(self.pupilsData[p][self.fieldsIndexer[key_column]]) == str(id):
                    if force:
                        rng = self.__addRowToAddres(self.header[-1][self.fieldsIndexer.get(fieldname, -2)], self.pupilRowIndex[p])
                        result = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                          range=rng).execute()['values'][0][0]
                    else:
                        result = self.pupilsData[p][self.fieldsIndexer.get(fieldname, -1)]

        return result

    def getFieldValues(self, id, fieldnames, key_column='id'):
        print('getFieldValue')

        if self.header is None:
            self.header = self.__readHeader()

        result = [None]*len(fieldnames)
        if not(key_column in self.fieldsIndexer):
            return result

        if key_column=='id':
            if id in self.pupilsData:
                result = [self.pupilsData[id][self.fieldsIndexer.get(f, -1)] for f in fieldnames]
        else:
            for p in self.pupilsData:
                if str(self.pupilsData[p][self.fieldsIndexer.get(key_column, -1)]) == str(id):
                    result = [self.pupilsData[p][self.fieldsIndexer.get(f, -1)] for f in fieldnames]

        return result

    def checkFieldValue(self, value, field):
        print('checkFieldValue')
        # self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        if self.header is None:
            self.header = self.__readHeader()

        control_exp = self.header[3][self.fieldsIndexer.get(field, -1)]
        if re.match(control_exp, value):
            return True
        else:
            return False
        return False

    def getAllFieldValue(self, id): #TODO: review method and its application
        print('getAllFieldValue')
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        self.read_counter += 1

        return self.header, self.pupilsData[id]

    @my_shiny_new_decorator
    def setFieldValues(self, id, values, fieldnames, key_column='id'):
        print('setFieldValuessss')

        key_id = id
        if key_column=='id':
            if id in self.pupilsData:
                for h,v in zip(fieldnames, values):
                    self.pupilsData[id][self.fieldsIndexer.get(h, -1)] = str(v)
                self.pupilsData[id][-1] = None
        else:
            for p in self.pupilsData:
                if str(self.pupilsData[p][self.fieldsIndexer.get(key_column, -1)])==str(id):
                    key_id = int(self.pupilsData[p][self.fieldsIndexer.get('id', -1)])
                    for h, v in zip(fieldnames, values):
                        self.pupilsData[key_id][h] = str(v)
                    self.pupilsData[key_id][-1] = None
                    break

        if key_id in self.pupilsData:
            self.updateQueue[key_id] = list(self.updateQueue.get(key_id,[]))+fieldnames

        return None

    def setFieldValue(self, id, value, fieldname, key_column='id'):
        print('setFieldValue')
        if self.header is None:
            self.header = self.__readHeader()

        key_id = id
        if key_column=='id':
            if id in self.pupilsData:
                self.pupilsData[id][self.fieldsIndexer.get(fieldname, -1)] = value
                self.pupilsData[id][-1] = None
        else:
            for p in self.pupilsData:
                if str(self.pupilsData[p][self.fieldsIndexer.get(key_column, -1)]) == str(id):
                    key_id = int(self.pupilsData[p][self.fieldsIndexer.get('id', -1)])
                    self.pupilsData[key_id][self.fieldsIndexer.get(fieldname, -1)] = value
                    self.pupilsData[key_id][-1] = None
                    break

        if key_id in self.pupilsData:
            self.updateQueue[key_id] = list(self.updateQueue.get(key_id,[]))+[fieldname]

        return None

    @my_shiny_new_decorator
    def setValue(self, value, sheetName, cellRange):
        rng = sheetName + '!' + cellRange
        print('setValue')
        body = {}
        if type(value) == type([]):
            if type(value[0]) == type([]):
                body['values'] = value
            else:
                body['values'] = [value]
        else:
            body['values'] = [[value]]

        resp = None
        self.write_counter += 1
        if value[0] is None or value[0] == '':
            resp = self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheetId,
                range=rng).execute()
        else:
            resp = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheetId,
                range=rng,
                valueInputOption="RAW",
                body=body).execute()

        return resp

    def getPupilStatus(self, id):
        print('getPupilStatus')

        if self.header is None:
            self.header = self.__readHeader()

        pupil_info = {}
        if not(id in self.pupilsData):
            return pupil_info

        for h in self.header[0]:
            pupil_info[h] = self.pupilsData[id][self.fieldsIndexer[h]]

        return pupil_info

    @my_shiny_new_decorator
    def getAllValue(self, sheetName):
        print('getAllValue')
        # self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        rng = sheetName + '!' + 'A1:BZ999'
        self.read_counter += 1
        results = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId, range=rng).execute()
        if not ('values' in results):
            return [[None]]
        sheet_values = results['values']
        return sheet_values

    @my_shiny_new_decorator
    def getValue(self, sheetName, cellRange):
        print('getValue')
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        rng = sheetName + '!' + cellRange
        self.read_counter+=1
        results = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId, range=rng).execute()
        if not('values' in results):
            return [[None]]
        sheet_values = results['values']
        return sheet_values

    @my_shiny_new_decorator
    def getValueFromStr(self, address):
        print('getValueFromStr')
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        rng = address
        self.read_counter += 1
        results = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId, range=rng).execute()
        sheet_values = results['values']
        return sheet_values

    @my_shiny_new_decorator
    def getAllPupilColumns(self, columns): #TODO: extract sheet name from header for nested sheets
        print('getAllPupilColumns')
        if len(columns)<1:
            return []

        if self.header is None:
            self.header = self.__readHeader()

        result = []
        for c in columns:
            result.append([self.pupilsData[id][self.fieldsIndexer.get(c, -1)] for id in self.pupilsData])

        return result

    @my_shiny_new_decorator
    def getPupilStruct(self, sheetName='pupils', rng='A1:BZ4'):
        return self.__getPupilStruct(sheetName=sheetName, rng=rng)

    def __getPupilStruct(self, sheetName='pupils', rng='A1:BZ4'):
        print('getPupilStruct')
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        pupil_data_struct = {}
        header_rng  = sheetName + '!' + rng
        self.read_counter += 1
        results = self.header
        names  = results[0]
        source = results[1]
        defval = results[2]
        regex  = results[3]
        for n in names:
            r = re.match("(\w+)!([A-Z]+\d+:[A-Z]+\d+)", n)
            if not (r is None):
                tmp = self.__getPupilStruct(sheetName=r[1], rng=r[2])
                names  = names  + list(tmp.keys())
                source = source + [tmp[n]['source'] for n in tmp.keys()]
                regex  = regex  + [tmp[n]['regex' ] for n in tmp.keys()]
                defval = defval + [tmp[n]['defval'] for n in tmp.keys()]

        for i in range(len(names[:-1])):
            pupil_data_struct[names[i]]={'source':source[i], 'defval': defval[i], 'regex':regex[i]}

        return pupil_data_struct

    def addPupil(self, pupil_info):
        print('addPupil')

        p_id = int(pupil_info['id'])
        if p_id in self.pupilsData:
            return None

        pupil_info['alingment'] = 0
        self.pupilsData[p_id] = [''] * len(self.header[0])
        for f in pupil_info:
            self.pupilsData[p_id][self.fieldsIndexer.get(f, -1)] = str(pupil_info[f])
        self.pupilsData[p_id][-1]=None
        self.pupilRowIndex[p_id] = self.pupilRowIndex[max(self.pupilRowIndex, key=self.pupilRowIndex.get)]+1

        self.updateQueue[p_id] = pupil_info.keys()
        return None

    @my_shiny_new_decorator
    def getValuesFromStr(self, addr_list):
        resp = self.service.spreadsheets().values().batchGet(spreadsheetId=self.spreadsheetId,
                                                             ranges=addr_list).execute()['valueRanges']
        result = []
        for c in resp:
            if 'values' in c :
                result.append(c['values'][0][0])
        return result

    def __addRowToAddres(self, addr, row):
        return addr.split('!')[0] + '!' + addr.split('!')[1] + str(row)

    @my_shiny_new_decorator
    def forceWrite(self):
        return self.__updateRemoteSpreadsheet()

    def __updateRemoteSpreadsheet(self):
        self.header = self.__readHeader()
        for pupil in self.updateQueue:
            self.updateQueue[pupil] = list(set(self.updateQueue[pupil]))

        body = {'valueInputOption': 'RAW', 'data': []}
        for pupil in self.updateQueue:
            for f in self.updateQueue[pupil]:
                if f in self.fieldsIndexer:
                    addr  = self.__addRowToAddres(self.header[-1][self.fieldsIndexer[f]], self.pupilRowIndex[pupil])
                    value = self.pupilsData[pupil][self.fieldsIndexer[f]]
                    body['data'].append({'range': addr, 'values':[[value]]})
        resp = True
        if len(body['data'])>0:
            try:
                resp = self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.spreadsheetId, body=body).execute()
            except Exception as err:
                print('ERROR_ERROR_ERROR: ' + str(list(self.updateQueue.keys()))  + ' ' + str(err))
                return False
                pass
        self.updateQueue = {}

        body = {'valueInputOption': 'RAW', 'data': []}
        for ent in self.logQueue:
            self.logHeader['next_row'] += 1
            for h in ent:
                addr = self.__addRowToAddres(self.logHeader['sheet'] +'!' + self.alphabet[self.logHeader['header'][h]], self.logHeader['next_row'])
                value = ent[h]
                body['data'].append({'range': addr, 'values': [[value]]})

        if len(self.logQueue)>0:
            try:
                resp = self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.spreadsheetId, body=body).execute()
                self.logQueue = []
            except Exception as err:
                print('ERROR_LOG, ' + 'trying to write log: ' + str(err))
                return False
                pass

        return resp

