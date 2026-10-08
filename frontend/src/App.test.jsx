import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import App from './App.jsx';
import { summarizeUrl } from './services/api.js';
vi.mock('./services/api.js', () => ({ summarizeUrl: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
const data = { url: 'https://example.com/article', title: 'A useful article', content_type: 'article',
  characters_processed: 1200, summary: 'A concise summary of the key facts.', truncated: false };
function submit() {
  fireEvent.change(screen.getByLabelText('Webpage URL'), { target: { value: data.url } });
  fireEvent.submit(screen.getByRole('button', { name: /Summarize/ }).closest('form'));
}
describe('summary workflow', () => {
  it('shows loading then the result', async () => {
    let complete;
    summarizeUrl.mockReturnValue(new Promise(resolve => { complete = resolve; }));
    render(<App />); submit();
    expect(screen.getByText('Finding the essentials…')).toBeInTheDocument();
    expect(screen.getByLabelText('Webpage URL')).toBeDisabled();
    complete(data);
    expect(await screen.findByText(data.summary)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /example.com/ })).toHaveAttribute('href', data.url);
  });
  it('shows server errors and allows retry', async () => {
    summarizeUrl.mockRejectedValueOnce(new Error('This page is private.')).mockResolvedValueOnce(data);
    render(<App />); submit();
    expect(await screen.findByRole('alert')).toHaveTextContent('This page is private.');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText(data.summary)).toBeInTheDocument();
    expect(summarizeUrl).toHaveBeenCalledTimes(2);
  });
  it('rejects unsupported protocols before requesting', () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText('Webpage URL'), { target: { value: 'file:///example' } });
    fireEvent.submit(screen.getByRole('button', { name: /Summarize/ }).closest('form'));
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a valid HTTP or HTTPS URL.');
    expect(summarizeUrl).not.toHaveBeenCalled();
  });
  it('copies summary text', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
    summarizeUrl.mockResolvedValue(data);
    render(<App />); submit();
    fireEvent.click(await screen.findByRole('button', { name: 'Copy summary' }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(data.summary));
    expect(await screen.findByRole('button', { name: 'Copied!' })).toBeInTheDocument();
  });
});
