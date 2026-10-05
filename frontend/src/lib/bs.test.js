import { greeks, hedgeMtm, normCdf, price } from './bs';

// Golden values from the Python library (quant/black_scholes.py, quant/hedging.py).
const CASES = [
  [{ S: 100, K: 100, T: 0.25, r: 0.05, sigma: 0.2, q: 0, kind: 'call' }, 4.6149971296,
    { delta: 0.5694601832, gamma: 0.0392880009, theta: -10.4741512485, vega: 19.6440004724, rho: 13.0827552978 }],
  [{ S: 100, K: 120, T: 1.0, r: 0.03, sigma: 0.35, q: 0.02, kind: 'put' }, 25.8607648528,
    { delta: -0.612143831, gamma: 0.0106239834, theta: -5.119223043, vega: 37.1839418264, rho: -87.0751479555 }],
  [{ S: 50, K: 40, T: 0.1, r: 0, sigma: 0.5, q: 0, kind: 'call' }, 10.2523464362,
    { delta: 0.9319326588, gamma: 0.016621147, theta: -5.1941084458, vega: 2.0776433783, rho: 3.6344286505 }],
  [{ S: 80, K: 100, T: 2, r: 0.08, sigma: 0.15, q: 0.04, kind: 'put' }, 13.8659460568,
    { delta: -0.6602373905, gamma: 0.0184601761, theta: 1.892902657, vega: 35.4435380602, rho: -133.3698746006 }],
];

test.each(CASES)('matches the Python library %#', (args, expectedPrice, expectedGreeks) => {
  expect(price(args)).toBeCloseTo(expectedPrice, 8);
  const g = greeks(args);
  for (const [k, v] of Object.entries(expectedGreeks)) {
    expect(g[k]).toBeCloseTo(v, 7);
  }
});

test('normal CDF is accurate in the body and tails', () => {
  expect(normCdf(0)).toBeCloseTo(0.5, 15);
  expect(normCdf(1.959963984540054)).toBeCloseTo(0.975, 12);
  // Far tail: relative accuracy is what matters.
  expect(Math.abs(normCdf(-8) / 6.22096057427178e-16 - 1)).toBeLessThan(1e-7);
});

test('expiry limit is intrinsic value', () => {
  expect(price({ S: 110, K: 100, T: 0, sigma: 0.2 })).toBe(10);
  expect(greeks({ S: 110, K: 100, T: 0, sigma: 0.2 }).delta).toBe(1);
});

test('hedge mark-to-market matches the Python accounting', () => {
  const out = hedgeMtm({
    spots: [100, 102, 99, 101, 105],
    hedges: [0.5, 0.6, 0.4, 0.55],
    optionValues: [4, 5, 3.2, 3.9, 5.0],
    premium: 4,
    T: 0.25,
    r: 0.05,
    q: 0.01,
    cost: 0.001,
  });
  const expected = [0.0, -0.16287157026130927, -0.31125100939369066, -0.32125734561629704, 0.5778606287958521];
  expected.forEach((v, i) => expect(out[i]).toBeCloseTo(v, 10));
});

test('hedge mark-to-market can be evaluated mid-game', () => {
  const out = hedgeMtm({
    spots: [100, 102, 99, 101, 105],
    hedges: [0.5],
    optionValues: [4, 5, 3.2, 3.9, 5.0],
    premium: 4,
    T: 0.25,
  });
  expect(out[0]).toBeCloseTo(0, 12);
  expect(out[1]).not.toBeNull();
  expect(out[2]).toBeNull();
});
