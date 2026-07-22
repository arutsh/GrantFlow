import { Routes, Route, Navigate, BrowserRouter, Outlet } from "react-router-dom";
import { useAuth, AuthProvider } from "./context/AuthContext";
import { AiChatProvider } from "./context/AiChatContext";
import Login from "./pages/Login";
import LandingPage from "./pages/LandingPage";
import LegalPage from "./pages/Legal";
import Dashboard from "./pages/Dashboard/Dashboard";
import { JSX } from "react";
import Register from "./pages/Register";
import Onboarding from "./pages/OnBoarding";
import BudgetsPage from "./pages/Budgets/budgets";
import { SingleBudgetViewContainer } from "./pages/Budgets/SingleBudgetView";
import DashboardLayout from "./pages/Dashboard/DashboardLayout";
import SettingsPage from "./pages/Settings/Settings";
import DonorDashboard from "./pages/DonorDashboard/DonorDashboard";

function PrivateRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

function AuthenticatedLayout() {
  return (
    <DashboardLayout>
      <Outlet />
    </DashboardLayout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AiChatProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/legal" element={<LegalPage />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/onboarding"
              element={
                <PrivateRoute>
                  <Onboarding />
                </PrivateRoute>
              }
            />
            <Route
              element={
                <PrivateRoute>
                  <AuthenticatedLayout />
                </PrivateRoute>
              }
            >
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/donor-dashboard" element={<DonorDashboard />} />
              <Route path="/budgets" element={<BudgetsPage />} />
              <Route path="/budgets/:id" element={<SingleBudgetViewContainer />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AiChatProvider>
    </AuthProvider>
  );
}
