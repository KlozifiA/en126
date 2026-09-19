"""Собирает данные с 126.en.cx в data/*.js для редизайна.

Запуск:  python tools/scrape.py
Нужен beautifulsoup4 (pip install beautifulsoup4).
Скрипт читает только публичные страницы (без входа).
"""
import json, re, sys, time, os, urllib.request as ur
from datetime import datetime, timezone
from bs4 import BeautifulSoup, NavigableString

sys.stdout.reconfigure(encoding='utf-8')
BASE = 'https://126.en.cx/'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
os.makedirs(OUT, exist_ok=True)


def get(path, pause=.35):
    time.sleep(pause)
    req = ur.Request(BASE + path.lstrip('/'), headers={'User-Agent': 'Mozilla/5.0 (en126-redesign)'})
    return ur.urlopen(req, timeout=30).read().decode('utf-8', 'replace')


def soup(html):
    s = BeautifulSoup(html, 'html.parser')
    for t in s(['script', 'noscript']):
        t.decompose()
    return s


def txt(el):
    return re.sub(r'\s+', ' ', el.get_text(' ') if el else '').strip()


def save(name, var, obj):
    p = os.path.join(OUT, name + '.js')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(f'window.{var}=' + json.dumps(obj, ensure_ascii=False) + ';\n')
    print('saved', p, os.path.getsize(p))


def gid_of(href):
    m = re.search(r'gid=(\d+)', href or '')
    return int(m.group(1)) if m else None


def uid_of(href):
    m = re.search(r'[ut]id=(\d+)', href or '')
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- home
def scrape_home():
    s = soup(get(''))
    games = []
    for box in s.select('.boxGameInfo'):
        a = box.select_one('#lnkGameTitle, a[ID=lnkGameTitle], a.yellow_darkgreen19')
        if not a:
            continue
        gid = gid_of(a['href'])
        if any(g['id'] == gid for g in games):
            continue
        tname = txt(box.select_one('[id$=lblGameTypeName]'))
        games.append({'id': gid, 'type': tname, 'title': a.get_text(strip=True)})
    # Карточки-анонсы (с картинками, датами и числом команд) — плитка сверху
    tiles = {}
    for a in s.select('a[href*="GameDetails.aspx?gid="]'):
        gid = gid_of(a['href'])
        img = a.find('img', src=re.compile(r'data/games|default-\d'))
        t = a.get_text('\n', strip=True).split('\n')
        if img and gid not in tiles:
            tiles[gid] = {'img': img['src'], 'raw': t}
    for g in games:
        tl = tiles.get(g['id'])
        if tl:
            g['img'] = tl['img'] if 'data/games' in tl['img'] else None
            raw = tl['raw']
            m = [x for x in raw if re.match(r'\d\d\.\d\d\.\d\d, \d\d:\d\d', x)]
            g['short'] = m[0] if m else ''
            try:
                g['teams'] = int(raw[raw.index('Команд:') + 1])
            except Exception:
                g['teams'] = None
    # ТОПы
    def top(title):
        span = s.find(string=re.compile(title))
        table = span.find_next('table')
        rows = []
        for tr in table.select('tr'):
            links = tr.select('a[href*="Details.aspx"]')
            if not links:
                continue
            rank_img = tr.select_one('img.rank')
            t = txt(tr)
            m = re.search(r'\(#\s*(\d+)\s*\)', t)
            pts = re.search(r'\(\s*([\d\s ,]+)\s*очк', t)
            rows.append({
                'pos': int(m.group(1)) if m else None,
                'name': links[0].get_text(strip=True), 'id': uid_of(links[0]['href']),
                'points': pts.group(1).replace('\xa0', ' ').strip() if pts else '',
                'rank': rank_img['title'] if rank_img else None,
                'rankImg': rank_img['src'] if rank_img else None,
                'members': (lambda x: int(x.get_text()) if x else None)(tr.select_one('span[title="Количество участников в команде"]')),
                'captain': links[1].get_text(strip=True) if len(links) > 1 else None,
                'captainId': uid_of(links[1]['href']) if len(links) > 1 else None,
                'rankText': (re.search(r'очка?, ([^)]+)\)', t).group(1) if re.search(r'очка?, ([^)]+)\)', t) else None),
            })
        return rows
    players = top('ТОП 5 личного состава')
    teams = top('ТОП 5 команд')
    body = txt(s)
    num = lambda pat: re.search(pat, body).group(1).replace('\xa0', ' ') if re.search(pat, body) else ''
    N = r'([\d\s ]+?)'
    stats = {
        'projectUsers': num(r'Всего в проекте\s*:\s*' + N + r'\s*участник'),
        'projectTeams': num(r'Всего в проекте.*?\)\s*,\s*' + N + r'\s*команд'),
        'domainUsers': num(r'Всего в домене\s*:\s*' + N + r'\s*участник'),
        'domainTeams': num(r'Всего в домене.*?\)\s*,\s*' + N + r'\s*команд'),
        'guests': num(r'Сейчас на сайте\s*:\s*' + N + r'\s*гост'),
        'online': num(r'гост\w*\s*,\s*' + N + r'\s*участник'),
        'newbies': num(r'Новобранцы за неделю\s*:\s*' + N + r'\s*участник'),
    }
    stats = {k: re.sub(r'\s+', ' ', v).strip() for k, v in stats.items()}
    return {'games': games, 'players': players, 'teams': teams, 'stats': stats}


