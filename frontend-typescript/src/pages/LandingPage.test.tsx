import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import LandingPage from "./LandingPage";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<div>Dashboard Page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("LandingPage", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("renders the mission-driven content when unauthenticated", () => {
    renderAt("/");

    expect(
      screen.getByText("Grant management without spreadsheets."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Become a Founding Design Partner" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Become a Founding Design Partner" }),
    ).toBeInTheDocument();
  });

  it("does not offer login/sign-up/get-started anywhere on the page", () => {
    renderAt("/");

    expect(screen.queryByText(/sign up/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^log in$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/get started/i)).not.toBeInTheDocument();
  });

  it("renders the contact form and accepts a submission", async () => {
    renderAt("/");

    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Organisation")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Role")).toBeInTheDocument();
    expect(screen.getByLabelText("Message")).toBeInTheDocument();
    expect(
      screen.getByLabelText("I'd like to request a demo"),
    ).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Name"), "Jane Doe");
    await userEvent.type(screen.getByLabelText("Organisation"), "Acme Foundation");
    await userEvent.type(screen.getByLabelText("Email"), "jane@example.org");
    await userEvent.selectOptions(screen.getByLabelText("Role"), "Foundation");
    await userEvent.type(screen.getByLabelText("Message"), "We'd love to talk.");
    await userEvent.click(screen.getByLabelText("I'd like to request a demo"));
    await userEvent.click(
      screen.getByRole("button", { name: "Let's Start a Conversation" }),
    );

    expect(
      screen.getByText(/we've received your message/i),
    ).toBeInTheDocument();
  });

  it("redirects to /dashboard when authenticated", () => {
    localStorage.setItem("token", "fake-token");
    localStorage.setItem("username", "john");

    renderAt("/");

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
    expect(
      screen.queryByText("Grant management without spreadsheets."),
    ).not.toBeInTheDocument();
  });
});
