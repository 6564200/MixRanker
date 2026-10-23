/**
 * Выбор дизайна эфирной графики в настройках панели (применяется по кнопке «Сохранить настройки»).
 * Список берётся с сервера (/api/design): папки из static/themes.
 */
(function () {
    const select = document.getElementById('designSelect');
    if (!select) return;

    let current = 'old';

    function notify(message, type) {
        if (typeof showAlert === 'function') showAlert(message, type);
        else console.log(message);
    }

    async function load() {
        try {
            const response = await fetch('/api/design');
            if (!response.ok) return;
            const data = await response.json();
            current = data.active || 'old';
            select.innerHTML = '';
            const titles = data.titles || {};
            (data.available || ['old']).forEach(function (name, index) {
                const option = document.createElement('option');
                option.value = name;
                option.textContent = (index + 1) + '. ' + (titles[name] || name);
                select.appendChild(option);
            });
            select.value = current;
            select.disabled = false;
        } catch (e) {
            console.error('design: не удалось загрузить список', e);
        }
    }

    // Дизайн применяется только по кнопке «Сохранить настройки»:
    // дополняем штатное сохранение настроек отправкой выбранного дизайна.
    async function saveDesign() {
        const wanted = select.value;
        if (select.disabled || wanted === current) return;
        try {
            const response = await fetch('/api/design', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ design: wanted })
            });
            if (response.status === 401) return; // авторизация запрашивается основным сохранением
            const data = await response.json();
            if (!response.ok || !data.success) {
                select.value = current;
                notify(data.error || 'Не удалось переключить дизайн', 'danger');
                return;
            }
            current = data.active;
            notify('Дизайн «' + select.options[select.selectedIndex].textContent + '» включён. В vMix обновите Browser Source.', 'success');
        } catch (e) {
            select.value = current;
            notify('Ошибка связи с сервером', 'danger');
        }
    }

    if (typeof window.saveSettingsWithAuth === 'function') {
        const originalSave = window.saveSettingsWithAuth;
        window.saveSettingsWithAuth = async function () {
            await originalSave.apply(this, arguments);
            await saveDesign();
        };
    }

    load();
})();
