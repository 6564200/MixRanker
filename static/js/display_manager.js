/**
 * Display Manager - управление окнами трансляции
 * Работает как на отдельной странице, так и в модальном окне
 */

// Глобальные переменные
let displayWindows = { pool: [], court: [] };
let displayTournaments = [];
let currentRotationItems = [];
let displayIsAuthenticated = false;
let displayMediaImages = [];

async function checkDisplayAuthStatus() {
    try {
        const response = await fetch('/api/auth/status');
        if (!response.ok) return false;
        const data = await response.json();
        displayIsAuthenticated = !!data.authenticated;
        return displayIsAuthenticated;
    } catch {
        displayIsAuthenticated = false;
        return false;
    }
}

function ensureDisplayAuth() {
    if (displayIsAuthenticated) return true;
    showAlert('Требуется авторизация для изменения настроек', 'warning');
    return false;
}

/**
 * Загрузка менеджера окон (для отдельной страницы)
 */
async function loadDisplayManager() {
    try {
        await checkDisplayAuthStatus();
        await Promise.all([
            loadDisplayWindows(),
            loadDisplayTournaments()
        ]);
        
        renderCourtWindows();
        renderPoolWindows();
        
    } catch (error) {
        console.error('Error loading display manager:', error);
        showAlert('Ошибка загрузки окон трансляции', 'danger');
    }
}

/**
 * Открытие менеджера в новой вкладке
 */
function openDisplayManager() {
    window.open('/display/manager', '_blank');
}

/**
 * Загрузка всех окон
 */
async function loadDisplayWindows() {
    const response = await fetch('/api/display/windows');
    if (!response.ok) throw new Error('Failed to load windows');
    displayWindows = await response.json();
}

/**
 * Загрузка списка турниров
 */
async function loadDisplayTournaments() {
    const response = await fetch('/api/tournaments');
    if (!response.ok) throw new Error('Failed to load tournaments');
    displayTournaments = await response.json();
}

async function ensureDisplayMediaImages() {
    if (displayMediaImages.length > 0) return;
    const response = await fetch('/api/media/images');
    if (response.status === 401) {
        displayIsAuthenticated = false;
        throw new Error('auth_required');
    }
    if (!response.ok) throw new Error('Failed to load media images');
    displayMediaImages = await response.json();
}

function getWindowPlaceholderImage(windowData) {
    return windowData?.placeholder_image || windowData?.settings?.placeholder_image || 'bg_001.png';
}

function getWindowBackgroundType(windowData) {
    return windowData?.settings?.background_type || 'image';
}

function setBackgroundTypeRadio(name, value) {
    document.querySelectorAll(`input[name="${name}"]`).forEach(r => { r.checked = r.value === value; });
}

function getBackgroundTypeRadio(name) {
    return document.querySelector(`input[name="${name}"]:checked`)?.value || 'image';
}

function getImageUrlByName(imageName) {
    const match = displayMediaImages.find(item => item.name === imageName);
    if (match?.url) return match.url;
    return `/static/images/${encodeURIComponent(imageName)}`;
}

function setupPlaceholderPicker(selectId, previewId, selectedImage) {
    const select = document.getElementById(selectId);
    const preview = document.getElementById(previewId);
    if (!select || !preview) return;

    const normalized = selectedImage || 'bg_001.png';
    const names = [...new Set(['bg_001.png', ...displayMediaImages.map(item => item.name), normalized])];
    select.innerHTML = names
        .map(name => `<option value="${name}" ${name === normalized ? 'selected' : ''}>${name}</option>`)
        .join('');

    const applyPreview = () => {
        preview.src = getImageUrlByName(select.value || 'bg_001.png');
    };

    select.onchange = applyPreview;
    applyPreview();
}

/**
 * Рендер списка окон кортов
 */
