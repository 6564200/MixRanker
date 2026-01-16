/**
 * introduction.js - Масштабирование и обновление страницы представления матча
 * Базовое разрешение: FHD 1920x339
 */

(function() {
    'use strict';

    const BASE_WIDTH = 1920;
    const BASE_HEIGHT = 339;
    
    const container = document.querySelector('.intro-container');
    
    /**
     * Масштабирование контейнера под размер окна
     */
    function scaleToFit() {
        if (!container) return;
        
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        
        // Вычисляем масштаб по ширине (основной)
        const scaleX = windowWidth / BASE_WIDTH;
        
        // Вычисляем масштаб по высоте для проверки
        const scaleY = windowHeight / BASE_HEIGHT;
        
        // Используем меньший масштаб чтобы всё поместилось
        const scale = Math.min(scaleX, scaleY);
        
        container.style.transform = `scale(${scale})`;
        
        // Центрируем если есть свободное место
        const scaledWidth = BASE_WIDTH * scale;
        const scaledHeight = BASE_HEIGHT * scale;
        
        const offsetX = (windowWidth - scaledWidth) / 2;
        const offsetY = (windowHeight - scaledHeight) / 2;
        
        container.style.position = 'absolute';
        container.style.left = offsetX + 'px';
        container.style.top = offsetY + 'px';
    }
    
    /**
     * Обновление данных через AJAX (опционально)
     */
    function updateData() {
        const tournamentId = container?.dataset.tournamentId;
        const courtId = container?.dataset.courtId;
        
        if (!tournamentId || !courtId) return;
        
        fetch(`/api/court/${tournamentId}/${courtId}/introduction-data`)
            .then(response => response.json())
            .then(data => {
                if (data.error) return;
                
                // Обновляем поля с анимацией
                updateField('round_name', data.round_name);
                updateField('team1_name1', data.team1_name1);
                updateField('team1_name2', data.team1_name2);
                updateField('team2_name1', data.team2_name1);
                updateField('team2_name2', data.team2_name2);
                
                // Обновляем флаги
                updateFlag('team1_flag1', data.team1_flag1);
                updateFlag('team1_flag2', data.team1_flag2);
                updateFlag('team2_flag1', data.team2_flag1);
                updateFlag('team2_flag2', data.team2_flag2);
            })
            .catch(err => console.error('Update error:', err));
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
        
        // Обработчик изменения размера окна
        window.addEventListener('resize', scaleToFit);
        
        // Опционально: периодическое обновление данных
        // setInterval(updateData, 5000);
    }
    
    // Запуск при загрузке
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
