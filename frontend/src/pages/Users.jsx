import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function Users() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ email: "", full_name: "", role: "officer", password: "" });

  function refresh() {
    api.listUsers().then(setUsers).catch((e) => setError(e.message));
  }

  useEffect(refresh, []);

  async function handleCreate(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.createUser(form);
      setForm({ email: "", full_name: "", role: "officer", password: "" });
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeactivate(id) {
    await api.deactivateUser(id);
    refresh();
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">FR-12 · Admin only</div>
          <h1 className="page-title">User Access Management</h1>
        </div>
      </div>

      {error && <div className="error-text">{error}</div>}

      <form className="bbox-card" onSubmit={handleCreate} style={{ marginBottom: 28, maxWidth: 420 }}>
        <div className="corner-tl" />
        <div className="corner-br" />
        <div className="field">
          <label>Full name</label>
          <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
        </div>
        <div className="field">
          <label>Email</label>
          <input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        </div>
        <div className="field">
          <label>Role</label>
          <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="officer">Traffic Safety Officer</option>
            <option value="admin">Administrator</option>
            <option value="auditor">Auditor</option>
          </select>
        </div>
        <div className="field">
          <label>Temporary password</label>
          <input className="input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
        </div>
        <button className="btn" type="submit">Create account</button>
      </form>

      <div className="bbox-card" style={{ padding: 0 }}>
        <div className="corner-tl" />
        <div className="corner-br" />
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>{u.role}</td>
                <td style={{ color: u.is_active ? "var(--safe-green)" : "var(--slate-400)" }}>
                  {u.is_active ? "active" : "deactivated"}
                </td>
                <td>
                  {u.is_active && (
                    <button className="btn secondary" onClick={() => handleDeactivate(u.id)}>
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