# ---------------------------------------------------------------- game details
ALLOWED = {'p', 'br', 'b', 'strong', 'i', 'em', 'u', 'ul', 'ol', 'li', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5',
           'h6', 'blockquote', 'table', 'tr', 'td', 'th', 'tbody', 'thead', 'span', 'div', 'hr'}


def clean_html(nodes):
    """Очищает авторское описание: оставляет текст, списки, ссылки, картинки."""
    frag = BeautifulSoup('<div></div>', 'html.parser')
    root = frag.div
    for n in nodes:
        root.append(n.__copy__() if not isinstance(n, NavigableString) else NavigableString(str(n)))
    for t in root.find_all(['style', 'script', 'iframe', 'svg', 'form', 'input', 'button', 'link', 'meta']):
        t.decompose()
    for t in root.find_all(True):
        if t.name not in ALLOWED:
            t.unwrap()
            continue
        keep = {}
        if t.name == 'a' and t.get('href'):
            href = t['href']
            if href.startswith('/'):
                href = BASE.rstrip('/') + href
            if href.startswith('http'):
                keep = {'href': href, 'target': '_blank', 'rel': 'noopener'}
        if t.name == 'img' and t.get('src', '').startswith('http'):
            keep = {'src': t['src'], 'alt': '', 'loading': 'lazy'}
        t.attrs = keep
        if t.name in ('span', 'div'):
            t.unwrap()
    html = str(root)[5:-6]
    html = re.sub(r'(<p>\s*(&nbsp;|\xa0)?\s*</p>\s*)+', '', html)
    html = re.sub(r'(<br/?>\s*){3,}', '<br><br>', html)
    return html.strip()


