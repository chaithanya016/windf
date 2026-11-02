import { useEffect, useState } from "react";
import {
  Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "./api.js";

const fmt = (n, d = 0) => (n == null ? "–" : Number(n).toLocaleString("en-GB", { maximumFractionDigits: d }));
const hhmm = (iso) => new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" });
const stamp = (iso) => new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/London" });

const Card = ({ k, v, s }) => (
  <div className="card"><div className="k">{k}</div><div className="v">{v}</div>{s && <div className="s">{s}</div>}</div>
);
const Panel = ({ title, sub, children }) => (
  <section className="panel"><h3>{title}</h3>{sub && <p>{sub}</p>}{children}</section>
);
const Chart = ({ h = 280, children }) => <div style={{ height: h }}><ResponsiveContainer>{children}</ResponsiveContainer></div>;

function Decision({ cutoff }) {
  const [date, setDate] = useState("2026-01-15");
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    setErr("");
    api("day", { date, cutoff }).then(setD).catch((e) => { setD(null); setErr(e.message); });
  }, [date, cutoff]);
  const rows = (d?.rows || []).map((r) => ({ ...r, t: hhmm(r.startTime), range: r.upper != null ? [r.lower, r.upper] : null,
    base: r.lower, width: r.upper != null ? r.upper - r.lower : null }));
  const s = d?.summary;
  return (<>
    <div className="controls">
      <label>Delivery day (Jan 2026)<input type="date" min="2026-01-01" max="2026-01-31" value={date} onChange={(e) => setDate(e.target.value)} /></label>
    </div>
    {err && <p className="err">{err}</p>}
    {s && <>
      <div className="cards">
        <Card k="Forecast wind energy" v={`${fmt(s.forecast_mwh)} MWh`} s="Σ forecast × 0.5h" />
        <Card k="Peak / minimum" v={`${fmt(s.peak_forecast_mw)} / ${fmt(s.min_forecast_mw)} MW`} />
        <Card k="Forecast used (published)" v={stamp(s.latest_publish_used)} s={`Latest before ${cutoff} UK on D-1`} />
        <Card k="Uncertainty (90% band)" v={d.band ? `${fmt(-d.band.q95)} … +${fmt(-d.band.q05)} MW` : "n/a"} s={d.band ? `Learned from ${d.band.history_days} earlier days` : "No earlier days to learn from"} />
      </div>
      <Panel title="Wind forecast available at decision time vs. what happened"
        sub="Shaded band = range the actual output fell in 90% of earlier half-hours. Plan thermal purchases against the band, not just the line.">
        <Chart h={340}>
          <ComposedChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
            <XAxis dataKey="t" interval={5} fontSize={12} /><YAxis fontSize={12} unit=" MW" width={80} />
            <Tooltip formatter={(v) => (Array.isArray(v) ? v.join(" – ") : fmt(v) + " MW")} />
            <Legend />
            <Area dataKey="base" stackId="b" stroke="none" fill="transparent" legendType="none" isAnimationActive={false} />
            <Area dataKey="width" stackId="b" name="90% band" stroke="none" fill="var(--band)" fillOpacity={0.6} isAnimationActive={false} />
            <Line dataKey="forecast" name="Forecast (D-1)" stroke="var(--accent)" dot={false} strokeWidth={2} />
            <Line dataKey="actual" name="Actual" stroke="var(--bad)" dot={false} strokeWidth={2} />
          </ComposedChart>
        </Chart>
      </Panel>
      <Panel title="Half-hourly detail">
        <div className="scroll"><table><thead><tr><th>Time (UK)</th><th>Forecast MW</th><th>Low</th><th>High</th><th>Actual MW</th><th>Error MW</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.startTime}><td>{r.t}</td><td>{fmt(r.forecast)}</td><td>{fmt(r.lower)}</td><td>{fmt(r.upper)}</td><td>{fmt(r.actual)}</td><td>{fmt(r.error)}</td></tr>)}</tbody></table></div>
      </Panel>
    </>}
  </>);
}

