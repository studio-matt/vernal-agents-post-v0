"use client"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { User } from "lucide-react"

interface PersonalityConfirmationModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  personalityName: string
}

export function PersonalityConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  personalityName,
}: PersonalityConfirmationModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Confirm Personality Selection</DialogTitle>
          <DialogDescription>
            You are about to use the "{personalityName}" personality for content generation.
          </DialogDescription>
        </DialogHeader>
        <div className="flex items-center space-x-2 py-4">
          <div className="rounded-full bg-gray-100 p-2">
            <User className="h-6 w-6 text-gray-600" />
          </div>
          <div>
            <p className="font-medium">{personalityName}</p>
            <p className="text-sm text-gray-500">
              This personality will be used for all new content generation until changed.
            </p>
          </div>
        </div>
        <DialogFooter className="sm:justify-between">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onConfirm} className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">
            Confirm Selection
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
