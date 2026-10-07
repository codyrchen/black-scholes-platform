import React, { useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { apiPost } from '../api';
import ChartTooltip from '../components/ChartTooltip';
import { hedgeMtm } from '../lib/bs';

const IMPLIED = 0.2;
const MATURITY = 0.25;
const REGIMES = {
  same: { label: 'Same as implied (20%)', vol: 0.2 },
  high: { label: 'Higher (30%)', vol: 0.3 },
  low: { label: 'Lower (10%)', vol: 0.1 },
  mystery: { label: 'Mystery', vol: null },
};

// Round before taking the sign so tiny negatives don't print as "−$0.00".
const money = (x) => {
  if (x == null) return '–';
  const v = Math.round(x * 100) / 100;
  return `${v < 0 ? '−' : ''}$${Math.abs(v).toFixed(2)}`;
};

function realizedVol(spots, T) {
  const n = spots.length - 1;
  const rets = [];
  for (let i = 1; i < spots.length; i++) rets.push(Math.log(spots[i] / spots[i - 1]));
  const mean = rets.reduce((a, b) => a + b, 0) / n;
  const variance = rets.reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(n - 1, 1);
  return Math.sqrt(variance / (T / n));
}

function Setup({ onStart, error, busy }) {
  const [kind, setKind] = useState('call');
  const [regime, setRegime] = useState('same');
  const [steps, setSteps] = useState(13);
  return (
    <div className="card" style={{ maxWidth: 720 }}>
      <p>
        You just <strong>sold one {kind}</strong> (strike 100, spot 100, 3 months to expiry) at 20% implied vol.
        Your job: hold shares to offset the option's risk, rebalancing {steps} times. You keep the premium; you owe
        the payoff at expiry. A perfect hedger ends near $0.
      </p>
      <div className="field">
        <label>Option you sell</label>
        <div className="segmented">
          {['call', 'put'].map((k) => (
            <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}>
              {k === 'call' ? 'Call' : 'Put'}
            </button>
          ))}
        </div>
      </div>
      <div className="field">
        <label>Realized vol (how much the stock actually moves)</label>
        <div className="chips">
          {Object.entries(REGIMES).map(([k, v]) => (
            <button key={k} type="button" className="chip" aria-pressed={regime === k} onClick={() => setRegime(k)}>
              {v.label}
            </button>
          ))}
        </div>
      </div>
      <div className="field">
        <label>Rebalances</label>
        <div className="segmented">
          {[
            [6, 'Every 2 weeks'],
            [13, 'Weekly'],
            [26, 'Twice a week'],
          ].map(([n, text]) => (
            <button key={n} type="button" aria-pressed={steps === n} onClick={() => setSteps(n)}>
              {text}
            </button>
          ))}
        </div>
      </div>
      {error && <div className="notice notice-error" style={{ marginBottom: '1rem' }}>{error}</div>}
      <button type="button" className="btn" disabled={busy} onClick={() => onStart({ kind, regime, steps })}>
        {busy ? 'Simulating…' : 'Sell the option and start'}
      </button>
    </div>
  );
}

function StudyChart({ setup }) {
  const [study, setStudy] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await apiPost('/api/v1/hedging/study', {
        implied_vol: IMPLIED,
        realized_vol: setup.realized,
        option_type: setup.kind,
        maturity: MATURITY,
        steps: [3, 6, 13, 26, 52, 126, 252],
        paths: 2000,
      });
      const first = r.results[0];
      setStudy(
        r.results.map((row) => ({
          steps: row.steps,
          std: row.std,
          mean: row.mean,
          reference: first.std * Math.sqrt(first.steps / row.steps),
        })),
      );
    } catch (e) {
      setError(e.message);
    }
    setBusy(false);
  };

  return (
    <div className="card">
      <h2>One game is one sample. What about thousands?</h2>
      <p className="muted">
        Simulate 2,000 paths with the same realized vol and see how the spread of a perfect Black-Scholes delta
        hedger's P&amp;L depends on how often it rebalances.
      </p>
      {!study && (
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={run}>
          {busy ? 'Running 14,000 simulations…' : 'Run the study'}
        </button>
      )}
      {error && <div className="notice notice-error">{error}</div>}
      {study && (
        <>
          <div className="legend">
            <span><i style={{ background: 'var(--series-1)' }} />std. dev. of hedged P&amp;L</span>
            <span><i className="dashed" />1/√N reference</span>
          </div>
          <div className="chart-box short">
            <ResponsiveContainer>
              <LineChart data={study} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="steps" type="number" scale="log" domain={['dataMin', 'dataMax']} ticks={study.map((d) => d.steps)} stroke="var(--axis)" label={{ value: 'Rebalances (log scale)', position: 'insideBottom', offset: -12 }} />
                <YAxis type="number" scale="log" domain={['auto', 'auto']} stroke="var(--axis)" width={56} tickFormatter={(v) => `$${Number(v.toPrecision(2))}`} />
                <Tooltip content={<ChartTooltip labelFormat={(v) => `${v} rebalances`} valueFormat={(v) => `$${v.toFixed(3)}`} />} />
                <Line dataKey="reference" name="1/√N" stroke="var(--muted)" strokeDasharray="4 3" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                <Line dataKey="std" name="Std. dev." stroke="var(--series-1)" strokeWidth={2} dot={{ r: 4, strokeWidth: 2, fill: 'var(--surface)' }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <table className="data" style={{ marginTop: '0.75rem' }}>
            <thead>
              <tr><th>Rebalances</th><th>Mean P&amp;L</th><th>Std. dev.</th></tr>
            </thead>
            <tbody>
              {study.map((row) => (
                <tr key={row.steps}><td>{row.steps}</td><td>{money(row.mean)}</td><td>{money(row.std)}</td></tr>
              ))}
            </tbody>
          </table>
          <p className="finding" style={{ marginTop: '1rem' }}>
            {setup.realized === IMPLIED
              ? 'With realized vol equal to implied, the mean is about zero and the spread falls roughly like 1/√N: rebalancing 4× as often halves the error. Hedging is never perfect in discrete time.'
              : setup.realized > IMPLIED
                ? 'Realized vol above implied: the mean is negative no matter how often you rebalance. The option was sold too cheap, and more hedging only makes the loss more certain.'
                : 'Realized vol below implied: the mean is positive. The option was sold rich; hedging locks in the difference between implied and realized variance.'}
          </p>
        </>
      )}
    </div>
  );
}

