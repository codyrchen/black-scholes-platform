import React, { useEffect, useState } from 'react';
import { NavLink, Route, Routes } from 'react-router-dom';
import { apiGet } from './api';
import Calculator from './pages/Calculator';
import Drills from './pages/Drills';
import GreeksLab from './pages/GreeksLab';
import HedgingGame from './pages/HedgingGame';
import Home from './pages/Home';
import Learn from './pages/Learn';

const NAV = [
  ['/drills', 'Drills'],
  ['/greeks', 'Greeks Lab'],
  ['/hedging', 'Hedging Game'],
  ['/learn', 'Learn'],
  ['/calculator', 'Calculator'],
];

function ApiStatus() {
  const [up, setUp] = useState(null);
  useEffect(() => {
    let cancelled = false;
    const check = () =>
      apiGet('/api/health')
        .then(() => !cancelled && setUp(true))
        .catch(() => !cancelled && setUp(false));
    check();
    const id = setInterval(check, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);
  if (up !== false) return null;
  return (
    <div className="banner banner-error" role="alert">
      <span aria-hidden="true">⚠</span> The API isn't reachable. Drills, the hedging game and the calculator
      need it; the Greeks Lab and Learn pages work offline.
    </div>
  );
}

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <span className="brand-mark" aria-hidden="true">σ</span> Options Trainer
        </NavLink>
        <nav aria-label="Main">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <ApiStatus />
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/drills" element={<Drills />} />
          <Route path="/greeks" element={<GreeksLab />} />
          <Route path="/hedging" element={<HedgingGame />} />
          <Route path="/learn" element={<Learn />} />
          <Route path="/learn/:slug" element={<Learn />} />
          <Route path="/calculator" element={<Calculator />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>
      <footer className="footer">
        Every answer is computed by a pricing library with a property-based test suite.{' '}
        <a href="https://github.com/codyrchen/black-scholes-platform">Source on GitHub</a>
      </footer>
    </div>
  );
}
