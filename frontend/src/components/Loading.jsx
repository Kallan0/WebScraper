export default function Loading() {
  return <div className="loading-state" role="status" aria-live="polite">
    <span className="spinner" aria-hidden="true" />
    <div><strong>Finding the essentials…</strong><p>Loading the page and generating your summary.</p></div>
  </div>;
}
