import gatewayApi from "@/api/gatewayApi";

export interface BugReport {
  id: string;
  user_id: string;
  description: string;
  page_path: string;
  user_agent: string;
  client_timestamp: string;
  screenshot_storage_key: string | null;
}

export const submitBugReport = async (payload: {
  description: string;
  pagePath: string;
  userAgent: string;
  clientTimestamp: string;
  lastApiCall?: string | null;
  screenshot?: File | null;
}): Promise<BugReport> => {
  const formData = new FormData();
  formData.append("description", payload.description);
  formData.append("page_path", payload.pagePath);
  formData.append("user_agent", payload.userAgent);
  formData.append("client_timestamp", payload.clientTimestamp);
  if (payload.lastApiCall) formData.append("last_api_call", payload.lastApiCall);
  if (payload.screenshot) formData.append("screenshot", payload.screenshot);

  const { data } = await gatewayApi.post("/bug-reports/", formData);
  return data;
};
