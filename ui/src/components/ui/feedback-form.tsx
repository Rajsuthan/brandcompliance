import { useState } from "react";
import { Button } from "@/components/ui/button";
import { submitFeedback } from "@/services/complianceService";

interface FeedbackFormProps {
  authToken: string | null;
  onFeedbackSubmitted?: () => void;
}

export function FeedbackForm({
  authToken,
  onFeedbackSubmitted,
}: FeedbackFormProps) {
  const [feedback, setFeedback] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!authToken) {
      setError("You must be logged in to submit feedback");
      return;
    }

    if (!feedback.trim()) {
      setError("Feedback cannot be empty");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await submitFeedback(feedback, authToken);
      setSubmitSuccess(true);
      setFeedback("");

      // Call the callback if provided
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted();
      }

      // Reset success message after 3 seconds
      setTimeout(() => {
        setSubmitSuccess(false);
      }, 3000);
    } catch (err) {
      setError("Failed to submit feedback. Please try again.");
      console.error("Feedback submission error:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="border border-zinc-700 rounded-lg p-4 bg-zinc-800/50 shadow-md">
      <h3 className="text-lg font-medium mb-3 text-white">Provide Feedback</h3>
      <p className="text-sm text-zinc-400 mb-4">
        Your feedback helps improve the compliance system. It will be stored and
        used to enhance future compliance checks.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Share your feedback, suggestions, or corrections..."
            className="w-full p-3 bg-zinc-900 border border-zinc-700 rounded-md text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            rows={4}
            disabled={isSubmitting}
          />
        </div>

        {error && <div className="text-red-400 text-sm py-1">{error}</div>}

        {submitSuccess && (
          <div className="text-green-400 text-sm py-1 flex items-center gap-2">
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
            Feedback submitted successfully!
          </div>
        )}

        <div className="flex justify-end">
          <Button
            type="submit"
            disabled={isSubmitting || !authToken}
            className={`bg-indigo-600 hover:bg-indigo-500 text-white transition-all duration-200 ${
              isSubmitting ? "opacity-70" : ""
            }`}
          >
            {isSubmitting ? (
              <span className="flex items-center">
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
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
                Submitting...
              </span>
            ) : (
              "Submit Feedback"
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
