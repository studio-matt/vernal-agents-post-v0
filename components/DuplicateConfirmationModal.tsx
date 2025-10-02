import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

interface DuplicateConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  sourceDay: string;
  sourceCount: number;
  targetCounts: { [key: string]: number };
}

export function DuplicateConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  sourceDay,
  sourceCount,
  targetCounts
}: DuplicateConfirmationModalProps) {
  const targetDaysWithMoreSlots = Object.entries(targetCounts)
    .filter(([_, count]) => count > sourceCount)
    .map(([day, count]) => `${day} (${count} slots)`)
    .join(', ');

  return (
    <AlertDialog open={isOpen} onOpenChange={onClose}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Confirm Schedule Duplication</AlertDialogTitle>
          <AlertDialogDescription>
            You are about to duplicate the schedule from {sourceDay} ({sourceCount} slots) to other days.
            The following days have more slots than the source day:
            {targetDaysWithMoreSlots}
            
            Do you want to override these days with the schedule from {sourceDay}?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onClose}>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>Confirm Duplication</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
