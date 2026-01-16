/**
 * intro_player.js - Масштабирование и обновление страницы представления игрока
 * Базовое разрешение: FHD 1920x400
 */

(function() {
    'use strict';

    const BASE_WIDTH = 1920;
    const BASE_HEIGHT = 400;
    
    const container = document.querySelector('.intro-player-container');
    
    /**
     * Масштабирование контейнера под размер окна
     */
    function scaleToFit() {
        if (!container) return;
        
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        
        // Вычисляем масштаб
        const scaleX = windowWidth / BASE_WIDTH;
        const scaleY = windowHeight / BASE_HEIGHT;
        
        // Используем меньший масштаб чтобы всё поместилось
        const scale = Math.min(scaleX, scaleY);
        
        container.style.transform = `scale(${scale})`;
        
        // Центрируем
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
    
    /**
     * Обновление флага
     */
    function updateFlag(fieldName, newUrl) {
        const element = document.querySelector(`[data-field="${fieldName}"]`);
        if (!element) return;
        
        const currentUrl = element.style.backgroundImage;
        const newBgUrl = `url('${newUrl}')`;
        
        if (currentUrl === newBgUrl) return;
        
        element.classList.add('updating');
        element.style.backgroundImage = newBgUrl;
        
        setTimeout(() => element.classList.remove('updating'), 300);
    }
    
    // Инициализация
    function init() {
        scaleToFit();
        window.addEventListener('resize', scaleToFit);
    }
    
    // Запуск при загрузке
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
