"use client"

import type React from "react"

import { 
  deletePostById,
  generateImageMachineContent,
  getScheduledPosts,
  regenerateContentAPI,
  scheduleTime,
} from "@/components/Service"
import { toast } from "sonner"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Header } from "@/components/Header" // Added Header component import
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuTrigger 
} from "@/components/ui/dropdown-menu"
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
import { 
  Grid3X3, 
  List, 
  Filter, 
  Trash2, 
  Calendar,
  Instagram,
  Facebook,
  Youtube,
  Twitter,
  Linkedin,
  Music
} from "lucide-react"

interface Post {
  id: number
  topic: string
  title: string
  content: string
  day: string
  platform: string
  schedule_time: string
  image: string
  image_url?: string
}

// Platform definitions with icons
const PLATFORMS = [
  { name: "Instagram", icon: Instagram },
  { name: "Facebook", icon: Facebook },
  { name: "YouTube", icon: Youtube },
  { name: "Twitter", icon: Twitter },
  { name: "LinkedIn", icon: Linkedin },
  { name: "TikTok", icon: Music },
]

export default function Menu1Page() {
  const [scheduledPosts, setScheduledPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [globalLoading, setGlobalLoading] = useState(false) // New global loading state
  const [actionLoading, setActionLoading] = useState<{
    [key: number]: { regenerateContent?: boolean; regenerateImage?: boolean; delete?: boolean; scheduleTime?: boolean }
  }>({})
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [currentPostId, setCurrentPostId] = useState<number | null>(null)
  const [editedContent, setEditedContent] = useState("")
  const [editedPlatform, setEditedPlatform] = useState("")
  const [isContentModalOpen, setIsContentModalOpen] = useState(false)
  const [modalContent, setModalContent] = useState<string>("")
  const [modalTitle, setModalTitle] = useState<string>("")
  
  // New state for view toggle, selection, and filtering
  const [viewMode, setViewMode] = useState<"list" | "grid">("list")
  const [selectedPosts, setSelectedPosts] = useState<number[]>([])
  const [isBulkDeleteModalOpen, setIsBulkDeleteModalOpen] = useState(false)
  const [deleteProgress, setDeleteProgress] = useState({ current: 0, total: 0 })
  const [filters, setFilters] = useState({
    startDate: "",
    endDate: "",
    platforms: [] as string[]
  })
  const [isFilterOpen, setIsFilterOpen] = useState(false)

  // Helper functions for selection and filtering
  const handleSelectPost = (postId: number, checked: boolean) => {
    if (checked) {
      setSelectedPosts(prev => [...prev, postId])
    } else {
      setSelectedPosts(prev => prev.filter(id => id !== postId))
    }
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedPosts(filteredPosts.map(post => post.id))
    } else {
      setSelectedPosts([])
    }
  }

  const handleBulkDelete = async () => {
    try {
      setGlobalLoading(true)
      setDeleteProgress({ current: 0, total: selectedPosts.length })
      
      const deletedPosts: number[] = []
      const failedDeletions: number[] = []
      
      for (let i = 0; i < selectedPosts.length; i++) {
        const postId = selectedPosts[i]
        try {
          await deletePostById(postId.toString())
          deletedPosts.push(postId)
        } catch (error) {
          console.error(`Error deleting post ${postId}:`, error)
          failedDeletions.push(postId)
        }
        
        setDeleteProgress({ current: i + 1, total: selectedPosts.length })
        
        // Add small delay to show progress
        if (i < selectedPosts.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 100))
        }
      }
      
      // Update the posts list
      setScheduledPosts(prev => prev.filter(post => !deletedPosts.includes(post.id)))
      setSelectedPosts([])
      setIsBulkDeleteModalOpen(false)
      setDeleteProgress({ current: 0, total: 0 })
      
      // Show success/error messages
      if (deletedPosts.length > 0) {
        toast.success(`Successfully deleted ${deletedPosts.length} post${deletedPosts.length > 1 ? 's' : ''}`)
      }
      if (failedDeletions.length > 0) {
        toast.error(`Failed to delete ${failedDeletions.length} post${failedDeletions.length > 1 ? 's' : ''}`)
      }
      
    } catch (error) {
      console.error("Error in bulk delete:", error)
      toast.error("An unexpected error occurred during deletion")
    } finally {
      setGlobalLoading(false)
    }
  }

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const clearFilters = () => {
    setFilters({
      startDate: "",
      endDate: "",
      platforms: []
    })
  }

  // Filter posts based on current filters
  const filteredPosts = (scheduledPosts || []).filter(post => {
    const postDate = new Date(post.schedule_time)
    const startDate = filters.startDate ? new Date(filters.startDate) : null
    const endDate = filters.endDate ? new Date(filters.endDate) : null
    
    // Date filtering
    if (startDate && postDate < startDate) return false
    if (endDate && postDate > endDate) return false
    
    // Platform filtering - make it case insensitive
    if (filters.platforms.length > 0) {
      const postPlatformLower = post.platform.toLowerCase()
      const hasMatchingPlatform = filters.platforms.some(platform => 
        platform.toLowerCase() === postPlatformLower
      )
      if (!hasMatchingPlatform) return false
    }
    
    return true
  })

  const getSchedulePosts = async () => {
    try {
      setLoading(true)
      const response = await getScheduledPosts()
      console.log("response", response)

      if (response.status === "success") {
        setScheduledPosts(response.message.posts)
      } else {
        setError("Failed to fetch posts. Please try again later.")
        console.error("Failed to generate ideas:", response.message)
      }
    } catch (e) {
      setError("An unexpected error occurred.")
      console.error("Error fetching posts:", e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    getSchedulePosts()
  }, [])

  const handleRegenerateImage = async (postId: number, content: string) => {
    try {
      setGlobalLoading(true) // Set global loading to true
      setActionLoading((prev) => ({
        ...prev,
        [postId]: { ...prev[postId], regenerateImage: true },
      }))
      const response = await generateImageMachineContent({
        id: postId.toString(),
        query: content,
      })

      if (response.status === "success") {
        await getSchedulePosts()
      } else {
        console.error("Image regeneration failed:", response.message)
      }
    } catch (e) {
      console.error("Error regenerating image:", e)
      setError("An unexpected error occurred.")
    } finally {
      setGlobalLoading(false) // Set global loading to false
      setActionLoading((prev) => ({
        ...prev,
        [postId]: { ...prev[postId], regenerateImage: false },
      }))
    }
  }

  const handleRegenerateContent = async (postId: number, content: string, platform: string) => {
    try {
      setGlobalLoading(true) // Set global loading to true
      setActionLoading((prev) => ({
        ...prev,
        [postId]: { ...prev[postId], regenerateContent: true },
      }))
      const response = await regenerateContentAPI({
        id: postId.toString(),
        query: content,
        platform,
      })

      if (response.status === "success") {
        await getSchedulePosts()
      } else {
        console.error("Content regeneration failed:", response.message)
      }
    } catch (error) {
      console.error("Error regenerating content:", error)
      setError("Error regenerating content:")
    } finally {
      setGlobalLoading(false) // Set global loading to false
      setActionLoading((prev) => ({
        ...prev,
        [postId]: { ...prev[postId], regenerateContent: false },
      }))
    }
  }

  const handleTimeChange = async (event: React.ChangeEvent<HTMLSelectElement>, content: string) => {
    const newTime = event.target.value
    try {
      setGlobalLoading(true)
      const response = await scheduleTime({ newTime, content })
      if (response) {
        await getSchedulePosts()
      } else {
        console.error("Failed to schedule the time.")
      }
    } catch (error) {
      console.error("Error scheduling time:", error)
      setError("Error scheduling time.")
    } finally {
      setGlobalLoading(false)
    }
  }

  const deletePost = async (postId: number) => {
    try {
      setGlobalLoading(true) // Set global loading to true
      setActionLoading((prev) => ({
        ...prev,
        [postId]: { ...prev[postId], delete: true },
      }))
      const response = await deletePostById(postId.toString())
      if (response.status === "success") {
        await getSchedulePosts()
        toast.success("Post deleted successfully")
      } else {
        console.error("Failed to delete post:", response.message)
        toast.error("Failed to delete post: " + response.message)
      }
    } catch (error) {
      console.error("Error deleting post:", error)
      toast.error("Error deleting post")
    } finally {
      setGlobalLoading(false) // Set global loading to false
      setActionLoading((prev) => ({
        ...prev,
        [postId]: { ...prev[postId], delete: false },
      }))
    }
  }

  // Format schedule_time to a readable format in 24-hour format
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString("en-GB", {
      // "en-GB" uses 24-hour time by default
      weekday: "short", // Display day as a short name (e.g., Mon, Tue)
      hour: "2-digit", // Hour in 2-digit format (24-hour)
      minute: "2-digit", // Minute in 2-digit format
    })
  }

  // Generate time options for the dropdown (hourly slots for the same day)
  const generateTimeOptions = (currentTime: string) => {
    const options = []
    const date = new Date(currentTime)
    const baseDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())

    for (let hour = 0; hour < 24; hour++) {
      const time = new Date(baseDate)
      time.setHours(hour, 0) // Set minutes to 0 for hourly times
      const isoTime = time.toISOString()
      const displayTime = time.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      })
      options.push({ value: isoTime, label: displayTime })
    }
    return options
  }

  const timeOptions: string[] = []
  for (let i = 0; i < 24; i++) {
    // Format time as 00:00, 01:00, ..., 23:00
    const time = i < 10 ? `0${i}:00` : `${i}:00`
    timeOptions.push(time)
  }

  return (
    <>
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-md w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">Edit Content</h2>
            <textarea
              className="w-full h-40 border border-gray-300 rounded-lg p-2 mb-4"
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setIsModalOpen(false)
                  setCurrentPostId(null)
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={() => {
                  if (currentPostId !== null) {
                    handleRegenerateContent(currentPostId, editedContent, editedPlatform)
                  }
                  setIsModalOpen(false)
                  setCurrentPostId(null)
                }}
              >
                Submit
              </Button>
            </div>
          </div>
        </div>
      )}

      {isContentModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-md max-w-lg max-h-[80vh] overflow-auto">
            <h2 className="text-xl font-semibold mb-4">{modalTitle}</h2>
            <p className="whitespace-pre-wrap text-gray-800">{modalContent}</p>
            <div className="flex justify-end mt-6">
              <Button onClick={() => setIsContentModalOpen(false)}>Close</Button>
            </div>
          </div>
        </div>
      )}

      <div className="min-h-screen bg-[#7A99A8]">
        <Header /> {/* Added Header component */}
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <h1 className="text-4xl font-extrabold text-white">Scheduled Posts</h1>

          <Card className="w-full">
            <CardContent className="p-6">
              <div className="space-y-6">
                <div className="flex justify-between items-center">
              
              {/* Controls */}
              <div className="flex items-center gap-3">
                {/* Filter Dropdown */}
                <DropdownMenu open={isFilterOpen} onOpenChange={setIsFilterOpen}>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="bg-white text-gray-700 hover:bg-gray-50">
                      <Filter className="h-4 w-4 mr-2" />
                      Filter
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-80 p-4">
                    <div className="space-y-4">
                      <h3 className="font-semibold text-gray-900">Filter Posts</h3>
                      
                      {/* Date Range */}
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-700">Date Range</label>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="text-xs text-gray-500">Start Date</label>
                            <input
                              type="date"
                              value={filters.startDate}
                              onChange={(e) => handleFilterChange("startDate", e.target.value)}
                              className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-gray-500">End Date</label>
                            <input
                              type="date"
                              value={filters.endDate}
                              onChange={(e) => handleFilterChange("endDate", e.target.value)}
                              className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                            />
                          </div>
                        </div>
                      </div>
                      
                      {/* Platform Filter */}
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-700">Platforms</label>
                        <div className="space-y-2 max-h-32 overflow-y-auto">
                          {PLATFORMS.map((platform) => {
                            const IconComponent = platform.icon
                            return (
                              <label key={platform.name} className="flex items-center space-x-2 cursor-pointer">
                                <Checkbox
                                  checked={filters.platforms.includes(platform.name)}
                                  onCheckedChange={(checked) => {
                                    if (checked) {
                                      handleFilterChange("platforms", [...filters.platforms, platform.name])
                                    } else {
                                      handleFilterChange("platforms", filters.platforms.filter(p => p !== platform.name))
                                    }
                                  }}
                                />
                                <IconComponent className="h-4 w-4" />
                                <span className="text-sm">{platform.name}</span>
                              </label>
                            )
                          })}
                        </div>
                      </div>
                      
                      <div className="flex justify-between pt-2">
                        <Button variant="outline" size="sm" onClick={clearFilters}>
                          Clear
                        </Button>
                        <Button size="sm" onClick={() => setIsFilterOpen(false)}>
                          Apply
                        </Button>
                      </div>
                    </div>
                  </DropdownMenuContent>
                </DropdownMenu>
                
                {/* Bulk Delete Button */}
                {selectedPosts.length >= 2 && (
                  <Button 
                    variant="destructive" 
                    onClick={() => setIsBulkDeleteModalOpen(true)}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete ({selectedPosts.length})
                  </Button>
                )}
                
                {/* View Toggle */}
                <div className="flex border border-gray-300 rounded-lg overflow-hidden">
                  <Button
                    variant={viewMode === "list" ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setViewMode("list")}
                    className="rounded-none"
                  >
                    <List className="h-4 w-4" />
                  </Button>
                  <Button
                    variant={viewMode === "grid" ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setViewMode("grid")}
                    className="rounded-none"
                  >
                    <Grid3X3 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>

            {loading && (
              <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-blue-500"></div>
              </div>
            )}

            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>
            )}

            {!loading && !error && filteredPosts.length === 0 && (
              <div className="text-center text-gray-600 py-10">
                {(scheduledPosts || []).length === 0 ? "No scheduled posts found." : "No posts match the current filters."}
              </div>
            )}

            {!loading && !error && filteredPosts.length > 0 && (
              <>
                {/* Select All Checkbox */}
                <div className="flex items-center space-x-2 mb-4">
                  <Checkbox
                    id="select-all"
                    checked={selectedPosts.length === filteredPosts.length && filteredPosts.length > 0}
                    onCheckedChange={handleSelectAll}
                  />
                  <label htmlFor="select-all" className="text-sm font-medium text-white cursor-pointer">
                    Select All ({filteredPosts.length})
                  </label>
                </div>

                {/* List View */}
                {viewMode === "list" && (
                  <div className="space-y-3">
                    {filteredPosts
                      .slice()
                      .sort((a, b) => b.id - a.id)
                      .map((post) => {
                        const scheduledHour = new Date(post.schedule_time).getHours()
                        const formattedScheduledTime = scheduledHour < 10 ? `0${scheduledHour}:00` : `${scheduledHour}:00`
                        const platformInfo = PLATFORMS.find(p => p.name === post.platform)
                        const PlatformIcon = platformInfo?.icon || Music

                        return (
                          <Card key={post.id} className="bg-white border border-gray-200 shadow-sm" style={{ backgroundColor: 'white' }}>
                            <CardContent className="p-4" style={{ backgroundColor: 'white' }}>
                              <div className="flex items-start space-x-4">
                                <Checkbox
                                  checked={selectedPosts.includes(post.id)}
                                  onCheckedChange={(checked) => handleSelectPost(post.id, !!checked)}
                                  className="mt-1"
                                />
                                
                                {/* Image */}
                                <div className="flex-shrink-0">
                                  {post.image_url ? (
                                    <img
                                      src={post.image_url}
                                      alt={post.title}
                                      className="w-20 h-20 object-cover rounded-md"
                                      onError={(e) => {
                                        e.currentTarget.src = "/placeholder-image.jpg"
                                      }}
                                    />
                                  ) : (
                                    <div className="w-20 h-20 bg-gray-200 rounded-md flex items-center justify-center text-gray-500 text-xs">
                                      No Image
                                    </div>
                                  )}
                                </div>
                                
                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                      <h3 className="text-lg font-semibold text-gray-900 mb-1">{post.title}</h3>
                                      <p className="text-gray-600 text-sm line-clamp-2 mb-2">{post.content}</p>
                                      
                                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                                        <div className="flex items-center space-x-1">
                                          <PlatformIcon className="h-4 w-4" />
                                          <span>{post.platform}</span>
                                        </div>
                                        <div className="flex items-center space-x-1">
                                          <Calendar className="h-4 w-4" />
                                          <span>{formatDate(post.schedule_time)}</span>
                                        </div>
                                        <Badge variant="outline" className="text-xs">
                                          {formattedScheduledTime}
                                        </Badge>
                                      </div>
                                    </div>
                                    
                                    {/* Actions */}
                                    <div className="flex flex-col space-y-2 ml-4">
                                      <select
                                        value={formattedScheduledTime}
                                        onChange={(e) => handleTimeChange(e, post.content)}
                                        className="px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                                      >
                                        {timeOptions.map((time) => (
                                          <option key={time} value={time}>{time}</option>
                                        ))}
                                      </select>
                                      
                                      <div className="flex space-x-1">
                                        <Button
                                          variant="outline"
                                          size="sm"
                                          onClick={() => {
                                            setEditedContent(post.content)
                                            setEditedPlatform(post.platform)
                                            setCurrentPostId(post.id)
                                            setIsModalOpen(true)
                                          }}
                                          disabled={actionLoading[post.id]?.regenerateContent}
                                          className="text-xs px-2 py-1"
                                        >
                                          {actionLoading[post.id]?.regenerateContent ? (
                                            <div className="animate-spin rounded-full h-3 w-3 border-t-2 border-blue-500"></div>
                                          ) : (
                                            "Edit"
                                          )}
                                        </Button>
                                        <Button
                                          variant="outline"
                                          size="sm"
                                          onClick={() => handleRegenerateImage(post.id, post.content)}
                                          disabled={actionLoading[post.id]?.regenerateImage}
                                          className="text-xs px-2 py-1"
                                        >
                                          {actionLoading[post.id]?.regenerateImage ? (
                                            <div className="animate-spin rounded-full h-3 w-3 border-t-2 border-blue-500"></div>
                                          ) : (
                                            "Image"
                                          )}
                                        </Button>
                                        <Button
                                          variant="destructive"
                                          size="sm"
                                          onClick={() => deletePost(post.id)}
                                          disabled={actionLoading[post.id]?.delete}
                                          className="text-xs px-2 py-1"
                                        >
                                          {actionLoading[post.id]?.delete ? (
                                            <div className="animate-spin rounded-full h-3 w-3 border-t-2 border-red-500"></div>
                                          ) : (
                                            "Delete"
                                          )}
                                        </Button>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        )
                      })}
                  </div>
                )}

                {/* Grid View */}
                {viewMode === "grid" && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredPosts
                      .slice()
                      .sort((a, b) => b.id - a.id)
                      .map((post) => {
                    // Extract the hour from the schedule_time
                    const scheduledHour = new Date(post.schedule_time).getHours() // Extract hour (0-23)
                    const formattedScheduledTime = scheduledHour < 10 ? `0${scheduledHour}:00` : `${scheduledHour}:00`

                    return (
                      <div
                        key={post.id}
                        className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow duration-300 relative"
                      >
                        <div className="absolute top-4 right-4">
                          <Checkbox
                            checked={selectedPosts.includes(post.id)}
                            onCheckedChange={(checked) => handleSelectPost(post.id, !!checked)}
                          />
                        </div>
                        <h2 className="text-xl font-semibold text-gray-800 mb-2 pr-8">{post.title}</h2>
                        {post.image_url ? (
                          <img
                            src={post.image_url || "/placeholder.svg"}
                            alt={post.title}
                            className="w-full h-48 object-cover rounded-md mb-4"
                            onError={(e) => {
                              e.currentTarget.src = "/placeholder-image.jpg" // Fallback image
                            }}
                          />
                        ) : (
                          <div className="w-full h-48 bg-gray-200 rounded-md mb-4 flex items-center justify-center text-gray-500">
                            No Image
                          </div>
                        )}
                        {/* <p className="text-gray-600 mb-4">{post.content}</p> */}
                        <p
                          className="text-gray-600 mb-4 line-clamp-3 cursor-pointer hover:underline"
                          onClick={() => {
                            setModalContent(post.content)
                            setModalTitle(post.title)
                            setIsContentModalOpen(true)
                          }}
                        >
                          {post.content}
                        </p>
                        <div className="flex items-center justify-between text-sm text-gray-500 mb-2">
                          <span className="font-medium">Platform:</span>
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-semibold ${
                              post.platform.toLowerCase() === "twitter"
                                ? "bg-blue-100 text-blue-600"
                                : "bg-gray-100 text-gray-600"
                            }`}
                          >
                            {post.platform}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500 mb-2">
                          <span className="font-medium">Scheduled:</span> {formatDate(post.schedule_time)}{" "}
                          {/* Display day and time */}
                        </div>
                        <div>
                          <select
                            id="time"
                            value={formattedScheduledTime} // Set the default value to the extracted hour
                            onChange={(e) => handleTimeChange(e, post.content)}
                            className="w-[180px] px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 appearance-none bg-white text-gray-700 cursor-pointer bg-no-repeat bg-[right_0.75rem_center] bg-[length:1rem]"
                            style={{
                              backgroundImage: `url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" fill="gray" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>')`,
                            }}
                          >
                            {timeOptions.map((time) => (
                              <option key={time} value={time}>
                                {time}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {/* <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() =>
                                                        handleRegenerateContent(post.id, post.content, post.platform)
                                                    }
                                                    disabled={actionLoading[post.id]?.regenerateContent}
                                                >
                                                    {actionLoading[post.id]?.regenerateContent ? (
                                                        <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-blue-500 mr-2"></div>
                                                    ) : null}
                                                    Regenerate Content
                                                </Button> */}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setEditedContent(post.content)
                              setEditedPlatform(post.platform)
                              setCurrentPostId(post.id)
                              setIsModalOpen(true)
                            }}
                            disabled={actionLoading[post.id]?.regenerateContent}
                          >
                            {actionLoading[post.id]?.regenerateContent ? (
                              <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-blue-500 mr-2"></div>
                            ) : null}
                            Regenerate Content
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRegenerateImage(post.id, post.content)}
                            disabled={actionLoading[post.id]?.regenerateImage}
                          >
                            {actionLoading[post.id]?.regenerateImage ? (
                              <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-blue-500 mr-2"></div>
                            ) : null}
                            Regenerate Image
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => deletePost(post.id)}
                            disabled={actionLoading[post.id]?.delete}
                          >
                            {actionLoading[post.id]?.delete ? (
                              <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-red-500 mr-2"></div>
                            ) : null}
                            Delete
                          </Button>
                        </div>
                      </div>
                    )
                  })}
                  </div>
                )}
              </>
            )}
              </div>
            </CardContent>
          </Card>
        </main>
      </div>

      {/* Bulk Delete Confirmation Modal */}
      <AlertDialog open={isBulkDeleteModalOpen} onOpenChange={setIsBulkDeleteModalOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-500" />
              Delete Selected Posts
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>
                Are you sure you want to delete <strong>{selectedPosts.length} selected posts</strong>?
              </p>
              <p className="text-red-600 font-medium">
                ⚠️ This action cannot be undone. All selected posts and their data will be permanently deleted.
              </p>
              {selectedPosts.length > 10 && (
                <p className="text-orange-600 font-medium">
                  ⏱️ This may take a moment as you're deleting {selectedPosts.length} posts.
                </p>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          
          {/* Progress indicator */}
          {globalLoading && deleteProgress.total > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-gray-600">
                <span>Deleting posts...</span>
                <span>{deleteProgress.current} of {deleteProgress.total}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-red-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(deleteProgress.current / deleteProgress.total) * 100}%` }}
                ></div>
              </div>
            </div>
          )}
          
          <AlertDialogFooter>
            <AlertDialogCancel disabled={globalLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleBulkDelete}
              className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
              disabled={globalLoading}
            >
              {globalLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-white mr-2"></div>
                  Deleting... ({deleteProgress.current}/{deleteProgress.total})
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete {selectedPosts.length} Posts
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
