// API service for compliance-related operations

// Base URL for the API
const API_BASE_URL = "http://localhost:8001";

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
