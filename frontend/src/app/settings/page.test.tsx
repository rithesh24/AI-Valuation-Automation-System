import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import Settings from './page';
import * as api from '@/lib/api';

describe('Settings', () => {
  it('shows the configured status once loaded', async () => {
    vi.spyOn(api, 'getApiKeyStatus').mockResolvedValue({ configured: true });

    render(<Settings />);

    expect(await screen.findByText('Key configured')).toBeInTheDocument();
  });

  it('shows a not-configured message when no key is set', async () => {
    vi.spyOn(api, 'getApiKeyStatus').mockResolvedValue({ configured: false });

    render(<Settings />);

    expect(await screen.findByText('No key configured yet')).toBeInTheDocument();
  });

  it('saves a new key and shows confirmation', async () => {
    vi.spyOn(api, 'getApiKeyStatus').mockResolvedValue({ configured: false });
    vi.spyOn(api, 'setApiKey').mockResolvedValue({ configured: true });
    const user = userEvent.setup();

    render(<Settings />);
    await screen.findByText('No key configured yet');

    await user.type(screen.getByPlaceholderText('sk-ant-...'), 'sk-ant-test123');
    await user.click(screen.getByRole('button', { name: 'Save Key' }));

    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(api.setApiKey).toHaveBeenCalledWith('sk-ant-test123');
  });

  it('shows an error message when saving fails', async () => {
    vi.spyOn(api, 'getApiKeyStatus').mockResolvedValue({ configured: false });
    vi.spyOn(api, 'setApiKey').mockRejectedValue(new Error('API key cannot be empty.'));
    const user = userEvent.setup();

    render(<Settings />);
    await screen.findByText('No key configured yet');

    await user.type(screen.getByPlaceholderText('sk-ant-...'), 'x');
    await user.click(screen.getByRole('button', { name: 'Save Key' }));

    expect(await screen.findByText('API key cannot be empty.')).toBeInTheDocument();
  });
});
