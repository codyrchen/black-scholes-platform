import React, { useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import ChartTooltip from '../components/ChartTooltip';
import { greeks, price } from '../lib/bs';

// Quoting units for display: theta per day, vega and rho per 1 vol / rate point.
const MEASURES = {
  price: { label: 'Price', unit: '$', f: (a) => price(a) },
  delta: { label: 'Delta', unit: '', f: (a) => greeks(a).delta },
  gamma: { label: 'Gamma', unit: '', f: (a) => greeks(a).gamma },
  vega: { label: 'Vega', unit: 'per 1 vol pt', f: (a) => greeks(a).vega / 100 },
  theta: { label: 'Theta', unit: 'per day', f: (a) => greeks(a).theta / 365 },
};

const fmt = (x, d = 4) => (x == null || Number.isNaN(x) ? '–' : Number(x).toFixed(d));

function Slider({ id, label, value, min, max, step, onChange, display }) {
  return (
    <div className="field">
      <div className="slider-head">
        <label htmlFor={id}>{label}</label>
        <output htmlFor={id}>{display(value)}</output>
      </div>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </div>
  );
}

const SCENARIOS = [
  { param: 'sigma', label: 'implied vol rises by 10 points', apply: (s) => ({ ...s, sigma: s.sigma + 0.1 }) },
  { param: 'days', label: 'a week passes (spot unchanged)', apply: (s) => ({ ...s, days: Math.max(s.days - 7, 1) }) },
  { param: 'S', label: 'spot rises 5%', apply: (s) => ({ ...s, S: s.S * 1.05 }) },
  { param: 'S', label: 'spot falls 5%', apply: (s) => ({ ...s, S: s.S * 0.95 }) },
];

function toArgs(s) {
  return { S: s.S, K: s.K, T: s.days / 365, r: s.r, sigma: s.sigma, q: s.q, kind: s.kind };
}

function randomScenario() {
  const kind = Math.random() < 0.5 ? 'call' : 'put';
  const S = 100;
  const K = [90, 95, 100, 105, 110][Math.floor(Math.random() * 5)];
  const days = [14, 30, 60, 120][Math.floor(Math.random() * 4)];
  const sigma = [0.15, 0.2, 0.3][Math.floor(Math.random() * 3)];
  const base = { S, K, days, sigma, r: 0, q: 0, kind };
  const scenario = SCENARIOS[Math.floor(Math.random() * SCENARIOS.length)];
  const measures = ['delta', 'gamma', 'vega', 'theta', 'price'];
  const measure = measures[Math.floor(Math.random() * measures.length)];
  return { base, scenario, measure };
}

function Predict() {
  const [item, setItem] = useState(randomScenario);
  const [guess, setGuess] = useState(null);
  const [score, setScore] = useState({ right: 0, total: 0 });

  const before = MEASURES[item.measure].f(toArgs(item.base));
  const after = MEASURES[item.measure].f(toArgs(item.scenario.apply(item.base)));
  const change = after - before;
  const tiny = Math.abs(change) < 1e-3 * Math.max(Math.abs(before), 1e-6);
  const truth = tiny ? 'same' : change > 0 ? 'up' : 'down';
  const label = MEASURES[item.measure].label.toLowerCase();

  const answer = (g) => {
    if (guess) return;
    setGuess(g);
    setScore((s) => ({ right: s.right + (g === truth ? 1 : 0), total: s.total + 1 }));
  };

  const { base } = item;
  return (
    <div className="card">
      <h2>Predict, then reveal</h2>
      <p>
        A long {base.kind}, strike {base.K}, spot {base.S}, {base.days} days to expiry, vol {Math.round(base.sigma * 100)}%. If{' '}
        <strong>{item.scenario.label}</strong>, what happens to its <strong>{label}</strong>?
      </p>
      <div className="row">
        {[
          ['up', 'Goes up'],
          ['down', 'Goes down'],
          ['same', 'About the same'],
        ].map(([g, text]) => {
          let cls = 'choice';
          if (guess && g === truth) cls += ' correct';
          else if (guess === g) cls += ' wrong';
          return (
            <button key={g} type="button" className={cls} disabled={!!guess} onClick={() => answer(g)}>
              {text}
            </button>
          );
        })}
      </div>
      {guess && (
        <div className={`feedback ${guess === truth ? 'correct' : 'wrong'}`} role="status">
          <strong className={guess === truth ? 'status-good' : 'status-bad'}>{guess === truth ? '✓ Right' : '✗ Not this time'}</strong>
          The {label} moves from <span className="num">{fmt(before)}</span> to <span className="num">{fmt(after)}</span>{' '}
          ({change >= 0 ? '+' : ''}
          {fmt(change)}).
        </div>
      )}
      <div className="row" style={{ marginTop: '1rem', justifyContent: 'space-between' }}>
        <span className="small muted num">
          Score: {score.right}/{score.total}
        </span>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => {
            setItem(randomScenario());
            setGuess(null);
          }}
        >
          Next scenario
        </button>
      </div>
    </div>
  );
}

