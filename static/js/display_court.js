/**
 * Display Court - логика автоматического/ручного режима
 */

(function() {
    'use strict';

    const CONFIG = {
        checkInterval: 1000,      
        fadeTime: 250             
    };

    let slotNumber = null;
    let tournamentId = null;
    let courtId = null;
    let mode = 'auto';
    let currentPage = null;
    let currentState = null;
    let currentBgType = null;
    let checkTimer = null;
    let loadRequestId = 0;

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
        applyPlaceholderImage(container.dataset.placeholderUrl);
        applyBackgroundType(container.dataset.backgroundType || 'image');

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
            applyPlaceholderImage(data.placeholder_url);

            // Обновляем тип фона если изменился
            if (data.background_type && data.background_type !== currentBgType) {
                currentBgType = data.background_type;
                applyBackgroundType(currentBgType);
                console.log(`Background type changed to: ${currentBgType}`);
            }

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
        
        // Получаем настройки окна для  tournament_id, court_id Рё custom_url
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
            
            // Стандартные страницы - требуются‚ tournament_id и court_id
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
            const window = await response.json();
            applyPlaceholderImage(window.placeholder_url);
            return window;
        } catch (error) {
            console.error('Failed to fetch window config:', error);
            return null;
        }
    }

    function buildMatrix(matrix, rows = 8, cols = 18) {
        if (matrix.children.length) return; // уже построена
        const fragment = document.createDocumentFragment();
        for (let r = 0; r < rows; r++) {
            const row = document.createElement('div');
            row.className = 'bg-matrix-row';
            for (let c = 1; c <= cols; c++) {
                const rect = document.createElement('div');
                rect.className = 'bg-matrix-rect';
                rect.style.setProperty('--i', c);
                row.appendChild(rect);
            }
            fragment.appendChild(row);
        }
        matrix.appendChild(fragment);
    }

    function applyBackgroundType(type) {
        const matrix = document.querySelector('.bg-matrix');
        const bgImage = document.querySelector('.bg-image');
        if (!matrix) return;
        if (type === 'matrix') {
            buildMatrix(matrix);
            matrix.classList.add('active');
            if (bgImage) bgImage.style.display = 'none';
            document.documentElement.style.background = '';
            document.body.style.background = '';
        } else if (type === 'transparent') {
            matrix.classList.remove('active');
            if (bgImage) bgImage.style.display = 'none';
            document.documentElement.style.background = 'transparent';
            document.body.style.background = 'transparent';
        } else {
            matrix.classList.remove('active');
            if (bgImage) bgImage.style.display = '';
            document.documentElement.style.background = '';
            document.body.style.background = '';
        }
    }

    function applyPlaceholderImage(url) {
        if (!url) return;
        const emptyImage = document.querySelector('.empty-state .empty-image');
        if (emptyImage && emptyImage.getAttribute('src') !== url) {
            emptyImage.setAttribute('src', url);
        }
    }

    function setPlaceholderVisible(visible) {
        const emptyState = document.querySelector('.empty-state');
        if (!emptyState) return;

        if (visible) {
            emptyState.style.display = 'flex';
            void emptyState.offsetHeight;
            emptyState.style.opacity = '1';
            return;
        }

        emptyState.style.opacity = '0';
        setTimeout(() => {
            if (emptyState.style.opacity === '0') {
                emptyState.style.display = 'none';
            }
        }, CONFIG.fadeTime);
    }

    /**
     * Показать заглушку с fade эффектом
     */
    function showEmptyState() {
        const emptyState = document.querySelector('.empty-state');
        const content = document.querySelector('.display-content');
        
        if (!emptyState) return;
        
        // Если заглушка уже показана - ничего не делаем
        if (emptyState.style.display === 'flex' && emptyState.style.opacity === '1') {
            return;
        }

        if (content) content.style.display = 'none';
        setPlaceholderVisible(true);
    }

    /**
     * Скрыть заглушку с fade эффектом
     */
    function hideEmptyState() {
        const emptyState = document.querySelector('.empty-state');
        const content = document.querySelector('.display-content');
        
        if (!emptyState || emptyState.style.display === 'none') {
            if (content) {
                content.style.display = 'block';
                content.style.opacity = '1';
            }
            return;
        }
        
        setPlaceholderVisible(false);
        if (content) {
            content.style.display = 'block';
            content.style.opacity = '1';
        }
    }

    /**
     * Загрузка страницы в iframe с fade эффектом
     */
    function loadPage(url) {
        const iframe = document.getElementById('display-frame');
        const content = document.querySelector('.display-content');
        
        if (!iframe) return;
        
        console.log(`Loading page: ${url}`);

        if (content) {
            content.style.display = 'block';
            content.style.opacity = '0';
        }

        const requestId = ++loadRequestId;

        setTimeout(() => {
            if (requestId !== loadRequestId) return;
            iframe.src = url;
        }, CONFIG.fadeTime);

        iframe.onload = () => {
            if (requestId !== loadRequestId) return;
            setTimeout(() => {
                if (content) {
                    content.style.opacity = '1';
                }
            }, 50);
        };
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

