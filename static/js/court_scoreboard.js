/**
 * Court Scoreboard - универсальный модуль обновления счёта
 * Обслуживает три режима: score_full, scoreboard, fullscreen
 * Режим определяется автоматически по DOM.
 */

(function () {
    'use strict';

    const CONFIG = {
        updateInterval: 500,
        animationDuration: 300
    };

    let mode = null;
    let tournamentId = null;
    let courtId = null;
    let updateTimer = null;
    let lastServeState = null;

    // =========================================================
    // ИНИЦИАЛИЗАЦИЯ
    // =========================================================

    function init() {
        const fullContainer = document.querySelector('.scoreboard-full-container');
        if (fullContainer) {
            mode = 'score_full';
            tournamentId = fullContainer.dataset.tournamentId;
            courtId = fullContainer.dataset.courtId;
            scaleToFit();
            window.addEventListener('resize', scaleToFit);
        } else {
            const body = document.body;
            mode = body.dataset.mode || 'scoreboard';
            tournamentId = body.dataset.tournamentId;
            courtId = body.dataset.courtId;
        }

        if (!tournamentId || !courtId) {
            console.error('[Scoreboard] Missing tournament_id or court_id');
            return;
        }

        console.log(`[Scoreboard] mode=${mode}, tournament=${tournamentId}, court=${courtId}`);
        startUpdates();
    }

    // =========================================================
    // ПОЛИНГ
    // =========================================================

    function startUpdates() {
        if (updateTimer) clearInterval(updateTimer);
        fetchAndUpdate();
        updateTimer = setInterval(fetchAndUpdate, CONFIG.updateInterval);
    }

    function stopUpdates() {
        if (updateTimer) {
            clearInterval(updateTimer);
            updateTimer = null;
        }
    }

    async function fetchAndUpdate() {
        try {
            const response = await fetch(`/api/court/${tournamentId}/${courtId}/data`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (data.error) { console.warn('[Scoreboard] API error:', data.error); return; }
            dispatch(data);
        } catch (e) {
            console.error('[Scoreboard] fetch error:', e);
        }
    }

    function dispatch(data) {
        if (mode === 'score_full')   updateScoreboardFull(data);
        else if (mode === 'fullscreen') updateFullscreenScoreboard(data);
        else                          updateScoreboard(data);
    }

    // =========================================================
    // ОБЩИЕ УТИЛИТЫ
    // =========================================================

    /**
     * Счёт текущего гейма: теннисный формат или тай-брейк
     */
    function getGameScore(detailed, fallback, participant) {
        if (!detailed || !detailed.length) return fallback || 0;
        const lastSet = detailed[detailed.length - 1];
        if (!lastSet) return fallback || 0;
        const gs = lastSet.gameScore;
        if (gs && gs[participant] !== undefined) return gs[participant];
        return fallback || 0;
    }

    /**
     * Индикатор подачи (общий для всех режимов)
     */
    function updateServeIndicator(data) {
        const isFirstServing = data.is_first_participant_serving;
        if (isFirstServing === null || isFirstServing === undefined) return;
        lastServeState = isFirstServing;
        const row1 = document.querySelector('.team-row[data-team="1"]');
        const row2 = document.querySelector('.team-row[data-team="2"]');
        if (row1) row1.classList.toggle('serving', isFirstServing === true);
        if (row2) row2.classList.toggle('serving', isFirstServing === false);
    }

    /**
     * URL флага по коду страны (3- или 2-буквенный)
     */
    function getFlagUrl(countryCode) {
        if (!countryCode) return '';
        const codeMap = {
            'rin': 'ru', 'rus': 'ru',
            'usa': 'us', 'ger': 'de', 'fra': 'fr', 'esp': 'es',
            'ita': 'it', 'gbr': 'gb', 'por': 'pt', 'ned': 'nl',
            'bel': 'be', 'sui': 'ch', 'aut': 'at', 'swe': 'se',
            'nor': 'no', 'den': 'dk', 'dnk': 'dk', 'fin': 'fi',
            'pol': 'pl', 'cze': 'cz', 'svk': 'sk', 'cro': 'hr',
            'srb': 'rs', 'ukr': 'ua', 'blr': 'by',
            'bra': 'br', 'arg': 'ar', 'chi': 'cl', 'uru': 'uy', 'col': 'co',
            'jpn': 'jp', 'kor': 'kr', 'chn': 'cn', 'ind': 'in',
            'aus': 'au', 'nzl': 'nz', 'kaz': 'kz', 'uzb': 'uz',
            'arm': 'am', 'geo': 'ge', 'aze': 'az',
            'isr': 'il', 'uae': 'ae', 'qat': 'qa', 'kuw': 'kw',
            'ksa': 'sa', 'tur': 'tr', 'egy': 'eg', 'mar': 'ma',
            'tun': 'tn', 'rsa': 'za', 'can': 'ca', 'mex': 'mx'
        };
        const code = codeMap[countryCode.toLowerCase()] || countryCode.toLowerCase();
        return `/static/flags/4x3/${code}.svg`;
    }

    function updateFlag(selector, countryCode) {
        const el = document.querySelector(selector);
        if (!el) return;
        el.style.backgroundImage = countryCode ? `url('${getFlagUrl(countryCode)}')` : '';
    }

    /**
     * Анимация изменения значения ячейки
     */
    function animateUpdate(el) {
        el.classList.remove('updating');
        void el.offsetWidth; // reflow
        el.classList.add('updating');
        setTimeout(() => el.classList.remove('updating'), CONFIG.animationDuration);
    }

    // =========================================================
    // РЕЖИМ: score_full
    // =========================================================

    function scaleToFit() {
        const container = document.querySelector('.scoreboard-full-container');
        if (!container) return;
        const baseW = 3840, baseH = 2160;
        const scale = Math.min(window.innerWidth / baseW, window.innerHeight / baseH);
        const offsetX = (window.innerWidth - baseW * scale) / 2;
        const offsetY = (window.innerHeight - baseH * scale) / 2;
        container.style.transform = `scale(${scale})`;
        container.style.transformOrigin = 'top left';
        container.style.position = 'absolute';
        container.style.left = `${offsetX}px`;
        container.style.top = `${offsetY}px`;
    }

    function updateScoreboardFull(data) {
        updateTeamNamesFull(data);
        updateSetScores(data);
        updateGameScore(data);
        updateFlags(data);
        updateServeIndicator(data);
    }

    function updateCellValue(selector, newValue) {
        const cell = document.querySelector(selector);
        if (!cell) return;
        const newStr = String(newValue);
        if (cell.textContent !== newStr) {
            cell.textContent = newStr;
            animateUpdate(cell);
        }
    }

    function updateTeamNamesFull(data) {
        const t1 = data.team1_players || [];
        const t2 = data.team2_players || [];
        function setName(sel, player) {
            const el = document.querySelector(sel);
            if (!el) return;
            const name = player ? `${player.firstName || ''} ${player.lastName || ''}`.trim().toUpperCase() : '';
            if (el.textContent !== name) el.textContent = name;
        }
        setName('[data-field="team1_player1"]', t1[0]);
        setName('[data-field="team1_player2"]', t1[1]);
        setName('[data-field="team2_player1"]', t2[0]);
        setName('[data-field="team2_player2"]', t2[1]);
    }

    function updateSetScores(data) {
        const sets = data.detailed_result || [];
        const tableHeader = document.querySelector('.table-header-block');
        const row1 = document.querySelector('.team-row[data-team="1"] .scores-block');
        const row2 = document.querySelector('.team-row[data-team="2"] .scores-block');
        if (!tableHeader || !row1 || !row2) return;

        const currentCount = tableHeader.querySelectorAll('.header-cell:not(.total)').length;
        if (sets.length !== currentCount) {
            rebuildSets(sets, tableHeader, row1, row2);
        } else {
            for (let i = 0; i < sets.length; i++) {
                updateCellValue(`[data-field="team1_set${i + 1}"]`, sets[i].firstParticipantScore ?? '-');
                updateCellValue(`[data-field="team2_set${i + 1}"]`, sets[i].secondParticipantScore ?? '-');
            }
        }
    }

    function rebuildSets(sets, tableHeader, row1, row2) {
        tableHeader.querySelectorAll('.header-cell:not(.total)').forEach(el => el.remove());
        row1.querySelectorAll('.score-cell:not(.total)').forEach(el => el.remove());
        row2.querySelectorAll('.score-cell:not(.total)').forEach(el => el.remove());

        const beforeH = tableHeader.querySelector('.header-cell.total');
        const beforeC1 = row1.querySelector('.score-cell.total');
        const beforeC2 = row2.querySelector('.score-cell.total');

        for (let i = 0; i < sets.length; i++) {
            const set = sets[i];
            const hCell = document.createElement('div');
            hCell.className = 'header-cell';
            hCell.textContent = `СЕТ ${i + 1}`;
            tableHeader.insertBefore(hCell, beforeH);

            const c1 = document.createElement('div');
            c1.className = 'score-cell';
            c1.dataset.field = `team1_set${i + 1}`;
            c1.textContent = set.firstParticipantScore ?? '-';
            row1.insertBefore(c1, beforeC1);
            animateUpdate(c1);

            const c2 = document.createElement('div');
            c2.className = 'score-cell';
            c2.dataset.field = `team2_set${i + 1}`;
            c2.textContent = set.secondParticipantScore ?? '-';
            row2.insertBefore(c2, beforeC2);
            animateUpdate(c2);
        }
    }

    function updateGameScore(data) {
        const detailed = data.detailed_result || [];
        updateCellValue('[data-field="team1_total"]', getGameScore(detailed, data.team1_score, 'first'));
        updateCellValue('[data-field="team2_total"]', getGameScore(detailed, data.team2_score, 'second'));
    }

    function updateFlags(data) {
        const t1 = data.team1_players || [];
        const t2 = data.team2_players || [];
        updateFlag('[data-field="team1_flag1"]', t1[0]?.countryCode);
        updateFlag('[data-field="team1_flag2"]', t1[1]?.countryCode);
        updateFlag('[data-field="team2_flag1"]', t2[0]?.countryCode);
        updateFlag('[data-field="team2_flag2"]', t2[1]?.countryCode);
    }

    // =========================================================
    // РЕЖИМ: scoreboard (smart_scoreboard)
    // =========================================================

    function formatTeamName(players, useInitials = true) {
        if (!players || !players.length) return '';
        const key = useInitials ? 'initialLastName' : 'fullName';
        return players.map(p => p[key] || p.fullName || '').filter(Boolean).join(' / ').toUpperCase();
    }

    function renderSets(detailed, participant, maxSets = 3) {
        const scoreKey = participant === 'first' ? 'firstParticipantScore' : 'secondParticipantScore';
        const otherKey = participant === 'first' ? 'secondParticipantScore' : 'firstParticipantScore';
        const prefix = participant === 'first' ? 1 : 2;
        let html = '';

        if (!detailed || !detailed.length) {
            for (let i = 0; i < maxSets; i++) html += `<div class="set set${prefix}-${i}">-</div>`;
            return html;
        }
        for (let i = 0; i < detailed.length && i < maxSets; i++) {
            const s = detailed[i][scoreKey] || 0;
            const o = detailed[i][otherKey] || 0;
            html += `<div class="${s > o ? 'setV' : 'set'} set${prefix}-${i}">${s}</div>`;
        }
        return html;
    }

    /**
     * Обновление элемента с fade-анимацией (для scoreboard/fullscreen)
     */
    function updateElement(selector, newValue) {
        const el = document.querySelector(selector);
        if (!el) return;
        const newStr = String(newValue).trim();
        if (el.innerHTML.trim() === newStr) return;

        if (el.classList.contains('fade-update')) {
            el.classList.add('updating');
            setTimeout(() => {
                el.innerHTML = newStr;
                el.classList.remove('updating');
            }, 150);
        } else {
            el.innerHTML = newStr;
        }
    }

    function updateScoreboard(data) {
        const team1 = data.team1_players || data.first_participant || [];
        const team2 = data.team2_players || data.second_participant || [];
        const detailed = data.detailed_result || [];
        const hasMatch = team1.length > 0;

        const score1Raw = data.team1_score ?? data.first_participant_score ?? 0;
        const score2Raw = data.team2_score ?? data.second_participant_score ?? 0;
        const showScore = hasMatch && (detailed.length > 0 || score1Raw > 0 || score2Raw > 0);

        const matchEl = document.getElementById('match-content');
        const noMatchEl = document.getElementById('no-match-content');
        if (matchEl) matchEl.style.display = hasMatch ? 'block' : 'none';
        if (noMatchEl) noMatchEl.style.display = hasMatch ? 'none' : 'block';
        if (!hasMatch) return;

        updateElement('[data-field="team1_name"]', formatTeamName(team1));
        updateElement('[data-field="team2_name"]', formatTeamName(team2));
        updateElement('[data-field="team1_score"]', showScore ? getGameScore(detailed, score1Raw, 'first') : '-');
        updateElement('[data-field="team2_score"]', showScore ? getGameScore(detailed, score2Raw, 'second') : '-');
        updateElement('[data-field="team1_sets"]', showScore ? renderSets(detailed, 'first') : '*');
        updateElement('[data-field="team2_sets"]', showScore ? renderSets(detailed, 'second') : '*');
        updateServeIndicator(data);
    }

    // =========================================================
    // РЕЖИМ: fullscreen (scoreboard в полный экран)
    // =========================================================

    function updateFullscreenScoreboard(data) {
        const team1 = data.first_participant || [];
        const team2 = data.second_participant || [];
        const detailed = data.detailed_result || [];
        const hasMatch = team1.length > 0;
        const showScore = hasMatch && (detailed.length > 0 ||
            data.first_participant_score > 0 || data.second_participant_score > 0);

        const matchEl = document.getElementById('match-content');
        const noMatchEl = document.getElementById('no-match-content');
        if (matchEl) matchEl.style.display = hasMatch ? 'block' : 'none';
        if (noMatchEl) noMatchEl.style.display = hasMatch ? 'none' : 'flex';
        if (!hasMatch) return;

        const names1 = team1.slice(0, 2).map(p => `${p.firstName || ''} ${p.lastName || ''}`.trim());
        const names2 = team2.slice(0, 2).map(p => `${p.firstName || ''} ${p.lastName || ''}`.trim());

        updateElement('[data-field="player1_name1"]', names1[0] || '');
        updateElement('[data-field="player1_name2"]', names1[1] || '');
        updateElement('[data-field="player2_name1"]', names2[0] || '');
        updateElement('[data-field="player2_name2"]', names2[1] || '');

        for (let i = 0; i < 3; i++) {
            const set = detailed[i];
            const hasSet = showScore && set !== undefined;
            const el1 = document.querySelector(`[data-field="team1_set${i}"]`);
            const el2 = document.querySelector(`[data-field="team2_set${i}"]`);
            const hdr = document.querySelector(`[data-field="set_header_${i}"]`);
            if (hasSet) {
                if (el1) { el1.classList.remove('hidden'); updateElement(`[data-field="team1_set${i}"]`, String(set.firstParticipantScore ?? 0)); }
                if (el2) { el2.classList.remove('hidden'); updateElement(`[data-field="team2_set${i}"]`, String(set.secondParticipantScore ?? 0)); }
                if (hdr) hdr.classList.remove('hidden');
            } else {
                if (el1) el1.classList.add('hidden');
                if (el2) el2.classList.add('hidden');
                if (hdr) hdr.classList.add('hidden');
            }
        }

        const g1 = showScore ? getGameScore(detailed, data.first_participant_score, 'first') : '';
        const g2 = showScore ? getGameScore(detailed, data.second_participant_score, 'second') : '';
        updateElement('[data-field="team1_game"]', String(g1));
        updateElement('[data-field="team2_game"]', String(g2));
    }

    // =========================================================
    // ЖИЗНЕННЫЙ ЦИКЛ
    // =========================================================

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) stopUpdates();
        else startUpdates();
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Экспорт для отладки
    window.CourtScoreboard = { startUpdates, stopUpdates, fetchAndUpdate, CONFIG };
})();