function renderCourtWindows() {
    const container = document.getElementById('court-windows-list');
    if (!container) return;
    
    container.innerHTML = displayWindows.court.map(window => {
        const isAuto = window.mode === 'auto';
        const isConfigured = window.tournament_id && window.court_id;
        
        return `
        <div class="col-md-6 col-lg-4 col-xl-3">
            <div class="card h-100 window-card ${isConfigured ? '' : 'border-warning'}">
                <div class="card-header d-flex justify-content-between align-items-center py-2">
                    <span class="fw-bold">
                        <i class="fas fa-desktop me-2 text-primary"></i>
                        ${window.name || 'Корт ' + window.slot_number}
                    </span>
                    <div class="form-check form-switch mb-0">
                        <input class="form-check-input" type="checkbox" role="switch" 
                               id="modeSwitch${window.slot_number}" 
                               ${isAuto ? 'checked' : ''}
                               onchange="toggleCourtMode(${window.slot_number}, this.checked)"
                               title="${isAuto ? 'Авто режим' : 'Ручной режим'}">
                        <label class="form-check-label small" for="modeSwitch${window.slot_number}">
                            ${isAuto ? 'Авто' : 'Ручн'}
                        </label>
                    </div>
                </div>
                <div class="card-body py-2">
                    ${isConfigured ? `
                        <p class="card-text small mb-1">
                            <i class="fas fa-trophy me-1 text-warning"></i>
                            ${getTournamentName(window.tournament_id)}
                        </p>
                        <p class="card-text small mb-2">
                            <i class="fas fa-map-marker-alt me-1 text-secondary"></i>
                            Корт: <strong>${window.court_id}</strong>
                        </p>
                        
                        <!-- Быстрые кнопки выбора страницы -->
                        <div class="btn-group btn-group-sm w-100 mb-2 ${isAuto ? 'opacity-50' : ''}" role="group">
                            <button class="btn ${window.manual_page === 'vs' && !isAuto ? 'btn-success' : 'btn-outline-secondary'}" 
                                    onclick="setCourtPage(${window.slot_number}, 'vs')" 
                                    ${isAuto ? 'disabled' : ''} title="VS">
                                <i class="fas fa-users"></i>
                            </button>
                            <button class="btn ${window.manual_page === 'scoreboard' && !isAuto ? 'btn-success' : 'btn-outline-secondary'}" 
                                    onclick="setCourtPage(${window.slot_number}, 'scoreboard')" 
                                    ${isAuto ? 'disabled' : ''} title="Scoreboard">
                                <i class="fas fa-table"></i>
                            </button>
                            <button class="btn ${window.manual_page === 'winner' && !isAuto ? 'btn-success' : 'btn-outline-secondary'}" 
                                    onclick="setCourtPage(${window.slot_number}, 'winner')" 
                                    ${isAuto ? 'disabled' : ''} title="Winner">
                                <i class="fas fa-trophy"></i>
                            </button>
                            <button class="btn ${window.manual_page === 'introduction' && !isAuto ? 'btn-success' : 'btn-outline-secondary'}" 
                                    onclick="setCourtPage(${window.slot_number}, 'introduction')" 
                                    ${isAuto ? 'disabled' : ''} title="Introduction">
                                <i class="fas fa-id-card"></i>
                            </button>
                        </div>
                        
                        <!-- Дополнительные кнопки: заглушка и произвольный URL -->
                        <div class="btn-group btn-group-sm w-100 ${isAuto ? 'opacity-50' : ''}" role="group">
                            <button class="btn ${window.manual_page === 'empty' && !isAuto ? 'btn-success' : 'btn-outline-secondary'}" 
                                    onclick="setCourtPage(${window.slot_number}, 'empty')" 
                                    ${isAuto ? 'disabled' : ''} title="�������� (${getWindowPlaceholderImage(window)})">
                                <i class="fas fa-image"></i> Заглушка
                            </button>
                            <button class="btn ${window.manual_page === 'custom' && !isAuto ? 'btn-success' : 'btn-outline-secondary'}" 
                                    onclick="setCourtCustomUrl(${window.slot_number})" 
                                    ${isAuto ? 'disabled' : ''} title="Произвольный URL">
                                <i class="fas fa-link"></i> URL
                            </button>
                        </div>
                        ${window.manual_page === 'custom' && window.settings?.custom_url ? `
                            <p class="card-text small text-muted mt-1 mb-0 text-truncate" title="${window.settings.custom_url}">
                                <i class="fas fa-link me-1"></i>${window.settings.custom_url}
                            </p>
                        ` : ''}
                    ` : `
                        <p class="card-text text-warning small mb-2">
                            <i class="fas fa-exclamation-triangle me-1"></i>
                            Не настроено
                        </p>
                        <button class="btn btn-outline-primary btn-sm w-100" onclick="editCourtWindow(${window.slot_number})">
                            <i class="fas fa-cog me-1"></i>Настроить
                        </button>
                    `}
                </div>
                <div class="card-footer py-2">
                    <div class="btn-group btn-group-sm w-100">
                        <button class="btn btn-outline-primary" onclick="editCourtWindow(${window.slot_number})" title="Настройки">
                            <i class="fas fa-cog"></i>
                        </button>
                        <a href="/display/court/${window.slot_number}" target="_blank" class="btn btn-outline-success" title="Открыть">
                            <i class="fas fa-external-link-alt"></i>
                        </a>
                        <button class="btn btn-outline-secondary" onclick="copyDisplayUrl('court', ${window.slot_number})" title="Копировать URL">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `}).join('');
}

