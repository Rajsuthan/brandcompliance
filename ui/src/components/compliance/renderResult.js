import React from 'react';
import ReactMarkdown from 'react-markdown';

// Helper function to render the result based on its structure
export function renderResult(resultText, MarkdownComponents) {
  try {
    // First, check if the result is already in markdown format (not JSON)
    if (resultText.trim().startsWith('#') || resultText.trim().startsWith('Brand Compliance Analysis')) {
      console.log("Result appears to be markdown, rendering directly");
      return (
        <ReactMarkdown components={MarkdownComponents}>
          {resultText}
        </ReactMarkdown>
      );
    }

    // Try to parse the result as JSON
    const parsed = JSON.parse(resultText);
    console.log("Parsed JSON result:", parsed);

    // Direct detailed_report from tool_result (from the logs, this is the structure we need)
    if (parsed && parsed.tool_result && parsed.tool_result.detailed_report &&
        typeof parsed.tool_result.detailed_report === "string") {
      console.log("Found tool_result.detailed_report");
      return (
        <ReactMarkdown components={MarkdownComponents}>
          {parsed.tool_result.detailed_report}
        </ReactMarkdown>
      );
    }

    // Check for XML tags in detailed_report
    if (parsed && parsed.tool_result && parsed.tool_result.detailed_report &&
        typeof parsed.tool_result.detailed_report === "string") {
      const result = parsed.tool_result.detailed_report;
      const regex = /<r>(.*?)<\/result>/s;
      const match = result.match(regex);
      if (match) {
        console.log("Found result inside tool_result.detailed_report XML tags");
        return (
          <ReactMarkdown components={MarkdownComponents}>
            {match[1]}
          </ReactMarkdown>
        );
      }
    }

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
                  {resultsObj[key]}
                </ReactMarkdown>
              </div>
            ))}
          </div>
        );
      }
    }

    // If it has a 'result' property as a string (single result)
    if (parsed && parsed.result && typeof parsed.result === "string") {
      console.log("Found result property as string");
      return (
        <ReactMarkdown components={MarkdownComponents}>
          {parsed.result}
        </ReactMarkdown>
      );
    }

    // If it has a 'recommendation' property as a string
    if (parsed && parsed.recommendation && typeof parsed.recommendation === "string") {
      console.log("Found recommendation property as string");
      return (
        <ReactMarkdown components={MarkdownComponents}>
          {parsed.recommendation}
        </ReactMarkdown>
      );
    }

    // Handle XML tags in detailed_report
    if (parsed && parsed.detailed_report && typeof parsed.detailed_report === "string") {
      const regex1 = /<attempt_completion>\s*<r>(.*?)<\/result>\s*<\/attempt_completion>/s;
      const match1 = parsed.detailed_report.match(regex1);
      if (match1) {
        console.log("Found result inside attempt_completion XML tags");
        return (
          <ReactMarkdown components={MarkdownComponents}>
            {match1[1]}
          </ReactMarkdown>
        );
      }
    }

    // Direct detailed_report
    if (parsed && parsed.detailed_report && typeof parsed.detailed_report === "string") {
      console.log("Found detailed_report");
      return (
        <ReactMarkdown components={MarkdownComponents}>
          {parsed.detailed_report}
        </ReactMarkdown>
      );
    }

    // If we got here, it's a JSON object but not in the expected format
    // Fall back to displaying the stringified JSON
    console.log("Falling back to raw content");
    return (
      <ReactMarkdown components={MarkdownComponents}>
        {resultText}
      </ReactMarkdown>
    );
  } catch (e) {
    // Not valid JSON, just render as markdown
    console.log("Error parsing JSON, rendering as markdown:", e);
    return (
      <ReactMarkdown components={MarkdownComponents}>
        {resultText}
      </ReactMarkdown>
    );
  }
}
