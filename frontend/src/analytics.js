// Cookie-free visitor counts via Plausible, only when REACT_APP_PLAUSIBLE_DOMAIN is set.
export function initAnalytics() {
  const domain = process.env.REACT_APP_PLAUSIBLE_DOMAIN;
  if (!domain || typeof document === 'undefined') return;
  const s = document.createElement('script');
  s.defer = true;
  s.dataset.domain = domain;
  s.src = 'https://plausible.io/js/script.js';
  document.head.appendChild(s);
}
