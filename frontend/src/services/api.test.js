import { afterEach, expect, it, vi } from 'vitest';

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules(); });

const data = { summary: 'A useful summary.' };

it('uses the configured deployed backend origin without duplicate slashes', async () => {
  vi.stubEnv('VITE_API_BASE_URL', 'https://backend.example.com/');
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ success: true, data }) });
  vi.stubGlobal('fetch', fetch);
  const { summarizeUrl } = await import('./api.js');
  expect(await summarizeUrl('https://example.com/article')).toEqual(data);
  expect(fetch).toHaveBeenCalledWith('https://backend.example.com/api/summarize', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ url: 'https://example.com/article' }),
  }));
});

it('uses the development proxy when no backend origin is configured', async () => {
  vi.stubEnv('VITE_API_BASE_URL', '');
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ success: true, data }) });
  vi.stubGlobal('fetch', fetch);
  const { summarizeUrl } = await import('./api.js');
  await summarizeUrl('https://example.com');
  expect(fetch).toHaveBeenCalledWith('/api/summarize', expect.any(Object));
});
