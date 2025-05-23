import { useState, useEffect, useRef } from "react";
import { FeedbackForm } from "@/components/ui/feedback-form";
import { ProcessingToast } from "@/components/ui/processing-toast";
import { useAuth } from "@/lib/auth-context";
import "@/animations.css";
import {
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
  // Use Firebase authentication
  const { user, getIdToken } = useAuth();
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

  // Get Firebase ID token when user is authenticated
  useEffect(() => {
    const getToken = async () => {
      if (user) {
        try {
          const token = await getIdToken();
          setAuthToken(token);
          console.log("Firebase token obtained");
        } catch (error) {
          console.error("Failed to get Firebase token:", error);
        }
      } else {
        setAuthToken(null);
      }
    };

    getToken();
  }, [user, getIdToken]);

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
            `Conduct a comprehensive brand compliance analysis for this ${item.brandName} video. Follow these specific steps:
1. Research ${item.brandName}'s official brand guidelines thoroughly, focusing on visual identity (logo, colors, typography, imagery), verbal identity (tone, messaging, terminology), and usage rules.
2. Analyze each frame methodically for visual compliance issues, including logo placement, color accuracy, typography, and overall visual presentation.
3. Evaluate verbal content for brand voice compliance, including terminology, messaging consistency, and tone alignment.
4. Document specific timestamps where compliance issues occur, with precise references to the relevant guideline sections.
5. Provide a detailed compliance score with factual justification based solely on objective guideline violations.
6. Include actionable recommendations for each identified issue with specific corrections.

Your analysis must be extremely detailed, fact-based, and reference specific sections of ${item.brandName}'s guidelines. Avoid generalizations or assumptions. Use all available tools to extract and analyze every aspect of the video.`,
            authToken,
            (event) => handleItemComplianceEvent(item.id, event),
            ["visual", "brand_voice", "tone"],
            item.brandName
          );
        } else {
          await checkImageCompliance(
            item.file,
            `Conduct a comprehensive brand compliance analysis for this ${item.brandName} image. Follow these specific steps:
1. Research ${item.brandName}'s official brand guidelines thoroughly, focusing on visual identity (logo, colors, typography, imagery), verbal identity (tone, messaging, terminology), and usage rules.
2. Analyze the image methodically for visual compliance issues, examining:
   - Logo: placement, size, clear space, color version, and any distortions
   - Colors: exact color values (RGB/HEX/CMYK), gradient usage, and background compatibility
   - Typography: font families, weights, sizes, and text formatting
   - Imagery: style, quality, composition, and subject matter
   - Layout: spacing, alignment, and overall composition
3. Evaluate any text content for brand voice compliance, including terminology, messaging consistency, and tone alignment.
4. Document specific areas of the image where compliance issues occur, with precise references to the relevant guideline sections.
5. Provide a detailed compliance score with factual justification based solely on objective guideline violations.
6. Include actionable recommendations for each identified issue with specific corrections.

Your analysis must be extremely detailed, fact-based, and reference specific sections of ${item.brandName}'s guidelines. Avoid generalizations or assumptions. Use all available tools to extract and analyze every aspect of the image.`,
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
      console.log("Received complete event:", event.content.substring(0, 100) + "...");
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
                (parsed.tool_name === "attempt_completion" ||
                  parsed.toolName === "attempt_completion") &&
                parsed.result
              ) {
                finalResult =
                  typeof parsed.result === "string"
                    ? parsed.result
                    : JSON.stringify(parsed.result, null, 2);
                break;
              }
            } catch (e) {
              console.error("Error parsing tool step:", e);
              // Ignore parse errors
            }
          }
        }

        // 2. If not found, try to parse the complete event content
        if (!finalResult) {
          try {
            const jsonResult = JSON.parse(event.content);

            // Check for tool_result.detailed_report structure (from logs)
            if (jsonResult && jsonResult.tool_result && jsonResult.tool_result.detailed_report) {
              console.log("Found detailed_report in complete event");
              finalResult = jsonResult.tool_result.detailed_report;
            }
            // Check for result property
            else if (jsonResult && jsonResult.result) {
              finalResult =
                typeof jsonResult.result === "string"
                  ? jsonResult.result
                  : JSON.stringify(jsonResult.result, null, 2);
            }
            // Check for tool_result property
            else if (jsonResult && jsonResult.tool_result) {
              finalResult =
                typeof jsonResult.tool_result === "string"
                  ? jsonResult.tool_result
                  : JSON.stringify(jsonResult.tool_result, null, 2);
            }
            // Fallback to raw content
            else {
              finalResult = event.content;
            }
          } catch (e) {
            console.error("Error parsing complete event:", e);
            // Not valid JSON, just use the raw content
            finalResult = event.content;
          }
        }

        console.log("Final result set:", finalResult ? finalResult.substring(0, 100) + "..." : "null");

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
          return (
            jsonData.tool_input.task_detail ||
            jsonData.tool_input.taskDetail ||
            undefined
          );
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
