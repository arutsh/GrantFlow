import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import CompanyManagementPage from "./CompanyManagement";
import { AuthProvider } from "@/context/AuthContext";
import * as customerApi from "@/api/customerApi";
import * as adminManagementApi from "@/api/adminManagementApi";

function makeFakeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

function renderPage(claims: Record<string, unknown>) {
  localStorage.setItem("token", makeFakeJwt(claims));
  localStorage.setItem("username", "Jane Doe");
  const queryClient = new QueryClient();
  return render(
    <MemoryRouter initialEntries={["/company-management"]}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <Routes>
            <Route path="/company-management" element={<CompanyManagementPage />} />
            <Route path="/dashboard" element={<div>Dashboard page</div>} />
          </Routes>
        </AuthProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("CompanyManagementPage", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.spyOn(customerApi, "getCustomer").mockResolvedValue({
      id: "cust-1",
      name: "Acme NGO",
      country: "GB",
      currency: "GBP",
      is_ngo: true,
      is_donor: false,
    });
    vi.spyOn(adminManagementApi, "listCompanyUsers").mockResolvedValue([]);
  });

  it("redirects a plain user away to the dashboard", () => {
    renderPage({ role: "user", customer_id: "cust-1" });

    expect(screen.getByText("Dashboard page")).toBeInTheDocument();
  });

  it("shows the company picker for a superuser who isn't impersonating", () => {
    renderPage({ role: "superuser" });

    expect(screen.getByText("Manage a company")).toBeInTheDocument();
    expect(screen.queryByText("Team members")).not.toBeInTheDocument();
  });

  it("shows company details and team members for a real company admin", async () => {
    renderPage({ role: "admin", customer_id: "cust-1" });

    expect(await screen.findByText("Company details")).toBeInTheDocument();
    expect(screen.getByText("Team members")).toBeInTheDocument();
    expect(screen.queryByText("Danger zone")).not.toBeInTheDocument();
  });

  it("also shows the danger zone for a superuser mid-impersonation", async () => {
    renderPage({ role: "admin", customer_id: "cust-1", is_impersonating: true });

    expect(await screen.findByText("Company details")).toBeInTheDocument();
    expect(screen.getByText("Danger zone")).toBeInTheDocument();
  });
});
