import { useState } from 'react';

export default function SummaryCard({ data }) {
  const [copyState, setCopyState] = useState('Copy summary');
  async function copy() {
    try {
      await navigator.clipboard.writeText(data.summary);
      setCopyState('Copied!');
    } catch { setCopyState('Copy failed'); }
  }
  return <article className="summary-card" aria-label="Page summary">
    <div className="summary-topline"><span className="eyebrow">YOUR SUMMARY</span>
      <span className="type-badge">{data.content_type.replaceAll('_', ' ')}</span></div>
    <h2>{data.title || 'The essentials'}</h2>
    <a className="source-link" href={data.url} target="_blank" rel="noopener noreferrer">{data.url} ↗</a>
    {data.content_type === 'blog_index' && <p className="truncation-note">This summary covers the headlines listed on this page. Open an individual post for a summary of its full content.</p>}
    <p className="summary-text">{data.summary}</p>
    {data.truncated && <p className="truncation-note">This page was long, so the summary covers the beginning of its readable content.</p>}
    <div className="summary-footer"><span>{data.characters_processed.toLocaleString()} characters processed</span>
      <button className="secondary-button" onClick={copy}>{copyState}</button></div>
    <span className="sr-only" role="status">{copyState === 'Copied!' ? 'Summary copied to clipboard' : ''}</span>
  </article>;
}
