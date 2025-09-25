"use client"

import type React from "react"

import {
  deletePostById,
  generateImageMachineContent,
  getScheduledPosts,
  regenerateContentAPI,
  scheduleTime,
} from "@/components/Service"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Header } from "@/components/Header" // Added Header component import

interface Post {
  id: number
  topic: string
  title: string
  content: string
  day: string
  platform: string
  schedule_time: string
  image: string
}

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
      const response = await deletePostById(postId)
      if (response.status === "success") {
        await getSchedulePosts()
      } else {
        console.error("Failed to delete post:", response.message)
      }
    } catch (error) {
      console.error("Error deleting post:", error)
      setError("Error deleting post:")
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
        <main className="p-6 max-w-7xl mx-auto">
          <div className="space-y-6">
            <h1 className="text-4xl font-extrabold text-white mb-6">Scheduled Posts</h1>

            {loading && (
              <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-blue-500"></div>
              </div>
            )}

            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>
            )}

            {!loading && !error && scheduledPosts.length === 0 && (
              <div className="text-center text-gray-600 py-10">No scheduled posts found.</div>
            )}

            {!loading && !error && scheduledPosts.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {scheduledPosts
                  .slice() // make a shallow copy to avoid mutating state
                  .sort((a, b) => b.id - a.id)
                  .map((post) => {
                    // Extract the hour from the schedule_time
                    const scheduledHour = new Date(post.schedule_time).getHours() // Extract hour (0-23)
                    const formattedScheduledTime = scheduledHour < 10 ? `0${scheduledHour}:00` : `${scheduledHour}:00`

                    return (
                      <div
                        key={post.id}
                        className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow duration-300"
                      >
                        <h2 className="text-xl font-semibold text-gray-800 mb-2">{post.title}</h2>
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
          </div>
        </main>
      </div>
    </>
  )
}
