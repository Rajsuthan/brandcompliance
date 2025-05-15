import { useAuth } from "@/lib/auth-context";

// Base API URL
const API_URL = "http://localhost:8000/api";

/**
 * Service for interacting with the compliance API
 */
export const useComplianceService = () => {
  const { getIdToken } = useAuth();

  /**
   * Get the compliance history for the current user
   */
  const getComplianceHistory = async () => {
    try {
      console.log("Getting ID token...");
      const token = await getIdToken();
      console.log(
        "Token received:",
        token ? `${token.substring(0, 10)}...` : "null"
      );

      if (!token) {
        throw new Error("Not authenticated");
      }

      console.log("Fetching from:", `${API_URL}/compliance/history`);
      const response = await fetch(`${API_URL}/compliance/history`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      console.log("Response status:", response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Error response body:", errorText);
        throw new Error(
          `Error fetching compliance history: ${response.status} ${response.statusText} - ${errorText}`
        );
      }

      const data = await response.json();
      console.log("Response data:", data);
      return data;
    } catch (error) {
      console.error("Error fetching compliance history:", error);
      throw error;
    }
  };

  /**
   * Get a specific compliance analysis
   */
  const getComplianceAnalysis = async (analysisId: string) => {
    try {
      const token = await getIdToken();
      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(
        `${API_URL}/compliance/analysis/${analysisId}`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(
          `Error fetching compliance analysis: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("Error fetching compliance analysis:", error);
      throw error;
    }
  };

  /**
   * Submit feedback for the compliance system
   */
  const submitFeedback = async (content: string) => {
    try {
      const token = await getIdToken();
      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(`${API_URL}/compliance/feedback`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        throw new Error(`Error submitting feedback: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error submitting feedback:", error);
      throw error;
    }
  };

  /**
   * Get all feedback for the current user
   */
  const getFeedback = async () => {
    try {
      const token = await getIdToken();
      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(`${API_URL}/compliance/feedback`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Error fetching feedback: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error fetching feedback:", error);
      throw error;
    }
  };

  return {
    getComplianceHistory,
    getComplianceAnalysis,
    submitFeedback,
    getFeedback,
  };
};

// Types for compliance data
export interface ComplianceAnalysisSummary {
  id: string;
  type: "image" | "video";
  filename: string;
  brand_name: string;
  created_at: string;
  compliance_score: number;
  media_type?: string;
  video_url?: string;
}

export interface ComplianceAnalysisDetail {
  id: string;
  user_id: string;
  type: "image" | "video";
  filename: string;
  brand_name: string;
  created_at: string;
  results: any;
  compliance_score: number;
  media_type?: string;
  video_url?: string;
}

export interface ComplianceHistoryResponse {
  analyses: ComplianceAnalysisSummary[];
  status: string;
}

export interface ComplianceAnalysisResponse {
  analysis: ComplianceAnalysisDetail;
  status: string;
}

export interface FeedbackItem {
  id: string;
  user_id: string;
  content: string;
  created_at: string;
}

export interface FeedbackResponse {
  feedback: FeedbackItem[];
  status: string;
}
