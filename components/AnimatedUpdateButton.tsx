'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { RotateCw, Check } from 'lucide-react'

interface AnimatedUpdateButtonProps {
  onClick: () => void
}

export function AnimatedUpdateButton({ onClick }: AnimatedUpdateButtonProps) {
  const [isUpdating, setIsUpdating] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  useEffect(() => {
    if (isUpdating) {
      const timer = setTimeout(() => {
        setIsUpdating(false)
        setShowSuccess(true)
      }, 2000) // Simulate a 2-second update process

      return () => clearTimeout(timer)
    }
  }, [isUpdating])

  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => {
        setShowSuccess(false)
      }, 3000) // Show success message for 3 seconds

      return () => clearTimeout(timer)
    }
  }, [showSuccess])

  const handleClick = () => {
    setIsUpdating(true)
    onClick()
  }

  return (
    <div className="relative">
      <Button
        onClick={handleClick}
        disabled={isUpdating}
        className={`w-full sm:w-auto ${isUpdating ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {isUpdating ? (
          <RotateCw className="w-4 h-4 mr-2 animate-spin" />
        ) : (
          'Update'
        )}
      </Button>
      {showSuccess && (
        <div className="absolute left-0 -top-8 flex items-center text-green-600 font-medium">
          <Check className="w-4 h-4 mr-1" />
          Settings Saved
        </div>
      )}
    </div>
  )
}
