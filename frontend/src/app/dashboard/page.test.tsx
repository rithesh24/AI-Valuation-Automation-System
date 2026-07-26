import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Dashboard from './page';
import * as api from '@/lib/api';

describe('Dashboard', () => {
  it('renders monthly usage stats once loaded', async () => {
    vi.spyOn(api, 'getMonthlyUsage').mockResolvedValue({
      year: 2026,
      month: 7,
      request_count: 3,
      input_tokens: 1500,
      output_tokens: 750,
      total_tokens: 2250,
      cost_usd: 0.02,
    });

    render(<Dashboard />);

    expect(await screen.findByText('3')).toBeInTheDocument();
    expect(screen.getByText('1,500')).toBeInTheDocument();
    expect(screen.getByText('750')).toBeInTheDocument();
    expect(screen.getByText('2,250')).toBeInTheDocument();
    expect(screen.getByText('$0.02')).toBeInTheDocument();
  });

  it('shows an error message when the usage request fails', async () => {
    vi.spyOn(api, 'getMonthlyUsage').mockRejectedValue(new Error('Failed to load usage'));

    render(<Dashboard />);

    expect(await screen.findByText('Failed to load usage')).toBeInTheDocument();
  });
});
