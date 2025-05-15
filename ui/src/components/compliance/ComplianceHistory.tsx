import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useComplianceService,
  ComplianceAnalysisSummary,
} from "@/services/compliance-service";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDistanceToNow } from "date-fns";

const ComplianceHistory: React.FC = () => {
  const [analyses, setAnalyses] = useState<ComplianceAnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const complianceService = useComplianceService();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        console.log("Fetching compliance history...");
        const response = await complianceService.getComplianceHistory();
        console.log("Compliance history response:", response);
        setAnalyses(response.analyses);
        setError(null);
      } catch (err: any) {
        console.error("Error fetching compliance history:", err);
        // Show more detailed error message
        setError(`Failed to load compliance history: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const handleViewAnalysis = (analysisId: string) => {
    navigate(`/compliance/analysis/${analysisId}`);
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "bg-green-500";
    if (score >= 60) return "bg-yellow-500";
    return "bg-red-500";
  };

  const getTypeIcon = (type: string) => {
    if (type === "image") {
      return (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
            clipRule="evenodd"
          />
        </svg>
      );
    }
    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-5 w-5"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
      </svg>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="!text-lg font-bold">Compliance History</h1>
        <Button onClick={() => navigate("/")}>New Analysis</Button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="overflow-hidden">
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-1/2 mb-2" />
                <Skeleton className="h-6 w-3/4" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-2/3" />
              </CardContent>
              <CardFooter>
                <Skeleton className="h-10 w-full" />
              </CardFooter>
            </Card>
          ))}
        </div>
      ) : analyses.length === 0 ? (
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
                d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <h3 className="text-xl font-medium mb-2">
            No compliance analyses yet
          </h3>
          <p className="text-zinc-500 mb-6">
            Start by analyzing an image or video for brand compliance
          </p>
          <Button onClick={() => navigate("/")}>New Analysis</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {analyses.map((analysis) => (
            <Card
              key={analysis.id}
              className="overflow-hidden hover:shadow-md transition-shadow"
            >
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <Badge variant="outline" className="flex items-center gap-1">
                    {getTypeIcon(analysis.type)}
                    {analysis.type.charAt(0).toUpperCase() +
                      analysis.type.slice(1)}
                  </Badge>
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-white ${getScoreColor(
                      analysis.compliance_score
                    )}`}
                  >
                    {Math.round(analysis.compliance_score)}
                  </div>
                </div>
                <CardTitle
                  className="text-lg mt-2 truncate"
                  title={analysis.filename}
                >
                  {analysis.filename}
                </CardTitle>
                <CardDescription>
                  {analysis.brand_name || "No brand specified"}
                </CardDescription>
              </CardHeader>
              <CardContent className="pb-2">
                <p className="text-sm text-zinc-500">
                  {formatDistanceToNow(new Date(analysis.created_at), {
                    addSuffix: true,
                  })}
                </p>
              </CardContent>
              <CardFooter>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleViewAnalysis(analysis.id)}
                >
                  View Analysis
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default ComplianceHistory;
