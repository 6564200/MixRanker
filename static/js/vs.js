/**
 * vs.js - Масштабирование и обновление VS страницы
 * Базовое разрешение: FHD 1920x1080
 */

(function() {
    'use strict';

    const BASE_WIDTH  = 1920;
    const BASE_HEIGHT = 1080;
    const POLL_INTERVAL = 3000;
    const SILHOUETTE = '/static/images/silhouette.png';

    const container = document.querySelector('.vs-container');

    /**
     * Масштабирование контейнера под размер окна с центрированием
     */
    function scaleToFit() {
        if (!container) return;
        const scaleX = window.innerWidth  / BASE_WIDTH;
        const scaleY = window.innerHeight / BASE_HEIGHT;
        const scale  = Math.min(scaleX, scaleY);
        container.style.width  = BASE_WIDTH  + 'px';
        container.style.height = BASE_HEIGHT + 'px';
        container.style.position      = 'absolute';
        container.style.left          = '50%';
        container.style.top           = '50%';
        container.style.transformOrigin = 'center center';
        container.style.transform     = `translate(-50%, -50%) scale(${scale})`;
    }

    /**
     * Обновление текстового поля по data-field
     */
    function updateField(fieldName, newValue) {
        const el = document.querySelector(`[data-field="${fieldName}"]`);
        if (!el) return;
        const val = newValue ?? '';
        if (el.textContent === String(val)) return;
        el.classList.add('updating');
        el.textContent = val;
        setTimeout(() => el.classList.remove('updating'), 300);
    }

    /**
     * Обновление src фото-элемента по data-field.
     * Сравниваем через getAttribute('src'), а не el.src —
     * el.src возвращает абсолютный URL, а API отдаёт относительный.
     */
    function updatePhoto(fieldName, newUrl) {
        const el = document.querySelector(`[data-field="${fieldName}"]`);
        if (!el) return;
        const url = newUrl || SILHOUETTE;
        if (el.getAttribute('src') === url) return;
        el.src = url;
        if (newUrl) {
            el.classList.remove('silhouette');
        } else {
            el.classList.add('silhouette');
        }
    }

    /**
     * Показ/скрытие блока сета в зависимости от наличия счёта
     */
    function updateSetVisibility(setNum, score1, score2) {
        const block = document.querySelector(`.set-block[data-set="${setNum}"]`);
        if (!block) return;
        const hasScore = (score1 !== '' && score1 !== null && score1 !== undefined)
                      || (score2 !== '' && score2 !== null && score2 !== undefined);
        block.classList.toggle('hidden', !hasScore);
    }

    /**
     * Обновление всех данных через AJAX
     */
    function updateData() {
        const tournamentId = container?.dataset.tournamentId;
        const courtId      = container?.dataset.courtId;
        if (!tournamentId || !courtId) return Promise.resolve();

        return fetch(`/api/court/${tournamentId}/${courtId}/vs-data`)
            .then(r => r.json())
            .then(data => {
                if (data.error) return;

                // Имена
                updateField('team1_player1', data.team1_player1);
                updateField('team1_player2', data.team1_player2);
                updateField('team2_player1', data.team2_player1);
                updateField('team2_player2', data.team2_player2);

                // Фото
                updatePhoto('team1_photo1', data.team1_photo1);
                updatePhoto('team1_photo2', data.team1_photo2);
                updatePhoto('team2_photo1', data.team2_photo1);
                updatePhoto('team2_photo2', data.team2_photo2);

                // Счета сетов
                updateField('set1_score1', data.set1_score1);
                updateField('set1_score2', data.set1_score2);
                updateField('set2_score1', data.set2_score1);
                updateField('set2_score2', data.set2_score2);
                updateField('set3_score1', data.set3_score1);
                updateField('set3_score2', data.set3_score2);

                // Видимость блоков сетов
                updateSetVisibility(1, data.set1_score1, data.set1_score2);
                updateSetVisibility(2, data.set2_score1, data.set2_score2);
                updateSetVisibility(3, data.set3_score1, data.set3_score2);
            })
            .catch(err => console.error('VS update error:', err));
    }

    function init() {
        scaleToFit();
        window.addEventListener('resize', scaleToFit);
        if (container?.dataset.tournamentId && container?.dataset.courtId) {
            updateData();
            setInterval(updateData, POLL_INTERVAL);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
