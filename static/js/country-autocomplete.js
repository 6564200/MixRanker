/**
 * Country Autocomplete Module for MixRanker v2.6
 * Автоматизация и валидация выбора страны с флагами
 */

class CountryAutocomplete {
    constructor(inputElementId, options = {}) {
        this.inputElement = document.getElementById(inputElementId);
        this.options = {
            enableFlags: true,
            placeholder: 'Введите страну...',
            noResultsText: 'Страна не найдена',
            maxResults: 8,
            allowFreeText: false, // Запрещает произвольный текст
            ...options
        };
        
        this.countries = this.getCountriesData();
        this.selectedCountry = null;
        this.isValid = false;
        this.dropdown = null;
        this.flagElement = null;
        
        this.init();
    }

    /**
     * ISO 3166-1 alpha-3 codes для стран с поддержкой флагов
     */
    getCountriesData() {
        return [
            { name: 'Россия', name_en: 'Russia', code: 'RUS', iso2: 'RU' },
            { name: 'США', name_en: 'United States', code: 'USA', iso2: 'US' },
            { name: 'Германия', name_en: 'Germany', code: 'GER', iso2: 'DE' },
            { name: 'Франция', name_en: 'France', code: 'FRA', iso2: 'FR' },
            { name: 'Испания', name_en: 'Spain', code: 'ESP', iso2: 'ES' },
            { name: 'Италия', name_en: 'Italy', code: 'ITA', iso2: 'IT' },
            { name: 'Великобритания', name_en: 'United Kingdom', code: 'GBR', iso2: 'GB' },
            { name: 'Португалия', name_en: 'Portugal', code: 'POR', iso2: 'PT' },
            { name: 'Нидерланды', name_en: 'Netherlands', code: 'NED', iso2: 'NL' },
            { name: 'Бельгия', name_en: 'Belgium', code: 'BEL', iso2: 'BE' },
            { name: 'Швейцария', name_en: 'Switzerland', code: 'SUI', iso2: 'CH' },
            { name: 'Австрия', name_en: 'Austria', code: 'AUT', iso2: 'AT' },
            { name: 'Швеция', name_en: 'Sweden', code: 'SWE', iso2: 'SE' },
            { name: 'Норвегия', name_en: 'Norway', code: 'NOR', iso2: 'NO' },
            { name: 'Дания', name_en: 'Denmark', code: 'DEN', iso2: 'DK' },
            { name: 'Финляндия', name_en: 'Finland', code: 'FIN', iso2: 'FI' },
            { name: 'Польша', name_en: 'Poland', code: 'POL', iso2: 'PL' },
            { name: 'Чехия', name_en: 'Czech Republic', code: 'CZE', iso2: 'CZ' },
            { name: 'Словакия', name_en: 'Slovakia', code: 'SVK', iso2: 'SK' },
            { name: 'Хорватия', name_en: 'Croatia', code: 'CRO', iso2: 'HR' },
            { name: 'Сербия', name_en: 'Serbia', code: 'SRB', iso2: 'RS' },
            { name: 'Австралия', name_en: 'Australia', code: 'AUS', iso2: 'AU' },
            { name: 'Новая Зеландия', name_en: 'New Zealand', code: 'NZL', iso2: 'NZ' },
            { name: 'Канада', name_en: 'Canada', code: 'CAN', iso2: 'CA' },
            { name: 'Мексика', name_en: 'Mexico', code: 'MEX', iso2: 'MX' },
            { name: 'Бразилия', name_en: 'Brazil', code: 'BRA', iso2: 'BR' },
            { name: 'Аргентина', name_en: 'Argentina', code: 'ARG', iso2: 'AR' },
            { name: 'Чили', name_en: 'Chile', code: 'CHI', iso2: 'CL' },
            { name: 'Уругвай', name_en: 'Uruguay', code: 'URU', iso2: 'UY' },
            { name: 'Колумбия', name_en: 'Colombia', code: 'COL', iso2: 'CO' },
            { name: 'Япония', name_en: 'Japan', code: 'JPN', iso2: 'JP' },
            { name: 'Южная Корея', name_en: 'South Korea', code: 'KOR', iso2: 'KR' },
            { name: 'Китай', name_en: 'China', code: 'CHN', iso2: 'CN' },
            { name: 'Индия', name_en: 'India', code: 'IND', iso2: 'IN' },
            { name: 'Израиль', name_en: 'Israel', code: 'ISR', iso2: 'IL' },
            { name: 'ОАЭ', name_en: 'United Arab Emirates', code: 'UAE', iso2: 'AE' },
            { name: 'Катар', name_en: 'Qatar', code: 'QAT', iso2: 'QA' },
            { name: 'Кувейт', name_en: 'Kuwait', code: 'KUW', iso2: 'KW' },
            { name: 'Саудовская Аравия', name_en: 'Saudi Arabia', code: 'KSA', iso2: 'SA' },
            { name: 'Турция', name_en: 'Turkey', code: 'TUR', iso2: 'TR' },
            { name: 'Египет', name_en: 'Egypt', code: 'EGY', iso2: 'EG' },
            { name: 'Марокко', name_en: 'Morocco', code: 'MAR', iso2: 'MA' },
            { name: 'Тунис', name_en: 'Tunisia', code: 'TUN', iso2: 'TN' },
            { name: 'ЮАР', name_en: 'South Africa', code: 'RSA', iso2: 'ZA' },
            { name: 'Беларусь', name_en: 'Belarus', code: 'BLR', iso2: 'BY' },
            { name: 'Украина', name_en: 'Ukraine', code: 'UKR', iso2: 'UA' },
            { name: 'Казахстан', name_en: 'Kazakhstan', code: 'KAZ', iso2: 'KZ' },
            { name: 'Узбекистан', name_en: 'Uzbekistan', code: 'UZB', iso2: 'UZ' },
            { name: 'Армения', name_en: 'Armenia', code: 'ARM', iso2: 'AM' },
            { name: 'Грузия', name_en: 'Georgia', code: 'GEO', iso2: 'GE' },
            { name: 'Азербайджан', name_en: 'Azerbaijan', code: 'AZE', iso2: 'AZ' }
        ].sort((a, b) => a.name.localeCompare(b.name));
    }

