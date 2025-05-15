import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  useComplianceService,
  ComplianceAnalysisDetail,
} from "@/services/compliance-service";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";
import ReactMarkdown from "react-markdown";

const ComplianceDetail: React.FC = () => {
  const { analysisId } = useParams<{ analysisId: string }>();
  const [analysis, setAnalysis] = useState<ComplianceAnalysisDetail | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const complianceService = useComplianceService();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAnalysis = async () => {
      if (!analysisId) return;

      try {
        setLoading(true);
        const response = await complianceService.getComplianceAnalysis(
          analysisId
        );
        setAnalysis(response.analysis);
        setError(null);
      } catch (err) {
        setError("Failed to load compliance analysis. Please try again later.");
        console.error("Error fetching compliance analysis:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, [analysisId]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-500";
    if (score >= 60) return "text-yellow-500";
    return "text-red-500";
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 80) return "bg-green-500";
    if (score >= 60) return "bg-yellow-500";
    return "bg-red-500";
  };

  const getRecommendation = () => {
    if (!analysis) return "";

    console.log("Analysis results:", analysis.results);

    try {
      // Try to extract tool_result and detailed_report
      if (
        analysis.results.tool_result &&
        analysis.results.tool_result.detailed_report
      ) {
        console.log("Found tool_result.detailed_report");
        return analysis.results.tool_result.detailed_report;
      }

      // Try to extract detailed_report directly
      if (analysis.results.detailed_report) {
        console.log("Found detailed_report");
        return analysis.results.detailed_report;
      }

      // Check for XML tags in detailed_report
      if (typeof analysis.results === "string") {
        try {
          // Try to parse the string as JSON
          const parsedResults = JSON.parse(analysis.results);

          if (
            parsedResults.tool_result &&
            parsedResults.tool_result.detailed_report
          ) {
            console.log("Found tool_result.detailed_report in parsed string");
            return parsedResults.tool_result.detailed_report;
          }

          if (parsedResults.detailed_report) {
            console.log("Found detailed_report in parsed string");
            return parsedResults.detailed_report;
          }
        } catch (e) {
          // Not a valid JSON string, continue with other checks
        }
      }

      // Try to extract recommendation from different result formats
      if (analysis.results.recommendation) {
        console.log("Found recommendation");
        return analysis.results.recommendation;
      }

      if (analysis.results.summary) {
        console.log("Found summary");
        return analysis.results.summary;
      }

      // Fallback to stringified results
      console.log("Using fallback stringified results");
      return JSON.stringify(analysis.results, null, 2);
    } catch (error) {
      console.error("Error parsing results:", error);
      return "Error displaying compliance report. Please contact support.";
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center mb-6">
        <Button
          variant="ghost"
          className="mr-2"
          onClick={() => navigate("/compliance/history")}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5 mr-1"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
              clipRule="evenodd"
            />
          </svg>
          Back
        </Button>
        <h1 className="!text-2xl font-bold">Compliance Analysis</h1>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-8 w-1/3 mb-2" />
              <Skeleton className="h-4 w-1/4" />
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
              </div>
              <Skeleton className="h-40" />
            </CardContent>
          </Card>
        </div>
      ) : analysis ? (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-xl mb-1">
                    {analysis.filename}
                  </CardTitle>
                  <p className="text-zinc-500 text-sm">
                    {format(new Date(analysis.created_at), "PPpp")}
                  </p>
                </div>
                <div
                  className={`w-16 h-16 rounded-full flex items-center justify-center text-white text-xl font-bold ${getScoreBgColor(
                    analysis.compliance_score
                  )}`}
                >
                  {Math.round(analysis.compliance_score)}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className="bg-zinc-100 dark:bg-zinc-800 p-4 rounded-lg">
                  <h3 className="font-medium mb-2">Analysis Details</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Type:</span>
                      <Badge variant="outline">
                        {analysis.type === "image" ? (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="h-4 w-4 mr-1"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                          >
                            <path
                              fillRule="evenodd"
                              d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
                              clipRule="evenodd"
                            />
                          </svg>
                        ) : (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="h-4 w-4 mr-1"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                          >
                            <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
                          </svg>
                        )}
                        {analysis.type.charAt(0).toUpperCase() +
                          analysis.type.slice(1)}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Brand:</span>
                      <span>{analysis.brand_name || "Not specified"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Compliance Score:</span>
                      <span
                        className={`font-medium ${getScoreColor(
                          analysis.compliance_score
                        )}`}
                      >
                        {Math.round(analysis.compliance_score)}%
                      </span>
                    </div>
                  </div>
                </div>

                {analysis.type === "image" ? (
                  <div className="bg-zinc-100 dark:bg-zinc-800 p-4 rounded-lg flex items-center justify-center">
                    <p className="text-zinc-500 text-center">
                      Image preview not available
                    </p>
                  </div>
                ) : (
                  <div className="bg-zinc-100 dark:bg-zinc-800 p-4 rounded-lg">
                    <h3 className="font-medium mb-2">Video Details</h3>
                    {analysis.video_url ? (
                      <a
                        href={analysis.video_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:underline flex items-center"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-4 w-4 mr-1"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                          <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                        </svg>
                        View Original Video
                      </a>
                    ) : (
                      <p className="text-zinc-500">Video URL not available</p>
                    )}
                  </div>
                )}
              </div>

              <div className="bg-zinc-50 dark:bg-zinc-900 p-6 rounded-lg">
                <h2 className="text-lg font-medium mb-4">Compliance Report</h2>
                <div className="custom-markdown">
                  <style>
                    {`
                    .custom-markdown {
                      font-size: 0.875rem;
                      line-height: 1.5;
                      // color: #52525b;
                    }

                    .dark .custom-markdown {
                      color: #a1a1aa;
                    }

                    .custom-markdown h1,
                    .custom-markdown h2,
                    .custom-markdown h3,
                    .custom-markdown h4 {
                      margin-top: 1.5em;
                      margin-bottom: 0.75em;
                      font-weight: 500;
                      line-height: 1.3;
                    }

                    .custom-markdown h1 {
                      font-size: 1.25rem;
                      color: #18181b;
                    }

                    .dark .custom-markdown h1 {
                      color: #e4e4e7;
                    }

                    .custom-markdown h2 {
                      font-size: 1.125rem;
                      color: #27272a;
                    }

                    .dark .custom-markdown h2 {
                      color: #d4d4d8;
                    }

                    .custom-markdown h3 {
                      font-size: 1rem;
                      color: #3f3f46;
                    }

                    .dark .custom-markdown h3 {
                      color: #a1a1aa;
                    }

                    .custom-markdown p {
                      margin-bottom: 1rem;
                    }

                    .custom-markdown ul,
                    .custom-markdown ol {
                      margin-top: 0.5rem;
                      margin-bottom: 1rem;
                      padding-left: 1.5rem;
                    }

                    .custom-markdown li {
                      margin-bottom: 0.25rem;
                    }

                    .custom-markdown strong {
                      font-weight: 600;
                      color: #27272a;
                    }

                    .dark .custom-markdown strong {
                      color: #e4e4e7;
                    }

                    .custom-markdown blockquote {
                      border-left: 2px solid #d4d4d8;
                      padding-left: 1rem;
                      font-style: italic;
                      color: #71717a;
                      margin: 1rem 0;
                    }

                    .dark .custom-markdown blockquote {
                      border-left-color: #52525b;
                    }

                    .custom-markdown code {
                      font-family: monospace;
                      font-size: 0.875rem;
                      background-color: #f4f4f5;
                      padding: 0.125rem 0.25rem;
                      border-radius: 0.25rem;
                    }

                    .dark .custom-markdown code {
                      background-color: #27272a;
                    }

                    .custom-markdown hr {
                      margin: 1.5rem 0;
                      border: 0;
                      border-top: 1px solid #e4e4e7;
                    }

                    .dark .custom-markdown hr {
                      border-top-color: #3f3f46;
                    }

                    .custom-markdown table {
                      width: 100%;
                      border-collapse: collapse;
                      margin: 1rem 0;
                      font-size: 0.875rem;
                    }

                    .custom-markdown th {
                      background-color: #f4f4f5;
                      font-weight: 500;
                      text-align: left;
                      padding: 0.5rem;
                      border: 1px solid #e4e4e7;
                    }

                    .dark .custom-markdown th {
                      background-color: #27272a;
                      border-color: #3f3f46;
                    }

                    .custom-markdown td {
                      padding: 0.5rem;
                      border: 1px solid #e4e4e7;
                    }

                    .dark .custom-markdown td {
                      border-color: #3f3f46;
                    }
                  `}
                  </style>
                  <ReactMarkdown>{getRecommendation()}</ReactMarkdown>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="text-zinc-400 mb-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-16 w-16 mx-auto"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h3 className="text-xl font-medium mb-2">Analysis not found</h3>
          <p className="text-zinc-500 mb-6">
            The compliance analysis you're looking for doesn't exist or you
            don't have permission to view it.
          </p>
          <Button onClick={() => navigate("/compliance/history")}>
            Back to History
          </Button>
        </div>
      )}
    </div>
  );
};

export default ComplianceDetail;
