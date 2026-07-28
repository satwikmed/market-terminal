import { describe, expect, it } from 'vitest';

import { formatMoney, formatPct } from './api';

describe('financial formatters', () => {
  it('formats market caps at human scale', () => {
    expect(formatMoney(4_890_000_000_000)).toBe('$4.89T');
    expect(formatMoney(90_000_000_000)).toBe('$90.0B');
  });

  it('makes price direction explicit', () => {
    expect(formatPct(3.531)).toBe('+3.53%');
    expect(formatPct(-0.919)).toBe('-0.92%');
  });

  it('does not invent missing values', () => {
    expect(formatMoney(null)).toBe('n/a');
    expect(formatPct(undefined)).toBe('n/a');
  });
});
