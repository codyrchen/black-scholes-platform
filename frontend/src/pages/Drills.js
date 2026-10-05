import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiGet, apiPost } from '../api';
import { recordRound } from '../lib/stats';

const CATEGORIES = [
  ['mental_math', 'Mental math'],
  ['greeks', 'Greeks intuition'],
  ['pricing', 'Pricing'],
  ['arbitrage', 'Arbitrage'],
];
const DIFFICULTIES = ['easy', 'medium', 'hard'];
const SECONDS_PER_QUESTION = 12;

function parseList(value, allowed) {
  if (!value) return [];
  return value.split(',').filter((v) => allowed.includes(v));
}

function useConfigFromUrl() {
  const [params] = useSearchParams();
  return {
    categories: parseList(params.get('category'), CATEGORIES.map((c) => c[0])),
    difficulties: parseList(params.get('difficulty'), DIFFICULTIES),
    count: [5, 10, 20].includes(Number(params.get('count'))) ? Number(params.get('count')) : 10,
    timed: params.get('timed') !== '0',
    seed: params.get('seed') ? Number(params.get('seed')) : null,
  };
}

function configKey(c) {
  return [c.categories.join('+') || 'all', c.difficulties.join('+') || 'all', c.count, c.timed ? 't' : 'u'].join('|');
}

function Toggle({ pressed, onClick, children }) {
  return (
    <button type="button" className="chip" aria-pressed={pressed} onClick={onClick}>
      {children}
    </button>
  );
}

function Setup({ initial, onStart, error }) {
  const [cfg, setCfg] = useState(initial);
  const toggle = (key, value) =>
    setCfg((c) => ({
      ...c,
      [key]: c[key].includes(value) ? c[key].filter((v) => v !== value) : [...c[key], value],
    }));
  return (
    <div className="card drill-card stack">
      <div>
        <label>Topics</label>
        <div className="chips">
          {CATEGORIES.map(([id, name]) => (
            <Toggle key={id} pressed={cfg.categories.includes(id)} onClick={() => toggle('categories', id)}>
              {name}
            </Toggle>
          ))}
        </div>
        <small className="muted">None selected means all topics.</small>
      </div>
      <div>
        <label>Difficulty</label>
        <div className="chips">
          {DIFFICULTIES.map((d) => (
            <Toggle key={d} pressed={cfg.difficulties.includes(d)} onClick={() => toggle('difficulties', d)}>
              {d[0].toUpperCase() + d.slice(1)}
            </Toggle>
          ))}
        </div>
      </div>
      <div className="row">
        <div>
          <label>Questions</label>
          <div className="segmented">
            {[5, 10, 20].map((n) => (
              <button key={n} type="button" aria-pressed={cfg.count === n} onClick={() => setCfg({ ...cfg, count: n })}>
                {n}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label>Clock</label>
          <div className="segmented">
            <button type="button" aria-pressed={cfg.timed} onClick={() => setCfg({ ...cfg, timed: true })}>
              Timed ({SECONDS_PER_QUESTION}s each)
            </button>
            <button type="button" aria-pressed={!cfg.timed} onClick={() => setCfg({ ...cfg, timed: false })}>
              Untimed
            </button>
          </div>
        </div>
      </div>
      {cfg.seed != null && (
        <p className="small muted">
          You're playing a shared challenge round (#{cfg.seed}). Everyone with this link gets the same questions.
        </p>
      )}
      {error && <div className="notice notice-error">{error}</div>}
      <div>
        <button type="button" className="btn" onClick={() => onStart(cfg)}>
          Start round
        </button>
      </div>
    </div>
  );
}

function Question({ q, index, total, secondsLeft, onAnswered }) {
  const [value, setValue] = useState('');
  const [result, setResult] = useState(null);
  const [picked, setPicked] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    setValue('');
    setResult(null);
    setPicked(null);
    setError(null);
    if (inputRef.current) inputRef.current.focus();
  }, [q.id]);

  const submit = async (response) => {
    if (busy || result) return;
    setBusy(true);
    setError(null);
    try {
      const r = await apiPost('/api/v1/drills/check', { id: q.id, response });
      setResult(r);
      onAnswered(q, response, r);
    } catch (e) {
      setError(e.message);
    }
    setBusy(false);
  };

  return (
    <>
      <div className="progress" aria-hidden="true">
        <div style={{ width: `${(100 * index) / total}%` }} />
      </div>
      <div className="drill-meta">
        <span>
          Question {index + 1} of {total} · <span className="badge">{q.difficulty}</span>
        </span>
        {secondsLeft != null && <span aria-live="off">{Math.max(secondsLeft, 0)}s left</span>}
      </div>
      <p className="prompt">{q.prompt}</p>
      {q.answer_type === 'choice' ? (
        <div className="choices">
          {q.choices.map((c, i) => {
            let cls = 'choice';
            if (result) {
              if (i === result.answer) cls += ' correct';
              else if (i === picked) cls += ' wrong';
            }
            return (
              <button
                key={c}
                type="button"
                className={cls}
                disabled={!!result || busy}
                onClick={() => {
                  setPicked(i);
                  submit(i);
                }}
              >
                {c}
              </button>
            );
          })}
        </div>
      ) : (
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            if (value.trim() !== '') submit(value.trim());
          }}
        >
          <div style={{ flex: '1 1 200px' }}>
            <label htmlFor="answer">
              Your answer{q.unit ? ` (${q.unit})` : ''} · graded {q.tolerance}
            </label>
            <input
              id="answer"
              ref={inputRef}
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={value}
              disabled={!!result}
              onChange={(e) => setValue(e.target.value.replace(/[$,%\s]/g, ''))}
            />
          </div>
          <button className="btn" type="submit" disabled={!!result || busy || value.trim() === ''} style={{ alignSelf: 'flex-end' }}>
            Check
          </button>
        </form>
      )}
      {error && <div className="notice notice-error" style={{ marginTop: '1rem' }}>{error}</div>}
      {result && (
        <div className={`feedback ${result.correct ? 'correct' : 'wrong'}`} role="status">
          <strong className={result.correct ? 'status-good' : 'status-bad'}>
            {result.correct ? '✓ Correct' : `✗ Not quite. Answer: ${result.answer_display}`}
          </strong>
          {result.explanation}
        </div>
      )}
    </>
  );
}

