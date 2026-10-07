import React, { useState } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { apiPost } from '../api';
import ChartTooltip from '../components/ChartTooltip';

const FIELDS = [
  ['spot', 'Spot price', '0.01'],
  ['strike', 'Strike price', '0.01'],
  ['maturity', 'Time to expiry (years)', '0.01'],
  ['rate', 'Risk-free rate (decimal, 0.05 = 5%)', '0.001'],
  ['volatility', 'Volatility (decimal, 0.2 = 20%)', '0.01'],
  ['dividend_yield', 'Dividend yield (decimal)', '0.001'],
];

const fmt = (x, d = 4) => Number(x).toFixed(d);

export default function Calculator() {
  const [inputs, setInputs] = useState({
    spot: 100,
    strike: 100,
    maturity: 0.25,
    rate: 0.05,
    volatility: 0.2,
    dividend_yield: 0,
    option_type: 'call',
  });
  const [result, setResult] = useState(null);
  const [curve, setCurve] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [marketPrice, setMarketPrice] = useState('');
  const [iv, setIv] = useState(null);
  const [ivError, setIvError] = useState(null);

  const onChange = (e) => {
    const { name, value } = e.target;
    setInputs((prev) => ({ ...prev, [name]: name === 'option_type' ? value : value === '' ? '' : Number(value) }));
  };

  const calculate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const priced = await apiPost('/api/v1/price', inputs);
      const payoff = await apiPost('/api/v1/payoff', {
        strike: inputs.strike,
        premium: priced.price,
        option_type: inputs.option_type,
        maturity: inputs.maturity,
        rate: inputs.rate,
        volatility: inputs.volatility,
        dividend_yield: inputs.dividend_yield,
      });
      setResult(priced);
      setCurve(payoff.payoffs);
    } catch (err) {
      setError(err.message);
      setResult(null);
      setCurve([]);
    }
    setLoading(false);
  };

  const solveIv = async (e) => {
    e.preventDefault();
    setIvError(null);
    setIv(null);
    try {
      setIv(
        await apiPost('/api/v1/implied-vol', {
          market_price: Number(marketPrice),
          spot: inputs.spot,
          strike: inputs.strike,
          maturity: inputs.maturity,
          rate: inputs.rate,
          dividend_yield: inputs.dividend_yield,
          option_type: inputs.option_type,
        }),
      );
    } catch (err) {
      setIvError(err.message);
    }
  };

  return (
    <>
      <div className="page-header">
        <h1>Calculator</h1>
        <p>
          Black-Scholes-Merton price and Greeks for a European option, an implied-vol solver, and the P&amp;L of
          the long option today versus at expiry.
        </p>
      </div>
      <div className="grid-2">
        <div className="stack">
          <form className="card" onSubmit={calculate}>
            <div className="field">
              <label htmlFor="option_type">Option type</label>
              <select id="option_type" name="option_type" value={inputs.option_type} onChange={onChange}>
                <option value="call">Call</option>
                <option value="put">Put</option>
              </select>
            </div>
            {FIELDS.map(([name, label, step]) => (
              <div className="field" key={name}>
                <label htmlFor={name}>{label}</label>
                <input id={name} type="number" name={name} value={inputs[name]} onChange={onChange} step={step} />
              </div>
            ))}
            <button type="submit" className="btn btn-block" disabled={loading}>
              {loading ? 'Calculating…' : 'Calculate'}
            </button>
          </form>
          <form className="card" onSubmit={solveIv}>
            <h2>Implied vol</h2>
            <p className="small muted">Uses the inputs above, except volatility, and solves for the vol that reproduces a market price.</p>
            <div className="field">
              <label htmlFor="market_price">Market price</label>
              <input id="market_price" type="number" step="0.01" value={marketPrice} onChange={(e) => setMarketPrice(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-secondary btn-block" disabled={marketPrice === ''}>
              Solve
            </button>
            {iv && (
              <p style={{ marginTop: '0.75rem', marginBottom: 0 }}>
                Implied vol <strong className="num">{(iv.implied_vol * 100).toFixed(3)}%</strong>{' '}
                <span className="small muted">
                  ({iv.method === 'newton' ? `Newton, ${iv.iterations} iterations` : 'Brent fallback'})
                </span>
              </p>
            )}
            {ivError && <div className="notice notice-error" style={{ marginTop: '0.75rem' }}>{ivError}</div>}
          </form>
        </div>
        <div className="stack">
          {error && <div className="notice notice-error">{error}</div>}
          {!result && !error && <div className="card muted">Set the inputs and press Calculate.</div>}
          {result && (
            <>
              <div className="card">
                <h2>
                  {inputs.option_type === 'call' ? 'Call' : 'Put'} price: <span className="num">${fmt(result.price)}</span>
                </h2>
                <dl className="kv">
                  <div><dt>Delta</dt><dd>{fmt(result.greeks.delta)}</dd></div>
                  <div><dt>Gamma</dt><dd>{fmt(result.greeks.gamma)}</dd></div>
                  <div><dt>Theta / day</dt><dd>{fmt(result.greeks.theta)}</dd></div>
                  <div><dt>Vega / 1%</dt><dd>{fmt(result.greeks.vega)}</dd></div>
                  <div><dt>Rho / 1%</dt><dd>{fmt(result.greeks.rho)}</dd></div>
                </dl>
              </div>
              <div className="card">
                <h2>Profit / loss of the long option</h2>
                <div className="legend">
                  <span><i style={{ background: 'var(--series-1)' }} />At expiry</span>
                  <span><i style={{ background: 'var(--series-2)' }} />Today</span>
                </div>
                <div className="chart-box">
                  <ResponsiveContainer>
                    <LineChart data={curve} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
                      <CartesianGrid stroke="var(--grid)" vertical={false} />
                      <XAxis dataKey="spot" type="number" domain={['dataMin', 'dataMax']} tickFormatter={(v) => v.toFixed(0)} stroke="var(--axis)" label={{ value: 'Spot', position: 'insideBottom', offset: -12 }} />
                      <YAxis stroke="var(--axis)" width={56} tickFormatter={(v) => `${v < 0 ? '−' : ''}$${Math.abs(v).toFixed(0)}`} />
                      <Tooltip content={<ChartTooltip labelFormat={(v) => `Spot ${v}`} valueFormat={(v) => `$${v.toFixed(2)}`} />} />
                      <ReferenceLine y={0} stroke="var(--axis)" />
                      <Line dataKey="payoff" name="At expiry" stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
                      <Line dataKey="value" name="Today" stroke="var(--series-2)" strokeWidth={2} dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="small muted" style={{ marginBottom: 0 }}>Computed in {result.response_time_ms} ms.</p>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
