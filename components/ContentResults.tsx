"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Check, PlusCircle, RefreshCw, FileText, Calendar, Clock } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

// Sample content data
const SAMPLE_CONTENT = [
  {
    id: "c1",
    title: "10 Digital Marketing Trends for 2025",
    type: "Blog Post",
    wordCount: 1250,
    qualityScore: 92,
    keywords: ["digital marketing", "trends", "2025", "AI", "personalization"],
    snippet:
      "As we approach 2025, the digital marketing landscape continues to evolve at a rapid pace. Staying ahead of emerging trends is crucial for businesses looking to maintain a competitive edge.",
  },
  {
    id: "c2",
    title: "How to Optimize Your Content Strategy",
    type: "Blog Post",
    wordCount: 980,
    qualityScore: 88,
    keywords: ["content strategy", "optimization", "content marketing", "ROI"],
    snippet:
      "A well-optimized content strategy is essential for driving engagement, generating leads, and building brand authority in today's competitive digital landscape.",
  },
  {
    id: "c3",
    title: "Boost Your Social Media Engagement",
    type: "Social Media",
    wordCount: 320,
    qualityScore: 85,
    keywords: ["social media", "engagement", "followers", "interaction"],
    snippet:
      "Try these 5 proven strategies that are working RIGHT NOW to boost your social media engagement and grow your audience.",
  },
  {
    id: "c4",
    title: "Monthly Newsletter: Industry Insights",
    type: "Email",
    wordCount: 650,
    qualityScore: 90,
    keywords: ["newsletter", "industry insights", "trends", "updates"],
    snippet:
      "Stay updated with the latest industry trends, insights, and best practices in our monthly newsletter designed to keep you informed and ahead of the competition.",
  },
  {
    id: "c5",
    title: "Transform Your Marketing Strategy",
    type: "Landing Page",
    wordCount: 850,
    qualityScore: 94,
    keywords: ["marketing strategy", "transformation", "growth", "ROI"],
    snippet:
      "Discover how our proven approach can transform your marketing strategy and drive unprecedented growth for your business.",
  },
]

// Sample platforms
const PLATFORMS = [
  { id: "twitter", name: "Twitter", icon: "Twitter" },
  { id: "facebook", name: "Facebook", icon: "Facebook" },
  { id: "instagram", name: "Instagram", icon: "Instagram" },
  { id: "linkedin", name: "LinkedIn", icon: "LinkedIn" },
  { id: "blog", name: "Blog", icon: "Blog" },
  { id: "email", name: "Email", icon: "Email" },
]

// Sample days
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

// Sample times
const TIMES = ["9:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM"]

