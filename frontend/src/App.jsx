import React, { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import LiveFeed from "./pages/LiveFeed.jsx";
import Alerts from "./pages/Alerts.jsx";
import Zones from "./pages/Zones.jsx";
import Users from "./pages/Users.jsx";
import { api } from "./api/client.js";

function useAuthedUser() {
  const [user, setUser] = useState(undefined);
  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);
  return user;
}

export default function App() {
  const user = useAuthedUser();
  const [showRegister, setShowRegister] = useState(false);

  if (user === undefined) {
    return <div className="login-shell"><span className="mono" style={{ color: "var(--slate-400)" }}>Loading…</span></div>;
  }

  if (user === null) {
    if (showRegister) {
      return (
        <Register 
          onRegistered={() => window.location.reload()} 
          switchToLogin={() => setShowRegister(false)} 
        />
      );
    }
    return (
      <Login 
        onLoggedIn={() => window.location.reload()} 
        switchToRegister={() => setShowRegister(true)} 
      />
    );
  }

  return (
    <div className="app-shell">
      <Sidebar user={user} />
      <div className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/live" element={<LiveFeed />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/zones" element={<Zones />} />
          <Route path="/users" element={user.role === "admin" ? <Users /> : <Navigate to="/" />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>
    </div>
  );
}