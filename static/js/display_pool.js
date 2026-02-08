/**
 * Display Pool - логика ротации страниц
 */

(function() {
    'use strict';

    const CONFIG = {
        checkInterval: 5000,      // Проверка настроек каждые 5 сек
        fadeTime: 500,            // Время fade эффекта (мс)
        defaultDuration: 30       // Длительность по умолчанию (сек)
    };

    let slotNumber = null;
    let currentSettings = null;
    let currentIndex = 0;
    let rotationTimer = null;
    let checkTimer = null;
    let mode = 'auto';

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
        mode = container.dataset.mode || 'auto';

        console.log(`Display Pool ${slotNumber}: initialized, mode=${mode}`);

        // Загружаем настройки и запускаем
        loadSettings();
        
        // Периодическая проверка настроек
        checkTimer = setInterval(loadSettings, CONFIG.checkInterval);
    }

    /**
     * Загрузка настроек окна
     */
    async function loadSettings() {
        try {
            const response = await fetch(`/api/display/window/pool/${slotNumber}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const window = await response.json();
            
            // Проверяем изменился ли режим
            if (window.mode !== mode) {
                mode = window.mode;
                console.log(`Mode changed to: ${mode}`);
            }
            
            // В ручном режиме показываем выбранную страницу
            if (mode === 'manual' && window.manual_page) {
                showManualPage(window);
                return;
            }
            
            // Проверяем изменились ли настройки ротации
            const newSettings = window.settings || { items: [] };
            const settingsChanged = JSON.stringify(newSettings) !== JSON.stringify(currentSettings);
            
            if (settingsChanged) {
                console.log('Settings changed, restarting rotation');
                currentSettings = newSettings;
                currentIndex = newSettings.current_index || 0;
                startRotation();
            }
            
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    /**
     * Показ страницы в ручном режиме
     */
    function showManualPage(windowData) {
        stopRotation();
        
        const manualPage = windowData.manual_page;
        const items = windowData.settings?.items || [];
        
        // Заглушка
        if (manualPage === 'empty') {
            showEmptyState();
            return;
        }
        
        hideEmptyState();
        
        // Произвольный URL
        if (manualPage === 'custom') {
            const customUrl = windowData.settings?.custom_url;
            if (customUrl) {
                loadPage(customUrl);
            } else {
                console.log('No custom URL configured');
                showEmptyState();
            }
            return;
        }
        
        // Страница из плейлиста (item_0, item_1, ...)
        if (manualPage && manualPage.startsWith('item_')) {
            const index = parseInt(manualPage.split('_')[1]);
            if (items[index] && items[index].url) {
                loadPage(items[index].url);
            } else {
                console.log(`Item ${index} not found in playlist`);
                showEmptyState();
            }
            return;
        }
        
        console.log('Unknown manual page:', manualPage);
        showEmptyState();
    }

    /**
     * Показать заглушку с fade эффектом
     */
    function showEmptyState() {
        const emptyState = document.querySelector('.empty-state');
        const content = document.querySelector('.display-content');
        const overlay = document.querySelector('.fade-overlay');
        
        if (!emptyState) return;
        
        if (emptyState.style.display === 'flex' && emptyState.style.opacity === '1') {
            return;
        }
        
        if (overlay) overlay.classList.add('active');
        
        setTimeout(() => {
            if (content) content.style.display = 'none';
            emptyState.style.display = 'flex';
            emptyState.style.opacity = '0';
            
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
        
        emptyState.style.transition = `opacity ${CONFIG.fadeTime}ms ease`;
        emptyState.style.opacity = '0';
        
        setTimeout(() => {
            emptyState.style.display = 'none';
            if (content) content.style.display = 'block';
        }, CONFIG.fadeTime);
    }

    /**
     * Запуск ротации
     */
    function startRotation() {
        stopRotation();
        
        if (!currentSettings || !currentSettings.items || currentSettings.items.length === 0) {
            console.log('No items for rotation');
            return;
        }
        
        // Показываем текущую страницу
        showCurrentPage();
    }

    /**
     * Остановка ротации
     */
    function stopRotation() {
        if (rotationTimer) {
            clearTimeout(rotationTimer);
            rotationTimer = null;
        }
    }

    /**
     * Показ текущей страницы из списка ротации
     */
    function showCurrentPage() {
        if (!currentSettings || !currentSettings.items || currentSettings.items.length === 0) {
            return;
        }
        
        const items = currentSettings.items;
        const item = items[currentIndex % items.length];
        
        console.log(`Showing page ${currentIndex + 1}/${items.length}: ${item.url}`);
        
        loadPage(item.url, () => {
            // После загрузки планируем переход на следующую
            const duration = (item.duration || CONFIG.defaultDuration) * 1000;
            
            rotationTimer = setTimeout(() => {
                currentIndex = (currentIndex + 1) % items.length;
                showCurrentPage();
            }, duration);
        });
    }

    /**
     * Загрузка страницы в iframe с fade эффектом
     */
    function loadPage(url, callback) {
        const iframe = document.getElementById('display-frame');
        const overlay = document.querySelector('.fade-overlay');
        
        if (!iframe || !overlay) return;
        
        // Fade out
        overlay.classList.add('active');
        
        setTimeout(() => {
            // Загружаем новую страницу
            iframe.src = url;
            
            iframe.onload = () => {
                // Fade in
                setTimeout(() => {
                    overlay.classList.remove('active');
                    if (callback) callback();
                }, 100);
            };
        }, CONFIG.fadeTime);
    }

    /**
     * Очистка при закрытии
     */
    function cleanup() {
        stopRotation();
        if (checkTimer) {
            clearInterval(checkTimer);
            checkTimer = null;
        }
    }

    // Автопауза при скрытии вкладки
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopRotation();
        } else if (mode === 'auto') {
            startRotation();
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
    window.DisplayPool = { 
        loadSettings, 
        startRotation, 
        stopRotation,
        loadPage 
    };
})();
