'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { RotateCw, Check } from 'lucide-react'

interface GeneratePlanButtonProps {
  onClick: () => void
}

export function GeneratePlanButton({ onClick }: GeneratePlanButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  useEffect(() => {
    if (isGenerating) {
      const timer = setTimeout(() => {
        setIsGenerating(false)
        setShowSuccess(true)
      }, 2000)

      return () => clearTimeout(timer)
    }
  }, [isGenerating])

  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => {
        setShowSuccess(false)
      }, 3000)

      return () => clearTimeout(timer)
    }
  }, [showSuccess])

  const handleClick = () => {
    setIsGenerating(true)
    onClick()
  }

  return (
    <div className="relative">
      <Button
        onClick={handleClick}
        disabled={isGenerating}
        className={`w-full generate-plan-button bg-[#3d545f] text-white hover:bg-[#3d545f]/90 ${isGenerating ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {isGenerating ? (
          <RotateCw className="w-4 h-4 mr-2 animate-spin" />
        ) : (
          'Generate Plan'
        )}
      </Button>
      {showSuccess && (
        <div className="absolute left-0 -top-8 flex items-center text-green-600 font-medium">
          <Check className="w-4 h-4 mr-1" />
          Plan Created
        </div>
      )}
    </div>
  )
}
