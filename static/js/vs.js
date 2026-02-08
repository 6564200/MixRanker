/**
 * vs.js - Масштабирование и обновление VS страницы
 * Базовое разрешение: FHD 1920x1080
 */

(function() {
    'use strict';

    const BASE_WIDTH = 1920;
    const BASE_HEIGHT = 1080;
    
    const container = document.querySelector('.vs-container');
    
    /**
     * Масштабирование контейнера под размер окна с центрированием
     */
    function scaleToFit() {
        if (!container) return;
        
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        
        // Вычисляем масштаб с сохранением пропорций 16:9
        const scaleX = windowWidth / BASE_WIDTH;
        const scaleY = windowHeight / BASE_HEIGHT;
        const scale = Math.min(scaleX, scaleY);
        
        // Устанавливаем фиксированные размеры
        container.style.width = BASE_WIDTH + 'px';
        container.style.height = BASE_HEIGHT + 'px';
        
        // Центрируем через transform-origin и позиционирование
        container.style.position = 'absolute';
        container.style.left = '50%';
        container.style.top = '50%';
        container.style.transformOrigin = 'center center';
        container.style.transform = `translate(-50%, -50%) scale(${scale})`;
    }
    
    /**
     * Обновление данных через AJAX
     */
    function updateData() {
        const tournamentId = container?.dataset.tournamentId;
        const courtId = container?.dataset.courtId;
        
        if (!tournamentId || !courtId) return;
        
        fetch(`/api/court/${tournamentId}/${courtId}/vs-data`)
            .then(response => response.json())
            .then(data => {
                if (data.error) return;
                
                // Обновляем счета
                updateField('set1_score1', data.set1_score1);
                updateField('set1_score2', data.set1_score2);
                updateField('set2_score1', data.set2_score1);
                updateField('set2_score2', data.set2_score2);
                updateField('set3_score1', data.set3_score1);
                updateField('set3_score2', data.set3_score2);
                updateField('game_score1', data.game_score1);
                updateField('game_score2', data.game_score2);
                
                // Обновляем имена
                updateField('team1_player1', data.team1_player1);
                updateField('team1_player2', data.team1_player2);
                updateField('team2_player1', data.team2_player1);
                updateField('team2_player2', data.team2_player2);
            })
            .catch(err => console.error('Update error:', err));
    }
    
    /**
     * Обновление текстового поля
     */
    function updateField(fieldName, newValue) {
        const element = document.querySelector(`[data-field="${fieldName}"]`);
        if (!element) return;
        
        const currentValue = element.textContent;
        if (currentValue === String(newValue)) return;
        
        element.classList.add('updating');
        element.textContent = newValue ?? '';
        
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