    init() {
        if (!this.inputElement) {
            console.error('Country autocomplete: Input element not found');
            return;
        }

        this.createStructure();
        this.bindEvents();
        this.initializePriorityFromRankedin();
    }

    createStructure() {
        // Создаем контейнер для автокомплита
        const container = document.createElement('div');
        container.className = 'country-autocomplete-container position-relative';
        
        // Обворачиваем существующий input
        this.inputElement.parentNode.insertBefore(container, this.inputElement);
        container.appendChild(this.inputElement);

        // Настраиваем input
        this.inputElement.className = 'form-control form-control-sm';
        this.inputElement.setAttribute('autocomplete', 'off');
        this.inputElement.placeholder = this.options.placeholder;

        // Создаем элемент флага
        if (this.options.enableFlags) {
            this.createFlagElement(container);
        }

        // Создаем dropdown
        this.createDropdown(container);

        // Добавляем стили
        this.addStyles();
    }

    createFlagElement(container) {
        const flagWrapper = document.createElement('div');
        flagWrapper.className = 'country-flag-wrapper';
        
        this.flagElement = document.createElement('img');
        this.flagElement.className = 'country-flag';
        this.flagElement.style.display = 'none';
        
        flagWrapper.appendChild(this.flagElement);
        container.appendChild(flagWrapper);
    }

    createDropdown(container) {
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'country-dropdown';
        this.dropdown.style.display = 'none';
        container.appendChild(this.dropdown);
    }

