/**
 * Schedule Live Updates
 * AJAX обновление расписания без перезагрузки страницы
 */

(function() {
    'use strict';

    // Конфигурация
    const CONFIG = {
        updateInterval: 10000,  // 10 секунд - проверка изменений
        fullReloadInterval: 60000,  // 60 секунд - полная перезагрузка
        animationDuration: 300,
        retryDelay: 5000
    };

    // Состояние
    let currentVersion = null;
    let tournamentId = null;
    let targetDate = null;
    let updateTimer = null;
    let reloadTimer = null;
    let isUpdating = false;

    /**
     * Инициализация
     */
    function init() {
        // Получаем параметры из data-атрибутов или URL
        const container = document.querySelector('.schedule-container');
        if (!container) {
            console.error('Schedule container not found');
            return;
        }

        tournamentId = container.dataset.tournamentId;
        targetDate = container.dataset.targetDate || null;
        currentVersion = container.dataset.version || null;

        if (!tournamentId) {
            console.error('Tournament ID not found');
            return;
        }

        console.log(`Schedule Live: initialized for tournament ${tournamentId}`);
        
        // Запускаем периодические обновления
        startUpdates();
    }

    /**
     * Запуск периодических обновлений
     */
    function startUpdates() {
        if (updateTimer) {
            clearInterval(updateTimer);
        }
        if (reloadTimer) {
            clearInterval(reloadTimer);
        }
        
        // AJAX проверка каждые 10 сек
        updateTimer = setInterval(checkForUpdates, CONFIG.updateInterval);
        
        // Полная перезагрузка раз в минуту
        reloadTimer = setInterval(() => {
            console.log('Schedule Live: full page reload');
            location.reload();
        }, CONFIG.fullReloadInterval);
    }

    /**
     * Проверка обновлений
     */
    async function checkForUpdates() {
        if (isUpdating) return;
        isUpdating = true;

        try {
            const url = `/api/schedule/${tournamentId}/data` + (targetDate ? `?date=${targetDate}` : '');
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                console.error('API error:', data.error);
                return;
            }

            // Проверяем изменилась ли версия
            if (data.version !== currentVersion) {
                console.log(`Schedule Live: updating (${currentVersion} -> ${data.version})`);
                await updateSchedule(data);
                currentVersion = data.version;
            }

        } catch (error) {
            console.error('Update check failed:', error);
        } finally {
            isUpdating = false;
        }
    }

    /**
     * Обновление расписания
     */
    async function updateSchedule(data) {
        const { time_slots, courts, matches } = data;
        
        // Добавляем класс для fade-out анимации
        const container = document.querySelector('.schedule-container');
        const mainGrid = container.querySelector('.main-grid');
        
        if (mainGrid) {
            mainGrid.style.opacity = '0';
            mainGrid.style.transition = 'opacity 0.3s ease-out';
        }
        
        // Ждём завершения fade-out
        await new Promise(resolve => setTimeout(resolve, 300));

        // Обновляем time slots
        updateTimeSlots(time_slots);

        // Обновляем заголовки кортов
        updateCourtHeaders(courts);

        // Полностью перестраиваем матчи
        rebuildMatches(matches, time_slots, courts);
        
        // Fade-in
        if (mainGrid) {
            mainGrid.style.opacity = '1';
        }
    }
    
    /**
     * Полная перестройка матчей
     */
    function rebuildMatches(matches, timeSlots, courts) {
        const matchesGrid = document.querySelector('.matches-grid');
        if (!matchesGrid) return;
        
        // Обновляем grid стили
        matchesGrid.style.gridTemplateRows = `repeat(${timeSlots.length}, 86px)`;
        matchesGrid.style.gridTemplateColumns = `repeat(${courts.length}, 534px)`;
        
        // Очищаем
        matchesGrid.innerHTML = '';
        
        // Создаём новые элементы
        matches.forEach(match => {
            const el = createMatchElement(match);
            matchesGrid.appendChild(el);
        });
    }

    /**
     * Обновление временных слотов
     */
    function updateTimeSlots(timeSlots) {
        const timeScale = document.querySelector('.time-scale');
        if (!timeScale) return;

        const currentSlots = Array.from(timeScale.querySelectorAll('.time-slot'));
        const currentTimes = currentSlots.map(el => el.textContent.trim());

        // Проверяем нужно ли обновлять
        if (JSON.stringify(currentTimes) === JSON.stringify(timeSlots)) {
            return;
        }

        // Обновляем grid-template-rows
        timeScale.style.gridTemplateRows = `repeat(${timeSlots.length}, 86px)`;

        // Создаём новые слоты
        const fragment = document.createDocumentFragment();
        timeSlots.forEach((time, index) => {
            const slot = document.createElement('div');
            slot.className = 'time-slot';
            slot.textContent = time;
            slot.style.animationDelay = `${0.1 + index * 0.05}s`;
            fragment.appendChild(slot);
        });

        // Fade out старые, заменяем, fade in новые
        currentSlots.forEach(slot => slot.classList.add('fade-out'));
        
        setTimeout(() => {
            timeScale.innerHTML = '';
            timeScale.appendChild(fragment);
        }, 200);
    }

    /**
     * Обновление заголовков кортов
     */
    function updateCourtHeaders(courts) {
        const courtsHeader = document.querySelector('.courts-header');
        if (!courtsHeader) return;

        const currentHeaders = Array.from(courtsHeader.querySelectorAll('.court-header h3'));
        const currentCourts = currentHeaders.map(el => el.textContent.trim());

        if (JSON.stringify(currentCourts) === JSON.stringify(courts)) {
            return;
        }

        // Пересоздаём заголовки
        const fragment = document.createDocumentFragment();
        courts.forEach(court => {
            const header = document.createElement('div');
            header.className = 'court-header';
            header.innerHTML = `<h3>${court}</h3>`;
            fragment.appendChild(header);
        });

        courtsHeader.innerHTML = '';
        courtsHeader.appendChild(fragment);
    }

    /**
     * Обновление матчей
     */
    function updateMatches(matches, timeSlots, courts) {
        const matchesGrid = document.querySelector('.matches-grid');
        if (!matchesGrid) return;

        // Создаём map текущих матчей по позиции
        const currentMatches = new Map();
        matchesGrid.querySelectorAll('.match-item').forEach(el => {
            const style = el.getAttribute('style') || '';
            const rowMatch = style.match(/grid-row:\s*(\d+)/);
            const colMatch = style.match(/grid-column:\s*(\d+)/);
            if (rowMatch && colMatch) {
                const key = `${rowMatch[1]}-${colMatch[1]}`;
                currentMatches.set(key, el);
            }
        });

        // Создаём map новых матчей
        const newMatchesMap = new Map();
        matches.forEach(match => {
            const key = `${match.row}-${match.col}`;
            newMatchesMap.set(key, match);
        });

        // Обновляем grid columns
        const numCols = courts.length;
        matchesGrid.querySelectorAll('.court-column').forEach((col, idx) => {
            if (idx >= numCols) {
                col.remove();
            }
        });

        // Находим изменения
        const toRemove = [];
        const toAdd = [];
        const toUpdate = [];

        // Проверяем какие матчи удалить или обновить
        currentMatches.forEach((el, key) => {
            if (!newMatchesMap.has(key)) {
                toRemove.push(el);
            } else {
                toUpdate.push({ el, data: newMatchesMap.get(key) });
            }
        });

        // Проверяем какие матчи добавить
        newMatchesMap.forEach((data, key) => {
            if (!currentMatches.has(key)) {
                toAdd.push(data);
            }
        });

        // Выполняем обновления
        // 1. Удаляем с анимацией
        toRemove.forEach(el => {
            el.classList.add('fade-out');
            setTimeout(() => el.remove(), 300);
        });

        // 2. Обновляем существующие
        toUpdate.forEach(({ el, data }) => {
            updateMatchElement(el, data);
        });

        // 3. Добавляем новые с анимацией
        setTimeout(() => {
            toAdd.forEach(data => {
                const el = createMatchElement(data);
                // Находим или создаём колонку корта
                let courtColumn = matchesGrid.querySelector(`.court-column[data-court="${data.court}"]`);
                if (!courtColumn) {
                    courtColumn = document.createElement('div');
                    courtColumn.className = 'court-column';
                    courtColumn.dataset.court = data.court;
                    courtColumn.style.display = 'grid';
                    courtColumn.style.gridTemplateRows = `repeat(${timeSlots.length}, 86px)`;
                    courtColumn.style.gap = '16px';
                    matchesGrid.appendChild(courtColumn);
                }
                courtColumn.appendChild(el);
            });
        }, toRemove.length > 0 ? 300 : 0);
    }

    /**
     * Обновление элемента матча
     */
    function updateMatchElement(el, data) {
        const statusClass = `match-${data.status}`;
        const rowClass = `row-${data.row}`;

        // Обновляем классы статуса
        el.classList.remove('match-finished', 'match-active', 'match-future');
        el.classList.add(statusClass);

        // Обновляем row class
        el.className = el.className.replace(/row-\d+/g, '');
        el.classList.add(rowClass);

        // Обновляем имена
        const teamNames = el.querySelectorAll('.match-team-name');
        if (teamNames[0]) teamNames[0].textContent = data.challenger;
        if (teamNames[1]) teamNames[1].textContent = data.challenged;

        // Обновляем счёт
        const scores = el.querySelectorAll('.match-team-score');
        const teams = el.querySelectorAll('.match-team');

        // Challenger score
        if (data.challenger_score && data.challenger_score !== 'Won W.O.') {
            if (scores[0]) {
                scores[0].textContent = data.challenger_score;
            } else if (teams[0]) {
                const scoreDiv = document.createElement('div');
                scoreDiv.className = 'match-team-score';
                scoreDiv.textContent = data.challenger_score;
                teams[0].appendChild(scoreDiv);
            }
        }

        // Challenged score
        if (data.challenged_score && data.challenged_score !== 'Won W.O.') {
            if (scores[1]) {
                scores[1].textContent = data.challenged_score;
            } else if (teams[1]) {
                const scoreDiv = document.createElement('div');
                scoreDiv.className = 'match-team-score';
                scoreDiv.textContent = data.challenged_score;
                teams[1].appendChild(scoreDiv);
            }
        }

        // Номер матча
        const matchNumber = el.querySelector('.match-number');
        if (matchNumber) matchNumber.textContent = data.episode;

        // Подсветка изменения
        el.classList.add('updated');
        setTimeout(() => el.classList.remove('updated'), 1000);
    }

    /**
     * Создание элемента матча
     */
    function createMatchElement(data) {
        const statusClass = `match-${data.status}`;
        const rowClass = `row-${data.row}`;

        const el = document.createElement('div');
        el.className = `match-item ${statusClass} ${rowClass}`;
        el.style.cssText = `grid-row: ${data.row}; grid-column: ${data.col};`;

        const challengerWO = data.challenger_score === 'Won W.O.';
        const challengedWO = data.challenged_score === 'Won W.O.';

        const challengerScoreHtml = data.challenger_score && !challengerWO 
            ? `<div class="match-team-score">${data.challenger_score}</div>` : '';
        const challengedScoreHtml = data.challenged_score && !challengedWO 
            ? `<div class="match-team-score">${data.challenged_score}</div>` : '';
        
        const challengerWOHtml = challengerWO ? `<div class="match-team-wo">W.O.</div>` : '';
        const challengedWOHtml = challengedWO ? `<div class="match-team-wo">W.O.</div>` : '';

        el.innerHTML = `
            <div class="match-content">
                <div class="match-number">${data.episode}</div>
                <div class="match-teams-wrapper">
                    <div class="match-team">
                        <div class="match-team-name">${data.challenger}</div>
                        ${challengerWOHtml}${challengerScoreHtml}
                    </div>
                    <div class="match-team">
                        <div class="match-team-name">${data.challenged}</div>
                        ${challengedWOHtml}${challengedScoreHtml}
                    </div>
                </div>
            </div>
        `;

        return el;
    }

    /**
     * Добавляем CSS для анимаций обновления
     */
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .fade-out {
                animation: fadeOutDown 0.3s ease-out forwards !important;
            }
            
            @keyframes fadeOutDown {
                from {
                    opacity: 1;
                    transform: translateY(0);
                }
                to {
                    opacity: 0;
                    transform: translateY(10px);
                }
            }
            
            .match-item.updated {
                animation: highlightUpdate 1s ease-out;
            }
            
            @keyframes highlightUpdate {
                0% {
                    box-shadow: 0 0 0 0 rgba(174, 213, 87, 0.7);
                }
                50% {
                    box-shadow: 0 0 20px 5px rgba(174, 213, 87, 0.5);
                }
                100% {
                    box-shadow: 0 0 0 0 rgba(174, 213, 87, 0);
                }
            }
        `;
        document.head.appendChild(style);
    }

    // Запуск при загрузке страницы
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            injectStyles();
            init();
        });
    } else {
        injectStyles();
        init();
    }

})();