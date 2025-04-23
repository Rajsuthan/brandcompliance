import React from 'react';
import MediaItem from './MediaItem';

export interface MediaFile {
  id: string;
  file: File;
  preview: string;
  isVideo: boolean;
  brandName: string;
}

interface MediaGridProps {
  mediaItems: MediaFile[];
  onBrandNameChange: (id: string, brandName: string) => void;
  onRemoveItem: (id: string) => void;
}

export const MediaGrid: React.FC<MediaGridProps> = ({ 
  mediaItems, 
  onBrandNameChange, 
  onRemoveItem 
}) => {
  if (mediaItems.length === 0) {
    return null;
  }

  return (
    <div className="w-full">
      <h3 className="text-md font-medium text-white mb-3">Uploaded Files ({mediaItems.length})</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {mediaItems.map((item) => (
          <MediaItem
            key={item.id}
            id={item.id}
            file={item.file}
            preview={item.preview}
            isVideo={item.isVideo}
            brandName={item.brandName}
            onBrandNameChange={onBrandNameChange}
            onRemove={onRemoveItem}
          />
        ))}
      </div>
    </div>
  );
};

export default MediaGrid;