    addStyles() {
        if (document.getElementById('country-autocomplete-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'country-autocomplete-styles';
        styles.textContent = `
            .country-autocomplete-container {
                position: relative;
            }
            
            .country-autocomplete-container input.invalid {
                border-color: #dc3545;
                box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25);
            }
            
            .country-autocomplete-container input.valid {
                border-color: #198754;
                box-shadow: 0 0 0 0.2rem rgba(25, 135, 84, 0.25);
            }
            
            .country-flag-wrapper {
                position: absolute;
                right: 8px;
                top: 50%;
                transform: translateY(-50%);
                z-index: 10;
                pointer-events: none;
            }
            
            .country-flag {
                width: 20px;
                height: 15px;
                border: 1px solid #ddd;
                border-radius: 2px;
                object-fit: cover;
            }
            
            .country-dropdown {
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: white;
                border: 1px solid #ced4da;
                border-top: none;
                border-radius: 0 0 4px 4px;
                max-height: 200px;
                overflow-y: auto;
                z-index: 1000;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .country-dropdown-item {
                padding: 8px 12px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                border-bottom: 1px solid #f8f9fa;
            }
            
            .country-dropdown-item:hover,
            .country-dropdown-item.highlighted {
                background-color: #f8f9fa;
            }
            
            .country-dropdown-item.selected {
                background-color: #e3f2fd;
            }
            
            .country-dropdown-item .flag {
                width: 16px;
                height: 12px;
                border: 1px solid #ddd;
                border-radius: 1px;
                object-fit: cover;
            }
            
            .country-dropdown-item .name {
                flex: 1;
            }
            
            .country-dropdown-item .code {
                font-size: 11px;
                color: #6c757d;
                font-weight: 500;
            }
            
            .country-dropdown .no-results {
                padding: 12px;
                text-align: center;
                color: #6c757d;
                font-style: italic;
            }
            
            [data-theme="dark"] .country-dropdown {
                background: #2d3748;
                border-color: #4a5568;
            }
            
            [data-theme="dark"] .country-dropdown-item {
                border-bottom-color: #4a5568;
                color: #e2e8f0;
            }
            
            [data-theme="dark"] .country-dropdown-item:hover,
            [data-theme="dark"] .country-dropdown-item.highlighted {
                background-color: #4a5568;
            }
            
            [data-theme="dark"] .country-dropdown-item.selected {
                background-color: #2b6cb0;
            }
        `;
        document.head.appendChild(styles);
    }

    bindEvents() {
        // Поиск при вводе
        this.inputElement.addEventListener('input', (e) => {
            this.handleInput(e.target.value);
        });

        // Фокус - показать dropdown
        this.inputElement.addEventListener('focus', () => {
            this.showDropdown();
        });

        // Клавиатурная навигация
        this.inputElement.addEventListener('keydown', (e) => {
            this.handleKeyDown(e);
        });

        // Закрытие по клику вне области
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.country-autocomplete-container')) {
                this.hideDropdown();
            }
        });

