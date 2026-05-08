import { NavLink } from "react-router-dom";

export default function Header({ connected }) {
  return (
    <header className="header">
      <div className="brand">
        <span>IMS CONTROL</span>
        <h1>Cerebro Incident Desk</h1>
      </div>
      <nav className="nav">
        <NavLink to="/" end>
          Dashboard
        </NavLink>
        <NavLink to="/metrics">Metrics</NavLink>
        <div className="status-chip">
          <span className={connected ? "status-dot" : "status-dot offline"} />
          {connected ? "Live" : "Offline"}
        </div>
      </nav>
    </header>
  );
}
