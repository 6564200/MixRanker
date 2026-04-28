// static/js/main.js

// === ГЛОБАЛЬНОЕ СОСТОЯНИЕ ===
let tournaments = [];
let courts = [];
let currentTournamentId = null;
let autoRefreshTimer = null;
let refreshInterval = 30000; // 30 секунд
let isAuthenticated = false;
let currentUsername = '';
let pendingAuthAction = null;
let mediaImages = [];

// Опции popup-окна 4K (используется во всех окнах трансляции)
const POPUP_4K = 'width=3840,height=2160,resizable=yes,scrollbars=yes,menubar=no,toolbar=no';

document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    initializeTheme();
    checkAuthStatus();
    loadTournaments();
    setupEventListeners();
    startAutoRefresh();
    updateSystemInfo();
});

// === ОБРАБОТЧИКИ СОБЫТИЙ ===
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
    if (!dateInput || dateInput.value) return;
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    dateInput.value = `${now.getFullYear()}-${month}-${day}`;
}

function getSelectedScheduleDate() {
    const dateInput = document.getElementById('scheduleDateInput');
    if (!dateInput || !dateInput.value) return null;
    const [year, month, day] = dateInput.value.split('-');
    if (!year || !month || !day) return null;
    return `${day}.${month}.${year}`;
}

