/**
 * Schedule Half Live Updates
 * AJAX обновление половины расписания без перезагрузки страницы.
 * Читает data-half="1|2" из .schedule-container и передаёт ?half=N в API.
 * Базовое разрешение: FHD 1920x1080
 */

(function() {
    'use strict';

    if (window._scheduleHalfLiveInitialized) {
        console.log('Schedule Half Live: already initialized, skipping');
        return;
    }
    window._scheduleHalfLiveInitialized = true;

    const CONFIG = {
        BASE_WIDTH: 1920,
        BASE_HEIGHT: 1080,
        updateInterval: 10000,
        animationDuration: 300,
        retryDelay: 5000
    };

    let container = null;
    let currentVersion = null;
    let tournamentId = null;
    let targetDate = null;
    let halfNum = null;
    let updateTimer = null;
    let isUpdating = false;
    let isInitialized = false;

    function scaleToFit() {
        if (!container) return;
        const scaleX = window.innerWidth / CONFIG.BASE_WIDTH;
        const scaleY = window.innerHeight / CONFIG.BASE_HEIGHT;
        const scale = Math.min(scaleX, scaleY);
        container.style.transform = `scale(${scale})`;
        container.style.transformOrigin = 'top left';
        container.style.position = 'absolute';
        container.style.left = Math.max(0, (window.innerWidth - CONFIG.BASE_WIDTH * scale) / 2) + 'px';
        container.style.top  = Math.max(0, (window.innerHeight - CONFIG.BASE_HEIGHT * scale) / 2) + 'px';
    }

    function init() {
        if (isInitialized) return;
        isInitialized = true;

        container = document.querySelector('.schedule-container');
        if (!container) {
            console.error('Schedule Half Live: container not found');
            return;
        }

        tournamentId  = container.dataset.tournamentId;
        targetDate    = container.dataset.targetDate || null;
        currentVersion = container.dataset.version || null;
        halfNum       = container.dataset.half || null;

        scaleToFit();
        window.addEventListener('resize', scaleToFit);

        if (!tournamentId) {
            console.error('Schedule Half Live: tournament ID not found');
            return;
        }

        console.log(`Schedule Half Live: tournament=${tournamentId} half=${halfNum} version=${currentVersion}`);
        startUpdates();
    }

    function startUpdates() {
        if (updateTimer) clearInterval(updateTimer);
        setTimeout(checkForUpdates, 1000);
        updateTimer = setInterval(checkForUpdates, CONFIG.updateInterval);
    }

    async function checkForUpdates() {
        if (isUpdating) return;
        isUpdating = true;
        try {
            let url = `/api/schedule/${tournamentId}/data`;
            const params = [];
            if (targetDate) params.push(`date=${targetDate}`);
            if (halfNum)    params.push(`half=${halfNum}`);
            if (params.length) url += '?' + params.join('&');

            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            if (data.error) { console.error('API error:', data.error); return; }

            if (data.version !== currentVersion) {
                console.log(`Schedule Half Live: updating (${currentVersion} -> ${data.version})`);
                await updateSchedule(data);
                currentVersion = data.version;
            }
        } catch (error) {
            console.error('Update check failed:', error);
        } finally {
            isUpdating = false;
        }
    }

    async function updateSchedule(data) {
        const { time_slots, courts, matches } = data;
        const mainGrid = container.querySelector('.main-grid');
        if (mainGrid) {
            mainGrid.style.opacity = '0';
            mainGrid.style.transition = 'opacity 0.3s ease-out';
        }
        await new Promise(resolve => setTimeout(resolve, 300));
        updateTimeSlots(time_slots);
        updateCourtHeaders(courts);
        rebuildMatches(matches, time_slots, courts);
        if (mainGrid) mainGrid.style.opacity = '1';
    }

    function rebuildMatches(matches, timeSlots, courts) {
        const matchesGrid = document.querySelector('.matches-grid');
        if (!matchesGrid) return;
        matchesGrid.style.gridTemplateRows    = `repeat(${timeSlots.length}, 86px)`;
        matchesGrid.style.gridTemplateColumns = `repeat(${courts.length}, 1fr)`;
        matchesGrid.style.gap = '38px';
        matchesGrid.innerHTML = '';
        matches.forEach(match => matchesGrid.appendChild(createMatchElement(match)));
    }

    function updateTimeSlots(timeSlots) {
        const timeScale = document.querySelector('.time-scale');
        if (!timeScale) return;
        const currentTimes = Array.from(timeScale.querySelectorAll('.time-slot'))
            .map(el => el.textContent.trim());
        if (JSON.stringify(currentTimes) === JSON.stringify(timeSlots)) return;
        timeScale.style.gridTemplateRows = `repeat(${timeSlots.length}, 116px)`;
        const fragment = document.createDocumentFragment();
        timeSlots.forEach((time, index) => {
            const slot = document.createElement('div');
            slot.className = 'time-slot';
            slot.textContent = time;
            slot.style.animationDelay = `${0.1 + index * 0.05}s`;
            fragment.appendChild(slot);
        });
        Array.from(timeScale.querySelectorAll('.time-slot')).forEach(s => s.classList.add('fade-out'));
        setTimeout(() => { timeScale.innerHTML = ''; timeScale.appendChild(fragment); }, 200);
    }

    function updateCourtHeaders(courts) {
        const courtsHeader = document.querySelector('.courts-header');
        if (!courtsHeader) return;
        const currentCourts = Array.from(courtsHeader.querySelectorAll('.court-header h3'))
            .map(el => el.textContent.trim());
        if (JSON.stringify(currentCourts) === JSON.stringify(courts)) return;
        courtsHeader.style.gridTemplateColumns = `repeat(${courts.length}, 1fr)`;
        const fragment = document.createDocumentFragment();
        courts.forEach(court => {
            const header = document.createElement('div');
            header.className = 'court-header';
            header.innerHTML = `<h3>${court}</h3>`;
            fragment.appendChild(header);
        });
        courtsHeader.innerHTML = '';
        courtsHeader.appendChild(fragment);
    }

    function splitTeamName(teamName) {
        if (!teamName) return ['TBD'];
        if (teamName.includes('/')) return teamName.split('/').map(p => p.trim()).filter(p => p);
        return [teamName];
    }

    function createMatchElement(data) {
        const el = document.createElement('div');
        el.className = `match-item match-${data.status} row-${data.row}`;
        el.style.cssText = `grid-row: ${data.row}; grid-column: ${data.col};`;

        const challengerWO = data.challenger_score === 'Won W.O.';
        const challengedWO = data.challenged_score === 'Won W.O.';
        const challengerPlayers = data.challenger_players || splitTeamName(data.challenger);
        const challengedPlayers = data.challenged_players || splitTeamName(data.challenged);

        function teamHtml(players, wo, score) {
            const woHtml    = wo ? `<div class="match-team-wo">W.O.</div>` : '';
            const scoreHtml = score && !wo ? `<div class="match-team-score">${score}</div>` : '';
            if (players.length === 1) {
                return `<div class="match-team"><div class="match-team-name">${players[0]}</div>${woHtml}${scoreHtml}</div>`;
            }
            const playersHtml = players.slice(0, 2).map(p => `<div class="match-player-name">${p}</div>`).join('');
            return `<div class="match-team"><div class="match-team-names">${playersHtml}</div>${woHtml}${scoreHtml}</div>`;
        }

        el.innerHTML = `
            <div class="match-content">
                <div class="match-number">:</div>
                <div class="match-teams-wrapper">
                    ${teamHtml(challengerPlayers, challengerWO, data.challenger_score)}
                    ${teamHtml(challengedPlayers, challengedWO, data.challenged_score)}
                </div>
            </div>`;
        return el;
    }

    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .fade-out { animation: fadeOutDown 0.3s ease-out forwards !important; }
            @keyframes fadeOutDown {
                from { opacity: 1; transform: translateY(0); }
                to   { opacity: 0; transform: translateY(10px); }
            }
            .match-item.updated { animation: highlightUpdate 1s ease-out; }
            @keyframes highlightUpdate {
                0%   { box-shadow: 0 0 0 0 rgba(174,213,87,0.7); }
                50%  { box-shadow: 0 0 20px 5px rgba(174,213,87,0.5); }
                100% { box-shadow: 0 0 0 0 rgba(174,213,87,0); }
            }`;
        document.head.appendChild(style);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => { injectStyles(); init(); });
    } else {
        injectStyles();
        init();
    }

})();
