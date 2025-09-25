import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface WeekNavigationProps {
  currentWeek: number
  totalWeeks: number
  onWeekChange: (week: number) => void
}

export function WeekNavigation({ currentWeek, totalWeeks, onWeekChange }: WeekNavigationProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <Button
        variant="outline"
        size="sm"
        onClick={() => onWeekChange(currentWeek - 1)}
        disabled={currentWeek === 1}
      >
        <ChevronLeft className="h-4 w-4 mr-2" />
        Previous Week
      </Button>
      <Select value={currentWeek.toString()} onValueChange={(value) => onWeekChange(parseInt(value))}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder={`Week ${currentWeek} of ${totalWeeks}`} />
        </SelectTrigger>
        <SelectContent>
          {Array.from({ length: totalWeeks }, (_, i) => i + 1).map((week) => (
            <SelectItem key={week} value={week.toString()}>
              Week {week} of {totalWeeks}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button
        variant="outline"
        size="sm"
        onClick={() => onWeekChange(currentWeek + 1)}
        disabled={currentWeek === totalWeeks}
      >
        Next Week
        <ChevronRight className="h-4 w-4 ml-2" />
      </Button>
    </div>
  )
}