// === АУТЕНТИФИКАЦИЯ ===
async function checkAuthStatus() {
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

        // Если активна скрытая вкладка — откатываемся на "Турниры"
        const isHiddenActive =
            (settingsPane && settingsPane.classList.contains('active')) ||
            (mediaPane && mediaPane.classList.contains('active'));
        if (isHiddenActive) {
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();

        if (response.ok && data.success) {
            isAuthenticated = true;
            currentUsername = data.username;
            updateAuthUI(true);
            closeAuthModal();
            showAlert('Успешная авторизация!', 'success');
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
            headers: { 'Content-Type': 'application/json' }
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

    if (!currentPasswordInput || !newPasswordInput || !confirmPasswordInput) return;

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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_password, new_password, confirm_password })
        });

        if (response.status === 401) {
            handleUnauthorized(changePassword);
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

/** Обрабатывает 401 от сервера: сбрасывает сессию и открывает форму входа. */
function handleUnauthorized(retryAction) {
    isAuthenticated = false;
    updateAuthUI(false);
    showAuthModal(retryAction);
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
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (response.status === 401 && data.auth_required) {
            handleUnauthorized(() => loadTournamentWithAuth(tournamentId));
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

    // Группы загружаются независимо — не блокируют основной поток
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
    document.getElementById('selectedParticipantName').textContent = `${participant.first_name} ${participant.last_name}`;
    document.getElementById('selectedParticipantId').value = participant.id;
    document.getElementById('uploadFormArea').classList.remove('d-none');
    document.getElementById('uploadFormArea').classList.add('d-flex');
    document.getElementById('noSelectionMessage').style.display = 'none';

    document.querySelectorAll('.participant-item').forEach(el => el.classList.remove('active'));
    const item = document.querySelector(`.participant-item[data-id="${participant.id}"]`);
    if (item) item.classList.add('active');

    const previewArea = document.getElementById('previewArea');
    const editorControls = document.getElementById('editorControls');

    if (participant.photo_url) {
        previewArea.innerHTML = `<img class="existing-photo" src="${participant.photo_url}?t=${Date.now()}" alt="Фото">`;
        editorControls.classList.add('d-none');
    } else {
        previewArea.innerHTML = `
            <div class="d-flex flex-column align-items-center justify-content-center h-100 text-muted">
                <img src="/static/images/silhouette.png" style="opacity:0.3;max-height:80%;">
                <span class="mt-2">Выберите фото</span>
            </div>
        `;
        editorControls.classList.add('d-none');
    }

    let info = {};
    try { info = JSON.parse(participant.info || '{}'); } catch (e) {}
    photoEditor.destroy();
    document.getElementById('photoFile').value = '';

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
        photoEditor.file = file;
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

    const countryField = document.getElementById('country');
    if (window.countryAutocomplete && countryField.value.trim()) {
        if (!window.countryAutocomplete.isValidSelection()) {
            showAlert('Выберите страну из списка', 'warning');
            return;
        }
    }

    const formData = new FormData();
    formData.append('participant_id', participantId);
    const selectedCountry = window.countryAutocomplete ? window.countryAutocomplete.getSelectedCountry() : null;
    formData.append('country', selectedCountry ? selectedCountry.code : countryField.value);
    formData.append('rating', document.getElementById('rating').value);
    formData.append('height', document.getElementById('height').value);
    formData.append('position', document.getElementById('position').value);
    formData.append('english', document.getElementById('english-name').value);

    if (photoEditor.file) {
        formData.append('photo', photoEditor.file);
        const crop = photoEditor.getCropParams();
        formData.append('crop_x', crop.x);
        formData.append('crop_y', crop.y);
        formData.append('crop_scale', crop.scale);
        formData.append('natural_width', crop.naturalWidth);
        formData.append('natural_height', crop.naturalHeight);
    }

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
            handleUnauthorized(uploadPhoto);
            return;
        }

        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Ошибка сервера');

        if (result.success) {
            showAlert('Сохранено', 'success');

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

            if (result.preview_url) {
                previewArea.innerHTML = `<img class="existing-photo" src="${result.preview_url}?t=${Date.now()}" alt="Фото">`;
                document.getElementById('editorControls').classList.add('d-none');
                const item = document.querySelector(`.participant-item[data-id="${participantId}"]`);
                if (item && !item.querySelector('.fa-check-circle')) {
                    item.insertAdjacentHTML('beforeend', '<i class="fas fa-check-circle"></i>');
                }
                if (p) p.photo_url = result.preview_url;
            }

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
        const hasCurrentMatch = (court.first_participant && court.first_participant.length > 0) ||
                               (court.current_first_participant && court.current_first_participant.length > 0);

        const currentPlayers1 = court.current_first_participant || court.first_participant || [];
        const currentPlayers2 = court.current_second_participant || court.second_participant || [];
        const currentScore1   = court.current_first_participant_score || court.first_participant_score || 0;
        const currentScore2   = court.current_second_participant_score || court.second_participant_score || 0;
        const currentSets     = court.current_detailed_result || court.detailed_result || [];
        const currentClass    = court.current_class_name || court.class_name || '';
        const eventState      = court.event_state || '';

        const isFinished   = eventState.toLowerCase() === 'finished';
        const isInProgress = eventState.toLowerCase() === 'inprogress' || eventState.toLowerCase() === 'in progress';
        const matchLabel      = isFinished ? '⏹ Завершён' : isInProgress ? '▶ Сейчас' : eventState;
        const matchLabelClass = isFinished ? 'text-muted' : isInProgress ? 'text-success' : 'text-secondary';

        const hasNextMatch  = court.next_first_participant && court.next_first_participant.length > 0;
        const nextPlayers1  = court.next_first_participant || [];
        const nextPlayers2  = court.next_second_participant || [];
        const nextClass     = court.next_class_name || '';
        const nextStartTime = court.next_start_time || court.next_scheduled_time || '';

        const setsDisplay = currentSets && currentSets.length > 0
            ? currentSets.map(set => `${set.firstParticipantScore}-${set.secondParticipantScore}`).join(' ')
            : '';

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
                              title="${court.has_referee === false ? 'Режим: без судьи. Кликни чтобы вернуть режим с судьёй.' : 'Кликни чтобы переключить в режим без судьи'}">
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
                            <button class="btn btn-sm btn-outline-info" onclick="openCourtPage(this.dataset.tournamentId, '${court.court_id}', 'introduction')" data-tournament-id="${currentTournamentId}" title="INTRO">
                                <i class="fas fa-users me-1"></i>INTRO
                            </button>
                            <button class="btn btn-sm btn-outline-primary" onclick="openCourtPage(this.dataset.tournamentId, '${court.court_id}', 'vs')" data-tournament-id="${currentTournamentId}" title="VS">
                                <i class="fas fa-users me-1"></i>VS
                            </button>
                            <button class="btn btn-sm btn-warning" onclick="openCourtHTML('${currentTournamentId}', '${court.court_id}')" title="HTML Scoreboard">
                                <i class="fa-solid fa-address-card"></i>SM
                            </button>
                            <button class="btn btn-sm btn-success" onclick="openCourtPage('${currentTournamentId}', '${court.court_id}', 'score_full')" title="HTML Scoreboard Full 4K">
                                <i class="fas fa-tv me-1"></i>4K
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="openCourtPage(this.dataset.tournamentId, '${court.court_id}', 'winner')" data-tournament-id="${currentTournamentId}" title="Winner">
                                <i class="fas fa-users me-1"></i>WIN
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');

    countBadge.textContent = `${courts.length} кортов`;
}

// === LIVE XML ===
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
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        const liveXMLInfo = await response.json();
        if (liveXMLInfo.error) throw new Error(liveXMLInfo.error);
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
                        <button class="btn btn-sm btn-outline-primary" onclick="copyToClipboard('${baseUrl}${xmlType.live_url}')" title="Копировать">
                            <i class="fas fa-copy"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info" onclick="openInNewTab('${xmlType.live_url}')" title="Открыть">
                            <i class="fas fa-external-link-alt"></i>
                        </button>
                        ${xmlType.type === 'tournament_table' && xmlType.draw_type === 'elimination' ? `
                            <button class="btn btn-sm btn-warning" onclick="openEliminationHTML('${tournament_id}', '${xmlType.class_id}', ${xmlType.draw_index})" title="HTML Турнирная сетка">
                                <i class="fas fa-tv"></i>
                            </button>
                        ` : ''}
                        ${xmlType.type === 'tournament_table' && xmlType.draw_type === 'round_robin' ? `
                            <button class="btn btn-sm btn-warning" onclick="openRoundRobinHTML('${tournament_id}', '${xmlType.class_id}', ${xmlType.draw_index})" title="HTML Групповая таблица">
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
                <li>Для HTML турнирных сеток используйте кнопку <i class="fas fa-tv"></i> — откроется Live версия в формате UHD 3840×2160</li>
            </ol>
        </div>
    `;
}

// === ОТКРЫТИЕ ОКОН ТРАНСЛЯЦИИ ===

/** Открывает страницу корта по суффиксу пути: vs, score_full, winner, introduction */
function openCourtPage(tournamentId, courtId, path) {
    window.open(`/api/html-live/${tournamentId}/${courtId}/${path}`, '_blank', POPUP_4K);
}

function openCourtHTML(tournamentId, courtId) {
    window.open(`/api/html-live/${tournamentId}/${courtId}`, '_blank',
        'width=600,height=200,resizable=yes,scrollbars=no,menubar=no,toolbar=no');
}

function openRoundRobinHTML(tournamentId, classId, drawIndex) {
    window.open(`/api/html-live/round-robin/${tournamentId}/${classId}/${drawIndex}`, '_blank', POPUP_4K);
}

function openEliminationHTML(tournamentId, classId, drawIndex) {
    window.open(`/api/html-live/elimination/${tournamentId}/${classId}/${drawIndex}`, '_blank', POPUP_4K);
}

function openScheduleHTML() {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (!tournamentId) { showAlert('Выберите турнир', 'warning'); return; }
    const selectedDate = getSelectedScheduleDate();
    const query = selectedDate ? `?date=${encodeURIComponent(selectedDate)}` : '';
    window.open(`/api/html-live/schedule/${tournamentId}${query}`, '_blank', POPUP_4K);
}

function openScheduleHalfHTML(half) {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (!tournamentId) { showAlert('Выберите турнир', 'warning'); return; }
    const selectedDate = getSelectedScheduleDate();
    const query = selectedDate ? `?date=${encodeURIComponent(selectedDate)}` : '';
    window.open(`/api/html-live/schedule/${tournamentId}/half/${half}${query}`, '_blank', POPUP_4K);
}

function openMediaDashboard() {
    const tid = currentTournamentId || (tournaments.length > 0 ? tournaments[0].id : null);
    if (!tid) { showAlert('Сначала загрузите турнир', 'warning'); return; }
    window.open(`/display/media-dashboard/${tid}`, '_blank',
        'width=1920,height=1080,resizable=yes,scrollbars=no,menubar=no,toolbar=no');
}

// === УТИЛИТЫ XML ===
function getXMLTypeIcon(type) {
    const icons = {
        'court_score': 'scoreboard',
        'tournament_table': 'table',
        'schedule': 'calendar-alt'
    };
    return icons[type] || 'code';
}

function openInNewTab(url) {
    window.open(url, '_blank');
}

function updateXMLTypes() {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    const showLiveXMLBtn     = document.getElementById('showLiveXMLBtn');
    const openLiveScheduleBtn  = document.getElementById('openLiveScheduleBtn');
    const openScheduleHalf1Btn = document.getElementById('openScheduleHalf1Btn');
    const openScheduleHalf2Btn = document.getElementById('openScheduleHalf2Btn');

    const enabled = !!tournamentId;
    if (showLiveXMLBtn)      showLiveXMLBtn.disabled      = !enabled;
    if (openLiveScheduleBtn)  openLiveScheduleBtn.disabled  = !enabled;
    if (openScheduleHalf1Btn) openScheduleHalf1Btn.disabled = !enabled;
    if (openScheduleHalf2Btn) openScheduleHalf2Btn.disabled = !enabled;
    enableCompositeButtons(enabled);

    if (!enabled) {
        document.getElementById('liveXMLList').innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-broadcast-tower fa-3x mb-3 opacity-50"></i>
                <p>Live XML ссылки не загружены</p>
                <small>Выберите турнир для отображения live ссылок</small>
            </div>
        `;
        return;
    }

    loadLiveXMLList(tournamentId);
}

// === АЛЕРТЫ И UI ===
function showAlert(message, type = 'info') {
    const div = document.createElement('div');
    div.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    div.style.cssText = 'top:20px;right:20px;z-index:10000;min-width:350px;';
    div.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 5000);
}

function showLoading(show) {
    document.getElementById('loadingSpinner').style.display = show ? 'flex' : 'none';
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .then(() => showAlert('Ссылка скопирована в буфер обмена!', 'success'))
        .catch(() => showAlert('Не удалось скопировать ссылку', 'danger'));
}

// === ФОРМАТИРОВАНИЕ ===
function formatPlayerNames(players, compact = false) {
    if (!players || players.length === 0) return 'TBD';
    return players.map(p => {
        const firstName = (p.firstName || '').trim();
        const lastName  = (p.lastName  || '').trim();
        if (compact) {
            if (firstName && lastName) return `${firstName.charAt(0)}.${lastName}`;
            if (lastName)  return lastName;
            if (firstName) return firstName.charAt(0);
            return '?';
        } else {
            if (firstName && lastName) return `${firstName} ${lastName}`;
            if (firstName) return firstName;
            if (lastName)  return lastName;
            return 'Игрок';
        }
    }).filter(name => name && name !== 'Игрок' && name !== '?').join('/') || 'TBD';
}

function getCourtStatus(court) {
    const eventState = court.event_state?.toLowerCase();
    if (eventState === 'finished') return 'finished';
    if ((court.first_participant && court.first_participant.length > 0) ||
        (court.current_first_participant && court.current_first_participant.length > 0)) return 'playing';
    if (court.next_first_participant && court.next_first_participant.length > 0) return 'scheduled';
    return 'free';
}

function getCourtStatusText(court) {
    const statusMap = { playing: 'Играет', finished: 'Завершен', scheduled: 'Запланирован', free: 'Свободен' };
    return statusMap[getCourtStatus(court)] || 'Неизвестно';
}

function getStatusText(status) {
    const statusMap = { active: 'Активный', finished: 'Завершен', pending: 'Ожидание' };
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
        return new Date(dateTimeString).toLocaleString('ru-RU', {
            day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
        });
    } catch (e) {
        return dateTimeString;
    }
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

// === НАСТРОЙКИ ===
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        if (!response.ok) throw new Error('Ошибка загрузки настроек с сервера');
        const settings = await response.json();
        localStorage.setItem('vmixSettings', JSON.stringify(settings));
        applySettings(settings);
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
        // Fallback — из localStorage
        const saved = localStorage.getItem('vmixSettings');
        if (saved) {
            try { applySettings(JSON.parse(saved)); } catch (e) {
                console.error('Ошибка из localStorage:', e);
            }
        }
    }
}

function applySettings(settings) {
    refreshInterval = (settings.refreshInterval || 30) * 1000;

    const el = id => document.getElementById(id);
    if (el('refreshIntervalInput'))   el('refreshIntervalInput').value   = settings.refreshInterval || 30;
    if (el('autoRefreshEnabled'))     el('autoRefreshEnabled').checked   = settings.autoRefresh !== false;
    if (el('debugMode'))              el('debugMode').checked             = settings.debugMode || false;
    if (el('themeSelect'))            el('themeSelect').value             = settings.theme || 'light';
    if (el('finishedMatchesCount'))   el('finishedMatchesCount').value   = settings.finishedMatchesCount || 3;
    if (el('refreshInterval'))        el('refreshInterval').textContent  = settings.refreshInterval || 30;
}

function startAutoRefresh() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
    if (document.getElementById('autoRefreshEnabled')?.checked) {
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (response.status === 401) {
            handleUnauthorized(saveSettingsWithAuth);
            return;
        }

        if (response.ok) {
            localStorage.setItem('vmixSettings', JSON.stringify(settings));
            refreshInterval = settings.refreshInterval * 1000;
            if (document.getElementById('refreshInterval')) {
                document.getElementById('refreshInterval').textContent = settings.refreshInterval;
            }
            if (settings.autoRefresh) startAutoRefresh();
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
    const el = id => document.getElementById(id);
    if (el('totalTournaments')) el('totalTournaments').textContent = tournaments.length;
    if (el('totalCourts'))      el('totalCourts').textContent      = Array.isArray(courts) ? courts.length : 0;
    if (el('lastUpdate'))       el('lastUpdate').textContent       = formatTime(new Date());
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
            headers: { 'Content-Type': 'application/json' }
        });
        const result = await response.json();

        if (response.status === 401 && result.auth_required) {
            handleUnauthorized(() => deleteTournamentWithAuth(id));
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

function toggleAutoRefresh() {
    if (document.getElementById('autoRefreshEnabled').checked) {
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
        await Promise.all([loadTournaments(), refreshCourts()]);
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
    if (!tournamentId) { showAlert('Выберите турнир', 'warning'); return; }
    window.open(`/composite/${tournamentId}/${pageType}/${slotNumber}`, '_blank');
}

function openCompositeEditor(pageType, slotNumber) {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (!tournamentId) { showAlert('Турнир не найден!', 'warning'); return; }
    if (!isAuthenticated) {
        showAuthModal(() => openCompositeEditor(pageType, slotNumber));
        return;
    }
    window.open(`/composite/editor/${tournamentId}/${pageType}/${slotNumber}`, '_blank');
}

function enableCompositeButtons(enabled) {
    for (let i = 1; i <= 4; i++) {
        const btn     = document.getElementById(`compositeRound${i}Btn`);
        const editBtn = document.getElementById(`compositeRound${i}EditBtn`);
        if (btn)     btn.disabled     = !enabled;
        if (editBtn) editBtn.disabled = !enabled;
    }
    for (let i = 1; i <= 4; i++) {
        const btn     = document.getElementById(`compositeElimination${i}Btn`);
        const editBtn = document.getElementById(`compositeElimination${i}EditBtn`);
        if (btn)     btn.disabled     = !enabled;
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
        if (document.getElementById('autoRefreshEnabled')?.checked) {
            startAutoRefresh(); // startAutoRefresh сам делает clearInterval перед запуском
        }
    }
}

// === МЕДИА ===
async function loadMediaImages() {
    try {
        const response = await fetch('/api/media/images');
        if (response.status === 401) {
            handleUnauthorized(loadMediaImages);
            return;
        }
        if (!response.ok) throw new Error('Failed to load media list');
        mediaImages = await response.json();
        renderMediaList();
    } catch (error) {
        console.error('Load media error:', error);
        showAlert('Ошибка загрузки списка изображений', 'danger');
    }
}

function renderMediaList() {
    const container   = document.getElementById('mediaList');
    const count       = document.getElementById('mediaCount');
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
                <img src="${item.url}" class="card-img-top" alt="${escapeHtml(item.name)}" style="height:180px;object-fit:cover;">
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
            const response = await fetch('/api/media/images', { method: 'POST', body: formData });
            if (response.status === 401) { handleUnauthorized(uploadMediaImage); return; }
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Upload failed');
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
            const response = await fetch(`/api/media/images/${encodeURIComponent(name)}`, { method: 'DELETE' });
            if (response.status === 401) { handleUnauthorized(() => deleteMediaImage(encodedName)); return; }
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Delete failed');
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
            if (response.status === 401) { handleUnauthorized(() => renameMediaImage(encodedName)); return; }
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Rename failed');
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
