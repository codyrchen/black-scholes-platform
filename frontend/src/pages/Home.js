import React from 'react';
import { Link } from 'react-router-dom';
import { currentStreak, loadStats } from '../lib/stats';

const MODES = [
  {
    to: '/drills',
    title: 'Drills',
    body: 'Timed rounds of the questions quant interviews actually ask: ATM approximations, put-call parity, Greeks intuition, arbitrage spotting.',
  },
  {
    to: '/greeks',
    title: 'Greeks Lab',
    body: 'Drag spot, vol and time and watch every Greek respond. Predict the direction first, then check.',
  },
  {
    to: '/hedging',
    title: 'Hedging Game',
    body: 'Sell an option and delta hedge it yourself, step by step. See why hedging error shrinks like 1/√N and what happens when realized vol differs from implied.',
  },
];

export default function Home() {
  const stats = loadStats();
  const streak = currentStreak(stats);
  return (
    <>
      <section className="hero">
        <h1>Practice options intuition for quant interviews</h1>
        <p>
          Free drills, interactive Greeks and a delta-hedging game. Every answer is computed by a tested
          Black-Scholes library, not typed into an answer key.
        </p>
        <div className="row">
          <Link className="btn" to="/drills?count=10&timed=1">
            Start a 2-minute drill
          </Link>
          <Link className="btn btn-secondary" to="/learn">
            Read the research notes
          </Link>
        </div>
        {stats.rounds > 0 && (
          <div className="stat-row" aria-label="Your progress">
            <div className="stat">
              <div className="value">{streak}</div>
              <div className="label">day streak</div>
            </div>
            <div className="stat">
              <div className="value">{stats.rounds}</div>
              <div className="label">rounds played</div>
            </div>
            <div className="stat">
              <div className="value">
                {stats.answered ? Math.round((100 * stats.correct) / stats.answered) : 0}%
              </div>
              <div className="label">accuracy</div>
            </div>
          </div>
        )}
      </section>
      <section className="grid-3">
        {MODES.map((m) => (
          <Link key={m.to} to={m.to} className="card card-link">
            <h3>{m.title}</h3>
            <p className="muted small">{m.body}</p>
          </Link>
        ))}
      </section>
    </>
  );
}
