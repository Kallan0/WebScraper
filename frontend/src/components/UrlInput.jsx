export default function UrlInput({ url, setUrl, loading, onSubmit }) {
  return (
    <form onSubmit={onSubmit} className="url-form">
      <label htmlFor="page-url">Webpage URL</label>
      <div className="input-row">
        <span className="link-icon" aria-hidden="true">↗</span>
        <input id="page-url" name="url" type="url" placeholder="https://example.com/article"
          required maxLength={2048} value={url} onChange={event => setUrl(event.target.value)}
          disabled={loading} autoComplete="url" aria-describedby="url-hint" />
        <button className="primary-button" disabled={loading || !url.trim()} type="submit">
          {loading ? 'Working…' : 'Summarize'} <span aria-hidden="true">→</span>
        </button>
      </div>
      <p id="url-hint">Works with public articles, news, blogs, and documentation.</p>
    </form>
  );
}
