// API service for compliance-related operations

// REMIND ME TO CHANGE THIS WHEN DEPLOYING
// PROD: https://brandcompliance.onrender.com

// Base URL for the API
// local
// export const API_BASE_URL = "http://localhost:8001";
export const API_BASE_URL = "https://brandcompliance.onrender.com";

// Interface for authentication response
interface AuthResponse {
  access_token: string;
  token_type: string;
}

// Interface for compliance check event
interface ComplianceEvent {
  type: "thinking" | "text" | "tool" | "complete";
  content: string;
}

// Interface for video compliance check request
interface VideoComplianceRequest {
  video_url?: string;
  message?: string;
  analysis_modes?: string[];
  brand_name?: string; // Added brand name field
}

// Interface for video upload response
interface VideoUploadResponse {
  filename: string;
  url: string | null;
}

// Interface for feedback response
interface FeedbackResponse {
  id: string;
  status: string;
}

// Interface for feedback item
interface FeedbackItem {
  id: string;
  user_id: string;
  content: string;
  created_at: string;
}

// Interface for get feedback response
interface GetFeedbackResponse {
  feedback: FeedbackItem[];
  status: string;
}

/**
 * Login to get an authentication token
 * @param username User's username
 * @param password User's password
 * @returns Promise with the authentication token
 */
export const login = async (
  username: string,
  password: string
): Promise<string> => {
  try {
    const response = await fetch(`${API_BASE_URL}/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      throw new Error(`Login failed: ${response.status}`);
    }

    const data: AuthResponse = await response.json();
    return data.access_token;
  } catch (error) {
    console.error("Login error:", error);
    throw error;
  }
};

/**
 * Submit user feedback for the compliance system
 * @param content The feedback content
 * @param token Authentication token
 * @returns Promise with the feedback ID
 */
export const submitFeedback = async (
  content: string,
  token: string
): Promise<string> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/compliance/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }

    const data: FeedbackResponse = await response.json();
    return data.id;
  } catch (error) {
    console.error("Submit feedback error:", error);
    throw error;
  }
};

/**
 * Get all feedback submitted by the current user
 * @param token Authentication token
 * @returns Promise with the list of feedback items
 */
export const getFeedback = async (token: string): Promise<FeedbackItem[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/compliance/feedback`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }

    const data: GetFeedbackResponse = await response.json();
    return data.feedback;
  } catch (error) {
    console.error("Get feedback error:", error);
    throw error;
  }
};

/**
 * Check image compliance with streaming response
 * @param imageFile The image file to check
 * @param text Optional text prompt to accompany the image
 * @param token Authentication token
 * @param onEvent Callback function for each streaming event
 * @returns Promise that resolves when the stream ends
 */
export const checkImageCompliance = (
  imageFile: File,
  text: string = "Analyze this image for brand compliance.",
  token: string,
  onEvent: (event: ComplianceEvent) => void
): Promise<void> => {
  return new Promise((resolve, reject) => {
    // Create form data
    const formData = new FormData();
    formData.append("file", imageFile);
    formData.append("text", text);

    // Create fetch request
    const controller = new AbortController();
    const { signal } = controller;

    fetch(`${API_BASE_URL}/api/compliance/check-image`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
      signal,
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`API request failed: ${response.status}`);
        }

        // Set up event stream processing
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("Response body is not readable");
        }

        // Process the stream
        const processStream = async () => {
          try {
            let buffer = "";

            while (true) {
              const { done, value } = await reader.read();

              if (done) {
                // Process any remaining data in the buffer
                if (buffer.trim()) {
                  processEventData(buffer, onEvent);
                }
                break;
              }

              // Convert the chunk to text and add to buffer
              const chunk = new TextDecoder().decode(value);
              buffer += chunk;

              // Process complete events in the buffer
              const lines = buffer.split("\n\n");
              buffer = lines.pop() || ""; // Keep the last incomplete chunk in the buffer

              for (const line of lines) {
                if (line.trim()) {
                  processEventData(line, onEvent);
                }
              }
            }

            resolve();
          } catch (error) {
            reject(error);
          }
        };

        processStream();
      })
      .catch((error) => {
        reject(error);
      });

    // Helper function to process event data
    const processEventData = (
      data: string,
      callback: (event: ComplianceEvent) => void
    ) => {
      // Extract the data part from the SSE format
      const match = data.match(/^data:\s*(.*)/);
      if (!match) return;

      const eventData = match[1];

      // Parse the event type and content
      const colonIndex = eventData.indexOf(":");
      if (colonIndex === -1) return;

      const type = eventData.substring(
        0,
        colonIndex
      ) as ComplianceEvent["type"];
      const content = eventData.substring(colonIndex + 1);

      // Call the callback with the event
      callback({ type, content });

      // If this is the completion event, resolve the promise
      if (type === "complete") {
        resolve();
      }
    };
  });
};