def scrape_game(gid):
    h = get(f'GameDetails.aspx?gid={gid}')
    s = soup(h)
    info = s.select_one('table.gameInfo')
    if not info:
        return None
    g = {'id': gid}
    g['type'] = txt(info.select_one('[id$=lblGameTypeName]'))
    g['num'] = txt(info.select_one('[id$=lblGameNum]'))
    g['title'] = txt(info.select_one('#lnkGameTitle, a[ID=lnkGameTitle]'))
    hl = next((x for x in info.select('a[href*="HowTo.aspx?about="]') if 'about=UTC' not in x['href']), None)
    g['help'] = re.search(r'about=(\w+)', hl['href']).group(1) if hl else None
    topic = info.select_one('a[ID=lnkGbTopic]')
    g['topic'] = BASE + topic['href'].lstrip('/') if topic else None
    g['authors'] = [{'name': a.get_text(strip=True), 'id': uid_of(a['href'])}
                    for a in info.select('a[id*=AuthorsRepeater]')]
    fields = []
    for tr in info.find_all('tr', recursive=True):
        tds = tr.find_all('td', recursive=False)
        if len(tds) != 1:
            continue
        td = tds[0]
        lab = td.select_one('span.title')
        if not lab:
            continue
        label = txt(lab).rstrip(':').strip()
        full = txt(td)
        value = full[len(txt(lab)):].strip()
        if label.startswith('Автор'):
            continue
        value = value.replace('( UTC +3)', '(UTC+3)').replace('(UTC +3)', '(UTC+3)')
        fields.append([label, value])
    g['fields'] = fields
    acc = info.find(string=re.compile('Приняты к участию'))
    g['accepted'] = []
    if acc:
        box = acc.parent
        g['accepted'] = [{'name': a.get_text(strip=True), 'id': uid_of(a['href'])}
                         for a in box.select('a[href*="TeamDetails"], a[href*="UserDetails"]')]
    # ТОП-10
    top = []
    for tr in s.select('tr.toWinnerItem, tr.toWinnerAltItem'):
        tds = tr.find_all('td', recursive=False)
        cells = [txt(td) for td in tds]
        top.append(cells)
    head = s.select_one('tr.topWinnerHead')
    g['top10'] = {'head': [txt(td) for td in head.find_all('td', recursive=False)] if head else [], 'rows': top}
    enter = s.select_one('a[href*="gameengines/encounter/play"]')
    g['enter'] = BASE + enter['href'].lstrip('/') if enter else None
    fee = s.select_one('#lnkMakeGameFee')
    g['feeLink'] = BASE + fee['href'].lstrip('/') if fee else None
    for f in g['fields']:
        f[1] = re.sub(r'\s*подать заявку на участие', '', f[1])
        f[1] = re.sub(r'\(\s+', '(', re.sub(r'\s+\)', ')', f[1]))
    g['fields'] = [f for f in g['fields'] if f[0] not in ('Начало игры в вашей временной зоне',)]
    # Описание автора: вводная часть + вкладки (как в авторском виджете game-tabs)
    lbl = s.find(id='lblFromAuthor')
    g['intro'], g['tabs'], g['img'] = '', [], None
    if lbl:
        nodes = []
        for sib in lbl.next_siblings:
            if getattr(sib, 'get', None) and sib.get('id') == 'lblPhotoGalleries':
                break
            nodes.append(sib)
        wrap = BeautifulSoup('<div></div>', 'html.parser').div
        for n in nodes:
            wrap.append(n.__copy__() if not isinstance(n, NavigableString) else NavigableString(str(n)))
        block = wrap.select_one('.game-tabs--block')
        if block:
            names = [txt(b) for b in block.select('.game-tabs--sidebar .game-tabs--button__name')] or                     [txt(b) for b in block.select('.game-tabs--sidebar .game-tabs--button')]
            icons = [(b.find('img') or {}).get('src') for b in block.select('.game-tabs--sidebar .game-tabs--button')]
            contents = block.select('.game-tabs--content-tab')
            g['tabs'] = [{'name': n, 'icon': ic, 'html': clean_html(list(c.contents))}
                         for n, ic, c in zip(names, icons, contents)]
            block.decompose()
        for extra in wrap.select('.game-tabs--bottons-mobile, [class*="game-tabs"]'):
            extra.decompose()
        g['intro'] = re.sub(r'^(\s*<br/?>\s*)+', '', clean_html(list(wrap.contents)))
        m = re.search(r'src="(https://[^"]+/data/games/[^"]+)"', g['intro'] + ''.join(t['html'] for t in g['tabs']))
        g['img'] = m.group(1) if m else None
    return g


# ---------------------------------------------------------------- help «(?)»
def help_key(gid):
    s = soup(get(f'GameDetails.aspx?gid={gid}'))
    info = s.select_one('table.gameInfo')
    hl = next((x for x in info.select('a[href*="HowTo.aspx?about="]') if 'about=UTC' not in x['href']), None) if info else None
    return re.search(r'about=(\w+)', hl['href']).group(1) if hl else None


def scrape_help(games):
    """Справка по типу игры — то, что открывает «(?)» рядом с типом на странице игры."""
    types, items = {}, {}
    for g in games.values():
        t = g['type']
        if t in types:
            continue
        key = g.get('help') or help_key(g['id'])
        if not key:
            continue
        types[t] = key
        if key in items:
            continue
        s = soup(get(f'HowTo.aspx?about={key}'))
        box = s.select_one('.divCenter')
        html = clean_html(list(box.contents)) if box else ''
        # «Предстоящие игры» → календарь макета
        html = re.sub(r'https://126\.en\.cx/GameCalendar\.aspx\?([^"]*)',
                      lambda m: 'calendar.html?' + m.group(1).replace('&amp;', '&'), html)
        html = html.replace('href="calendar.html', 'data-local="1" href="calendar.html')
        items[key] = {'type': t, 'html': html, 'src': BASE + f'HowTo.aspx?about={key}'}
        print('help', t, key, len(html))
    return {'types': types, 'items': items}