function Accuracy({ cutoff }) {
  const [a, setA] = useState(null);
  useEffect(() => { api("accuracy", { cutoff }).then(setA).catch(() => setA(null)); }, [cutoff]);
  if (!a) return <p>Loading…</p>;
  const s = a.summary;
  return (<>
    <div className="cards">
      <Card k="MAE" v={`${fmt(s.mae)} MW`} s="Typical miss" />
      <Card k="RMSE" v={`${fmt(s.rmse)} MW`} s="Penalises big misses" />
      <Card k="Bias" v={`${fmt(s.bias)} MW`} s="+ = over-forecast" />
      <Card k="wMAPE" v={`${fmt(s.wmape, 1)}%`} s="Σ|err| / Σ actual" />
      <Card k="95th pct abs error" v={`${fmt(s.p95_abs)} MW`} s={`${fmt(s.n)} half-hours`} />
    </div>
    <Panel title="Error distribution" sub="Forecast − actual, MW. Left = under-forecast (risk of buying too much), right = over-forecast (risk of shortfall).">
      <Chart><BarChart data={a.histogram.map((h) => ({ ...h, label: fmt(h.from) }))}><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
        <XAxis dataKey="label" fontSize={11} /><YAxis fontSize={12} /><Tooltip /><Bar dataKey="count" fill="var(--accent)" /></BarChart></Chart>
    </Panel>
    <Panel title="Error by delivery day" sub="Mean absolute error and bias per day.">
      <Chart><LineChart data={a.by_day}><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" /><XAxis dataKey="date" tickFormatter={(d) => d.slice(8)} fontSize={12} />
        <YAxis fontSize={12} /><Tooltip /><Legend /><Line dataKey="mae" name="MAE" stroke="var(--accent)" dot={false} strokeWidth={2} /><Line dataKey="bias" name="Bias" stroke="var(--bad)" dot={false} strokeWidth={2} /></LineChart></Chart>
    </Panel>
    <Panel title="Error by hour of day (UK)">
      <Chart><BarChart data={a.by_hour}><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" /><XAxis dataKey="hour" fontSize={12} /><YAxis fontSize={12} /><Tooltip /><Legend />
        <Bar dataKey="mae" name="MAE" fill="var(--accent)" /><Bar dataKey="bias" name="Bias" fill="var(--bad)" /></BarChart></Chart>
    </Panel>
  </>);
}

function Lead() {
  const [b, setB] = useState(null);
  useEffect(() => { api("lead-time").then((r) => setB(r.buckets)).catch(() => setB([])); }, []);
  if (!b) return <p>Loading…</p>;
  return (
    <Panel title="Forecast error vs. lead time" sub="Every published forecast run, grouped by how many hours before delivery it was issued. Shows what is gained by waiting for newer runs.">
      <Chart h={340}><BarChart data={b.map((x) => ({ ...x, label: `${x.lead_from}–${x.lead_to}h` }))}><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
        <XAxis dataKey="label" fontSize={12} /><YAxis fontSize={12} unit=" MW" width={80} /><Tooltip /><Legend />
        <Bar dataKey="mae" name="MAE" fill="var(--accent)" /><Bar dataKey="bias" name="Bias" fill="var(--bad)" /></BarChart></Chart>
    </Panel>
  );
}

export default function App() {
  const [tab, setTab] = useState("day");
  const [cfg, setCfg] = useState(null);
  const [cutoff, setCutoff] = useState("09:00");
  useEffect(() => { api("config").then((c) => { setCfg(c); setCutoff(c.default_cutoff); }).catch(() => {}); }, []);
  return (<>
    {cfg?.sample_data && <div className="banner">Showing SYNTHETIC sample data. Run scripts/fetch_data.py for real Elexon data.</div>}
    <header><h1>UK Day-Ahead Wind Forecast Desk</h1>
      <p>National wind (Elexon FUELHH actuals, WINDFOR forecasts) · delivery days in January 2026</p></header>
    <nav>{[["day", "Decision view"], ["acc", "Forecast accuracy"], ["lead", "Lead time"]].map(([k, l]) =>
      <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}
      <span style={{ flex: 1 }} />
      <label style={{ flexDirection: "row", alignItems: "center" }}>D-1 gate time (UK)&nbsp;
        <input type="time" value={cutoff} onChange={(e) => e.target.value && setCutoff(e.target.value)} /></label>
    </nav>
    <main>{tab === "day" && <Decision cutoff={cutoff} />}{tab === "acc" && <Accuracy cutoff={cutoff} />}{tab === "lead" && <Lead />}</main>
  </>);
}
