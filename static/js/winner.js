/**
 * winner.js - Масштабирование страницы победителя
 * Базовое разрешение: FHD 1920x1080
 */

(function() {
    'use strict';

    const BASE_WIDTH = 1920;
    const BASE_HEIGHT = 1080;
    
    const container = document.querySelector('.winner');
    
    /**
     * Масштабирование контейнера под размер окна
     */
    function scaleToFit() {
        if (!container) return;
        
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        
        const scaleX = windowWidth / BASE_WIDTH;
        const scaleY = windowHeight / BASE_HEIGHT;
        const scale = Math.min(scaleX, scaleY);
        
        container.style.transform = `scale(${scale})`;
        
        const scaledWidth = BASE_WIDTH * scale;
        const scaledHeight = BASE_HEIGHT * scale;
        
        const offsetX = (windowWidth - scaledWidth) / 2;
        const offsetY = (windowHeight - scaledHeight) / 2;
        
        container.style.position = 'absolute';
        container.style.left = offsetX + 'px';
        container.style.top = offsetY + 'px';
    }
    
    /**
     * Обновление текстового поля
     */
    function updateField(fieldName, newValue) {
        const element = document.querySelector(`[data-field="${fieldName}"]`);
        if (!element || element.textContent === newValue) return;
        
        element.classList.add('updating');
        element.textContent = newValue || '';
        
        setTimeout(() => element.classList.remove('updating'), 300);
    }
    
    // Инициализация
    function init() {
        scaleToFit();
        window.addEventListener('resize', scaleToFit);
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
