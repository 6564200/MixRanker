/**
 * Elimination Live Updates
 * AJAX обновление турнирной сетки без перезагрузки страницы
 * Базовое разрешение: FHD 1920x1080
 */

(function() {
    'use strict';

    // Конфигурация
    const CONFIG = {
        BASE_WIDTH: 1920,
        BASE_HEIGHT: 1080,
        updateInterval: 10000,      // 10 секунд - проверка изменений
        fullReloadInterval: 120000, // 2 минуты - полная перезагрузка
        animationDuration: 300,
        retryDelay: 5000
    };

    // Состояние
    let container = null;
    let currentVersion = null;
    let tournamentId = null;
    let classId = null;
    let drawIndex = null;
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
        container = document.querySelector('.elimination-container');
        if (!container) {
            console.error('Elimination container not found');
            return;
        }

        tournamentId = container.dataset.tournamentId;
        classId = container.dataset.classId;
        drawIndex = container.dataset.drawIndex || '0';
        currentVersion = container.dataset.version || null;

        // Масштабирование
        scaleToFit();
        window.addEventListener('resize', scaleToFit);

        if (!tournamentId || !classId) {
            console.error('Tournament ID or Class ID not found');
            return;
        }

        console.log(`Elimination Live: initialized for tournament ${tournamentId}, class ${classId}`);
        
        // Анимация появления
        animateInitialAppearance();
        
        startUpdates();
    }

    /**
     * Анимация начального появления
     */
    function animateInitialAppearance() {
        const matches = container.querySelectorAll('.container');
        matches.forEach((match, index) => {
            match.style.opacity = '0';
            match.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                match.style.transition = 'opacity 0.4s ease-out, transform 0.4s ease-out';
                match.style.opacity = '1';
                match.style.transform = 'translateY(0)';
            }, 50 + index * 30);
        });
    }

    /**
     * Запуск периодических обновлений
     */
    function startUpdates() {
        if (updateTimer) clearInterval(updateTimer);
        if (reloadTimer) clearInterval(reloadTimer);
        
        updateTimer = setInterval(checkForUpdates, CONFIG.updateInterval);
        
        reloadTimer = setInterval(() => {
            console.log('Elimination Live: full page reload');
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
            const url = `/api/elimination/${tournamentId}/${classId}/data?draw_index=${drawIndex}`;
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
                console.log(`Elimination Live: updating (${currentVersion} -> ${data.version})`);
                await updateBracket(data);
                currentVersion = data.version;
            }

        } catch (error) {
            console.error('Update check failed:', error);
        } finally {
            isUpdating = false;
        }
    }

    /**
     * Обновление турнирной сетки
     */
    async function updateBracket(data) {
        const { matches } = data;
        
        if (!matches || !Array.isArray(matches)) return;

        matches.forEach(matchData => {
            const matchEl = findMatchElement(matchData.match_id);
            if (matchEl) {
                updateMatchElement(matchEl, matchData);
            }
        });
    }

    /**
     * Поиск элемента матча
     */
    function findMatchElement(matchId) {
        return container.querySelector(`.container[data-match-id="${matchId}"]`);
    }

    /**
     * Обновление элемента матча
     */
    function updateMatchElement(el, data) {
        const rowTop = el.querySelector('.row-top');
        const rowBottom = el.querySelector('.row-bottom');
        
        if (!rowTop || !rowBottom) return;

        // Проверяем изменения
        const currentTeam1 = rowTop.querySelector('.name-main')?.textContent;
        const currentTeam2 = rowBottom.querySelector('.name-main')?.textContent;
        const currentScore1 = rowTop.querySelector('.rank-number')?.textContent;
        const currentScore2 = rowBottom.querySelector('.rank-number')?.textContent;
        
        const hasChanges = 
            currentTeam1 !== data.team_1_name ||
            currentTeam2 !== data.team_2_name ||
            currentScore1 !== data.score1 ||
            currentScore2 !== data.score2;

        if (!hasChanges) return;

        // Обновляем имена
        const name1 = rowTop.querySelector('.name-main');
        const name2 = rowBottom.querySelector('.name-main');
        
        if (name1) {
            name1.textContent = data.team_1_name;
            name1.className = `name-main ${data.secondary1 || ''}`;
        }
        if (name2) {
            name2.textContent = data.team_2_name;
            name2.className = `name-main ${data.secondary2 || ''}`;
        }

        // Обновляем счёт сетов
        updateSetScores(rowTop, data.sets1);
        updateSetScores(rowBottom, data.sets2);

        // Обновляем общий счёт
        const rank1 = rowTop.querySelector('.rank-number');
        const rank2 = rowBottom.querySelector('.rank-number');
        
        if (rank1) rank1.textContent = data.score1;
        if (rank2) rank2.textContent = data.score2;

        // Анимация обновления
        el.classList.add('updated');
        setTimeout(() => el.classList.remove('updated'), 1500);
    }

    /**
     * Обновление счёта сетов
     */
    function updateSetScores(row, setsStr) {
        const scoreContainer = row.querySelector('.score');
        if (!scoreContainer) return;

        const sets = (setsStr || '').split(' ').filter(s => s);
        
        scoreContainer.innerHTML = sets.map(s => 
            `<span class="set-score">${s}</span>`
        ).join('');
    }

    /**
     * Добавляем CSS для анимаций
     */
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Анимация появления */
            .container {
                transition: opacity 0.4s ease-out, transform 0.4s ease-out;
            }
            
            /* Анимация обновления */
            .container.updated {
                animation: highlightUpdate 1.5s ease-out;
            }
            
            @keyframes highlightUpdate {
                0% {
                    box-shadow: 0 0 0 0 rgba(174, 211, 91, 0.8);
                }
                30% {
                    box-shadow: 0 0 25px 8px rgba(174, 211, 91, 0.6);
                }
                100% {
                    box-shadow: 0 0 0 0 rgba(174, 211, 91, 0);
                }
            }
            
            /* Анимация изменения счёта */
            .rank-number {
                transition: transform 0.3s ease-out;
            }
            
            .container.updated .rank-number {
                animation: scoreChange 0.5s ease-out;
            }
            
            @keyframes scoreChange {
                0% { transform: scale(1); }
                50% { transform: scale(1.3); }
                100% { transform: scale(1); }
            }
            
            /* Анимация изменения имени (при переходе участника) */
            .name-main {
                transition: color 0.3s ease-out;
            }
            
            /* Подсветка проигравшего */
            .name-main.lost {
                transition: color 0.5s ease-out;
            }
            
            /* Fade out анимация */
            .fade-out {
                animation: fadeOut 0.3s ease-out forwards;
            }
            
            @keyframes fadeOut {
                from { opacity: 1; }
                to { opacity: 0; }
            }
            
            /* Fade in анимация */
            .fade-in {
                animation: fadeIn 0.4s ease-out forwards;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
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
