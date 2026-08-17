import { Navigate, Route, Routes } from "react-router-dom";
import DashboardLayout from "./layouts/DashboardLayout";
import Dashboard from "./pages/Dashboard";

function Placeholder({ title }: { title: string }) {
  return (
    <div className="placeholder-page">
      <p className="eyebrow">Nexora</p>
      <h2>{title}</h2>
      <p>This section is coming next.</p>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/projects" element={<Placeholder title="Projects" />} />
        <Route path="/tasks" element={<Placeholder title="Tasks" />} />
        <Route path="/team" element={<Placeholder title="Team" />} />
        <Route path="/analytics" element={<Placeholder title="Analytics" />} />
        <Route path="/settings" element={<Placeholder title="Settings" />} />
      </Route>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
