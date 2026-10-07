// Per-browser progress (best scores, streak). Everything is best-effort:
// storage can be unavailable (private windows), and the app works without it.
const KEY = 'options-trainer-stats-v1';

function today() {
  return new Date().toISOString().slice(0, 10);
}

function daysBetween(a, b) {
  return Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
}

export function loadStats() {
  try {
    const raw = window.localStorage.getItem(KEY);
    const stats = raw ? JSON.parse(raw) : {};
    return { rounds: 0, answered: 0, correct: 0, streak: 0, lastPlayed: null, best: {}, ...stats };
  } catch {
    return { rounds: 0, answered: 0, correct: 0, streak: 0, lastPlayed: null, best: {} };
  }
}

export function currentStreak(stats) {
  if (!stats.lastPlayed) return 0;
  return daysBetween(stats.lastPlayed, today()) <= 1 ? stats.streak : 0;
}

export function recordRound(configKey, correct, total) {
  const stats = loadStats();
  const d = today();
  if (stats.lastPlayed !== d) {
    stats.streak = stats.lastPlayed && daysBetween(stats.lastPlayed, d) === 1 ? stats.streak + 1 : 1;
    stats.lastPlayed = d;
  }
  stats.rounds += 1;
  stats.answered += total;
  stats.correct += correct;
  const prev = stats.best[configKey];
  const isBest = !prev || correct > prev.correct;
  if (isBest) stats.best[configKey] = { correct, total, date: d };
  try {
    window.localStorage.setItem(KEY, JSON.stringify(stats));
  } catch {
    // Ignore: progress just won't persist.
  }
  return { stats, isBest, previousBest: prev };
}
