import React, { useState, useEffect } from "react";

interface ProcessingToastProps {
  isVisible: boolean;
  fileCount: number;
  onClose: () => void;
}

export const ProcessingToast: React.FC<ProcessingToastProps> = ({
  isVisible,
  fileCount,
  onClose,
}) => {
  const [isShowing, setIsShowing] = useState(false);

  // Animate in and auto-dismiss after a certain time
  useEffect(() => {
    if (isVisible) {
      setIsShowing(true);

      // Auto-dismiss after 10 seconds
      const timer = setTimeout(() => {
        setIsShowing(false);
        setTimeout(onClose, 300); // Wait for animation to finish before calling onClose
      }, 10000);

      return () => clearTimeout(timer);
    } else {
      setIsShowing(false);
    }
  }, [isVisible, onClose]);

  if (!isVisible && !isShowing) return null;

  return (
    <div
      className={`fixed bottom-6 left-1/2 transform -translate-x-1/2 max-w-md w-full bg-zinc-800 border border-zinc-700 rounded-lg shadow-lg z-50 transition-all duration-300 ${
        isShowing ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"
      }`}
    >
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0 bg-indigo-500/20 p-2 rounded-full">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 text-indigo-400"
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
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-white">
              Starting Compliance Check
            </h3>
            <div className="mt-2 text-sm text-zinc-300 space-y-2">
              <p>
                Processing {fileCount} file{fileCount > 1 ? "s" : ""} for brand
                compliance:
              </p>
              <ul className="list-disc pl-5 space-y-1 text-xs">
                <li>Files will be analyzed one at a time in sequence</li>
                <li>Each file's progress will be shown in real-time</li>
                <li>Results will be displayed as soon as they're available</li>
                <li>
                  You can navigate between files using the tabs or navigation
                  buttons
                </li>
                <li>
                  When complete, you can provide feedback at the bottom of the
                  page
                </li>
              </ul>
            </div>
          </div>
          <button
            onClick={() => {
              setIsShowing(false);
              setTimeout(onClose, 300);
            }}
            className="flex-shrink-0 ml-2 bg-zinc-700 rounded-full p-1 text-zinc-400 hover:text-white"
          >
            <svg
              className="h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
      {/* Progress indicator dots */}
      <div className="flex justify-center items-center pb-2">
        <div className="flex space-x-1">
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
      </div>
    </div>
  );
};

export default ProcessingToast;
