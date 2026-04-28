/**
 * Media Dashboard — обновление данных кортов каждые 10 сек.
 * Разметка карточек живёт в <template> в media_dashboard.html.
 */
(function () {
    'use strict';

    const UPDATE_INTERVAL = 1000;

    const PALETTE = [
        '#1D4ED8', '#15803D', '#B45309', '#9333EA', '#0E7490',
        '#BE123C', '#4D7C0F', '#7C3AED', '#0369A1', '#C2410C',
        '#0F766E', '#A21CAF', '#1E40AF', '#166534', '#92400E',
        '#6D28D9',
    ];

    let tournamentId   = null;
    let categoryColors = {};
    let paletteIndex   = 0;
    let updateTimer    = null;
    let prevFinished   = new Set();

    // ── ИНИЦИАЛИЗАЦИЯ ─────────────────────────────────────────

    function init() {
        const root = document.querySelector('.dashboard-root');
        if (!root) return;
        tournamentId = root.dataset.tournamentId;
        if (!tournamentId) { console.error('[Dashboard] no tournamentId'); return; }

        scaleToFit();
        window.addEventListener('resize', scaleToFit);
        startClock();
        fetchAndRender();
        updateTimer = setInterval(fetchAndRender, UPDATE_INTERVAL);
    }

    // ── МАСШТАБИРОВАНИЕ ───────────────────────────────────────

    function scaleToFit() {
        const root = document.querySelector('.dashboard-root');
        if (!root) return;
        const scale = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
        root.style.transform = `scale(${scale})`;
        root.style.left = `${(window.innerWidth  - 1920 * scale) / 2}px`;
        root.style.top  = `${(window.innerHeight - 1080 * scale) / 2}px`;
    }

    // ── ЧАСЫ ──────────────────────────────────────────────────

    function startClock() {
        function tick() {
            const el = document.getElementById('dash-time');
            if (el) el.textContent = new Date().toLocaleTimeString('ru-RU',
                { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
        tick();
        setInterval(tick, 1000);
    }

    // ── ЗАГРУЗКА ДАННЫХ ───────────────────────────────────────

    async function fetchAndRender() {
        try {
            const resp = await fetch(`/api/media-dashboard/${tournamentId}/data`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            render(data);
        } catch (e) {
            console.error('[Dashboard] fetch error:', e);
        }
    }

    // ── ЦВЕТА КАТЕГОРИЙ ───────────────────────────────────────

    function categoryColor(name) {
        if (!name) return '#374151';
        if (!categoryColors[name]) {
            categoryColors[name] = PALETTE[paletteIndex % PALETTE.length];
            paletteIndex++;
        }
        return categoryColors[name];
    }

    // ── РЕНДЕР ────────────────────────────────────────────────

    function render(data) {
        const el = document.getElementById('dash-title');
        if (el && data.tournament_name) el.textContent = data.tournament_name;

        renderGrid(data.courts    || []);
        renderFooter(data.categories || []);
    }

    // ── СЕТКА ─────────────────────────────────────────────────

    function renderGrid(courts) {
        const grid = document.getElementById('dash-grid');
        if (!grid) return;

        const n = courts.length;
        const cols = n <= 4 ? 2 : n <= 6 ? 3 : n <= 9 ? 3 : 4;
        grid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

        const nowFinished = new Set();

        courts.forEach(court => {
            const cid = String(court.court_id || '');
            const isFinished = (court.current_match_state || '').toLowerCase() === 'finished';
            if (isFinished) nowFinished.add(cid);

            let card = document.getElementById(`court-card-${cid}`);
            if (!card) {
                card = document.createElement('div');
                card.id = `court-card-${cid}`;
                card.className = 'court-card';
                card.appendChild(document.getElementById('tpl-court-card').content.cloneNode(true));
                grid.appendChild(card);
            }

            // Анимация завершения — только при переходе в finished
            if (isFinished && !prevFinished.has(cid)) {
                card.classList.remove('state-finished');
                void card.offsetWidth; // reflow
                card.classList.add('state-finished');
            }

            updateCard(card, court);
        });

        prevFinished = nowFinished;

        // Удаляем карточки исчезнувших кортов
        grid.querySelectorAll('.court-card').forEach(card => {
            const id = card.id.replace('court-card-', '');
            if (!courts.find(c => String(c.court_id) === id)) card.remove();
        });
    }

    // ── ОБНОВЛЕНИЕ КАРТОЧКИ ───────────────────────────────────

    function updateCard(card, court) {
        const team1    = court.team1_players || court.first_participant  || [];
        const team2    = court.team2_players || court.second_participant || [];
        const detailed = court.detailed_result || [];
        const hasMatch = team1.length > 0 || team2.length > 0;

        const state      = (court.current_match_state || '').toLowerCase();
        const isActive   = state === 'live' || state === 'playing_no_score';
        const isFinished = state === 'finished';
        const isTiebreak = !!(court.is_tiebreak || court.is_super_tiebreak);

        card.className = 'court-card'
            + (isActive   ? ' state-active'   : '')
            + (isFinished ? ' state-finished' : '');

        const score1   = court.team1_score ?? court.first_participant_score  ?? 0;
        const score2   = court.team2_score ?? court.second_participant_score ?? 0;
        const sets1Win = detailed.filter(s => (s.firstParticipantScore  ?? 0) > (s.secondParticipantScore ?? 0)).length;
        const sets2Win = detailed.filter(s => (s.secondParticipantScore ?? 0) > (s.firstParticipantScore  ?? 0)).length;
        const t1leads  = sets1Win > sets2Win || (sets1Win === sets2Win && score1 > score2);
        const t2leads  = sets2Win > sets1Win || (sets1Win === sets2Win && score2 > score1);

        // ── Заголовок ──────────────────────────────────────────

        card.querySelector('.court-name').textContent =
            court.court_name || `Корт ${court.court_id}`;

        const stageEl = card.querySelector('.badge-stage');
        if (court.stage_type === 'group' || court.stage_type === 'playoff') {
            stageEl.textContent = court.stage_type === 'group' ? 'Групповой' : 'Плей-офф';
            stageEl.className   = `badge-stage ${court.stage_type}`;
            stageEl.hidden      = false;
        } else {
            stageEl.hidden = true;
        }

        const statusEl = card.querySelector('.badge-status');
        if (isActive) {
            statusEl.textContent = '● Live';
            statusEl.className   = 'badge-status live';
        } else if (isFinished) {
            statusEl.textContent = '✓ Завершён';
            statusEl.className   = 'badge-status finished';
        } else {
            statusEl.textContent = 'Ожидание';
            statusEl.className   = 'badge-status waiting';
        }

        // ── Категория ──────────────────────────────────────────

        const catEl = card.querySelector('.card-category');
        if (court.class_name) {
            catEl.textContent      = court.class_name;
            catEl.style.background = categoryColor(court.class_name);
            catEl.hidden           = false;
        } else {
            catEl.hidden = true;
        }

        // ── Матч / заглушка ────────────────────────────────────

        const matchEl   = card.querySelector('.card-match');
        const noMatchEl = card.querySelector('.no-match');

        if (hasMatch) {
            matchEl.hidden   = false;
            noMatchEl.hidden = true;

            const gs    = gameScore(detailed, score1, score2);
            const teams = [
                { players: team1, score: gs.first,  leads: t1leads, which: 'first'  },
                { players: team2, score: gs.second, leads: t2leads, which: 'second' },
            ];

            card.querySelectorAll('.team-block').forEach((block, i) => {
                const t = teams[i];
                block.classList.toggle('leader', t.leads);
                fillNames(block.querySelector('.team-names'), t.players, 'player-name');
                block.querySelector('.game-score').textContent = t.score;
                fillSets(block.querySelector('.sets-col'), detailed, t.which);
            });

            card.querySelector('.tiebreak-indicator').classList.toggle('active', isTiebreak);
        } else {
            matchEl.hidden   = true;
            noMatchEl.hidden = false;
        }

        // ── Следующий матч ─────────────────────────────────────

        const nextEl = card.querySelector('.card-next');
        const next1  = court.next_first_participant  || [];
        const next2  = court.next_second_participant || [];

        if (next1.length || next2.length) {
            nextEl.hidden = false;

            const nextClass = court.next_class_name || '';
            const nextStage = court.next_stage_type  || '';

            const catBadge = nextEl.querySelector('.next-cat-badge');
            if (nextClass) {
                catBadge.textContent      = nextClass;
                catBadge.style.background = categoryColor(nextClass);
                catBadge.hidden           = false;
            } else {
                catBadge.hidden = true;
            }

            const stageBadge = nextEl.querySelector('.next-stage-badge');
            if (nextStage === 'group' || nextStage === 'playoff') {
                stageBadge.textContent = nextStage === 'group' ? 'Групповой' : 'Плей-офф';
                stageBadge.className   = `next-stage-badge ${nextStage}`;
                stageBadge.hidden      = false;
            } else {
                stageBadge.hidden = true;
            }

            const playerEls = nextEl.querySelectorAll('.next-player');
            const nextTeams = [next1, next2];
            playerEls.forEach((el, i) => {
                if (nextTeams[i] && nextTeams[i].length) {
                    fillNames(el, nextTeams[i], 'next-player-name');
                    el.hidden = false;
                } else {
                    el.hidden = true;
                }
            });
        } else {
            nextEl.hidden = true;
        }
    }

    // ── ПОДВАЛ ────────────────────────────────────────────────

    function renderFooter(categories) {
        const container = document.getElementById('footer-categories');
        if (!container) return;
        const tpl = document.getElementById('tpl-footer-cat');
        container.textContent = '';
        categories.forEach(cat => {
            const clone = tpl.content.cloneNode(true);
            const el    = clone.querySelector('.footer-cat');
            el.textContent      = cat;
            el.style.background = categoryColor(cat);
            container.appendChild(el);
        });
    }

    // ── УТИЛИТЫ ───────────────────────────────────────────────

    /** Заполняет контейнер именами игроков — по одному элементу на игрока */
    function fillNames(container, players, cls) {
        container.textContent = '';
        (players || []).forEach(p => {
            const name = `${p.firstName || ''} ${p.lastName || p.fullName || ''}`.trim();
            if (!name) return;
            const el = document.createElement('div');
            el.className   = cls;
            el.textContent = name;
            container.appendChild(el);
        });
    }

    /** Заполняет .sets-col спанами сетов без innerHTML */
    function fillSets(col, detailed, which) {
        col.textContent = '';
        detailed.forEach(s => {
            const v1   = s.firstParticipantScore  ?? 0;
            const v2   = s.secondParticipantScore ?? 0;
            const mine = which === 'first' ? v1 : v2;
            const opp  = which === 'first' ? v2 : v1;
            const span = document.createElement('span');
            span.className   = 'set-score' + (mine > opp ? ' won' : '');
            span.textContent = mine;
            col.appendChild(span);
        });
    }

    /** Текущий счёт в геймах из детальных результатов */
    function gameScore(detailed, fb1, fb2) {
        if (!detailed.length) return { first: fb1 || 0, second: fb2 || 0 };
        const last = detailed[detailed.length - 1];
        const gs   = last && last.gameScore;
        if (gs) return { first: gs.first ?? fb1, second: gs.second ?? fb2 };
        return { first: fb1 || 0, second: fb2 || 0 };
    }

    // ── ЗАПУСК ────────────────────────────────────────────────

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) { clearInterval(updateTimer); updateTimer = null; }
        else { fetchAndRender(); updateTimer = setInterval(fetchAndRender, UPDATE_INTERVAL); }
    });

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
