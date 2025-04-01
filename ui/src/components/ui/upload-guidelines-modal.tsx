import { useState } from "react";
import { FileUpload } from "./file-upload";
import { Button } from "./button";
import { uploadBrandGuideline } from "@/services/brandGuidelinesService";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./dialog";

interface UploadGuidelinesModalProps {
  onUploadComplete?: () => void;
  authToken: string | null;
}

interface PdfUpload {
  file: File;
  brandName: string;
  description?: string;
  status: "pending" | "uploading" | "completed" | "error";
  progress: number;
  error?: string;
  estimatedTime?: string;
}

// Function to format time
const formatTime = (seconds: number): string => {
  if (seconds < 60) return `${Math.round(seconds)} seconds`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes} minute${
    minutes > 1 ? "s" : ""
  } ${remainingSeconds} seconds`;
};

export function UploadGuidelinesModal({
  onUploadComplete,
  authToken,
}: UploadGuidelinesModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [pdfs, setPdfs] = useState<PdfUpload[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const handleFileSelect = async (file: File) => {
    const fileSizeMB = file.size / (1024 * 1024);
    const estimatedTime = formatTime(fileSizeMB * 6); // 3 seconds per MB
    setPdfs((prev) => [
      ...prev,
      {
        file,
        brandName: "",
        status: "pending",
        progress: 0,
        estimatedTime,
      },
    ]);
  };

  const handleRemovePdf = (index: number) => {
    setPdfs((prev) => prev.filter((_, i) => i !== index));
  };

  const handleBrandNameChange = (index: number, value: string) => {
    setPdfs((prev) =>
      prev.map((pdf, i) => (i === index ? { ...pdf, brandName: value } : pdf))
    );
  };

  const handleDescriptionChange = (index: number, value: string) => {
    setPdfs((prev) =>
      prev.map((pdf, i) => (i === index ? { ...pdf, description: value } : pdf))
    );
  };

  const uploadPdf = async (pdf: PdfUpload, index: number) => {
    if (!authToken) {
      throw new Error("No authentication token found");
      return;
    }
    setPdfs((prev) =>
      prev.map((p, i) =>
        i === index ? { ...p, status: "uploading", progress: 0 } : p
      )
    );

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setPdfs((prev) =>
          prev.map((p, i) =>
            i === index
              ? {
                  ...p,
                  progress: p.progress >= 90 ? 90 : p.progress + 10,
                }
              : p
          )
        );
      }, 500);

      await uploadBrandGuideline(
        pdf.file,
        pdf.brandName,
        authToken,
        pdf.description
      );

      clearInterval(progressInterval);
      setPdfs((prev) =>
        prev.map((p, i) =>
          i === index ? { ...p, status: "completed", progress: 100 } : p
        )
      );
    } catch (err) {
      setPdfs((prev) =>
        prev.map((p, i) =>
          i === index
            ? {
                ...p,
                status: "error",
                error: err instanceof Error ? err.message : "Failed to upload",
              }
            : p
        )
      );
    }
  };

  const handleUploadAll = async () => {
    if (!pdfs.every((pdf) => pdf.brandName.trim())) {
      setPdfs((prev) =>
        prev.map((pdf) => ({
          ...pdf,
          error: !pdf.brandName.trim() ? "Brand name is required" : undefined,
        }))
      );
      return;
    }

    setIsUploading(true);

    for (let i = 0; i < pdfs.length; i++) {
      if (pdfs[i].status !== "completed") {
        await uploadPdf(pdfs[i], i);
      }
    }

    setIsUploading(false);
    onUploadComplete?.();

    // Close modal if all uploads are successful
    if (pdfs.every((pdf) => pdf.status === "completed")) {
      setIsOpen(false);
      setPdfs([]);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="border-zinc-700 hover:bg-zinc-800">
          Upload Brand Guidelines
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px] bg-zinc-900 border border-zinc-800 p-0">
        <div className="flex flex-col h-[85vh]">
          <DialogHeader className="flex-shrink-0 p-6 pb-4 border-b border-zinc-800">
            <DialogTitle className="text-lg font-semibold text-white">
              Upload Brand Guidelines
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* File Upload Area */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-200">
                Add PDF Files
              </label>
              <FileUpload
                onFileSelect={handleFileSelect}
                maxSize={1024} // 1GB
                acceptedFileTypes={["application/pdf"]}
                multiple={true}
              />
            </div>

            {/* PDF List */}
            {pdfs.length > 0 && (
              <div className="space-y-4 mt-6">
                <div className="text-sm font-medium text-zinc-200">
                  PDF Files ({pdfs.length})
                </div>
                <div className="space-y-4">
                  {pdfs.map((pdf, index) => (
                    <div
                      key={index}
                      className="p-4 bg-zinc-800/50 border border-zinc-700 rounded-lg space-y-4"
                    >
                      {/* PDF Info */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-zinc-700 rounded flex items-center justify-center">
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              className="h-4 w-4 text-zinc-300"
                              viewBox="0 0 20 20"
                              fill="currentColor"
                            >
                              <path
                                fillRule="evenodd"
                                d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                                clipRule="evenodd"
                              />
                            </svg>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white truncate max-w-[200px]">
                              {pdf.file.name}
                            </p>
                            <div className="text-xs text-zinc-400">
                              {(pdf.file.size / (1024 * 1024)).toFixed(2)} MB
                            </div>
                          </div>
                        </div>
                        {pdf.status === "pending" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-zinc-400 hover:text-white"
                            onClick={() => handleRemovePdf(index)}
                          >
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              className="h-4 w-4"
                              viewBox="0 0 20 20"
                              fill="currentColor"
                            >
                              <path
                                fillRule="evenodd"
                                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                                clipRule="evenodd"
                              />
                            </svg>
                          </Button>
                        )}
                      </div>

                      {/* Form Fields */}
                      <div className="space-y-3">
                        <div>
                          <input
                            type="text"
                            value={pdf.brandName}
                            onChange={(e) =>
                              handleBrandNameChange(index, e.target.value)
                            }
                            placeholder="Enter brand name"
                            className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                            disabled={pdf.status !== "pending"}
                          />
                          {pdf.error && (
                            <p className="text-xs text-red-400 mt-1">
                              {pdf.error}
                            </p>
                          )}
                        </div>
                        <textarea
                          value={pdf.description}
                          onChange={(e) =>
                            handleDescriptionChange(index, e.target.value)
                          }
                          placeholder="Description (optional)"
                          rows={2}
                          className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                          disabled={pdf.status !== "pending"}
                        />
                      </div>

                      {/* Upload Progress */}
                      {pdf.status === "uploading" && (
                        <div className="space-y-2">
                          <div className="space-y-1">
                            <div className="text-sm text-zinc-400">
                              Uploading... {pdf.progress}%
                            </div>
                            <div className="text-xs text-zinc-500">
                              Estimated time remaining:{" "}
                              {formatTime(
                                (pdf.file.size / (1024 * 1024)) *
                                  3 *
                                  (1 - pdf.progress / 100)
                              )}
                            </div>
                          </div>
                          <div className="w-full bg-zinc-800 rounded-full h-1">
                            <div
                              className="bg-indigo-600 h-1 rounded-full transition-all duration-300"
                              style={{ width: `${pdf.progress}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Status Indicators */}
                      {pdf.status === "completed" && (
                        <div className="flex items-center gap-2 text-sm text-green-400">
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="h-4 w-4"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                          >
                            <path
                              fillRule="evenodd"
                              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                              clipRule="evenodd"
                            />
                          </svg>
                          Upload complete
                        </div>
                      )}

                      {pdf.status === "error" && (
                        <div className="text-sm text-red-400 bg-red-950/50 border border-red-900/50 p-2 rounded">
                          {pdf.error}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Actions - Fixed at bottom */}
          <div className="flex justify-end gap-3 p-6 border-t border-zinc-800 flex-shrink-0 bg-zinc-900/50 backdrop-blur-sm">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setIsOpen(false);
                setPdfs([]);
              }}
              disabled={isUploading}
              className="border-zinc-700 hover:bg-zinc-800 text-white"
            >
              Cancel
            </Button>
            <Button
              onClick={handleUploadAll}
              disabled={isUploading || pdfs.length === 0}
              className="bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              {isUploading ? "Uploading..." : "Upload All"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