/**
 * Рендер списка окон пула
 */
function renderPoolWindows() {
    const container = document.getElementById('pool-windows-list');
    if (!container) return;
    
    container.innerHTML = displayWindows.pool.map(window => {
        const items = window.settings?.items || [];
        const isAuto = window.mode === 'auto';
        const currentIndex = window.settings?.current_index;
        
        // Кнопки плейлиста (номера)
        const playlistButtons = items.map((item, idx) => {
            const isActive = window.manual_page === `item_${idx}` && !isAuto;
            return `<button class="btn ${isActive ? 'btn-success' : 'btn-outline-secondary'}" 
                           onclick="setPoolPage(${window.slot_number}, 'item_${idx}')" 
                           ${isAuto ? 'disabled' : ''} 
                           title="${item.name || item.url}">
                        ${idx + 1}
                    </button>`;
        }).join('');
        
        return `
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 window-card">
                    <div class="card-header d-flex justify-content-between align-items-center py-2">
                        <span class="fw-bold">
                            <i class="fas fa-layer-group me-2 text-info"></i>
                            ${window.name || 'Пул ' + window.slot_number}
                        </span>
                        <div class="form-check form-switch mb-0">
                            <input class="form-check-input" type="checkbox" role="switch" 
                                   id="poolModeSwitch${window.slot_number}" 
                                   ${isAuto ? 'checked' : ''}
                                   onchange="togglePoolMode(${window.slot_number}, this.checked)"
                                   title="${isAuto ? 'Авто режим (ротация)' : 'Ручной режим'}">
                            <label class="form-check-label small" for="poolModeSwitch${window.slot_number}">
                                ${isAuto ? 'Авто' : 'Ручн'}
                            </label>
                        </div>
                    </div>
                    <div class="card-body py-2">
                        <p class="card-text small mb-2">
                            <i class="fas fa-list me-1 text-muted"></i>
                            Плейлист: <strong>${items.length}</strong> стр.
                            ${items.length > 0 ? `
                                <button class="btn btn-link btn-sm p-0 ms-2" onclick="editPoolWindow(${window.slot_number})" title="Редактировать плейлист">
                                    <i class="fas fa-edit"></i>
                                </button>
                            ` : ''}
                        </p>
                        
                        ${items.length > 0 ? `
                            <!-- Кнопки плейлиста -->
                            <div class="btn-group btn-group-sm w-100 mb-2 ${isAuto ? 'opacity-50' : ''}" role="group">
                                ${playlistButtons}
                            </div>
                        ` : `
                            <p class="text-warning small mb-2">
                                <i class="fas fa-exclamation-triangle me-1"></i>
                                Пустой плейлист
                                <button class="btn btn-outline-primary btn-sm ms-2" onclick="editPoolWindow(${window.slot_number})">
                                    <i class="fas fa-plus me-1"></i>Добавить
                                </button>
                            </p>
                        `}
                        
                        <!-- Дополнительные кнопки: заглушка и произвольный URL -->
                        <div class="btn-group btn-group-sm w-100 ${isAuto ? 'opacity-50' : ''}" role="group">
                            <button class="btn ${window.manual_page === 'empty' && !isAuto ? 'btn-success' : 'btn-outline-secondary'}" 
                                    onclick="setPoolPage(${window.slot_number}, 'empty')" 
                                    ${isAuto ? 'disabled' : ''} title="�������� (${getWindowPlaceholderImage(window)})">
                                <i class="fas fa-image"></i> Заглушка
                            </button>
                            <button class="btn ${window.manual_page === 'custom' && !isAuto ? 'btn-success' : 'btn-outline-secondary'}" 
                                    onclick="setPoolCustomUrl(${window.slot_number})" 
                                    ${isAuto ? 'disabled' : ''} title="Произвольный URL">
                                <i class="fas fa-link"></i> URL
                            </button>
                        </div>
                        ${window.manual_page === 'custom' && window.settings?.custom_url ? `
                            <p class="card-text small text-muted mt-1 mb-0 text-truncate" title="${window.settings.custom_url}">
                                <i class="fas fa-link me-1"></i>${window.settings.custom_url}
                            </p>
                        ` : ''}
                    </div>
                    <div class="card-footer py-2">
                        <div class="btn-group btn-group-sm w-100">
                            <button class="btn btn-outline-primary" onclick="editPoolWindow(${window.slot_number})" title="Настройки плейлиста">
                                <i class="fas fa-cog"></i>
                            </button>
                            <a href="/display/pool/${window.slot_number}" target="_blank" class="btn btn-outline-success" title="Открыть">
                                <i class="fas fa-external-link-alt"></i>
                            </a>
                            <button class="btn btn-outline-secondary" onclick="copyDisplayUrl('pool', ${window.slot_number})" title="Копировать URL">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Переключение режима корта (авто/ручной)
 */
async function toggleCourtMode(slotNumber, isAuto) {
    if (!ensureDisplayAuth()) return;
    try {
        const response = await fetch(`/api/display/window/court/${slotNumber}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: isAuto ? 'auto' : 'manual' })
        });
        if (response.status === 401) {
            displayIsAuthenticated = false;
            showAlert('Требуется авторизация для изменения настроек', 'warning');
            return;
        }
        if (!response.ok) throw new Error('Failed to update');
        
        await loadDisplayWindows();
        renderCourtWindows();
        
    } catch (error) {
        console.error('Error toggling mode:', error);
        showAlert('Ошибка переключения режима', 'danger');
    }
}

