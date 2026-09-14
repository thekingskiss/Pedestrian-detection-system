import React from "react";

export default function AlertBadge({ severity }) {
  const label = severity === "critical" ? "Critical" : severity === "caution" ? "Caution" : "Safe";
  return (
    <span className={`badge ${severity}`}>
      <span className="pulse" />
      {label}
    </span>
  );
}
