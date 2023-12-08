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

    answer = row[2]
    pattern = r'(LEZIONE)* ?(\d+)\.( ?\d?)\.? *(.*)\n+'
    repl = r'LEZIONE \2.\3.\n\4\n\n'
    answer2 = re.sub(pattern, repl, answer)

    row[1], row[2] = answer2, answer1
    pass

row_id = ROW_START-1
ii=0
for row in old_lessons:
    row_id += 1
    if len(row)<2:
        continue
    if row[2]=='' or True:
        row[1] +=  '\n--new-message--\n'
        row[1] += '🤖 Напишите мне в ответном сообщении <b>//controlla</b>, и я отправлю Ваш урок на проверку преподавателю.\n'
        row[1] += '[[//controlla;lezione_A1!C' + str(row_id) + ';/ucommand]]'
        row[1] += '\n🤖 Напишите <b>//prossima</b>, чтоб получить следующий урок вне очереди.\n'
        row[1] += '[[//prossima;lezione_A1!C' + str(row_id+1) + ';/ucommand]]'
    else:
        row[1] += '\n--new-message--\n'
        row[1] += '🤖 Отправьте мне в сообщении <b>//le_risposte</b>, и я пришлю Вам ответы\n'
        row[1] += '[[//le_risposte;lezione_A1!B' + str(row_id) + ';/ucommand]]'
    row.append('')
    row.append('')
    row[3] = 'Урок отправлен на проверку, спасибо! 🥳🥳🥳\n[[//controllato;lezione_A1!D' + str(row_id) + ';/tcommand]]'
    row[4] = 'Урок проверен. 🥳🥳🥳\n[[Следующий урок;lezione_A1!A' + str(row_id+1) + ';/tomorrow]]'
    old_lessons[ii] = row[1:5]
    ii+=1

lesson_table.setValue(old_lessons, 'tmp', 'A5:Z999')

print('END')
