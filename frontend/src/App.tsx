import { Navigate, Route, Routes } from "react-router-dom";
import DashboardLayout from "./layouts/DashboardLayout";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ProtectedRoute from "./routes/ProtectedRoute";

function Placeholder({ title }: { title: string }) {
  return <div className="placeholder-page"><p className="eyebrow">Nexora</p><h2>{title}</h2><p>This workspace section is coming next.</p></div>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/projects" element={<Placeholder title="Projects" />} />
          <Route path="/tasks" element={<Placeholder title="Tasks" />} />
          <Route path="/team" element={<Placeholder title="Team" />} />
          <Route path="/analytics" element={<Placeholder title="Analytics" />} />
          <Route path="/settings" element={<Placeholder title="Settings" />} />
        </Route>
      </Route>
      <Route path="/" element={<Navigate to={localStorage.getItem("nexora_token") ? "/dashboard" : "/login"} replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
