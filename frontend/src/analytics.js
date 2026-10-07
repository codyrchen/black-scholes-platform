function addScript(src, attrs = {}) {
  const s = document.createElement('script');
  s.defer = true;
  s.src = src;
  Object.assign(s.dataset, attrs);
  document.head.appendChild(s);
}

// Visitor counts, cookie-free:
// - Vercel Web Analytics in production builds served from a real host. Vercel serves the
//   script from the site's own domain, so there is no npm package to install.
// - Plausible as well, if REACT_APP_PLAUSIBLE_DOMAIN is set.
export function initAnalytics() {
  if (typeof window === 'undefined') return;
  const local = ['localhost', '127.0.0.1'].includes(window.location.hostname);
  if (process.env.NODE_ENV === 'production' && !local) {
    window.va =
      window.va ||
      function va(...args) {
        (window.vaq = window.vaq || []).push(args);
      };
    addScript('/_vercel/insights/script.js');
  }
  const plausible = process.env.REACT_APP_PLAUSIBLE_DOMAIN;
  if (plausible) addScript('https://plausible.io/js/script.js', { domain: plausible });
}
