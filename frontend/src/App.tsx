import { FormEvent, useState } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot, CheckCircle2, ClipboardCheck, LayoutDashboard, Library, Settings,
  Sun, Moon, Workflow, LogOut, Plus,
} from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "./api";

type RequestRow = {
  id: string; sender: string; subject: string; message: string;
  category: string; department: string; priority: string; status: string;
};

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const result = await api<{ access_token: string }>(registering ? "/api/auth/register" : "/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("intelliflow_token", result.access_token);
      navigate("/");
    } catch (exc) {
      setError((exc as Error).message);
    }
  }
  return (
    <main className="auth">
      <form className="auth-card" onSubmit={submit}>
        <div className="brand"><Bot /> IntelliFlow AI</div>
        <h1>{registering ? "Create your account" : "Welcome back"}</h1>
        <p>{registering ? "First account becomes Admin; later accounts are Employees." : "Sign in to manage automated business requests."}</p>
        {error && <div className="error">{error}</div>}
        <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label>
        <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} minLength={8} required /></label>
        <button className="primary" type="submit">{registering ? "Create account" : "Sign in"}</button>
        <button className="auth-toggle" type="button" onClick={() => { setRegistering(!registering); setError(""); }}>
          {registering ? "Already have an account? Sign in" : "New here? Create an account"}
        </button>
      </form>
    </main>
  );
}

function Shell() {
  const [dark, setDark] = useState(false);
  const navigate = useNavigate();
  const links = [
    ["/", "Dashboard", LayoutDashboard], ["/requests", "Requests", ClipboardCheck],
    ["/approvals", "Approvals", CheckCircle2], ["/agents", "AI Agents", Bot],
    ["/workflows", "Workflows", Workflow], ["/knowledge", "Knowledge Base", Library],
    ["/settings", "Settings", Settings],
  ] as const;
  return (
    <div className={dark ? "app dark" : "app"}>
      <aside>
        <div className="brand"><Bot /> <span>IntelliFlow</span></div>
        <nav>{links.map(([to, label, Icon]) =>
          <NavLink key={to} to={to} end={to === "/"}><Icon size={18} /> {label}</NavLink>
        )}</nav>
        <button className="theme" onClick={() => setDark(!dark)}>{dark ? <Sun /> : <Moon />} Theme</button>
      </aside>
      <main>
        <header>
          <div />
          <button className="icon-button" title="Sign out" onClick={() => { localStorage.removeItem("intelliflow_token"); navigate("/login"); }}><LogOut /></button>
        </header>
        <Routes>
          <Route index element={<Dashboard />} />
          <Route path="requests" element={<Requests />} />
          <Route path="approvals" element={<Approvals />} />
          <Route path="agents" element={<Agents />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="knowledge" element={<Knowledge />} />
          <Route path="settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}

function PageTitle({ title, action }: { title: string; action?: React.ReactNode }) {
  return <div className="page-title"><h1>{title}</h1>{action}</div>;
}

function Dashboard() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => api<any>("/api/dashboard/stats") });
  const analytics = useQuery({ queryKey: ["analytics"], queryFn: () => api<any>("/api/dashboard/analytics") });
  if (stats.isLoading) return <div className="loading">Loading dashboard...</div>;
  if (stats.isError) return <div className="error">{(stats.error as Error).message}</div>;
  const cards = [
    ["Total requests", stats.data.total_requests],
    ["Pending", stats.data.pending_requests],
    ["Completed", stats.data.completed_requests],
    ["High priority", stats.data.high_priority_requests],
  ];
  return (
    <>
      <PageTitle title="Dashboard" />
      <section className="stat-grid">{cards.map(([label, value]) =>
        <div className="card stat" key={String(label)}><span>{label}</span><strong>{value}</strong></div>
      )}</section>
      <section className="chart-grid">
        <div className="card"><h3>Requests by department</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={analytics.data?.requests_by_department || []}>
              <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip />
              <Bar dataKey="value" fill="#6366f1" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card"><h3>Requests by priority</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={analytics.data?.requests_by_priority || []}>
              <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip />
              <Bar dataKey="value" fill="#14b8a6" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </>
  );
}

