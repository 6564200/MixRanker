/**
 * Display Court - логика автоматического/ручного режима
 */

(function() {
    'use strict';

    const CONFIG = {
        checkInterval: 2000,      // Проверка состояния каждые 2 сек
        fadeTime: 500             // Время fade эффекта (мс)
    };

    let slotNumber = null;
    let tournamentId = null;
    let courtId = null;
    let mode = 'auto';
    let currentPage = null;
    let currentState = null;
    let checkTimer = null;

    /**
     * Инициализация
     */
    function init() {
        const container = document.querySelector('.display-container');
        if (!container) {
            console.error('Display container not found');
            return;
        }

        slotNumber = parseInt(container.dataset.slot);
        tournamentId = container.dataset.tournamentId;
        courtId = container.dataset.courtId;
        mode = container.dataset.mode || 'auto';

        console.log(`Display Court ${slotNumber}: initialized, tournament=${tournamentId}, court=${courtId}, mode=${mode}`);

        // Первая проверка
        checkState();
        
        // Периодическая проверка состояния
        checkTimer = setInterval(checkState, CONFIG.checkInterval);
    }

    /**
     * Проверка состояния корта
     */
    async function checkState() {
        try {
            const response = await fetch(`/api/display/court/${slotNumber}/state`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            // Обновляем режим если изменился
            if (data.mode && data.mode !== mode) {
                mode = data.mode;
                console.log(`Mode changed to: ${mode}`);
            }
            
            // В ручном режиме используем manual_page
            if (mode === 'manual' && data.manual_page) {
                handleManualMode(data);
                return;
            }
            
            // В автоматическом режиме
            handleAutoMode(data);
            
        } catch (error) {
            console.error('Failed to check state:', error);
        }
    }

    /**
     * Обработка автоматического режима
     */
    function handleAutoMode(data) {
        const newState = data.state;
        const newPage = data.page;
        const newUrl = data.url;
        
        // Показываем заглушку если корт пуст
        if (newPage === 'empty' || newState === 'empty' || newState === 'not_configured') {
            showEmptyState();
            currentPage = 'empty';
            currentState = newState;
            return;
        }
        
        // Скрываем заглушку
        hideEmptyState();
        
        // Если страница не изменилась - не перезагружаем
        if (newPage === currentPage && newState === currentState) {
            return;
        }
        
        console.log(`State changed: ${currentState} -> ${newState}, page: ${currentPage} -> ${newPage}`);
        
        currentPage = newPage;
        currentState = newState;
        
        if (newUrl) {
            loadPage(newUrl);
        }
    }

    /**
     * Обработка ручного режима
     */
    function handleManualMode(data) {
        const manualPage = data.manual_page;
        
        // Если страница не изменилась
        if (manualPage === currentPage && mode === 'manual') {
            return;
        }
        
        // Заглушка - показываем empty state
        if (manualPage === 'empty') {
            showEmptyState();
            currentPage = 'empty';
            return;
        }
        
        hideEmptyState();
        
        // Получаем настройки окна для tournament_id, court_id и custom_url
        fetchWindowConfig().then(window => {
            if (!window) {
                console.log('No window config');
                showEmptyState();
                return;
            }
            
            // Произвольный URL
            if (manualPage === 'custom') {
                const customUrl = window.settings?.custom_url;
                if (customUrl) {
                    currentPage = 'custom';
                    loadPage(customUrl);
                } else {
                    console.log('No custom URL configured');
                    showEmptyState();
                }
                return;
            }
            
            // Стандартные страницы - требуют tournament_id и court_id
            if (!window.tournament_id || !window.court_id) {
                console.log('No tournament/court configured');
                showEmptyState();
                return;
            }
            
            const pageUrls = {
                'vs': `/api/html-live/${window.tournament_id}/${window.court_id}/vs`,
                'scoreboard': `/api/html-live/${window.tournament_id}/${window.court_id}/score_full`,
                'winner': `/api/html-live/${window.tournament_id}/${window.court_id}/winner`,
                'introduction': `/api/html-live/${window.tournament_id}/${window.court_id}/introduction`
            };
            
            const url = pageUrls[manualPage];
            if (url) {
                currentPage = manualPage;
                loadPage(url);
            }
        });
    }

    /**
     * Получение конфигурации окна
     */
    async function fetchWindowConfig() {
        try {
            const response = await fetch(`/api/display/window/court/${slotNumber}`);
            if (!response.ok) return null;
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch window config:', error);
            return null;
        }
    }

    /**
     * Показать заглушку с fade эффектом
     */
    function showEmptyState() {
        const emptyState = document.querySelector('.empty-state');
        const content = document.querySelector('.display-content');
        const overlay = document.querySelector('.fade-overlay');
        
        if (!emptyState) return;
        
        // Если заглушка уже показана - ничего не делаем
        if (emptyState.style.display === 'flex' && emptyState.style.opacity === '1') {
            return;
        }
        
        // Fade out через overlay
        if (overlay) overlay.classList.add('active');
        
        setTimeout(() => {
            if (content) content.style.display = 'none';
            emptyState.style.display = 'flex';
            emptyState.style.opacity = '0';
            
            // Fade in заглушки
            setTimeout(() => {
                emptyState.style.transition = `opacity ${CONFIG.fadeTime}ms ease`;
                emptyState.style.opacity = '1';
                if (overlay) overlay.classList.remove('active');
            }, 50);
        }, CONFIG.fadeTime);
    }

    /**
     * Скрыть заглушку с fade эффектом
     */
    function hideEmptyState() {
        const emptyState = document.querySelector('.empty-state');
        const content = document.querySelector('.display-content');
        
        if (!emptyState || emptyState.style.display === 'none') {
            if (content) content.style.display = 'block';
            return;
        }
        
        // Fade out заглушки
        emptyState.style.transition = `opacity ${CONFIG.fadeTime}ms ease`;
        emptyState.style.opacity = '0';
        
        setTimeout(() => {
            emptyState.style.display = 'none';
            if (content) content.style.display = 'block';
        }, CONFIG.fadeTime);
    }

    /**
     * Загрузка страницы в iframe с fade эффектом
     */
    function loadPage(url) {
        const iframe = document.getElementById('display-frame');
        const overlay = document.querySelector('.fade-overlay');
        
        if (!iframe || !overlay) return;
        
        console.log(`Loading page: ${url}`);
        
        // Fade out
        overlay.classList.add('active');
        
        setTimeout(() => {
            // Загружаем новую страницу
            iframe.src = url;
            
            iframe.onload = () => {
                // Fade in
                setTimeout(() => {
                    overlay.classList.remove('active');
                }, 100);
            };
        }, CONFIG.fadeTime);
    }

    /**
     * Очистка при закрытии
     */
    function cleanup() {
        if (checkTimer) {
            clearInterval(checkTimer);
            checkTimer = null;
        }
    }

    // Автопауза при скрытии вкладки
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            if (checkTimer) {
                clearInterval(checkTimer);
                checkTimer = null;
            }
        } else {
            checkState();
            checkTimer = setInterval(checkState, CONFIG.checkInterval);
        }
    });

    // Очистка при закрытии
    window.addEventListener('beforeunload', cleanup);

    // Запуск
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Экспорт для отладки
    window.DisplayCourt = { 
        checkState, 
        loadPage,
        showEmptyState,
        hideEmptyState
    };
})();