/**
 * Smart Scoreboard - AJAX обновление без перезагрузки страницы
 * Используется для scoreboard и fullscreen_scoreboard
 */

(function() {
    'use strict';

    // Конфигурация берётся из data-атрибутов body
    const body = document.body;
    const CONFIG = {
        tournamentId: body.dataset.tournamentId,
        courtId: body.dataset.courtId,
        updateInterval: parseInt(body.dataset.updateInterval) || 2000,
        mode: body.dataset.mode || 'scoreboard' // 'scoreboard' или 'fullscreen'
    };

    let updateTimer = null;

    /**
     * Форматирование имени команды
     */
    function formatTeamName(players, useInitials = true) {
        if (!players || !players.length) return '';
        
        const key = useInitials ? 'initialLastName' : 'fullName';
        return players
            .map(p => p[key] || p.fullName || '')
            .filter(n => n)
            .join(' / ')
            .toUpperCase();
    }

    /**
     * Получение полного имени игрока
     */
    function getFullName(player) {
        return player.fullName || `${player.firstName || ''} ${player.lastName || ''}`.trim();
    }

    /**
     * Получение счёта текущего гейма
     * В тай-брейке показывает очки тай-брейка, иначе теннисный формат
     */
    function getGameScore(detailed, score, participant) {
        if (!detailed || !detailed.length) return score || 0;
        
        const lastSet = detailed[detailed.length - 1];
        if (!lastSet) return score || 0;
        
        // gameScore - словарь с ключами 'first' и 'second'
        // В тай-брейке там уже правильные очки (1, 2, 3...)
        // В обычном гейме - теннисный формат (0, 15, 30, 40, AD)
        const gameScore = lastSet.gameScore;
        if (gameScore && gameScore[participant] !== undefined) {
            return gameScore[participant];
        }
        
        return score || 0;
    }

    /**
     * Рендер сетов для обычного scoreboard
     */
    function renderSets(detailed, participant, maxSets = 3) {
        let html = '';
        const scoreKey = participant === 'first' ? 'firstParticipantScore' : 'secondParticipantScore';
        const otherKey = participant === 'first' ? 'secondParticipantScore' : 'firstParticipantScore';
        const prefix = participant === 'first' ? 1 : 2;
        
        if (!detailed || !detailed.length) {
            for (let i = 0; i < maxSets; i++) {
                html += `<div class="set set${prefix}-${i}">-</div>`;
            }
            return html;
        }
        
        for (let i = 0; i < detailed.length && i < maxSets; i++) {
            const s = detailed[i][scoreKey] || 0;
            const other = detailed[i][otherKey] || 0;
            const cls = s > other ? 'setV' : 'set';
            html += `<div class="${cls} set${prefix}-${i}">${s}</div>`;
        }
        
        return html;
    }

    /**
     * Обновление элемента с анимацией
     */
    function updateElement(selector, newValue, useAnimation = true) {
        const el = document.querySelector(selector);
        if (!el) return false;
        
        const currentValue = el.innerHTML.trim();
        const newValueTrimmed = String(newValue).trim();
        
        if (currentValue === newValueTrimmed) return false;
        
        if (useAnimation && el.classList.contains('fade-update')) {
            el.classList.add('updating');
            setTimeout(() => {
                el.innerHTML = newValueTrimmed;
                el.classList.remove('updating');
            }, 150);
        } else {
            el.innerHTML = newValueTrimmed;
        }
        
        return true;
    }

    /**
     * Обновление обычного scoreboard
     */
    function updateScoreboard(court) {
        const team1 = court.first_participant || [];
        const team2 = court.second_participant || [];
        const detailed = court.detailed_result || [];
        const hasMatch = team1.length > 0;
        
        const hasScoreData = detailed.length > 0 || 
            court.first_participant_score > 0 || 
            court.second_participant_score > 0;
        const showScore = hasMatch && hasScoreData;

        // Показываем/скрываем блоки
        const matchContent = document.getElementById('match-content');
        const noMatchContent = document.getElementById('no-match-content');
        
        if (matchContent) matchContent.style.display = hasMatch ? 'block' : 'none';
        if (noMatchContent) noMatchContent.style.display = hasMatch ? 'none' : 'block';

        if (!hasMatch) return;

        // Обновляем данные
        const team1Name = formatTeamName(team1);
        const team2Name = formatTeamName(team2);
        const score1 = showScore ? getGameScore(detailed, court.first_participant_score, 'first') : '-';
        const score2 = showScore ? getGameScore(detailed, court.second_participant_score, 'second') : '-';
        const sets1Html = showScore ? renderSets(detailed, 'first') : '*';
        const sets2Html = showScore ? renderSets(detailed, 'second') : '*';

        updateElement('[data-field="team1_name"]', team1Name);
        updateElement('[data-field="team2_name"]', team2Name);
        updateElement('[data-field="team1_score"]', score1);
        updateElement('[data-field="team2_score"]', score2);
        updateElement('[data-field="team1_sets"]', sets1Html);
        updateElement('[data-field="team2_sets"]', sets2Html);
    }

    /**
     * Обновление fullscreen scoreboard
     */
    function updateFullscreenScoreboard(court) {
        const team1 = court.first_participant || [];
        const team2 = court.second_participant || [];
        const detailed = court.detailed_result || [];
        const hasMatch = team1.length > 0;
        
        const hasScoreData = detailed.length > 0 || 
            court.first_participant_score > 0 || 
            court.second_participant_score > 0;
        const showScore = hasMatch && hasScoreData;

        // Показываем/скрываем блоки
        const matchContent = document.getElementById('match-content');
        const noMatchContent = document.getElementById('no-match-content');
        
        if (matchContent) matchContent.style.display = hasMatch ? 'block' : 'none';
        if (noMatchContent) noMatchContent.style.display = hasMatch ? 'none' : 'flex';

        if (!hasMatch) return;

        // Имена игроков
        const names1 = team1.slice(0, 2).map(p => getFullName(p));
        const names2 = team2.slice(0, 2).map(p => getFullName(p));

        updateElement('[data-field="player1_name1"]', names1[0] || '');
        updateElement('[data-field="player1_name2"]', names1[1] || '');
        updateElement('[data-field="player2_name1"]', names2[0] || '');
        updateElement('[data-field="player2_name2"]', names2[1] || '');

        // Счета по сетам - показываем/скрываем через CSS класс
        for (let i = 0; i < 3; i++) {
            const set = detailed[i];
            const hasSet = showScore && set !== undefined;
            
            // Элементы счёта
            const el1 = document.querySelector(`[data-field="team1_set${i}"]`);
            const el2 = document.querySelector(`[data-field="team2_set${i}"]`);
            // Заголовок сета
            const header = document.querySelector(`[data-field="set_header_${i}"]`);
            
            if (hasSet) {
                // Показываем сет
                if (el1) {
                    el1.classList.remove('hidden');
                    updateElement(`[data-field="team1_set${i}"]`, String(set.firstParticipantScore ?? 0));
                }
                if (el2) {
                    el2.classList.remove('hidden');
                    updateElement(`[data-field="team2_set${i}"]`, String(set.secondParticipantScore ?? 0));
                }
                if (header) header.classList.remove('hidden');
            } else {
                // Скрываем пустой сет
                if (el1) el1.classList.add('hidden');
                if (el2) el2.classList.add('hidden');
                if (header) header.classList.add('hidden');
            }
        }

        // Текущий гейм
        const game1 = showScore ? getGameScore(detailed, court.first_participant_score, 'first') : '';
        const game2 = showScore ? getGameScore(detailed, court.second_participant_score, 'second') : '';
        updateElement('[data-field="team1_game"]', String(game1));
        updateElement('[data-field="team2_game"]', String(game2));
    }

    /**
     * Основная функция обновления
     */
    async function update() {
        try {
            const response = await fetch(`/api/tournament/${CONFIG.tournamentId}/courts`);
            if (!response.ok) throw new Error('Network error');
            
            const courts = await response.json();
            const court = courts.find(c => String(c.court_id) === String(CONFIG.courtId));
            
            if (!court) {
                console.warn('Court not found:', CONFIG.courtId);
                return;
            }

            if (CONFIG.mode === 'fullscreen') {
                updateFullscreenScoreboard(court);
            } else {
                updateScoreboard(court);
            }

        } catch (error) {
            console.error('Update error:', error);
        }
    }

    /**
     * Запуск обновлений
     */
    function start() {
        if (!CONFIG.tournamentId || !CONFIG.courtId) {
            console.error('Missing tournament_id or court_id');
            return;
        }
        
        update();
        updateTimer = setInterval(update, CONFIG.updateInterval);
    }

    /**
     * Остановка обновлений
     */
    function stop() {
        if (updateTimer) {
            clearInterval(updateTimer);
            updateTimer = null;
        }
    }

    // Автопауза при скрытии вкладки
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stop();
        } else {
            start();
        }
    });

    // Запуск при загрузке
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }

    // Экспорт для отладки
    window.SmartScoreboard = { start, stop, update, CONFIG };
})();