import { useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  Activity,
  Camera,
  CheckCircle2,
  Clock,
  FileText,
  Monitor,
  MessageCircle,
} from "lucide-react";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import { submitBugReport } from "@/api/bugReportApi";
import { getLastApiCall } from "@/api/axiosConfig";

const MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024;
const ALLOWED_SCREENSHOT_TYPES = ["image/png", "image/jpeg", "image/webp"];

// Friendly browser/OS label for the chip; display-only, raw UA is still sent to the backend.
function describeUserAgent(userAgent: string): string {
  const browserMatch =
    userAgent.match(/(Edg|Chrome|Firefox|Safari)\/(\d+)/) ??
    userAgent.match(/(Version)\/(\d+).*Safari/);
  const browserName = browserMatch?.[1] === "Edg" ? "Edge" : browserMatch?.[1];
  const browserVersion = browserMatch?.[2];

  let os = "";
  if (userAgent.includes("Windows")) os = "Windows";
  else if (userAgent.includes("Mac OS X")) os = "macOS";
  else if (userAgent.includes("Android")) os = "Android";
  else if (userAgent.includes("iPhone") || userAgent.includes("iPad")) os = "iOS";
  else if (userAgent.includes("Linux")) os = "Linux";

  if (!browserName) return userAgent;
  return [`${browserName} ${browserVersion ?? ""}`.trim(), os].filter(Boolean).join(" · ");
}

export function ReportProblemWidget() {
  const location = useLocation();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [description, setDescription] = useState("");
  const [screenshot, setScreenshot] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [context, setContext] = useState({
    pagePath: "",
    userAgent: "",
    clientTimestamp: new Date(),
    lastApiCall: null as string | null,
  });

  const resetForm = () => {
    setDescription("");
    setScreenshot(null);
    setError("");
  };

  const handleOpen = () => {
    setContext({
      pagePath: location.pathname,
      userAgent: navigator.userAgent,
      clientTimestamp: new Date(),
      lastApiCall: getLastApiCall(),
    });
    resetForm();
    setIsSubmitted(false);
    setIsOpen(true);
  };

  const handleClose = () => {
    setIsOpen(false);
    setIsSubmitted(false);
    resetForm();
  };

  const applyScreenshot = (file: File) => {
    setError("");
    if (file.size > MAX_SCREENSHOT_BYTES) {
      setError("Screenshot exceeds the 5MB limit.");
      return;
    }
    if (!ALLOWED_SCREENSHOT_TYPES.includes(file.type)) {
      setError("Unsupported image type — allowed: PNG, JPEG, WebP.");
      return;
    }
    setScreenshot(file);
  };

  const handleScreenshotChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (file) applyScreenshot(file);
  };

  const handleDescriptionPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const item = Array.from(e.clipboardData.items).find((i) => i.type.startsWith("image/"));
    const file = item?.getAsFile();
    if (!file) return;
    e.preventDefault();
    applyScreenshot(file);
  };

  const handleSubmit = async () => {
    if (!description.trim()) {
      setError("Please describe what happened.");
      return;
    }
    setError("");
    setIsSubmitting(true);
    try {
      await submitBugReport({
        description: description.trim(),
        pagePath: context.pagePath,
        userAgent: context.userAgent,
        clientTimestamp: context.clientTimestamp.toISOString(),
        lastApiCall: context.lastApiCall,
        screenshot,
      });
      setIsSubmitted(true);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(detail || "Failed to send report. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={handleOpen}
        title="Report a problem"
        aria-label="Report a problem"
        className="flex items-center justify-center w-9 h-9 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
      >
        <MessageCircle size={20} />
      </button>

      {isOpen && (
        <Modal isOpen onClose={handleClose} title={isSubmitted ? undefined : "Report a problem"}>
          {isSubmitted ? (
            <div className="flex flex-col items-center text-center py-2">
              <div className="w-14 h-14 rounded-full bg-green-50 flex items-center justify-center mb-4">
                <CheckCircle2 size={28} className="text-green-600" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Thanks — we&rsquo;ll follow up</h3>
              <p className="text-sm text-slate-500 leading-relaxed max-w-xs mb-6">
                We&rsquo;ve saved this report with the page, browser, and time above. If we need
                more details, we&rsquo;ll reach out to your account email.
              </p>
              <Button variant="primary" className="w-full" onClick={handleClose}>
                Done
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <p className="text-sm text-slate-500 leading-relaxed -mt-2">
                Tell us what happened — we&rsquo;ll include some technical details automatically.
              </p>

              <div>
                <label className="block text-sm font-medium text-slate-900 mb-2">
                  What were you trying to do?
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  onPaste={handleDescriptionPaste}
                  placeholder="Describe what you were doing and what went wrong... (you can paste a screenshot here)"
                  className="w-full min-h-[72px] border border-slate-300 rounded-lg p-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  disabled={isSubmitting}
                />
              </div>

              <div>
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
                  Included automatically
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center gap-1.5 bg-slate-100 text-slate-700 text-xs font-medium px-2.5 py-1.5 rounded-full">
                    <FileText size={14} />
                    {context.pagePath}
                  </span>
                  <span className="inline-flex items-center gap-1.5 bg-slate-100 text-slate-700 text-xs font-medium px-2.5 py-1.5 rounded-full">
                    <Monitor size={14} />
                    {describeUserAgent(context.userAgent)}
                  </span>
                  <span className="inline-flex items-center gap-1.5 bg-slate-100 text-slate-700 text-xs font-medium px-2.5 py-1.5 rounded-full">
                    <Clock size={14} />
                    {context.clientTimestamp.toLocaleString()}
                  </span>
                  {context.lastApiCall && (
                    <span className="inline-flex items-center gap-1.5 bg-slate-100 text-slate-700 text-xs font-medium px-2.5 py-1.5 rounded-full">
                      <Activity size={14} />
                      {context.lastApiCall}
                    </span>
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isSubmitting}
                className="flex items-center gap-2 border-[1.5px] border-dashed border-slate-300 rounded-lg px-3 py-2.5 text-sm text-slate-500 hover:border-slate-400 hover:text-slate-600 text-left"
              >
                <Camera size={16} />
                {screenshot ? screenshot.name : "Attach a screenshot (optional)"}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                aria-label="Attach a screenshot"
                accept="image/png,image/jpeg,image/webp"
                onChange={handleScreenshotChange}
                disabled={isSubmitting}
                className="hidden"
              />

              {error && <p className="text-sm text-red-600">{error}</p>}

              <div className="flex justify-end gap-3">
                <Button variant="text" onClick={handleClose} disabled={isSubmitting}>
                  Cancel
                </Button>
                <Button variant="primary" onClick={handleSubmit} disabled={isSubmitting}>
                  {isSubmitting ? "Sending..." : "Send report"}
                </Button>
              </div>
            </div>
          )}
        </Modal>
      )}
    </>
  );
}
