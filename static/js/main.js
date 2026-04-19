// static/js/main.js
// Глобальные переменные
let tournaments = [];
let courts = [];
let currentTournamentId = null;
let autoRefreshTimer = null;
let refreshInterval = 30000; // 30 секунд
let isAuthenticated = false;
let currentUsername = '';
let pendingAuthAction = null;
let xmlFiles = [];
let mediaImages = [];

document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    initializeTheme();
	checkAuthStatus();
    loadTournaments();
    setupEventListeners();
    startAutoRefresh();
    updateSystemInfo();
});

// Настройка обработчиков событий
function setupEventListeners() {
    initializeScheduleDateInput();
    document.getElementById('tournamentForm').addEventListener('submit', handleTournamentSubmit);
    document.getElementById('xmlTournamentSelect').addEventListener('change', updateXMLTypes);
    document.getElementById('refreshIntervalInput').addEventListener('change', updateRefreshInterval);
    document.getElementById('autoRefreshEnabled').addEventListener('change', toggleAutoRefresh);
    document.getElementById('themeSelect').addEventListener('change', handleThemeChange);
    const mediaTab = document.getElementById('media-tab');
    if (mediaTab) {
        mediaTab.addEventListener('shown.bs.tab', loadMediaImages);
    }

    // Обработчик формы авторизации
    document.getElementById('authForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const username = document.getElementById('authUsername').value.trim();
        const password = document.getElementById('authPassword').value.trim();
        
        if (!username || !password) {
            showAlert('Введите имя пользователя и пароль', 'warning');
            return;
        }
        
        await performLogin(username, password);
    });

    const changePasswordForm = document.getElementById('changePasswordForm');
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await changePassword();
        });
    }
}

function initializeScheduleDateInput() {
    const dateInput = document.getElementById('scheduleDateInput');
    if (!dateInput || dateInput.value) {
        return;
    }
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    dateInput.value = `${now.getFullYear()}-${month}-${day}`;
}

function getSelectedScheduleDate() {
    const dateInput = document.getElementById('scheduleDateInput');
    if (!dateInput || !dateInput.value) {
        return null;
    }
    const [year, month, day] = dateInput.value.split('-');
    if (!year || !month || !day) {
        return null;
    }
    return `${day}.${month}.${year}`;
}

// ФУНКЦИИ для аутентификации
async function checkAuthStatus() {
    // Проверяет статус аутентификации при загрузке страницы
    try {
        const response = await fetch('/api/auth/status');
        const data = await response.json();
        
        if (data.authenticated) {
            isAuthenticated = true;
            currentUsername = data.username;
            updateAuthUI(true);
        } else {
            isAuthenticated = false;
            updateAuthUI(false);
        }
    } catch (error) {
        console.error('Ошибка проверки аутентификации:', error);
        isAuthenticated = false;
        updateAuthUI(false);
    }
}

function updateAuthUI(authenticated) {
    // Обновляет интерфейс в зависимости от статуса аутентификации
    const authUserInfo = document.getElementById('authUserInfo');
    const currentUsernameSpan = document.getElementById('currentUsername');
    const settingsTab = document.getElementById('settings-tab');
    const settingsPane = document.getElementById('settings-pane');
    const mediaTab = document.getElementById('media-tab');
    const mediaPane = document.getElementById('media-pane');
    
    if (authenticated && currentUsername) {
        authUserInfo.style.display = 'flex';
        currentUsernameSpan.textContent = currentUsername;
        if (settingsTab) settingsTab.style.display = '';
        if (settingsPane) settingsPane.style.display = '';
        if (mediaTab) mediaTab.style.display = '';
        if (mediaPane) mediaPane.style.display = '';
    } else {
        authUserInfo.style.display = 'none';
        if (settingsTab) settingsTab.style.display = 'none';
        if (settingsPane) settingsPane.style.display = 'none';
        if (mediaTab) mediaTab.style.display = 'none';
        if (mediaPane) mediaPane.style.display = 'none';
        if (settingsPane && settingsPane.classList.contains('active')) {
            const tournamentTab = document.getElementById('tournament-tab');
            if (tournamentTab) tournamentTab.click();
        }
        if (mediaPane && mediaPane.classList.contains('active')) {
            const tournamentTab = document.getElementById('tournament-tab');
            if (tournamentTab) tournamentTab.click();
        }
    }
}

function showAuthModal(callback) {
    pendingAuthAction = callback;
    document.getElementById('authOverlay').style.display = 'flex';
}

function closeAuthModal() {
    document.getElementById('authOverlay').style.display = 'none';
    document.getElementById('authForm').reset();
    pendingAuthAction = null;
}

async function performLogin(username, password) {
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            isAuthenticated = true;
            currentUsername = data.username;
            updateAuthUI(true);
            closeAuthModal();
            
            showAlert('Успешная авторизация!', 'success');
            
            // Выполняем отложенное действие
            if (pendingAuthAction) {
                pendingAuthAction();
                pendingAuthAction = null;
            }
            
            return true;
        } else {
            showAlert(data.error || 'Ошибка авторизации', 'danger');
            return false;
        }
    } catch (error) {
        console.error('Login error:', error);
        showAlert('Ошибка подключения к серверу', 'danger');
        return false;
    }
}

async function logout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            isAuthenticated = false;
            currentUsername = '';
            updateAuthUI(false);
            showAlert('Выход выполнен', 'info');
        }
    } catch (error) {
        console.error('Logout error:', error);
        showAlert('Ошибка выхода из системы', 'danger');
    }
}

async function changePassword() {
    if (!isAuthenticated) {
        showAuthModal(changePassword);
        return;
    }

    const currentPasswordInput = document.getElementById('currentPassword');
    const newPasswordInput = document.getElementById('newPassword');
    const confirmPasswordInput = document.getElementById('confirmPassword');

    if (!currentPasswordInput || !newPasswordInput || !confirmPasswordInput) {
        return;
    }

    const current_password = currentPasswordInput.value;
    const new_password = newPasswordInput.value;
    const confirm_password = confirmPasswordInput.value;

    if (!current_password || !new_password || !confirm_password) {
        showAlert('Заполните все поля пароля', 'warning');
        return;
    }

    if (new_password !== confirm_password) {
        showAlert('Новый пароль и подтверждение не совпадают', 'warning');
        return;
    }

    if (new_password.length < 6) {
        showAlert('Минимальная длина нового пароля: 6 символов', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ current_password, new_password, confirm_password })
        });

        if (response.status === 401) {
            isAuthenticated = false;
            updateAuthUI(false);
            showAuthModal(changePassword);
            return;
        }

        const data = await response.json();
        if (response.ok && data.success) {
            currentPasswordInput.value = '';
            newPasswordInput.value = '';
            confirmPasswordInput.value = '';
            showAlert(data.message || 'Пароль изменен', 'success');
        } else {
            showAlert(data.error || 'Ошибка смены пароля', 'danger');
        }
    } catch (error) {
        console.error('Change password error:', error);
        showAlert('Ошибка подключения к серверу', 'danger');
    }
}

function requireAuth(action) {
    if (isAuthenticated) {
        action();
    } else {
        showAuthModal(action);
    }
}

