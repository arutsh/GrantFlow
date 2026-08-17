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
import ConfirmEmail from "./pages/ConfirmEmail";
import VerifyEmail from "./pages/VerifyEmail";
import AcceptInvite from "./pages/AcceptInvite";
import CompanyManagementPage from "./pages/CompanyManagement/CompanyManagement";
import BudgetsPage from "./pages/Budgets/budgets";
import { SingleBudgetViewContainer } from "./pages/Budgets/SingleBudgetView";
import ReportDetailView from "./pages/Budgets/ReportDetailView";
import BudgetReportsPage from "./pages/Budgets/BudgetReportsPage";
import ReportsPage from "./pages/Budgets/ReportsPage";
import FundedReportsPage from "./pages/Budgets/FundedReportsPage";
import DashboardLayout from "./pages/Dashboard/DashboardLayout";
import SettingsPage from "./pages/Settings/Settings";

// Authenticated, but doesn't require a verified email — used for the
// confirm-email screen itself, which must stay reachable by unverified
// users (otherwise PrivateRoute's redirect target would loop back to
// itself).
function AuthOnlyRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

function PrivateRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated, loading, emailVerified } = useAuth();
  if (loading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!emailVerified) return <Navigate to="/confirm-email" replace />;
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
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/accept-invite" element={<AcceptInvite />} />
            <Route
              path="/confirm-email"
              element={
                <AuthOnlyRoute>
                  <ConfirmEmail />
                </AuthOnlyRoute>
              }
            />
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
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/reports/funded" element={<FundedReportsPage />} />
              <Route path="/budgets" element={<BudgetsPage />} />
              <Route path="/budgets/:id" element={<SingleBudgetViewContainer />} />
              <Route path="/budgets/:id/reports" element={<BudgetReportsPage />} />
              <Route
                path="/budgets/:id/reports/:reportId"
                element={<ReportDetailView />}
              />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/company-management" element={<CompanyManagementPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AiChatProvider>
    </AuthProvider>
  );
}
