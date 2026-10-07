import React, { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  MAX_WIDTH,
  NUM_CARDS,
  baselineTrades,
  cardLabel,
  counterparty,
  deal,
  fairValue,
  pnl,
  validateQuote,
} from '../lib/marketMaking';

const fmt = (x) => (Number.isInteger(x) ? String(x) : x.toFixed(2));
const signed = (x) => `${x > 0 ? '+' : x < 0 ? '−' : ''}${fmt(Math.abs(x))}`;
const randomSeed = () => Math.floor(Math.random() * 2 ** 31);

function Card({ card, hidden }) {
  if (hidden || !card) {
    return (
      <div className="playing-card face-down" aria-label="Face-down card">
        ?
      </div>
    );
  }
  const red = card.suit === '♥' || card.suit === '♦';
  return (
    <div className={`playing-card${red ? ' red' : ''}`} aria-label={`${cardLabel(card)}, worth ${card.value}`}>
      {cardLabel(card)}
    </div>
  );
}

function describeTrade(t) {
  if (!t.side) return 'Nobody traded.';
  return t.side < 0 ? `Someone bought from you: you sold 1 at ${fmt(t.price)}.` : `Someone sold to you: you bought 1 at ${fmt(t.price)}.`;
}

function roundList(rounds) {
  const names = rounds.map((r) => r + 1);
  if (names.length === 1) return `Round ${names[0]}`;
  return `Rounds ${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}

function lessons(game, trades, baselinePnl) {
  const out = [];
  const informed = trades.filter((t) => t.informed);
  if (informed.length) {
    const sides = new Set(informed.map((t) => (t.side < 0 ? 'bought from' : 'sold to')));
    out.push(
      `${roundList(informed.map((t) => t.round))}: the trader who ${[...sides].join(' and ')} you had seen the ` +
        `${cardLabel(game.cards[NUM_CARDS - 1])}. When someone trades with you, assume they know something and ` +
        `move your next quote toward their side.`,
    );
  }
  const offCenter = trades.filter((t) => {
    const fair = fairValue(game.cards.slice(0, t.round));
    return Math.abs((t.bid + t.ask) / 2 - fair) > 1.5;
  });
  if (offCenter.length) {
    out.push(
      `${roundList(offCenter.map((t) => t.round))}: your mid was more than 1.5 away from fair value. Anchor on ` +
        `E[sum] = revealed cards + (cards left) × (average of the cards still in the deck).`,
    );
  }
  if (baselinePnl < 0 && informed.length) {
    out.push(
      `The textbook market maker lost too (${signed(baselinePnl)}): quoting the public fair value isn't enough ` +
        `against informed flow. The edge comes from updating after every trade.`,
    );
  }
  if (out.length === 0) out.push('Clean game: your quotes stayed near fair value and nobody picked you off.');
  return out;
}

