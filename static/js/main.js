// static/js/main.js
// Глобальные переменные
let tournaments = [];
let courts = [];
let xmlFiles = [];
let currentTournamentId = null;
let autoRefreshTimer = null;
let refreshInterval = 30000; // 30 секунд
let isAuthenticated = false;
let currentUsername = '';
let pendingAuthAction = null;

// Инициализация приложения
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
    document.getElementById('tournamentForm').addEventListener('submit', handleTournamentSubmit);
    document.getElementById('xmlTournamentSelect').addEventListener('change', updateXMLTypes);
    document.getElementById('refreshIntervalInput').addEventListener('change', updateRefreshInterval);
    document.getElementById('autoRefreshEnabled').addEventListener('change', toggleAutoRefresh);
    document.getElementById('themeSelect').addEventListener('change', handleThemeChange);

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
    
    if (authenticated && currentUsername) {
        authUserInfo.style.display = 'flex';
        currentUsernameSpan.textContent = currentUsername;
    } else {
        authUserInfo.style.display = 'none';
    }
}

function showAuthModal(callback) {
    // Показывает модальное окно авторизации
    pendingAuthAction = callback;
    document.getElementById('authOverlay').style.display = 'flex';
}

function closeAuthModal() {
    // Закрывает модальное окно авторизации
    document.getElementById('authOverlay').style.display = 'none';
    document.getElementById('authForm').reset();
    pendingAuthAction = null;
}

