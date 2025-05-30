import React from "react";
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

  // Remove fenced code block markers (```) and optional language identifier
  cleaned = cleaned.replace(/```[a-zA-Z0-9_\-]*\s*/g, ''); // Remove opening ``` and optional language/whitespace
  cleaned = cleaned.replace(/```/g, ''); // Remove closing ```

  // Remove inline code markers (`)
  cleaned = cleaned.replace(/`/g, '');

  return cleaned;
};

export const AnalysisTabs: React.FC<AnalysisTabsProps> = ({ sections, MarkdownComponents }) => {
  // Get the list of section IDs
  const sectionIds = Object.keys(sections);

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

  // Combine all section content into a single string
  const fullAnalysisText = sectionIds.map((sectionId) => {
    const section = sections[sectionId];
    return section.isComplete ? cleanMarkdownCodeBlocks(section.content) : '';
  }).join('\n\n'); // Join with double newlines for spacing

  return (
    <div className="w-full bg-zinc-800/50 p-4 rounded-lg">
      <ReactMarkdown components={MarkdownComponents}>
        {fullAnalysisText}
      </ReactMarkdown>
    </div>
  );
};

export default AnalysisTabs;
