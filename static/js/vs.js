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
     * Масштабирование контейнера под размер окна
     */
    function scaleToFit() {
        if (!container) return;
        
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        
        // Вычисляем масштаб
        const scaleX = windowWidth / BASE_WIDTH;
        const scaleY = windowHeight / BASE_HEIGHT;
        
        // Используем меньший масштаб чтобы сохранить пропорции 16:9
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
        
        // Опционально: периодическое обновление
        // const updateInterval = container?.dataset.updateInterval || 2000;
        // setInterval(updateData, updateInterval);
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