async function performLogin(username, password) {
    // Выполняет авторизацию
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
    // Выход из системы
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

function requireAuth(action) {
    // Проверяет аутентификацию перед выполнением действия
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

    // Проверяем аутентификацию
    if (!isAuthenticated) {
        showAuthModal(() => loadTournamentWithAuth(tournamentId));
        return;
    }
    
    loadTournamentWithAuth(tournamentId);
}

async function loadTournamentWithAuth(tournamentId) {
    // Загружает турнир с аутентификацией
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

function renderCourts() {
    const container = document.getElementById('courtGrid');
    const countBadge = document.getElementById('courtCount');
    
    // Проверяем, что courts является массивом
    if (!Array.isArray(courts)) {
        console.error('Courts data is not an array:', courts);
        
        // Если courts содержит ошибку
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
        
        // Информация о следующем матче
        const hasNextMatch = court.next_first_participant && court.next_first_participant.length > 0;
        const nextPlayers1 = court.next_first_participant || [];
        const nextPlayers2 = court.next_second_participant || [];
        const nextClass = court.next_class_name || '';
        const nextStartTime = court.next_start_time || court.next_scheduled_time || '';
        
        return `
            <div class="court-card slide-in">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="mb-0">${court.court_name || `Корт ${court.court_id}`}</h6>
                    <div class="d-flex align-items-center gap-2">
                        <span class="status-badge status-${getCourtStatus(court)}">
                            ${getCourtStatusText(court)}
                        </span>
                        ${court.sport ? `<small class="text-muted">${court.sport}</small>` : ''}
                    </div>
                </div>
                
                ${currentClass ? `
                    <div class="mb-2">
                        <small class="text-muted">
                            <i class="fas fa-trophy me-1"></i>${currentClass}
                        </small>
                    </div>
                ` : ''}
                
                ${hasCurrentMatch ? `
                    <div class="mb-3">
                        <div class="d-flex flex-column align-items-center mb-2">
                            <div class="text-truncate mb-1 w-100 text-center">
                                <strong>${formatPlayerNames(currentPlayers1)}</strong>
                            </div> 
                            <div class="text-truncate w-100 text-center">
                                <strong>${formatPlayerNames(currentPlayers2)}</strong>
                            </div>
                        </div>
                        <div class="score-display text-center mb-2">
                            ${currentScore1} - ${currentScore2}
                        </div>
                        ${currentSets && currentSets.length > 0 ? `
                            <div class="text-center">
                                <small class="text-muted">
                                    Сеты: ${currentSets.map(set => 
                                        `${set.firstParticipantScore}-${set.secondParticipantScore}`
                                    ).join(', ')}
                                </small>
                            </div>
                        ` : ''}
                        
                        ${court.current_is_winner_first !== null && court.current_is_winner_first !== undefined ? `
                            <div class="text-center mt-1">
                                <small class="badge ${court.current_is_winner_first ? 'bg-success' : 'bg-warning'}">
                                    ${court.current_is_winner_first ? 'Победа первой команды' : 'Победа второй команды'}
                                </small>
                            </div>
                        ` : ''}
                    </div>
                ` : `
                    <div class="text-center text-muted py-3 mb-3">
                        <i class="fas fa-pause-circle fa-2x mb-2 opacity-50"></i>
                        <p class="mb-0">Корт свободен</p>
                    </div>
                `}
                
                ${hasNextMatch ? `
                    <div class="border-top pt-3 mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <small class="text-primary fw-bold">
                                <i class="fas fa-clock me-1"></i>Следующий матч
                            </small>
                            ${nextStartTime ? `
                                <small class="text-muted">
                                    ${formatDateTime(nextStartTime)}
                                </small>
                            ` : ''}
                        </div>
                        
                        ${nextClass ? `
                            <div class="mb-2">
                                <small class="text-muted">
                                    <i class="fas fa-trophy me-1"></i>${nextClass}
                                </small>
                            </div>
                        ` : ''}
                        
                        <div class="small">
                            <div class="mb-1">
                                <strong>${formatPlayerNames(nextPlayers1)}</strong>
                            </div>
                            <div class="text-center my-1">
                                <span class="text-muted">vs</span>
                            </div>
                            <div>
                                <strong>${formatPlayerNames(nextPlayers2)}</strong>
                            </div>
                        </div>
                    </div>
                ` : ''}
                
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">
                        <i class="fas fa-sync me-1"></i>Обновлено: ${formatTime(new Date())}
                    </small>
					<div class="d-flex gap-1">
						${hasCurrentMatch || hasNextMatch ? `
							<button class="btn btn-sm btn-outline-primary" onclick="generateCourtXML('${court.court_id}')">
								<i class="fas fa-code me-1"></i>XML
							</button>
							<button class="btn btn-sm btn-warning" onclick="openCourtHTML('${currentTournamentId}', '${court.court_id}')" title="HTML Scoreboard">
								<i class="fas fa-tv"></i>
							</button>
						` : ''}
						<button class="btn btn-sm btn-outline-info" onclick="refreshSingleCourt('${court.court_id}')">
							<i class="fas fa-sync-alt"></i>
						</button>
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
					<small class="text-muted">
						<i class="fas fa-info-circle me-1"></i>
						Используйте эту ссылку в vMix для получения актуальных данных
					</small>
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
            </ol>
        </div>
    `;
}

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

function openCourtHTML(tournamentId, courtId) {
    // Открываем Live HTML scoreboard в новом окне
    const liveUrl = `/api/html-live/${tournamentId}/${courtId}`;
    window.open(liveUrl, '_blank', 'width=390,height=90,resizable=no,scrollbars=no,menubar=no,toolbar=no');
}

function generateCourtHTML(tournamentId, courtId) {
    // Генерируем статический HTML файл
    showLoading(true);
    
    fetch(`/api/html/${tournamentId}/${courtId}`)
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        })
        .then(fileInfo => {
            showAlert(`HTML Scoreboard создан: ${fileInfo.filename}`, 'success');
            
            // Предлагаем открыть файл
            const openFile = confirm('Открыть созданный HTML файл?');
            if (openFile) {
                window.open(fileInfo.url, '_blank', 'width=390,height=90,resizable=no,scrollbars=no,menubar=no,toolbar=no');
            }
        })
        .catch(error => {
            showAlert(`Ошибка создания HTML: ${error.message}`, 'danger');
        })
        .finally(() => {
            showLoading(false);
        });
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
    const generateAllBtn = document.getElementById('generateAllBtn');
    const testAllBtn = document.getElementById('testAllBtn');
    
    if (!tournamentId) {
        if (showLiveXMLBtn) showLiveXMLBtn.disabled = true;
        if (generateAllBtn) generateAllBtn.disabled = true;
        if (testAllBtn) testAllBtn.disabled = true;
        
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
    if (generateAllBtn) generateAllBtn.disabled = false;
    if (testAllBtn) testAllBtn.disabled = false;
    
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

function formatPlayerNames(players) {
    if (!players || players.length === 0) return 'Неизвестные игроки';
    
    return players.map(p => {
        const firstName = (p.firstName || '').trim();
        const lastName = (p.lastName || '').trim();
        
        if (firstName && lastName) {
            return `${firstName} ${lastName}`;
        } else if (firstName) {
            return firstName;
        } else if (lastName) {
            return lastName;
        } else {
            return 'Игрок';
        }
    }).filter(name => name && name !== 'Игрок').join(' / ') || 'Неизвестные игроки';
}


function getCourtStatus(court) {
    // Проверяем статус корта из API
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
        
        // Обновляем только данные конкретного корта
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

// Остальные функции для совместимости (заглушки)
function loadSettings() {
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
            }
        } catch (error) {
            console.error('Ошибка загрузки настроек:', error);
        }
    }
    
    if (document.getElementById('refreshInterval')) {
        document.getElementById('refreshInterval').textContent = refreshInterval / 1000;
    }
}


    // Реализация автообновления
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
    // Сохраняет настройки с аутентификацией
    const settings = {
        refreshInterval: parseInt(document.getElementById('refreshIntervalInput').value),
        autoRefresh: document.getElementById('autoRefreshEnabled').checked,
        debugMode: document.getElementById('debugMode').checked,
        theme: document.getElementById('themeSelect').value,
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

    // Реализация обновления системной информации
function updateSystemInfo() {
    if (document.getElementById('totalTournaments')) {
        document.getElementById('totalTournaments').textContent = tournaments.length;
    }
    if (document.getElementById('totalCourts')) {
        document.getElementById('totalCourts').textContent = courts.length;
    }
    if (document.getElementById('totalXMLFiles')) {
        document.getElementById('totalXMLFiles').textContent = xmlFiles.length;
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
    // Удаляет турнир с аутентификацией
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
        // Используем правильный endpoint для генерации XML корта
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

async function testAllLiveXML() {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (!tournamentId) {
        showAlert('Выберите турнир для тестирования', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`/api/tournament/${tournamentId}/live-xml-info`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const liveXMLInfo = await response.json();
        
        if (!liveXMLInfo.live_xml_types || liveXMLInfo.live_xml_types.length === 0) {
            showAlert('Нет доступных Live XML для тестирования', 'info');
            return;
        }
        
        let successCount = 0;
        let errorCount = 0;
        
        for (const xmlType of liveXMLInfo.live_xml_types) {
            try {
                const testResponse = await fetch(xmlType.live_url);
                if (testResponse.ok) {
                    successCount++;
                } else {
                    errorCount++;
                }
            } catch (error) {
                errorCount++;
            }
        }
        
        if (errorCount === 0) {
            showAlert(`Все Live XML работают корректно! (${successCount}/${successCount})`, 'success');
        } else {
            showAlert(`Результат тестирования: ${successCount} работают, ${errorCount} с ошибками`, 'warning');
        }
                      
    } catch (error) {
        console.error('Test all live XML error:', error);
        showAlert(`Ошибка тестирования Live XML: ${error.message}`, 'danger');
    } finally {
        showLoading(false);
    }
}

function generateAllXMLForTournament() {
    const tournamentId = document.getElementById('xmlTournamentSelect').value;
    if (tournamentId) {
        generateAllXML(tournamentId);
    } else {
        showAlert('Выберите турнир для генерации статических XML', 'warning');
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
        
        // Перезапуск автообновления с новым интервалом
        if (document.getElementById('autoRefreshEnabled') && document.getElementById('autoRefreshEnabled').checked) {
            if (autoRefreshTimer) {
                clearInterval(autoRefreshTimer);
            }
            startAutoRefresh();
        }
    }
}