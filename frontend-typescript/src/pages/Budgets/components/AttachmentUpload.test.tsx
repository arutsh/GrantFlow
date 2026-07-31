import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import { AttachmentUpload } from "./AttachmentUpload";
import { Attachment } from "../types/budget";
import * as reportApi from "@/api/reportApi";

vi.mock("@/api/reportApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/reportApi")>();
  return {
    ...actual,
    listAttachmentsByReportLine: vi.fn(),
    uploadAttachment: vi.fn(),
    deleteAttachment: vi.fn(),
    downloadAttachment: vi.fn(),
  };
});

const listAttachmentsByReportLineMock = reportApi.listAttachmentsByReportLine as unknown as Mock;
const uploadAttachmentMock = reportApi.uploadAttachment as unknown as Mock;
const deleteAttachmentMock = reportApi.deleteAttachment as unknown as Mock;
const downloadAttachmentMock = reportApi.downloadAttachment as unknown as Mock;

function makeAttachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: "a1",
    report_line_id: "rl1",
    filename: "receipt.pdf",
    content_type: "application/pdf",
    size: 2048,
    ...overrides,
  };
}

function renderAttachmentUpload(editable: boolean) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AttachmentUpload reportLineId="rl1" editable={editable} />
    </QueryClientProvider>,
  );
}

describe("AttachmentUpload row control", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows an attachment count on the paperclip control", async () => {
    listAttachmentsByReportLineMock.mockResolvedValue([makeAttachment(), makeAttachment({ id: "a2" })]);
    renderAttachmentUpload(false);

    await waitFor(() => expect(screen.getByText("2")).toBeInTheDocument());
  });

  it("hides the upload shortcut when not editable", async () => {
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    renderAttachmentUpload(false);

    await waitFor(() => expect(listAttachmentsByReportLineMock).toHaveBeenCalledWith("rl1"));
    expect(screen.queryByTitle("Upload attachment")).not.toBeInTheDocument();
  });

  it("shows the upload shortcut when editable, opening the same modal as the paperclip", async () => {
    const user = userEvent.setup();
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    renderAttachmentUpload(true);

    await waitFor(() => expect(screen.getByTitle("Upload attachment")).toBeInTheDocument());
    await user.click(screen.getByTitle("Upload attachment"));

    expect(screen.getByRole("heading", { name: "Attachments" })).toBeInTheDocument();
    expect(screen.getByLabelText("Upload attachment")).toBeInTheDocument();
  });
});

describe("AttachmentUpload modal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function openModal(editable: boolean) {
    const user = userEvent.setup();
    renderAttachmentUpload(editable);
    await waitFor(() =>
      expect(screen.getByTitle(editable ? "Upload attachment" : /attachment/i)).toBeInTheDocument(),
    );
    await user.click(screen.getAllByRole("button")[0]);
    return user;
  }

  it("lists attachments with filename/size, a download control, and no delete control when not editable", async () => {
    listAttachmentsByReportLineMock.mockResolvedValue([makeAttachment()]);
    await openModal(false);

    await waitFor(() => expect(screen.getByText("receipt.pdf")).toBeInTheDocument());
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
    expect(screen.getByTitle("Download attachment")).toBeInTheDocument();
    expect(screen.queryByTitle("Delete attachment")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Upload attachment")).not.toBeInTheDocument();
  });

  it("rejects an oversized file client-side without calling the upload endpoint", async () => {
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    const user = await openModal(true);

    const oversized = new File([new Uint8Array(16 * 1024 * 1024)], "big.pdf", {
      type: "application/pdf",
    });
    await user.upload(screen.getByLabelText("Upload attachment"), oversized);

    expect(screen.getByText(/exceeds the 15mb limit/i)).toBeInTheDocument();
    expect(uploadAttachmentMock).not.toHaveBeenCalled();
  });

  it("rejects a disallowed content type client-side without calling the upload endpoint", async () => {
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    // The real accept="" filter would already stop most OS file pickers from
    // offering this file, but a user can still override it — bypass it here
    // to prove the component's own validation is the backstop.
    const user = userEvent.setup({ applyAccept: false });
    renderAttachmentUpload(true);
    await waitFor(() => expect(screen.getByTitle("Upload attachment")).toBeInTheDocument());
    await user.click(screen.getByTitle("Upload attachment"));

    const badType = new File(["hello"], "notes.txt", { type: "text/plain" });
    await user.upload(screen.getByLabelText("Upload attachment"), badType);

    expect(screen.getByText(/unsupported file type/i)).toBeInTheDocument();
    expect(uploadAttachmentMock).not.toHaveBeenCalled();
  });

  it("uploads a valid file and appends it to the displayed list", async () => {
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    uploadAttachmentMock.mockResolvedValue(makeAttachment({ id: "a2", filename: "photo.png" }));
    const user = await openModal(true);

    const file = new File(["hello"], "photo.png", { type: "image/png" });
    await user.upload(screen.getByLabelText("Upload attachment"), file);

    await waitFor(() =>
      expect(uploadAttachmentMock).toHaveBeenCalledWith("rl1", expect.any(File)),
    );
    await waitFor(() => expect(screen.getByText("photo.png")).toBeInTheDocument());
  });

  it("shows the backend's rejection message and leaves no partial attachment when upload fails", async () => {
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    uploadAttachmentMock.mockRejectedValue({
      response: { data: { detail: "File content does not match its declared type" } },
    });
    const user = await openModal(true);

    const file = new File(["hello"], "photo.png", { type: "image/png" });
    await user.upload(screen.getByLabelText("Upload attachment"), file);

    await waitFor(() =>
      expect(
        screen.getByText(/file content does not match its declared type/i),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText("photo.png")).not.toBeInTheDocument();
  });

  it("deletes an attachment and removes it from the displayed list", async () => {
    listAttachmentsByReportLineMock.mockResolvedValue([makeAttachment()]);
    deleteAttachmentMock.mockResolvedValue({});
    const user = await openModal(true);

    await waitFor(() => expect(screen.getByText("receipt.pdf")).toBeInTheDocument());
    await user.click(screen.getByTitle("Delete attachment"));
    await user.click(screen.getByRole("button", { name: "Yes" }));

    await waitFor(() => expect(deleteAttachmentMock).toHaveBeenCalledWith("a1"));
    await waitFor(() => expect(screen.queryByText("receipt.pdf")).not.toBeInTheDocument());
  });

  it("downloads an attachment using its filename", async () => {
    listAttachmentsByReportLineMock.mockResolvedValue([makeAttachment()]);
    const user = await openModal(false);

    await waitFor(() => expect(screen.getByText("receipt.pdf")).toBeInTheDocument());
    await user.click(screen.getByTitle("Download attachment"));

    expect(downloadAttachmentMock).toHaveBeenCalledWith("a1", "receipt.pdf");
  });

  it("shows a Download All control only when there's more than one attachment", async () => {
    listAttachmentsByReportLineMock.mockResolvedValue([
      makeAttachment({ id: "a1" }),
      makeAttachment({ id: "a2", filename: "photo.png" }),
    ]);
    const user = await openModal(false);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Download All" })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Download All" }));

    await waitFor(() => expect(downloadAttachmentMock).toHaveBeenCalledTimes(2));
  });
});
