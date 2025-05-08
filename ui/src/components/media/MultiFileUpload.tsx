import React, { useState } from "react";
import { FileUpload } from "@/components/ui/file-upload";
import { MediaItem } from "./MediaItem";
import { Button } from "@/components/ui/button";

export interface MediaFile {
  id: string;
  file: File;
  preview: string;
  isVideo: boolean;
  brandName: string;
}

interface MultiFileUploadProps {
  onFilesReady: (files: MediaFile[]) => void;
}

export const MultiFileUpload: React.FC<MultiFileUploadProps> = ({
  onFilesReady,
}) => {
  const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([]);

  const handleFileSelect = (file: File) => {
    // Check if file already exists in the list
    if (
      mediaFiles.some(
        (item) => item.file.name === file.name && item.file.size === file.size
      )
    ) {
      // Show a notification or alert that the file is already added
      console.log("File already added");
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onload = () => {
      const isVideoFile = file.type.startsWith("video/");

      // Create new media file item
      const newMediaFile: MediaFile = {
        id: `${file.name}-${Date.now()}`,
        file,
        preview: reader.result as string,
        isVideo: isVideoFile,
        brandName: "",
      };

      // Add to list
      setMediaFiles((prev) => [...prev, newMediaFile]);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveFile = (id: string) => {
    setMediaFiles((prev) => prev.filter((file) => file.id !== id));
  };

  const handleBrandNameChange = (id: string, brandName: string) => {
    setMediaFiles((prev) =>
      prev.map((file) => (file.id === id ? { ...file, brandName } : file))
    );
  };

  const handleSubmit = () => {
    // Validate that all files have brand names
    const allValid = mediaFiles.every((file) => file.brandName.trim() !== "");

    if (!allValid) {
      // Show error message
      console.error("Please provide brand names for all files");
      return;
    }

    // Submit files for processing
    onFilesReady(mediaFiles);
  };

  return (
    <div className="flex flex-col space-y-6">
      <FileUpload
        onFileSelect={handleFileSelect}
        maxSize={100}
        acceptedFileTypes={[
          "image/jpeg",
          "image/png",
          "image/gif",
          "image/webp",
          "video/mp4",
          "video/webm",
          "video/quicktime",
        ]}
        multiple={true}
        className="w-full"
      />

      {mediaFiles.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-md font-medium text-white">
            Uploaded Files ({mediaFiles.length})
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {mediaFiles.map((mediaFile) => (
              <MediaItem
                key={mediaFile.id}
                file={mediaFile.file}
                preview={mediaFile.preview}
                isVideo={mediaFile.isVideo}
                brandName={mediaFile.brandName}
                onBrandNameChange={(brandName) =>
                  handleBrandNameChange(mediaFile.id, brandName)
                }
                onRemove={() => handleRemoveFile(mediaFile.id)}
              />
            ))}
          </div>

          <Button
            onClick={handleSubmit}
            disabled={
              mediaFiles.length === 0 ||
              !mediaFiles.every((file) => file.brandName.trim() !== "")
            }
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white transition-all duration-200 disabled:opacity-50 disabled:pointer-events-none shadow-lg shadow-indigo-900/30 hover:shadow-xl hover:shadow-indigo-900/40 hover:translate-y-[-1px] press-effect mt-4"
          >
            Check Compliance for All Files
          </Button>
        </div>
      )}
    </div>
  );
};
