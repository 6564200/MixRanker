/**
 * JavaScript для редактора композитных страниц
 */

// Глобальные переменные (инициализируются из HTML)
let tournamentId, pageType, slotNumber;
let layers = [];
let backgroundUrl = '';
let availablePages = { round_robin: [], elimination: [] };
let selectedLayerIndex = -1;
let isDragging = false;
let dragOffset = { x: 0, y: 0 };

/**
 * Инициализация редактора
 */
function initCompositeEditor(config) {
    console.log('initCompositeEditor called with config:', config);
    tournamentId = config.tournamentId;
    pageType = config.pageType;
    slotNumber = config.slotNumber;
    layers = config.layers || [];
    
    // Автоматически формируем URL фона на основе типа страницы и слота
    backgroundUrl = `/composite/bg/${pageType}/${slotNumber}/${tournamentId}`;
    
    console.log('Editor initialized, layers:', layers.length);
    
    loadAvailablePages();
    renderLayers();
    updateBackground();
    scalePreview();
    window.addEventListener('resize', scalePreview);
}

/**
 * Масштабирование предпросмотра
 */
function scalePreview() {
    const wrapper = document.getElementById('previewWrapper');
    const frame = document.getElementById('previewFrame');
    
    if (!wrapper || !frame) return;
    
    const wrapperWidth = wrapper.clientWidth;
    const wrapperHeight = wrapper.clientHeight;
    
    const scaleX = wrapperWidth / 1920;
    const scaleY = wrapperHeight / 1080;
    const scale = Math.min(scaleX, scaleY) * 0.95;
    
    const offsetX = (wrapperWidth - 1920 * scale) / 2;
    const offsetY = (wrapperHeight - 1080 * scale) / 2;
    
    frame.style.transform = `scale(${scale})`;
    frame.style.left = `${offsetX}px`;
    frame.style.top = `${offsetY}px`;
    
    document.getElementById('previewScale').textContent = Math.round(scale * 100) + '%';
}

/**
 * Загрузка доступных страниц
 */
async function loadAvailablePages() {
    try {
        const response = await fetch(`/api/composite/available-pages/${tournamentId}`);
        availablePages = await response.json();
        renderAvailablePages();
    } catch (error) {
        console.error('Error loading available pages:', error);
    }
}

/**
 * Рендер списков доступных страниц
 */
function renderAvailablePages() {
    const rrList = document.getElementById('roundRobinList');
    const elList = document.getElementById('eliminationList');
    
    if (availablePages.round_robin.length === 0) {
        rrList.innerHTML = '<p class="text-muted small">Нет доступных групп</p>';
    } else {
        rrList.innerHTML = availablePages.round_robin.map(p => `
            <button class="list-group-item list-group-item-action" onclick="selectPage('${p.url}')">
                <i class="fas fa-table me-2"></i>${p.name}
            </button>
        `).join('');
    }
    
    if (availablePages.elimination.length === 0) {
        elList.innerHTML = '<p class="text-muted small">Нет доступных сеток</p>';
    } else {
        elList.innerHTML = availablePages.elimination.map(p => `
            <button class="list-group-item list-group-item-action" onclick="selectPage('${p.url}')">
                <i class="fas fa-sitemap me-2"></i>${p.name}
            </button>
        `).join('');
    }
}

/**
 * Обновление фона
 */
function updateBackground() {
    const bgContainer = document.getElementById('previewBackground');
    bgContainer.innerHTML = `<iframe src="${backgroundUrl}" allowtransparency="true"></iframe>`;
}

/**
 * Выбор страницы из модального окна
 */
function selectPage(url) {
    const target = document.getElementById('selectPageTarget').value;
    
    if (target.startsWith('layer_')) {
        const index = parseInt(target.split('_')[1]);
        if (layers[index]) {
            layers[index].url = url;
            renderLayers();
        }
    }
    
    bootstrap.Modal.getInstance(document.getElementById('selectPageModal')).hide();
}

/**
 * Добавление слоя
 */
/**
 * Добавление слоя
 */
function addLayer() {
    console.log('addLayer called, current layers:', layers.length);
    layers.push({
        url: '',
        x: 100 + layers.length * 50,
        y: 100 + layers.length * 50,
        width: 600,
        height: 400,
        scale: 0.5
    });
    console.log('Layer added, new count:', layers.length);
    renderLayers();
    selectLayer(layers.length - 1);
}

/**
 * Удаление слоя
 */
function removeLayer(index) {
    layers.splice(index, 1);
    selectedLayerIndex = -1;
    renderLayers();
}

/**
 * Выбор слоя
 */
function selectLayer(index) {
    selectedLayerIndex = index;
    renderLayers();
}

/**
 * Рендер слоёв
 */
