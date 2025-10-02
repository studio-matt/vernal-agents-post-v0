import Link from "next/link"
import { Info } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ContentAnalysisLinkProps {
  sectionId?: string
  buttonText?: string
  variant?: "default" | "outline" | "ghost" | "link"
  size?: "default" | "sm" | "lg" | "icon"
  showIcon?: boolean
}

export function ContentAnalysisLink({
  sectionId = "",
  buttonText = "Learn More",
  variant = "outline",
  size = "sm",
  showIcon = true,
}: ContentAnalysisLinkProps) {
  const href = `/dashboard?tab=content-planner${sectionId ? `#${sectionId}` : ""}`

  return (
    <Link href={href}>
      <Button variant={variant} size={size} className="flex items-center">
        {showIcon && <Info className="w-4 h-4 mr-2" />}
        {buttonText}
      </Button>
    </Link>
  )
}
