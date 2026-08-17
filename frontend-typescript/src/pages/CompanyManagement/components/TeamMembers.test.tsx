import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { TeamMembers } from "./TeamMembers";
import * as adminManagementApi from "@/api/adminManagementApi";

function renderTeamMembers() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <TeamMembers />
    </QueryClientProvider>,
  );
}

describe("TeamMembers", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("lists members and lets an admin invite a new teammate", async () => {
    const user = userEvent.setup();
    vi.spyOn(adminManagementApi, "listCompanyUsers").mockResolvedValue([
      {
        id: "u1",
        first_name: "Ada",
        last_name: "Lovelace",
        email: "ada@example.com",
        role: "admin",
        status: "active",
        email_verified: true,
      },
    ]);
    const inviteMock = vi.spyOn(adminManagementApi, "inviteUser").mockResolvedValue({
      user_id: "u2",
      email: "new@example.com",
      status: "pending",
    });

    renderTeamMembers();

    expect(await screen.findByText("Ada Lovelace")).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("teammate@example.org"), "new@example.com");
    await user.click(screen.getByRole("button", { name: "Invite" }));

    await waitFor(() => {
      expect(inviteMock).toHaveBeenCalledWith({ email: "new@example.com" });
    });
  });

  it("promotes a non-admin member on click", async () => {
    const user = userEvent.setup();
    vi.spyOn(adminManagementApi, "listCompanyUsers").mockResolvedValue([
      {
        id: "u1",
        first_name: "Grace",
        last_name: "Hopper",
        email: "grace@example.com",
        role: "user",
        status: "active",
        email_verified: true,
      },
    ]);
    const roleMock = vi.spyOn(adminManagementApi, "updateUserRole").mockResolvedValue({
      id: "u1",
      first_name: "Grace",
      last_name: "Hopper",
      email: "grace@example.com",
      role: "admin",
      status: "active",
      email_verified: true,
    });

    renderTeamMembers();
    await screen.findByText("Grace Hopper");

    await user.click(screen.getByRole("button", { name: "Promote" }));

    await waitFor(() => {
      expect(roleMock).toHaveBeenCalledWith("u1", "admin");
    });
  });

  it("removes a member after confirming", async () => {
    const user = userEvent.setup();
    vi.spyOn(adminManagementApi, "listCompanyUsers").mockResolvedValue([
      {
        id: "u1",
        first_name: "Grace",
        last_name: "Hopper",
        email: "grace@example.com",
        role: "user",
        status: "active",
        email_verified: true,
      },
    ]);
    const removeMock = vi.spyOn(adminManagementApi, "removeCompanyUser").mockResolvedValue();

    renderTeamMembers();
    await screen.findByText("Grace Hopper");

    await user.click(screen.getByRole("button", { name: "Remove" }));
    await user.click(screen.getByRole("button", { name: "Yes" }));

    await waitFor(() => {
      expect(removeMock).toHaveBeenCalledWith("u1");
    });
  });
});
