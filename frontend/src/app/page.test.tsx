import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import Home from './page';

describe('Home', () => {
  it('renders all three upload sections and the dashboard link', () => {
    render(<Home />);

    expect(screen.getByText('Property Documents')).toBeInTheDocument();
    expect(screen.getByText('Bank Valuation Template')).toBeInTheDocument();
    expect(screen.getByText('Supporting Images')).toBeInTheDocument();
    expect(screen.getByText('Official Guideline Rate (eASR, optional)')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /usage dashboard/i })).toHaveAttribute(
      'href',
      '/dashboard'
    );
  });
});
