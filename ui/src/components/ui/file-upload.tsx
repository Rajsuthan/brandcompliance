import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface FileUploadProps extends React.HTMLAttributes<HTMLDivElement> {
  onFileSelect?: (file: File) => void;
  maxSize?: number; // in MB
  acceptedFileTypes?: string[];
  multiple?: boolean;
}

export function FileUpload({
  className,
  onFileSelect,
  maxSize = 100, // Default 100MB
  acceptedFileTypes = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "video/mp4",
    "video/webm",
    "video/quicktime",
  ],
  multiple = false,
  ...props
}: FileUploadProps) {
  const [isDragging, setIsDragging] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const validateFile = (file: File): boolean => {
    // Check file type
    if (
      acceptedFileTypes.length > 0 &&
      !acceptedFileTypes.includes(file.type)
    ) {
      setError(
        `File type not supported. Please upload: ${acceptedFileTypes
          .map((type) => type.split("/")[1])
          .join(", ")}`
      );
      return false;
    }

    // Check file size
    if (file.size > maxSize * 1024 * 1024) {
      setError(`File size exceeds ${maxSize}MB limit`);
      return false;
    }

    setError(null);
    return true;
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files);
    }
  };

  const processFiles = (fileList: FileList) => {
    // Convert FileList to array for easier processing
    const files = Array.from(fileList);

    // If not multiple, just take the first file
    const filesToProcess = multiple ? files : [files[0]];

    filesToProcess.forEach((file) => {
      if (validateFile(file) && onFileSelect) {
        onFileSelect(file);
      }
    });
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files);
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center w-full",
        className
      )}
      {...props}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        accept={acceptedFileTypes.join(",")}
        multiple={multiple}
        className="hidden"
      />

      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={cn(
          "relative flex flex-col items-center justify-center w-full min-h-[300px] border-2 border-dashed rounded-xl p-6 transition-all duration-300 ease-in-out",
          isDragging
            ? "border-primary bg-primary/5 scale-[1.02]"
            : "border-border hover:border-primary/50 hover:bg-accent/5",
          "group animate-in fade-in duration-500"
        )}
      >
        <div className="flex flex-col items-center justify-center gap-4 text-center">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 text-primary animate-in zoom-in-50 duration-500 delay-200">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-8 h-8"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
              />
            </svg>
          </div>
          <div className="animate-in fade-in-50 slide-in-from-bottom-4 duration-500 delay-300">
            <h3 className="text-lg font-semibold">
              Drag & Drop {multiple ? "your files" : "your file"} here
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              or click to browse files
            </p>
          </div>
          <div className="flex gap-2 animate-in fade-in-50 slide-in-from-bottom-4 duration-500 delay-400">
            <Button onClick={handleButtonClick}>Select Image or Video</Button>
          </div>
          <p className="text-xs text-muted-foreground mt-4 animate-in fade-in-50 slide-in-from-bottom-4 duration-500 delay-500">
            Supported formats:{" "}
            {acceptedFileTypes.map((type) => type.split("/")[1]).join(", ")}
            <br />
            Max size: {maxSize}MB {multiple && "per file"}
          </p>
        </div>

        {/* Animated border effect */}
        <div className="absolute inset-0 rounded-xl overflow-hidden pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500">
          <div className="absolute inset-0 bg-gradient-to-r from-primary/30 via-primary/10 to-primary/30 animate-gradient-x"></div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-4 flex items-center gap-2 text-sm text-destructive animate-in fade-in slide-in-from-bottom-2 duration-300 bg-destructive/10 p-3 rounded-lg">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-5 h-5 flex-shrink-0"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
