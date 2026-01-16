/**
 * Schedule Live Updates
 * AJAX обновление расписания без перезагрузки страницы
 * Базовое разрешение: FHD 1920x1080
 */

(function() {
    'use strict';

    // Конфигурация
    const CONFIG = {
        BASE_WIDTH: 1920,
        BASE_HEIGHT: 1080,
        updateInterval: 10000,  // 10 секунд - проверка изменений
        fullReloadInterval: 60000,  // 60 секунд - полная перезагрузка
        animationDuration: 300,
        retryDelay: 5000
    };

    // Состояние
    let container = null;
    let currentVersion = null;
    let tournamentId = null;
    let targetDate = null;
    let updateTimer = null;
    let reloadTimer = null;
    let isUpdating = false;

    /**
     * Масштабирование контейнера под размер окна
     */
    function scaleToFit() {
        if (!container) return;
        
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        
        const scaleX = windowWidth / CONFIG.BASE_WIDTH;
        const scaleY = windowHeight / CONFIG.BASE_HEIGHT;
        const scale = Math.min(scaleX, scaleY);
        
        container.style.transform = `scale(${scale})`;
        container.style.transformOrigin = 'top left';
        
        // Центрируем если есть свободное место
        const scaledWidth = CONFIG.BASE_WIDTH * scale;
        const scaledHeight = CONFIG.BASE_HEIGHT * scale;
        
        const offsetX = Math.max(0, (windowWidth - scaledWidth) / 2);
        const offsetY = Math.max(0, (windowHeight - scaledHeight) / 2);
        
        container.style.position = 'absolute';
        container.style.left = offsetX + 'px';
        container.style.top = offsetY + 'px';
    }

    /**
     * Инициализация
     */
    function init() {
        container = document.querySelector('.schedule-container');
        if (!container) {
            console.error('Schedule container not found');
            return;
        }

        tournamentId = container.dataset.tournamentId;
        targetDate = container.dataset.targetDate || null;
        currentVersion = container.dataset.version || null;

        // Масштабирование
        scaleToFit();
        window.addEventListener('resize', scaleToFit);

        if (!tournamentId) {
            console.error('Tournament ID not found');
            return;
        }

        console.log(`Schedule Live: initialized for tournament ${tournamentId}`);
        
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
        
        updateTimer = setInterval(checkForUpdates, CONFIG.updateInterval);
        
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
        
        const container = document.querySelector('.schedule-container');
        const mainGrid = container.querySelector('.main-grid');
        
        if (mainGrid) {
            mainGrid.style.opacity = '0';
            mainGrid.style.transition = 'opacity 0.3s ease-out';
        }
        
        await new Promise(resolve => setTimeout(resolve, 300));

        updateTimeSlots(time_slots);
        updateCourtHeaders(courts);
        rebuildMatches(matches, time_slots, courts);
        
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
        
        // FHD размеры (увеличенные)
        matchesGrid.style.gridTemplateRows = `repeat(${timeSlots.length}, 86px)`;
        matchesGrid.style.gridTemplateColumns = `repeat(${courts.length}, 1fr)`;
        
        matchesGrid.innerHTML = '';
        
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

        if (JSON.stringify(currentTimes) === JSON.stringify(timeSlots)) {
            return;
        }

        // Обновляем grid-template-rows (FHD размеры увеличенные)
        timeScale.style.gridTemplateRows = `repeat(${timeSlots.length}, 86px)`;

        const fragment = document.createDocumentFragment();
        timeSlots.forEach((time, index) => {
            const slot = document.createElement('div');
            slot.className = 'time-slot';
            slot.textContent = time;
            slot.style.animationDelay = `${0.1 + index * 0.05}s`;
            fragment.appendChild(slot);
        });

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

        // Обновляем grid-template-columns
        courtsHeader.style.gridTemplateColumns = `repeat(${courts.length}, 1fr)`;

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
     * Обновление элемента матча
     */
    function updateMatchElement(el, data) {
        const statusClass = `match-${data.status}`;
        const rowClass = `row-${data.row}`;

        el.classList.remove('match-finished', 'match-active', 'match-future');
        el.classList.add(statusClass);

        el.className = el.className.replace(/row-\d+/g, '');
        el.classList.add(rowClass);

        // Обновляем имена (поддержка обоих форматов)
        const teamNamesContainers = el.querySelectorAll('.match-team-names');
        const teamNamesSingle = el.querySelectorAll('.match-team-name');
        
        if (teamNamesContainers.length >= 2) {
            // Новый формат с вертикальными именами
            updatePlayerNames(teamNamesContainers[0], data.challenger_players || [data.challenger]);
            updatePlayerNames(teamNamesContainers[1], data.challenged_players || [data.challenged]);
        } else if (teamNamesSingle.length >= 2) {
            // Старый формат
            teamNamesSingle[0].textContent = data.challenger;
            teamNamesSingle[1].textContent = data.challenged;
        }

        // Обновляем счёт
        const scores = el.querySelectorAll('.match-team-score');
        const teams = el.querySelectorAll('.match-team');

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

        const matchNumber = el.querySelector('.match-number');
        if (matchNumber) matchNumber.textContent = data.episode;

        el.classList.add('updated');
        setTimeout(() => el.classList.remove('updated'), 1000);
    }

    /**
     * Обновление имён игроков в контейнере
     */
    function updatePlayerNames(container, players) {
        container.innerHTML = '';
        players.forEach(player => {
            const div = document.createElement('div');
            div.className = 'match-player-name';
            div.textContent = player;
            container.appendChild(div);
        });
    }

    /**
     * Разбиение имени команды на игроков
     */
    function splitTeamName(teamName) {
        if (!teamName) return ['TBD'];
        if (teamName.includes('/')) {
            return teamName.split('/').map(p => p.trim()).filter(p => p);
        }
        return [teamName];
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

        // Разбиваем имена на игроков
        const challengerPlayers = data.challenger_players || splitTeamName(data.challenger);
        const challengedPlayers = data.challenged_players || splitTeamName(data.challenged);

        function createTeamHtml(players, wo, score) {
            const woHtml = wo ? `<div class="match-team-wo">W.O.</div>` : '';
            const scoreHtml = score && !wo ? `<div class="match-team-score">${score}</div>` : '';
            
            if (players.length === 1) {
                return `<div class="match-team">
                    <div class="match-team-name">${players[0]}</div>
                    ${woHtml}${scoreHtml}
                </div>`;
            }
            
            const playersHtml = players.slice(0, 2).map(p => 
                `<div class="match-player-name">${p}</div>`
            ).join('');
            
            return `<div class="match-team">
                <div class="match-team-names">${playersHtml}</div>
                ${woHtml}${scoreHtml}
            </div>`;
        }

        el.innerHTML = `
            <div class="match-content">
                <div class="match-number">${data.episode}</div>
                <div class="match-teams-wrapper">
                    ${createTeamHtml(challengerPlayers, challengerWO, data.challenger_score)}
                    ${createTeamHtml(challengedPlayers, challengedWO, data.challenged_score)}
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