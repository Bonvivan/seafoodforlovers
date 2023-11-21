#seafoodforlovers@seafoodforlovers.iam.gserviceaccount.com

import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
import threading
import time
import random

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
        threading.Timer(313.0, self.__reconnect).start()
        pass

    def my_shiny_new_decorator(function_to_decorate):
        def wrapper(self, *args, **kwargs):
            access_count = 0
            r = random.random()
            if self.read_counter > 100:
                time.sleep(2+r)
                print('Too many requests 1')
            if self.read_counter > 150:
                time.sleep(3+r)
                print('Too many requests 2')
            if self.read_counter > 200:
                time.sleep(4+r)
                print('Too many requests 3')
            if self.read_counter > 250:
                time.sleep(30+r)
                print('Too many requests 3')

            while self.critical_flag:
                access_count += 1
                time.sleep(1 + r)
                print('Access is closed, wait for ' + str(1+r) + ' count = ' + str(access_count))
                if access_count > 20:
                    self.critical_flag = False

            self.critical_flag = True
            try:
                res = function_to_decorate(self, *args, **kwargs)
            except Exception as err:
                self.critical_flag = False
                print('Error in google sheet access: ' + str(err))

            self.critical_flag = False
            return res
        return wrapper

    @my_shiny_new_decorator
    def __resetAccessCounter(self):
        threading.Timer(60.0, self.__resetAccessCounter).start()
        print('Access counter, read: ' + str(self.read_counter))
        self.read_counter  = 0
        self.write_counter = 0
        self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                          range='pupils' + '!' + 'A1:Z1').execute()['values'][0]


    @my_shiny_new_decorator
    def __reconnect(self):
        threading.Timer(300.0, self.__reconnect).start()
        self.httpAuth = self.credentials.authorize(httplib2.Http())  # Авторизуемся в системе
        self.service = apiclient.discovery.build('sheets', 'v4',
                                                 http=self.httpAuth)  # Выбираем работу с таблицами и 4 версию API


    def refresh(self):
        self.pupils_id = self.getAllPupilColumns(['id'])[0]
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

        if self.header is None:
            self.read_counter += 1
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
        myheader = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z4').execute()['values']

        all_user_id = self.pupils_id
        if self.pupils_id == None:
            self.pupils_id = self.getAllPupilColumns(['id'])[0]

        if not(str(id) in all_user_id):
            return None
        u_row = str(all_user_id.index(str(id))+4+1)
        record = self.getValue(sheetName, 'A' + u_row + ':' + 'Z' + u_row)[0]

        myheader.append(record)

        return myheader


    @my_shiny_new_decorator
    def setFieldValues(self, id, values, fieldnames, key_column='id', sheetName='pupils'):
        print('setFieldValuessss')

        # print('Before read header!')
        if self.header is None:
            self.read_counter += 1
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]

        all_keys_collumn = self.pupils_id
        if key_column != 'id':
            all_keys_collumn = self.getAllPupilColumns([key_column])[0]
        elif self.pupils_id == None:
            self.pupils_id = self.getAllPupilColumns([key_column])[0]
            all_keys_collumn = self.pupils_id

        if not (str(id) in all_keys_collumn):
            return None

        u_row = str(all_keys_collumn.index(str(id)) + 4 + 1)
        body  = {'valueInputOption': 'RAW', 'data': []}
        for fn,v in zip(fieldnames,values):
            if fn in self.header:
                j = self.header.index(fn)
                letter = self.alphabet[j]
                body['data'].append({'range': sheetName + '!' + letter + u_row, 'values': [[v]]})
            pass
        self.write_counter += 1
        self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.spreadsheetId, body=body).execute()

        return None

    def setFieldValue(self, id, value, fieldname, key_column='id',sheetName='pupils'):
        print('setFieldValue')
        #print('Before read header!')
        if self.header is None:
            self.read_counter += 1
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

        resp = None
        self.write_counter += 1
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
            self.read_counter += 1
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        all_keys = self.pupils_id
        if self.pupils_id == None:
            self.pupils_id = self.getAllPupilColumns(['id'])[0]
            all_keys = self.pupils_id

        if not (str(id) in all_keys):
            return None
        u_row = str(all_keys.index(str(id)) + 4 + 1)
        result = self.getValue(sheetName, 'A' + u_row + ':' + 'Z' + u_row)[0]
        pupil_info = {}
        for k, r in zip(self.header, result):
            j = self.header.index(k)
            pupil_info[k] = r

        return pupil_info
    @my_shiny_new_decorator
    def getAllValue(self, sheetName):
        print('getAllValue')
        # self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        rng = sheetName + '!' + 'A1:Z999'
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

        if self.header is None:
            self.read_counter += 1
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        columns_ids = []
        for c in columns:
            columns_ids.append(self.header.index(c))

        self.read_counter += 1
        res = None
        try:
            res = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                       range=sheetName + '!' + 'A5:'  + 'Z999').execute()
        except Exception as err:
            print('!!!!!!!!!!!!This is you exception')
            pass

        result = []
        if not 'values' in res:
            result.append([])
            return result

        for ci in columns_ids:
            res_col = [col[ci] for col in res['values']]
            result.append(res_col)

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
        self.write_counter += 1
        resp = self.service.spreadsheets().batchUpdate(spreadsheetId = self.spreadsheetId, body=resource).execute()
        self.pupils_id = self.getAllPupilColumns(['id'])[0]
        return resp

    def addPupil(self, pupil_info, sheetName='pupils'):
        print('addPupil')
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)

        ids = self.pupils_id
        if self.pupils_id == None:
            self.pupils_id = self.getAllPupilColumns(['id'])[0]
            ids = self.pupils_id

        pupil_info['alingment'] = 0
        #self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,range=sheetName + '!' + 'A5:A9999').execute()
        #ids = flatten(ids['values'])
        if str(pupil_info['id']) in ids:
            return None

        if self.header is None:
            self.read_counter += 1
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        pupil_spreadsheet = {'values':[[]]}
        for inf in self.header:
            if inf in pupil_info:
                pupil_spreadsheet['values'][0].append(pupil_info[inf])
            else:
                pupil_spreadsheet['values'][0].append('')

        self.write_counter += 1
        resp = self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheetId,
            range="pupils!A1",
            valueInputOption="RAW",
            body=pupil_spreadsheet).execute()

        self.pupils_id = self.getAllPupilColumns(['id'])[0]

        return resp

