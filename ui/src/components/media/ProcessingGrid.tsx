import React, { useRef } from 'react';
import { Button } from '@/components/ui/button';
import ReactMarkdown from 'react-markdown';

export interface ProcessingStep {
  id: string;
  type: 'text' | 'tool';
  content: string;
  taskDetail?: string;
}

export interface ProcessingItem {
  id: string;
  file: File;
  preview: string;
  isVideo: boolean;
  brandName: string;
  isProcessing: boolean;
  steps: ProcessingStep[];
  finalResult: string | null;
  elapsedTime: number;
}

interface ProcessingGridProps {
  items: ProcessingItem[];
  stepsCollapsed: boolean;
  onToggleStepsCollapse: () => void;
  onNewAnalysis: () => void;
  formatTime: (seconds: number) => string;
}

export const ProcessingGrid: React.FC<ProcessingGridProps> = ({
  items,
  stepsCollapsed,
  onToggleStepsCollapse,
  onNewAnalysis,
  formatTime
}) => {
  const stepsEndRefs = useRef<(HTMLDivElement | null)[]>([]);
  
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
      <p className="text-xs leading-relaxed my-2 text-zinc-300" {...props} />
    ),
    ul: (props: React.HTMLAttributes<HTMLUListElement>) => (
      <ul className="list-disc pl-4 my-2 text-zinc-300" {...props} />
    ),
    ol: (props: React.HTMLAttributes<HTMLOListElement>) => (
      <ol className="list-decimal pl-4 my-2 text-zinc-300" {...props} />
    ),
    li: (props: React.HTMLAttributes<HTMLLIElement>) => (
      <li className="text-xs my-1 leading-relaxed" {...props} />
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
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {items.map((item, itemIndex) => (
          <div key={item.id} className="flex flex-col border border-zinc-700 rounded-lg overflow-hidden bg-zinc-800/30 shadow-lg animate-in enhanced-fade-in duration-400">
            {/* Media header with preview thumbnail */}
            <div className="flex items-start p-3 border-b border-zinc-700 bg-zinc-800/70">
              <div className="w-12 h-12 rounded-md overflow-hidden flex-shrink-0 border border-zinc-700 shadow-md mr-3">
                {item.isVideo ? (
                  <div className="w-full h-full bg-zinc-900 flex items-center justify-center">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-6 w-6 text-indigo-400"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
                    </svg>
                  </div>
                ) : (
                  <img
                    src={item.preview}
                    alt="Thumbnail"
                    className="w-full h-full object-cover"
                  />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-medium truncate text-white">
                  {item.file.name}
                </h3>
                <div className="flex flex-col text-xs">
                  <span className="text-zinc-400">
                    {(item.file.size / (1024 * 1024)).toFixed(2)} MB
                  </span>
                  <span className="text-zinc-300">
                    Brand: <span className="text-indigo-300">{item.brandName}</span>
                  </span>
                </div>
              </div>
              {/* Processing status */}
              <div className="ml-auto">
                {item.isProcessing ? (
                  <div className="flex items-center">
                    <span className="inline-flex items-center text-xs text-zinc-300">
                      <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full mr-1.5 animate-pulse"></span>
                      {item.isVideo && (
                        <span className="text-xs text-zinc-400 ml-1">
                          {formatTime(item.elapsedTime)}
                        </span>
                      )}
                    </span>
                  </div>
                ) : (
                  <span className="inline-flex items-center text-xs text-zinc-300">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1.5"></span>
                    Done
                  </span>
                )}
              </div>
            </div>
            
            {/* Steps or results */}
            <div className="flex-1 p-3">
              {/* Show steps if available */}
              {item.steps.length > 0 && !item.finalResult && (
                <div className="relative">
                  {/* Vertical timeline line */}
                  <div className="absolute left-[9px] top-0 bottom-0 w-[1px] bg-zinc-700"></div>
                  
                  <div className="space-y-2 pl-6">
                    {!stepsCollapsed && item.steps.map((step, stepIndex) => (
                      <div
                        key={step.id}
                        className="animate-in fade-in duration-300"
                        style={{ animationDelay: `${stepIndex * 50}ms` }}
                      >
                        <div className="flex items-start gap-2 relative">
                          {/* Step indicator dot */}
                          <div className="absolute left-[-18px] top-0 z-10">
                            <div
                              className={`w-4 h-4 rounded-full flex items-center justify-center transition-all duration-300 bg-zinc-800 text-lg ${stepIndex === item.steps.length - 1 && !item.isProcessing ? "bg-green-700 text-white" : ""}`}
                            >
                              {stepIndex === item.steps.length - 1 && item.isProcessing ? (
                                <svg
                                  className="animate-spin h-2 w-2 text-white"
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
                                  className="h-2 w-2 text-white animate-in fade-in duration-300"
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
                          <div className="text-xs text-zinc-200 whitespace-pre-wrap break-words animate-in fade-in duration-300">
                            {step.type === "text" ? step.content : step.taskDetail ? `${step.taskDetail}...` : "Processing..."}
                          </div>
                        </div>
                      </div>
                    ))}
                    
                    {/* Loading indicator for active processing */}
                    {item.isProcessing && (
                      <div className="py-1 text-xs text-zinc-300 flex items-center gap-2">
                        <div className="w-1 h-1 bg-indigo-500 rounded-full animate-pulse"></div>
                        <div
                          className="w-1 h-1 bg-indigo-500 rounded-full animate-pulse"
                          style={{ animationDelay: "300ms" }}
                        ></div>
                        <div
                          className="w-1 h-1 bg-indigo-500 rounded-full animate-pulse"
                          style={{ animationDelay: "600ms" }}
                        ></div>
                      </div>
                    )}
                    
                    {/* Reference for scrolling */}
                    <div ref={el => { stepsEndRefs.current[itemIndex] = el; }} />
                  </div>
                </div>
              )}
              
              {/* Show final result if available */}
              {item.finalResult && (
                <div className="prose prose-sm prose-zinc dark:prose-invert overflow-auto max-h-[300px] custom-scrollbar p-1">
                  <ReactMarkdown components={MarkdownComponents}>
                    {item.finalResult}
                  </ReactMarkdown>
                </div>
              )}
              
              {/* Empty state - no steps yet */}
              {item.steps.length === 0 && !item.finalResult && (
                <div className="flex items-center justify-center h-[200px] text-zinc-500 text-sm">
                  Waiting to start processing...
                </div>
              )}
            </div>
            
            {/* Toggle for steps/results */}
            {(item.steps.length > 0 || item.finalResult) && (
              <div className="border-t border-zinc-700 p-2">
                <button
                  onClick={onToggleStepsCollapse}
                  className="w-full flex items-center justify-center p-1 text-xs text-zinc-400 hover:text-white transition-colors"
                >
                  {stepsCollapsed ? "Show Details" : "Hide Details"}
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className={`h-3 w-3 ml-1 transition-transform duration-200 ${stepsCollapsed ? "rotate-180" : ""}`}
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
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
