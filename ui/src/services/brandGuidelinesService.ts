import { API_BASE_URL } from "./complianceService";

export interface BrandGuideline {
  id: string;
  filename: string;
  user_id: string;
  brand_name: string;
  total_pages: number;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface BrandGuidelineUploadResponse {
  guideline: BrandGuideline;
  pages_processed: number;
  message: string;
}

export const uploadBrandGuideline = (
  file: File,
  brand_name: string,
  authToken: string,
  description?: string,
  onProgress?: (progress: number) => void
): Promise<any> => {
  return new Promise(async (resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("brand_name", brand_name);
    if (description) {
      formData.append("description", description);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/brand-guidelines/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        // Try to get error message from response, else generic
        let errMsg = "Upload failed";
        try {
          const text = await response.text();
          errMsg = text;
        } catch {}
        reject(new Error(errMsg));
        return;
      }

      if (!response.body) {
        reject(new Error("No response body"));
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let lastResult: any = null;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          // SSE: split by double newlines
          const events = chunk.split("\n\n").filter(Boolean);
          for (const event of events) {
            if (event.startsWith("data:")) {
              try {
                const data = JSON.parse(event.replace("data:", "").trim());
                if (onProgress && typeof data.progress === "number") {
                  onProgress(data.progress);
                }
                lastResult = data;
              } catch (e) {
                // Ignore parse errors
              }
            }
          }
        }
      }

      if (lastResult && lastResult.status === "done") {
        resolve(lastResult);
      } else {
        reject(new Error("Upload did not complete successfully"));
      }
    } catch (err) {
      reject(err);
    }
  });
};

export const getUserBrandGuidelines = async (
  authToken: string
): Promise<BrandGuideline[]> => {
  const response = await fetch(`${API_BASE_URL}/api/brand-guidelines`, {
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to fetch brand guidelines");
  }

  return response.json();
};