        // Валидация при потере фокуса
        this.inputElement.addEventListener('blur', () => {
            setTimeout(() => this.validateInput(), 200);
        });
    }

    handleInput(value) {
        this.updateValidation(false);
        
        if (value.length === 0) {
            this.showAllCountries();
            return;
        }

        const filtered = this.filterCountries(value);
        this.renderDropdown(filtered);
    }

    filterCountries(query) {
        const lowerQuery = query.toLowerCase();
        
        return this.countries.filter(country => 
            country.name.toLowerCase().includes(lowerQuery) ||
            country.name_en.toLowerCase().includes(lowerQuery) ||
            country.code.toLowerCase().includes(lowerQuery)
        );
    }

    showAllCountries() {
        this.renderDropdown(this.countries.slice(0, this.options.maxResults));
    }

    renderDropdown(countries) {
        if (countries.length === 0) {
            this.dropdown.innerHTML = `
                <div class="no-results">${this.options.noResultsText}</div>
            `;
        } else {
            this.dropdown.innerHTML = countries
                .slice(0, this.options.maxResults)
                .map(country => this.renderCountryItem(country))
                .join('');
        }

        this.bindDropdownEvents();
        this.showDropdown();
    }

    renderCountryItem(country) {
        const flagUrl = this.getFlagUrl(country.iso2);
        const isSelected = this.selectedCountry && this.selectedCountry.code === country.code;
        
        return `
            <div class="country-dropdown-item ${isSelected ? 'selected' : ''}" 
                 data-country='${JSON.stringify(country)}'>
                ${this.options.enableFlags ? `<img class="flag" src="${flagUrl}" alt="${country.code}">` : ''}
                <span class="name">${country.name}</span>
                <span class="code">${country.code}</span>
            </div>
        `;
    }

    bindDropdownEvents() {
        this.dropdown.querySelectorAll('.country-dropdown-item').forEach(item => {
            item.addEventListener('click', () => {
                const country = JSON.parse(item.getAttribute('data-country'));
                this.selectCountry(country);
            });
        });
    }

    selectCountry(country) {
        this.selectedCountry = country;
        this.inputElement.value = country.name;
        this.updateFlag(country);
        this.updateValidation(true);
        this.hideDropdown();

        // Триггерим событие изменения для внешних слушателей
        this.inputElement.dispatchEvent(new CustomEvent('countrySelected', {
            detail: country
        }));
    }

    updateFlag(country) {
        if (!this.flagElement) return;
        
        this.flagElement.src = this.getFlagUrl(country.iso2);
        this.flagElement.style.display = 'block';
    }

    getFlagUrl(iso2Code) {
        // Используем CDN флагов или локальные файлы
        return `/static/flags/4x3/${iso2Code.toLowerCase()}.svg`;
    }

    updateValidation(isValid) {
        this.isValid = isValid;
        
        this.inputElement.classList.remove('valid', 'invalid');
        
        if (this.inputElement.value.trim()) {
            this.inputElement.classList.add(isValid ? 'valid' : 'invalid');
        }
    }

    validateInput() {
        const value = this.inputElement.value.trim();
        
        if (!value) {
            this.updateValidation(false);
            return false;
        }

        // Если поле не пустое, ищем точное совпадение
        const exactMatch = this.countries.find(country => 
            country.name === value || country.code === value
        );

        if (exactMatch) {
            this.selectCountry(exactMatch);
            return true;
        } else if (!this.options.allowFreeText) {
            this.updateValidation(false);
            return false;
        }

        return true;
    }

    showDropdown() {
        this.dropdown.style.display = 'block';
    }

    hideDropdown() {
        this.dropdown.style.display = 'none';
    }

    handleKeyDown(e) {
        const items = this.dropdown.querySelectorAll('.country-dropdown-item:not(.no-results)');
        const highlighted = this.dropdown.querySelector('.highlighted');
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.highlightNext(items, highlighted);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.highlightPrev(items, highlighted);
                break;
            case 'Enter':
                e.preventDefault();
                if (highlighted) {
                    highlighted.click();
                }
                break;
            case 'Escape':
                this.hideDropdown();
                break;
        }
    }

    highlightNext(items, current) {
        if (!items.length) return;
        
        const currentIndex = Array.from(items).indexOf(current);
        const nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        
        if (current) current.classList.remove('highlighted');
        items[nextIndex].classList.add('highlighted');
    }

    highlightPrev(items, current) {
        if (!items.length) return;
        
        const currentIndex = Array.from(items).indexOf(current);
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        
        if (current) current.classList.remove('highlighted');
        items[prevIndex].classList.add('highlighted');
    }

    /**
     * Приоритетная логика: заполняем страну только если поле пустое
     * Ручные правки пользователя имеют приоритет
     */
    initializePriorityFromRankedin() {
        const currentValue = this.inputElement.value.trim();
        
        // Если поле уже заполнено, не перезаписываем
        if (currentValue) {
            this.validateInput();
            return;
        }

        // Здесь можно добавить логику получения страны из данных Rankedin
        // Пример: получаем код страны участника
        const rankedinCountry = this.getRankedinCountryCode();
        
        if (rankedinCountry) {
            const country = this.countries.find(c => c.code === rankedinCountry);
            if (country) {
                this.selectCountry(country);
            }
        }
    }

    /**
     * Получение кода страны из данных участника Rankedin
     * Интегрируется с существующей логикой загрузки участников
     */
    getRankedinCountryCode() {
        // Здесь нужно интегрироваться с существующим кодом загрузки участников
        // Пример получения из глобальных данных или API
        
        // Получаем ID выбранного участника
        const participantId = document.getElementById('selectedParticipantId')?.value;
        if (!participantId) return null;

        // Ищем участника в кэшированных данных турнира
        if (window.currentTournamentData && window.currentTournamentData.participants) {
            const participant = window.currentTournamentData.participants.find(p => 
                p.Id == participantId || p.id == participantId
            );
            
            if (participant) {
                return participant.CountryShort || participant.country_code;
            }
        }

        return null;
    }

    /**
     * API методы для внешнего использования
     */
    getSelectedCountry() {
        return this.selectedCountry;
    }

    setCountry(countryCode) {
        const country = this.countries.find(c => c.code === countryCode);
        if (country) {
            this.selectCountry(country);
        }
    }

    isValidSelection() {
        return this.isValid;
    }

    clear() {
        this.inputElement.value = '';
        this.selectedCountry = null;
        this.updateValidation(false);
        if (this.flagElement) {
            this.flagElement.style.display = 'none';
        }
        this.hideDropdown();
    }
}

// Экспорт для глобального использования
window.CountryAutocomplete = CountryAutocomplete;