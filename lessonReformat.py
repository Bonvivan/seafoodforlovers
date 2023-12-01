import googleSheetTest
import json
import re

TITLE_TOKEN = 'LEZIONE'
NUM_START   = 3
ROW_START   = 5

state_f = open('resources/tokens.json', 'r')
tokens = json.load(state_f)
state_f.close()

lesson_table = googleSheetTest.GoogleTableReader(tokens['gsheet'])

old_lessons = lesson_table.getAllValue(sheetName='old_lesson')

old_lessons = old_lessons[1:]

start_row = -1
for row in old_lessons:
    start_row += 1
    if len(row)<2:
        continue
    text = row[2]
    text = text.split('--new-message--')
    l_number = re.match('.*LEZIONE\s*(\d+).\d+.*', text[0])
    if  l_number is None:
        continue
    if int(l_number.group(1)) == NUM_START:
        break

old_lessons = old_lessons[start_row:]

for row in old_lessons:
    if len(row)<2:
        continue
    answer = row[1]
    pattern = r'(LEZIONE)* ?(\d+)\.( ?\d)\.? *(.*)\n+'
    repl = r'RISPOSTE \2.\3.\4\n'
    answer1 = re.sub(pattern, repl, answer)

    answer2 = row[2]
    pattern = r'(LEZIONE)* ?(\d+)\.( ?\d?)\.? *(.*)\n+'
    repl = r'RISPOSTE \2.\3.\4\n'
    answer1 = re.sub(pattern, repl, answer)

    row[1], row[2] = row[2], answer1
    pass

row_id = ROW_START-1
ii=0
for row in old_lessons:
    row_id += 1
    if len(row)<2:
        continue
    if row[2]=='':
        row[1] = row[1] + '\n' + '[[//chekme;lezione_A1!C' + str(row_id) + ';/ucommand]]'
    else:
        row[1] = row[1] + '\n' + '[[//le_risposte;lezione_A1!B' + str(row_id) + ';/ucommand]]'
    row.append('')
    row.append('')
    row[3] = 'Урок отправлен на проверку, спасибо! 🥳🥳🥳\n[[//checked;lezione_A1!D' + str(row_id) + ';/tcommand]]'
    row[4] = 'Урок проверен. 🥳🥳🥳\n[[Следующий урок;lezione_A1!A' + str(row_id+1) + ';/tomorrow]]'
    old_lessons[ii] = row[1:5]
    ii+=1

lesson_table.setValue(old_lessons, 'tmp', 'A5:Z999')

print('END')