export default function MarketMaking() {
  const [params, setParams] = useSearchParams();
  const urlSeed = Number(params.get('seed'));
  const [seed, setSeed] = useState(Number.isInteger(urlSeed) && urlSeed > 0 ? urlSeed : randomSeed());
  const game = useMemo(() => deal(seed), [seed]);
  const [round, setRound] = useState(0);
  const [trades, setTrades] = useState([]);
  const [bid, setBid] = useState('');
  const [ask, setAsk] = useState('');
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const quoted = trades.length > round; // current round already quoted
  const done = trades.length === MAX_WIDTH.length && round >= MAX_WIDTH.length;
  const position = trades.reduce((s, t) => s + (t.side || 0), 0);
  const revealedCount = Math.min(round, NUM_CARDS);

  const restart = (newSeed) => {
    setSeed(newSeed);
    setRound(0);
    setTrades([]);
    setBid('');
    setAsk('');
    setError(null);
    setCopied(false);
    setParams({});
  };

  const submit = (e) => {
    e.preventDefault();
    const b = Number(bid);
    const a = Number(ask);
    const problem = validateQuote(bid === '' ? NaN : b, ask === '' ? NaN : a, round);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    setTrades((ts) => [...ts, { round, bid: b, ask: a, ...counterparty(game, round, b, a) }]);
  };

  const shareUrl = `${window.location.origin}/market-making?seed=${seed}`;
  const copy = async () => {
    const text = `I made ${signed(pnl(trades, game.settlement))} market making on this deal. Can you beat it? ${shareUrl}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      window.prompt('Copy this link:', text);
    }
  };

  const current = trades[round];
  const base = done ? baselineTrades(game) : null;

  return (
    <>
      <div className="page-header">
        <h1>Market Making</h1>
        <p>
          The trading-firm interview classic. The contract settles at the <strong>sum of {NUM_CARDS} cards</strong> from
          a standard deck (A = 1 … K = 13). Each round you quote a bid and an ask, and someone may trade one lot with
          you. Some counterparties know more than you do.
        </p>
      </div>
      <div className="grid-2">
        <div className="card">
          <div className="card-row" aria-label="Cards">
            {game.cards.map((c, i) => (
              <Card key={i} card={c} hidden={!done && i >= revealedCount} />
            ))}
          </div>
          <dl className="kv" style={{ margin: '1rem 0' }}>
            <div>
              <dt>Round</dt>
              <dd>{done ? 'Settled' : `${round + 1} of ${MAX_WIDTH.length}`}</dd>
            </div>
            <div>
              <dt>Position</dt>
              <dd>{signed(position) || '0'}</dd>
            </div>
            <div>
              <dt>Max spread</dt>
              <dd>{done ? '–' : MAX_WIDTH[round]}</dd>
            </div>
          </dl>

          {!done && !quoted && (
            <form onSubmit={submit}>
              <div className="row">
                <div className="field" style={{ flex: '1 1 100px' }}>
                  <label htmlFor="bid">Bid</label>
                  <input id="bid" type="number" step="0.5" inputMode="decimal" value={bid} onChange={(e) => setBid(e.target.value)} />
                </div>
                <div className="field" style={{ flex: '1 1 100px' }}>
                  <label htmlFor="ask">Ask</label>
                  <input id="ask" type="number" step="0.5" inputMode="decimal" value={ask} onChange={(e) => setAsk(e.target.value)} />
                </div>
              </div>
              {error && <div className="notice notice-error" style={{ marginBottom: '0.75rem' }}>{error}</div>}
              <button className="btn" type="submit">
                Quote
              </button>
              <p className="small muted" style={{ marginTop: '0.75rem', marginBottom: 0 }}>
                You buy at your bid and sell at your ask, one lot per round. Positive position = long the sum.
              </p>
            </form>
          )}

          {!done && quoted && (
            <div className="stack">
              <div className="feedback" role="status">
                <strong>{describeTrade(current)}</strong>
                Fair value given the cards shown: <span className="num">{fmt(fairValue(game.cards.slice(0, round)))}</span>
                . Your mid: <span className="num">{fmt((current.bid + current.ask) / 2)}</span>.
              </div>
              <div>
                <button
                  className="btn"
                  type="button"
                  onClick={() => {
                    setRound(round + 1);
                    setBid('');
                    setAsk('');
                  }}
                >
                  {round + 1 < MAX_WIDTH.length ? 'Reveal next card →' : 'Settle →'}
                </button>
              </div>
            </div>
          )}

          {done && (
            <div className="stack">
              <div>
                <div className="muted small">Settles at {game.settlement}. Your P&amp;L</div>
                <div className="big-score">{signed(pnl(trades, game.settlement))}</div>
                <p className="small muted" style={{ marginTop: '0.5rem' }}>
                  A textbook market maker (fair value ± max spread / 2) made{' '}
                  <strong>{signed(pnl(base, game.settlement))}</strong> on the same deal.
                </p>
              </div>
              <div className="row">
                <button className="btn" type="button" onClick={() => restart(randomSeed())}>
                  New deal
                </button>
                <button className="btn btn-secondary" type="button" onClick={() => restart(seed)}>
                  Replay this deal
                </button>
                <button className="btn btn-secondary" type="button" onClick={copy}>
                  {copied ? 'Copied ✓' : 'Copy challenge link'}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="stack">
          <div className="card">
            <h2>Trades</h2>
            {trades.length === 0 ? (
              <p className="muted small">No quotes yet. Start with the expected sum of three cards.</p>
            ) : (
              <table className="data">
                <thead>
                  <tr>
                    <th>Round</th>
                    <th>Your quote</th>
                    <th>Fair</th>
                    <th>Trade</th>
                    {done && <th>Who</th>}
                    {done && <th>P&amp;L</th>}
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t) => (
                    <tr key={t.round}>
                      <td>{t.round + 1}</td>
                      <td>
                        {fmt(t.bid)} / {fmt(t.ask)}
                      </td>
                      <td>{fmt(fairValue(game.cards.slice(0, t.round)))}</td>
                      <td>{t.side ? `${t.side > 0 ? 'Bought' : 'Sold'} @ ${fmt(t.price)}` : '–'}</td>
                      {done && <td>{t.side ? (t.informed ? 'Informed' : 'Noise') : '–'}</td>}
                      {done && <td>{t.side ? signed(t.side * (game.settlement - t.price)) : '–'}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          {done && (
            <div className="card">
              <h2>What to take away</h2>
              <ul style={{ margin: 0, paddingLeft: '1.2rem' }}>
                {lessons(game, trades, pnl(base, game.settlement)).map((l) => (
                  <li key={l} style={{ marginBottom: '0.5rem' }}>
                    {l}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="card">
            <h2>How it works</h2>
            <ul className="small" style={{ margin: 0, paddingLeft: '1.2rem' }}>
              <li>Fair value = revealed cards + (cards left) × (average of the cards still in the deck).</li>
              <li>One counterparty has secretly seen the last card. They trade only when your quote is wrong by at least 0.5.</li>
              <li>Others trade at random. Those trades are free money on average if your quote is centered on fair value.</li>
              <li>Firms grade the process: anchor on expectation, keep spreads honest, and update after every trade.</li>
            </ul>
          </div>
        </div>
      </div>
    </>
  );
}