// === ТЕМА ИНТЕРФЕЙСА ===
function initializeTheme() {
    const savedTheme = localStorage.getItem('vmixTheme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    document.getElementById('themeSelect').value = savedTheme;
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('vmixTheme', newTheme);
    document.getElementById('themeSelect').value = newTheme;
    updateThemeIcon(newTheme);
}

function handleThemeChange() {
    const theme = document.getElementById('themeSelect').value;
    if (theme === 'auto') {
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.setAttribute('data-theme', systemDark ? 'dark' : 'light');
    } else {
        document.documentElement.setAttribute('data-theme', theme);
    }
    localStorage.setItem('vmixTheme', theme);
    updateThemeIcon(theme);
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('themeIcon');
    if (theme === 'dark') {
        icon.className = 'fas fa-sun';
    } else {
        icon.className = 'fas fa-moon';
    }
}

// === УПРАВЛЕНИЕ ТУРНИРАМИ ===
async function handleTournamentSubmit(e) {
    e.preventDefault();
    
    const tournamentId = document.getElementById('tournamentId').value.trim();
    if (!tournamentId) {
        showAlert('Введите ID турнира', 'warning');
        return;
    }
    if (!isAuthenticated) {
        showAuthModal(() => loadTournamentWithAuth(tournamentId));
        return;
    }
    
    loadTournamentWithAuth(tournamentId);
}

async function loadTournamentWithAuth(tournamentId) {
    showLoading(true);
    
    try {
        const response = await fetch(`/api/tournament/${tournamentId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();
        
        if (response.status === 401 && data.auth_required) {
            // Требуется повторная аутентификация
            isAuthenticated = false;
            updateAuthUI(false);
            showAuthModal(() => loadTournamentWithAuth(tournamentId));
            return;
        }
        
        if (data.success) {
            currentTournamentId = tournamentId;
            loadTournaments();
            updateTournamentSelects();
            showAlert(`Турнир "${data.name}" успешно загружен!`, 'success');
            document.getElementById('tournamentForm').reset();
            
            setTimeout(() => {
                document.getElementById('courts-tab').click();
                refreshCourts();
            }, 1000);
        } else {
            showAlert(data.error || 'Ошибка загрузки турнира', 'danger');
        }
    } catch (error) {
        console.error('Tournament load error:', error);
        showAlert('Ошибка подключения к серверу', 'danger');
    } finally {
        showLoading(false);
    }
}

async function loadTournaments() {
    try {
        const response = await fetch('/api/tournaments');
        tournaments = await response.json();
        renderTournaments();
        updateTournamentSelects();
    } catch (error) {
        console.error('Load tournaments error:', error);
    }
}

function renderTournaments() {
    const container = document.getElementById('tournamentList');
    const countBadge = document.getElementById('tournamentCount');
    
    if (tournaments.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-trophy fa-3x mb-3 opacity-50"></i>
                <p>Турниры не загружены</p>
                <small>Введите ID турнира и нажмите "Загрузить турнир"</small>
            </div>
        `;
        countBadge.textContent = '0';
        return;
    }

    container.innerHTML = tournaments.map(tournament => `
        <div class="tournament-card fade-in">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <h6 class="mb-2">${tournament.name}</h6>
                    <div class="mb-2">
                        <small class="text-muted">
                            <i class="fas fa-hashtag me-1"></i>ID: ${tournament.id} | 
                            <i class="fas fa-globe me-1"></i>${tournament.country || 'Неизвестная страна'} |
                            <i class="fas fa-calendar me-1"></i>${formatDate(tournament.created_at)}
                        </small>
                    </div>
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge bg-info">
                            <i class="fas fa-layer-group me-1"></i>${tournament.categories || 0} категорий
                        </span>
                        <span class="badge bg-secondary">
                            <i class="fas fa-table-tennis me-1"></i>${tournament.courts || 0} кортов
                        </span>
                        <span class="status-badge status-${tournament.status || 'active'}">
                            ${getStatusText(tournament.status || 'active')}
                        </span>
                    </div>
                </div>
                <div class="d-flex flex-column gap-1">
                    <button class="btn btn-sm btn-outline-primary" onclick="viewTournament('${tournament.id}')" title="Просмотр">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-warning" onclick="fetchParticipants('${tournament.id}')" title="Загрузить фотографии">
                        <i class="fas fa-camera"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-success" onclick="generateAllXML('${tournament.id}')" title="Генерировать все XML">
                        <i class="fas fa-code"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteTournament('${tournament.id}')" title="Удалить">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
    
    countBadge.textContent = tournaments.length;
}

function updateTournamentSelects() {
    const select = document.getElementById('xmlTournamentSelect');
    
    if (tournaments.length === 0) {
        select.innerHTML = '<option value="">Сначала загрузите турнир</option>';
        return;
    }

    select.innerHTML = '<option value="">Выберите турнир</option>' +
        tournaments.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
}

// === ЗАГРУЗКА ФОТО УЧАСТНИКОВ ===

// Кэш участников для поиска
let allParticipants = [];

function openUploadModal() {
    document.getElementById('uploadOverlay').style.display = 'flex';
}

function closeUploadModal() {
    document.getElementById('uploadOverlay').style.display = 'none';
    document.getElementById('participantList').innerHTML = '';
    document.getElementById('uploadFormArea').classList.add('d-none');
    document.getElementById('uploadFormArea').classList.remove('d-flex');
    document.getElementById('noSelectionMessage').style.display = 'flex';
    document.getElementById('previewArea').innerHTML = '';
    document.getElementById('editorControls').classList.add('d-none');
    document.getElementById('photoFile').value = '';
    document.getElementById('participantSearch').value = '';
    const cf = document.getElementById('classFilter');
    cf.innerHTML = '<option value="">Все группы</option>';
    cf.classList.add('d-none');
    photoEditor.destroy();
    allParticipants = [];
}

async function fetchParticipants(tournamentId) {
    try {
        openUploadModal();
        document.getElementById('participantList').innerHTML = '<div class="text-center p-3"><div class="spinner-border spinner-border-sm"></div></div>';

        const response = await fetch(`/api/tournament/${tournamentId}/participants`);
        if (!response.ok) throw new Error('Ошибка загрузки');
        allParticipants = await response.json();
        renderParticipantsList(allParticipants);
    } catch (error) {
        console.error("Ошибка:", error);
        showAlert('Ошибка загрузки участников', 'danger');
        document.getElementById('participantList').innerHTML = '<div class="text-danger p-2">Ошибка загрузки</div>';
    }

    // Загружаем группы независимо — не влияет на основной поток
    try {
        const r = await fetch(`/api/tournament/${tournamentId}/participant-classes`);
        if (!r.ok) return;
        const classes = await r.json();
        if (!classes.length) return;
        const cf = document.getElementById('classFilter');
        cf.innerHTML = '<option value="">Все группы</option>' +
            classes.map(c => `<option value="${c.class_id}" data-ids="${c.participant_ids.join(',')}">${c.class_name}</option>`).join('');
        cf.classList.remove('d-none');
    } catch (e) { /* группы не критичны */ }
}

function filterParticipants() {
    const query = document.getElementById('participantSearch').value.toLowerCase();
    const cf = document.getElementById('classFilter');
    const opt = cf.options[cf.selectedIndex];
    const classIds = opt && opt.value
        ? new Set(opt.dataset.ids.split(',').map(Number))
        : null;

    const filtered = allParticipants.filter(p => {
        const nameOk  = `${p.first_name} ${p.last_name}`.toLowerCase().includes(query);
        const classOk = !classIds || classIds.has(p.id);
        return nameOk && classOk;
    });
    renderParticipantsList(filtered);
}

function renderParticipantsList(participants) {
    const list = document.getElementById('participantList');
    
    if (participants.length === 0) {
        list.innerHTML = '<div class="text-muted p-2">Не найдено</div>';
        return;
    }
    
    list.innerHTML = participants.map(p => `
        <div class="participant-item" data-id="${p.id}" data-photo="${p.photo_url || ''}"
             onclick="selectParticipantById(${p.id})">
            <span>${p.first_name} ${p.last_name}</span>
            ${p.photo_url ? '<i class="fas fa-check-circle"></i>' : ''}
        </div>
    `).join('');
}

function selectParticipantById(id) {
    const participant = allParticipants.find(p => p.id === id);
    if (participant) selectParticipant(participant);
}

function selectParticipant(participant) {
    // Обновляем UI
    document.getElementById('selectedParticipantName').textContent = `${participant.first_name} ${participant.last_name}`;
    document.getElementById('selectedParticipantId').value = participant.id;
    document.getElementById('uploadFormArea').classList.remove('d-none');
    document.getElementById('uploadFormArea').classList.add('d-flex');
    document.getElementById('noSelectionMessage').style.display = 'none';
    
    // Подсвечиваем выбранного
    document.querySelectorAll('.participant-item').forEach(el => el.classList.remove('active'));
    const item = document.querySelector(`.participant-item[data-id="${participant.id}"]`);
    if (item) item.classList.add('active');
    
    // Область превью
    const previewArea = document.getElementById('previewArea');
    const editorControls = document.getElementById('editorControls');
    
    if (participant.photo_url) {
        // Фото есть - показываем статично
        previewArea.innerHTML = `<img class="existing-photo" src="${participant.photo_url}?t=${Date.now()}" alt="Фото">`;
        editorControls.classList.add('d-none');
    } else {
        // Фото нет - плейсхолдер
        previewArea.innerHTML = `
            <div class="d-flex flex-column align-items-center justify-content-center h-100 text-muted">
                <img src="/static/images/silhouette.png" style="opacity:0.3;max-height:80%;">
                <span class="mt-2">Выберите фото</span>
            </div>
        `;
        editorControls.classList.add('d-none');
    }
    
    // Заполняем поля из сохранённого info
    let info = {};
    try { info = JSON.parse(participant.info || '{}'); } catch (e) {}
    photoEditor.destroy();
    document.getElementById('photoFile').value = '';

    // Страна: info.country имеет приоритет над country_code от Rankedin
    const countryCode = info.country || participant.country_code || 'RUS';
    if (window.countryAutocomplete) {
        window.countryAutocomplete.clear();
        if (countryCode) window.countryAutocomplete.setCountry(countryCode);
    } else {
        document.getElementById('country').value = countryCode;
    }
    if (window.countryFormIntegration) window.countryFormIntegration.updateSaveButton();

    document.getElementById('rating').value       = info.rating    || '';
    document.getElementById('height').value       = info.height    || '';
    document.getElementById('position').value     = info.position  || '';
    document.getElementById('english-name').value = info.full_name || '';
}

function handleFileSelect(input) {
    const file = input.files[0];
    if (!file) return;
    
    const previewArea = document.getElementById('previewArea');
    const editorControls = document.getElementById('editorControls');
    
    const reader = new FileReader();
    reader.onload = (e) => {
        photoEditor.init(previewArea, e.target.result);
        photoEditor.file = file; // Устанавливаем ПОСЛЕ init, чтобы не сбросился
        editorControls.classList.remove('d-none');
    };
    reader.readAsDataURL(file);
}

async function uploadPhoto() {
    const participantId = document.getElementById('selectedParticipantId').value;
    const previewArea = document.getElementById('previewArea');
    
    if (!participantId) {
        showAlert('Выберите участника', 'warning');
        return;
    }
    
    // Валидация страны: если в поле что-то введено, это должно быть из справочника
    const countryField = document.getElementById('country');
    if (window.countryAutocomplete && countryField.value.trim()) {
        if (!window.countryAutocomplete.isValidSelection()) {
            showAlert('Выберите страну из списка', 'warning');
            return;
        }
    }

    // Собираем данные
    const formData = new FormData();
    formData.append('participant_id', participantId);
    // Отправляем 3-буквенный код (из autocomplete), а не отображаемое имя
    const selectedCountry = window.countryAutocomplete ? window.countryAutocomplete.getSelectedCountry() : null;
    formData.append('country', selectedCountry ? selectedCountry.code : countryField.value);
    formData.append('rating', document.getElementById('rating').value);
    formData.append('height', document.getElementById('height').value);
    formData.append('position', document.getElementById('position').value);
    formData.append('english', document.getElementById('english-name').value);
    
    // Если есть файл - добавляем с параметрами кропа
    if (photoEditor.file) {
        formData.append('photo', photoEditor.file);
        const crop = photoEditor.getCropParams();
        formData.append('crop_x', crop.x);
        formData.append('crop_y', crop.y);
        formData.append('crop_scale', crop.scale);
        formData.append('natural_width', crop.naturalWidth);
        formData.append('natural_height', crop.naturalHeight);
    }
    
    // UI загрузки
    const btn = document.getElementById('uploadPhotoButton');
    const btnText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Сохранение...';
    
    try {
        const response = await fetch('/api/participants/upload-photo', {
            method: 'POST',
            body: formData
        });

        if (response.status === 401) {
            isAuthenticated = false;
            updateAuthUI(false);
            showAuthModal(uploadPhoto);
            return;
        }

        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Ошибка сервера');
        
        if (result.success) {
            showAlert('Сохранено', 'success');

            // Обновляем info в кэше всегда — даже если фото не менялось
            const p = allParticipants.find(x => x.id == participantId);
            if (p) {
                let cachedInfo = {};
                try { cachedInfo = JSON.parse(p.info || '{}'); } catch (e) {}
                const savedCountry = window.countryAutocomplete?.getSelectedCountry();
                cachedInfo.country   = savedCountry ? savedCountry.code : document.getElementById('country').value;
                cachedInfo.rating    = document.getElementById('rating').value;
                cachedInfo.height    = document.getElementById('height').value;
                cachedInfo.position  = document.getElementById('position').value;
                cachedInfo.full_name = document.getElementById('english-name').value;
                p.info = JSON.stringify(cachedInfo);
            }

            // Обновляем превью если было новое фото
            if (result.preview_url) {
                previewArea.innerHTML = `<img class="existing-photo" src="${result.preview_url}?t=${Date.now()}" alt="Фото">`;
                document.getElementById('editorControls').classList.add('d-none');

                // Галочка в списке
                const item = document.querySelector(`.participant-item[data-id="${participantId}"]`);
                if (item && !item.querySelector('.fa-check-circle')) {
                    item.insertAdjacentHTML('beforeend', '<i class="fas fa-check-circle"></i>');
                }

                if (p) p.photo_url = result.preview_url;
            }

            // Очищаем редактор
            photoEditor.file = null;
            document.getElementById('photoFile').value = '';
        } else {
            throw new Error(result.error || 'Ошибка');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка: ' + error.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = btnText;
    }
}

// === МОНИТОРИНГ КОРТОВ ===
async function refreshCourts() {
    if (!currentTournamentId && tournaments.length > 0) {
        currentTournamentId = tournaments[0].id;
    }
    
    if (!currentTournamentId) {
        document.getElementById('courtGrid').innerHTML = `
            <div class="text-center text-muted py-5 w-100">
                <i class="fas fa-table-tennis fa-3x mb-3 opacity-50"></i>
                <p>Выберите турнир для мониторинга кортов</p>
            </div>
        `;
        return;
    }

    try {
        const response = await fetch(`/api/tournament/${currentTournamentId}/courts`);
        courts = await response.json();
        renderCourts();
    } catch (error) {
        console.error('Courts refresh error:', error);
        showAlert('Ошибка обновления кортов', 'danger');
    }
}

async function toggleReferee(tournamentId, courtId, hasReferee) {
    try {
        const response = await fetch(`/api/court/${tournamentId}/${courtId}/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ has_referee: hasReferee })
        });
        if (!response.ok) throw new Error('Failed');
        await refreshCourts();
    } catch (error) {
        console.error('toggleReferee error:', error);
        showAlert('Ошибка изменения настройки судьи', 'danger');
    }
}