/**
 * Upload a video file to Cloudflare R2 storage
 * @param videoFile The video file to upload
 * @param token Authentication token
 * @returns Promise with the upload response containing filename and URL
 */
export const uploadVideoToR2 = async (
  videoFile: File,
  token: string
): Promise<VideoUploadResponse> => {
  try {
    const formData = new FormData();
    formData.append("file", videoFile);

    const response = await fetch(`${API_BASE_URL}/api/upload-video/`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Video upload failed: ${response.status}`);
    }

    const data: VideoUploadResponse = await response.json();
    return data;
  } catch (error) {
    console.error("Video upload error:", error);
    throw error;
  }
};

/**
 * Check video compliance with streaming response
 * @param videoFile The video file to check or YouTube URL
 * @param isUrl Whether the provided input is a URL
 * @param text Optional text prompt to accompany the video
 * @param token Authentication token
 * @param onEvent Callback function for each streaming event
 * @returns Promise that resolves when the stream ends
 */
export const checkVideoCompliance = (
  videoFile: File | string,
  isUrl: boolean = false,
  text: string = "Analyze this video for brand compliance.",
  token: string,
  onEvent: (event: ComplianceEvent) => void,
  analysisModes: string[] = ["visual", "brand_voice", "tone"],
  brandName: string = "" // Added brand name parameter with default empty string
): Promise<void> => {
  return new Promise((resolve, reject) => {
    // Helper function to process event data
    const processEventData = (
      data: string,
      callback: (event: ComplianceEvent) => void
    ) => {
      // Extract the data part from the SSE format
      const match = data.match(/^data:\s*(.*)/);
      if (!match) return;

      const eventData = match[1];

      // Parse the event type and content
      const colonIndex = eventData.indexOf(":");
      if (colonIndex === -1) return;

      const type = eventData.substring(
        0,
        colonIndex
      ) as ComplianceEvent["type"];
      const content = eventData.substring(colonIndex + 1);

      console.log(`Streaming event: ${type}`, content.substring(0, 50) + "...");

      // Call the callback with the event
      callback({ type, content });

      // If this is the completion event, resolve the promise
      if (type === "complete") {
        resolve();
      }
    };

    // Handle file upload first if needed
    const prepareVideoSource = async (): Promise<VideoComplianceRequest> => {
      if (isUrl) {
        // Handle URL-based video
        return {
          video_url: videoFile as string,
          message: text,
          analysis_modes: analysisModes,
          brand_name: brandName, // Include brand name in the request
        };
      } else {
        // Handle file upload by first uploading to R2
        // First event to indicate upload is starting
        onEvent({
          type: "text",
          content: "Uploading video to storage...",
        });

        try {
          // Upload the video file to R2
          const uploadResult = await uploadVideoToR2(videoFile as File, token);

          // Notify about successful upload
          onEvent({
            type: "text",
            content: "Video uploaded successfully. Starting analysis...",
          });

          // Return request body with the uploaded video URL
          return {
            video_url: uploadResult.url || uploadResult.filename,
            message: text,
            analysis_modes: analysisModes,
            brand_name: brandName, // Include brand name in the request
          };
        } catch (error) {
          throw new Error(`Failed to upload video: ${error}`);
        }
      }
    };

    // Main execution flow
    prepareVideoSource()
      .then((requestBody) => {
        const controller = new AbortController();
        const { signal } = controller;

        return fetch(`${API_BASE_URL}/api/compliance/check-video`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
          signal,
        });
      })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`API request failed: ${response.status}`);
        }

        // Set up event stream processing
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("Response body is not readable");
        }

        // Process the stream
        const processStream = async () => {
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              // Process any remaining data in the buffer
              if (buffer.trim()) {
                processEventData(buffer, onEvent);
              }
              break;
            }

            // Convert the chunk to text and add to buffer
            const chunk = new TextDecoder().decode(value);
            buffer += chunk;

            // Process complete events in the buffer
            const lines = buffer.split("\n\n");
            buffer = lines.pop() || ""; // Keep the last incomplete chunk in the buffer

            for (const line of lines) {
              if (line.trim()) {
                processEventData(line, onEvent);
              }
            }
          }
        };

        return processStream();
      })
      .catch((error) => {
        console.error("Video compliance check error:", error);
        onEvent({
          type: "text",
          content: `Error: ${error.message}`,
        });
        reject(error);
      });
  });
};
