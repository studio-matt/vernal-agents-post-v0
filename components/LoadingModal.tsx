import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

interface LoadingModalProps {
  isOpen: boolean;
  title: string;
  progress?: number;
}

export const LoadingModal: React.FC<LoadingModalProps> = ({ 
  isOpen, 
  title, 
  progress 
}) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!isOpen || !mounted) return null;

  const modalContent = (
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70"
      style={{ 
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100vw',
        height: '100vh'
      }}
    >
      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-2xl p-8 max-w-sm w-full mx-4 border border-gray-200">
        <div className="flex flex-col items-center space-y-4">
          {/* Spinning circle */}
          <div className="relative">
            <svg
              className="animate-spin h-12 w-12 text-[#3d545f]"
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
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          </div>
          
          {/* Title */}
          <h3 className="text-lg font-medium text-gray-900 text-center">
            {title}
          </h3>
          
          {/* Progress bar if progress is provided */}
          {progress !== undefined && (
            <div className="w-full space-y-2">
              <div className="flex justify-between text-sm text-gray-600">
                <span>Progress</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-[#3d545f] h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // Use portal to render modal outside the normal DOM hierarchy
  return createPortal(modalContent, document.body);
};