function renderLayers() {
    const list = document.getElementById('layersList');
    
    if (layers.length === 0) {
        list.innerHTML = `
            <p class="text-muted small text-center py-3">
                Нет слоёв. Нажмите "Добавить" для создания.
            </p>
        `;
    } else {
        list.innerHTML = layers.map((layer, idx) => `
            <div class="card layer-card mb-2 ${idx === selectedLayerIndex ? 'selected' : ''}" data-index="${idx}">
                <div class="card-header d-flex align-items-center" onclick="selectLayer(${idx})">
                    <i class="fas fa-grip-vertical layer-handle me-2"></i>
                    <span class="flex-grow-1 small">Слой ${idx + 1}</span>
                    <button class="btn btn-outline-danger btn-sm py-0 px-1" onclick="event.stopPropagation(); removeLayer(${idx})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="card-body py-2 px-2" style="display: ${idx === selectedLayerIndex ? 'block' : 'none'}">
                    <div class="mb-2">
                        <label class="form-label small mb-0">URL</label>
                        <div class="input-group input-group-sm">
                            <input type="text" class="form-control" value="${layer.url || ''}" 
                                   onchange="updateLayerProp(${idx}, 'url', this.value)">
                            <button class="btn btn-outline-secondary" type="button" onclick="openPageSelector(${idx})">
                                <i class="fas fa-list"></i>
                            </button>
                        </div>
                    </div>
                    <div class="row g-2 mb-2">
                        <div class="col-6">
                            <label class="form-label small mb-0">X</label>
                            <input type="number" class="form-control form-control-sm" value="${layer.x}" 
                                   onchange="updateLayerProp(${idx}, 'x', Number(this.value))">
                        </div>
                        <div class="col-6">
                            <label class="form-label small mb-0">Y</label>
                            <input type="number" class="form-control form-control-sm" value="${layer.y}" 
                                   onchange="updateLayerProp(${idx}, 'y', Number(this.value))">
                        </div>
                    </div>
                    <div class="row g-2 mb-2">
                        <div class="col-6">
                            <label class="form-label small mb-0">Ширина</label>
                            <input type="number" class="form-control form-control-sm" value="${layer.width}" 
                                   onchange="updateLayerProp(${idx}, 'width', Number(this.value))">
                        </div>
                        <div class="col-6">
                            <label class="form-label small mb-0">Высота</label>
                            <input type="number" class="form-control form-control-sm" value="${layer.height}" 
                                   onchange="updateLayerProp(${idx}, 'height', Number(this.value))">
                        </div>
                    </div>
                    <div class="mb-1">
                        <label class="form-label small mb-0">Масштаб: ${(layer.scale * 100).toFixed(0)}%</label>
                        <input type="range" class="form-range" min="0.1" max="2" step="0.05" value="${layer.scale}" 
                               oninput="updateLayerProp(${idx}, 'scale', Number(this.value))">
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    // Превью слоёв
    const preview = document.getElementById('previewLayers');
    preview.innerHTML = layers.map((layer, idx) => `
        <div class="preview-layer ${idx === selectedLayerIndex ? 'selected' : ''}" 
             data-index="${idx}"
             style="left: ${layer.x}px; top: ${layer.y}px; width: ${layer.width}px; height: ${layer.height}px;"
             onmousedown="startDrag(event, ${idx})">
            <div class="layer-label">Слой ${idx + 1}</div>
            ${layer.url ? `
                <iframe src="${layer.url}" allowtransparency="true"
                        style="width: ${layer.width / layer.scale}px; height: ${layer.height / layer.scale}px; transform: scale(${layer.scale});"></iframe>
            ` : `
                <div style="width:100%;height:100%;background:rgba(100,100,100,0.3);display:flex;align-items:center;justify-content:center;color:#fff;">
                    <i class="fas fa-plus fa-2x"></i>
                </div>
            `}
        </div>
    `).join('');
}

/**
 * Обновление свойства слоя
 */
function updateLayerProp(index, prop, value) {
    if (layers[index]) {
        layers[index][prop] = value;
        renderLayers();
    }
}

/**
 * Открытие модального окна выбора страницы
 */
function openPageSelector(index) {
    document.getElementById('selectPageTarget').value = `layer_${index}`;
    new bootstrap.Modal(document.getElementById('selectPageModal')).show();
}

/**
 * Начало перетаскивания слоя
 */
function startDrag(event, index) {
    if (event.button !== 0) return;
    
    isDragging = true;
    selectedLayerIndex = index;
    
    const layer = layers[index];
    const previewFrame = document.getElementById('previewFrame');
    const scale = previewFrame.getBoundingClientRect().width / 1920;
    
    dragOffset.x = event.clientX - layer.x * scale;
    dragOffset.y = event.clientY - layer.y * scale;
    
    document.addEventListener('mousemove', onDrag);
    document.addEventListener('mouseup', stopDrag);
    
    renderLayers();
    event.preventDefault();
}

/**
 * Перетаскивание слоя
 */
function onDrag(event) {
    if (!isDragging || selectedLayerIndex < 0) return;
    
    const previewFrame = document.getElementById('previewFrame');
    const rect = previewFrame.getBoundingClientRect();
    const scale = rect.width / 1920;
    
    let newX = (event.clientX - dragOffset.x) / scale;
    let newY = (event.clientY - dragOffset.y) / scale;
    
    // Ограничиваем границами
    newX = Math.max(0, Math.min(1920 - layers[selectedLayerIndex].width, newX));
    newY = Math.max(0, Math.min(1080 - layers[selectedLayerIndex].height, newY));
    
    layers[selectedLayerIndex].x = Math.round(newX);
    layers[selectedLayerIndex].y = Math.round(newY);
    
    // Обновляем только позицию элемента для производительности
    const layerEl = document.querySelector(`.preview-layer[data-index="${selectedLayerIndex}"]`);
    if (layerEl) {
        layerEl.style.left = `${layers[selectedLayerIndex].x}px`;
        layerEl.style.top = `${layers[selectedLayerIndex].y}px`;
    }
}

/**
 * Завершение перетаскивания
 */
function stopDrag() {
    isDragging = false;
    document.removeEventListener('mousemove', onDrag);
    document.removeEventListener('mouseup', stopDrag);
    renderLayers();
}

/**
 * Сохранение композитной страницы
 */
async function saveComposite() {
    const data = {
        background_settings: { url: backgroundUrl },
        layers: layers
    };
    
    try {
        const response = await fetch(`/api/composite/page/${tournamentId}/${pageType}/${slotNumber}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) throw new Error('Ошибка сохранения');
        
        alert('Сохранено!');
    } catch (error) {
        console.error('Save error:', error);
        alert('Ошибка сохранения: ' + error.message);
    }
}