function Requests() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [processMessage, setProcessMessage] = useState("");
  const list = useQuery({
    queryKey: ["requests", search],
    queryFn: () => api<{ items: RequestRow[] }>(`/api/requests?page=1&page_size=50&search=${encodeURIComponent(search)}`),
  });
  const create = useMutation({
    mutationFn: (body: { sender: string; subject: string; message: string }) =>
      api("/api/requests", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => { setShowForm(false); queryClient.invalidateQueries({ queryKey: ["requests"] }); },
  });
  const process = useMutation({
    mutationFn: (requestId: string) => api<{
      status: string;
      result: { classification: { provider: { provider: string } } };
    }>(`/api/ai/process/${requestId}`, { method: "POST" }),
    onSuccess: result => {
      setProcessMessage(`Analysis used ${result.result.classification.provider.provider}; workflow status: ${result.status}.`);
      queryClient.invalidateQueries({ queryKey: ["requests"] });
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    create.mutate({ sender: String(data.get("sender")), subject: String(data.get("subject")), message: String(data.get("message")) });
  }
  return (
    <>
      <PageTitle title="Requests" action={<button className="primary" onClick={() => setShowForm(!showForm)}><Plus /> New request</button>} />
      {showForm && <form className="card form-grid" onSubmit={submit}>
        <input name="sender" type="email" placeholder="Sender email" required />
        <input name="subject" placeholder="Subject" required />
        <textarea name="message" placeholder="Request details" required />
        <button className="primary" type="submit" disabled={create.isPending}>{create.isPending ? "Submitting..." : "Submit"}</button>
      </form>}
      {create.isError && <div className="error">{(create.error as Error).message}</div>}
      {process.isError && <div className="error">{(process.error as Error).message}</div>}
      {processMessage && <div className="success-message">{processMessage}</div>}
      <input className="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search requests..." />
      <div className="card table-wrap">
        {list.isLoading ? <div className="loading">Loading requests...</div> :
          list.isError ? <div className="error">{(list.error as Error).message}</div> :
          (list.data?.items.length ? <table><thead><tr><th>Request</th><th>Department</th><th>Priority</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>{list.data.items.map(row =>
              <tr key={row.id}><td><strong>{row.subject}</strong><small>{row.sender}</small></td><td>{row.department}</td>
                <td><span className={`badge ${row.priority.toLowerCase()}`}>{row.priority}</span></td><td>{row.status}</td>
                <td>{["Pending", "Failed"].includes(row.status)
                  ? <button className="primary" disabled={process.isPending} onClick={() => { setProcessMessage(""); process.mutate(row.id); }}>
                      {process.isPending ? "Processing..." : "Run AI workflow"}
                    </button>
                  : "—"}</td></tr>
            )}</tbody></table> : <div className="empty">No requests have been submitted.</div>)}
      </div>
    </>
  );
}

function Approvals() {
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: ["approvals"], queryFn: () => api<any[]>("/api/approvals") });
  const action = useMutation({
    mutationFn: ({ id, decision, draft }: { id: string; decision: "approve" | "reject"; draft: string }) =>
      api(`/api/approvals/${id}/${decision}`, { method: "POST", body: JSON.stringify({ comments: "Reviewed in dashboard", draft }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["approvals"] }),
  });
  return <><PageTitle title="Approval Center" /><div className="approval-list">
    {list.isLoading && <div className="loading">Loading approvals...</div>}
    {list.data?.length ? list.data.map((item: any) => <ApprovalCard key={item.request.id} item={item} action={action.mutate} />)
      : <div className="card empty">No requests are awaiting approval.</div>}
  </div></>;
}

function ApprovalCard({ item, action }: { item: any; action: (value: { id: string; decision: "approve" | "reject"; draft: string }) => void }) {
  const [draft, setDraft] = useState(item.draft);
  return <article className="card approval-card">
    <div><h3>{item.request.subject}</h3><p>{item.request.sender}</p><span className="badge high">{item.request.priority}</span></div>
    <textarea value={draft} onChange={e => setDraft(e.target.value)} />
    <div className="actions"><button className="danger" onClick={() => action({ id: item.request.id, decision: "reject", draft })}>Reject</button>
      <button className="primary" onClick={() => action({ id: item.request.id, decision: "approve", draft })}>Approve</button></div>
  </article>;
}

function Agents() {
  const query = useQuery({ queryKey: ["agents"], queryFn: () => api<any[]>("/api/ai/agents") });
  return <><PageTitle title="AI Agent Monitoring" /><div className="card table-wrap">
    {query.data ? <table><thead><tr><th>Agent</th><th>Status</th><th>Mode</th></tr></thead><tbody>
      {query.data.map(agent => <tr key={agent.name}><td>{agent.name}</td><td><span className="badge low">Available</span></td><td>{agent.mode}</td></tr>)}
    </tbody></table> : <div className="loading">Loading agents...</div>}
  </div></>;
}

function Workflows() {
  const query = useQuery({ queryKey: ["workflows"], queryFn: () => api<any[]>("/api/workflows") });
  return <><PageTitle title="Workflow Management" /><div className="card table-wrap">
    {query.data?.length ? <table><thead><tr><th>Workflow</th><th>Request</th><th>Status</th><th>Error</th></tr></thead><tbody>
      {query.data.map(row => <tr key={row.id}><td>{row.id.slice(0, 8)}</td><td>{row.request_id.slice(0, 8)}</td><td>{row.status}</td><td>{row.error || "—"}</td></tr>)}
    </tbody></table> : <div className="empty">No workflow executions yet.</div>}
  </div></>;
}

function Knowledge() {
  const queryClient = useQueryClient();
  const docs = useQuery({ queryKey: ["knowledge"], queryFn: () => api<any[]>("/api/knowledge/documents") });
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData(); form.append("file", file);
      const token = localStorage.getItem("intelliflow_token");
      const response = await fetch(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/knowledge/upload`, {
        method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {}, body: form,
      });
      if (!response.ok) throw new Error("Upload failed");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["knowledge"] }),
  });
  return <><PageTitle title="Knowledge Base" /><div className="card">
    <label className="upload"><input type="file" accept=".pdf,.txt" onChange={e => e.target.files?.[0] && upload.mutate(e.target.files[0])} />
      Upload PDF or TXT</label>
    {upload.isError && <div className="error">{(upload.error as Error).message}</div>}
  </div><div className="card table-wrap">{docs.data?.length ?
    <table><thead><tr><th>Document</th><th>Type</th></tr></thead><tbody>{docs.data.map(doc =>
      <tr key={doc.id}><td>{doc.filename}</td><td>{doc.content_type}</td></tr>)}</tbody></table> :
    <div className="empty">No documents uploaded.</div>}</div></>;
}

function SettingsPage() {
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<any>("/api/settings") });
  return <><PageTitle title="Settings" /><div className="card settings">
    {settings.isLoading ? <div>Loading settings...</div> : <>
      <label>AI provider<input value={settings.data?.ai_provider || "mock"} readOnly /></label>
      {settings.data?.ai_provider === "gemini" && <>
        <label>Gemini model<input value={settings.data?.ai_model || ""} readOnly /></label>
        <label>Gemini API key<input value={settings.data?.gemini_api_key_configured ? "Configured on backend" : "Missing from backend environment"} readOnly /></label>
      </>}
      <p>Gemini credentials, database connection, and JWT signing secret are configured on the backend and never sent to the browser.</p>
    </>}
  </div></>;
}

export default function App() {
  const authenticated = Boolean(localStorage.getItem("intelliflow_token"));
  return <Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/*" element={authenticated ? <Shell /> : <Navigate to="/login" replace />} />
  </Routes>;
}