# ---------------------------------------------------------------- archive
def scrape_archive(pages=3):
    out = []
    total = 1
    for p in range(1, pages + 1):
        html = get(f'Games.aspx?page={p}')
        total = max([total] + [int(x) for x in re.findall(r'Games\.aspx\?page=(\d+)', html)])
        s = soup(html)
        titles = [(gid_of(a['href']), a.get_text(strip=True)) for a in s.select('a[id=lnkGameTitle]')]
        c = s.select_one('#tdContentCenter') or s.body
        t = re.sub(r'\s+', ' ', c.get_text(' '))
        blocks = t.split('Подробнее об игре >>>')[:-1]
        for (gid, title), b in zip(titles, blocks):
            f = lambda pat: (re.search(pat, b).group(1).strip() if re.search(pat, b) else '')
            auth = f(r'Авторы? сценария\s*:\s*(.+?)\s*Дата проведения')
            out.append({
                'id': gid, 'title': title,
                'type': f(r'Игра\s*:\s*(Схватка|Точки|Мозговой штурм|Викторина|Фотоохота|Фотоэкстрим|Кэшинг|Мокрые войны|Конкурс)'),
                'num': f(r'\(#\s*(\d+)\s*\)'),
                'mode': f(r'Играем\s*:\s*(\S+)'),
                'k': f(r'Коэффициент сложности игры\s*:\s*([\d,]+)'),
                'aks': f(r'\(АКС\)\s*:\s*([\d,]+)'),
                'q': f(r'Индекс качества\s*:\s*([\d,]+)'),
                'authors': [x.strip() for x in auth.split(',') if x.strip()],
                'date': f(r'Дата проведения\s*:\s*(\d+ \S+ \d{4})'),
                'teams': f(r'приняли участие\s*:\s*(\d+ \S+)'),
                'status': f(r'Статус игры\s*:\s*(.+?)\s*(?:Победител|$)'),
                'winner': f(r'Победител\S* игры\s*:\s*(.+?)\s*$'),
            })
    return {'totalPages': total, 'games': out}


# ---------------------------------------------------------------- calendar
ZONES = [('Real', 'Схватка', 'СХ'), ('Points', 'Точки', 'ТЧ'), ('Virtual', 'Мозговой штурм', 'МШ'),
         ('Quiz', 'Викторина', 'ВК'), ('PhotoHunt', 'Фотоохота', 'ФО'), ('PhotoExtreme', 'Фотоэкстрим', 'ФЭ'),
         ('Caching', 'Кэшинг', 'КШ'), ('WetWars', 'Мокрые войны', 'МВ'), ('Competition', 'Конкурс', 'КН')]


def cal_rows(html):
    rows = []
    for m in re.finditer(r'<tr id="[^"]*_trItem" class="infoRow">([\s\S]*?)</tr>', html):
        r = m.group(1)
        country = re.search(r'countries/[^"]+" alt="([^"]*)"', r)
        num = re.search(r'lblGameNum"[^>]*>(\d+)<', r)
        gid = re.search(r'lblGameID"[^>]*>(\d+)<', r)
        utc = re.search(r"DateToLocalString\('([^']+)'\)", r)
        counter = re.search(r'"StartCounter":(-?\d+)', r)
        dom = re.search(r'lnkSiteInfo"[^>]*>([^<]+)<', r) or re.search(r'href="https?://([^/"]+)/"[^>]*target', r)
        title = re.search(r'lnkGameTitle"[^>]*>([\s\S]*?)</a>', r)
        link = re.search(r'href="([^"]+GameDetails\.aspx\?gid=\d+)"', r)
        authors = re.findall(r'lnkAuthor"[^>]*>([^<]+)</a>\s*(?:\(<span[^>]*>([^<]*)</span>\))?', r)
        fee = re.search(r'FeeLink"[^>]*>([^<]*)<', r)
        dt = None
        if utc:
            dt = datetime.strptime(utc.group(1), '%B %d, %Y %H:%M:%S UTC').replace(tzinfo=timezone.utc).isoformat()
        rows.append({
            'country': country.group(1) if country else '', 'num': num.group(1) if num else '',
            'id': int(gid.group(1)) if gid else None, 'start': dt,
            'domain': dom.group(1).strip() if dom else '',
            'title': BeautifulSoup(title.group(1), 'html.parser').get_text(strip=True) if title else '',
            'link': link.group(1) if link else '',
            'authors': [[a, i] for a, i in authors], 'fee': fee.group(1).strip() if fee else '',
        })
    return rows


