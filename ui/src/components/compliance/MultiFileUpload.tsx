import React, { useState } from "react";
import { FileUpload } from "@/components/ui/file-upload";
import { Button } from "@/components/ui/button";
import { MediaFile } from "./MediaGrid";

interface MultiFileUploadProps {
  onStartProcessing: (mediaItems: MediaFile[]) => void;
  isProcessing: boolean;
}

export const MultiFileUpload: React.FC<MultiFileUploadProps> = ({
  onStartProcessing,
  isProcessing,
}) => {
  const [mediaItems, setMediaItems] = useState<MediaFile[]>([]);
  const [expandedItemId, setExpandedItemId] = useState<string | null>(null);

  // Handle file selection
  const handleFileSelect = (file: File) => {
    // Check if file already exists by name (simple duplicate check)
    if (mediaItems.some((item) => item.file.name === file.name)) {
      return;
    }

    // Create a new media item with preview
    const reader = new FileReader();
    const isVideoFile = file.type.startsWith("video/");

    reader.onload = () => {
      const newItem: MediaFile = {
        id: `file-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        file,
        preview: reader.result as string,
        isVideo: isVideoFile,
        brandName: "", // Initialize with empty brand name
      };

      setMediaItems((prev) => [...prev, newItem]);

      // Automatically expand the brand name input for the newly added item
      setExpandedItemId(newItem.id);
    };

    reader.readAsDataURL(file);
  };

  // Update brand name for a specific item
  const updateBrandName = (id: string, brandName: string) => {
    setMediaItems(
      mediaItems.map((item) => (item.id === id ? { ...item, brandName } : item))
    );
  };

  // Handle removal of a media item
  const handleRemoveMediaItem = (id: string) => {
    setMediaItems((prev) => prev.filter((item) => item.id !== id));

    // If the removed item was expanded, clear the expanded state
    if (expandedItemId === id) {
      setExpandedItemId(null);
    }
  };

  // Clear all files
  const handleClearAll = () => {
    setMediaItems([]);
    setExpandedItemId(null);
  };

  // Toggle expanded state for a specific item
  const toggleExpanded = (id: string) => {
    setExpandedItemId(expandedItemId === id ? null : id);
  };

  // Check if we can start processing (all files have brand names)
  const canStartProcessing =
    mediaItems.length > 0 &&
    mediaItems.every((item) => item.brandName.trim() !== "");

  // Count how many files have brand names set
  const completedItemsCount = mediaItems.filter(
    (item) => item.brandName.trim() !== ""
  ).length;

  return (
    <div className="w-full space-y-4">
      {/* File info and uploads list */}
      {mediaItems.length > 0 ? (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <span className="font-medium text-sm text-white">
                {mediaItems.length} file{mediaItems.length > 1 ? "s" : ""}{" "}
                selected
              </span>

              {/* Show completion status */}
              {mediaItems.length > 1 && (
                <span className="text-xs text-zinc-400">
                  ({completedItemsCount}/{mediaItems.length} with brand names)
                </span>
              )}
            </div>
            <button
              onClick={handleClearAll}
              className="text-xs text-zinc-400 hover:text-white transition-colors"
            >
              Clear all
            </button>
          </div>

          {/* Individual files with brand name inputs */}
          <div className="space-y-3 max-w-lg">
            {mediaItems.map((item) => (
              <div
                key={item.id}
                className="border border-zinc-700 bg-zinc-800/50 rounded-lg overflow-hidden"
              >
                <div
                  className="flex items-center px-3 py-2 cursor-pointer"
                  onClick={() => toggleExpanded(item.id)}
                >
                  {/* File thumbnail */}
                  <div className="w-12 h-12 rounded-md overflow-hidden border border-zinc-700 bg-zinc-800 flex-shrink-0 mr-3">
                    {item.isVideo ? (
                      <div className="w-full h-full flex items-center justify-center bg-zinc-900">
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-5 w-5 text-indigo-400"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
                        </svg>
                      </div>
                    ) : (
                      <img
                        src={item.preview}
                        alt={item.file.name}
                        className="w-full h-full object-cover"
                      />
                    )}
                  </div>

                  {/* File info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate text-white">
                      {item.file.name}
                    </p>
                    <p className="text-xs text-zinc-400">
                      {(item.file.size / (1024 * 1024)).toFixed(2)} MB
                      {item.isVideo ? " • Video" : " • Image"}
                    </p>
                  </div>

                  {/* Brand name status */}
                  <div className="ml-2 flex items-center">
                    {item.brandName.trim() ? (
                      <div className="flex items-center text-xs text-green-400 px-2 py-1 rounded bg-green-500/10">
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-3 w-3 mr-1"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                        <span className="truncate max-w-[80px]">
                          {item.brandName}
                        </span>
                      </div>
                    ) : (
                      <div className="text-xs text-zinc-400 flex items-center">
                        <span className="bg-zinc-700 text-zinc-300 px-2 py-1 rounded-sm">
                          Brand name required
                        </span>
                      </div>
                    )}

                    {/* Expand/collapse chevron */}
                    <div className="ml-2">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className={`h-4 w-4 text-zinc-400 transition-transform ${
                          expandedItemId === item.id ? "rotate-180" : ""
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
                    </div>
                  </div>

                  {/* Remove button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveMediaItem(item.id);
                    }}
                    className="ml-3 p-1.5 text-zinc-400 hover:text-white rounded-full hover:bg-zinc-700"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-3.5 w-3.5"
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

                {/* Brand name input when expanded */}
                {expandedItemId === item.id && (
                  <div className="p-3 border-t border-zinc-700 bg-zinc-800/80 animate-in slide-in-from-top-2 duration-200">
                    <div className="flex flex-col space-y-1">
                      <label
                        htmlFor={`brand-name-${item.id}`}
                        className="block text-xs font-medium text-zinc-400"
                      >
                        Brand Name (required)
                      </label>
                      <input
                        id={`brand-name-${item.id}`}
                        type="text"
                        value={item.brandName}
                        onChange={(e) =>
                          updateBrandName(item.id, e.target.value)
                        }
                        placeholder="Enter brand name (e.g., Coca-Cola, Nike)"
                        className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200 text-sm"
                        autoFocus
                        required
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Add more files button */}
          <div className="pb-2">
            <div className="flex flex-col items-center p-3 border border-dashed border-zinc-700 rounded-lg bg-zinc-900/50 hover:bg-zinc-800/30 transition-colors cursor-pointer">
              <FileUpload
                onFileSelect={handleFileSelect}
                multiple={true}
                acceptedFileTypes={[
                  "image/jpeg",
                  "image/png",
                  "image/gif",
                  "video/mp4",
                  "video/webm",
                  "video/quicktime",
                ]}
                className="w-full"
              />
              <div className="text-xs text-zinc-400 mt-2">Add more files</div>
            </div>
          </div>

          {/* Process button */}
          <div className="flex justify-end mt-4">
            <Button
              onClick={() => onStartProcessing(mediaItems)}
              disabled={!canStartProcessing || isProcessing}
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? (
                <div className="flex items-center">
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
                  Processing...
                </div>
              ) : (
                `Check Compliance (${mediaItems.length} file${
                  mediaItems.length > 1 ? "s" : ""
                })`
              )}
            </Button>
          </div>
        </div>
      ) : (
        /* Upload area - simplified and more compact */
        <FileUpload
          onFileSelect={handleFileSelect}
          multiple={true}
          acceptedFileTypes={[
            "image/jpeg",
            "image/png",
            "image/gif",
            "video/mp4",
            "video/webm",
            "video/quicktime",
          ]}
          className="w-full"
        />
      )}
    </div>
  );
};

export default MultiFileUpload;
