// "Make a market" game: the contract settles at the sum of NUM_CARDS cards
// drawn from a standard deck (A = 1 ... K = 13). Each round one more card is
// revealed and the player quotes a bid and an ask; a counterparty trades one
// lot against the quote. Everything is deterministic given the seed, so a
// challenge link replays the same deal and the same counterparties.

export const NUM_CARDS = 3;
export const MAX_WIDTH = [8, 5, 3]; // max ask - bid per round, shrinking as cards are revealed
export const INFORMED_EDGE = 0.5; // informed trader needs at least this much edge to trade
export const NOISE_PROB = 0.35; // chance a noise trader shows up when the informed one passes

const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
const SUITS = ['♠', '♥', '♦', '♣'];
const DECK_TOTAL = 4 * ((13 * 14) / 2); // 364
const DECK_SIZE = 52;

// Small, fast, seedable PRNG (mulberry32).
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function cardLabel(card) {
  return `${RANKS[card.value - 1]}${card.suit}`;
}

export function deal(seed) {
  const rand = rng(seed);
  const deck = [];
  for (const suit of SUITS) for (let v = 1; v <= 13; v++) deck.push({ value: v, suit });
  // Fisher-Yates
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  const cards = deck.slice(0, NUM_CARDS);
  // Per-round noise-trader draws, fixed up front so they don't depend on the player's quotes.
  const noise = MAX_WIDTH.map(() => ({ shows: rand() < NOISE_PROB, buys: rand() < 0.5 }));
  return { seed, cards, noise, settlement: cards.reduce((s, c) => s + c.value, 0) };
}

// E[sum of all cards | the cards in `known` are among them], drawing the rest
// without replacement from the remaining deck.
export function fairValue(known) {
  const knownSum = known.reduce((s, c) => s + c.value, 0);
  const remaining = NUM_CARDS - known.length;
  if (remaining === 0) return knownSum;
  const mean = (DECK_TOTAL - knownSum) / (DECK_SIZE - known.length);
  return knownSum + remaining * mean;
}

// The informed trader has seen the last card (the one revealed last), on top of what is public.
export function informedFair(game, round) {
  const known = game.cards.slice(0, round);
  if (round < NUM_CARDS) known.push(game.cards[NUM_CARDS - 1]); // the last card is public only at settlement
  return fairValue(known);
}

export function validateQuote(bid, ask, round) {
  if (!Number.isFinite(bid) || !Number.isFinite(ask)) return 'Enter a bid and an ask.';
  if (bid < 0) return 'The bid must be at least 0.';
  if (ask <= bid) return 'The ask must be above the bid.';
  if (ask - bid > MAX_WIDTH[round] + 1e-9) return `Your spread can be at most ${MAX_WIDTH[round]} this round.`;
  return null;
}

// Who trades against a quote in a round. Returns { side, price, informed } where
// side is +1 if the player buys (counterparty hits the bid), -1 if the player
// sells (counterparty lifts the ask), or null if nobody trades.
export function counterparty(game, round, bid, ask) {
  const theirFair = informedFair(game, round);
  const buyEdge = theirFair - ask; // they buy from you at your ask
  const sellEdge = bid - theirFair; // they sell to you at your bid
  if (Math.max(buyEdge, sellEdge) >= INFORMED_EDGE) {
    return buyEdge >= sellEdge
      ? { side: -1, price: ask, informed: true }
      : { side: +1, price: bid, informed: true };
  }
  const noise = game.noise[round];
  if (noise.shows) {
    return noise.buys ? { side: -1, price: ask, informed: false } : { side: +1, price: bid, informed: false };
  }
  return { side: null, price: null, informed: false };
}

export function pnl(trades, settlement) {
  return trades.reduce((s, t) => (t.side ? s + t.side * (settlement - t.price) : s), 0);
}

// A textbook market maker: quotes the public fair value with the widest allowed spread.
export function baselineTrades(game) {
  return MAX_WIDTH.map((width, round) => {
    const fair = fairValue(game.cards.slice(0, round));
    const bid = Math.round((fair - width / 2) * 2) / 2;
    const ask = bid + width;
    return { round, bid, ask, ...counterparty(game, round, bid, ask) };
  });
}