def scrape_calendar():
    data = {'zones': [[z, n, s] for z, n, s in ZONES], 'items': {}, 'counts': {}}
    for zone, _, _ in ZONES:
        for status in ('Coming', 'Active'):
            for typ in ('Team', 'Single'):
                key = f'{zone}|{status}|{typ}'
                html = get(f'GameCalendar.aspx?zone={zone}&status={status}&type={typ}')
                cnt = re.search(r'Прошедшие игры \(<span class=\'gold\'>(\d+)', html) or re.search(r'Прошедшие игры[^()]*\((?:<[^>]+>)*(\d+)', html)
                rows = cal_rows(html)
                last = max([1] + [int(x) for x in re.findall(r'GameCalendar\.aspx\?page=(\d+)', html)])
                for p in range(2, last + 1):
                    rows += cal_rows(get(f'GameCalendar.aspx?zone={zone}&status={status}&type={typ}&page={p}'))
                data['items'][key] = rows
                # счётчики вкладок
                c = {}
                for lab, rx in (('Coming', r'Предстоящие игры\s*(?:<[^>]+>)*\s*\((?:<[^>]+>)*(\d+)'),
                                ('Active', r'Активные игры\s*(?:<[^>]+>)*\s*\((?:<[^>]+>)*(\d+)'),
                                ('Finished', r'Прошедшие игры\s*(?:<[^>]+>)*\s*\((?:<[^>]+>)*(\d+)'),
                                ('Team', r'Командные игры\s*(?:<[^>]+>)*\s*\((?:<[^>]+>)*(\d+)'),
                                ('Single', r'Одиночные игры\s*(?:<[^>]+>)*\s*\((?:<[^>]+>)*(\d+)')):
                    mm = re.search(rx, html)
                    c[lab] = int(mm.group(1)) if mm else None
                data['counts'][key] = c
                print('calendar', key, len(rows), c)
    return data


# ---------------------------------------------------------------- authors
def scrape_authors():
    html = get('GameAuthors.aspx?sid=678')
    s = soup(html)
    table = None
    for t in s.find_all('table'):
        if t.find(string=re.compile(r'^\s*Автор\s*$')) and t.find('a', href=re.compile('UserDetails')):
            table = t
    heads = []
    rows = []
    for tr in table.find_all('tr', recursive=False) or table.select('tr'):
        tds = tr.find_all('td', recursive=False)
        if not tds:
            continue
        if not heads:
            heads = [(td.find('img') or {}).get('title') or txt(td) for td in tds]
            continue
        a = tr.select_one('a[href*="UserDetails"]')
        if not a:
            continue
        cells = [txt(td) for td in tds]
        rows.append({'pos': cells[0], 'name': a.get_text(strip=True), 'id': uid_of(a['href']), 'scores': cells[2:]})
    return {'heads': heads[2:], 'rows': rows}


# ---------------------------------------------------------------- statistics
def scrape_stats():
    s = soup(get('Statistics.aspx'))
    c = s.select_one('#tdContentCenter') or s.body
    t = txt(c)
    last = []
    for m in re.finditer(r'# (\d{5,}) (.+?) \(\s*(\d+) очк\w*\s*\) (\d\d\.\d\d\.\d{4} / \d\d:\d\d) (\S+\.en\.cx)', t):
        last.append({'id': m.group(1), 'name': m.group(2), 'date': m.group(4), 'domain': m.group(5)})
    i = t.find('Статистика')
    return {'text': t[i:], 'last': last}


if __name__ == '__main__':
    what = sys.argv[1:] or ['home', 'archive', 'games', 'help', 'calendar', 'authors', 'stats']
    stamp = datetime.now(timezone.utc).isoformat()
    home = arch = None
    if 'home' in what or 'games' in what:
        home = scrape_home(); home['updated'] = stamp; save('home', 'EN_HOME', home)
    if 'archive' in what or 'games' in what:
        arch = scrape_archive(); arch['updated'] = stamp; save('archive', 'EN_ARCHIVE', arch)
    if 'games' in what:
        ids = [g['id'] for g in home['games']] + [g['id'] for g in arch['games']]
        games = {}
        for gid in dict.fromkeys(ids):
            g = scrape_game(gid)
            if g:
                games[gid] = g
                print('game', gid, g['title'], len(g['tabs']), 'tabs')
        save('games', 'EN_GAMES', {'updated': stamp, 'games': games})
    if 'help' in what:
        raw = open(os.path.join(OUT, 'games.js'), encoding='utf-8').read()
        gs = json.loads(raw.split('=', 1)[1].strip().rstrip(';'))['games']
        h = scrape_help(gs); h['updated'] = stamp; save('help', 'EN_HELP', h)
    if 'calendar' in what:
        c = scrape_calendar(); c['updated'] = stamp; save('calendar', 'EN_CALENDAR', c)
    if 'authors' in what:
        a = scrape_authors(); a['updated'] = stamp; save('authors', 'EN_AUTHORS', a)
    if 'stats' in what:
        st = scrape_stats(); st['updated'] = stamp; save('stats', 'EN_STATS', st)
