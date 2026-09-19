"""Сверка данных макета (data/*.js) с живыми страницами 126.en.cx.

Для каждого значения, которое показывает сайт, проверяет, что оно есть
на соответствующей странице исходника. Печатает только расхождения.
Запуск:  python tools/verify.py
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scrape as S

sys.stdout.reconfigure(encoding='utf-8')
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
problems, checks = [], 0


def load(name):
    s = open(os.path.join(D, name + '.js'), encoding='utf-8').read()
    return json.loads(s.split('=', 1)[1].strip().rstrip(';'))


def norm(t):
    t = re.sub(r'\s+', ' ', (t or '').replace('\xa0', ' ')).strip()
    return re.sub(r'\s*([(),])\s*', r'\1', t)  # «( 5 человек )» и «(5 человек)» — одно и то же


def page_text(path):
    return norm(S.txt(S.soup(S.get(path))))


def expect(where, value, text, label):
    global checks
    v = norm(str(value))
    if not v:
        return
    checks += 1
    if v not in text:
        problems.append(f'[{where}] {label}: «{v}» нет на исходнике')


# ---------- главная
home = load('home')
t = page_text('')
for p in home['players']:
    for k in ('name', 'points', 'rank'):
        expect('главная/игроки', p[k], t, f"#{p['pos']} {k}")
for tm in home['teams']:
    for k in ('name', 'points', 'members', 'captain'):
        expect('главная/команды', tm[k], t, f"#{tm['pos']} {k}")
for g in home['games']:
    expect('главная/анонсы', g['title'], t, f"игра {g['id']}")
st = home['stats']
for k in ('projectUsers', 'projectTeams', 'domainUsers', 'domainTeams', 'newbies'):
    expect('главная/цифры', st[k], t, k)
# порядок топов
for key, lst, start in (('игроки', home['players'], 'ТОП 5 личного состава'), ('команды', home['teams'], 'ТОП 5 команд')):
    sec = t[t.find(start):]
    pos = [sec.find(norm(x['name'])) for x in lst]
    if pos != sorted(pos):
        problems.append(f'[главная/{key}] порядок не совпадает с исходником')

# ---------- страницы игр
games = load('games')['games']
for gid, g in games.items():
    t = page_text(f'GameDetails.aspx?gid={gid}')
    expect(f'игра {gid}', g['title'], t, 'название')
    expect(f'игра {gid}', g['type'], t, 'тип')
    if g['num']:
        expect(f'игра {gid}', f"#{g['num']}", t.replace('(# ', '(#'), 'номер')
    for a in g['authors']:
        expect(f'игра {gid}', a['name'], t, 'автор')
    for k, v in g['fields']:
        if k == 'Времени осталось':
            continue  # таймер, на сайте считается вживую
        expect(f'игра {gid}', k, t, 'поле')
        expect(f'игра {gid}', re.sub(r'\s*\(UTC\+3\)', '', v), t.replace('( UTC +3)', '').replace('(UTC +3)', ''), k)
    for tm in g['accepted']:
        expect(f'игра {gid}', tm['name'], t, 'команда в заявке')
    for row in g['top10']['rows']:
        for cell in row[1:]:
            expect(f'игра {gid}/ТОП-10', cell, t, f'место {row[0]}')

# ---------- архив
arch = load('archive')
texts = {}
for p in range(1, 4):
    texts[p] = page_text(f'Games.aspx?page={p}')
allarch = ' '.join(texts.values())
for g in arch['games']:
    for k in ('title', 'date', 'q', 'k', 'aks', 'winner', 'teams'):
        expect(f"архив {g['id']}", g[k], allarch, k)
    for a in g['authors']:
        expect(f"архив {g['id']}", a, allarch, 'автор')
ids = [g['id'] for g in arch['games']]
src_ids = []
for p in range(1, 4):
    src_ids += [S.gid_of(a['href']) for a in S.soup(S.get(f'Games.aspx?page={p}')).select('a[id=lnkGameTitle]')]
if ids != src_ids:
    problems.append('[архив] порядок/состав игр не совпадает с исходником')

# ---------- авторы
auth = load('authors')
s = S.soup(S.get('GameAuthors.aspx?sid=678'))
src_rows = {}
for tr in s.select('tr'):
    a = tr.select_one('a[href*="UserDetails"]')
    tds = tr.find_all('td', recursive=False)
    if a and len(tds) >= 10:
        src_rows[a.get_text(strip=True)] = [S.txt(td) for td in tds[2:10]]
for r in auth['rows']:
    checks += 1
    if src_rows.get(r['name']) != r['scores']:
        problems.append(f"[авторы] {r['name']}: у нас {r['scores']}, на исходнике {src_rows.get(r['name'])}")
if len(src_rows) != len(auth['rows']):
    problems.append(f"[авторы] на исходнике {len(src_rows)} авторов, у нас {len(auth['rows'])}")

# ---------- статистика
stt = load('stats')
t = page_text('Statistics.aspx')
for n in re.findall(r'\d[\d ]*\d', stt['text']):
    expect('статистика', n, t, 'число')
for u in stt['last']:
    expect('статистика/регистрации', u['name'], t, u['id'])

print(f'Проверено значений: {checks}')
print(f'Расхождений: {len(problems)}')
for p in problems:
    print(' -', p)
