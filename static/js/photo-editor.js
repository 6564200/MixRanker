// photo-editor.js - Простой редактор фото

const photoEditor = {
    canvas: null,
    img: null,
    file: null,
    
    // Позиция и размеры изображения в пикселях превью
    x: 0,
    y: 0,
    width: 0,
    height: 0,
    
    // Оригинальные размеры изображения
    naturalWidth: 0,
    naturalHeight: 0,
    
    // Начальные размеры (при zoom 100%)
    initWidth: 0,
    initHeight: 0,
    
    // Drag
    dragging: false,
    startX: 0,
    startY: 0,
    startImgX: 0,
    startImgY: 0,
    
    // Размеры области превью
    previewW: 375,
    previewH: 512,
    
    // Выходные размеры
    outputW: 1500,
    outputH: 2048,
    
    eventsReady: false,
    
    init(container, imageSrc) {
        console.log('photoEditor.init called');
        this.file = null;
        this.x = 0;
        this.y = 0;
        this.width = 0;
        this.height = 0;
        this.initWidth = 0;
        this.initHeight = 0;
        this.naturalWidth = 0;
        this.naturalHeight = 0;
        
        container.innerHTML = `
            <div class="photo-editor-canvas" id="peCanvas">
                <img id="peImage" src="${imageSrc}" draggable="false">
                <img class="silhouette-overlay" src="/static/images/silhouette.png" draggable="false">
                <div class="crop-frame"></div>
            </div>
        `;
        
        this.canvas = document.getElementById('peCanvas');
        this.img = document.getElementById('peImage');
        
        this.img.onload = () => {
            console.log('Image loaded:', this.img.naturalWidth, 'x', this.img.naturalHeight);
            this.naturalWidth = this.img.naturalWidth;
            this.naturalHeight = this.img.naturalHeight;
            
            // Вычисляем размер чтобы покрыть превью (cover)
            const ratioW = this.previewW / this.naturalWidth;
            const ratioH = this.previewH / this.naturalHeight;
            const ratio = Math.max(ratioW, ratioH);
            
            this.initWidth = this.naturalWidth * ratio;
            this.initHeight = this.naturalHeight * ratio;
            
            console.log('initWidth:', this.initWidth, 'initHeight:', this.initHeight);
            
            // Начальные размеры = 100%
            this.width = this.initWidth;
            this.height = this.initHeight;
            
            // Центрируем
            this.x = (this.previewW - this.width) / 2;
            this.y = (this.previewH - this.height) / 2;
            
            this.render();
            this.updateSlider();
        };
        
        // Если картинка уже загружена (из кэша)
        if (this.img.complete && this.img.naturalWidth > 0) {
            console.log('Image already complete, triggering onload manually');
            this.img.onload();
        }
        
        this.setupEvents();
    },
    
    setupEvents() {
        if (this.eventsReady) return;
        this.eventsReady = true;
        
        // Mouse
        document.addEventListener('mousedown', (e) => this.onDown(e));
        document.addEventListener('mousemove', (e) => this.onMove(e));
        document.addEventListener('mouseup', () => this.onUp());
        
        // Touch
        document.addEventListener('touchstart', (e) => this.onTouchDown(e), {passive: false});
        document.addEventListener('touchmove', (e) => this.onTouchMove(e), {passive: false});
        document.addEventListener('touchend', () => this.onUp());
        
        // Wheel
        document.addEventListener('wheel', (e) => this.onScroll(e), {passive: false});
    },
    
    onDown(e) {
        if (!this.canvas || !this.canvas.contains(e.target)) return;
        e.preventDefault();
        this.dragging = true;
        this.startX = e.clientX;
        this.startY = e.clientY;
        this.startImgX = this.x;
        this.startImgY = this.y;
    },
    
    onMove(e) {
        if (!this.dragging) return;
        this.x = this.startImgX + (e.clientX - this.startX);
        this.y = this.startImgY + (e.clientY - this.startY);
        this.render();
    },
    
    onUp() {
        this.dragging = false;
    },
    
    onTouchDown(e) {
        if (!this.canvas || e.touches.length !== 1) return;
        if (!this.canvas.contains(e.touches[0].target)) return;
        e.preventDefault();
        this.dragging = true;
        this.startX = e.touches[0].clientX;
        this.startY = e.touches[0].clientY;
        this.startImgX = this.x;
        this.startImgY = this.y;
    },
    
    onTouchMove(e) {
        if (!this.dragging || e.touches.length !== 1) return;
        e.preventDefault();
        this.x = this.startImgX + (e.touches[0].clientX - this.startX);
        this.y = this.startImgY + (e.touches[0].clientY - this.startY);
        this.render();
    },
    
    onScroll(e) {
        if (!this.canvas || !this.canvas.contains(e.target)) return;
        if (this.initWidth === 0) return;
        e.preventDefault();
        const percent = this.getZoomPercent();
        const delta = e.deltaY > 0 ? -5 : 5;
        this.setZoomPercent(percent + delta);
    },
    
    // Получить текущий зум в процентах (100 = начальный размер)
    getZoomPercent() {
        if (this.initWidth === 0) return 100;
        return Math.round((this.width / this.initWidth) * 100);
    },
    
    // Установить зум в процентах
    setZoomPercent(percent) {
        console.log('setZoomPercent called:', percent, 'initWidth:', this.initWidth, 'width:', this.width);
        if (this.initWidth === 0 || this.width === 0) {
            console.log('setZoomPercent: early return');
            return;
        }
        
        percent = Math.max(50, Math.min(300, percent));
        
        const oldW = this.width;
        const oldH = this.height;
        
        // Новые размеры
        const newW = this.initWidth * (percent / 100);
        const newH = this.initHeight * (percent / 100);
        
        console.log('newW:', newW, 'newH:', newH);
        
        // Центр превью
        const cx = this.previewW / 2;
        const cy = this.previewH / 2;
        
        // Смещаем позицию чтобы центр остался на месте
        this.x = cx - (cx - this.x) * (newW / oldW);
        this.y = cy - (cy - this.y) * (newH / oldH);
        
        this.width = newW;
        this.height = newH;
        
        this.render();
        this.updateSlider();
    },
    
    zoomIn() {
        console.log('zoomIn called, initWidth:', this.initWidth, 'width:', this.width);
        if (this.initWidth === 0) return;
        this.setZoomPercent(this.getZoomPercent() + 10);
    },
    
    zoomOut() {
        console.log('zoomOut called, initWidth:', this.initWidth, 'width:', this.width);
        if (this.initWidth === 0) return;
        this.setZoomPercent(this.getZoomPercent() - 10);
    },
    
    render() {
        if (!this.img) return;
        console.log('render: x:', this.x, 'y:', this.y, 'w:', this.width, 'h:', this.height);
        this.img.style.left = this.x + 'px';
        this.img.style.top = this.y + 'px';
        this.img.style.width = this.width + 'px';
        this.img.style.height = this.height + 'px';
    },
    
    updateSlider() {
        const percent = this.getZoomPercent();
        const slider = document.getElementById('zoomSlider');
        const label = document.getElementById('zoomValue');
        if (slider) slider.value = percent;
        if (label) label.textContent = percent + '%';
    },
    
    // Параметры для сервера
    getCropParams() {
        if (this.naturalWidth === 0) {
            return { x: 0, y: 0, scale: 1, naturalWidth: 0, naturalHeight: 0 };
        }
        
        const ratio = this.outputW / this.previewW;
        const scale = (this.width / this.naturalWidth) * ratio;
        
        return {
            x: Math.round(this.x * ratio),
            y: Math.round(this.y * ratio),
            scale: scale,
            naturalWidth: this.naturalWidth,
            naturalHeight: this.naturalHeight
        };
    },
    
    destroy() {
        this.canvas = null;
        this.img = null;
        this.file = null;
        this.dragging = false;
    }
};