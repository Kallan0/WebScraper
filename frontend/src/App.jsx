import { useEffect, useRef, useState } from 'react';
import UrlInput from './components/UrlInput.jsx';
import Loading from './components/Loading.jsx';
import SummaryCard from './components/SummaryCard.jsx';
import { summarizeUrl } from './services/api.js';

export default function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const controller = useRef(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function submit(event) {
    event.preventDefault();
    if (loading) return;
    const value = url.trim();
    let parsed;
    try { parsed = new URL(value); } catch { setError('Enter a valid HTTP or HTTPS URL.'); return; }
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      setError('Enter a valid HTTP or HTTPS URL.'); return;
    }
    setLoading(true); setError(''); setData(null);
    controller.current = new AbortController();
    try { setData(await summarizeUrl(value, controller.current.signal)); }
    catch (err) { if (err.name !== 'AbortError') setError(err.message); }
    finally { setLoading(false); }
  }
  return <div className="app-shell">
    <header className="site-header"><a href="/" className="brand"><span className="brand-mark" aria-hidden="true">≋</span>AI Web Scraper</a>
      <span className="header-note">A little less scrolling.</span></header>
    <main>
      <section className="hero"><span className="eyebrow"><span className="status-dot" /> FROM WEBPAGE TO TAKEAWAY</span>
        <h1>Read less.<br /><span>Understand more.</span></h1>
        <p className="hero-description">Turn a long webpage into a clear, concise summary.<br className="desktop-break" /> Paste a link. Find what matters. Get on with your day.</p>
      </section>
      <section className="workspace" aria-label="Summarize a webpage">
        <UrlInput url={url} setUrl={setUrl} loading={loading} onSubmit={submit} />
        {loading && <Loading />}
        {error && <div className="error-state" role="alert"><strong>We couldn’t summarize that page.</strong><p>{error}</p>
          <button className="secondary-button" onClick={submit}>Try again</button></div>}
        {data && <SummaryCard key={data.url + data.summary} data={data} />}
        {!loading && !error && !data && <div className="empty-state"><span className="paper-icon" aria-hidden="true">≡</span>
          <div><h2>The big picture, without the big read.</h2><p>Your summary will appear here, with a link back to the source.</p></div></div>}
      </section>
      <section className="steps" aria-label="How it works">
        {[['01', 'Drop a link', 'Choose a public webpage you want to understand.'],
          ['02', 'Find the substance', 'We extract the readable content from the page.'],
          ['03', 'Keep the essentials', 'Get the key facts in a few concise sentences.']].map(([number,title,text]) =>
          <div className="step" key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p></div>)}
      </section>
    </main>
    <footer><span>Less noise. More clarity.</span><span>Always check the source for the full context.</span></footer>
  </div>;
}
