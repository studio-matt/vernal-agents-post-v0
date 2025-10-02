"use client"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { AlertCircle } from "lucide-react"

interface ErrorDialogProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  message: string
}

export function ErrorDialog({ isOpen, onClose, title = "Error", message }: ErrorDialogProps) {
  return (
    <AlertDialog open={isOpen} onOpenChange={onClose}>
      <AlertDialogContent className="bg-white border-red-200 border-2">
        <AlertDialogHeader className="flex flex-row items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <AlertDialogTitle className="text-red-600">{title}</AlertDialogTitle>
        </AlertDialogHeader>
        <AlertDialogDescription className="text-gray-700">{message}</AlertDialogDescription>
        <AlertDialogFooter>
          <AlertDialogAction className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90" onClick={onClose}>
            OK
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