function renderCourts() {
    const container = document.getElementById('courtGrid');
    const countBadge = document.getElementById('courtCount');
    
    if (!Array.isArray(courts)) {
        console.error('Courts data is not an array:', courts);

        if (courts && courts.error) {
            container.innerHTML = `
                <div class="text-center text-muted py-5 w-100">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3 text-warning"></i>
                    <p>Ошибка загрузки данных кортов</p>
                    <small class="text-danger">${courts.error}</small>
                    <div class="mt-3">
                        <button class="btn btn-outline-primary" onclick="refreshCourts()">
                            <i class="fas fa-sync-alt me-1"></i>Попробовать снова
                        </button>
                    </div>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div class="text-center text-muted py-5 w-100">
                    <i class="fas fa-table-tennis fa-3x mb-3 opacity-50"></i>
                    <p>Нет данных о кортах</p>
                    <small>Корты появятся после загрузки турнира</small>
                </div>
            `;
        }
        countBadge.textContent = '0 кортов';
        return;
    }
    
    if (courts.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5 w-100">
                <i class="fas fa-table-tennis fa-3x mb-3 opacity-50"></i>
                <p>Нет данных о кортах</p>
                <small>Корты появятся после загрузки турнира</small>
            </div>
        `;
        countBadge.textContent = '0 кортов';
        return;
    }

    container.innerHTML = courts.map(court => {
        // Определяем активный матч
        const hasCurrentMatch = (court.first_participant && court.first_participant.length > 0) || 
                               (court.current_first_participant && court.current_first_participant.length > 0);
        
        const currentPlayers1 = court.current_first_participant || court.first_participant || [];
        const currentPlayers2 = court.current_second_participant || court.second_participant || [];
        const currentScore1 = court.current_first_participant_score || court.first_participant_score || 0;
        const currentScore2 = court.current_second_participant_score || court.second_participant_score || 0;
        const currentSets = court.current_detailed_result || court.detailed_result || [];
        const currentClass = court.current_class_name || court.class_name || '';
        const eventState = court.event_state || '';
        
        // Определяем статус матча для отображения
        const isFinished = eventState.toLowerCase() === 'finished';
        const isInProgress = eventState.toLowerCase() === 'inprogress' || eventState.toLowerCase() === 'in progress';
        const matchLabel = isFinished ? '⏹ Завершён' : isInProgress ? '▶ Сейчас' : eventState;
        const matchLabelClass = isFinished ? 'text-muted' : isInProgress ? 'text-success' : 'text-secondary';
        
        // Информация о следующем матче
        const hasNextMatch = court.next_first_participant && court.next_first_participant.length > 0;
        const nextPlayers1 = court.next_first_participant || [];
        const nextPlayers2 = court.next_second_participant || [];
        const nextClass = court.next_class_name || '';
        const nextStartTime = court.next_start_time || court.next_scheduled_time || '';
        
        // Формат сетов: "6-4 3-6 7-5"
        const setsDisplay = currentSets && currentSets.length > 0 
            ? currentSets.map(set => `${set.firstParticipantScore}-${set.secondParticipantScore}`).join(' ')
            : '';
        
        // Корт свободен только если нет ни текущего, ни следующего матча
        const isCourtFree = !hasCurrentMatch && !hasNextMatch;
        
        return `
            <div class="court-card slide-in">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="mb-0">${court.court_name || `Корт ${court.court_id}`}</h6>
                    <div class="d-flex align-items-center gap-2">
                        <span class="status-badge status-${getCourtStatus(court)}">
                            ${getCourtStatusText(court)}
                        </span>
                        <span class="badge ${court.has_referee === false ? 'bg-warning text-dark' : 'bg-light text-secondary border'}"
                              style="cursor:pointer; font-size:0.7em;"
                              onclick="toggleReferee('${currentTournamentId}', '${court.court_id}', ${court.has_referee === false})"
                              title="${court.has_referee === false ? 'Режим: без судьи. Показываются участники следующего матча. Кликни чтобы вернуть режим с судьёй.' : 'Кликни чтобы переключить в режим без судьи'}">
                            <i class="fas fa-user-tie me-1"></i>${court.has_referee === false ? 'Без судьи' : 'Судья'}
                        </span>
                        <small class="text-muted"><i class="fas fa-sync me-1"></i>${formatTime(new Date())}</small>
                    </div>
                </div>
                
                ${hasCurrentMatch ? `
                    <div class="mb-2 small d-flex justify-content-between align-items-center">
                        <span>
                            ${currentClass ? `<span class="text-muted me-2"><i class="fas fa-trophy me-1"></i>${currentClass}</span>` : ''}
                        </span>
                        <span class="${matchLabelClass} fw-bold">${matchLabel}</span>
                    </div>
                    <div class="mb-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-truncate" style="max-width: 60%"><strong>${formatPlayerNames(currentPlayers1, true)}</strong></span>
                            <span class="fw-bold">${currentScore1}</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-truncate" style="max-width: 60%"><strong>${formatPlayerNames(currentPlayers2, true)}</strong></span>
                            <span class="fw-bold">${currentScore2}</span>
                        </div>
                        ${setsDisplay ? `<div class="text-muted small text-end">${setsDisplay}</div>` : ''}
                    </div>
                ` : ''}
                
                ${hasNextMatch ? `
                    <div class="${hasCurrentMatch ? 'border-top pt-2' : ''} mb-2 small">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="text-primary fw-bold"><i class="fas fa-clock me-1"></i>Следующий</span>
                            ${nextStartTime ? `<span class="text-muted">${formatDateTime(nextStartTime)}</span>` : ''}
                        </div>
                        ${nextClass ? `<div class="text-muted small mb-1">${nextClass}</div>` : ''}
                        <div>${formatPlayerNames(nextPlayers1, true)} <span class="text-muted">vs</span> ${formatPlayerNames(nextPlayers2, true)}</div>
                    </div>
                ` : ''}
                
                ${isCourtFree ? `
                    <div class="text-center text-muted py-2 mb-2">
                        <i class="fas fa-pause-circle me-1"></i>Корт свободен
                    </div>
                ` : ''}
                
                <div class="d-flex justify-content-end">
					<div class="d-flex gap-1">
						${hasCurrentMatch || hasNextMatch ? `
<button class="btn btn-sm btn-outline-info" onclick="openCourtINTRO(this.dataset.tournamentId, '${court.court_id}')" data-tournament-id="${currentTournamentId}" title="HTML VS">
    <i class="fas fa-users me-1"></i>INTRO
</button>


<button class="btn btn-sm btn-outline-primary" onclick="openCourtVS(this.dataset.tournamentId, '${court.court_id}')" data-tournament-id="${currentTournamentId}" title="HTML VS">
    <i class="fas fa-users me-1"></i>VS
</button>
							<button class="btn btn-sm btn-warning" onclick="openCourtHTML('${currentTournamentId}', '${court.court_id}')" title="HTML Scoreboard">
								<i class="fa-solid fa-address-card"></i>SM
							</button>
<button class="btn btn-sm btn-success" onclick="openCourtScoreFull('${currentTournamentId}', '${court.court_id}')" title="HTML Scoreboard Full 4K">
	<i class="fas fa-tv me-1"></i>4K
</button>

<button class="btn btn-sm btn-outline-danger" onclick="openCourtWIN(this.dataset.tournamentId, '${court.court_id}')" data-tournament-id="${currentTournamentId}" title="HTML VS">
    <i class="fas fa-users me-1"></i>VIN
</button>
						` : ''}
					</div>
                </div>
            </div>
        `;
    }).join('');

    countBadge.textContent = `${courts.length} кортов`;
}

// === LIVE XML ФУНКЦИИ ===
async function loadLiveXMLList(tournamentId) {
    if (!tournamentId) {
        tournamentId = document.getElementById('xmlTournamentSelect').value;
    }
    
    if (!tournamentId) {
        showAlert('Выберите турнир', 'warning');
        return;
    }

    document.getElementById('liveXMLList').innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Загрузка...</span>
            </div>
            <p class="mt-2 text-muted">Загружаем Live XML данные...</p>
        </div>
    `;

    try {
        const response = await fetch(`/api/tournament/${tournamentId}/live-xml-info`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const liveXMLInfo = await response.json();
        
        if (liveXMLInfo.error) {
            throw new Error(liveXMLInfo.error);
        }
        
        renderLiveXMLList(liveXMLInfo);
        
    } catch (error) {
        console.error('Live XML info error:', error);
        document.getElementById('liveXMLList').innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Ошибка загрузки Live XML:</strong> ${error.message}
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-danger" onclick="loadLiveXMLList('${tournamentId}')">
                        <i class="fas fa-redo me-1"></i>Попробовать снова
                    </button>
                </div>
            </div>
        `;
    }
}


function renderLiveXMLList(liveXMLInfo) {
    const container = document.getElementById('liveXMLList');
    const tournament_id = liveXMLInfo.tournament_id || document.getElementById('xmlTournamentSelect').value;
    
    if (!liveXMLInfo.live_xml_types || liveXMLInfo.live_xml_types.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-broadcast-tower fa-3x mb-3 opacity-50"></i>
                <p>Нет доступных Live XML</p>
                <small>Загрузите турнир для получения live ссылок</small>
            </div>
        `;
        return;
    }

    const baseUrl = window.location.origin;
    
    container.innerHTML = `
        <div class="alert alert-success mb-3">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <i class="fas fa-trophy me-2"></i>
                    <strong>${liveXMLInfo.tournament_name}</strong>
                </div>
                <span class="badge bg-success">${liveXMLInfo.live_xml_count} Live XML</span>
            </div>
        </div>
        
        ${liveXMLInfo.live_xml_types.map(xmlType => `
            <div class="live-xml-card mb-3 p-3 border rounded">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">
                            <i class="fas fa-${getXMLTypeIcon(xmlType.type)} me-2"></i>
                            ${xmlType.name}
                        </h6>
                        <small class="text-muted">${xmlType.description}</small>
                        <div class="mt-1">
                            <span class="badge bg-info">${xmlType.update_frequency}</span>
                        </div>
                    </div>
                    <div class="d-flex flex-column gap-1">
                        <button class="btn btn-sm btn-success" onclick="testLiveXML('${xmlType.live_url}')" title="Тест">
                            <i class="fas fa-play"></i>
                        </button>

                        <button class="btn btn-sm btn-outline-primary" onclick="copyToClipboard('${baseUrl}${xmlType.live_url}')" title="Копировать">
                            <i class="fas fa-copy"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info" onclick="openInNewTab('${xmlType.live_url}')" title="Открыть">
                            <i class="fas fa-external-link-alt"></i>
                        </button>

						${xmlType.type === 'tournament_table' && xmlType.draw_type === 'elimination' ? `
							<button class="btn btn-sm btn-warning" onclick="openEliminationHTML('${tournament_id}', '${xmlType.class_id}', ${xmlType.draw_index}, '${xmlType.stage_name}')" title="HTML Турнирная сетка">
								<i class="fas fa-tv"></i>
							</button>
						` : ''}
						${xmlType.type === 'tournament_table' && xmlType.draw_type === 'round_robin' ? `
							<button class="btn btn-sm btn-warning" onclick="openRoundRobinHTML('${tournament_id}', '${xmlType.class_id}', ${xmlType.draw_index}, '${xmlType.group_name}')" title="HTML Групповая таблица">
								<i class="fas fa-tv"></i>
							</button>
						` : ''}
						
                    </div>
                </div>
                
                <div class="mt-2">
                    <div class="input-group input-group-sm">
                        <span class="input-group-text bg-success text-white">
                            <i class="fas fa-broadcast-tower"></i>
                        </span>
                        <input type="text" class="form-control font-monospace" 
                               value="${baseUrl}${xmlType.live_url}" 
                               readonly onclick="this.select()">
                    </div>
                </div>
            </div>
        `).join('')}
        
        <div class="alert alert-info mt-3">
            <h6><i class="fas fa-lightbulb me-2"></i>Как использовать в vMix:</h6>
            <ol class="mb-0">
                <li>Скопируйте нужную Live XML ссылку</li>
                <li>В vMix добавьте Data Source → Web</li>
                <li>Вставьте ссылку в поле URL</li>
                <li>Настройте интервал обновления (рекомендуется 5-30 секунд)</li>
                <li>Для HTML турнирных сеток используйте кнопку <i class="fas fa-tv"></i> - откроется Live версия в формате UHD 3840x2160</li>
            </ol>
        </div>
    `;
}



// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===


function openCourtVS(tournamentId, courtId) {
   
    const liveUrl = `/api/html-live/${tournamentId}/${courtId}/vs`;
    window.open(liveUrl, '_blank', 'width=3840,height=2160,resizable=yes,scrollbars=yes,menubar=no,toolbar=no');
}

function openCourtScoreFull(tournamentId, courtId) {
    const liveUrl = `/api/html-live/${tournamentId}/${courtId}/score_full`;
    window.open(liveUrl, '_blank', 'width=3840,height=2160,resizable=yes,scrollbars=yes,menubar=no,toolbar=no');
}

function openCourtWIN(tournamentId, courtId) {
    const liveUrl = `/api/html-live/${tournamentId}/${courtId}/winner`;
    window.open(liveUrl, '_blank', 'width=3840,height=2160,resizable=yes,scrollbars=yes,menubar=no,toolbar=no');
}

function openCourtINTRO(tournamentId, courtId) {
    const liveUrl = `/api/html-live/${tournamentId}/${courtId}/introduction`;
    window.open(liveUrl, '_blank', 'width=3840,height=2160,resizable=yes,scrollbars=yes,menubar=no,toolbar=no');
}

function openRoundRobinHTML(tournamentId, classId, drawIndex, groupName) {
    const liveUrl = `/api/html-live/round-robin/${tournamentId}/${classId}/${drawIndex}`;
    window.open(liveUrl, '_blank', 'width=3840,height=2160,resizable=yes,scrollbars=yes,menubar=no,toolbar=no');
}


function openScheduleHTML() {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (!tournamentId) {
        showAlert('Выберите турнир', 'warning');
        return;
    }

    const selectedDate = getSelectedScheduleDate();
    const query = selectedDate ? `?date=${encodeURIComponent(selectedDate)}` : '';
    const liveUrl = `/api/html-live/schedule/${tournamentId}${query}`;
    window.open(liveUrl, '_blank', 'width=3840,height=2160,resizable=yes,scrollbars=yes,menubar=no,toolbar=no');
}

function openScheduleHalfHTML(half) {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (!tournamentId) {
        showAlert('Выберите турнир', 'warning');
        return;
    }

    const selectedDate = getSelectedScheduleDate();
    const query = selectedDate ? `?date=${encodeURIComponent(selectedDate)}` : '';
    const liveUrl = `/api/html-live/schedule/${tournamentId}/half/${half}${query}`;
    window.open(liveUrl, '_blank', 'width=3840,height=2160,resizable=yes,scrollbars=yes,menubar=no,toolbar=no');
}

function openCourtHTML(tournamentId, courtId) {
    const liveUrl = `/api/html-live/${tournamentId}/${courtId}`;
    window.open(liveUrl, '_blank', 'width=600, height=200, resizable=yes, scrollbars=no,menubar=no,toolbar=no');
}

function getXMLTypeIcon(type) {
    const icons = {
        'court_score': 'scoreboard',
        'tournament_table': 'table',
        'schedule': 'calendar-alt'
    };
    return icons[type] || 'code';
}

function testLiveXML(liveUrl) {
    showLoading(true);
    
    fetch(liveUrl)
        .then(response => {
            if (response.ok) {
                showAlert('Live XML работает корректно!', 'success');
                return response.text();
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        })
        .then(xmlContent => {
            console.log('Live XML content preview:', xmlContent.substring(0, 200) + '...');
        })
        .catch(error => {
            showAlert(`Ошибка тестирования Live XML: ${error.message}`, 'danger');
        })
        .finally(() => {
            showLoading(false);
        });
}

function openInNewTab(url) {
    window.open(url, '_blank');
}

function copyAllLiveXML() {
    const liveXMLInputs = document.querySelectorAll('#liveXMLList input[readonly]');
    const urls = Array.from(liveXMLInputs).map(input => input.value);
    
    if (urls.length === 0) {
        showAlert('Нет доступных Live XML ссылок', 'warning');
        return;
    }
    
    const allUrls = urls.join('\n');
    navigator.clipboard.writeText(allUrls).then(() => {
        showAlert(`Скопированы все Live XML ссылки (${urls.length} шт.)`, 'success');
    }).catch(() => {
        showAlert('Не удалось скопировать ссылки', 'danger');
    });
}

function updateXMLTypes() {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    const showLiveXMLBtn = document.getElementById('showLiveXMLBtn');
    const openLiveScheduleBtn = document.getElementById('openLiveScheduleBtn');
    const openScheduleHalf1Btn = document.getElementById('openScheduleHalf1Btn');
    const openScheduleHalf2Btn = document.getElementById('openScheduleHalf2Btn');

    if (!tournamentId) {
        if (showLiveXMLBtn) showLiveXMLBtn.disabled = true;
        if (openLiveScheduleBtn) openLiveScheduleBtn.disabled = true;
        if (openScheduleHalf1Btn) openScheduleHalf1Btn.disabled = true;
        if (openScheduleHalf2Btn) openScheduleHalf2Btn.disabled = true;
        enableCompositeButtons(false);
        
        document.getElementById('liveXMLList').innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-broadcast-tower fa-3x mb-3 opacity-50"></i>
                <p>Live XML ссылки не загружены</p>
                <small>Выберите турнир для отображения live ссылок</small>
            </div>
        `;
        return;
    }

    if (showLiveXMLBtn) showLiveXMLBtn.disabled = false;
    if (openLiveScheduleBtn) openLiveScheduleBtn.disabled = false;
    if (openScheduleHalf1Btn) openScheduleHalf1Btn.disabled = false;
    if (openScheduleHalf2Btn) openScheduleHalf2Btn.disabled = false;
    enableCompositeButtons(true);
    
    loadLiveXMLList(tournamentId);
}

// === УТИЛИТЫ ===
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show position-fixed" 
             style="top: 20px; right: 20px; z-index: 10000; min-width: 350px;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', alertHtml);
    
    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) alert.remove();
    }, 5000);
}

function showLoading(show) {
    document.getElementById('loadingSpinner').style.display = show ? 'flex' : 'none';
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Ссылка скопирована в буфер обмена!', 'success');
    }).catch(() => {
        showAlert('Не удалось скопировать ссылку', 'danger');
    });
}

function formatPlayerNames(players, compact = false) {
    if (!players || players.length === 0) return 'TBD';
    
    return players.map(p => {
        const firstName = (p.firstName || '').trim();
        const lastName = (p.lastName || '').trim();
        
        if (compact) {
            // Компактный формат: A.Фамилия
            if (firstName && lastName) {
                return `${firstName.charAt(0)}.${lastName}`;
            } else if (lastName) {
                return lastName;
            } else if (firstName) {
                return firstName.charAt(0);
            }
            return '?';
        } else {
            // Полный формат
            if (firstName && lastName) {
                return `${firstName} ${lastName}`;
            } else if (firstName) {
                return firstName;
            } else if (lastName) {
                return lastName;
            }
            return 'Игрок';
        }
    }).filter(name => name && name !== 'Игрок' && name !== '?').join('/') || 'TBD';
}


function getCourtStatus(court) {
    const eventState = court.event_state?.toLowerCase();
    
    if (eventState === 'finished') {
        return 'finished';
    }
    
    if ((court.first_participant && court.first_participant.length > 0) || 
        (court.current_first_participant && court.current_first_participant.length > 0)) {
        return 'playing';
    }
    
    if (court.next_first_participant && court.next_first_participant.length > 0) {
        return 'scheduled';
    }
    
    return 'free';
}

async function refreshSingleCourt(courtId) {
    if (!currentTournamentId) return;
    
    try {
        const response = await fetch(`/api/tournament/${currentTournamentId}/courts`);
        const allCourts = await response.json();
        const courtIndex = courts.findIndex(c => c.court_id == courtId);
        const updatedCourt = allCourts.find(c => c.court_id == courtId);
        
        if (courtIndex !== -1 && updatedCourt) {
            courts[courtIndex] = updatedCourt;
            renderCourts(); // Перерисовываем все корты
            showAlert(`Корт ${updatedCourt.court_name || courtId} обновлен`, 'success');
        } else {
            showAlert('Корт не найден', 'warning');
        }
    } catch (error) {
        console.error('Single court refresh error:', error);
        showAlert('Ошибка обновления корта', 'danger');
    }
}

function getCourtStatusText(court) {
    const status = getCourtStatus(court);
    const statusMap = {
        'playing': 'Играет',
        'finished': 'Завершен',
        'scheduled': 'Запланирован',
        'free': 'Свободен'
    };
    return statusMap[status] || 'Неизвестно';
}

function getStatusText(status) {
    const statusMap = {
        'active': 'Активный',
        'finished': 'Завершен', 
        'pending': 'Ожидание'
    };
    return statusMap[status] || status;
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('ru-RU');
}

function formatTime(date) {
    return date.toLocaleTimeString('ru-RU');
}

function formatDateTime(dateTimeString) {
    if (!dateTimeString) return '';
    
    try {
        const date = new Date(dateTimeString);
        return date.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return dateTimeString;
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        if (!response.ok) throw new Error('Ошибка загрузки настроек с сервера');
        
        const settings = await response.json();

        localStorage.setItem('vmixSettings', JSON.stringify(settings));

        refreshInterval = (settings.refreshInterval || 30) * 1000;

        if (document.getElementById('refreshIntervalInput')) {
            document.getElementById('refreshIntervalInput').value = settings.refreshInterval || 30;
        }
        if (document.getElementById('autoRefreshEnabled')) {
            document.getElementById('autoRefreshEnabled').checked = settings.autoRefresh !== false;
        }
        if (document.getElementById('debugMode')) {
            document.getElementById('debugMode').checked = settings.debugMode || false;
				if (document.getElementById('finishedMatchesCount')) {
					document.getElementById('finishedMatchesCount').value = settings.finishedMatchesCount || 3;
				}
        }
        if (document.getElementById('themeSelect')) {
            document.getElementById('themeSelect').value = settings.theme || 'light';
        }
        if (document.getElementById('finishedMatchesCount')) {
            document.getElementById('finishedMatchesCount').value = settings.finishedMatchesCount || 3;
        }

        if (document.getElementById('refreshInterval')) {
            document.getElementById('refreshInterval').textContent = settings.refreshInterval;
        }

    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
        // fallback — из localStorage
        const saved = localStorage.getItem('vmixSettings');
        if (saved) {
            try {
                const settings = JSON.parse(saved);
                refreshInterval = (settings.refreshInterval || 30) * 1000;
				if (document.getElementById('refreshIntervalInput')) {
					document.getElementById('refreshIntervalInput').value = settings.refreshInterval || 30;
				}
				if (document.getElementById('autoRefreshEnabled')) {
					document.getElementById('autoRefreshEnabled').checked = settings.autoRefresh !== false;
				}
				if (document.getElementById('debugMode')) {
					document.getElementById('debugMode').checked = settings.debugMode || false;
				if (document.getElementById('finishedMatchesCount')) {
					document.getElementById('finishedMatchesCount').value = settings.finishedMatchesCount || 3;
				}
				}
            } catch (error) {
                console.error('Ошибка из localStorage:', error);
            }
        }
    }
}

function startAutoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
    }
    
    if (document.getElementById('autoRefreshEnabled') && document.getElementById('autoRefreshEnabled').checked) {
        autoRefreshTimer = setInterval(() => {
            if (currentTournamentId) {
                refreshCourts();
                updateSystemInfo();
            }
        }, refreshInterval);
    }
}

async function saveSettings() {
    if (!isAuthenticated) {
        showAuthModal(saveSettingsWithAuth);
        return;
    }
    
    saveSettingsWithAuth();
}

async function saveSettingsWithAuth() {
    const settings = {
        refreshInterval: parseInt(document.getElementById('refreshIntervalInput').value),
        autoRefresh: document.getElementById('autoRefreshEnabled').checked,
        debugMode: document.getElementById('debugMode').checked,
        theme: document.getElementById('themeSelect').value,
        finishedMatchesCount: parseInt(document.getElementById('finishedMatchesCount').value) || 3,
        lastSaved: new Date().toISOString()
    };
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });
        
        if (response.status === 401) {
            isAuthenticated = false;
            updateAuthUI(false);
            showAuthModal(saveSettingsWithAuth);
            return;
        }
        
        if (response.ok) {
            localStorage.setItem('vmixSettings', JSON.stringify(settings));
            refreshInterval = settings.refreshInterval * 1000;
            
            if (document.getElementById('refreshInterval')) {
                document.getElementById('refreshInterval').textContent = settings.refreshInterval;
            }
            
            if (settings.autoRefresh) {
                if (autoRefreshTimer) {
                    clearInterval(autoRefreshTimer);
                }
                startAutoRefresh();
            }
            
            showAlert('Настройки сохранены', 'success');
        } else {
            const data = await response.json();
            showAlert(data.error || 'Ошибка сохранения настроек', 'danger');
        }
    } catch (error) {
        console.error('Save settings error:', error);
        showAlert('Ошибка подключения к серверу', 'danger');
    }
}

function updateSystemInfo() {
    if (document.getElementById('totalTournaments')) {
        document.getElementById('totalTournaments').textContent = tournaments.length;
    }
    if (document.getElementById('totalCourts')) {
        document.getElementById('totalCourts').textContent = Array.isArray(courts) ? courts.length : 0;
    }
    if (document.getElementById('totalXMLFiles')) {
        document.getElementById('totalXMLFiles').textContent = Array.isArray(xmlFiles) ? xmlFiles.length : 0;
    }
    if (document.getElementById('lastUpdate')) {
        document.getElementById('lastUpdate').textContent = formatTime(new Date());
    }
}

function viewTournament(id) {
    currentTournamentId = id;
    document.getElementById('courts-tab').click();
    refreshCourts();
}

async function deleteTournament(id) {
    if (!confirm('Вы уверены, что хотите удалить этот турнир?')) return;
    
    if (!isAuthenticated) {
        showAuthModal(() => deleteTournamentWithAuth(id));
        return;
    }
    
    deleteTournamentWithAuth(id);
}

async function deleteTournamentWithAuth(id) {
    showLoading(true);
    
    try {
        const response = await fetch(`/api/tournament/${id}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        
        if (response.status === 401 && result.auth_required) {
            isAuthenticated = false;
            updateAuthUI(false);
            showAuthModal(() => deleteTournamentWithAuth(id));
            return;
        }
        
        if (response.ok && result.success) {
            await loadTournaments();
            updateTournamentSelects();
            showAlert('Турнир удален', 'warning');
            
            if (currentTournamentId === id) {
                currentTournamentId = null;
                courts = [];
                renderCourts();
            }
        } else {
            showAlert(result.error || 'Ошибка удаления турнира', 'danger');
        }
    } catch (error) {
        console.error('Delete tournament error:', error);
        showAlert('Ошибка подключения к серверу', 'danger');
    } finally {
        showLoading(false);
    }
}

async function generateAllXML(id) {
    showLoading(true);
    
    try {
        const response = await fetch(`/api/xml/${id}/all`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const xmlFiles = await response.json();
            showAlert(`Созданы XML файлы для турнира (${xmlFiles.length} шт.)`, 'success');
            document.getElementById('xml-tab').click();
        } else {
            showAlert('Ошибка массовой генерации XML', 'danger');
        }
    } catch (error) {
        console.error('Generate all XML error:', error);
        showAlert('Ошибка подключения к серверу', 'danger');
    } finally {
        showLoading(false);
    }
}

async function generateCourtXML(courtId) {
    if (!currentTournamentId) {
        showAlert('Сначала выберите турнир', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`/api/xml/${currentTournamentId}/court_${courtId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            const xmlInfo = await response.json();
            showAlert('XML для корта создан!', 'success');
            console.log('Generated court XML:', xmlInfo);
        } else {
            const error = await response.json();
            showAlert(error.error || 'Ошибка создания XML для корта', 'danger');
        }
    } catch (error) {
        console.error('Court XML error:', error);
        showAlert('Ошибка подключения к серверу', 'danger');
    } finally {
        showLoading(false);
    }
}

function toggleAutoRefresh() {
    const enabled = document.getElementById('autoRefreshEnabled').checked;
    if (enabled) {
        startAutoRefresh();
    } else {
        if (autoRefreshTimer) {
            clearInterval(autoRefreshTimer);
            autoRefreshTimer = null;
        }
    }
}

async function refreshAllData() {
    showLoading(true);
    
    try {
        await Promise.all([
            loadTournaments(),
            refreshCourts()
        ]);
        
        updateSystemInfo();
        showAlert('Все данные обновлены', 'success');
    } catch (error) {
        console.error('Refresh all error:', error);
        showAlert('Ошибка обновления данных', 'danger');
    } finally {
        showLoading(false);
    }
}

function showLiveXMLList() {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (tournamentId) {
        loadLiveXMLList(tournamentId);
    } else {
        showAlert('Выберите турнир для отображения Live XML ссылок', 'warning');
    }
}

// === КОМПОЗИТНЫЕ СТРАНИЦЫ ===

function openCompositePage(pageType, slotNumber) {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (!tournamentId) {
        showAlert('Выберите турнир', 'warning');
        return;
    }
    window.open(`/composite/${tournamentId}/${pageType}/${slotNumber}`, '_blank');
}

function openCompositeEditor(pageType, slotNumber) {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (!tournamentId) {
        showAlert('�������� ������', 'warning');
        return;
    }
    if (!isAuthenticated) {
        showAuthModal(() => openCompositeEditor(pageType, slotNumber));
        return;
    }
    window.open(`/composite/editor/${tournamentId}/${pageType}/${slotNumber}`, '_blank');
}

function enableCompositeButtons(enabled) {
    // Round buttons
    for (let i = 1; i <= 4; i++) {
        const btn = document.getElementById(`compositeRound${i}Btn`);
        const editBtn = document.getElementById(`compositeRound${i}EditBtn`);
        if (btn) btn.disabled = !enabled;
        if (editBtn) editBtn.disabled = !enabled;
    }
    // Elimination buttons
    for (let i = 1; i <= 4; i++) {
        const btn = document.getElementById(`compositeElimination${i}Btn`);
        const editBtn = document.getElementById(`compositeElimination${i}EditBtn`);
        if (btn) btn.disabled = !enabled;
        if (editBtn) editBtn.disabled = !enabled;
    }
}

function refreshLiveXMLList() {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (tournamentId) {
        loadLiveXMLList(tournamentId);
        showAlert('Список Live XML обновлен', 'info');
    } else {
        showAlert('Выберите турнир для обновления списка', 'warning');
    }
}

function updateRefreshInterval() {
    const newInterval = parseInt(document.getElementById('refreshIntervalInput').value);
    if (newInterval >= 5 && newInterval <= 300) {
        refreshInterval = newInterval * 1000;
        if (document.getElementById('refreshInterval')) {
            document.getElementById('refreshInterval').textContent = newInterval;
        }
        if (document.getElementById('autoRefreshEnabled') && document.getElementById('autoRefreshEnabled').checked) {
            if (autoRefreshTimer) {
                clearInterval(autoRefreshTimer);
            }
            startAutoRefresh();
        }
    }
}

function openEliminationHTML(tournamentId, classId, drawIndex, stageName) {
    const liveUrl = `/api/html-live/elimination/${tournamentId}/${classId}/${drawIndex}`;
    window.open(liveUrl, '_blank', 'width=3840,height=2160,resizable=yes,scrollbars=yes,menubar=no,toolbar=no');
}

// === MEDIA TAB ===
async function loadMediaImages() {
    try {
        const response = await fetch('/api/media/images');
        if (response.status === 401) {
            isAuthenticated = false;
            updateAuthUI(false);
            showAuthModal(loadMediaImages);
            return;
        }
        if (!response.ok) {
            throw new Error('Failed to load media list');
        }
        mediaImages = await response.json();
        renderMediaList();
    } catch (error) {
        console.error('Load media error:', error);
        showAlert('Ошибка загрузки списка изображений', 'danger');
    }
}

function renderMediaList() {
    const container = document.getElementById('mediaList');
    const count = document.getElementById('mediaCount');
    const searchInput = document.getElementById('mediaSearchInput');
    if (!container || !count) return;

    const query = (searchInput?.value || '').trim().toLowerCase();
    const items = mediaImages.filter(item => !query || item.name.toLowerCase().includes(query));
    count.textContent = String(items.length);

    if (items.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="text-center text-muted py-5">
                    <i class="fas fa-images fa-3x mb-3 opacity-50"></i>
                    <p class="mb-0">Изображения не найдены</p>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = items.map(item => `
        <div class="col-md-6 col-xl-4">
            <div class="card h-100">
                <img src="${item.url}" class="card-img-top" alt="${escapeHtml(item.name)}" style="height: 180px; object-fit: cover;">
                <div class="card-body">
                    <h6 class="card-title text-truncate mb-2" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</h6>
                    <div class="d-flex justify-content-between gap-2">
                        <a class="btn btn-sm btn-outline-primary" href="${item.url}" target="_blank" rel="noopener noreferrer" title="Открыть">
                            <i class="fas fa-eye"></i>
                        </a>
                        <button class="btn btn-sm btn-outline-secondary" onclick="renameMediaImage('${encodeURIComponent(item.name)}')" title="Переименовать">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteMediaImage('${encodeURIComponent(item.name)}')" title="Удалить">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

async function uploadMediaImage() {
    const input = document.getElementById('mediaUploadInput');
    if (!input || !input.files || input.files.length === 0) {
        showAlert('Выберите файл для загрузки', 'warning');
        return;
    }

    requireAuth(async () => {
        const formData = new FormData();
        formData.append('image', input.files[0]);

        try {
            showLoading(true);
            const response = await fetch('/api/media/images', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (response.status === 401) {
                isAuthenticated = false;
                updateAuthUI(false);
                showAuthModal(uploadMediaImage);
                return;
            }

            if (!response.ok) {
                throw new Error(data.error || 'Upload failed');
            }

            showAlert(data.replaced ? 'Файл заменён' : 'Файл загружен', 'success');
            input.value = '';
            await loadMediaImages();
        } catch (error) {
            console.error('Upload media error:', error);
            showAlert(error.message || 'Ошибка загрузки файла', 'danger');
        } finally {
            showLoading(false);
        }
    });
}

function deleteMediaImage(encodedName) {
    const name = decodeURIComponent(encodedName);
    if (!confirm(`Удалить файл ${name}?`)) return;

    requireAuth(async () => {
        try {
            showLoading(true);
            const response = await fetch(`/api/media/images/${encodeURIComponent(name)}`, {
                method: 'DELETE'
            });
            const data = await response.json();

            if (response.status === 401) {
                isAuthenticated = false;
                updateAuthUI(false);
                showAuthModal(() => deleteMediaImage(encodedName));
                return;
            }

            if (!response.ok) {
                throw new Error(data.error || 'Delete failed');
            }

            showAlert('Файл удалён', 'success');
            await loadMediaImages();
        } catch (error) {
            console.error('Delete media error:', error);
            showAlert(error.message || 'Ошибка удаления файла', 'danger');
        } finally {
            showLoading(false);
        }
    });
}

function renameMediaImage(encodedName) {
    const oldName = decodeURIComponent(encodedName);
    const newName = prompt('Новое имя файла:', oldName);
    if (!newName || newName === oldName) return;

    requireAuth(async () => {
        try {
            showLoading(true);
            const response = await fetch('/api/media/images/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_name: oldName, new_name: newName })
            });
            const data = await response.json();

            if (response.status === 401) {
                isAuthenticated = false;
                updateAuthUI(false);
                showAuthModal(() => renameMediaImage(encodedName));
                return;
            }

            if (!response.ok) {
                throw new Error(data.error || 'Rename failed');
            }

            showAlert('Файл переименован', 'success');
            await loadMediaImages();
        } catch (error) {
            console.error('Rename media error:', error);
            showAlert(error.message || 'Ошибка переименования файла', 'danger');
        } finally {
            showLoading(false);
        }
    });
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatBytes(size) {
    if (!Number.isFinite(size)) return '0 B';
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