export default function GreeksLab() {
  const [s, setS] = useState({ S: 100, K: 100, days: 90, sigma: 0.2, r: 0.03, q: 0, kind: 'call' });
  const [measure, setMeasure] = useState('gamma');
  const set = (key) => (v) => setS((prev) => ({ ...prev, [key]: v }));
  const m = MEASURES[measure];
  const shortDays = Math.max(Math.round(s.days / 4), 1);

  const bySpot = useMemo(() => {
    const pts = [];
    for (let i = 0; i <= 120; i++) {
      const spot = s.K * (0.5 + i / 120);
      pts.push({
        spot,
        now: m.f({ ...toArgs(s), S: spot }),
        short: m.f({ ...toArgs(s), S: spot, T: shortDays / 365 }),
      });
    }
    return pts;
  }, [s, m, shortDays]);

  const byTime = useMemo(() => {
    const pts = [];
    const maxDays = Math.max(s.days, 30);
    for (let i = 0; i <= 100; i++) {
      const d = maxDays * (1 - i / 100) + 0.5 * (i / 100);
      pts.push({ days: d, value: m.f({ ...toArgs(s), T: d / 365 }) });
    }
    return pts;
  }, [s, m]);

  const g = greeks(toArgs(s));
  const p = price(toArgs(s));
  const yLabel = `${m.label}${m.unit ? ` (${m.unit})` : ''}`;

  return (
    <>
      <div className="page-header">
        <h1>Greeks Lab</h1>
        <p>
          Move the sliders and watch how each Greek depends on spot and time. Notice how gamma piles up around the
          strike as expiry approaches, and how vega does the opposite.
        </p>
      </div>
      <div className="grid-2">
        <div className="card">
          <div className="field">
            <label>Option</label>
            <div className="segmented">
              {['call', 'put'].map((k) => (
                <button key={k} type="button" aria-pressed={s.kind === k} onClick={() => set('kind')(k)}>
                  {k === 'call' ? 'Call' : 'Put'}
                </button>
              ))}
            </div>
          </div>
          <Slider id="S" label="Spot" value={s.S} min={50} max={150} step={0.5} onChange={set('S')} display={(v) => v.toFixed(1)} />
          <Slider id="K" label="Strike" value={s.K} min={50} max={150} step={1} onChange={set('K')} display={(v) => v.toFixed(0)} />
          <Slider id="days" label="Days to expiry" value={s.days} min={1} max={730} step={1} onChange={set('days')} display={(v) => `${v}`} />
          <Slider id="sigma" label="Implied vol" value={s.sigma} min={0.05} max={1} step={0.01} onChange={set('sigma')} display={(v) => `${Math.round(v * 100)}%`} />
          <Slider id="r" label="Rate" value={s.r} min={0} max={0.1} step={0.0025} onChange={set('r')} display={(v) => `${(v * 100).toFixed(2)}%`} />
          <Slider id="q" label="Dividend yield" value={s.q} min={0} max={0.08} step={0.0025} onChange={set('q')} display={(v) => `${(v * 100).toFixed(2)}%`} />
          <dl className="kv">
            <div><dt>Price</dt><dd>{fmt(p, 3)}</dd></div>
            <div><dt>Delta</dt><dd>{fmt(g.delta)}</dd></div>
            <div><dt>Gamma</dt><dd>{fmt(g.gamma)}</dd></div>
            <div><dt>Vega /1pt</dt><dd>{fmt(g.vega / 100)}</dd></div>
            <div><dt>Theta /day</dt><dd>{fmt(g.theta / 365)}</dd></div>
            <div><dt>Rho /1pt</dt><dd>{fmt(g.rho / 100)}</dd></div>
          </dl>
        </div>
        <div className="stack">
          <div className="card">
            <div className="row" style={{ justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <h2 style={{ margin: 0 }}>{m.label} vs spot</h2>
              <div className="segmented" role="group" aria-label="Measure">
                {Object.entries(MEASURES).map(([k, v]) => (
                  <button key={k} type="button" aria-pressed={measure === k} onClick={() => setMeasure(k)}>
                    {v.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="legend">
              <span><i style={{ background: 'var(--series-1)' }} />{s.days} days to expiry</span>
              <span><i style={{ background: 'var(--series-2)' }} />{shortDays} days to expiry</span>
              <span><i className="dashed" />current spot</span>
            </div>
            <div className="chart-box">
              <ResponsiveContainer>
                <LineChart data={bySpot} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis
                    dataKey="spot"
                    type="number"
                    domain={['dataMin', 'dataMax']}
                    tickFormatter={(v) => v.toFixed(0)}
                    stroke="var(--axis)"
                    label={{ value: 'Spot', position: 'insideBottom', offset: -12 }}
                  />
                  <YAxis stroke="var(--axis)" width={64} tickFormatter={(v) => Number(v.toPrecision(3)).toString()} label={{ value: yLabel, angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }} />
                  <Tooltip content={<ChartTooltip labelFormat={(v) => `Spot ${Number(v).toFixed(2)}`} valueFormat={(v) => fmt(v)} />} />
                  <ReferenceLine x={s.S} stroke="var(--muted)" strokeDasharray="4 3" />
                  <Line type="monotone" dataKey="now" name={`${s.days}d`} stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="short" name={`${shortDays}d`} stroke="var(--series-2)" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="card">
            <h2>{m.label} as expiry approaches (spot {s.S.toFixed(1)})</h2>
            <div className="chart-box short">
              <ResponsiveContainer>
                <LineChart data={byTime} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis
                    dataKey="days"
                    type="number"
                    reversed
                    domain={['dataMin', 'dataMax']}
                    tickFormatter={(v) => v.toFixed(0)}
                    stroke="var(--axis)"
                    label={{ value: 'Days to expiry', position: 'insideBottom', offset: -12 }}
                  />
                  <YAxis stroke="var(--axis)" width={64} tickFormatter={(v) => Number(v.toPrecision(3)).toString()} />
                  <Tooltip content={<ChartTooltip labelFormat={(v) => `${Number(v).toFixed(1)} days left`} valueFormat={(v) => fmt(v)} />} />
                  <Line type="monotone" dataKey="value" name={m.label} stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <Predict />
        </div>
      </div>
    </>
  );
}
