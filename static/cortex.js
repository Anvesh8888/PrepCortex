// --- CORTEX CORE: XP, LEVELING & ACHIEVEMENT SYSTEM ---

function getLevelInfo(totalXp) {
    let level = 0;
    let requiredForNext = 10; 
    let xpRemaining = totalXp;

    while (xpRemaining >= requiredForNext && level < 50) {
        xpRemaining -= requiredForNext;
        level++;
        requiredForNext += 5;
    }
    return { level, currentLevelXp: xpRemaining, nextLevelReq: requiredForNext };
}

function getTitle(level) {
    if (level >= 50) return "Cortex Commander 👑";
    if (level >= 30) return "Neural Navigator ⚡";
    if (level >= 10) return "Synaptic Striker ⚔️";
    if (level >= 1)  return "Wandering Neuron 🧠";
    return "Awakened Spark 🌱";
}

function addXP(amount, reason) {
    let currentXp = parseInt(localStorage.getItem('cortex_xp')) || 0;
    let oldLevel = getLevelInfo(currentXp).level;
    
    let newXp = currentXp + amount;
    localStorage.setItem('cortex_xp', newXp);
    let newLevel = getLevelInfo(newXp).level;
    
    showToast(`+${amount} XP: ${reason}`);
    
    if (newLevel > oldLevel) {
        setTimeout(() => {
            showToast(`🚀 LEVEL UP! You are now a ${getTitle(newLevel)}`);
            checkAchievements('level_up', { level: newLevel });
        }, 800);
    }
    
    updateUI();
}

function logActivity(type) {
    const now = Date.now();
    const twentyHours = 20 * 60 * 60 * 1000;

    if (type === 'plan') localStorage.setItem('last_plan_time', now);
    if (type === 'quiz') localStorage.setItem('last_quiz_time', now);

    const lastPlan = parseInt(localStorage.getItem('last_plan_time')) || 0;
    const lastQuiz = parseInt(localStorage.getItem('last_quiz_time')) || 0;
    const lastBonus = parseInt(localStorage.getItem('last_daily_bonus_time')) || 0;

    if (lastPlan > 0 && lastQuiz > 0 && (now - lastBonus > twentyHours)) {
        if (lastPlan > lastBonus && lastQuiz > lastBonus) {
            localStorage.setItem('last_daily_bonus_time', now);
            addXP(50, "Daily Task Complete!");
            
            // Track total daily tasks completed
            let dailyCount = (parseInt(localStorage.getItem('cortex_total_dailies')) || 0) + 1;
            localStorage.setItem('cortex_total_dailies', dailyCount);
            checkAchievements('daily_task', { count: dailyCount });
        }
    }
}

// --- ACHIEVEMENT ENGINE ---
function checkAchievements(event, data = {}) {
    let unlocked = JSON.parse(localStorage.getItem('cortex_achievements')) || [];
    
    function unlock(id, title) {
        if (!unlocked.includes(id)) {
            unlocked.push(id);
            localStorage.setItem('cortex_achievements', JSON.stringify(unlocked));
            setTimeout(() => showToast(`🏆 ACHIEVEMENT: ${title}`, true), 500);
        }
    }

    if (event === 'plan_generated') {
        // Track Total Plans
        let totalPlans = (parseInt(localStorage.getItem('cortex_total_plans')) || 0) + 1;
        localStorage.setItem('cortex_total_plans', totalPlans);
        
        // Track Daily Plans
        let today = new Date().toDateString();
        let dailyPlans = JSON.parse(localStorage.getItem('cortex_daily_plans')) || { date: today, count: 0 };
        if (dailyPlans.date !== today) dailyPlans = { date: today, count: 0 }; // Reset if new day
        dailyPlans.count++;
        localStorage.setItem('cortex_daily_plans', JSON.stringify(dailyPlans));

        // Evaluate Planner Achievements
        if (totalPlans >= 1) unlock('first_spark', 'The First Spark');
        if (totalPlans >= 10) unlock('frontal_architect', 'Frontal Lobe Architect');
        if (dailyPlans.count >= 3) unlock('info_overload', 'Information Overload');
    }

    if (event === 'quiz_finished') {
        if (data.maxStreak >= 3) unlock('action_potential', 'Action Potential');
        if (data.totalQs >= 5 && data.score === data.totalQs) unlock('absolute_recall', 'Absolute Recall');
        if (data.totalPlayers >= 4) unlock('hive_mind', 'Hive Mind');
        if (data.rank === 1 && data.totalPlayers > 1) unlock('winner', 'Winner!');
    }

    if (event === 'level_up') {
        if (data.level >= 10) unlock('cortical_awakening', 'Cortical Awakening');
        if (data.level >= 50) unlock('limitless', 'Limitless');
    }

    if (event === 'daily_task') {
        if (data.count >= 5) unlock('synaptic_chain', 'Synaptic Chain');
    }
}

function updateUI() {
    const totalXp = parseInt(localStorage.getItem('cortex_xp')) || 0;
    const info = getLevelInfo(totalXp);
    
    const titleDisplay = document.getElementById('user-title');
    const levelDisplay = document.getElementById('user-level');
    
    if (titleDisplay && levelDisplay) {
        titleDisplay.innerText = getTitle(info.level);
        levelDisplay.innerText = `Level ${info.level} • ${info.currentLevelXp} / ${info.nextLevelReq} XP`;
    }
}

let activeToasts = 0;
function showToast(message, isAchievement = false) {
    const toast = document.createElement('div');
    toast.innerText = message;
    
    // Stack toasts upwards if multiple happen at once
    const bottomOffset = 30 + (activeToasts * 70);
    activeToasts++;
    
    // Gold styling for achievements, standard blue for XP
    const bg = isAchievement ? 'linear-gradient(135deg, #fbbf24, #d97706)' : '#0f172a';
    const textCol = isAchievement ? '#0f172a' : '#38bdf8';
    const border = isAchievement ? '#f59e0b' : '#38bdf8';

    toast.style.cssText = `
        position: fixed; bottom: ${bottomOffset}px; right: -350px; 
        background: ${bg}; color: ${textCol}; 
        padding: 16px 24px; border-radius: 12px; 
        border: 1px solid ${border}; font-weight: bold;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        z-index: 9999;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => toast.style.right = '30px', 100);
    
    setTimeout(() => {
        toast.style.right = '-350px';
        setTimeout(() => {
            toast.remove();
            activeToasts--;
        }, 600);
    }, isAchievement ? 5000 : 3500); // Achievements stay on screen a bit longer
}

window.addEventListener('DOMContentLoaded', updateUI);
