import React, { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";

export interface ProcessingStep {
  id: string;
  type: "text" | "tool";
  content: string;
  taskDetail?: string;
}

export interface ProcessingItem extends MediaFile {
  isProcessing: boolean;
  steps: ProcessingStep[];
  finalResult: string | null;
  elapsedTime: number;
}

interface ProcessingResultGridProps {
  items: ProcessingItem[];
  stepsCollapsed: boolean;
  onToggleStepsCollapse: () => void;
  onNewAnalysis: () => void;
  formatTime: (seconds: number) => string;
  currentProcessingIndex: number; // Index of the file currently being processed
  analysisSectionsData?: Record<string, Record<string, {
    id: string;
    title: string;
    content: string;
    isComplete: boolean;
  }>>;
  onAnalysisSection?: (itemIndex: number, sectionId: string, sectionTitle: string, content: string, isComplete: boolean) => void;
}

// Import MediaFile interface
import { MediaFile } from "./MediaGrid";

// Define the ref type
interface ProcessingResultGridRef {
  handleAnalysisSection: (
    itemIndex: number,
    sectionId: string,
    sectionTitle: string,
    content: string,
    isComplete: boolean
  ) => void;
}

// Use forwardRef to expose methods to parent components
export const ProcessingResultGrid = forwardRef<ProcessingResultGridRef, ProcessingResultGridProps>(({
  items,
  stepsCollapsed,
  onToggleStepsCollapse,
  onNewAnalysis,
  formatTime,
  currentProcessingIndex,
  onAnalysisSection,
}, ref) => {
  // Add state to track the current item index being viewed
  const [currentIndex, setCurrentIndex] = useState(0);
  
  // We'll extract analysis sections directly from the steps
  // No need for additional state management

  // When the currentProcessingIndex changes, automatically view that item
  useEffect(() => {
    if (currentProcessingIndex >= 0 && currentProcessingIndex < items.length) {
      setCurrentIndex(currentProcessingIndex);
    }
  }, [currentProcessingIndex, items.length]);

  // Navigation handlers
  const handlePrevious = () => {
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => Math.min(items.length - 1, prev + 1));
  };
  
  // Method to handle analysis section events
  const handleAnalysisSection = (itemIndex: number, sectionId: string, sectionTitle: string, content: string, isComplete: boolean) => {
    console.log(`Received analysis section: ${sectionId} for item ${itemIndex}, isComplete: ${isComplete}`);
    
    // We're now extracting sections directly from steps, so we just need to make sure
    // the step data contains the section information we need
    
    // Add a step for this section to the item
    const currentItem = items[itemIndex];
    if (currentItem && sectionId && content && content.trim()) {
      // Create a tool step with the section data in JSON format
      const stepData = {
        section_id: sectionId,
        section_title: sectionTitle,
        content: content,
        is_complete: isComplete
      };
      
      // The parent component will handle updating the steps
      console.log(`Prepared section data for ${sectionId}:`, stepData);
    }
    
    // Call the parent handler if provided
    if (onAnalysisSection) {
      onAnalysisSection(itemIndex, sectionId, sectionTitle, content, isComplete);
    }
  };
  
  // Expose methods to parent component via ref
  useImperativeHandle(ref, () => ({
    handleAnalysisSection
  }));

  // Custom components for markdown rendering
  const MarkdownComponents = {
    h1: (props: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h1 className="text-lg font-semibold mt-4 mb-3 text-white" {...props} />
    ),
    h2: (props: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h2 className="text-base font-semibold mt-3 mb-2 text-white" {...props} />
    ),
    h3: (props: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h3 className="text-sm font-medium mt-2 mb-1 text-white" {...props} />
    ),
    p: (props: React.HTMLAttributes<HTMLParagraphElement>) => (
      <p className="text-sm leading-relaxed my-2 text-zinc-300" {...props} />
    ),
    ul: (props: React.HTMLAttributes<HTMLUListElement>) => (
      <ul className="list-disc pl-4 my-2 text-zinc-300" {...props} />
    ),
    ol: (props: React.HTMLAttributes<HTMLOListElement>) => (
      <ol className="list-decimal pl-4 my-2 text-zinc-300" {...props} />
    ),
    li: (props: React.HTMLAttributes<HTMLLIElement>) => (
      <li className="text-sm my-1 leading-relaxed" {...props} />
    ),
    code: ({
      inline,
      ...props
    }: { inline?: boolean } & React.HTMLAttributes<HTMLElement>) =>
      inline ? (
        <code
          className="bg-zinc-800 px-1 py-0.5 rounded text-xs font-mono text-zinc-300"
          {...props}
        />
      ) : (
        <code
          className="block bg-zinc-800 p-2 rounded-md my-2 overflow-x-auto text-xs font-mono text-zinc-300"
          {...props}
        />
      ),
  };

  if (items.length === 0) {
    return null;
  }

  // Get the current item based on the currentIndex
  const currentItem = items[currentIndex];

  useEffect(() => {
    console.log(items)
    console.log(currentItem)
  }, [items]);

  return (
    <div className="flex flex-col space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Processing Results</h2>
        <Button
          onClick={onNewAnalysis}
          variant="outline"
          size="sm"
          className="h-8 text-xs border-zinc-700 hover:bg-zinc-700 text-white transition-all duration-200"
        >
          New Analysis
        </Button>
      </div>

      {/* File navigation tabs with sequential processing indicator */}
      <div className="flex items-center mb-4 gap-1.5 flex-wrap">
        {items.map((item, idx) => (
          <button
            key={idx}
            onClick={() => setCurrentIndex(idx)}
            className={`relative flex items-center h-8 px-3 rounded-full text-xs font-medium transition-all duration-200 ${idx === currentIndex
              ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/50"
              : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700/50"
              } ${idx === currentProcessingIndex && item.isProcessing
                ? "ring-2 ring-indigo-500/50 ring-offset-1 ring-offset-zinc-900"
                : ""
              }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full mr-1.5 ${item.isProcessing
                ? "bg-indigo-500 animate-pulse"
                : item.finalResult
                  ? "bg-green-500"
                  : idx < currentProcessingIndex
                    ? "bg-green-500" // Processed but no result (error?)
                    : "bg-zinc-500" // Not processed yet
                }`}
            ></span>
            <span className="flex items-center">
              {/* Show processing order number */}
              {idx < currentProcessingIndex ? (
                <span className="mr-1.5 text-green-500 text-xs flex items-center">
                  ✓
                </span>
              ) : idx === currentProcessingIndex ? (
                <span className="mr-1.5 bg-indigo-500/80 text-white w-4 h-4 rounded-full flex items-center justify-center text-[10px]">
                  {idx + 1}
                </span>
              ) : (
                <span className="mr-1.5 bg-zinc-700 text-zinc-400 w-4 h-4 rounded-full flex items-center justify-center text-[10px]">
                  {idx + 1}
                </span>
              )}

              {item.file.name.length > 15
                ? `${item.file.name.substring(0, 15)}...`
                : item.file.name}
            </span>
          </button>
        ))}
      </div>

      {/* Current file card - full width */}
      {items.length > 0 && (
        <div
          className={`flex flex-col w-full animate-in fade-in slide-in-from-bottom-4 duration-500 ${currentIndex === currentProcessingIndex &&
            items[currentIndex].isProcessing
            ? "border-2 border-indigo-500/30 rounded-lg"
            : ""
            }`}
        >
          {/* File header with details */}
          <div className="flex items-start p-4 border-b border-zinc-700 bg-zinc-800/70 rounded-t-lg">
            <div className="w-16 h-16 rounded-md overflow-hidden flex-shrink-0 border border-zinc-700 shadow-md mr-4">
              {currentItem.isVideo ? (
                <div className="w-full h-full bg-zinc-900 flex items-center justify-center">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-7 w-7 text-indigo-400"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
                  </svg>
                </div>
              ) : (
                <img
                  src={currentItem.preview}
                  alt="Thumbnail"
                  className="w-full h-full object-cover"
                />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-medium text-white">
                {currentItem.file.name}
              </h3>
              <div className="flex flex-col text-sm mt-1">
                <span className="text-zinc-400">
                  {(currentItem.file.size / (1024 * 1024)).toFixed(2)} MB
                </span>
                <span className="text-zinc-300 mt-1">
                  Brand:{" "}
                  <span className="text-indigo-300 font-medium">
                    {currentItem.brandName}
                  </span>
                </span>
              </div>
            </div>
            <div className="ml-auto">
              {currentItem.isProcessing ? (
                <div className="flex items-center">
                  <span className="inline-flex items-center text-sm text-zinc-300">
                    <span className="w-2 h-2 bg-indigo-500 rounded-full mr-2 animate-pulse"></span>
                    Processing
                    {currentItem.isVideo && (
                      <span className="text-sm text-zinc-400 ml-2">
                        {formatTime(currentItem.elapsedTime)}
                      </span>
                    )}
                  </span>
                </div>
              ) : (
                <span className="inline-flex items-center text-sm text-zinc-300">
                  <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                  Complete
                </span>
              )}
            </div>
          </div>

          {/* Content section */}
          <div className="flex-1 p-5 border-l border-r border-zinc-700 bg-zinc-800/30 min-h-[300px]">
            {/* Show steps if available */}
            {currentItem.steps.length > 0 && !currentItem.finalResult && (
              <div className="relative">
                {/* Vertical timeline line */}
                <div className="absolute left-[12px] top-0 bottom-0 w-[1px] bg-zinc-700"></div>

                <div className="space-y-3 pl-8">
                  {!stepsCollapsed &&
                    currentItem.steps.map((step, stepIndex) => (
                      <div
                        key={step.id}
                        className="animate-in fade-in duration-300 !w-[calc(100%-20px)]"
                        style={{ animationDelay: `${stepIndex * 50}ms` }}
                      >
                        <div className="flex items-start gap-3 relative">
                          {/* Step indicator dot */}
                          <div className="absolute left-[-24px] top-0 z-10">
                            <div
                              className={`w-5 h-5 rounded-full flex items-center justify-center transition-all duration-300 bg-zinc-800 text-lg ${stepIndex === currentItem.steps.length - 1 &&
                                !currentItem.isProcessing
                                ? "bg-green-700 text-white"
                                : ""
                                }`}
                            >
                              {stepIndex === currentItem.steps.length - 1 &&
                                currentItem.isProcessing ? (
                                <svg
                                  className="animate-spin h-2.5 w-2.5 text-white"
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
                              ) : (
                                <svg
                                  xmlns="http://www.w3.org/2000/svg"
                                  className="h-2.5 w-2.5 text-white animate-in fade-in duration-300"
                                  viewBox="0 0 20 20"
                                  fill="currentColor"
                                >
                                  <path
                                    fillRule="evenodd"
                                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                    clipRule="evenodd"
                                  />
                                </svg>
                              )}
                            </div>
                          </div>

                          {/* Content */}
                          <div className={
                            (() => {
                              if (step.type === "tool") {
                                try {
                                  const parsed = JSON.parse(step.content);
                                  if (parsed.tool_name === "keep_alive") {
                                    // Only show pulse for the most recent keep_alive step
                                    const isLast = stepIndex === currentItem.steps.length - 1;
                                    return `text-sm text-zinc-200 whitespace-pre-wrap break-words animate-in fade-in duration-300 keep-alive-pulse ${isLast ? "" : ""}`;
                                  }
                                } catch { }
                              }
                              return "text-sm text-zinc-200 whitespace-pre-wrap break-words animate-in fade-in duration-300 max-w-[550px]";
                            })()
                          }>
                            {(() => {
                              if (step.type === "tool") {
                                try {
                                  const parsed = JSON.parse(step.content);
                                  if (parsed.tool_name === "keep_alive") {
                                    // Show a pulsing loader with the task_detail
                                    return (
                                      <span>
                                        <span className="inline-block w-3 h-3 mr-2 rounded-full bg-indigo-400 opacity-60 animate-pulse"></span>
                                        <span className="opacity-60">{parsed.task_detail || "Processing..."}</span>
                                      </span>
                                    );
                                  }
                                } catch { }
                              }
                              // Default rendering
                              if (step.type === "text") {
                                return step.content;
                              } else if (step.taskDetail) {
                                return `${step.taskDetail}...`;
                              } else {
                                return step.content;
                              }
                            })()}
                          </div>
                        </div>
                      </div>
                    ))}

                  {/* Loading indicator for active processing */}
                  {currentItem.isProcessing && (
                    <div className="py-2 text-sm text-zinc-300 flex items-center gap-3">
                      <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse"></div>
                      <div
                        className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse"
                        style={{ animationDelay: "300ms" }}
                      ></div>
                      <div
                        className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse"
                        style={{ animationDelay: "600ms" }}
                      ></div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Show analysis sections in tabs */}
            {currentItem.steps.length > 0 && (
              <div className="prose prose-sm prose-zinc dark:prose-invert overflow-auto p-2 max-h-[600px] custom-scrollbar">
                {!currentItem.isProcessing && (
                  <div className="bg-green-500/10 text-green-300 px-3 py-2 rounded-md text-xs font-medium mb-3 flex items-center space-x-2">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-4 w-4"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span>Analysis complete</span>
                  </div>
                )}

                {/* Simply show the full analysis text */}
                <div>
                  {currentItem.finalResult ? (
                    renderResult(currentItem.finalResult, MarkdownComponents)
                  ) : (
                    <div className="text-zinc-400 text-sm">Processing analysis...</div>
                  )}
                </div>
              </div>
            )}

            {/* Empty state - no steps yet */}
            {currentItem.steps.length === 0 && !currentItem.finalResult && (
              <div className="flex items-center justify-center h-[300px] text-zinc-500 text-sm">
                Waiting to start processing...
              </div>
            )}
          </div>

          {/* Footer with controls */}
          <div className="flex items-center justify-between p-3 border border-zinc-700 rounded-b-lg bg-zinc-800/70">
            {/* Sequential processing indicator */}
            {currentProcessingIndex >= 0 && items.length > 1 && (
              <div className="text-xs text-zinc-400">
                {currentProcessingIndex < items.length ? (
                  <span>
                    Processing file {currentProcessingIndex + 1} of{" "}
                    {items.length}...
                  </span>
                ) : (
                  <span>All files processed</span>
                )}
              </div>
            )}
            {/* Toggle for steps/results */}
            {(currentItem.steps.length > 0 || currentItem.finalResult) && (
              <button
                onClick={onToggleStepsCollapse}
                className="flex items-center p-1.5 text-xs text-zinc-400 hover:text-white transition-colors"
              >
                {stepsCollapsed ? "Show Details" : "Hide Details"}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className={`h-3.5 w-3.5 ml-1 transition-transform duration-200 ${stepsCollapsed ? "rotate-180" : ""
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

            {/* Navigation buttons */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-zinc-500">
                File {currentIndex + 1} of {items.length}
              </span>
              <div className="flex gap-2">
                <Button
                  onClick={handlePrevious}
                  variant="outline"
                  size="sm"
                  disabled={currentIndex === 0}
                  className="h-8 px-2 border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-white"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 19l-7-7 7-7"
                    />
                  </svg>
                </Button>
                <Button
                  onClick={handleNext}
                  variant="outline"
                  size="sm"
                  disabled={currentIndex === items.length - 1}
                  className="h-8 px-2 border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-white"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  // Helper function to render the result based on its structure
  function renderResult(resultText: string, MarkdownComponents: any) {
    if (!resultText) return null;

    // Helper function to clean markdown code blocks and syntax
    const cleanMarkdownCodeBlocks = (text: string): string => {
      if (!text) return '';

      let cleaned = text;

      // First, handle code blocks with language specifiers (```javascript, ```python, etc.)
      cleaned = cleaned.replace(/```[a-zA-Z0-9_\-]*\n([\s\S]*?)```/g, '$1');
      
      // Then handle any remaining code blocks (```)
      cleaned = cleaned.replace(/```([\s\S]*?)```/g, '$1');
      
      // Remove inline code (single backticks)
      cleaned = cleaned.replace(/`([^`]+)`/g, '$1');
      
      return cleaned;
    };
    
    // We now handle the analysis sections directly in the component
    // This function is only used for legacy result formats
    
    try {
      // Try to parse as JSON first
      const parsed = JSON.parse(resultText);
      console.log("Parsed JSON:", parsed);

      // Check if it has a results object with multiple keys
      if (parsed && parsed.results && typeof parsed.results === "object") {
        const resultsObj = parsed.results;
        const keys = Object.keys(resultsObj);

        console.log("Found results object with multiple keys");

        // If it has multiple keys, render each section
        if (keys.length > 0) {
          console.log("Found multiple keys in results object");
          return (
            <div className="space-y-6">
              {keys.map((key) => (
                <div key={key} className="mb-4">
                  <h3 className="text-md font-semibold text-indigo-300 border-b border-zinc-700 pb-2 mb-3 capitalize">
                    {key} Analysis
                  </h3>
                  <ReactMarkdown components={MarkdownComponents}>
                    {cleanMarkdownCodeBlocks(resultsObj[key])}
                  </ReactMarkdown>
                </div>
              ))}
            </div>
          );
        }
      }

      // Direct rendering of tool_result.detailed_report (this is the structure from the logs)
      if (parsed && parsed.tool_result && parsed.tool_result.detailed_report && typeof parsed.tool_result.detailed_report === "string") {
        console.log("Found tool_result.detailed_report - direct rendering");
        const cleanedReport = cleanMarkdownCodeBlocks(parsed.tool_result.detailed_report);
        return (
          <ReactMarkdown components={MarkdownComponents}>
            {cleanedReport}
          </ReactMarkdown>
        );
      }
      
      // If it has a detailed_report property as a string
      if (parsed && parsed.detailed_report && typeof parsed.detailed_report === "string") {
        console.log("Found detailed_report");
        const cleanedReport = cleanMarkdownCodeBlocks(parsed.detailed_report);
        return (
          <ReactMarkdown components={MarkdownComponents}>
            {cleanedReport}
          </ReactMarkdown>
        );
      }
      
      // If it has a 'result' property as a string (single result)
      if (parsed && parsed.result && typeof parsed.result === "string") {
        console.log("Found result property as string");
        const cleanedResult = cleanMarkdownCodeBlocks(parsed.result);
        return (
          <ReactMarkdown components={MarkdownComponents}>
            {cleanedResult}
          </ReactMarkdown>
        );
      }

      // If it has a 'recommendation' property as a string
      if (parsed && parsed.recommendation && typeof parsed.recommendation === "string") {
        console.log("Found recommendation property as string");
        const cleanedRecommendation = cleanMarkdownCodeBlocks(parsed.recommendation);
        return (
          <ReactMarkdown components={MarkdownComponents}>
            {cleanedRecommendation}
          </ReactMarkdown>
        );
      }

      // If we got here, it's a JSON object but not in the expected format
      // Fall back to displaying the stringified JSON
      const cleanedResultText = cleanMarkdownCodeBlocks(resultText);
      return (
        <ReactMarkdown components={MarkdownComponents}>
          {cleanedResultText}
        </ReactMarkdown>
      );
    } catch (e) {
      console.log("Error parsing JSON, rendering as markdown:", e);

      // Not valid JSON, just render as markdown
      const cleanedResultText = cleanMarkdownCodeBlocks(resultText);
      return (
        <ReactMarkdown components={MarkdownComponents}>
          {cleanedResultText}
        </ReactMarkdown>
      );
    }
  }
})

export default ProcessingResultGrid;
