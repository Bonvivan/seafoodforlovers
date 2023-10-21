#seafoodforlovers@seafoodforlovers.iam.gserviceaccount.com

import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
import threading
import time
import random

import google.type

import json

def flatten(l):
    return [item for sublist in l for item in sublist]
class GoogleTableReader():
    CREDENTIALS_FILE = 'resources/seafoodforlovers-451d571f02c4.json'
    credentials = None

    read_counter = 0

    header = None
    pupils_id = None

    critical_flag = False

    def __init__(self, spreadsheetId):
        self.alphabet = list(map(chr, range(ord('A'), ord('Z')+1)))
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name(self.CREDENTIALS_FILE,
                                                                       ['https://www.googleapis.com/auth/spreadsheets',
                                                                        'https://www.googleapis.com/auth/drive'])
        self.httpAuth = self.credentials.authorize(httplib2.Http())  # Авторизуемся в системе
        self.service  = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)  # Выбираем работу с таблицами и 4 версию API
        self.spreadsheetId = spreadsheetId

        self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                          range='pupils' + '!' + 'A1:Z1').execute()['values'][0]
        self.pupils_id = self.getAllPupilColumns(['id'])[0]

        print('Created reader for:' + 'https://docs.google.com/spreadsheets/d/' + spreadsheetId)

        threading.Timer(60.0, self.__resetAccessCounter).start()
        pass

    def my_shiny_new_decorator(function_to_decorate):
        def wrapper(self, *args, **kwargs):
            access_count = 0
            r = random.random()
            if self.read_counter > 10:
                time.sleep(1+r)
            if self.read_counter > 20:
                time.sleep(2+r)
            if self.read_counter > 30:
                time.sleep(4+r)
            if self.read_counter > 40:
                time.sleep(8+r)
            if self.read_counter > 50:
                print('Too many requests')
                time.sleep(45+r*5)
                self.read_counter = 0

            while self.critical_flag:
                print('Access is closed')
                access_count += 1
                time.sleep(1 + r)
                if access_count > 10:
                    self.critical_flag = False

            self.critical_flag = True
            try:
                res = function_to_decorate(self, *args, **kwargs)
            except Exception as err:
                print('Error in google sheet access: ' + err)
                self.critical_flag = False
            self.critical_flag=False
            return res
        return wrapper

    @my_shiny_new_decorator
    def __resetAccessCounter(self):
        print('Access counter, read: ' + str(self.read_counter))
        self.read_counter = 0
        self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                          range='pupils' + '!' + 'A1:Z1').execute()['values'][0]
        threading.Timer(30.0, self.__resetAccessCounter).start()
        threading.Timer(300.0, self.__reconnect).start()

    @my_shiny_new_decorator
    def __reconnect(self):
        self.httpAuth = self.credentials.authorize(httplib2.Http())  # Авторизуемся в системе
        self.service = apiclient.discovery.build('sheets', 'v4',
                                                 http=self.httpAuth)  # Выбираем работу с таблицами и 4 версию API
        threading.Timer(300.0, self.__reconnect).start()

    def giveAccess(self, email, role='writer'):
        access = self.service.permissions().create(
            fileId=self.spreadsheetId,
            body={'type': 'user', 'role': role, 'emailAddress': email},
            # Открываем доступ на редактирование
            fields='id'
        ).execute()

    def getFieldValue(self, id, fieldname, key_column='id', sheetName='pupils'):
        print('getFieldValue')
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        self.read_counter += 1
        if self.header is None:
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                          range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        all_keys = self.pupils_id
        if key_column!='id':
            all_keys = self.getAllPupilColumns([key_column])[0]
        elif self.pupils_id == None:
            self.pupils_id = self.getAllPupilColumns(['id'])[0]
            all_keys = self.pupils_id

        if not(str(id) in all_keys):
            return None
        u_row = str(all_keys.index(str(id))+4+1)
        if fieldname in self.header:
            j = self.header.index(fieldname)
            letter=self.alphabet[j]
            result = self.getValue(sheetName, letter+u_row+':'+letter+u_row)
            return result[0][0]

        return None

    def getAllFieldValue(self, id, sheetName='pupils'):
        print('getAllFieldValue')
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        self.read_counter += 1
        if self.header is None:
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        myheader = self.header

        all_user_id = self.pupils_id
        if self.pupils_id == None:
            self.pupils_id = self.getAllPupilColumns(['id'])[0]

        if not(str(id) in all_user_id):
            return None
        u_row = str(all_user_id.index(str(id))+4+1)
        record = self.getValue(sheetName, 'A' + u_row + ':' + 'Z' + u_row)[0]

        myheader.append(record)

        return myheader


    #TODO add decorator to prevent overcounting of requests


    def setFieldValue(self, value, id, fieldname, key_column='id',sheetName='pupils'):
        print('setFieldValue')
        self.read_counter += 1
        #print('Before read header!')
        if self.header is None:
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        #print('Header readen!')

        all_keys_collumn = self.pupils_id
        if key_column != 'id':
            all_keys_collumn = self.getAllPupilColumns([key_column])[0]
        elif self.pupils_id == None:
            self.pupils_id = self.getAllPupilColumns([key_column])[0]
            all_keys_collumn = self.pupils_id


        if not(str(id) in all_keys_collumn):
            return None
        u_row = str(all_keys_collumn.index(str(id))+4+1)
        if fieldname in self.header:
            j = self.header.index(fieldname)
            letter=self.alphabet[j]
            self.setValue([value], sheetName, letter+u_row)
            pass

        return None

    @my_shiny_new_decorator
    def setValue(self, value, sheetName, cellRange):
        rng = sheetName + '!' + cellRange
        print('setValue')
        body = {}
        body['values'] = [value]
        self.read_counter += 1
        resp = None
        if value[0] is None or value[0]=='':
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

    def getPupilStatus(self, id, sheetName='pupils'):
        print('getPupilStatus')
        if self.header is None:
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        all_keys = self.pupils_id
        if self.pupils_id == None:
            self.pupils_id = self.getAllPupilColumns(['id'])[0]
            all_keys = self.pupils_id

        if not (str(id) in all_keys):
            return None
        u_row = str(all_keys.index(str(id)) + 4 + 1)
        result = self.getValue(sheetName, 'A' + u_row + ':' + 'ZZ' + u_row)[0]
        pupil_info = {}
        for k, r in zip(self.header, result):
            j = self.header.index(k)
            pupil_info[k] = r

        return pupil_info
    @my_shiny_new_decorator
    def getAllValue(self, sheetName):
        print('getAllValue')
        # self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        rng = sheetName + '!' + 'A1:Z9999'
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
    def getAllPupilColumns(self, columns, sheetName='pupils'):
        print('getAllPupilColumns')

        if len(columns)<1:
            return []

        self.read_counter += 1
        if self.header is None:
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        columns_ids = []
        for c in columns:
            columns_ids.append(self.header.index(c))

        self.read_counter += 1
        res = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                       range=sheetName + '!' + 'A5:'  + 'ZZ9999').execute()

        result = []
        if not 'values' in res:
            result.append([])
            return result

        for ci in columns_ids:
            res_col = [col[ci] for col in res['values']]
            result.append(res_col)
        '''
        result = []
        for ci in columns_ids:
            rng = self.alphabet[ci]
            self.read_counter += 1
            res = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                     range=sheetName + '!' + rng + '5:' + rng + '9999').execute()
            if 'values' in res.keys():
                res = flatten(res['values'])
            else:
                res = []
            result.append(res)
        '''
        return result

    @my_shiny_new_decorator
    def getPupilStruct(self, sheetName='pupils'):
        print('getPupilStruct')
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        pupil_data_struct = {}
        header_rng  = sheetName + '!' + 'A1:Z4'
        self.read_counter += 1
        results = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId, range=header_rng).execute()
        names  = results['values'][0]
        source = results['values'][1]
        regex  = results['values'][3]
        for i in range(len(names)):
            pupil_data_struct[names[i]]={'source':source[i],'required':False,'reagex':regex[i]}

        return pupil_data_struct

    def deletePupil(self, uid):
        sheetName = 'pupils'
        ids = self.getAllPupilColumns(['id'])[0]
        u_row = int(ids.index(str(uid)) + 4 + 1)

        resource = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": 2087899597,
                            "dimension": "ROWS",
                            "startIndex": u_row-1,
                            "endIndex": u_row
                        }
                    }
                }
            ]
        }
        resp = self.service.spreadsheets().batchUpdate(spreadsheetId = self.spreadsheetId, body=resource).execute()
        self.pupils_id = self.getAllPupilColumns(['id'])[0]
        return resp

    def addPupil(self, pupil_info, sheetName='pupils'):
        print('addPupil')
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        self.read_counter += 1

        ids = self.pupils_id
        if self.pupils_id == None:
            self.pupils_id = self.getAllPupilColumns(['id'])[0]
            ids = self.pupils_id

        pupil_info['alingment'] = 0
        #self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,range=sheetName + '!' + 'A5:A9999').execute()
        #ids = flatten(ids['values'])
        if str(pupil_info['id']) in ids:
            return None

        self.read_counter += 1
        if self.header is None:
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        pupil_spreadsheet = {'values':[[]]}
        for inf in self.header:
            if inf in pupil_info:
                pupil_spreadsheet['values'][0].append(pupil_info[inf])
            else:
                pupil_spreadsheet['values'][0].append('')

        self.read_counter += 1
        resp = self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheetId,
            range="pupils!A1",
            valueInputOption="RAW",
            body=pupil_spreadsheet).execute()

        self.pupils_id = self.getAllPupilColumns(['id'])[0]

        return resp



# Читаем ключи из файла


"""
spreadsheet = service.spreadsheets().create(body = {
    'properties': {'title': 'tmp_test_doc', 'locale': 'ru_RU'},
    'sheets': [{'properties': {'sheetType': 'GRID',
                               'sheetId': 0,
                               'title': 'Pupils',
                               'gridProperties': {'rowCount': 100, 'columnCount': 15}}}]
}).execute()
"""
#spreadsheetId = "1A_s-2vCoTmf9ElTCPg9inH1FbuwIHp0JbIAPcrCnYdA"#spreadsheet['spreadsheetId']

#print('https://docs.google.com/spreadsheets/d/' + spreadsheetId)


#driveService = apiclient.discovery.build('drive', 'v3', http = httpAuth) # Выбираем работу с Google Drive и 3 версию API



