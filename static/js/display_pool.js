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
    let currentManualPage = null;
    let currentLoadedUrl = null;  // Текущий загруженный URL

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
            
            const windowData = await response.json();
            
            // Проверяем изменился ли режим
            if (windowData.mode !== mode) {
                mode = windowData.mode;
                console.log(`Mode changed to: ${mode}`);
                currentManualPage = null;
                currentLoadedUrl = null;  // Сбрасываем при смене режима
            }
            
            // В ручном режиме показываем выбранную страницу
            if (mode === 'manual') {
                handleManualMode(windowData);
                return;
            }
            
            // В авто режиме - ротация
            currentManualPage = null;
            
            // Проверяем изменились ли настройки ротации
            const newSettings = windowData.settings || { items: [] };
            const settingsChanged = JSON.stringify(newSettings) !== JSON.stringify(currentSettings);
            
            if (settingsChanged) {
                console.log('Settings changed, restarting rotation');
                currentSettings = newSettings;
                currentIndex = newSettings.current_index || 0;
                currentLoadedUrl = null;  // Сбрасываем при изменении настроек
                startRotation();
            }
            
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    /**
     * Обработка ручного режима
     */
    function handleManualMode(windowData) {
        stopRotation();
        
        const manualPage = windowData.manual_page;
        const items = windowData.settings?.items || [];
        
        // Проверяем изменилась ли страница
        if (manualPage === currentManualPage) {
            // Страница не изменилась, ничего не делаем
            return;
        }
        
        currentManualPage = manualPage;
        console.log(`Manual page changed to: ${currentManualPage}`);
        
        // Заглушка
        if (manualPage === 'empty' || !manualPage) {
            currentLoadedUrl = null;
            showEmptyState();
            return;
        }
        
        hideEmptyState();
        
        // Определяем URL для загрузки
        let targetUrl = null;
        
        // Произвольный URL
        if (manualPage === 'custom') {
            targetUrl = windowData.settings?.custom_url;
        }
        // Страница из плейлиста (item_0, item_1, ...)
        else if (manualPage.startsWith('item_')) {
            const index = parseInt(manualPage.split('_')[1]);
            if (items[index] && items[index].url) {
                targetUrl = items[index].url;
            }
        }
        
        if (targetUrl) {
            // Проверяем, не загружен ли уже этот URL
            if (targetUrl !== currentLoadedUrl) {
                loadPage(targetUrl);
                currentLoadedUrl = targetUrl;
            }
        } else {
            console.log('No valid URL for manual page:', manualPage);
            currentLoadedUrl = null;
            showEmptyState();
        }
    }

    /**
     * Показать заглушку с fade эффектом
     */
    function showEmptyState() {
        const emptyState = document.querySelector('.empty-state');
        const content = document.querySelector('.display-content');
        const overlay = document.querySelector('.fade-overlay');
        
        if (!emptyState) {
            console.error('Empty state element not found');
            return;
        }
        
        // Уже показана заглушка
        if (emptyState.style.display === 'flex' && emptyState.style.opacity === '1') {
            return;
        }
        
        console.log('Showing empty state');
        
        // Fade out через overlay
        if (overlay) overlay.classList.add('active');
        
        setTimeout(() => {
            if (content) content.style.display = 'none';
            emptyState.style.display = 'flex';
            emptyState.style.opacity = '0';
            
            // Форсируем reflow
            emptyState.offsetHeight;
            
            // Fade in заглушки
            emptyState.style.transition = `opacity ${CONFIG.fadeTime}ms ease`;
            emptyState.style.opacity = '1';
            
            setTimeout(() => {
                if (overlay) overlay.classList.remove('active');
            }, CONFIG.fadeTime);
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
            showEmptyState();
            return;
        }
        
        // Если только одна страница - загружаем без ротации
        if (currentSettings.items.length === 1) {
            const item = currentSettings.items[0];
            if (item.url !== currentLoadedUrl) {
                hideEmptyState();
                loadPage(item.url);
                currentLoadedUrl = item.url;
            }
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
        
        hideEmptyState();
        
        loadPage(item.url, () => {
            currentLoadedUrl = item.url;
            
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
        
        if (!iframe) return;
        
        // Если URL не изменился, не перезагружаем
        if (iframe.src === url || iframe.src === window.location.origin + url) {
            console.log('URL unchanged, skipping reload');
            if (callback) callback();
            return;
        }
        
        console.log('Loading page:', url);
        
        // Fade out
        if (overlay) overlay.classList.add('active');
        
        setTimeout(() => {
            // Загружаем новую страницу
            iframe.src = url;
            
            iframe.onload = () => {
                // Fade in
                setTimeout(() => {
                    if (overlay) overlay.classList.remove('active');
                    if (callback) callback();
                }, 100);
            };
            
            // Fallback если onload не сработает
            setTimeout(() => {
                if (overlay) overlay.classList.remove('active');
            }, 3000);
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
        } else if (mode === 'auto' && currentSettings?.items?.length > 1) {
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
        loadPage,
        getState: () => ({ mode, currentManualPage, currentLoadedUrl, currentIndex })
    };
})();