import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { BarChart, Image, Video, FileText, Clock } from "lucide-react";
import { format } from "date-fns";

interface UsageMetrics {
  total_analyses: number;
  image_analyses: number;
  video_analyses: number;
  total_guidelines: number;
  recent_activity: Array<{
    id: string;
    user_id: string;
    asset_type: string;
    analysis_id?: string;
    asset_id?: string; // Added asset_id property
    timestamp: any; // Firestore timestamp
  }>;
}

const ActivityPage: React.FC = () => {
  const { user, getIdToken } = useAuth();
  const [metrics, setMetrics] = useState<UsageMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      if (!user) return;

      try {
        setLoading(true);
        const token = await getIdToken();

        const response = await fetch(
          "http://localhost:8000/api/compliance/usage-metrics",
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch metrics: ${response.status}`);
        }

        const data = await response.json();
        setMetrics(data.metrics);
      } catch (err: any) {
        console.error("Error fetching metrics:", err);
        setError(err.message || "Failed to load activity metrics");
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [user, getIdToken]);

  const formatTimestamp = (timestamp: any) => {
    if (!timestamp) return "Unknown date";

    // Handle Firestore timestamp
    if (timestamp.seconds) {
      const date = new Date(timestamp.seconds * 1000);
      return format(date, "MMM d, yyyy h:mm a");
    }

    // Handle regular date strings
    try {
      return format(new Date(timestamp), "MMM d, yyyy h:mm a");
    } catch (e) {
      return "Invalid date";
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-8">
        <BarChart className="h-6 w-6 text-indigo-400" />
        <h1 className="!text-2xl font-bold text-white">Activity & Metrics</h1>
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full bg-zinc-800" />
          <Skeleton className="h-64 w-full bg-zinc-800" />
        </div>
      ) : error ? (
        <div className="p-4 border border-red-800 bg-red-900/20 rounded-md text-red-200">
          <p>{error}</p>
          <button
            className="mt-2 text-sm text-red-300 underline"
            onClick={() => window.location.reload()}
          >
            Try again
          </button>
        </div>
      ) : metrics ? (
        <div className="space-y-8">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 shadow-md">
              <div className="flex items-center justify-between">
                <h3 className="text-zinc-400 text-sm font-medium">
                  Total Analyses
                </h3>
                <BarChart className="h-5 w-5 text-indigo-400" />
              </div>
              <p className="text-3xl font-bold mt-2 text-white">
                {metrics.total_analyses}
              </p>
              <p className="text-xs text-zinc-500 mt-1">
                Completed analyses only
              </p>
            </div>

            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 shadow-md">
              <div className="flex items-center justify-between">
                <h3 className="text-zinc-400 text-sm font-medium">
                  Image Analyses
                </h3>
                <Image className="h-5 w-5 text-indigo-400" />
              </div>
              <p className="text-3xl font-bold mt-2 text-white">
                {metrics.image_analyses}
              </p>
            </div>

            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 shadow-md">
              <div className="flex items-center justify-between">
                <h3 className="text-zinc-400 text-sm font-medium">
                  Video Analyses
                </h3>
                <Video className="h-5 w-5 text-indigo-400" />
              </div>
              <p className="text-3xl font-bold mt-2 text-white">
                {metrics.video_analyses}
              </p>
            </div>

            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 shadow-md">
              <div className="flex items-center justify-between">
                <h3 className="text-zinc-400 text-sm font-medium">
                  Brand Guidelines
                </h3>
                <FileText className="h-5 w-5 text-indigo-400" />
              </div>
              <p className="text-3xl font-bold mt-2 text-white">
                {metrics.total_guidelines}
              </p>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 shadow-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-white">
                Recent Activity
              </h2>
              <div className="text-xs text-zinc-400">
                <span className="inline-flex items-center mr-2">
                  <span className="w-2 h-2 rounded-full bg-green-400 mr-1"></span>{" "}
                  Completed
                </span>
                <span className="inline-flex items-center">
                  <span className="w-2 h-2 rounded-full bg-yellow-400 mr-1"></span>{" "}
                  Started
                </span>
                <div className="mt-1">
                  <span className="text-zinc-500">
                    Note: "Started" activities may be from previous sessions or
                    incomplete analyses
                  </span>
                </div>
              </div>
            </div>

            {metrics.recent_activity.length === 0 ? (
              <p className="text-zinc-400 py-4">No recent activity found.</p>
            ) : (
              <div className="space-y-4">
                {metrics.recent_activity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-start gap-3 p-3 border border-zinc-800 rounded-md hover:bg-zinc-800/50 transition-colors"
                  >
                    <div className="mt-1">
                      {activity.asset_type === "image" ? (
                        <Image className="h-5 w-5 text-indigo-400" />
                      ) : activity.asset_type === "video" ? (
                        <Video className="h-5 w-5 text-indigo-400" />
                      ) : (
                        <FileText className="h-5 w-5 text-indigo-400" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className="bg-zinc-800 text-zinc-300 border-zinc-700"
                        >
                          {activity.asset_type}
                        </Badge>
                        {activity.analysis_id ? (
                          <Badge
                            variant="outline"
                            className="bg-green-900/30 text-green-300 border-green-800"
                          >
                            Completed
                          </Badge>
                        ) : (
                          <Badge
                            variant="outline"
                            className="bg-yellow-900/30 text-yellow-300 border-yellow-800"
                          >
                            Started
                          </Badge>
                        )}
                      </div>

                      {activity.analysis_id && (
                        <div className="mt-1 text-xs text-zinc-400">
                          Analysis ID:{" "}
                          <span className="font-mono">
                            {activity.analysis_id.substring(0, 8)}...
                          </span>
                        </div>
                      )}

                      <div className="flex items-center gap-1 mt-1 text-xs text-zinc-400">
                        <Clock className="h-3 w-3" />
                        <span>{formatTimestamp(activity.timestamp)}</span>
                      </div>

                      {/* Debug info */}
                      <div className="mt-2 p-2 bg-zinc-800/50 rounded text-xs font-mono text-zinc-500 overflow-x-auto">
                        <div>ID: {activity.id}</div>
                        <div>Type: {activity.asset_type}</div>
                        <div>Analysis ID: {activity.analysis_id || "None"}</div>
                        <div>Asset ID: {activity.asset_id || "None"}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <p className="text-zinc-400">No metrics available.</p>
      )}
    </div>
  );
};

export default ActivityPage;
