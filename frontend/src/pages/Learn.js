import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

// Each article's numbers come from frontend/public/research/results.json, written by
// the scripts in research/. Rerun those scripts and the text updates with them.

const pct = (x, d = 1) => `${(x * 100).toFixed(d)}%`;
// Round before taking the sign so tiny negatives don't print as "−$0.00".
const money = (x) => {
  if (x == null) return '–';
  const v = Math.round(x * 100) / 100;
  return `${v < 0 ? '−' : ''}$${Math.abs(v).toFixed(2)}`;
};

function Figure({ src, alt, caption }) {
  return (
    <figure>
      <img src={`/research/${src}`} alt={alt} loading="lazy" />
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}

function Hedging({ r }) {
  const f = r.frequency;
  const mm = r.vol_mismatch;
  const i63 = f.steps.indexOf(63);
  return (
    <>
      <p>
        Black-Scholes says a short option can be hedged perfectly by holding Δ shares, <em>if you rebalance
        continuously</em>. Nobody can. So how much risk is left when you rebalance a finite number of times, and what
        happens when the market moves more or less than the implied vol you sold at?
      </p>
      <p>
        Setup: sell a 3-month at-the-money call (S = K = {r.params.S}, implied vol {pct(r.params.implied_vol, 0)},
        rates {pct(r.params.r, 0)}) for {money(f.premium)}, delta hedge it N times, and repeat over{' '}
        {r.params.paths.toLocaleString()} simulated paths.
      </p>
      <h2>Error shrinks like 1/√N</h2>
      <Figure
        src="hedging_error.png"
        alt="Log-log chart: standard deviation of hedged P&L against number of rebalances, falling along a 1/√N line"
        caption="Standard deviation of the final hedged P&L. Dashed: a 1/√N line through the first point."
      />
      <p className="finding">
        The fitted log-log slope is <strong>{f.slope.toFixed(2)}</strong>, against a theoretical −0.5. Rebalancing
        4× as often only halves the error. Even daily hedging ({f.steps[i63]} rebalances) leaves a standard deviation
        of {money(f.std[i63])}, about {f.daily_std_pct_of_premium}% of the premium.
      </p>
      <p>
        Why ½? Over each interval the hedged book earns <code>½·Γ·S²·(σ²·dt − (ΔS/S)²)</code>: the theta it collects
        minus the gamma it pays on the realized move. Each term has mean zero when realized vol equals implied, and a
        standard deviation proportional to <code>dt</code>. Summing N independent terms of size 1/N gives a total of
        size √N · 1/N = 1/√N.
      </p>
      <h2>The vol you realize decides the sign</h2>
      <Figure
        src="hedging_vol_mismatch.png"
        alt="Three histograms of hedged P&L for realized vol 10%, 20% and 30%, centered near +2, 0 and −2"
        caption="Final P&L of the hedged short call, rebalanced daily, for three realized vols. Implied vol is 20% in every case."
      />
      <p className="finding">
        Realized 10%: mean {money(mm['10'].mean)}. Realized 20%: {money(mm['20'].mean)}. Realized 30%:{' '}
        {money(mm['30'].mean)}. The first-order prediction, vega × (σ<sub>implied</sub> − σ<sub>realized</sub>), is{' '}
        {money(mm['10'].vega_prediction)} and {money(mm['30'].vega_prediction)}.
      </p>
      <p>
        That's what an options trader is actually trading: implied versus realized volatility. Delta hedging removes
        the direction of the stock but leaves the vol bet, so hedging more often doesn't help a short option position
        when realized vol is high. It just makes the loss more certain. Notice too that the 30% distribution is wide
        and skewed: big moves hit a short gamma position hardest.
      </p>
      <p>
        <Link to="/hedging">Try it yourself in the Hedging Game →</Link>
      </p>
    </>
  );
}

function Convergence({ r }) {
  return (
    <>
      <p>
        Black-Scholes has a closed form for European options. Most real products (American options, path-dependent
        payoffs) don't, so they're priced numerically. A good way to trust a numerical method is to check it against
        the cases where you know the answer. Test case: a 1-year call, S = {r.params.S}, K = {r.params.K}, r ={' '}
        {pct(r.params.r, 0)}, σ = {pct(r.params.sigma, 0)}; Black-Scholes price {money(r.bs_price)}.
      </p>
      <h2>Binomial trees: 1/N, with wobbles</h2>
      <Figure
        src="convergence_crr.png"
        alt="Log-log chart of binomial tree pricing error against number of steps, roughly following a 1/N line with large oscillations"
        caption="Absolute error of the Cox-Ross-Rubinstein tree against Black-Scholes."
      />
      <p className="finding">
        The fitted slope is <strong>{r.crr_slope.toFixed(2)}</strong> (theory: −1), but the error oscillates by more
        than an order of magnitude: as N changes, the strike moves relative to the tree's terminal nodes. More steps
        is not always more accurate, which is why practitioners average adjacent N or smooth the payoff.
      </p>
      <p>
        The same tree prices American options by taking <code>max(continuation, exercise)</code> at every node. For
        the put on the same terms: American {money(r.american_put)} vs European {money(r.european_put)}, an early
        exercise premium of {money(r.early_exercise_premium)}.
      </p>
      <h2>Monte Carlo: 1/√N, and variance reduction is free speed</h2>
      <Figure
        src="convergence_mc.png"
        alt="Log-log chart of Monte Carlo standard error against paths for three estimators, all parallel lines with slope minus one half"
        caption="Standard error of the Monte Carlo estimate for three estimators."
      />
      <p className="finding">
        Slope <strong>{r.mc_slope.toFixed(2)}</strong> (theory: −0.5), so 100× the paths buys 10× the accuracy.
        Antithetic variates plus a control variate (the discounted stock, whose expectation is known exactly) cut the
        variance by a factor of <strong>{r.variance_reduction_factor}</strong>, the same as running{' '}
        {Math.round(r.variance_reduction_factor)}× more paths. With 1M paths: {r.mc_price_1m.toFixed(4)} ±{' '}
        {r.mc_stderr_1m.toFixed(4)} vs exact {r.bs_price.toFixed(4)}.
      </p>
      <p>
        Every claim on this page is also a unit test in <code>tests/test_numerical_methods.py</code>: convergence to
        Black-Scholes, American ≥ European, and an American call with no dividends equal to the European one.
      </p>
    </>
  );
}

function Smile({ r }) {
  return (
    <>
      <p>
        Black-Scholes assumes one volatility for every strike. If that were true, solving for implied vol across a
        real option chain would give a flat line. It doesn't.
      </p>
      <Figure
        src="vol_smile.png"
        alt={`${r.ticker} implied volatility by log-moneyness for several expiries`}
        caption={`${r.ticker} option chain snapshot, ${r.as_of.slice(0, 10)}. Source: ${r.source}. Out-of-the-money options only.`}
      />
      <table className="data">
        <thead>
          <tr><th>Expiry</th><th>Days</th><th>Implied rate</th><th>90% strike vol</th><th>ATM vol</th><th>110% strike vol</th></tr>
        </thead>
        <tbody>
          {r.expiries.map((e) => (
            <tr key={e.expiry}>
              <td>{e.expiry}</td><td>{e.days}</td><td>{pct(e.implied_rate, 2)}</td><td>{pct(e.vol_90)}</td><td>{pct(e.atm_vol)}</td><td>{pct(e.vol_110)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>
        Method: for each expiry, put-call parity <code>C − P = DF·(F − K)</code> is linear in K, so a regression on
        near-the-money strikes gives the market's own discount factor and forward. No guessed rate or dividend is
        needed. Implied vols come from out-of-the-money options only, which are the liquid ones. The procedure is
        tested against a synthetic chain with a known smile in <code>tests/test_smile.py</code>.
      </p>
    </>
  );
}

function WhyWrong({ hasSmile }) {
  return (
    <>
      <p>
        Black-Scholes is the language of options markets, but nobody believes its assumptions. Knowing exactly where
        it breaks is a standard interview topic.
      </p>
      <ul>
        <li>
          <strong>Constant volatility.</strong> Implied vol varies by strike (the smile or skew) and by expiry (the
          term structure).{' '}
          {hasSmile ? <Link to="/learn/smile">See a real smile →</Link> : 'Run research/vol_smile.py to see a real one.'}
        </li>
        <li>
          <strong>Lognormal returns.</strong> Real returns have fat tails and crash more than they rally. That's why
          equity index puts trade at higher implied vols than calls: the market charges for crash risk.
        </li>
        <li>
          <strong>Continuous, costless hedging.</strong> Hedging happens in discrete time with transaction costs,
          leaving residual risk. <Link to="/learn/hedging">See how much →</Link>
        </li>
        <li>
          <strong>Known, constant rates and dividends.</strong> Both change, and dividends are discrete cash payments.
        </li>
        <li>
          <strong>No jumps.</strong> Earnings, macro news and gaps overnight move prices discontinuously, and delta
          hedging can't protect against a jump.
        </li>
      </ul>
      <p>
        So why use it? Because implied vol is a convenient <em>quoting convention</em>: traders quote options in vol
        rather than dollars, and Black-Scholes is the map between the two. The model's Greeks are still the first
        approximation of risk, and models that fix its flaws (local vol, stochastic vol, jump diffusion) are
        calibrated to reproduce the Black-Scholes implied vol surface.
      </p>
    </>
  );
}

const ARTICLES = [
  { slug: 'hedging', title: "Why delta hedging isn't perfect", blurb: 'Hedge error scales like 1/√N, and realized vs implied vol decides the P&L.', needs: 'hedging', Body: Hedging },
  { slug: 'convergence', title: 'Trees vs Monte Carlo', blurb: 'How fast numerical pricers converge, and what variance reduction buys.', needs: 'convergence', Body: Convergence },
  { slug: 'smile', title: 'The volatility smile', blurb: 'Implied vols from a real option chain, with rates backed out of parity.', needs: 'smile', Body: Smile },
  { slug: 'why-bs-is-wrong', title: 'Where Black-Scholes breaks', blurb: 'The assumptions, how markets violate them, and why the model survives.', needs: null, Body: WhyWrong },
];

export default function Learn() {
  const { slug } = useParams();
  const [results, setResults] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch('/research/results.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))))
      .then(setResults)
      .catch(() => setError(true));
  }, []);

  const available = ARTICLES.filter((a) => !a.needs || (results && results[a.needs]));

  if (!slug) {
    return (
      <>
        <div className="page-header">
          <h1>Learn</h1>
          <p>
            Short research notes. Every chart and number is produced by the scripts in <code>research/</code> using
            the same library that grades the drills.
          </p>
        </div>
        {error && <div className="notice notice-error">Couldn't load the research results.</div>}
        <div className="grid-3">
          {available.map((a) => (
            <Link key={a.slug} to={`/learn/${a.slug}`} className="card card-link">
              <h3>{a.title}</h3>
              <p className="muted small">{a.blurb}</p>
            </Link>
          ))}
        </div>
      </>
    );
  }

  const article = ARTICLES.find((a) => a.slug === slug);
  if (!article) {
    return <p>No such article. <Link to="/learn">Back to Learn</Link></p>;
  }
  const data = article.needs ? results && results[article.needs] : null;
  return (
    <article className="article">
      <p className="small">
        <Link to="/learn">← Learn</Link>
      </p>
      <h1>{article.title}</h1>
      {article.needs && !results && !error && <p className="muted">Loading…</p>}
      {article.needs && results && !data && (
        <p className="muted">This study hasn't been generated yet. See research/ in the repository.</p>
      )}
      {(!article.needs || data) && <article.Body r={data} hasSmile={!!(results && results.smile)} />}
    </article>
  );
}
