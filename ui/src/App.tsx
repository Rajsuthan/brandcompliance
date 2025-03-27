import { useState, useEffect, useRef } from "react";
import { FileUpload } from "@/components/ui/file-upload";
import { Button } from "@/components/ui/button";
import "@/animations.css";
import { login, checkImageCompliance } from "@/services/complianceService";
import ReactMarkdown from "react-markdown";

interface ComplianceEvent {
  type: "thinking" | "text" | "tool" | "complete";
  content: string;
}

interface Step {
  id: string;
  type: "text" | "tool";
  content: string;
  taskDetail?: string;
}

export default function App() {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);
  const [finalResult, setFinalResult] = useState<string | null>(null);
  const [stepsCollapsed, setStepsCollapsed] = useState(false);
  const [allowAutoCollapse, setAllowAutoCollapse] = useState(true);
  const stepsEndRef = useRef<HTMLDivElement>(null);
  const finalResultRef = useRef<HTMLDivElement>(null);

  // Login on component mount
  useEffect(() => {
    const performLogin = async () => {
      try {
        // Using test credentials from the test script
        const token = await login("testuser2", "testpassword123");
        setAuthToken(token);
        console.log("Login successful, token:", token);
      } catch (error) {
        console.error("Login failed:", error);
      }
    };

    performLogin();
  }, []);

  // Scroll to bottom when new steps are added
  useEffect(() => {
    if (steps.length > 0 && isProcessing) {
      stepsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [steps, isProcessing]);

  // Auto-collapse steps when final result is set
  useEffect(() => {
    if (finalResult) {
      // Always collapse steps when final result is ready
      setStepsCollapsed(true);

      // Scroll to the final result
      setTimeout(() => {
        finalResultRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 300);
    }
  }, [finalResult]);

  const handleFileSelect = (file: File) => {
    if (file.type.startsWith("image/")) {
      setSelectedImage(file);

      // Create preview
      const reader = new FileReader();
      reader.onload = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);

      // Clear previous results
      setSteps([]);
      setFinalResult(null);
      setStepsCollapsed(false);
      setAllowAutoCollapse(true);
    }
  };

  // Helper function to try parsing JSON
  const tryParseJSON = (text: string) => {
    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  };

  // Helper function to extract task detail from tool content
  const extractTaskDetail = (content: string): string | undefined => {
    const jsonData = tryParseJSON(content);
    if (jsonData && typeof jsonData === "object") {
      return jsonData.task_detail || jsonData.taskDetail || undefined;
    }
    return undefined;
  };

  const processImage = async () => {
    if (!selectedImage) {
      console.error("No image selected");
      return;
    }

    if (!authToken) {
      console.error("Not authenticated. Please log in first.");
      return;
    }

    setIsProcessing(true);
    setSteps([]);
    setFinalResult(null);
    setStepsCollapsed(false);
    setAllowAutoCollapse(true);

    try {
      console.log("Processing image:", selectedImage.name);

      // Add initial step
      setSteps([
        {
          id: Date.now().toString(),
          type: "text",
          content: `Starting compliance check for ${selectedImage.name}`,
        },
      ]);

      // Variables to track the current content and state
      let currentContent = "";
      let currentStepId: string | null = null;
      let lastEventType: "text" | "tool" | null = null;

      // Call the compliance API
      await checkImageCompliance(
        selectedImage,
        "YOU MUST ONLY CHECK THE `get_region_color_scheme` AND THE `check_color_contrast` TOOL",
        authToken,
        (event: ComplianceEvent) => {
          // Log the event to console
          console.log(`[${event.type}]`, event.content);

          // Only process text and tool events for steps
          if (event.type === "text" || event.type === "tool") {
            // If the event type has changed or we don't have a current step,
            // create a new step and reset the content
            if (event.type !== lastEventType || !currentStepId) {
              // If we have accumulated content, create a new step
              if (currentContent && currentStepId) {
                // We're switching to a new type, so finalize the current step
                // (This is already handled by the state updates below)
              }

              // Create a new step for the new type
              const newId = `${event.type}-${Date.now()}`;
              currentStepId = newId;
              currentContent = event.content;
              lastEventType = event.type;

              // Extract task detail for tool events
              const taskDetail =
                event.type === "tool"
                  ? extractTaskDetail(event.content)
                  : undefined;

              // Add the new step (ensuring type is only 'text' or 'tool')
              setSteps((prev) => [
                ...prev,
                {
                  id: newId,
                  type: event.type as "text" | "tool", // This cast is safe because we check above
                  content: event.content,
                  taskDetail,
                },
              ]);
            } else {
              // Same event type as before, accumulate content
              currentContent += event.content;

              // Extract task detail for tool events
              const taskDetail =
                event.type === "tool"
                  ? extractTaskDetail(currentContent)
                  : undefined;

              // Update the current step
              setSteps((prev) =>
                prev.map((step) =>
                  step.id === currentStepId
                    ? {
                        ...step,
                        content: currentContent,
                        ...(event.type === "tool" ? { taskDetail } : {}),
                      }
                    : step
                )
              );
            }
          } else if (event.type === "complete") {
            // Find the last text step that doesn't have a tool step after it
            setTimeout(() => {
              const textSteps = steps.filter((s) => s.type === "text");
              if (textSteps.length > 0) {
                const lastTextStep = textSteps[textSteps.length - 1];
                setFinalResult(lastTextStep.content);
              } else {
                setFinalResult(event.content);
              }
              setIsProcessing(false);
            }, 500);
          }
        }
      );
    } catch (error) {
      console.error("Error processing image for compliance:", error);
      setSteps((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: "text",
          content: `Error: ${error}`,
        },
      ]);
      setIsProcessing(false);
    }
  };

  // Function to toggle steps collapse state
  const toggleStepsCollapse = () => {
    // When user manually toggles, disable auto-collapse
    setAllowAutoCollapse(false);
    setStepsCollapsed(!stepsCollapsed);
  };

  // Custom components for markdown rendering
  const MarkdownComponents = {
    h1: ({ node, ...props }: any) => (
      <h1 className="text-2xl font-semibold mt-6 mb-4 text-white" {...props} />
    ),
    h2: ({ node, ...props }: any) => (
      <h2 className="text-xl font-semibold mt-5 mb-3 text-white" {...props} />
    ),
    h3: ({ node, ...props }: any) => (
      <h3 className="text-lg font-medium mt-4 mb-2 text-white" {...props} />
    ),
    h4: ({ node, ...props }: any) => (
      <h4 className="text-base font-medium mt-3 mb-2 text-white" {...props} />
    ),
    p: ({ node, ...props }: any) => (
      <p className="text-sm leading-relaxed my-3 text-zinc-300" {...props} />
    ),
    ul: ({ node, ...props }: any) => (
      <ul className="list-disc pl-6 my-3 text-zinc-300" {...props} />
    ),
    ol: ({ node, ...props }: any) => (
      <ol className="list-decimal pl-6 my-3 text-zinc-300" {...props} />
    ),
    li: ({ node, ...props }: any) => (
      <li className="text-sm my-1 leading-relaxed" {...props} />
    ),
    blockquote: ({ node, ...props }: any) => (
      <blockquote
        className="border-l-2 border-zinc-700 pl-4 my-3 italic text-zinc-400"
        {...props}
      />
    ),
    code: ({ node, inline, ...props }: any) =>
      inline ? (
        <code
          className="bg-zinc-800 px-1 py-0.5 rounded text-xs font-mono text-zinc-300"
          {...props}
        />
      ) : (
        <code
          className="block bg-zinc-800 p-3 rounded-md my-3 overflow-x-auto text-xs font-mono text-zinc-300"
          {...props}
        />
      ),
    a: ({ node, ...props }: any) => (
      <a
        className="text-white underline hover:text-zinc-300 transition-colors"
        {...props}
      />
    ),
    strong: ({ node, ...props }: any) => (
      <strong className="font-semibold text-white" {...props} />
    ),
    em: ({ node, ...props }: any) => (
      <em className="italic text-zinc-300" {...props} />
    ),
    hr: ({ node, ...props }: any) => (
      <hr className="my-4 border-zinc-800" {...props} />
    ),
  };

  return (
    <div className="flex flex-col min-h-svh bg-zinc-950 text-white antialiased">
      {/* Header bar */}
      <header className="border-b border-zinc-800 py-3 px-4 sticky top-0 z-10 bg-zinc-950 backdrop-blur-sm bg-opacity-90">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center shadow-md shadow-indigo-900/30">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-3 w-3 text-white"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <p className="text-lg font-medium">Brand Compliance</p>
          </div>
          {steps.length > 0 && (
            <button
              onClick={toggleStepsCollapse}
              className="text-xs text-zinc-300 flex items-center gap-1.5 px-2 py-1 rounded-md border border-zinc-700 hover:bg-zinc-800 transition-all hover:shadow-md duration-200"
            >
              <span>{steps.length} steps</span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className={`h-3 w-3 transition-transform duration-200 ${
                  stepsCollapsed ? "rotate-180" : ""
                }`}
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          )}
        </div>
      </header>

      <main className="flex-1 max-w-2xl w-full mx-auto px-4 py-6">
        {/* Initial upload view - shown when no image is selected or no results yet */}
        {(!imagePreview || (steps.length === 0 && !finalResult)) && (
          <div className="flex flex-col items-center justify-center h-full max-w-md mx-auto py-10 space-y-8 animate-in enhanced-fade-in duration-500">
            <div className="text-center space-y-2">
              <h2 className="text-xl font-semibold bg-gradient-to-r from-white to-indigo-300 bg-clip-text text-transparent">
                Brand Compliance Checker
              </h2>
              <p className="text-sm text-zinc-400">
                Upload an image to check brand compliance
              </p>
            </div>

            <FileUpload
              onFileSelect={handleFileSelect}
              maxSize={10}
              acceptedFileTypes={[
                "image/jpeg",
                "image/png",
                "image/gif",
                "image/webp",
              ]}
              multiple={false}
              className="w-full"
            />

            {imagePreview && (
              <div className="border border-zinc-700 rounded-lg overflow-hidden w-full shadow-lg shadow-black/20 hover-lift">
                <img
                  src={imagePreview}
                  alt="Selected"
                  className="w-full h-auto"
                />
                <div className="p-3 bg-zinc-800 flex justify-between items-center">
                  <div>
                    <p className="text-sm font-medium truncate max-w-[200px] text-white">
                      {selectedImage?.name}
                    </p>
                    <p className="text-xs text-zinc-400">
                      {selectedImage &&
                        (selectedImage.size / (1024 * 1024)).toFixed(2)}{" "}
                      MB
                    </p>
                  </div>
                  <Button
                    onClick={() => {
                      setSelectedImage(null);
                      setImagePreview(null);
                    }}
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 rounded-full hover:bg-zinc-700 transition-all duration-200"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-3.5 w-3.5"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </Button>
                </div>
              </div>
            )}

            <Button
              onClick={processImage}
              disabled={!selectedImage || isProcessing || !authToken}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white transition-all duration-200 disabled:opacity-50 disabled:pointer-events-none shadow-lg shadow-indigo-900/30 hover:shadow-xl hover:shadow-indigo-900/40 hover:translate-y-[-1px] press-effect"
            >
              {isProcessing ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin mr-2 h-4 w-4"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Processing...
                </span>
              ) : (
                "Check Compliance"
              )}
            </Button>
          </div>
        )}

        {/* Results view - shown when there are results */}
        {(steps.length > 0 || finalResult) && (
          <div className="flex flex-col space-y-4 animate-in enhanced-fade-in duration-400">
            {/* Image attachment */}
            {imagePreview && (
              <div className="flex items-start gap-3 p-4 border border-zinc-700 rounded-lg bg-zinc-800/50 mb-2 shadow-md animate-in smooth-slide-up duration-400">
                <div className="w-12 h-12 rounded-md overflow-hidden flex-shrink-0 border border-zinc-700 shadow-md">
                  <img
                    src={imagePreview}
                    alt="Selected"
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="flex-1 min-w-0 flex flex-col">
                  <h2 className="text-sm font-medium truncate text-white">
                    {selectedImage?.name}
                  </h2>
                  <p className="text-xs text-zinc-400 mb-1">
                    {selectedImage &&
                      (selectedImage.size / (1024 * 1024)).toFixed(2)}{" "}
                    MB
                  </p>
                  <div className="flex items-center">
                    {isProcessing ? (
                      <span className="inline-flex items-center text-xs text-zinc-300">
                        <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full mr-1.5 animate-subtle-pulse"></span>
                        Processing...
                      </span>
                    ) : (
                      <span className="inline-flex items-center text-xs text-zinc-300">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1.5 animate-glow"></span>
                        Analysis complete
                      </span>
                    )}
                  </div>
                </div>
                {!isProcessing && (
                  <Button
                    onClick={() => {
                      setSteps([]);
                      setFinalResult(null);
                      setSelectedImage(null);
                      setImagePreview(null);
                    }}
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs border-zinc-700 hover:bg-zinc-700 text-white transition-all duration-200 hover:shadow-md press-effect"
                  >
                    New Analysis
                  </Button>
                )}
              </div>
            )}

            {/* Steps section - collapsible */}
            {steps.length > 0 && (
              <div className="mb-1 mt-6">
                <button
                  onClick={toggleStepsCollapse}
                  className="w-full flex items-center justify-between p-3 border border-zinc-700 rounded-lg bg-zinc-800/70 mb-4 hover:bg-zinc-800 transition-all duration-200 shadow-md hover-lift"
                >
                  <span className="text-sm font-medium text-white">
                    Processing Steps ({steps.length})
                  </span>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className={`h-4 w-4 text-zinc-400 transition-transform duration-200 ${
                      stepsCollapsed ? "rotate-180" : ""
                    }`}
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>

                {/* Steps list with timeline */}
                {!stepsCollapsed && (
                  <div id="steps-container" className="relative">
                    {/* Vertical timeline line */}
                    <div className="absolute left-[9px] top-0 bottom-0 w-[1px] bg-zinc-700"></div>

                    <div className="space-y-3">
                      {steps.map((step, index) => (
                        <div
                          key={step.id}
                          className="animate-in smooth-slide-up duration-400"
                          style={{ animationDelay: `${index * 80}ms` }}
                        >
                          <div className="flex items-start gap-3 group relative">
                            {/* Step indicator dot */}
                            <div className="relative z-10">
                              <div
                                className={`w-5 h-5 rounded-full flex items-center justify-center transition-all duration-300 bg-zinc-800 text-lg shadow-md ${
                                  index === steps.length - 1 && !isProcessing
                                    ? "animate-subtle-bounce !bg-green-700 !text-white"
                                    : ""
                                } ${step.taskDetail && "mt-5"}`}
                              >
                                {index === steps.length - 1 && isProcessing ? (
                                  <svg
                                    className="animate-spin h-3 w-3 text-white"
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                  >
                                    <circle
                                      className="opacity-25"
                                      cx="12"
                                      cy="12"
                                      r="10"
                                      stroke="currentColor"
                                      strokeWidth="4"
                                    ></circle>
                                    <path
                                      className="opacity-75"
                                      fill="currentColor"
                                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                    ></path>
                                  </svg>
                                ) : index < steps.length - 1 ||
                                  !isProcessing ? (
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    className="h-3 w-3 text-white animate-in fade-in duration-300"
                                    viewBox="0 0 20 20"
                                    fill="currentColor"
                                  >
                                    <path
                                      fillRule="evenodd"
                                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                      clipRule="evenodd"
                                    />
                                  </svg>
                                ) : step.type === "text" ? (
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    className="h-3 w-3 text-white"
                                    viewBox="0 0 20 20"
                                    fill="currentColor"
                                  >
                                    <path
                                      fillRule="evenodd"
                                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                                      clipRule="evenodd"
                                    />
                                  </svg>
                                ) : (
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    className="h-3 w-3 text-white"
                                    viewBox="0 0 20 20"
                                    fill="currentColor"
                                  >
                                    <path
                                      fillRule="evenodd"
                                      d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                                      clipRule="evenodd"
                                    />
                                  </svg>
                                )}
                              </div>
                            </div>

                            {/* Content card with hover effects */}
                            <div
                              className={`flex-1 min-w-0 p-3.5 rounded-lg bg-zinc-700/20 border border-zinc-700 hover:border-zinc-600 group-hover:bg-zinc-800 mb-1 shadow-md transition-all duration-200 hover-lift ${
                                index === steps.length - 1 && isProcessing
                                  ? "border-l-2 border-l-indigo-500"
                                  : ""
                              } ${
                                step.taskDetail
                                  ? "!bg-transparent !border-none"
                                  : ""
                              }`}
                            >
                              {!step.taskDetail && (
                                <div className="flex items-center justify-between mb-1">
                                  <div className="text-xs font-medium text-white">
                                    {step.type === "text"
                                      ? "Analysis"
                                      : step.taskDetail
                                      ? "Research"
                                      : "Tool"}
                                  </div>
                                  <div className="text-xs text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity">
                                    Step {index + 1}
                                  </div>
                                </div>
                              )}
                              <div
                                className={` text-zinc-200 whitespace-pre-wrap break-words animate-in fade-in duration-300 ${
                                  step.taskDetail
                                    ? "font-semibold text-md"
                                    : "text-sm"
                                }`}
                              >
                                {step.type === "text"
                                  ? step.content
                                  : step.taskDetail
                                  ? `${step.taskDetail}...`
                                  : "Processing..."}
                              </div>
                              {step.content.length > 300 &&
                                step.type === "text" && (
                                  <button
                                    className="text-xs mt-2 px-2 py-0.5 rounded bg-zinc-700 text-zinc-300 hover:text-white transition-colors press-effect"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      console.log(
                                        "Full content:",
                                        step.content
                                      );
                                      alert("Full content logged to console");
                                    }}
                                  >
                                    Show full content
                                  </button>
                                )}
                            </div>
                          </div>
                        </div>
                      ))}

                      {/* Loading indicator for active processing */}
                      {isProcessing && (
                        <div className="pl-8 py-2 text-xs text-zinc-300 flex items-center gap-2">
                          <div className="w-1 h-1 bg-indigo-500 rounded-full animate-subtle-pulse"></div>
                          <div
                            className="w-1 h-1 bg-indigo-500 rounded-full animate-subtle-pulse"
                            style={{ animationDelay: "300ms" }}
                          ></div>
                          <div
                            className="w-1 h-1 bg-indigo-500 rounded-full animate-subtle-pulse"
                            style={{ animationDelay: "600ms" }}
                          ></div>
                        </div>
                      )}

                      {/* Reference for scrolling to bottom */}
                      <div ref={stepsEndRef} />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Final Result Section */}
            {finalResult && (
              <div
                ref={finalResultRef}
                className="rounded-md animate-in enhanced-fade-in smooth-slide-up duration-700 mt-8 pb-24"
              >
                <h3 className="text-xl font-semibold mb-4 flex items-center gap-2 pb-3 border-b border-zinc-800">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-glow"></span>
                  Final Analysis
                </h3>
                <div className="prose prose-invert max-w-none pre-line">
                  <ReactMarkdown components={MarkdownComponents}>
                    {JSON.parse(steps[steps.length - 1].content).result}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
