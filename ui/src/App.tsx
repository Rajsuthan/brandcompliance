import { useState, useEffect, useRef } from "react";
// Removed unused Button import
import { UploadGuidelinesModal } from "@/components/ui/upload-guidelines-modal";
import { FeedbackForm } from "@/components/ui/feedback-form";
import { ProcessingToast } from "@/components/ui/processing-toast";
import "@/animations.css";
import {
  login,
  checkImageCompliance,
  checkVideoCompliance,
} from "@/services/complianceService";

// Import modular components
import {
  MultiFileUpload,
  MediaFile,
  ProcessingResultGrid,
  ProcessingItem,
  ProcessingStep,
} from "@/components/compliance";

interface ComplianceEvent {
  type: "thinking" | "text" | "tool" | "complete";
  content: string;
}

export default function App() {
  // Authentication state
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [stepsCollapsed, setStepsCollapsed] = useState(false);

  // Processing results state
  const [processingItems, setProcessingItems] = useState<ProcessingItem[]>([]);
  const [currentProcessingIndex, setCurrentProcessingIndex] =
    useState<number>(-1);
  const [showProcessingToast, setShowProcessingToast] = useState(false);

  // References
  const timersRef = useRef<{ [key: string]: NodeJS.Timeout | null }>({});

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      // Clear all timers when component unmounts
      Object.values(timersRef.current).forEach((timer) => {
        if (timer) clearInterval(timer);
      });
    };
  }, []);

  // Login on component mount
  useEffect(() => {
    const performLogin = async () => {
      try {
        // Using test credentials from the test script
        const token = await login("testuser2", "testpassword123");
        setAuthToken(token);
        console.log("Login successful");
      } catch (error) {
        console.error("Login failed:", error);
      }
    };

    performLogin();
  }, []);

  // Helper function to format elapsed time
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  // Helper function to toggle steps collapse
  const toggleStepsCollapse = () => {
    setStepsCollapsed((prev) => !prev);
  };

  // Process multiple files
  const handleStartProcessing = async (mediaFiles: MediaFile[]) => {
    if (!authToken) {
      console.error("Not authenticated");
      return;
    }

    setIsProcessing(true);
    setCurrentProcessingIndex(0); // Start with the first file
    setShowProcessingToast(true); // Show the processing toast

    // Create processing items from media files
    const newProcessingItems = mediaFiles.map((file) => {
      // Create a unique ID if one doesn't exist
      const id =
        file.id ||
        `file-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      return {
        ...file,
        id,
        isProcessing: true,
        steps: [
          {
            id: `init-${id}`,
            type: "text",
            content: `Starting compliance check for ${file.file.name}`,
          },
        ],
        finalResult: null,
        elapsedTime: 0,
      } as ProcessingItem;
    });

    // Update state with new processing items
    setProcessingItems(newProcessingItems);

    // Process each file sequentially
    for (let i = 0; i < newProcessingItems.length; i++) {
      const item = newProcessingItems[i];
      setCurrentProcessingIndex(i); // Update the current processing index
      try {
        // Start a timer for this item
        startItemTimer(item.id);

        if (item.isVideo) {
          await checkVideoCompliance(
            item.file,
            false,
            `Analyze this video for ${item.brandName} brand compliance.`,
            authToken,
            (event) => handleItemComplianceEvent(item.id, event),
            ["visual"],
            item.brandName
          );
        } else {
          await checkImageCompliance(
            item.file,
            `Analyze this image for ${item.brandName} brand compliance.`,
            authToken,
            (event) => handleItemComplianceEvent(item.id, event)
          );
        }
      } catch (error) {
        console.error(`Error processing ${item.file.name}:`, error);

        // Update the item with error state
        updateProcessingItem(item.id, (currentItem) => ({
          ...currentItem,
          isProcessing: false,
          steps: [
            ...currentItem.steps,
            {
              id: `error-${Date.now()}`,
              type: "text",
              content: `Error: ${error}`,
            },
          ],
        }));

        // Stop the timer for this item
        stopItemTimer(item.id);
      }
    }

    setCurrentProcessingIndex(-1); // Reset when done
    setIsProcessing(false);
  };

  // Handle compliance events for a specific item
  const handleItemComplianceEvent = (
    itemId: string,
    event: ComplianceEvent
  ) => {
    if (event.type === "thinking") return; // Ignore thinking steps

    if (event.type === "text" || event.type === "tool") {
      updateProcessingItem(itemId, (currentItem) => {
        const newSteps = [...currentItem.steps]; // Create a mutable copy
        const lastStep =
          newSteps.length > 0 ? newSteps[newSteps.length - 1] : null;

        // Try to extract task detail from tool content
        const taskDetail =
          event.type === "tool" ? extractTaskDetail(event.content) : undefined;

        if (event.type === "text") {
          // Filter out XML tool call responses (full or partial)
          const isXml =
            typeof event.content === "string" &&
            event.content.trim().startsWith("<") &&
            event.content.trim().includes(">");

          if (isXml) {
            // Do not append XML tool call responses to the UI
            return { ...currentItem, steps: newSteps };
          }

          // Group consecutive text events into one step, avoid duplicate appends
          if (lastStep && lastStep.type === "text") {
            // Only append if not already present at the end
            if (!lastStep.content.endsWith(event.content)) {
              lastStep.content += event.content;
            }
          } else {
            const newStep: ProcessingStep = {
              id: `${itemId}-${Date.now()}-${Math.random()
                .toString(36)
                .substring(2, 5)}`,
              type: "text",
              content: event.content,
            };
            newSteps.push(newStep);
          }
        } else if (event.type === "tool") {
          // Always create a new step for tool events
          const newStep: ProcessingStep = {
            id: `${itemId}-${Date.now()}-${Math.random()
              .toString(36)
              .substring(2, 5)}`,
            type: "tool",
            content: event.content,
          };
          if (taskDetail) {
            newStep.taskDetail = taskDetail;
          }
          newSteps.push(newStep);
        }

        return {
          ...currentItem,
          steps: newSteps,
        };
      });
    } else if (event.type === "complete") {
      updateProcessingItem(itemId, (currentItem) => {
        let finalResult = null;

        // 1. Prefer the last tool step with tool_name: "attempt_completion" and a result property
        for (let i = currentItem.steps.length - 1; i >= 0; i--) {
          const step = currentItem.steps[i];
          if (step.type === "tool") {
            try {
              const parsed = JSON.parse(step.content);
              if (
                parsed &&
                (parsed.tool_name === "attempt_completion" || parsed.toolName === "attempt_completion") &&
                parsed.result
              ) {
                finalResult =
                  typeof parsed.result === "string"
                    ? parsed.result
                    : JSON.stringify(parsed.result, null, 2);
                break;
              }
            } catch {
              // Ignore parse errors
            }
          }
        }

        // 2. If not found, fall back to the previous logic (parse event.content for result)
        if (!finalResult) {
          finalResult = event.content;
          try {
            const jsonResult = JSON.parse(event.content);
            if (jsonResult && jsonResult.result) {
              finalResult =
                typeof jsonResult.result === "string"
                  ? jsonResult.result
                  : JSON.stringify(jsonResult.result, null, 2);
            }
          } catch {
            // Not valid JSON, just use the raw content
          }
        }

        // Stop the timer for this item
        stopItemTimer(itemId);

        return {
          ...currentItem,
          isProcessing: false,
          finalResult, // Store the determined final result text
        };
      });
    }
  };

  // Helper function to extract task detail from tool content
  const extractTaskDetail = (content: string): string | undefined => {
    try {
      const jsonData = JSON.parse(content);
      if (jsonData && typeof jsonData === "object") {
        // Check for task_detail/taskDetail at the top level
        if (jsonData.task_detail || jsonData.taskDetail) {
          return jsonData.task_detail || jsonData.taskDetail;
        }
        // Check for tool_input.task_detail/taskDetail
        if (jsonData.tool_input && typeof jsonData.tool_input === "object") {
          return jsonData.tool_input.task_detail || jsonData.tool_input.taskDetail || undefined;
        }
      }
    } catch {
      // Removed empty catch block
    }
    return undefined;
  };

  // Start a timer for tracking elapsed time for an item
  const startItemTimer = (itemId: string) => {
    const timer = setInterval(() => {
      updateProcessingItem(itemId, (item) => ({
        ...item,
        elapsedTime: item.elapsedTime + 1,
      }));
    }, 1000);

    timersRef.current[itemId] = timer;
  };

  // Stop a timer for an item
  const stopItemTimer = (itemId: string) => {
    const timer = timersRef.current[itemId];
    if (timer) {
      clearInterval(timer);
      timersRef.current[itemId] = null;
    }
  };

  // Helper function to update a specific processing item
  const updateProcessingItem = (
    itemId: string,
    updateFn: (item: ProcessingItem) => ProcessingItem
  ) => {
    setProcessingItems((prevItems) => {
      const index = prevItems.findIndex((item) => item.id === itemId);
      if (index === -1) return prevItems;

      const updatedItems = [...prevItems];
      updatedItems[index] = updateFn(prevItems[index]);
      return updatedItems;
    });
  };

  // Start a new analysis (reset state)
  const handleNewAnalysis = () => {
    // Clear all timers
    Object.values(timersRef.current).forEach((timer) => {
      if (timer) clearInterval(timer);
    });
    timersRef.current = {};

    // Reset state
    setProcessingItems([]);
    setIsProcessing(false);
  };

  return (
    <div className="flex flex-col min-h-svh bg-zinc-950 text-white antialiased">
      <header className="border-b border-zinc-800 py-3 px-4 sticky top-0 z-10 bg-zinc-950 backdrop-blur-sm bg-opacity-90">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="size-6 bg-indigo-500 rounded-md flex items-center justify-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4 text-white"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <p className="text-lg font-semibold text-white">
                Brand Compliance
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Pass authToken if required by the component */}
            <UploadGuidelinesModal authToken={authToken} />
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-2xl w-full mx-auto px-4 py-6">
        {/* Upload Section - shown when no processing is happening */}
        {processingItems.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full max-w-md mx-auto py-10 space-y-8 animate-in enhanced-fade-in duration-500">
            <div className="text-center space-y-2">
              <h2 className="text-xl font-semibold bg-gradient-to-r from-white to-indigo-300 bg-clip-text text-transparent">
                Brand Compliance Checker
              </h2>
              <p className="text-sm text-zinc-400 max-w-md">
                Upload images or videos to check them against brand compliance
                guidelines.
              </p>
            </div>

            {/* MultiFileUpload component */}
            <MultiFileUpload
              onStartProcessing={handleStartProcessing}
              isProcessing={isProcessing}
            />
          </div>
        )}

        {/* Results Section - shown when there are processing items */}
        {processingItems.length > 0 && (
          <ProcessingResultGrid
            items={processingItems}
            stepsCollapsed={stepsCollapsed}
            onToggleStepsCollapse={toggleStepsCollapse}
            onNewAnalysis={handleNewAnalysis}
            formatTime={formatTime}
            currentProcessingIndex={currentProcessingIndex}
          />
        )}

        {/* Feedback form at the bottom */}
        {processingItems.some(
          (item) => !item.isProcessing && item.finalResult
        ) && (
            <div className="mt-12 pt-6 border-t border-zinc-800">
              {/* Pass authToken if required by the component */}
              <FeedbackForm authToken={authToken} />
            </div>
          )}
      </main>

      {/* Processing Toast */}
      <ProcessingToast
        isVisible={showProcessingToast}
        fileCount={processingItems.length}
        onClose={() => setShowProcessingToast(false)}
      />
    </div>
  );
}
