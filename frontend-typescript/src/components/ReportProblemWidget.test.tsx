import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi, type Mock } from "vitest";
import { ReportProblemWidget } from "./ReportProblemWidget";
import * as bugReportApi from "@/api/bugReportApi";
import * as axiosConfig from "@/api/axiosConfig";

vi.mock("@/api/bugReportApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/bugReportApi")>();
  return {
    ...actual,
    submitBugReport: vi.fn(),
  };
});

vi.mock("@/api/axiosConfig", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/axiosConfig")>();
  return {
    ...actual,
    getLastApiCall: vi.fn(),
  };
});

const submitBugReportMock = bugReportApi.submitBugReport as unknown as Mock;
const getLastApiCallMock = axiosConfig.getLastApiCall as unknown as Mock;

function renderWidget() {
  return render(
    <MemoryRouter initialEntries={["/budgets/142"]}>
      <ReportProblemWidget />
    </MemoryRouter>,
  );
}

describe("ReportProblemWidget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("opens the modal with the current page path captured as context", async () => {
    const user = userEvent.setup();
    renderWidget();

    await user.click(screen.getByTitle("Report a problem"));

    expect(screen.getByRole("heading", { name: "Report a problem" })).toBeInTheDocument();
    expect(screen.getByText("/budgets/142")).toBeInTheDocument();
  });

  it("shows and submits the last API call when one is on record", async () => {
    const user = userEvent.setup();
    getLastApiCallMock.mockReturnValue("GET /api/v1/budgets/123 (500)");
    submitBugReportMock.mockResolvedValue({ id: "br1" });
    renderWidget();

    await user.click(screen.getByTitle("Report a problem"));
    expect(screen.getByText("GET /api/v1/budgets/123 (500)")).toBeInTheDocument();

    await user.type(
      screen.getByPlaceholderText(/describe what you were doing/i),
      "Save button did nothing",
    );
    await user.click(screen.getByRole("button", { name: "Send report" }));

    await waitFor(() =>
      expect(submitBugReportMock).toHaveBeenCalledWith(
        expect.objectContaining({ lastApiCall: "GET /api/v1/budgets/123 (500)" }),
      ),
    );
  });

  it("omits the last-API-call chip when none is on record", async () => {
    const user = userEvent.setup();
    getLastApiCallMock.mockReturnValue(null);
    renderWidget();

    await user.click(screen.getByTitle("Report a problem"));

    expect(screen.queryByText(/\(200\)|\(500\)/)).not.toBeInTheDocument();
  });

  it("requires a non-empty description before submitting", async () => {
    const user = userEvent.setup();
    renderWidget();

    await user.click(screen.getByTitle("Report a problem"));
    await user.click(screen.getByRole("button", { name: "Send report" }));

    expect(screen.getByText("Please describe what happened.")).toBeInTheDocument();
    expect(submitBugReportMock).not.toHaveBeenCalled();
  });

  it("submits the report and shows the confirmation state", async () => {
    const user = userEvent.setup();
    submitBugReportMock.mockResolvedValue({ id: "br1" });
    renderWidget();

    await user.click(screen.getByTitle("Report a problem"));
    await user.type(
      screen.getByPlaceholderText(/describe what you were doing/i),
      "Save button did nothing",
    );
    await user.click(screen.getByRole("button", { name: "Send report" }));

    await waitFor(() =>
      expect(submitBugReportMock).toHaveBeenCalledWith(
        expect.objectContaining({
          description: "Save button did nothing",
          pagePath: "/budgets/142",
        }),
      ),
    );
    expect(await screen.findByText(/thanks/i)).toBeInTheDocument();
  });

  it("shows the backend's error message and stays on the form when submission fails", async () => {
    const user = userEvent.setup();
    submitBugReportMock.mockRejectedValue({
      response: { data: { detail: "Something went wrong" } },
    });
    renderWidget();

    await user.click(screen.getByTitle("Report a problem"));
    await user.type(
      screen.getByPlaceholderText(/describe what you were doing/i),
      "Save button did nothing",
    );
    await user.click(screen.getByRole("button", { name: "Send report" }));

    expect(await screen.findByText("Something went wrong")).toBeInTheDocument();
    expect(screen.queryByText(/thanks/i)).not.toBeInTheDocument();
  });

  it("rejects an oversized screenshot client-side without calling the endpoint", async () => {
    const user = userEvent.setup();
    renderWidget();

    await user.click(screen.getByTitle("Report a problem"));
    const oversized = new File([new Uint8Array(6 * 1024 * 1024)], "big.png", {
      type: "image/png",
    });
    await user.upload(screen.getByLabelText("Attach a screenshot"), oversized);

    expect(screen.getByText(/exceeds the 5mb limit/i)).toBeInTheDocument();
  });

  it("accepts a screenshot pasted into the description field", async () => {
    const user = userEvent.setup();
    renderWidget();

    await user.click(screen.getByTitle("Report a problem"));
    const textarea = screen.getByPlaceholderText(/describe what you were doing/i);

    const file = new File(["fake-png-bytes"], "pasted.png", { type: "image/png" });
    const clipboardData = {
      items: [{ type: "image/png", getAsFile: () => file }],
    };
    fireEvent.paste(textarea, { clipboardData });

    expect(screen.getByText("pasted.png")).toBeInTheDocument();
  });

  it("rejects a disallowed screenshot type client-side without calling the endpoint", async () => {
    const user = userEvent.setup({ applyAccept: false });
    renderWidget();

    await user.click(screen.getByTitle("Report a problem"));
    const badType = new File(["hello"], "notes.txt", { type: "text/plain" });
    await user.upload(screen.getByLabelText("Attach a screenshot"), badType);

    expect(screen.getByText(/unsupported image type/i)).toBeInTheDocument();
  });

  it("resets the form after cancelling and reopening", async () => {
    const user = userEvent.setup();
    renderWidget();

    await user.click(screen.getByTitle("Report a problem"));
    await user.type(
      screen.getByPlaceholderText(/describe what you were doing/i),
      "Draft text",
    );
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    await user.click(screen.getByTitle("Report a problem"));
    expect(screen.getByPlaceholderText(/describe what you were doing/i)).toHaveValue("");
  });
});
