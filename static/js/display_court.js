/**
 * Display Court - Р»РѕРіРёРєР° Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРѕРіРѕ/СЂСѓС‡РЅРѕРіРѕ СЂРµР¶РёРјР°
 */

(function() {
    'use strict';

    const CONFIG = {
        checkInterval: 1000,      // РџСЂРѕРІРµСЂРєР° СЃРѕСЃС‚РѕСЏРЅРёСЏ РєР°Р¶РґС‹Рµ 2 СЃРµРє
        fadeTime: 250             // Р’СЂРµРјСЏ fade СЌС„С„РµРєС‚Р° (РјСЃ)
    };

    let slotNumber = null;
    let tournamentId = null;
    let courtId = null;
    let mode = 'auto';
    let currentPage = null;
    let currentState = null;
    let checkTimer = null;
    let loadRequestId = 0;

    /**
     * РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ
     */
    function init() {
        const container = document.querySelector('.display-container');
        if (!container) {
            console.error('Display container not found');
            return;
        }

        slotNumber = parseInt(container.dataset.slot);
        tournamentId = container.dataset.tournamentId;
        courtId = container.dataset.courtId;
        mode = container.dataset.mode || 'auto';
        applyPlaceholderImage(container.dataset.placeholderUrl);

        console.log(`Display Court ${slotNumber}: initialized, tournament=${tournamentId}, court=${courtId}, mode=${mode}`);

        // РџРµСЂРІР°СЏ РїСЂРѕРІРµСЂРєР°
        checkState();
        
        // РџРµСЂРёРѕРґРёС‡РµСЃРєР°СЏ РїСЂРѕРІРµСЂРєР° СЃРѕСЃС‚РѕСЏРЅРёСЏ
        checkTimer = setInterval(checkState, CONFIG.checkInterval);
    }

    /**
     * РџСЂРѕРІРµСЂРєР° СЃРѕСЃС‚РѕСЏРЅРёСЏ РєРѕСЂС‚Р°
     */
    async function checkState() {
        try {
            const response = await fetch(`/api/display/court/${slotNumber}/state`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            applyPlaceholderImage(data.placeholder_url);
            
            // РћР±РЅРѕРІР»СЏРµРј СЂРµР¶РёРј РµСЃР»Рё РёР·РјРµРЅРёР»СЃСЏ
            if (data.mode && data.mode !== mode) {
                mode = data.mode;
                console.log(`Mode changed to: ${mode}`);
            }
            
            // Р’ СЂСѓС‡РЅРѕРј СЂРµР¶РёРјРµ РёСЃРїРѕР»СЊР·СѓРµРј manual_page
            if (mode === 'manual' && data.manual_page) {
                handleManualMode(data);
                return;
            }
            
            // Р’ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРѕРј СЂРµР¶РёРјРµ
            handleAutoMode(data);
            
        } catch (error) {
            console.error('Failed to check state:', error);
        }
    }

    /**
     * РћР±СЂР°Р±РѕС‚РєР° Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРѕРіРѕ СЂРµР¶РёРјР°
     */
    function handleAutoMode(data) {
        const newState = data.state;
        const newPage = data.page;
        const newUrl = data.url;
        
        // РџРѕРєР°Р·С‹РІР°РµРј Р·Р°РіР»СѓС€РєСѓ РµСЃР»Рё РєРѕСЂС‚ РїСѓСЃС‚
        if (newPage === 'empty' || newState === 'empty' || newState === 'not_configured') {
            showEmptyState();
            currentPage = 'empty';
            currentState = newState;
            return;
        }
        
        // РЎРєСЂС‹РІР°РµРј Р·Р°РіР»СѓС€РєСѓ
        hideEmptyState();
        
        // Р•СЃР»Рё СЃС‚СЂР°РЅРёС†Р° РЅРµ РёР·РјРµРЅРёР»Р°СЃСЊ - РЅРµ РїРµСЂРµР·Р°РіСЂСѓР¶Р°РµРј
        if (newPage === currentPage && newState === currentState) {
            return;
        }
        
        console.log(`State changed: ${currentState} -> ${newState}, page: ${currentPage} -> ${newPage}`);

        currentPage = newPage;
        currentState = newState;

        if (newUrl) {
            loadPage(newUrl);
        }
    }

    /**
     * РћР±СЂР°Р±РѕС‚РєР° СЂСѓС‡РЅРѕРіРѕ СЂРµР¶РёРјР°
     */
    function handleManualMode(data) {
        const manualPage = data.manual_page;
        
        // Р•СЃР»Рё СЃС‚СЂР°РЅРёС†Р° РЅРµ РёР·РјРµРЅРёР»Р°СЃСЊ
        if (manualPage === currentPage && mode === 'manual') {
            return;
        }
        
        // Р—Р°РіР»СѓС€РєР° - РїРѕРєР°Р·С‹РІР°РµРј empty state
        if (manualPage === 'empty') {
            showEmptyState();
            currentPage = 'empty';
            return;
        }
        
        hideEmptyState();
        
        // РџРѕР»СѓС‡Р°РµРј РЅР°СЃС‚СЂРѕР№РєРё РѕРєРЅР° РґР»СЏ tournament_id, court_id Рё custom_url
        fetchWindowConfig().then(window => {
            if (!window) {
                console.log('No window config');
                showEmptyState();
                return;
            }
            
            // РџСЂРѕРёР·РІРѕР»СЊРЅС‹Р№ URL
            if (manualPage === 'custom') {
                const customUrl = window.settings?.custom_url;
                if (customUrl) {
                    currentPage = 'custom';
                    loadPage(customUrl);
                } else {
                    console.log('No custom URL configured');
                    showEmptyState();
                }
                return;
            }
            
            // РЎС‚Р°РЅРґР°СЂС‚РЅС‹Рµ СЃС‚СЂР°РЅРёС†С‹ - С‚СЂРµР±СѓСЋС‚ tournament_id Рё court_id
            if (!window.tournament_id || !window.court_id) {
                console.log('No tournament/court configured');
                showEmptyState();
                return;
            }
            
            const pageUrls = {
                'vs': `/api/html-live/${window.tournament_id}/${window.court_id}/vs`,
                'scoreboard': `/api/html-live/${window.tournament_id}/${window.court_id}/score_full`,
                'winner': `/api/html-live/${window.tournament_id}/${window.court_id}/winner`,
                'introduction': `/api/html-live/${window.tournament_id}/${window.court_id}/introduction`
            };
            
            const url = pageUrls[manualPage];
            if (url) {
                currentPage = manualPage;
                loadPage(url);
            }
        });
    }

    /**
     * РџРѕР»СѓС‡РµРЅРёРµ РєРѕРЅС„РёРіСѓСЂР°С†РёРё РѕРєРЅР°
     */
    async function fetchWindowConfig() {
        try {
            const response = await fetch(`/api/display/window/court/${slotNumber}`);
            if (!response.ok) return null;
            const window = await response.json();
            applyPlaceholderImage(window.placeholder_url);
            return window;
        } catch (error) {
            console.error('Failed to fetch window config:', error);
            return null;
        }
    }

    function applyPlaceholderImage(url) {
        if (!url) return;
        const emptyImage = document.querySelector('.empty-state .empty-image');
        if (emptyImage && emptyImage.getAttribute('src') !== url) {
            emptyImage.setAttribute('src', url);
        }
    }

    function setPlaceholderVisible(visible) {
        const emptyState = document.querySelector('.empty-state');
        if (!emptyState) return;

        if (visible) {
            emptyState.style.display = 'flex';
            void emptyState.offsetHeight;
            emptyState.style.opacity = '1';
            return;
        }

        emptyState.style.opacity = '0';
        setTimeout(() => {
            if (emptyState.style.opacity === '0') {
                emptyState.style.display = 'none';
            }
        }, CONFIG.fadeTime);
    }

    /**
     * РџРѕРєР°Р·Р°С‚СЊ Р·Р°РіР»СѓС€РєСѓ СЃ fade СЌС„С„РµРєС‚РѕРј
     */
    function showEmptyState() {
        const emptyState = document.querySelector('.empty-state');
        const content = document.querySelector('.display-content');
        
        if (!emptyState) return;
        
        // Р•СЃР»Рё Р·Р°РіР»СѓС€РєР° СѓР¶Рµ РїРѕРєР°Р·Р°РЅР° - РЅРёС‡РµРіРѕ РЅРµ РґРµР»Р°РµРј
        if (emptyState.style.display === 'flex' && emptyState.style.opacity === '1') {
            return;
        }

        if (content) content.style.display = 'none';
        setPlaceholderVisible(true);
    }

    /**
     * РЎРєСЂС‹С‚СЊ Р·Р°РіР»СѓС€РєСѓ СЃ fade СЌС„С„РµРєС‚РѕРј
     */
    function hideEmptyState() {
        const emptyState = document.querySelector('.empty-state');
        const content = document.querySelector('.display-content');
        
        if (!emptyState || emptyState.style.display === 'none') {
            if (content) {
                content.style.display = 'block';
                content.style.opacity = '1';
            }
            return;
        }
        
        setPlaceholderVisible(false);
        if (content) {
            content.style.display = 'block';
            content.style.opacity = '1';
        }
    }

    /**
     * Р—Р°РіСЂСѓР·РєР° СЃС‚СЂР°РЅРёС†С‹ РІ iframe СЃ fade СЌС„С„РµРєС‚РѕРј
     */
    function loadPage(url) {
        const iframe = document.getElementById('display-frame');
        const content = document.querySelector('.display-content');
        
        if (!iframe) return;
        
        console.log(`Loading page: ${url}`);

        if (content) {
            content.style.display = 'block';
            content.style.opacity = '0';
        }

        const requestId = ++loadRequestId;

        setTimeout(() => {
            if (requestId !== loadRequestId) return;
            iframe.src = url;
        }, CONFIG.fadeTime);

        iframe.onload = () => {
            if (requestId !== loadRequestId) return;
            setTimeout(() => {
                if (content) {
                    content.style.opacity = '1';
                }
            }, 50);
        };
    }

    /**
     * РћС‡РёСЃС‚РєР° РїСЂРё Р·Р°РєСЂС‹С‚РёРё
     */
    function cleanup() {
        if (checkTimer) {
            clearInterval(checkTimer);
            checkTimer = null;
        }
    }

    // РђРІС‚РѕРїР°СѓР·Р° РїСЂРё СЃРєСЂС‹С‚РёРё РІРєР»Р°РґРєРё
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            if (checkTimer) {
                clearInterval(checkTimer);
                checkTimer = null;
            }
        } else {
            checkState();
            checkTimer = setInterval(checkState, CONFIG.checkInterval);
        }
    });

    // РћС‡РёСЃС‚РєР° РїСЂРё Р·Р°РєСЂС‹С‚РёРё
    window.addEventListener('beforeunload', cleanup);

    // Р—Р°РїСѓСЃРє
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Р­РєСЃРїРѕСЂС‚ РґР»СЏ РѕС‚Р»Р°РґРєРё
    window.DisplayCourt = { 
        checkState, 
        loadPage,
        showEmptyState,
        hideEmptyState
    };
})();

