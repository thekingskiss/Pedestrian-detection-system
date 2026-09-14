import React from "react";
import { NavLink } from "react-router-dom";
import { setToken } from "../api/client.js";

const LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/live", label: "Live Feed" },
  { to: "/alerts", label: "Alerts" },
  { to: "/zones", label: "Zones & Cameras" },
  { to: "/users", label: "Users", adminOnly: true },
];

export default function Sidebar({ user }) {
  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <span className="dot" />
        PedesPi Ops Console
      </div>
      {LINKS.filter((l) => !l.adminOnly || user.role === "admin").map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.end}
          className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
        >
          {l.label}
        </NavLink>
      ))}

      <div style={{ marginTop: "auto", paddingTop: 24 }}>
        <div className="mono" style={{ fontSize: 11, color: "var(--slate-400)", marginBottom: 6 }}>
          {user.full_name}
        </div>
        <div className="mono" style={{ fontSize: 10, color: "var(--slate-400)", marginBottom: 12 }}>
          role: {user.role}
        </div>
        <button
          className="btn secondary"
          style={{ width: "100%" }}
          onClick={() => {
            setToken(null);
            window.location.reload();
          }}
        >
          Sign out
        </button>
      </div>
    </nav>
  );
}
