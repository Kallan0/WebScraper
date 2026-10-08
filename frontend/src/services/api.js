export async function summarizeUrl(url, signal) {
  let response;
  try {
    response = await fetch('/api/summarize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
      signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Cannot reach the server. Check that the backend is running and try again.');
  }
  let result;
  try { result = await response.json(); }
  catch { throw new Error('The server returned an unreadable response. Please try again.'); }
  if (!response.ok || !result.success) {
    throw new Error(result.error || 'Unable to summarize this page. Please try again.');
  }
  return result.data;
}
