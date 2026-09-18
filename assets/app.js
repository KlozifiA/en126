/* Общий каркас всех страниц: меню, подвал, ссылки на исходник, утилиты. */
(function () {
  const SRC = 'https://126.en.cx/';
  // Страницы исходника, которые гостю не открываются (движок отправляет на вход)
  const LOCKED = /^(Guestbook|UserDetails|Teams\/TeamDetails|UserList|Teams\/TeamList|MakeGameFee|Guestbook\/Messages)/i;

  const EN = window.EN = {
    SRC,
    src(path) { return SRC + String(path || '').replace(/^\/+/, ''); },
    isLocked(url) { return LOCKED.test(String(url).replace(SRC, '').replace(/^\/+/, '')); },
    /** <a> на исходник; закрытые без входа страницы получают замок */
    ext(url, text, cls = '') {
      const u = url.startsWith('http') ? url : EN.src(url);
      const lock = EN.isLocked(u);
      return `<a href="${u}" class="${cls}${lock ? ' locked' : ''}"${lock ? ' title="Доступно после входа"' : ''}>${text}</a>`;
    },
    user(name, id) { return id ? EN.ext(`UserDetails.aspx?uid=${id}`, EN.esc(name)) : EN.esc(name); },
    team(name, id) { return id ? EN.ext(`Teams/TeamDetails.aspx?tid=${id}`, EN.esc(name)) : EN.esc(name); },
    esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); },
    qs(k) { return new URLSearchParams(location.search).get(k); },

    TYPES: {
      'Схватка': { c: '#ffb23f', s: 'СХ', icon: '⚡' },
      'Точки': { c: '#3de0ff', s: 'ТЧ', icon: '📍' },
      'Мозговой штурм': { c: '#8b6bff', s: 'МШ', icon: '🧠' },
      'Викторина': { c: '#35e08a', s: 'ВК', icon: '❓' },
      'Фотоохота': { c: '#ff4f9a', s: 'ФО', icon: '📸' },
      'Фотоэкстрим': { c: '#ff6b4a', s: 'ФЭ', icon: '🎯' },
      'Кэшинг': { c: '#e8d44d', s: 'КШ', icon: '🗺' },
      'Мокрые войны': { c: '#4da3ff', s: 'МВ', icon: '💧' },
      'Конкурс': { c: '#c3a6ff', s: 'КН', icon: '🏆' },
    },
    color(t) { return (EN.TYPES[t] || {}).c || '#3de0ff'; },
    byShort(s) { return Object.keys(EN.TYPES).find(k => EN.TYPES[k].s === s) || s; },

    /** «19.09.2026 22:00:00 (UTC+3)» → Date */
    parseEnDate(s) {
      const m = String(s || '').match(/(\d\d)\.(\d\d)\.(\d{4}) (\d{1,2}):(\d\d):(\d\d)(?:.*UTC\s*([+-]\d+))?/);
      if (!m) return null;
      const off = +(m[7] || 3);
      return new Date(Date.UTC(+m[3], +m[2] - 1, +m[1], +m[4] - off, +m[5], +m[6]));
    },
    plural(n, f) { n = Math.abs(n) % 100; const n1 = n % 10; return n > 10 && n < 20 ? f[2] : n1 > 1 && n1 < 5 ? f[1] : n1 === 1 ? f[0] : f[2]; },
    /** как таймер en.cx: «1 день 1 час 23 минуты 45 секунд» */
    span(sec, withSec = true) {
      sec = Math.max(0, Math.floor(sec));
      const d = Math.floor(sec / 86400), h = Math.floor(sec % 86400 / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60;
      const p = [];
      if (d) p.push(d + ' ' + EN.plural(d, ['день', 'дня', 'дней']));
      if (h) p.push(h + ' ' + EN.plural(h, ['час', 'часа', 'часов']));
      if (m) p.push(m + ' ' + EN.plural(m, ['минута', 'минуты', 'минут']));
      if (withSec && (s || !p.length)) p.push(s + ' ' + EN.plural(s, ['секунда', 'секунды', 'секунд']));
      return p.join(' ');
    },
    fmtDate(d, opts) { return d.toLocaleString('ru-RU', Object.assign({ timeZone: 'Europe/Moscow' }, opts)); },

    /** Процедурная обложка для игр без картинки */
    poster(g) {
      const c = EN.color(g.type), s = +g.id || 1;
      let r = s; const rnd = () => ((r = (r * 9301 + 49297) % 233280) / 233280);
      let bars = '';
      for (let i = 0; i < 14; i++) {
        const h = 40 + rnd() * 110, x = i * 22 - 6;
        bars += `<rect x="${x}" y="${170 - h}" width="18" height="${h}" fill="url(#b${s})" opacity="${.35 + rnd() * .5}"/>`;
        for (let j = 0; j < 6; j++) if (rnd() > .6) bars += `<rect x="${x + 4 + (j % 2) * 7}" y="${176 - h + Math.floor(j / 2) * 12}" width="3" height="4" fill="${c}" opacity=".9"/>`;
      }
      return `<div class="gen"><svg viewBox="0 0 300 170" preserveAspectRatio="xMidYMid slice"><defs>
        <linearGradient id="b${s}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${c}" stop-opacity=".5"/><stop offset="1" stop-color="#0a0f1c"/></linearGradient>
        <radialGradient id="g${s}" cx=".7" cy=".2" r=".8"><stop offset="0" stop-color="${c}" stop-opacity=".45"/><stop offset="1" stop-color="#070b16" stop-opacity="0"/></radialGradient></defs>
        <rect width="300" height="170" fill="#070b16"/><rect width="300" height="170" fill="url(#g${s})"/>
        <circle cx="220" cy="42" r="16" fill="${c}" opacity=".85"/>${bars}
        <text x="14" y="160" font-family="Unbounded" font-weight="900" font-size="54" fill="none" stroke="${c}" stroke-opacity=".35">${String(g.num || s).slice(-3)}</text></svg></div>`;
    },
    cover(g) {
      return g.img ? `<img loading="lazy" src="${g.img}" alt="" onerror="this.outerHTML=EN.poster(${EN.esc(JSON.stringify({ id: g.id, type: g.type, num: g.num }))})">` : EN.poster(g);
    },

    tilt(el, max = 10, lift = 0) {
      if (matchMedia('(hover: none)').matches) return;
      el.addEventListener('pointermove', e => {
        const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        el.style.transform = `rotateY(${(x - .5) * max * 2}deg) rotateX(${(.5 - y) * max * 2}deg) translateZ(${lift}px)`;
        el.style.setProperty('--mx', x * 100 + '%'); el.style.setProperty('--my', y * 100 + '%');
      });
      el.addEventListener('pointerleave', () => el.style.transform = '');
    },
    io: null,
    reveal(root = document) {
      if (!EN.io) EN.io = new IntersectionObserver(es => es.forEach(e => {
        if (!e.isIntersecting) return;
        const el = e.target; el.classList.add('in'); EN.io.unobserve(el);
        el.querySelectorAll?.('.bar i').forEach(b => b.style.width = b.dataset.w + '%');
        el.querySelectorAll?.('[data-n]').forEach(n => {
          const to = +n.dataset.n, t0 = performance.now();
          (function step(t) {
            const p = Math.min(1, (t - t0) / 1600);
            n.textContent = Math.round(to * (1 - Math.pow(1 - p, 4))).toLocaleString('ru-RU');
            if (p < 1) requestAnimationFrame(step);
          })(t0);
        });
      }), { threshold: .12 });
      root.querySelectorAll('.rv:not(.in), .gcard:not(.in)').forEach((el, i) => {
        // задержка только для появления (--d), а не для наклона при наведении
        if (el.classList.contains('gcard')) el.style.setProperty('--d', (i % 4) * 70 + 'ms');
        EN.io.observe(el);
      });
    },
    updated(stamp) {
      if (!stamp) return '';
      return `<div class="snap">Данные с 126.en.cx на ${EN.fmtDate(new Date(stamp), { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })} МСК</div>`;
    },
  };

  /* ---------- меню и подвал ---------- */
  const page = document.body.dataset.page || '';
  const NAV = [
    ['archive', 'archive.html', 'Архив'],
    ['calendar', 'calendar.html', 'Календарь'],
    ['authors', 'authors.html', 'Авторы'],
    ['stats', 'stats.html', 'Статистика'],
    ['forum', EN.src('Guestbook.aspx'), 'Форум'],
    ['search', EN.src('PlayerSearch.aspx'), 'Поиск по ID'],
  ];
  const cube = '<div class="logo-cube"><div class="cube"><b>126</b><b>EN</b><b>126</b><b>EN</b><b></b><b></b></div></div>';
  const header = document.createElement('header');
  header.className = 'nav';
  header.innerHTML = `
    <a href="index.html" class="logo">${cube}<div>ENCOUNTER<small>КМВ · 126.EN.CX</small></div></a>
    <ul>${NAV.map(([k, h, t]) => {
      const lock = EN.isLocked(h);
      return `<li><a href="${h}" class="${k === page ? 'on' : ''}${lock ? ' locked' : ''}"${lock ? ' title="Доступно после входа"' : ''}>${t}</a></li>`;
    }).join('')}</ul>
    <a class="btn btn-amber" href="login.html">Войти →</a>
    <button class="burger" aria-label="Меню" aria-expanded="false">☰</button>`;
  document.body.prepend(header);
  const burger = header.querySelector('.burger');
  const close = () => { header.classList.remove('open'); burger.setAttribute('aria-expanded', false); burger.textContent = '☰'; };
  burger.addEventListener('click', () => {
    const o = header.classList.toggle('open');
    burger.setAttribute('aria-expanded', o); burger.textContent = o ? '✕' : '☰';
  });
  header.querySelectorAll('ul a').forEach(a => a.addEventListener('click', close));

  const bg = document.createElement('div');
  bg.innerHTML = '<canvas id="scene"></canvas><div class="vignette"></div><div class="grain"></div>';
  document.body.prepend(...bg.children);

  const footer = document.createElement('footer');
  footer.innerHTML = `<div class="wrap">
    <div class="foot">
      <a href="index.html" class="logo">${cube}<div>ENCOUNTER<small>СЕТЬ ГОРОДСКИХ ИГР</small></div></a>
      <nav class="foot-links">
        <a href="index.html">Главная</a><a href="archive.html">Архив игр</a><a href="calendar.html">Календарь</a>
        <a href="authors.html">Авторы</a><a href="stats.html">Статистика</a>
        <a href="login.html">Вход</a><a href="signup.html">Регистрация</a>
      </nav>
      <div class="socials">
        <a class="soc" href="https://t.me/enkmv" aria-label="Telegram">TG</a>
        <a class="soc" href="https://vk.com/enkmv" aria-label="VK">VK</a>
        <a class="soc" href="https://www.instagram.com/encounterkmv" aria-label="Instagram">IG</a>
      </div>
    </div>
    <div class="fine" style="margin-top:22px">EncounterTM Ltd. 2004–2026 · Оригинал: <a href="${SRC}">126.en.cx</a></div>
    <div class="big-word">Encounter</div></div>`;
  document.addEventListener('DOMContentLoaded', () => { document.body.append(footer); EN.reveal(); });
})();
