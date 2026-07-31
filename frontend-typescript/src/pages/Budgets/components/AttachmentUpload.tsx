import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Paperclip, Trash2, Upload } from "lucide-react";
import Button, { ConfirmDeleteButton } from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import {
  deleteAttachment,
  downloadAttachment,
  listAttachmentsByReportLine,
  uploadAttachment,
} from "@/api/reportApi";
import { attachmentsQueryKey } from "../queryKeys";
import { Attachment } from "../types/budget";

const MAX_SIZE_BYTES = 15 * 1024 * 1024;
// Kept in sync by hand with the backend's ALLOWED_CONTENT_TYPES — see
// design.md's noted duplication risk; drift here only means a slightly
// wrong client-side error message, the backend stays authoritative.
const ALLOWED_CONTENT_TYPES = ["application/pdf", "image/jpeg", "image/png", "image/heic"];
// Non-Safari browsers commonly report file.type === "" for .heic since it's
// an unrecognized extension — fall back to checking the filename extension
// so those uploads aren't rejected client-side before the backend sees them.
const ALLOWED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".heic"];
const ACCEPT_ATTR = ".pdf,.jpg,.jpeg,.png,.heic,application/pdf,image/jpeg,image/png,image/heic";

function isAllowedFile(file: File): boolean {
  if (file.type) return ALLOWED_CONTENT_TYPES.includes(file.type);
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  return ALLOWED_EXTENSIONS.includes(ext);
}

function formatFileSize(bytes: number | undefined): string {
  if (!bytes && bytes !== 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Compact per-line control: a paperclip (with attachment count) and, while
// editable, an upload shortcut — both just open the same AttachmentsModal.
// Replaces an earlier always-expanded panel under each line, which made the
// report-lines table grow unusably tall on reports with many lines.
export function AttachmentUpload({
  reportLineId,
  editable,
}: {
  reportLineId: string;
  // Draft-only, same gating as ReportLineRow's line edit/delete — viewing/
  // downloading stays available regardless, per
  // specs/budget-report-attachment-ui/spec.md.
  editable: boolean;
}) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: attachments } = useQuery({
    queryKey: attachmentsQueryKey(reportLineId),
    queryFn: () => listAttachmentsByReportLine(reportLineId),
  });
  const count = attachments?.length ?? 0;

  return (
    <div className="flex items-center justify-end gap-1">
      <Button
        variant="icon"
        title={count > 0 ? `${count} attachment(s)` : "No attachments yet"}
        onClick={() => setIsModalOpen(true)}
      >
        <span className="flex items-center gap-1">
          <Paperclip size={16} />
          {count > 0 && <span className="text-xs">{count}</span>}
        </span>
      </Button>
      {editable && (
        <Button variant="icon" title="Upload attachment" onClick={() => setIsModalOpen(true)}>
          <Upload size={16} />
        </Button>
      )}
      {isModalOpen && (
        <AttachmentsModal
          reportLineId={reportLineId}
          editable={editable}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </div>
  );
}

function AttachmentsModal({
  reportLineId,
  editable,
  onClose,
}: {
  reportLineId: string;
  editable: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");

  const { data: attachments } = useQuery({
    queryKey: attachmentsQueryKey(reportLineId),
    queryFn: () => listAttachmentsByReportLine(reportLineId),
  });

  const validateAndUpload = async (file: File) => {
    setError("");
    if (file.size > MAX_SIZE_BYTES) {
      setError("File exceeds the 15MB limit.");
      return;
    }
    if (!isAllowedFile(file)) {
      setError("Unsupported file type — allowed: PDF, JPEG, PNG, HEIC.");
      return;
    }
    setIsUploading(true);
    try {
      const attachment = await uploadAttachment(reportLineId, file);
      queryClient.setQueryData(
        attachmentsQueryKey(reportLineId),
        (prev: Attachment[] | undefined) => [...(prev ?? []), attachment],
      );
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(detail || "Failed to upload attachment. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (file) void validateAndUpload(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void validateAndUpload(file);
  };

  const handleDelete = async (id: string) => {
    setError("");
    try {
      await deleteAttachment(id);
      queryClient.setQueryData(
        attachmentsQueryKey(reportLineId),
        (prev: Attachment[] | undefined) => (prev ?? []).filter((a) => a.id !== id),
      );
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(detail || "Failed to delete attachment. Please try again.");
    }
  };

  const handleDownloadAll = async () => {
    setError("");
    let failures = 0;
    for (const attachment of attachments ?? []) {
      try {
        await downloadAttachment(attachment.id, attachment.filename ?? "attachment");
      } catch {
        failures += 1;
      }
    }
    if (failures > 0) {
      setError(`Failed to download ${failures} file${failures > 1 ? "s" : ""}.`);
    }
  };

  return (
    <Modal isOpen onClose={onClose} title="Attachments">
      <div className="flex flex-col gap-3">
        {editable && (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-4 text-center text-sm transition-colors ${
              isDragging ? "border-slate-500 bg-slate-50" : "border-slate-300"
            }`}
          >
            <p className="text-slate-500 mb-2">Drag & drop a file here, or</p>
            <input
              ref={fileInputRef}
              type="file"
              aria-label="Upload attachment"
              accept={ACCEPT_ATTR}
              onChange={handleFileChange}
              disabled={isUploading}
              className="text-xs text-slate-600"
            />
            {isUploading && <p className="text-xs text-slate-500 mt-2">Uploading...</p>}
          </div>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {!!attachments?.length && (
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">
              {attachments.length} file{attachments.length > 1 ? "s" : ""}
            </span>
            {attachments.length > 1 && (
              <Button
                variant="secondary"
                className="text-xs py-1 px-2"
                onClick={handleDownloadAll}
              >
                Download All
              </Button>
            )}
          </div>
        )}

        {attachments?.length ? (
          <ul className="flex flex-col gap-1 max-h-64 overflow-y-auto">
            {attachments.map((attachment) => (
              <li
                key={attachment.id}
                className="flex items-center gap-2 text-sm text-slate-600 border-b border-slate-100 py-2 last:border-0"
              >
                <Paperclip size={14} className="text-slate-400 shrink-0" />
                <span className="truncate flex-1">{attachment.filename}</span>
                <span className="text-xs text-slate-400 shrink-0">
                  {formatFileSize(attachment.size)}
                </span>
                <Button
                  variant="icon"
                  title="Download attachment"
                  onClick={() =>
                    downloadAttachment(attachment.id, attachment.filename ?? "attachment")
                  }
                >
                  <Download size={14} />
                </Button>
                {editable && (
                  <ConfirmDeleteButton
                    variant="icon-danger"
                    title="Delete attachment"
                    onConfirm={() => handleDelete(attachment.id)}
                  >
                    <Trash2 size={14} />
                  </ConfirmDeleteButton>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">No attachments yet.</p>
        )}
      </div>
    </Modal>
  );
}