/**
 * Быстрая установка страницы для корта (ручной режим)
 */
async function setCourtPage(slotNumber, page) {
    if (!ensureDisplayAuth()) return;
    try {
        const response = await fetch(`/api/display/window/court/${slotNumber}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'manual', manual_page: page })
        });
        if (response.status === 401) {
            displayIsAuthenticated = false;
            showAlert('Требуется авторизация для изменения настроек', 'warning');
            return;
        }
        if (!response.ok) throw new Error('Failed to update');
        
        await loadDisplayWindows();
        renderCourtWindows();
        
    } catch (error) {
        console.error('Error setting page:', error);
        showAlert('Ошибка установки страницы', 'danger');
    }
}

/**
 * Установка произвольного URL для корта
 */
async function setCourtCustomUrl(slotNumber) {
    if (!ensureDisplayAuth()) return;
    const window = displayWindows.court.find(w => w.slot_number === slotNumber);
    const currentUrl = window?.settings?.custom_url || '';
    
    const url = prompt('Введите URL страницы:', currentUrl);
    if (url === null) return; // Отмена
    
    if (!url.trim()) {
        showAlert('URL не может быть пустым', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/display/window/court/${slotNumber}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                mode: 'manual', 
                manual_page: 'custom',
                settings: {
                    ...(window?.settings || {}),
                    custom_url: url.trim(),
                    placeholder_image: getWindowPlaceholderImage(window)
                }
            })
        });
        if (response.status === 401) {
            displayIsAuthenticated = false;
            showAlert('Требуется авторизация для изменения настроек', 'warning');
            return;
        }
        if (!response.ok) throw new Error('Failed to update');
        
        await loadDisplayWindows();
        renderCourtWindows();
        showAlert('URL установлен', 'success');
        
    } catch (error) {
        console.error('Error setting custom URL:', error);
        showAlert('Ошибка установки URL', 'danger');
    }
}

/**
 * Переключение режима пула (авто/ручной)
 */
async function togglePoolMode(slotNumber, isAuto) {
    if (!ensureDisplayAuth()) return;
    try {
        const response = await fetch(`/api/display/window/pool/${slotNumber}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: isAuto ? 'auto' : 'manual' })
        });
        if (response.status === 401) {
            displayIsAuthenticated = false;
            showAlert('Требуется авторизация для изменения настроек', 'warning');
            return;
        }
        if (!response.ok) throw new Error('Failed to update');
        
        await loadDisplayWindows();
        renderPoolWindows();
        
    } catch (error) {
        console.error('Error toggling pool mode:', error);
        showAlert('Ошибка переключения режима', 'danger');
    }
}

