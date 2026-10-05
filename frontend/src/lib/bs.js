// Black-Scholes-Merton in the browser, mirroring quant/black_scholes.py so the
// Greeks Lab and hedging game can recompute instantly without a server round
// trip. bs.test.js checks it against values produced by the Python library.
// Units match the Python library: theta per year, vega and rho per 1.00.

// Cumulative normal, Hart (1968) as given by West (2005); double precision.
export function normCdf(x) {
  const z = Math.abs(x);
  let c = 0;
  if (z <= 37) {
    const e = Math.exp((-z * z) / 2);
    if (z < 7.07106781186547) {
      let n = 3.52624965998911e-2 * z + 0.700383064443688;
      n = n * z + 6.37396220353165;
      n = n * z + 33.912866078383;
      n = n * z + 112.079291497871;
      n = n * z + 221.213596169931;
      n = n * z + 220.206867912376;
      let d = 8.83883476483184e-2 * z + 1.75566716318264;
      d = d * z + 16.064177579207;
      d = d * z + 86.7807322029461;
      d = d * z + 296.564248779674;
      d = d * z + 637.333633378831;
      d = d * z + 793.826512519948;
      d = d * z + 440.413735824752;
      c = (e * n) / d;
    } else {
      let b = z + 0.65;
      b = z + 4 / b;
      b = z + 3 / b;
      b = z + 2 / b;
      b = z + 1 / b;
      c = e / b / 2.506628274631;
    }
  }
  return x > 0 ? 1 - c : c;
}

export function normPdf(x) {
  return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}

const MIN_TOTAL_VOL = 1e-12;

export function price({ S, K, T, r = 0, sigma, q = 0, kind = 'call' }) {
  const totalVol = sigma * Math.sqrt(Math.max(T, 0));
  const discS = S * Math.exp(-q * T);
  const discK = K * Math.exp(-r * T);
  const call = kind === 'call';
  if (totalVol <= MIN_TOTAL_VOL) {
    return Math.max(call ? discS - discK : discK - discS, 0);
  }
  const d1 = (Math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / totalVol;
  const d2 = d1 - totalVol;
  return call
    ? discS * normCdf(d1) - discK * normCdf(d2)
    : discK * normCdf(-d2) - discS * normCdf(-d1);
}

export function greeks({ S, K, T, r = 0, sigma, q = 0, kind = 'call' }) {
  const totalVol = sigma * Math.sqrt(Math.max(T, 0));
  const dfq = Math.exp(-q * T);
  const dfr = Math.exp(-r * T);
  const call = kind === 'call';
  if (totalVol <= MIN_TOTAL_VOL) {
    const itm = S * dfq > K * dfr ? 1 : 0;
    const n1 = call ? itm : 1 - itm;
    return {
      delta: call ? dfq * n1 : -dfq * n1,
      gamma: 0,
      vega: 0,
      theta: call ? -r * K * dfr * n1 + q * S * dfq * n1 : r * K * dfr * n1 - q * S * dfq * n1,
      rho: call ? K * T * dfr * n1 : -K * T * dfr * n1,
    };
  }
  const sqrtT = Math.sqrt(T);
  const d1 = (Math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / totalVol;
  const d2 = d1 - totalVol;
  const pdf = normPdf(d1);
  const gamma = (dfq * pdf) / (S * totalVol);
  const vega = S * dfq * pdf * sqrtT;
  const decay = (-S * dfq * pdf * sigma) / (2 * sqrtT);
  if (call) {
    return {
      delta: dfq * normCdf(d1),
      gamma,
      vega,
      theta: decay - r * K * dfr * normCdf(d2) + q * S * dfq * normCdf(d1),
      rho: K * T * dfr * normCdf(d2),
    };
  }
  return {
    delta: -dfq * normCdf(-d1),
    gamma,
    vega,
    theta: decay + r * K * dfr * normCdf(-d2) - q * S * dfq * normCdf(-d1),
    rho: -K * T * dfr * normCdf(-d2),
  };
}

// Mark-to-market P&L of a short option hedged with `hedges[i]` shares held
// from step i to i + 1 (same accounting as quant.hedging.hedge_mtm).
// Returns an array of length hedges.length + 1; entries past the last hedge
// supplied are null, so it can be called mid-game.
export function hedgeMtm({ spots, hedges, optionValues, premium, T, r = 0, q = 0, cost = 0, nSteps }) {
  const steps = nSteps ?? spots.length - 1;
  const dt = T / steps;
  const growth = Math.exp(r * dt);
  const div = Math.exp(q * dt) - 1;
  const out = new Array(steps + 1).fill(null);
  let held = 0;
  let cash = premium;
  for (let i = 0; i < steps; i++) {
    out[i] = cash + held * spots[i] - optionValues[i];
    if (i >= hedges.length) return out;
    const trade = hedges[i] - held;
    cash = cash - trade * spots[i] - cost * Math.abs(trade) * spots[i];
    held = hedges[i];
    cash = cash * growth + held * spots[i] * div;
  }
  const sT = spots[steps];
  out[steps] = cash + held * sT - cost * Math.abs(held) * sT - optionValues[steps];
  return out;
}