export default function HedgingGame() {
  const [game, setGame] = useState(null);
  const [setup, setSetup] = useState(null);
  const [hedges, setHedges] = useState([]);
  const [current, setCurrent] = useState(0.5);
  const [hintsUsed, setHintsUsed] = useState(0);
  const [showHint, setShowHint] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const start = async ({ kind, regime, steps }) => {
    setBusy(true);
    setError(null);
    const vols = [0.1, 0.2, 0.3];
    const realized = REGIMES[regime].vol ?? vols[Math.floor(Math.random() * vols.length)];
    try {
      const r = await apiPost('/api/v1/hedging/simulate', {
        implied_vol: IMPLIED,
        realized_vol: realized,
        option_type: kind,
        maturity: MATURITY,
        steps,
      });
      setGame(r);
      setSetup({ kind, regime, steps, realized });
      setHedges([]);
      setCurrent(kind === 'call' ? 0.5 : -0.5);
      setHintsUsed(0);
      setShowHint(false);
    } catch (e) {
      setError(e.message);
    }
    setBusy(false);
  };

  const step = hedges.length;
  const done = game && step >= setup.steps;

  const yours = useMemo(
    () =>
      game &&
      hedgeMtm({
        spots: game.spots,
        hedges,
        optionValues: game.option_values,
        premium: game.premium,
        T: MATURITY,
        nSteps: setup.steps,
      }),
    [game, hedges, setup],
  );

  if (!game) {
    return (
      <>
        <div className="page-header">
          <h1>Hedging Game</h1>
          <p>
            Market makers sell options and hedge the risk with the stock. Try it: you set the hedge each period,
            the market moves, and you see whether your book holds up against the textbook Black-Scholes delta hedger.
          </p>
        </div>
        <Setup onStart={start} error={error} busy={busy} />
      </>
    );
  }

  const revealUpTo = done ? setup.steps : step;
  const chartData = game.times.map((t, i) => ({
    day: Math.round(t * 365),
    spot: i <= revealUpTo ? game.spots[i] : null,
    you: i <= revealUpTo ? yours[i] : null,
    bs: i <= revealUpTo ? game.bs_hedge_pnl[i] : null,
    none: i <= revealUpTo ? game.no_hedge_pnl[i] : null,
  }));
  const isCall = setup.kind === 'call';
  const bsDelta = !done ? game.deltas[step] : null;
  const daysLeft = Math.round((MATURITY - game.times[Math.min(step, setup.steps)]) * 365);

  const commit = () => {
    setHedges((h) => [...h, current]);
    setShowHint(false);
  };

  return (
    <>
      <div className="page-header">
        <h1>Hedging Game</h1>
        <p>
          You're short one {setup.kind}. Premium collected: <strong>{money(game.premium)}</strong>. Realized vol:{' '}
          <strong>{done || setup.regime !== 'mystery' ? `${Math.round(setup.realized * 100)}%` : 'hidden'}</strong>.
        </p>
      </div>
      <div className="grid-2">
        <div className="card">
          {!done ? (
            <>
              <h2>
                Step {step + 1} of {setup.steps}
              </h2>
              <dl className="kv" style={{ marginBottom: '1rem' }}>
                <div><dt>Spot</dt><dd>{game.spots[step].toFixed(2)}</dd></div>
                <div><dt>Option value</dt><dd>{game.option_values[step].toFixed(2)}</dd></div>
                <div><dt>Days left</dt><dd>{daysLeft}</dd></div>
                <div><dt>Your P&amp;L</dt><dd>{money(yours[step])}</dd></div>
              </dl>
              <div className="field">
                <div className="slider-head">
                  <label htmlFor="hedge">Shares to hold (per option)</label>
                  <output htmlFor="hedge">{current.toFixed(2)}</output>
                </div>
                <input
                  id="hedge"
                  type="range"
                  min={isCall ? 0 : -1}
                  max={isCall ? 1 : 0}
                  step={0.01}
                  value={current}
                  onChange={(e) => setCurrent(Number(e.target.value))}
                />
                <small>
                  You're short the {setup.kind}, so you hedge by holding {isCall ? 'a long' : 'a short'} stock position.
                </small>
              </div>
              <div className="row">
                <button type="button" className="btn" onClick={commit}>
                  Hedge &amp; advance
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    if (!showHint) setHintsUsed((n) => n + 1);
                    setShowHint(true);
                  }}
                >
                  Hint
                </button>
              </div>
              {showHint && (
                <p className="small muted" style={{ marginTop: '0.75rem' }}>
                  The Black-Scholes delta of the option is <strong className="num">{bsDelta.toFixed(2)}</strong>. To
                  be delta neutral while short it, hold that many shares.{' '}
                  <button type="button" className="chip" onClick={() => setCurrent(Number(bsDelta.toFixed(2)))}>
                    Use it
                  </button>
                </p>
              )}
            </>
          ) : (
            <>
              <h2>Final P&amp;L</h2>
              <table className="data">
                <tbody>
                  <tr><td>You</td><td><strong>{money(yours[setup.steps])}</strong></td></tr>
                  <tr><td>Black-Scholes delta hedger</td><td>{money(game.bs_hedge_pnl[setup.steps])}</td></tr>
                  <tr><td>No hedge</td><td>{money(game.no_hedge_pnl[setup.steps])}</td></tr>
                </tbody>
              </table>
              <p className="small muted" style={{ marginTop: '0.75rem' }}>
                Realized vol on this path: {(realizedVol(game.spots, MATURITY) * 100).toFixed(1)}% (target{' '}
                {Math.round(setup.realized * 100)}%). Hints used: {hintsUsed}.
              </p>
              <h3 style={{ marginTop: '1rem' }}>Where the delta hedger's P&amp;L came from</h3>
              <table className="data">
                <tbody>
                  <tr><td>Theta collected (½Γ·S²·σ²·dt)</td><td>{money(game.breakdown.theta)}</td></tr>
                  <tr><td>Gamma paid on moves (−½Γ·ΔS²)</td><td>{money(game.breakdown.gamma)}</td></tr>
                  <tr><td>Discretization residual</td><td>{money(game.breakdown.residual)}</td></tr>
                </tbody>
              </table>
              <p className="small muted" style={{ marginTop: '0.75rem' }}>
                A short option collects theta every day and pays out on every large move. If the stock moves the way
                implied vol predicted, the two cancel on average.
              </p>
              <div className="row">
                <button type="button" className="btn" onClick={() => start(setup)}>
                  Play again
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setGame(null)}>
                  Change settings
                </button>
              </div>
            </>
          )}
        </div>
        <div className="stack">
          <div className="card">
            <h2>Stock price</h2>
            <div className="chart-box short">
              <ResponsiveContainer>
                <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="day" type="number" domain={[0, Math.round(MATURITY * 365)]} stroke="var(--axis)" label={{ value: 'Day', position: 'insideBottom', offset: -12 }} />
                  <YAxis domain={['auto', 'auto']} stroke="var(--axis)" width={48} />
                  <Tooltip content={<ChartTooltip labelFormat={(v) => `Day ${v}`} valueFormat={(v) => v.toFixed(2)} />} />
                  <Line dataKey="spot" name="Spot" stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="card">
            <h2>Hedged P&amp;L</h2>
            <div className="legend">
              <span><i style={{ background: 'var(--series-1)' }} />You</span>
              <span><i style={{ background: 'var(--series-2)' }} />Black-Scholes delta</span>
              <span><i style={{ background: 'var(--series-3)' }} />No hedge</span>
            </div>
            <div className="chart-box short">
              <ResponsiveContainer>
                <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="day" type="number" domain={[0, Math.round(MATURITY * 365)]} stroke="var(--axis)" label={{ value: 'Day', position: 'insideBottom', offset: -12 }} />
                  <YAxis domain={['auto', 'auto']} stroke="var(--axis)" width={56} tickFormatter={(v) => money(v)} />
                  <Tooltip content={<ChartTooltip labelFormat={(v) => `Day ${v}`} valueFormat={(v) => money(v)} />} />
                  <Line dataKey="none" name="No hedge" stroke="var(--series-3)" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line dataKey="bs" name="BS delta" stroke="var(--series-2)" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line dataKey="you" name="You" stroke="var(--series-1)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          {done && <StudyChart setup={setup} />}
        </div>
      </div>
    </>
  );
}
