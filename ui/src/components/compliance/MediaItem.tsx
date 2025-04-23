import React from 'react';
import { Button } from '@/components/ui/button';

export interface MediaItemProps {
  id: string;
  file: File;
  preview: string;
  isVideo: boolean;
  brandName: string;
  onBrandNameChange: (id: string, brandName: string) => void;
  onRemove: (id: string) => void;
}

export const MediaItem: React.FC<MediaItemProps> = ({
  id,
  file,
  preview,
  isVideo,
  brandName,
  onBrandNameChange,
  onRemove
}) => {
  return (
    <div className="border border-zinc-700 rounded-lg overflow-hidden shadow-lg shadow-black/20 hover-lift">
      <div className="aspect-video bg-zinc-900 flex items-center justify-center overflow-hidden">
        {isVideo ? (
          <video src={preview} controls className="w-full h-auto" />
        ) : (
          <img
            src={preview}
            alt={file.name}
            className="w-full h-auto object-contain"
          />
        )}
      </div>
      <div className="p-3 bg-zinc-800 flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <div>
            <p className="text-sm font-medium truncate max-w-[200px] text-white">
              {file.name}
            </p>
            <p className="text-xs text-zinc-400">
              {(file.size / (1024 * 1024)).toFixed(2)} MB
            </p>
          </div>
          <Button
            onClick={() => onRemove(id)}
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 rounded-full hover:bg-zinc-700 transition-all duration-200"
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
          </Button>
        </div>
        
        {/* Brand Name Input */}
        <div className="w-full">
          <label
            htmlFor={`brandName-${id}`}
            className="block text-xs font-medium text-zinc-400 mb-1"
          >
            Brand Name (required)
          </label>
          <input
            id={`brandName-${id}`}
            type="text"
            value={brandName}
            onChange={(e) => onBrandNameChange(id, e.target.value)}
            placeholder="Enter brand name (e.g., Coca-Cola, Nike)"
            className="w-full px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-md text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200"
            required
          />
        </div>
      </div>
    </div>
  );
};

export default MediaItem;
