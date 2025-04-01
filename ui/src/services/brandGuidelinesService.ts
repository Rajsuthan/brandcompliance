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

export const uploadBrandGuideline = async (
  file: File,
  brand_name: string,
  authToken: string,
  description?: string
): Promise<BrandGuidelineUploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("brand_name", brand_name);
  if (description) {
    formData.append("description", description);
  }

  const response = await fetch(`${API_BASE_URL}/api/brand-guidelines/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to upload brand guideline");
  }

  return response.json();
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