export function ContentResults() {
  const [content, setContent] = useState(SAMPLE_CONTENT)
  const [selectedContent, setSelectedContent] = useState<Record<string, boolean>>({})
  const [addSuccess, setAddSuccess] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [activeTab, setActiveTab] = useState("content-pieces")
  const [showScheduler, setShowScheduler] = useState(false)
  const [scheduledContent, setScheduledContent] = useState<any[]>([])

  // Scheduling state
  const [selectedPlatform, setSelectedPlatform] = useState<string>("")
  const [selectedDay, setSelectedDay] = useState<string>("")
  const [selectedTime, setSelectedTime] = useState<string>("")

  // Handle selecting/deselecting content
  const handleSelectContent = (id: string, checked: boolean) => {
    setSelectedContent((prev) => ({
      ...prev,
      [id]: checked,
    }))
  }

  // Handle selecting all content
  const handleSelectAll = (checked: boolean) => {
    const newSelected = { ...selectedContent }

    content.forEach((item) => {
      newSelected[item.id] = checked
    })

    setSelectedContent(newSelected)
  }

  // Handle adding selected content to queue
  const handleAddToQueue = () => {
    // In a real app, this would dispatch to a global state or make an API call
    console.log(
      "Adding to queue:",
      Object.entries(selectedContent)
        .filter(([_, isSelected]) => isSelected)
        .map(([id]) => id),
    )

    // Show success message
    setAddSuccess(true)
    setTimeout(() => setAddSuccess(false), 3000)

    // Reset selections
    setSelectedContent({})
  }

  // Handle regenerating content
  const handleRegenerateContent = async () => {
    setIsRegenerating(true)

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000))

    // In a real app, this would call an API to regenerate content
    setContent([...content].sort(() => 0.5 - Math.random()))

    setIsRegenerating(false)
  }

  // Handle sending to production
  const handleSendToProduction = () => {
    setShowScheduler(true)
  }

  // Handle scheduling content
  const handleScheduleContent = () => {
    const selectedItems = Object.entries(selectedContent)
      .filter(([_, isSelected]) => isSelected)
      .map(([id]) => {
        const contentItem = content.find((item) => item.id === id)
        return {
          id,
          title: contentItem?.title,
          type: contentItem?.type,
          platform: selectedPlatform,
          day: selectedDay,
          time: selectedTime,
        }
      })

    setScheduledContent([...scheduledContent, ...selectedItems])
    setShowScheduler(false)
    setSelectedContent({})
    setSelectedPlatform("")
    setSelectedDay("")
    setSelectedTime("")
  }

  // Count selected content
  const selectedCount = Object.values(selectedContent).filter(Boolean).length

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <FileText className="h-5 w-5 text-indigo-500" />
          <span className="ml-2">Content Generation Results</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {addSuccess && (
          <div className="bg-green-50 border border-green-200 rounded-md p-3 mb-4 flex items-center">
            <Check className="h-5 w-5 text-green-500 mr-2" />
            <p className="text-green-700">Content successfully added to queue!</p>
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <CardContent className="p-4 flex flex-col items-center text-center">
              <div className="p-3 rounded-full bg-blue-100 mb-2">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
              <h4 className="font-medium">Content Pieces</h4>
              <p className="text-3xl font-bold mt-1 mb-1">{content.length}</p>
              <p className="text-sm text-gray-500">Generated articles and posts</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex flex-col items-center text-center">
              <div className="p-3 rounded-full bg-green-100 mb-2">
                <span className="w-6 h-6 text-green-600 font-bold flex items-center justify-center">#</span>
              </div>
              <h4 className="font-medium">Keywords Used</h4>
              <p className="text-3xl font-bold mt-1 mb-1">
                {content.reduce((acc, item) => acc + item.keywords.length, 0)}
              </p>
              <p className="text-sm text-gray-500">Across all content</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex flex-col items-center text-center">
              <div className="p-3 rounded-full bg-purple-100 mb-2">
                <span className="w-6 h-6 text-purple-600 font-bold flex items-center justify-center">A+</span>
              </div>
              <h4 className="font-medium">Avg. Quality Score</h4>
              <p className="text-3xl font-bold mt-1 mb-1">
                {Math.round(content.reduce((acc, item) => acc + item.qualityScore, 0) / content.length)}
              </p>
              <p className="text-sm text-gray-500">Content quality rating</p>
            </CardContent>
          </Card>
        </div>

        {/* Content Pieces Section */}
        <div className="mb-6 border rounded-md">
          <div className="bg-gray-50 px-4 py-3 border-b">
            <h3 className="font-medium">Content Pieces</h3>
          </div>
          <div className="p-4">
            <div className="space-y-4">
              {content.map((item) => (
                <div key={item.id} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Badge className="mr-2 bg-blue-100 text-blue-800 hover:bg-blue-100">{item.type}</Badge>
                    <span className="font-medium">{item.title}</span>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-sm text-gray-500">
                      <span className="font-medium text-gray-700">{item.wordCount}</span> words
                    </div>
                    <div className="text-sm text-gray-500">
                      <span className="font-medium text-gray-700">{item.qualityScore}/100</span> quality
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-6">
          <TabsList className="w-full mb-4">
            <TabsTrigger value="content-pieces" className="flex-1">
              Content Pieces
            </TabsTrigger>
            <TabsTrigger value="production-schedule" className="flex-1">
              Production Schedule
            </TabsTrigger>
          </TabsList>

          <TabsContent value="content-pieces">
            {showScheduler ? (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Schedule Content for Production</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <Label htmlFor="platform" className="block mb-2">
                          Platform
                        </Label>
                        <Select value={selectedPlatform} onValueChange={setSelectedPlatform}>
                          <SelectTrigger id="platform">
                            <SelectValue placeholder="Select platform" />
                          </SelectTrigger>
                          <SelectContent>
                            {PLATFORMS.map((platform) => (
                              <SelectItem key={platform.id} value={platform.id}>
                                {platform.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label htmlFor="day" className="block mb-2">
                          Day
                        </Label>
                        <Select value={selectedDay} onValueChange={setSelectedDay}>
                          <SelectTrigger id="day">
                            <SelectValue placeholder="Select day" />
                          </SelectTrigger>
                          <SelectContent>
                            {DAYS.map((day) => (
                              <SelectItem key={day} value={day}>
                                {day}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label htmlFor="time" className="block mb-2">
                          Time
                        </Label>
                        <Select value={selectedTime} onValueChange={setSelectedTime}>
                          <SelectTrigger id="time">
                            <SelectValue placeholder="Select time" />
                          </SelectTrigger>
                          <SelectContent>
                            {TIMES.map((time) => (
                              <SelectItem key={time} value={time}>
                                {time}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="border rounded-md p-4 bg-gray-50">
                      <h4 className="font-medium mb-2">Selected Content</h4>
                      <ul className="space-y-2">
                        {Object.entries(selectedContent)
                          .filter(([_, isSelected]) => isSelected)
                          .map(([id]) => {
                            const item = content.find((c) => c.id === id)
                            return (
                              <li key={id} className="flex items-center">
                                <Check className="h-4 w-4 text-green-500 mr-2" />
                                <span>{item?.title}</span>
                                <Badge className="ml-2">{item?.type}</Badge>
                              </li>
                            )
                          })}
                      </ul>
                    </div>

                    <div className="flex justify-end space-x-2">
                      <Button variant="outline" onClick={() => setShowScheduler(false)}>
                        Cancel
                      </Button>
                      <Button
                        onClick={handleScheduleContent}
                        disabled={!selectedPlatform || !selectedDay || !selectedTime}
                        className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                      >
                        Schedule Content
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <>
                <div className="flex justify-between items-center mb-4">
                  <div className="flex items-center space-x-2">
                    <Checkbox id="select-all-content" onCheckedChange={(checked) => handleSelectAll(!!checked)} />
                    <Label htmlFor="select-all-content">Select All</Label>
                  </div>
                  <div className="flex space-x-2">
                    <Button size="sm" onClick={handleAddToQueue} disabled={selectedCount === 0} variant="outline">
                      <PlusCircle className="h-4 w-4 mr-2" />
                      Add to Queue ({selectedCount})
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleSendToProduction}
                      disabled={selectedCount === 0}
                      className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                    >
                      Send to Production
                    </Button>
                  </div>
                </div>

                <div className="space-y-3">
                  {content.map((item) => (
                    <div key={item.id} className="p-3 border rounded-md">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center">
                          <Checkbox
                            id={item.id}
                            checked={selectedContent[item.id] || false}
                            onCheckedChange={(checked) => handleSelectContent(item.id, !!checked)}
                          />
                          <Label htmlFor={item.id} className="ml-3 font-medium cursor-pointer">
                            {item.title}
                          </Label>
                        </div>
                        <Badge
                          variant="outline"
                          className={`
                          ${
                            item.qualityScore >= 90
                              ? "bg-green-50 text-green-700"
                              : item.qualityScore >= 80
                                ? "bg-blue-50 text-blue-700"
                                : "bg-yellow-50 text-yellow-700"
                          }
                        `}
                        >
                          Quality: {item.qualityScore}/100
                        </Badge>
                      </div>
                      <div className="ml-7">
                        <div className="text-sm text-gray-600 mb-2">{item.snippet}</div>
                        <div className="flex items-center justify-between">
                          <div className="flex flex-wrap gap-1">
                            {item.keywords.map((keyword, idx) => (
                              <Badge key={idx} variant="secondary" className="text-xs">
                                {keyword}
                              </Badge>
                            ))}
                          </div>
                          <div className="text-sm text-gray-500">
                            {item.wordCount} words • {item.type}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-4 flex justify-center">
                  <Button onClick={handleRegenerateContent} disabled={isRegenerating} variant="outline">
                    {isRegenerating ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Regenerating Content...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Regenerate Content
                      </>
                    )}
                  </Button>
                </div>
              </>
            )}
          </TabsContent>

          <TabsContent value="production-schedule">
            {scheduledContent.length > 0 ? (
              <div className="space-y-4">
                {DAYS.map((day) => {
                  const dayContent = scheduledContent.filter((item) => item.day === day)
                  if (dayContent.length === 0) return null

                  return (
                    <div key={day} className="border rounded-md overflow-hidden">
                      <div className="bg-gray-50 px-4 py-2 border-b font-medium">{day}</div>
                      <div className="p-0">
                        <table className="w-full">
                          <tbody>
                            {dayContent.map((item, idx) => (
                              <tr key={`${item.id}-${idx}`} className={idx !== dayContent.length - 1 ? "border-b" : ""}>
                                <td className="px-4 py-3 flex items-center">
                                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center mr-3">
                                    {PLATFORMS.find((p) => p.id === item.platform)?.icon.charAt(0)}
                                  </div>
                                  <div>
                                    <div className="font-medium">{item.title}</div>
                                    <div className="text-sm text-gray-500">{item.type}</div>
                                  </div>
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <div className="flex items-center justify-end">
                                    <Clock className="h-4 w-4 text-gray-400 mr-1" />
                                    <span>{item.time}</span>
                                  </div>
                                  <div className="text-sm text-gray-500">
                                    {PLATFORMS.find((p) => p.id === item.platform)?.name}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-12 border rounded-md">
                <Calendar className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No Scheduled Content</h3>
                <p className="text-gray-500 max-w-md mx-auto mb-4">
                  Select content from the Content Pieces tab and use the "Send to Production" button to schedule content
                  for publication.
                </p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
