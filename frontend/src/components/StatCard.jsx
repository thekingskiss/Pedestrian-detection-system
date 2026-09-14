import React from "react";

export default function StatCard({ label, value, tone }) {
  return (
    <div className="bbox-card">
      <div className="corner-tl" />
      <div className="corner-br" />
      <div className="stat-label">{label}</div>
      <div className={`stat-value${tone ? ` ${tone}` : ""}`}>{value}</div>
    </div>
  );
}
