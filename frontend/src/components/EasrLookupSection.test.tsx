import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import EasrLookupSection from './EasrLookupSection';
import * as api from '@/lib/api';

describe('EasrLookupSection', () => {
  it('looks up a rate and applies it as tier1 official data', async () => {
    vi.spyOn(api, 'lookupEasr').mockResolvedValue({
      search_input: { year: '2025-2026', district: 'Pune', taluka: 'हवेली', village: 'आकुर्डी' },
      found: true,
      columns: ['उपविभाग', 'एकक (Rs./)'],
      rows: [{ 'उपविभाग': '5/52-मुंबई पुणे महामार्ग', 'एकक (Rs./)': '70310' }],
      preamble: {},
      source: 'IGR Maharashtra e ASR (igreval), accessed 2026-07-30',
      accessed_at: '2026-07-30T00:00:00Z',
    });

    const onResult = vi.fn();
    render(<EasrLookupSection onResult={onResult} />);
    await userEvent.click(screen.getByRole('button', { name: 'Manual lookup / override' }));

    await userEvent.type(screen.getByPlaceholderText(/District/), 'Pune');
    await userEvent.type(screen.getByPlaceholderText('Village'), 'आकुर्डी');
    await userEvent.click(screen.getByRole('button', { name: 'Look Up Rate' }));

    expect(await screen.findByText('Found 1 row(s).')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Use This Data' }));

    expect(onResult).toHaveBeenCalledWith(expect.stringContaining('70310'));
    expect(await screen.findByText(/Applied/)).toBeInTheDocument();
  });

  it('shows an error message when the lookup fails', async () => {
    vi.spyOn(api, 'lookupEasr').mockRejectedValue(new Error("'x' is not a valid option"));

    render(<EasrLookupSection onResult={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Manual lookup / override' }));

    await userEvent.type(screen.getByPlaceholderText(/District/), 'Pune');
    await userEvent.type(screen.getByPlaceholderText('Village'), 'x');
    await userEvent.click(screen.getByRole('button', { name: 'Look Up Rate' }));

    expect(await screen.findByText("'x' is not a valid option")).toBeInTheDocument();
  });

  it('clears the applied data and notifies the parent', async () => {
    vi.spyOn(api, 'lookupEasr').mockResolvedValue({
      search_input: { year: '2025-2026', district: 'Pune', village: 'आकुर्डी' },
      found: true,
      columns: ['एकक (Rs./)'],
      rows: [{ 'एकक (Rs./)': '70310' }],
      preamble: {},
      source: 'src',
      accessed_at: '2026-07-30T00:00:00Z',
    });

    const onResult = vi.fn();
    render(<EasrLookupSection onResult={onResult} />);
    await userEvent.click(screen.getByRole('button', { name: 'Manual lookup / override' }));

    await userEvent.type(screen.getByPlaceholderText(/District/), 'Pune');
    await userEvent.type(screen.getByPlaceholderText('Village'), 'आकुर्डी');
    await userEvent.click(screen.getByRole('button', { name: 'Look Up Rate' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Use This Data' }));
    await userEvent.click(screen.getByRole('button', { name: 'Clear' }));

    expect(onResult).toHaveBeenLastCalledWith(null);
  });
});
