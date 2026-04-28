const BASE_WIDTH  = 1920;
const BASE_HEIGHT = 1080;

function scaleToFit() {
    const container = document.getElementById('compositeContainer');
    if (!container) return;

    const scaleX = window.innerWidth  / BASE_WIDTH;
    const scaleY = window.innerHeight / BASE_HEIGHT;
    const scale  = Math.min(scaleX, scaleY);

    const offsetX = (window.innerWidth  - BASE_WIDTH  * scale) / 2;
    const offsetY = (window.innerHeight - BASE_HEIGHT * scale) / 2;

    container.style.transform = `scale(${scale})`;
    container.style.left      = `${offsetX}px`;
    container.style.top       = `${offsetY}px`;
}

window.addEventListener('resize', scaleToFit);
scaleToFit();
