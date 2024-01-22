import googleSheetTest
import json
import re

TITLE_TOKEN = 'LEZIONE'
NUM_START   = 3
ROW_START   = 3

state_f = open('resources/tokens.json', 'r')
tokens = json.load(state_f)
state_f.close()

test_q = open('resources/test_q.txt', 'r', encoding='utf-8')
test_a = open('resources/answers.txt', 'r', encoding='utf-8')
test_txt = test_q.read()
answers = test_a.read()
answers = answers.split('\n')
test_len = []
name_of_level = ['A1','A2','B1','B2']
quest_1 = test_txt.split('A1')
test_len.append(len(quest_1) - 1)
quest_2 = quest_1[-1].split('A2')
test_len.append(len(quest_2))
quest_3 = quest_2[-1].split('B1')
test_len.append(len(quest_3))
quest_4 = quest_3[-1].split('B2')
test_len.append(1000)

quest = quest_1[:-1] + quest_2[:-1] + quest_3[:-1] + quest_4
quest = quest[1:]
#pattern = r'A1\n\n(\d)+.\s(.)+'

#q_list = re.findall(pattern, test_txt)

q_list = []
a_list = []

q_pattern = '(\d)+(.+)\n\n(\w\.\s.+\n+\w\.\s.+\n\w\.\s.+\nне знаю)'
for q in quest:
    qst = re.match(q_pattern, q.strip())
    q_list.append(qst[2][1:].strip())
    ans = qst[3].strip()
    ans = ans.split('\n')
    a_list.append(ans)
    pass

all_cells = []
all_cells_answer = [[],[],[],[]]
answers_ref = ['a','b','c']
levels = ['A1', 'A2', 'B1', 'B2']
answers_id = []

for a in answers:
    answers_id.append(answers_ref.index(a.strip()[-1]))

count = 1
count_of_level = 0
level_count = 0
level_end = test_len[0]
for q,a in zip(q_list, a_list):
    count+=1
    level_count+=1

    if level_count>=level_end:
        level_count=1
        count_of_level+=1
        level_end = test_len[count_of_level]

    all_cells_answer[0].append(name_of_level[count_of_level] + '_' + str(level_count))
    all_cells_answer[1].append('test_q!A' + str(count-1))
    all_cells_answer[2].append(0)
    all_cells_answer[3].append(a[answers_id[count-2]])

    cell_test = levels[count_of_level] + '.' + str(level_count) + '. '
    cell_test += q + '\n'

    too_long = False
    for aa in a:
        if len(aa)>23:
            too_long = True
            break

    for i in range(len(a)-1):
        aa = a[i]
        if too_long:
            cell_test = cell_test + aa + '\n'
            a[i] = (a[i][:3]).strip()

    for aa in a[:-1]:
        cell_test += '[[' + aa + ';test_q!A' + str(count)+ ';/check' + ']]\n'
    cell_test += '[[' + a[-1] + ';test_q!A' + str(count) + ';' + ']]\n'
    if count>2:
        cell_test += '[[вернуться назад;' + 'test_q!A' + str(count-2) + ';/back]]'


    all_cells.append([cell_test])

test_table = googleSheetTest.GoogleTableReader(tokens['gsheet'])

test_table.setValue(all_cells, 'test_q', 'A1:Z99')
#test_table.setValue(all_cells_answer, 'test_results', 'G1:BZ99')

print('END')

exit(0)