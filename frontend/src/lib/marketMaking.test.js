import {
  MAX_WIDTH,
  baselineTrades,
  counterparty,
  deal,
  fairValue,
  informedFair,
  pnl,
  rng,
  validateQuote,
} from './marketMaking';

const card = (value) => ({ value, suit: '♠' });

test('fair value of three cards with nothing revealed is 21', () => {
  expect(fairValue([])).toBeCloseTo(21, 12);
});

test('fair value conditions on revealed cards without replacement', () => {
  // A king is gone: the remaining 51 cards average (364 - 13) / 51.
  expect(fairValue([card(13)])).toBeCloseTo(13 + 2 * (351 / 51), 12);
  expect(fairValue([card(1), card(1)])).toBeCloseTo(2 + 362 / 50, 12);
  expect(fairValue([card(4), card(5), card(6)])).toBe(15);
});

test('fair value matches brute force over the remaining deck', () => {
  const known = [card(12), card(3)];
  const deck = [];
  for (let v = 1; v <= 13; v++) for (let s = 0; s < 4; s++) deck.push(v);
  [12, 3].forEach((v) => deck.splice(deck.indexOf(v), 1));
  const mean = deck.reduce((a, b) => a + b, 0) / deck.length;
  expect(fairValue(known)).toBeCloseTo(15 + mean, 12);
});

test('deals are deterministic, valid and distinct cards', () => {
  const a = deal(42);
  const b = deal(42);
  expect(a).toEqual(b);
  expect(a.cards).toHaveLength(3);
  const keys = a.cards.map((c) => `${c.value}${c.suit}`);
  expect(new Set(keys).size).toBe(3);
  expect(a.settlement).toBe(a.cards.reduce((s, c) => s + c.value, 0));
  expect(deal(43)).not.toEqual(a);
});

test('rng is uniform enough over many draws', () => {
  const r = rng(7);
  let sum = 0;
  for (let i = 0; i < 20000; i++) sum += r();
  expect(sum / 20000).toBeCloseTo(0.5, 1);
});

test('informed trader knows the last card until it is public', () => {
  const g = deal(5);
  expect(informedFair(g, 0)).toBeCloseTo(fairValue([g.cards[2]]), 12);
  expect(informedFair(g, 2)).toBe(g.settlement); // two revealed + their card = everything
});

test('quote validation enforces the shrinking max width', () => {
  expect(validateQuote(17, 25, 0)).toBeNull();
  expect(validateQuote(17, 26, 0)).toMatch(/at most 8/);
  expect(validateQuote(20, 23, 2)).toBeNull();
  expect(validateQuote(20, 24, 2)).toMatch(/at most 3/);
  expect(validateQuote(25, 25, 0)).toMatch(/above the bid/);
  expect(validateQuote(NaN, 5, 0)).toMatch(/Enter/);
});

test('informed trader picks off a stale quote', () => {
  // Find a deal whose hidden last card is a king: their fair value is far above 21.
  let seed = 1;
  while (deal(seed).cards[2].value !== 13) seed++;
  const g = deal(seed);
  const t = counterparty(g, 0, 17, 25);
  expect(t).toMatchObject({ side: -1, price: 25, informed: true });
  // A quote centered on their value is not attractive to them.
  const theirs = informedFair(g, 0);
  const safe = counterparty(g, 0, theirs - 1, theirs + 1);
  expect(safe.informed).toBe(false);
});

test('pnl settles each trade against the final sum', () => {
  const trades = [
    { side: +1, price: 20 }, // bought at 20
    { side: -1, price: 24 }, // sold at 24
    { side: null, price: null },
  ];
  expect(pnl(trades, 22)).toBe(2 + 2);
  expect(pnl(trades, 30)).toBe(10 - 6);
});

test('baseline market maker quotes at max width around public fair value', () => {
  const g = deal(99);
  const base = baselineTrades(g);
  expect(base).toHaveLength(MAX_WIDTH.length);
  base.forEach((b, round) => {
    expect(b.ask - b.bid).toBeCloseTo(MAX_WIDTH[round], 9);
    const mid = (b.bid + b.ask) / 2;
    expect(Math.abs(mid - fairValue(g.cards.slice(0, round)))).toBeLessThanOrEqual(0.25 + 1e-9);
  });
});
