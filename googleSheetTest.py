#seafoodforlovers@seafoodforlovers.iam.gserviceaccount.com

import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
import threading

import time

import json


def flatten(l):
    return [item for sublist in l for item in sublist]
class GoogleTableReader():
    CREDENTIALS_FILE = 'resources/seafoodforlovers-451d571f02c4.json'
    credentials = None

    read_counter = 0

    header = None

    critical_flag = False

    def __init__(self, spreadsheetId):
        self.alphabet = list(map(chr, range(ord('A'), ord('Z')+1)))
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name(self.CREDENTIALS_FILE,
                                                                       ['https://www.googleapis.com/auth/spreadsheets',
                                                                        'https://www.googleapis.com/auth/drive'])
        self.httpAuth = self.credentials.authorize(httplib2.Http())  # Авторизуемся в системе
        self.service  = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)  # Выбираем работу с таблицами и 4 версию API
        self.spreadsheetId = spreadsheetId

        print('Created reader for:' + 'https://docs.google.com/spreadsheets/d/' + spreadsheetId)

        threading.Timer(60.0, self.__resetAccessCounter).start()
        pass

    def my_shiny_new_decorator(function_to_decorate):
        def wrapper(self, *args, **kwargs):
            while self.critical_flag:
                time.sleep(1)

            self.critical_flag=True
            res = function_to_decorate(self, *args, **kwargs)
            self.critical_flag=False
            return res
        return wrapper

    @my_shiny_new_decorator
    def __resetAccessCounter(self):
        print('Access counter, read: ' + str(self.read_counter))
        self.read_counter = 0
        self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        self.httpAuth = self.credentials.authorize(httplib2.Http())  # Авторизуемся в системе
        self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                          range='pupils' + '!' + 'A1:Z1').execute()['values'][0]
        threading.Timer(30.0, self.__resetAccessCounter).start()

    def giveAccess(self, email, role='writer'):
        access = self.service.permissions().create(
            fileId=self.spreadsheetId,
            body={'type': 'user', 'role': role, 'emailAddress': email},
            # Открываем доступ на редактирование
            fields='id'
        ).execute()

    def getFieldValue(self, id, fieldname, sheetName='pupils'):
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        self.read_counter += 1
        if self.header is None:
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                          range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        all_user_id = self.getAllPupilColumns(['id'])[0]
        if not(str(id) in all_user_id):
            return None
        u_row = str(all_user_id.index(str(id))+4+1)
        if fieldname in self.header:
            j = self.header.index(fieldname)
            letter=self.alphabet[j]
            result = self.getValue(sheetName, letter+u_row+':'+letter+u_row)
            return result[0][0]

        return None

    #TODO add decorator to prevent overcounting of requests


    def setFieldValue(self, value, id, fieldname, sheetName='pupils'):
        self.read_counter += 1
        #print('Before read header!')
        if self.header is None:
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        #print('Header readen!')

        all_user_id = self.getAllPupilColumns(['id'])[0]

        if not(str(id) in all_user_id):
            return None
        u_row = str(all_user_id.index(str(id))+4+1)
        if fieldname in self.header:
            j = self.header.index(fieldname)
            letter=self.alphabet[j]
            self.setValue([value], sheetName, letter+u_row)
            pass

        return None

    @my_shiny_new_decorator
    def setValue(self, value, sheetName, cellRange):
        rng = sheetName + '!' + cellRange

        body = {}
        body['values'] = [value]
        self.read_counter += 1
        resp = self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheetId,
            range=rng,
            valueInputOption="RAW",
            body=body).execute()

        return resp

    @my_shiny_new_decorator
    def getValue(self, sheetName, cellRange):
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
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        rng = address
        self.read_counter += 1
        results = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId, range=rng).execute()
        sheet_values = results['values']
        return sheet_values

    @my_shiny_new_decorator
    def getAllPupilColumns(self, columns, sheetName='pupils'):
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)

        if len(columns)<1:
            return []

        self.read_counter += 1
        if self.header is None:
            self.header = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheetId,
                                                                   range=sheetName + '!' + 'A1:Z1').execute()['values'][0]
        columns_ids = []
        for c in columns:
            columns_ids.append(self.header.index(c))

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
        return result

    @my_shiny_new_decorator
    def getPupilStruct(self, sheetName='pupils'):
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


    def addPupil(self, pupil_info, sheetName='pupils'):
        #self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)
        self.read_counter += 1
        ids = self.getAllPupilColumns(['id'])[0]
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