/**
 * Быстрая установка страницы для пула (ручной режим)
 */
async function setPoolPage(slotNumber, page) {
    if (!ensureDisplayAuth()) return;
    try {
        const response = await fetch(`/api/display/window/pool/${slotNumber}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'manual', manual_page: page })
        });
        if (response.status === 401) {
            displayIsAuthenticated = false;
            showAlert('Требуется авторизация для изменения настроек', 'warning');
            return;
        }
        if (!response.ok) throw new Error('Failed to update');
        
        await loadDisplayWindows();
        renderPoolWindows();
        
    } catch (error) {
        console.error('Error setting pool page:', error);
        showAlert('Ошибка установки страницы', 'danger');
    }
}

/**
 * Установка произвольного URL для пула
 */
async function setPoolCustomUrl(slotNumber) {
    if (!ensureDisplayAuth()) return;
    const window = displayWindows.pool.find(w => w.slot_number === slotNumber);
    const currentUrl = window?.settings?.custom_url || '';
    
    const url = prompt('Введите URL страницы:', currentUrl);
    if (url === null) return; // Отмена
    
    if (!url.trim()) {
        showAlert('URL не может быть пустым', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/display/window/pool/${slotNumber}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                mode: 'manual', 
                manual_page: 'custom',
                settings: { 
                    ...(window?.settings || {}),
                    items: window?.settings?.items || [],
                    custom_url: url.trim(),
                    placeholder_image: getWindowPlaceholderImage(window)
                }
            })
        });
        if (response.status === 401) {
            displayIsAuthenticated = false;
            showAlert('Требуется авторизация для изменения настроек', 'warning');
            return;
        }
        if (!response.ok) throw new Error('Failed to update');
        
        await loadDisplayWindows();
        renderPoolWindows();
        showAlert('URL установлен', 'success');
        
    } catch (error) {
        console.error('Error setting pool custom URL:', error);
        showAlert('Ошибка установки URL', 'danger');
    }
}

/**
 * Редактирование окна корта
 */
async function editCourtWindow(slotNumber) {
    if (!ensureDisplayAuth()) return;
    const window = displayWindows.court.find(w => w.slot_number === slotNumber);
    if (!window) return;
    try {
        await ensureDisplayMediaImages();
    } catch (error) {
        if (error.message === 'auth_required') {
            showAlert('��������� ����������� ��� ��������� ��������', 'warning');
            return;
        }
        showAlert('������ �������� ������ �����������', 'danger');
        return;
    }
    
    document.getElementById('editCourtSlot').value = slotNumber;
    document.getElementById('editCourtName').value = window.name || '';
    
    // Заполняем список турниров
    const tournamentSelect = document.getElementById('editCourtTournament');
    tournamentSelect.innerHTML = '<option value="">-- Выберите турнир --</option>' +
        displayTournaments.map(t => `<option value="${t.id}" ${t.id === window.tournament_id ? 'selected' : ''}>${t.name}</option>`).join('');
    
    // Загружаем корты если выбран турнир
    if (window.tournament_id) {
        await loadCourtsForSelect('editCourtCourt', window.tournament_id, window.court_id);
    } else {
        document.getElementById('editCourtCourt').innerHTML = '<option value="">-- Сначала выберите турнир --</option>';
        document.getElementById('editCourtCourt').disabled = true;
    }
    
    // Обработчик смены турнира
    tournamentSelect.onchange = async () => {
        const tid = tournamentSelect.value;
        if (tid) {
            await loadCourtsForSelect('editCourtCourt', tid);
        } else {
            document.getElementById('editCourtCourt').innerHTML = '<option value="">-- Сначала выберите турнир --</option>';
            document.getElementById('editCourtCourt').disabled = true;
        }
    };

    setupPlaceholderPicker(
        'editCourtPlaceholder',
        'editCourtPlaceholderPreview',
        getWindowPlaceholderImage(window)
    );
    setBackgroundTypeRadio('courtBgType', getWindowBackgroundType(window));

    const modal = new bootstrap.Modal(document.getElementById('editCourtWindowModal'));
    modal.show();
}

/**
 * Загрузка кортов для селекта
 */
async function loadCourtsForSelect(selectId, tournamentId, selectedCourtId = null) {
    const select = document.getElementById(selectId);
    select.disabled = true;
    select.innerHTML = '<option value="">Загрузка...</option>';
    
    try {
        const response = await fetch(`/api/tournament/${tournamentId}/courts`);
        if (!response.ok) throw new Error('Failed to load courts');
        
        const courts = await response.json();
        select.innerHTML = '<option value="">-- Выберите корт --</option>' +
            courts.map(c => `<option value="${c.court_id}" ${c.court_id == selectedCourtId ? 'selected' : ''}>${c.court_name || 'Корт ' + c.court_id}</option>`).join('');
        select.disabled = false;
        
    } catch (error) {
        console.error('Error loading courts:', error);
        select.innerHTML = '<option value="">Ошибка загрузки</option>';
    }
}

/**
 * Сохранение окна корта
 */
async function saveCourtWindow() {
    if (!ensureDisplayAuth()) return;
    const slotNumber = document.getElementById('editCourtSlot').value;
    const currentWindow = displayWindows.court.find(w => w.slot_number == slotNumber);
    
    const data = {
        name: document.getElementById('editCourtName').value,
        tournament_id: document.getElementById('editCourtTournament').value || null,
        court_id: document.getElementById('editCourtCourt').value || null,
        settings: {
            ...(currentWindow?.settings || {}),
            placeholder_image: document.getElementById('editCourtPlaceholder')?.value || getWindowPlaceholderImage(currentWindow),
            background_type: getBackgroundTypeRadio('courtBgType')
        }
    };
    
    try {
        const response = await fetch(`/api/display/window/court/${slotNumber}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (response.status === 401) {
            displayIsAuthenticated = false;
            showAlert('Требуется авторизация для изменения настроек', 'warning');
            return;
        }
        if (!response.ok) throw new Error('Failed to save');
        
        showAlert('Окно сохранено', 'success');
        bootstrap.Modal.getInstance(document.getElementById('editCourtWindowModal')).hide();
        
        await loadDisplayWindows();
        renderCourtWindows();
        
    } catch (error) {
        console.error('Error saving court window:', error);
        showAlert('Ошибка сохранения', 'danger');
    }
}

/**
 * Редактирование окна пула
 */
async function editPoolWindow(slotNumber) {
    if (!ensureDisplayAuth()) return;
    const window = displayWindows.pool.find(w => w.slot_number === slotNumber);
    if (!window) return;
    try {
        await ensureDisplayMediaImages();
    } catch (error) {
        if (error.message === 'auth_required') {
            showAlert('��������� ����������� ��� ��������� ��������', 'warning');
            return;
        }
        showAlert('������ �������� ������ �����������', 'danger');
        return;
    }
    
    // Инициализируем ротацию
    currentRotationItems = [...(window.settings?.items || [])];
    
    document.getElementById('editPoolSlot').value = slotNumber;
    document.getElementById('editPoolName').value = window.name || '';
    
    // Расписание ротации
    renderRotationItems(currentRotationItems);

    setupPlaceholderPicker(
        'editPoolPlaceholder',
        'editPoolPlaceholderPreview',
        getWindowPlaceholderImage(window)
    );
    setBackgroundTypeRadio('poolBgType', getWindowBackgroundType(window));

    const modal = new bootstrap.Modal(document.getElementById('editPoolWindowModal'));
    modal.show();
}

/**
 * Рендер элементов ротации
 */
function renderRotationItems(items) {
    const container = document.getElementById('rotationItems');
    
    if (items.length === 0) {
        container.innerHTML = '<p class="text-muted small">Нет страниц в расписании. Добавьте страницы для ротации.</p>';
        return;
    }
    
    container.innerHTML = items.map((item, index) => `
        <div class="rotation-item card card-body p-2 mb-2" data-index="${index}">
            <div class="row g-2 align-items-center">
                <div class="col">
                    <input type="text" class="form-control form-control-sm" 
                           placeholder="URL страницы" value="${item.url || ''}" 
                           onchange="updateRotationItem(${index}, 'url', this.value)">
                </div>
                <div class="col-3">
                    <div class="input-group input-group-sm">
                        <input type="number" class="form-control" 
                               placeholder="Сек" value="${item.duration || 30}" min="5" max="600"
                               onchange="updateRotationItem(${index}, 'duration', parseInt(this.value))">
                        <span class="input-group-text">сек</span>
                    </div>
                </div>
                <div class="col-auto">
                    <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeRotationItem(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Добавить элемент ротации
 */
function addRotationItem() {
    currentRotationItems.push({ url: '', duration: 30 });
    renderRotationItems(currentRotationItems);
}

/**
 * Обновить элемент ротации
 */
function updateRotationItem(index, field, value) {
    if (currentRotationItems[index]) {
        currentRotationItems[index][field] = value;
    }
}

/**
 * Удалить элемент ротации
 */
function removeRotationItem(index) {
    currentRotationItems.splice(index, 1);
    renderRotationItems(currentRotationItems);
}

/**
 * Сохранение окна пула
 */
async function savePoolWindow() {
    if (!ensureDisplayAuth()) return;
    const slotNumber = document.getElementById('editPoolSlot').value;
    
    // Получаем текущее окно для сохранения существующих настроек
    const currentWindow = displayWindows.pool.find(w => w.slot_number == slotNumber);
    
    const data = {
        name: document.getElementById('editPoolName').value,
        settings: {
            ...(currentWindow?.settings || {}),
            items: currentRotationItems.filter(item => item.url),
            custom_url: currentWindow?.settings?.custom_url || null,
            placeholder_image: document.getElementById('editPoolPlaceholder')?.value || getWindowPlaceholderImage(currentWindow),
            background_type: getBackgroundTypeRadio('poolBgType')
        }
    };
    
    try {
        const response = await fetch(`/api/display/window/pool/${slotNumber}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (response.status === 401) {
            displayIsAuthenticated = false;
            showAlert('Требуется авторизация для изменения настроек', 'warning');
            return;
        }
        if (!response.ok) throw new Error('Failed to save');
        
        showAlert('Плейлист сохранён', 'success');
        bootstrap.Modal.getInstance(document.getElementById('editPoolWindowModal')).hide();
        
        await loadDisplayWindows();
        renderPoolWindows();
        
    } catch (error) {
        console.error('Error saving pool window:', error);
        showAlert('Ошибка сохранения', 'danger');
    }
}

/**
 * Копирование URL окна
 */
function copyDisplayUrl(type, slotNumber) {
    const url = `${window.location.origin}/display/${type}/${slotNumber}`;
    navigator.clipboard.writeText(url).then(() => {
        showAlert('URL скопирован: ' + url, 'success');
    }).catch(() => {
        showAlert('Ошибка копирования', 'danger');
    });
}

/**
 * Показать уведомление
 */
function showAlert(message, type = 'info') {
    // Пробуем Toast (для отдельной страницы)
    const toastEl = document.getElementById('alertToast');
    if (toastEl) {
        const toastIcon = document.getElementById('toastIcon');
        const toastMessage = document.getElementById('toastMessage');
        
        toastIcon.className = 'fas me-2 ' + (type === 'success' ? 'fa-check-circle text-success' : 
                                              type === 'danger' ? 'fa-exclamation-circle text-danger' : 
                                              'fa-info-circle text-info');
        toastMessage.textContent = message;
        
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        return;
    }
    
    // Fallback на alert
    console.log(`[${type}] ${message}`);
}

/**
 * Вспомогательные функции
 */
function getTournamentName(id) {
    const tournament = displayTournaments.find(t => t.id === id);
    return tournament ? tournament.name : id;
}

function getPageName(page) {
    const names = {
        'vs': 'VS',
        'scoreboard': 'Scoreboard',
        'winner': 'Winner',
        'introduction': 'Introduction'
    };
    return names[page] || page;
}


