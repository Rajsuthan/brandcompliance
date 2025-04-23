// Batch Processing service for compliance operations
import { API_BASE_URL, login, submitFeedback, getFeedback } from './complianceService';

// Re-export these functions for convenience
export { login, submitFeedback, getFeedback };

// Interface for compliance check event
export interface ComplianceEvent {
  type: "thinking" | "text" | "tool" | "complete";
  content: string;
}

// Interface for batch processing status
export interface BatchProcessingStatus {
  id: string;
  status: 'queued' | 'processing' | 'completed' | 'error';
  progress: number;
  result?: string;
  error?: string;
}

/**
 * Process a media item (image or video) for compliance analysis
 * @param file The media file to process
 * @param isVideo Whether the file is a video
 * @param brandName The brand name for compliance checking
 * @param token Authentication token
 * @param onEvent Callback function for streaming events
 * @returns Promise that resolves when processing completes
 */
export const processMediaItem = async (
  file: File,
  isVideo: boolean,
  brandName: string,
  token: string,
  onEvent: (id: string, event: ComplianceEvent) => void
): Promise<void> => {
  try {
    // Create form data
    const formData = new FormData();
    formData.append("file", file);
    
    if (isVideo) {
      // For video compliance check
      formData.append("message", `Analyze this video for ${brandName} brand compliance, focusing on logo usage, colors, and tone of voice. This is specifically an ad for the ${brandName} brand as specified by the user.`);
      formData.append("analysis_modes", JSON.stringify(["visual"]));
      formData.append("brand_name", brandName);
      
      // Create fetch request for video
      const controller = new AbortController();
      const { signal } = controller;
      
      const response = await fetch(`${API_BASE_URL}/api/compliance/check-video`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
        signal,
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }
      
      // Set up event stream processing
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Response body is not readable");
      }
      
      // Process the stream
      let buffer = "";
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          // Process any remaining data in the buffer
          if (buffer.trim()) {
            processEventData(buffer, (event) => onEvent(file.name, event));
          }
          break;
        }
        
        // Convert the chunk to text and add to buffer
        const chunk = new TextDecoder().decode(value);
        buffer += chunk;
        
        // Process complete events in the buffer
        const events = extractEvents(buffer);
        if (events.length > 0) {
          // Update the buffer to contain only the remaining partial data
          const lastNewlineIndex = buffer.lastIndexOf("\n");
          if (lastNewlineIndex !== -1) {
            buffer = buffer.substring(lastNewlineIndex + 1);
          }
          
          // Process each complete event
          for (const eventData of events) {
            processEventData(eventData, (event) => onEvent(file.name, event));
          }
        }
      }
    } else {
      // For image compliance check
      formData.append("text", `Analyze this image for ${brandName} brand compliance, focusing on logo usage, colors, and brand elements.`);
      
      // Create fetch request for image
      const controller = new AbortController();
      const { signal } = controller;
      
      const response = await fetch(`${API_BASE_URL}/api/compliance/check-image`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
        signal,
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }
      
      // Set up event stream processing
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Response body is not readable");
      }
      
      // Process the stream
      let buffer = "";
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          // Process any remaining data in the buffer
          if (buffer.trim()) {
            processEventData(buffer, (event) => onEvent(file.name, event));
          }
          break;
        }
        
        // Convert the chunk to text and add to buffer
        const chunk = new TextDecoder().decode(value);
        buffer += chunk;
        
        // Process complete events in the buffer
        const events = extractEvents(buffer);
        if (events.length > 0) {
          // Update the buffer to contain only the remaining partial data
          const lastNewlineIndex = buffer.lastIndexOf("\n");
          if (lastNewlineIndex !== -1) {
            buffer = buffer.substring(lastNewlineIndex + 1);
          }
          
          // Process each complete event
          for (const eventData of events) {
            processEventData(eventData, (event) => onEvent(file.name, event));
          }
        }
      }
    }
  } catch (error) {
    console.error(`Error processing ${isVideo ? 'video' : 'image'} for compliance:`, error);
    throw error;
  }
};

/**
 * Process multiple media items for compliance in parallel
 * @param mediaItems Array of media items to process
 * @param token Authentication token
 * @param onItemEvent Callback for events on individual items
 * @param concurrency Maximum number of concurrent requests
 * @returns Promise that resolves when all items have been processed
 */
export const processBatchMedia = async (
  mediaItems: Array<{file: File, isVideo: boolean, brandName: string, id: string}>,
  token: string,
  onItemEvent: (id: string, event: ComplianceEvent) => void,
  concurrency: number = 2 // Default to processing 2 items at a time
): Promise<void> => {
  // Create a queue of media items to process
  const queue = [...mediaItems];
  const activePromises: Promise<void>[] = [];
  
  // Process queue with limited concurrency
  const processQueue = async () => {
    while (queue.length > 0 || activePromises.length > 0) {
      // Fill up to concurrency limit
      while (queue.length > 0 && activePromises.length < concurrency) {
        const item = queue.shift();
        if (item) {
          const promise = processMediaItem(
            item.file,
            item.isVideo,
            item.brandName,
            token,
            (_, event) => onItemEvent(item.id, event)
          ).catch(error => {
            console.error(`Error processing ${item.id}:`, error);
            // Signal error to UI
            onItemEvent(item.id, {
              type: 'complete',
              content: JSON.stringify({
                result: `Error processing ${item.file.name}: ${error.message}`
              })
            });
          });
          
          activePromises.push(promise);
        }
      }
      
      // Wait for at least one promise to complete
      if (activePromises.length > 0) {
        await Promise.race(activePromises.map(p => p.then(() => {})));
        // Remove completed promises
        for (let i = activePromises.length - 1; i >= 0; i--) {
          const promise = activePromises[i];
          if (promise.hasOwnProperty('resolved')) {
            activePromises.splice(i, 1);
          }
        }
      }
    }
  };
  
  await processQueue();
};

// Helper function to extract complete events from a buffer
function extractEvents(buffer: string): string[] {
  // Split by newline and filter out empty lines
  return buffer.split('\n')
    .filter(line => line.trim())
    .slice(0, -1); // Exclude the last line which might be incomplete
}

// Helper function to process event data
function processEventData(
  eventData: string,
  onEvent: (event: ComplianceEvent) => void
): void {
  try {
    // Try to parse as JSON
    const parsedData = JSON.parse(eventData);
    
    // Check if it has the expected format
    if (
      parsedData &&
      typeof parsedData === 'object' &&
      'type' in parsedData &&
      'content' in parsedData
    ) {
      onEvent({
        type: parsedData.type,
        content: parsedData.content
      });
    }
  } catch (error) {
    // If it's not valid JSON, treat as a text event
    if (eventData.trim()) {
      onEvent({
        type: 'text',
        content: eventData
      });
    }
  }
}
