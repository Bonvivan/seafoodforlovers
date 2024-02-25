import googleSheetTest
import json
import re

TITLE_TOKEN = 'LEZIONE'
NUM_START   = 3
ROW_START   = 3

state_f = open('resources/tokens.json', 'r')
tokens = json.load(state_f)
state_f.close()

lesson_table = googleSheetTest.GoogleTableReader(tokens['gsheet'])

old_lessons = lesson_table.getAllValue(sheetName='lsn_tmp')

#old_lessons = old_lessons[1:]

start_row = -1
'''
[[;lezione_B2!E1;/reminder:420;???curr_lesson???<=1]]
[[;lezione_B2!F1;/reminder:420;???curr_lesson???==2]]
[[;lezione_B2!G1;/reminder:420;???curr_lesson???==3]]
'''

'''
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
'''
'''

k = 0
for row in old_lessons:
    print(k)
    k+=1
    for k in range(3):
        i = 0
        answer = row[i]
        pattern = r'\[\[.*\;lezione.+]\]\n?'
        repl = r''
        answer1 = re.sub(pattern, repl, answer)
        pattern = r'\[\[.*\;lezione.+]\]\n?'
        row[i] = answer1
        break
    pass
'''

row_id = 0
for row in old_lessons:
    row_id += 1
    if len(row)<2:
        continue
    row[0] += ("[[;lezione_B2!E1;/reminder:240;???curr_lesson???<=1]]"
               "\n[[;lezione_B2!F1;/reminder:240;???curr_lesson???==2]]"
               "\n[[;lezione_B2!G1;/reminder:240;???curr_lesson???==3]]")
    row[3] = 'Урок проверен. 🥳🥳🥳\n[[Следующий урок;lezione_B2!A' + str(row_id + 1) + ';/tomorrow;???payment_info???>\'\']]\n'
    row[3] += '[[Следующий урок;lezione_B2!A' + str(row_id + 1) + ';/nextl;???payment_info???==\'\']]\n'
    row[3] += '[[//prossima;lezione_B2!A' + str(row_id + 1) + ';/tcommand]]\n'
    row[3] += '[[//prossima;lezione_B2!A' + str(row_id + 1) + ';/ucommand]]\n'
    if row[1] != '':
        row[3] += '[[//le_risposte;lezione_B2!B' + str(row_id) + ';/tcommand]]\n'

'''
row_id = 0
ii=0
for row in old_lessons:
    row_id += 1
    if len(row)<2:
        continue
    if row[1]=='' or True:
        row[0] += '--new-message--\n'
        row[0] += '🤖 Напишите мне в ответном сообщении <b>//controlla</b>, и я отправлю Ваш урок на проверку преподавателю.\n'
        #row[0] += '🤖 /status чтоб увидеть список всех доступных комманд.\n'
        row[0] += '[[//controlla;lezione_B2!C'   + str(row_id) + ';/ucommand]]\n'
        row[0] += '[[//controllato;lezione_B2!D' + str(row_id) + ';/tcommand]]\n'
    if row[1] != '':
        #row[1] += '\n--new-message--\n'
        #row[1] += '🤖 Отправьте мне в сообщении <b>//le_risposte</b>, и я пришлю Вам ответы\n'
        row[0] += '[[//le_risposte;lezione_B2!B' + str(row_id) + ';/tcommand]]'
    row.append('')
    row.append('')
    row[2] = 'Урок отправлен на проверку, спасибо! 🥳🥳🥳\n[[//controllato;lezione_B2!D' + str(row_id) + ';/tcommand]]\n'
    if row[1] != '':
        row[2] += '[[//le_risposte;lezione_B2!B' + str(row_id)  + ';/tcommand]]\n'
    row[2] += '[[//prossima;lezione_B2!A' + str(row_id + 1) + ';/tcommand]]\n'
    row[2] += '[[//prossima;lezione_B2!A' + str(row_id + 1) + ';/ucommand]]\n'
    row[3] = 'Урок проверен. 🥳🥳🥳\n[[Следующий урок;lezione_B2!A' + str(row_id+1) + ';/tomorrow]]\n'
    row[3] += '[[//prossima;lezione_B2!A' + str(row_id + 1) + ';/tcommand]]\n'
    row[3] += '[[//prossima;lezione_B2!A' + str(row_id + 1) + ';/ucommand]]\n'
    if row[1] != '':
        row[3] += '[[//le_risposte;lezione_B2!B' + str(row_id)  + ';/tcommand]]\n'

    old_lessons[ii] = row[0:4]
    ii+=1

'''
lesson_table.setValue(old_lessons, 'lsn_tmp_res', 'A1:Z999')

print('END')
