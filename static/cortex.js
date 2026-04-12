// --- CORTEX CORE: XP & LEVELING SYSTEM ---

/**
 * Calculates current level based on total XP.
 * Formula: Lvl 1=10XP, Lvl 2=15XP, Lvl 3=20XP...
 * The "required" amount increases by 5 each level.
 */
function getLevelInfo(totalXp) {
    let level = 0;
    let requiredForNext = 10; 
    let xpRemaining = totalXp;

    while (xpRemaining >= requiredForNext && level < 50) {
        xpRemaining -= requiredForNext;
        level++;
        requiredForNext += 5;
    }
    return { 
        level: level, 
        currentLevelXp: xpRemaining, 
        nextLevelReq: requiredForNext 
    };
}

/**
 * Returns the Rank Title based on Level
 */
function getTitle(level) {
    if (level >= 50) return "Cortex Commander 👑";
    if (level >= 30) return "Neural Navigator ⚡";
    if (level >= 10) return "Synaptic Striker ⚔️";
    if (level >= 1)  return "Wandering Neuron 🧠";
    return "Awakened Spark 🌱";
}

/**
 * Adds XP and handles Level-Up notifications
 */
function addXP(amount, reason) {
    let currentXp = parseInt(localStorage.getItem('cortex_xp')) || 0;
    let oldLevel = getLevelInfo(currentXp).level;
    
    let newXp = currentXp + amount;
    localStorage.setItem('cortex_xp', newXp);
    
    let newLevel = getLevelInfo(newXp).level;
    
    showToast(`+${amount} XP: ${reason}`);
    
    if (newLevel > oldLevel) {
        // Delay level up toast slightly so XP toast shows first
        setTimeout(() => {
            showToast(`🚀 LEVEL UP! You are now a ${getTitle(newLevel)}`);
        }, 1000);
    }
    
    updateUI();
}

/**
 * Tracks daily tasks (Plan + Quiz) with a 20-hour cooldown
 */
function logActivity(type) {
    const now = Date.now();
    const twentyHours = 20 * 60 * 60 * 1000;

    // Record the specific activity time
    if (type === 'plan') localStorage.setItem('last_plan_time', now);
    if (type === 'quiz') localStorage.setItem('last_quiz_time', now);

    const lastPlan = parseInt(localStorage.getItem('last_plan_time')) || 0;
    const lastQuiz = parseInt(localStorage.getItem('last_quiz_time')) || 0;
    const lastBonus = parseInt(localStorage.getItem('last_daily_bonus_time')) || 0;

    // Condition: Both tasks done AND 20 hours passed since the last +50 XP bonus
    if (lastPlan > 0 && lastQuiz > 0 && (now - lastBonus > twentyHours)) {
        // Check if both actions happened recently (within the same "window")
        // We ensure both were done after the last reset
        if (lastPlan > lastBonus && lastQuiz > lastBonus) {
            localStorage.setItem('last_daily_bonus_time', now);
            addXP(50, "Daily Task Complete!");
        }
    }
}

/**
 * Updates the Header UI (Title and Level)
 */
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

/**
 * Simple animated toast notification
 */
function showToast(message) {
    const toast = document.createElement('div');
    toast.innerText = message;
    toast.style.cssText = `
        position: fixed; bottom: 30px; right: -350px; 
        background: #0f172a; color: #38bdf8; 
        padding: 16px 24px; border-radius: 12px; 
        border: 1px solid #38bdf8; font-weight: bold;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        z-index: 9999;
    `;
    
    document.body.appendChild(toast);
    
    // Animate In
    setTimeout(() => toast.style.right = '30px', 100);
    
    // Animate Out and Remove
    setTimeout(() => {
        toast.style.right = '-350px';
        setTimeout(() => toast.remove(), 600);
    }, 4000);
}

// Ensure UI stays in sync on load
window.addEventListener('DOMContentLoaded', updateUI);