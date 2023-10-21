import re

url = 'https://www.dropbox.com/scl/fi/wns3g91prxx2iukl10cz7/lesson_1A1.MOV?rlkey=rzc719j0hu0i0wdxn7ds2zysl&dl=0'
z = re.findall('https://[a-zA-Z0-9.-_@/]+/([a-zA-Z0-9.-_]+.[a-zA-Z0-9])\?\S+', url)

print(z)