import { getFlags, getHealth } from "../../lib/api";

export default async function IngestionHealthPage() {
  const [health, flags] = await Promise.all([
    getHealth().catch(() => null),
    getFlags().catch(() => ({ flags: [] }))
  ]);
  const limiter = health?.rate_limiter;
  return (
    <div className="grid">
      <div>
        <h1>Ingestion Health</h1>
        <p className="muted">API, database, Redis, scheduler, limiter, and stale-data visibility.</p>
      </div>
      <section className="metric-grid">
        <div className="metric"><div className="muted">Scheduler</div><strong>{health?.scheduler?.enabled ? "running" : "disabled"}</strong></div>
        <div className="metric"><div className="muted">429 Count</div><strong>{limiter?.count_429 ?? 0}</strong></div>
        <div className="metric"><div className="muted">Limiter Budget</div><strong>{limiter?.current_budget ?? "--"}</strong></div>
        <div className="metric"><div className="muted">Queue Depth</div><strong>{limiter?.queue_depth ?? "--"}</strong></div>
      </section>
      <section className="panel" style={{ padding: 16 }}>
        <h2>Latest Jobs</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Job</th><th>Status</th><th>Started</th><th>Finished</th><th>Rows</th><th>Error</th></tr></thead>
            <tbody>
              {health?.latest_runs?.map((run: any) => (
                <tr key={run.job_name}>
                  <td>{run.job_name}</td>
                  <td>{run.status}</td>
                  <td>{run.started_at}</td>
                  <td>{run.finished_at ?? "--"}</td>
                  <td>{run.rows_written}</td>
                  <td>{run.error_message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel" style={{ padding: 16 }}>
        <h2>Recent Flags</h2>
        {flags.flags.map((flag) => <span className="tag" key={flag.id}>{flag.coin}: {flag.message}</span>)}
      </section>
    </div>
  );
}
