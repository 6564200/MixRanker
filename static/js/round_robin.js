/**
 * round_robin.js - Масштабирование и AJAX обновление Round Robin таблицы
 * Базовое разрешение: FHD (динамическое)
 */

(function() {
    'use strict';

    // Конфигурация
    const CONFIG = {
        updateInterval: 10000,      // 10 секунд - проверка изменений
        fullReloadInterval: 120000, // 2 минуты - полная перезагрузка
        animationDuration: 300,
        margin: 20                  // Внешний отступ
    };

    // Состояние
    let container = null;
    let table = null;
    let tournamentId = null;
    let classId = null;
    let drawIndex = null;
    let currentData = null;
    let updateTimer = null;
    let reloadTimer = null;
    let isUpdating = false;

    /**
     * Масштабирование контейнера под размер окна
     */
    function scaleToFit() {
        if (!container || !table) return;
        
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        
        // Получаем размеры таблицы
        const tableWidth = table.offsetWidth;
        const tableHeight = table.offsetHeight;
        
        if (!tableWidth || !tableHeight) return;
        
        // Учитываем отступы
        const availableWidth = windowWidth - (CONFIG.margin * 2);
        const availableHeight = windowHeight - (CONFIG.margin * 2);
        
        // Вычисляем масштаб
        const scaleX = availableWidth / tableWidth;
        const scaleY = availableHeight / tableHeight;
        const scale = Math.min(scaleX, scaleY, 1); // Не больше 1
        
        container.style.transform = `scale(${scale})`;
        
        // Центрируем
        const scaledWidth = tableWidth * scale;
        const scaledHeight = tableHeight * scale;
        
        const offsetX = Math.max(CONFIG.margin, (windowWidth - scaledWidth) / 2);
        const offsetY = Math.max(CONFIG.margin, (windowHeight - scaledHeight) / 2);
        
        container.style.position = 'absolute';
        container.style.left = offsetX + 'px';
        container.style.top = offsetY + 'px';
    }

    /**
     * Инициализация
     */
    function init() {
        container = document.querySelector('.round-robin-container');
        table = document.querySelector('.round-robin-table');
        
        if (!container) {
            console.error('Round Robin container not found');
            return;
        }

        // Получаем параметры
        tournamentId = container.dataset.tournamentId;
        classId = container.dataset.classId;
        drawIndex = container.dataset.drawIndex;

        // Сохраняем текущие данные для сравнения
        currentData = extractCurrentData();

        // Масштабирование
        scaleToFit();
        window.addEventListener('resize', scaleToFit);

        // Запускаем обновления если есть данные
        if (tournamentId && classId) {
            console.log(`Round Robin: initialized for ${tournamentId}/${classId}/${drawIndex}`);
            startUpdates();
        }
    }

    /**
     * Извлечение текущих данных из DOM
     */
    function extractCurrentData() {
        const data = {
            matches: {},
            points: {},
            places: {}
        };

        // Собираем данные матчей
        document.querySelectorAll('.match-cell[data-row][data-col]').forEach(cell => {
            const row = cell.dataset.row;
            const col = cell.dataset.col;
            const key = `${row}_${col}`;
            
            const scoreEl = cell.querySelector('.match-score');
            const setsEl = cell.querySelector('.match-sets');
            
            data.matches[key] = {
                score: scoreEl ? scoreEl.textContent : '',
                sets: setsEl ? setsEl.textContent : ''
            };
        });

        // Собираем очки и места
        document.querySelectorAll('.team-row').forEach((row, idx) => {
            const pointsEl = row.querySelector('.points-z');
            const placeEl = row.querySelector('.place-z');
            
            data.points[idx] = pointsEl ? pointsEl.textContent : '';
            data.places[idx] = placeEl ? placeEl.textContent : '';
        });

        return data;
    }

    /**
     * Запуск периодических обновлений
     */
    function startUpdates() {
        if (updateTimer) clearInterval(updateTimer);
        if (reloadTimer) clearInterval(reloadTimer);
        
        // AJAX проверка
        updateTimer = setInterval(checkForUpdates, CONFIG.updateInterval);
        
        // Полная перезагрузка
        reloadTimer = setInterval(() => {
            console.log('Round Robin: full page reload');
            location.reload();
        }, CONFIG.fullReloadInterval);
    }

    /**
     * Проверка обновлений через API
     */
    async function checkForUpdates() {
        if (isUpdating || !tournamentId || !classId) return;
        isUpdating = true;

        try {
            const url = `/api/round-robin/${tournamentId}/${classId}/${drawIndex}/data`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                console.error('API error:', data.error);
                return;
            }

            // Применяем обновления
            applyUpdates(data);

        } catch (error) {
            console.error('Update check failed:', error);
        } finally {
            isUpdating = false;
        }
    }

    /**
     * Применение обновлений к DOM
     */
    function applyUpdates(data) {
        let hasChanges = false;

        // Обновляем матчи
        if (data.matches) {
            Object.entries(data.matches).forEach(([key, matchData]) => {
                const [row, col] = key.split('_');
                const cell = document.querySelector(`.match-cell[data-row="${row}"][data-col="${col}"]`);
                
                if (cell) {
                    const updated = updateMatchCell(cell, matchData);
                    if (updated) hasChanges = true;
                }
            });
        }

        // Обновляем очки
        if (data.standings) {
            data.standings.forEach((standing, idx) => {
                const row = document.querySelectorAll('.team-row')[idx];
                if (row) {
                    const pointsEl = row.querySelector('.points-z');
                    const placeEl = row.querySelector('.place-z');
                    
                    if (pointsEl && pointsEl.textContent !== String(standing.points)) {
                        animateUpdate(pointsEl, standing.points);
                        hasChanges = true;
                    }
                    
                    if (placeEl && placeEl.textContent !== String(standing.place)) {
                        animateUpdate(placeEl, standing.place);
                        hasChanges = true;
                    }
                }
            });
        }

        if (hasChanges) {
            console.log('Round Robin: data updated');
            // Пересчитываем масштаб после обновления
            setTimeout(scaleToFit, 100);
        }
    }

    /**
     * Обновление ячейки матча
     */
    function updateMatchCell(cell, data) {
        const scoreEl = cell.querySelector('.match-score');
        const setsEl = cell.querySelector('.match-sets');
        
        let updated = false;
        
        if (scoreEl && data.score !== undefined) {
            const newScore = String(data.score);
            if (scoreEl.textContent !== newScore) {
                cell.classList.add('updating');
                scoreEl.textContent = newScore;
                updated = true;
            }
        }
        
        if (setsEl && data.sets !== undefined) {
            const newSets = String(data.sets);
            if (setsEl.textContent !== newSets) {
                setsEl.textContent = newSets;
                updated = true;
            }
        }
        
        if (updated) {
            // Анимация обновления
            setTimeout(() => {
                cell.classList.remove('updating');
                cell.classList.add('updated');
            }, CONFIG.animationDuration);
            
            setTimeout(() => {
                cell.classList.remove('updated');
            }, CONFIG.animationDuration + 1000);
        }
        
        return updated;
    }

    /**
     * Анимация обновления значения
     */
    function animateUpdate(element, newValue) {
        element.classList.add('updating');
        element.textContent = newValue;
        
        setTimeout(() => {
            element.classList.remove('updating');
        }, 500);
    }

    /**
     * Обновление конкретного поля по data-field
     */
    function updateField(fieldName, newValue) {
        const element = document.querySelector(`[data-field="${fieldName}"]`);
        if (!element) return false;
        
        const currentValue = element.textContent;
        if (currentValue === String(newValue)) return false;
        
        animateUpdate(element, newValue);
        return true;
    }

    // Запуск при загрузке
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
