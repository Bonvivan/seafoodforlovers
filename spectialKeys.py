from telebot import types

def createKeyFromContent(user_status, content):
    btns = []
    for b, addr, sp in zip(*content[1:]):
        if sp=='/saveuser':
            callback = 'saveuser;' + '' + ';' + user_status + ';' + addr
            btns.append(types.InlineKeyboardButton('Начать опрос', callback_data=callback))
            continue
        if sp=='/edit':
            pass
        if sp=='/delete_me':
            pass
        if sp==None:
            callback = 'ahd;' + b + ';' + user_status + ';' + addr
            btns.append(types.InlineKeyboardButton(b, callback_data=callback))

    return btns
#types.InlineKeyboardButton