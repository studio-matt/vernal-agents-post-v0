"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { UserCircle, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { usePathname } from "next/navigation"

export function Header() {
  const router = useRouter()
  const [username, setUsername] = useState<string | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const pathname = usePathname()
  const hideHeader = pathname.startsWith("/dashboard/campaigns/edit/")

  useEffect(() => {
    const token = localStorage.getItem("token")
    const storedUsername = localStorage.getItem("username")

    if (token) {
      setIsLoggedIn(true)
      setUsername(storedUsername || null)
    } else {
      setIsLoggedIn(false)
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem("token")
    localStorage.removeItem("email")
    localStorage.removeItem("username")
    setIsLoggedIn(false)
    setUsername(null)
    router.push("/")
  }

  // Correct conditional return syntax:
  if (hideHeader) {
    return null // don't render header
  }

  return (
    <header className="flex items-center justify-between p-4 bg-white border-b">
      <div className="flex items-center space-x-4">
        <Link href="/" className="text-2xl font-bold">
          Logo
        </Link>
        {isLoggedIn && (
          <nav>
            <ul className="flex space-x-6">
              <li>
                <Link
                  href="/dashboard/content-planner"
                  className={`text-gray-600 hover:text-gray-900 font-medium ${
                    pathname.startsWith("/dashboard/content-planner") ? "text-gray-900 border-b-2 border-gray-900" : ""
                  }`}
                >
                  Content Planner
                </Link>
              </li>
              <li>
                <Link
                  href="/dashboard/author-planning"
                  className={`text-gray-600 hover:text-gray-900 font-medium ${
                    pathname.startsWith("/dashboard/author-planning") ? "text-gray-900 border-b-2 border-gray-900" : ""
                  }`}
                >
                  Author Planning
                </Link>
              </li>
              <li>
                <Link
                  href="/dashboard/podcast-tools"
                  className={`text-gray-600 hover:text-gray-900 font-medium ${
                    pathname.startsWith("/dashboard/podcast-tools") ? "text-gray-900 border-b-2 border-gray-900" : ""
                  }`}
                >
                  Podcast Tools
                </Link>
              </li>
              <li>
                <Link href="/post" className="text-gray-600 hover:text-gray-900">
                  View Scheduled Post
                </Link>
              </li>
            </ul>
          </nav>
        )}
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="flex items-center gap-1">
            <UserCircle className="h-5 w-5" />
            <span>{isLoggedIn && username ? username : "Login"}</span>
            <ChevronDown className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {isLoggedIn ? (
            <>
              <DropdownMenuItem>
                <Link href="/account-settings" className="w-full">
                  My Account Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleLogout}>Logout</DropdownMenuItem>
            </>
          ) : (
            <DropdownMenuItem>
              <Link href="/" className="w-full">
                Login
              </Link>
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
