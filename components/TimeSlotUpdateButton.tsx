'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { RotateCw, Check } from 'lucide-react'

interface TimeSlotUpdateButtonProps {
  onClick: () => void
}

export function TimeSlotUpdateButton({ onClick }: TimeSlotUpdateButtonProps) {
  const [isUpdating, setIsUpdating] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  useEffect(() => {
    if (isUpdating) {
      const timer = setTimeout(() => {
        setIsUpdating(false)
        setShowSuccess(true)
      }, 2000)

      return () => clearTimeout(timer)
    }
  }, [isUpdating])

  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => {
        setShowSuccess(false)
      }, 3000)

      return () => clearTimeout(timer)
    }
  }, [showSuccess])

  const handleClick = () => {
    setIsUpdating(true)
    onClick()
  }

  return (
    <Button
      onClick={handleClick}
      disabled={isUpdating}
      size="sm"
      className={`${isUpdating ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {isUpdating ? (
        <RotateCw className="w-4 h-4 animate-spin" />
      ) : (
        'Update'
      )}
    </Button>
  )
}
