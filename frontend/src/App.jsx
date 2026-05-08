import { BrowserRouter, Route, Routes } from "react-router-dom";

import ErrorBoundary from "./components/ErrorBoundary";
import { useIncidentStream } from "./hooks/useIncidentStream";
import AnalyticsPage from "./pages/AnalyticsPage";
import DashboardPage from "./pages/DashboardPage";
import MetricsPage from "./pages/MetricsPage";

export default function App() {
  const stream = useIncidentStream();

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <div className="app-shell">
          <Routes>
            <Route path="/" element={<DashboardPage stream={stream} />} />
            <Route
              path="/metrics"
              element={<MetricsPage connected={stream.connected} />}
            />
            <Route
              path="/analytics"
              element={<AnalyticsPage connected={stream.connected} />}
            />
          </Routes>
        </div>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

