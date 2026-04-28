/**
 * Photo Upload Form Integration for MixRanker
 * Country Autocomplete integration + form validation
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        // Инициализируем один раз после загрузки DOM
        window.countryAutocomplete = new CountryAutocomplete('country', {
            enableFlags: true,
            placeholder: 'Введите или выберите страну...',
            noResultsText: 'Страна не найдена в справочнике',
            maxResults: 8,
            allowFreeText: false
        });

        // Обновляем кнопку при выборе из списка и при вводе текста
        document.getElementById('country').addEventListener('countrySelected', _updateSaveButton);
        document.getElementById('country').addEventListener('input', _updateSaveButton);
    });

    /**
     * Обновляет состояние кнопки «Сохранить»:
     * блокирует, если в поле текст, которого нет в справочнике.
     */
    function _updateSaveButton() {
        const saveButton = document.getElementById('uploadPhotoButton');
        if (!saveButton) return;

        const countryField = document.getElementById('country');
        const hasText = countryField.value.trim().length > 0;
        const isValid = !hasText || (window.countryAutocomplete && window.countryAutocomplete.isValidSelection());

        saveButton.disabled = !isValid;
        saveButton.title = (!isValid && hasText) ? 'Выберите страну из списка для сохранения' : '';
    }

    // Публичный API для main.js
    window.countryFormIntegration = {
        updateSaveButton: _updateSaveButton
    };
})();
