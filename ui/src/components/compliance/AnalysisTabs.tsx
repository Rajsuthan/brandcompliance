import React, { useState } from "react";
import ReactMarkdown from "react-markdown";

interface AnalysisSection {
  id: string;
  title: string;
  content: string;
  isComplete: boolean;
}

interface AnalysisTabsProps {
  sections: Record<string, AnalysisSection>;
  MarkdownComponents: Record<string, React.FC<any>>;
}

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

export const AnalysisTabs: React.FC<AnalysisTabsProps> = ({ sections, MarkdownComponents }) => {
  console.log("AnalysisTabs received sections:", sections);
  
  // Get the list of section IDs, ensuring executive_summary is first
  const sectionIds = Object.keys(sections).sort((a, b) => {
    if (a === "executive_summary") return -1;
    if (b === "executive_summary") return 1;
    return sections[a].title.localeCompare(sections[b].title);
  });

  console.log("Sorted section IDs:", sectionIds);

  // Get the executive summary section and other sections separately
  const executiveSummaryId = sectionIds.find(id => id === "executive_summary");
  const executiveSummary = executiveSummaryId ? sections[executiveSummaryId] : null;
  
  // Get all other sections (excluding executive summary)
  const detailSectionIds = sectionIds.filter(id => id !== "executive_summary");
  console.log("Detail section IDs:", detailSectionIds);
  
  // Add state to track the active tab - default to first non-executive summary section if available
  const [activeTabId, setActiveTabId] = useState(detailSectionIds.length > 0 ? detailSectionIds[0] : "");

  // If no sections are available yet, show a loading state
  if (sectionIds.length === 0) {
    return (
      <div className="flex items-center justify-center h-[300px] text-zinc-500 text-sm">
        <div className="flex items-center">
          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Preparing analysis sections...
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Executive Summary Section */}
      {executiveSummary && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-white mb-4">{executiveSummary.title}</h2>
          {executiveSummary.isComplete ? (
            <div className="bg-zinc-800/50 p-4 rounded-lg">
              <ReactMarkdown components={MarkdownComponents}>
                {cleanMarkdownCodeBlocks(executiveSummary.content)}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[200px] text-zinc-500 text-sm bg-zinc-800/50 p-4 rounded-lg">
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Generating executive summary...
              </div>
            </div>
          )}
        </div>
      )}

      {/* Detailed Analysis Sections */}
      {detailSectionIds.length > 0 && (
        <div>
          <h3 className="text-lg font-medium text-white mb-4">Detailed Analysis</h3>
          
          {/* Tabs for detailed sections */}
          <div className="flex overflow-x-auto mb-4 border-b border-zinc-700">
            {detailSectionIds.map((sectionId) => (
              <button
                key={sectionId}
                className={`px-4 py-2 text-sm font-medium whitespace-nowrap ${
                  sectionId === activeTabId 
                    ? "text-indigo-400 border-b-2 border-indigo-400"
                    : "text-zinc-400 hover:text-zinc-300"
                }`}
                onClick={() => setActiveTabId(sectionId)}
              >
                {sections[sectionId].title}
                {!sections[sectionId].isComplete && (
                  <span className="ml-2 animate-pulse">⋯</span>
                )}
              </button>
            ))}
          </div>

          {/* Content for active tab only */}
          {detailSectionIds.map((sectionId) => (
            <div
              key={sectionId}
              className={`mb-6 bg-zinc-800/30 p-4 rounded-lg ${sectionId === activeTabId ? 'block' : 'hidden'}`}
            >
              <h4 className="text-md font-medium text-white mb-2">{sections[sectionId].title}</h4>
              {sections[sectionId].isComplete ? (
                <ReactMarkdown components={MarkdownComponents}>
                  {cleanMarkdownCodeBlocks(sections[sectionId].content)}
                </ReactMarkdown>
              ) : (
                <div className="flex items-center justify-center h-[100px] text-zinc-500 text-sm">
                  <div className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Analyzing {sections[sectionId].title.toLowerCase()}...
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AnalysisTabs;
