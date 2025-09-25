'use client'

import * as React from 'react'
import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { RotateCw, Check, Copy } from 'lucide-react'

interface DuplicateScheduleButtonProps {
  onClick: () => void
}

export const DuplicateScheduleButton = React.forwardRef<
  HTMLButtonElement,
  DuplicateScheduleButtonProps
>(({ onClick }, ref) => {
  const [isDuplicating, setIsDuplicating] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  useEffect(() => {
    if (isDuplicating) {
      const timer = setTimeout(() => {
        setIsDuplicating(false)
        setShowSuccess(true)
      }, 2000) // Simulate a 2-second duplication process

      return () => clearTimeout(timer)
    }
  }, [isDuplicating])

  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => {
        setShowSuccess(false)
      }, 3000) // Show success message for 3 seconds

      return () => clearTimeout(timer)
    }
  }, [showSuccess])

  const handleClick = () => {
    setIsDuplicating(true)
    onClick()
  }

  return (
    <div className="relative">
      <Button
        ref={ref}
        onClick={handleClick}
        disabled={isDuplicating}
        className={`w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90 ${isDuplicating ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {isDuplicating ? (
          <RotateCw className="w-4 h-4 mr-2 animate-spin" />
        ) : (
          <Copy className="w-4 h-4 mr-2" />
        )}
        Duplicate Schedule to All Other Days
      </Button>
      {showSuccess && (
        <div className="absolute left-0 -bottom-8 flex items-center text-green-600 font-medium">
          <Check className="w-4 h-4 mr-1" />
          Schedule Copied
        </div>
      )}
    </div>
  )
})

DuplicateScheduleButton.displayName = 'DuplicateScheduleButton'



// MLLM code:
// "use client";

// import * as React from "react";
// import { useState, useEffect } from "react";
// import { Button } from "@/components/ui/button";
// import { RotateCw, Check, Copy } from "lucide-react";

// interface DuplicateScheduleButtonProps {
//   onClick: () => void;
// }

// export const DuplicateScheduleButton = React.forwardRef<
//   HTMLButtonElement,
//   DuplicateScheduleButtonProps
// >(({ onClick }, ref) => {
//   const [isDuplicating, setIsDuplicating] = useState(false);
//   const [showSuccess, setShowSuccess] = useState(false);

//   useEffect(() => {
//     if (isDuplicating) {
//       const timer = setTimeout(() => {
//         setIsDuplicating(false);
//         setShowSuccess(true);
//       }, 2000);

//       return () => clearTimeout(timer);
//     }
//   }, [isDuplicating]);

//   useEffect(() => {
//     if (showSuccess) {
//       const timer = setTimeout(() => {
//         setShowSuccess(false);
//       }, 3000);

//       return () => clearTimeout(timer);
//     }
//   }, [showSuccess]);

//   const handleClick = () => {
//     setIsDuplicating(true);
//     onClick();
//   };

//   return (
//     <div className="relative">
//       <Button
//         ref={ref}
//         onClick={handleClick}
//         disabled={isDuplicating}
//         className={`w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90 ${
//           isDuplicating ? "opacity-50 cursor-not-allowed" : ""
//         }`}
//       >
//         {isDuplicating ? (
//           <RotateCw className="w-4 h-4 mr-2 animate-spin" />
//         ) : (
//           <Copy className="w-4 h-4 mr-2" />
//         )}
//         Duplicate Schedule to All Other Days
//       </Button>
//       {showSuccess && (
//         <div className="absolute left-0 -bottom-8 flex items-center text-green-600 font-medium">
//           <Check className="w-4 h-4 mr-1" />
//           Schedule Copied
//         </div>
//       )}
//     </div>
//   );
// });

// DuplicateScheduleButton.displayName = "DuplicateScheduleButton";
