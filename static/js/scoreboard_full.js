/**
 * Scoreboard Full - AJAX updates with animations
 */

(function() {
    'use strict';

    const CONFIG = {
        updateInterval: 2000,  // 2 секунды
        animationDuration: 500
    };

    let tournamentId = null;
    let courtId = null;
    let updateTimer = null;
    let lastData = null;

    /**
     * Инициализация
     */
    function init() {
        const container = document.querySelector('.scoreboard-full-container');
        if (!container) {
            console.error('Scoreboard container not found');
            return;
        }

        tournamentId = container.dataset.tournamentId;
        courtId = container.dataset.courtId;

        if (!tournamentId || !courtId) {
            console.error('Tournament ID or Court ID not found');
            return;
        }

        // Масштабирование под размер экрана
        scaleToFit();
        window.addEventListener('resize', scaleToFit);

        console.log(`Scoreboard Full: initialized for ${tournamentId}/${courtId}`);
        
        // Запускаем обновления
        startUpdates();
    }

    /**
     * Масштабирование контейнера под размер окна
     */
    function scaleToFit() {
        const container = document.querySelector('.scoreboard-full-container');
        if (!container) return;

        const baseWidth = 3840;
        const baseHeight = 2160;
        
        const scaleX = window.innerWidth / baseWidth;
        const scaleY = window.innerHeight / baseHeight;
        const scale = Math.min(scaleX, scaleY);

        container.style.transform = `scale(${scale})`;
        
        // Центрируем если нужно
        const scaledWidth = baseWidth * scale;
        const scaledHeight = baseHeight * scale;
        const offsetX = (window.innerWidth - scaledWidth) / 2;
        const offsetY = (window.innerHeight - scaledHeight) / 2;
        
        container.style.transformOrigin = 'top left';
        container.style.position = 'absolute';
        container.style.left = `${offsetX}px`;
        container.style.top = `${offsetY}px`;
    }

    /**
     * Запуск периодических обновлений
     */
    function startUpdates() {
        if (updateTimer) {
            clearInterval(updateTimer);
        }
        // Первое обновление сразу
        checkForUpdates();
        updateTimer = setInterval(checkForUpdates, CONFIG.updateInterval);
    }

    /**
     * Проверка обновлений
     */
    async function checkForUpdates() {
        try {
            // ИСПРАВЛЕНО: используем правильный endpoint
            const url = `/api/court/${tournamentId}/${courtId}/data`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                console.error('API error:', data.error);
                return;
            }

            // Проверяем изменения и обновляем с анимацией
            updateScoreboard(data);
            lastData = data;

        } catch (error) {
            console.error('Update check failed:', error);
        }
    }

    /**
     * Обновление scoreboard
     */
    function updateScoreboard(data) {
        // Обновляем имена команд
        updateTeamNames(data);
        
        // Обновляем счёт по сетам
        updateSetScores(data);
        
        // Обновляем текущий счёт в геймах (колонка СЧЁТ)
        updateGameScore(data);
        
        // Обновляем флаги
        updateFlags(data);
    }

    /**
     * Обновление имён команд
     */
    function updateTeamNames(data) {
        const team1Players = data.team1_players || [];
        const team2Players = data.team2_players || [];

        // Team 1
        const team1Name1 = document.querySelector('[data-field="team1_player1"]');
        const team1Name2 = document.querySelector('[data-field="team1_player2"]');
        
        if (team1Name1 && team1Players[0]) {
            const newName = formatPlayerName(team1Players[0]);
            if (team1Name1.textContent !== newName) {
                team1Name1.textContent = newName;
            }
        }
        if (team1Name2 && team1Players[1]) {
            const newName = formatPlayerName(team1Players[1]);
            if (team1Name2.textContent !== newName) {
                team1Name2.textContent = newName;
            }
        }

        // Team 2
        const team2Name1 = document.querySelector('[data-field="team2_player1"]');
        const team2Name2 = document.querySelector('[data-field="team2_player2"]');
        
        if (team2Name1 && team2Players[0]) {
            const newName = formatPlayerName(team2Players[0]);
            if (team2Name1.textContent !== newName) {
                team2Name1.textContent = newName;
            }
        }
        if (team2Name2 && team2Players[1]) {
            const newName = formatPlayerName(team2Players[1]);
            if (team2Name2.textContent !== newName) {
                team2Name2.textContent = newName;
            }
        }
    }

    /**
     * Обновление счёта по сетам - только сыгранные
     */
    function updateSetScores(data) {
        const sets = data.detailed_result || [];
        const tableHeader = document.querySelector('.table-header-block');
        const team1Row = document.querySelector('.team-row[data-team="1"] .scores-block');
        const team2Row = document.querySelector('.team-row[data-team="2"] .scores-block');
        
        if (!tableHeader || !team1Row || !team2Row) return;
        
        // Получаем текущее количество сетов в DOM (исключая total)
        const currentSetHeaders = tableHeader.querySelectorAll('.header-cell:not(.total)');
        const currentSetCount = currentSetHeaders.length;
        
        // Если количество сетов изменилось - перестраиваем
        if (sets.length !== currentSetCount) {
            rebuildSets(sets, tableHeader, team1Row, team2Row);
        } else {
            // Обновляем существующие сеты
            for (let i = 0; i < sets.length; i++) {
                const set = sets[i];
                const score1 = set.firstParticipantScore ?? '-';
                const score2 = set.secondParticipantScore ?? '-';
                
                updateCellValue(`[data-field="team1_set${i + 1}"]`, score1);
                updateCellValue(`[data-field="team2_set${i + 1}"]`, score2);
            }
        }
    }

    /**
     * ИСПРАВЛЕНО: Получение счёта текущего гейма из detailed_result
     * В тай-брейке показывает очки тай-брейка, иначе теннисный формат (0, 15, 30, 40, AD)
     */
    function getGameScore(detailed, fallbackScore, participant) {
        if (!detailed || !detailed.length) {
            return fallbackScore || 0;
        }
        
        const lastSet = detailed[detailed.length - 1];
        if (!lastSet) {
            return fallbackScore || 0;
        }
        
        // gameScore содержит теннисный счет: "0", "15", "30", "40", "AD"
        // или в тай-брейке: "1", "2", "3"...
        const gameScore = lastSet.gameScore;
        if (gameScore && gameScore[participant] !== undefined) {
            return gameScore[participant];
        }
        
        return fallbackScore || 0;
    }

    /**
     * ИСПРАВЛЕНО: Обновление текущего счёта (СЧЁТ в total колонке)
     * Показывает теннисный счет текущего гейма
     */
    function updateGameScore(data) {
        const detailed = data.detailed_result || [];
        const eventState = (data.event_state || '').toLowerCase();
        const isFinished = eventState === 'finished';
        
        // ИСПРАВЛЕНО: Получаем теннисный счёт из gameScore
        const gameScore1 = getGameScore(detailed, data.team1_score, 'first');
        const gameScore2 = getGameScore(detailed, data.team2_score, 'second');
        
        // Обновляем колонку СЧЁТ (это текущий гейм)
        updateCellValue('[data-field="team1_total"]', gameScore1);
        updateCellValue('[data-field="team2_total"]', gameScore2);
    }

    /**
     * Обновление значения ячейки с анимацией
     */
    function updateCellValue(selector, newValue) {
        const cell = document.querySelector(selector);
        if (!cell) return;
        
        const oldValue = cell.textContent;
        const newValueStr = String(newValue);
        
        if (oldValue !== newValueStr) {
            cell.textContent = newValueStr;
            animateUpdate(cell);
        }
    }

    /**
     * Перестроение сетов при изменении количества
     */
    function rebuildSets(sets, tableHeader, team1Row, team2Row) {
        // Удаляем старые заголовки сетов (кроме СЧЁТ/total)
        const oldHeaders = tableHeader.querySelectorAll('.header-cell:not(.total)');
        oldHeaders.forEach(el => el.remove());
        
        // Удаляем старые ячейки счёта сетов
        const oldCells1 = team1Row.querySelectorAll('.score-cell:not(.total)');
        const oldCells2 = team2Row.querySelectorAll('.score-cell:not(.total)');
        oldCells1.forEach(el => el.remove());
        oldCells2.forEach(el => el.remove());
        
        // Находим точку вставки (перед total)
        const insertBeforeHeader = tableHeader.querySelector('.header-cell.total');
        const insertBeforeCell1 = team1Row.querySelector('.score-cell.total');
        const insertBeforeCell2 = team2Row.querySelector('.score-cell.total');
        
        // Добавляем новые сеты
        for (let i = 0; i < sets.length; i++) {
            const set = sets[i];
            
            // Заголовок
            const headerCell = document.createElement('div');
            headerCell.className = 'header-cell';
            headerCell.textContent = `СЕТ ${i + 1}`;
            tableHeader.insertBefore(headerCell, insertBeforeHeader);
            
            // Счёт команды 1
            const cell1 = document.createElement('div');
            cell1.className = 'score-cell';
            cell1.dataset.field = `team1_set${i + 1}`;
            cell1.textContent = set.firstParticipantScore ?? '-';
            team1Row.insertBefore(cell1, insertBeforeCell1);
            
            // Счёт команды 2
            const cell2 = document.createElement('div');
            cell2.className = 'score-cell';
            cell2.dataset.field = `team2_set${i + 1}`;
            cell2.textContent = set.secondParticipantScore ?? '-';
            team2Row.insertBefore(cell2, insertBeforeCell2);
            
            // Анимация появления
            animateUpdate(cell1);
            animateUpdate(cell2);
        }
    }

    /**
     * Обновление флагов
     */
    function updateFlags(data) {
        const team1Players = data.team1_players || [];
        const team2Players = data.team2_players || [];

        // Team 1 flags
        updateFlag('[data-field="team1_flag1"]', team1Players[0]?.countryCode);
        updateFlag('[data-field="team1_flag2"]', team1Players[1]?.countryCode);
        
        // Team 2 flags
        updateFlag('[data-field="team2_flag1"]', team2Players[0]?.countryCode);
        updateFlag('[data-field="team2_flag2"]', team2Players[1]?.countryCode);
    }

    /**
     * Обновление одного флага
     */
    function updateFlag(selector, countryCode) {
        const element = document.querySelector(selector);
        if (!element || !countryCode) return;
        
        const flagUrl = getFlagUrl(countryCode);
        element.style.backgroundImage = `url('${flagUrl}')`;
    }

    /**
     * Получение URL флага
     */
    function getFlagUrl(countryCode) {
        if (!countryCode) return '';
        
        let code = countryCode.toLowerCase();
        
        // Маппинг кодов
        const codeMap = {
            'rin': 'ru',
            'rus': 'ru',
            'bra': 'br',
            'arg': 'ar',
            'esp': 'es',
            'ita': 'it',
            'fra': 'fr',
            'ger': 'de',
            'gbr': 'gb',
            'usa': 'us',
            'den': 'dk',
            'dnk': 'dk'
        };
        
        code = codeMap[code] || code;
        return `https://flagcdn.com/w160/${code}.png`;
    }

    /**
     * Форматирование имени игрока
     */
    function formatPlayerName(player) {
        if (!player) return '';
        const firstName = player.firstName || '';
        const lastName = player.lastName || '';
        return `${firstName} ${lastName}`.trim().toUpperCase();
    }

    /**
     * Анимация обновления
     */
    function animateUpdate(element) {
        element.classList.remove('updating');
        // Trigger reflow
        void element.offsetWidth;
        element.classList.add('updating');
        
        setTimeout(() => {
            element.classList.remove('updating');
        }, CONFIG.animationDuration);
    }

    // Автопауза при скрытии вкладки
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            if (updateTimer) {
                clearInterval(updateTimer);
                updateTimer = null;
            }
        } else {
            startUpdates();
        }
    });

    // Запуск при загрузке
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();