function Summary({ log, config, seed, best, onAgain, onReplay }) {
  const correct = log.filter((l) => l.result && l.result.correct).length;
  const [copied, setCopied] = useState(false);
  const shareUrl = (() => {
    const p = new URLSearchParams();
    if (config.categories.length) p.set('category', config.categories.join(','));
    if (config.difficulties.length) p.set('difficulty', config.difficulties.join(','));
    p.set('count', String(config.count));
    p.set('timed', config.timed ? '1' : '0');
    p.set('seed', String(seed));
    return `${window.location.origin}/drills?${p.toString()}`;
  })();
  const shareText = `I scored ${correct}/${config.count} on this options drill. Can you beat it? ${shareUrl}`;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
    } catch {
      window.prompt('Copy this link:', shareText);
    }
  };
  return (
    <div className="stack drill-card">
      <div className="card">
        <div className="big-score">
          {correct}/{config.count}
        </div>
        <p className="muted" style={{ marginTop: '0.5rem' }}>
          {best.isBest
            ? best.previousBest
              ? `New best for this setup (previous ${best.previousBest.correct}/${best.previousBest.total}).`
              : 'First score recorded for this setup.'
            : `Your best for this setup is ${best.stats.best[configKey(config)].correct}/${config.count}.`}{' '}
          {log.length < config.count && `${config.count - log.length} unanswered when time ran out.`}
        </p>
        <div className="row">
          <button className="btn" type="button" onClick={onAgain}>
            New round
          </button>
          <button className="btn btn-secondary" type="button" onClick={onReplay}>
            Retry same questions
          </button>
          <button className="btn btn-secondary" type="button" onClick={copy}>
            {copied ? 'Copied ✓' : 'Copy challenge link'}
          </button>
        </div>
      </div>
      <div className="card">
        <h2>Review</h2>
        <ul className="review-list">
          {log.map(({ q, response, result }) => (
            <li key={q.id}>
              <p style={{ marginBottom: '0.4rem' }}>{q.prompt}</p>
              <p className="small" style={{ marginBottom: '0.4rem' }}>
                <span className={result.correct ? 'status-good' : 'status-bad'}>
                  {result.correct ? '✓ Correct' : '✗ Incorrect'}
                </span>
                {' · '}You: {q.answer_type === 'choice' ? q.choices[response] : response} · Answer: {result.answer_display}
              </p>
              <p className="small muted" style={{ marginBottom: 0 }}>
                {result.explanation}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function Drills() {
  const initial = useConfigFromUrl();
  const [phase, setPhase] = useState('setup');
  const [config, setConfig] = useState(initial);
  const [round, setRound] = useState(null);
  const [index, setIndex] = useState(0);
  const [log, setLog] = useState([]);
  const [deadline, setDeadline] = useState(null);
  const [now, setNow] = useState(Date.now());
  const [best, setBest] = useState(null);
  const [error, setError] = useState(null);
  const answeredRef = useRef(false);

  const start = useCallback(async (cfg, seedOverride) => {
    setError(null);
    const p = new URLSearchParams();
    if (cfg.categories.length) p.set('category', cfg.categories.join(','));
    if (cfg.difficulties.length) p.set('difficulty', cfg.difficulties.join(','));
    p.set('count', String(cfg.count));
    const seed = seedOverride ?? cfg.seed;
    if (seed != null) p.set('seed', String(seed));
    try {
      const r = await apiGet(`/api/v1/drills?${p.toString()}`);
      setConfig(cfg);
      setRound(r);
      setIndex(0);
      setLog([]);
      answeredRef.current = false;
      setDeadline(cfg.timed ? Date.now() + cfg.count * SECONDS_PER_QUESTION * 1000 : null);
      setPhase('play');
    } catch (e) {
      setError(e.message);
      setPhase('setup');
    }
  }, []);

  const finish = useCallback(
    (finalLog) => {
      setBest(recordRound(configKey(config), finalLog.filter((l) => l.result.correct).length, config.count));
      setPhase('done');
    },
    [config],
  );

  useEffect(() => {
    if (phase !== 'play' || !deadline) return undefined;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [phase, deadline]);

  useEffect(() => {
    if (phase === 'play' && deadline && now >= deadline) finish(log);
  }, [now, deadline, phase, finish, log]);

  const onAnswered = (q, response, result) => {
    answeredRef.current = true;
    setLog((l) => [...l, { q, response, result }]);
  };

  const next = () => {
    answeredRef.current = false;
    if (index + 1 >= round.questions.length) finish(log);
    else setIndex(index + 1);
  };

  // Enter moves to the next question once the current one is graded.
  useEffect(() => {
    if (phase !== 'play') return undefined;
    const onKey = (e) => {
      if (e.key === 'Enter' && answeredRef.current && log.length === index + 1) {
        e.preventDefault();
        next();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  return (
    <>
      <div className="page-header">
        <h1>Drills</h1>
        <p>
          Short rounds of interview-style questions. Mental-math answers are graded with a tolerance that accepts
          the standard rules of thumb, so practice the shortcuts.
        </p>
      </div>
      {phase === 'setup' && <Setup initial={config} onStart={(cfg) => start(cfg)} error={error} />}
      {phase === 'play' && round && (
        <div className="card drill-card">
          <Question
            q={round.questions[index]}
            index={index}
            total={round.questions.length}
            secondsLeft={deadline ? Math.ceil((deadline - now) / 1000) : null}
            onAnswered={onAnswered}
          />
          {log.length === index + 1 && (
            <div className="row" style={{ marginTop: '1rem' }}>
              <button className="btn" type="button" onClick={next} autoFocus>
                {index + 1 >= round.questions.length ? 'See results' : 'Next question →'}
              </button>
              <span className="small muted">or press Enter</span>
            </div>
          )}
        </div>
      )}
      {phase === 'done' && best && (
        <Summary
          log={log}
          config={config}
          seed={round.seed}
          best={best}
          onAgain={() => start({ ...config, seed: null })}
          onReplay={() => start(config, round.seed)}
        />
      )}
    </>
  );
}
