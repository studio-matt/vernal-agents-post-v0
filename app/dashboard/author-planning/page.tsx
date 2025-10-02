"use client"

import type React from "react"
import { useState, useRef } from "react"
import { Header } from "@/components/Header"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import {
  Instagram,
  Facebook,
  Youtube,
  Twitter,
  Linkedin,
  Compass as Wordpress,
  Music,
  Upload,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import { DayPlatformModule } from "@/components/DayPlatformModule"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Card, CardContent } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { ContentModificationModal } from "@/components/ContentModificationModal"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { generateCustomScripts, Service } from "@/components/Service"
import { ErrorDialog } from "@/components/ErrorDialog"

interface TimeSlot {
  time: string
  content: string
  image: string
}

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

const PLATFORMS = [
  { name: "Instagram", icon: Instagram },
  { name: "Facebook", icon: Facebook },
  { name: "YouTube", icon: Youtube },
  { name: "Twitter", icon: Twitter },
  { name: "LinkedIn", icon: Linkedin },
  { name: "WordPress", icon: Wordpress },
  { name: "TikTok", icon: Music },
]

export default function AuthorPlanningPage() {
  const [currentStep, setCurrentStep] = useState(1)
  const [numberOfWeeks, setNumberOfWeeks] = useState("1")
  const [defaultPosts, setDefaultPosts] = useState("3")
  const [activeDays, setActiveDays] = useState<string[]>([])
  const [activePlatforms, setActivePlatforms] = useState<string[]>([])
  const [isRegeneratingPlan, setIsRegeneratingPlan] = useState(false)

  const [timeSlots, setTimeSlots] = useState<Record<number, Record<string, Record<string, TimeSlot[]>>>>({})
  const [sourceFile, setSourceFile] = useState<File | null>(null)
  const [mainIdeas, setMainIdeas] = useState<string[]>([])
  const [subTopics, setSubTopics] = useState<string[][]>([])
  const [platform, setPlatform] = useState<string | undefined>(undefined)
  const [isModificationModalOpen, setIsModificationModalOpen] = useState(false)
  const [selectedModification, setSelectedModification] = useState<{
    type: "main" | "sub"
    weekIndex: number
    dayIndex?: number
  }>({ type: "main", weekIndex: 0 })
  const [isSettingsOpen, setIsSettingsOpen] = useState(true)
  const [isContentIdeasOpen, setIsContentIdeasOpen] = useState(true)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [isStepThreeOpen, setIsStepThreeOpen] = useState(false)
  const stepTwoRef = useRef<HTMLDivElement>(null)
  const stepThreeRef = useRef<HTMLDivElement>(null)

  const [isSubmitted, setIsSubmitted] = useState(false)
  const [isMainContent, setIsMainContent] = useState("")
  const [subTopic, setSubTopic] = useState<string | undefined>(undefined)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [showErrorDialog, setShowErrorDialog] = useState(false)

  const handleUpdateActiveDays = (days: string[]) => {
    setActiveDays(days)
  }

  const handleUpdateActivePlatforms = (platforms: string[]) => {
    setActivePlatforms(platforms)
  }

  const handleNextStep = async () => {
    if (currentStep === 1) {
      if (!sourceFile) {
        console.error("No source file provided.")
        setIsSubmitted(true)
        return Promise.reject("No source file provided.")
      }

      setIsRegenerating(true)

      try {
        const formData = new FormData()
        formData.append("file", sourceFile)
        formData.append("week", numberOfWeeks)
        formData.append("days", activeDays.join(","))

        const response = await Service("extract_content", "POST", formData)

        if (response?.status === "success" && response?.content) {
          const extractedContent = response.content
          const tempId = response.temp_id

          const newMainIdeas: string[] = []
          const newSubTopics: string[][] = []

          Object.keys(extractedContent).forEach((weekKey) => {
            const weekData = extractedContent[weekKey]

            const weekHeader = `Week: ${weekData.week}\nTopic: ${weekData.topic}\nQuote: "${weekData.quote}"`
            newMainIdeas.push(weekHeader)

            const dayEntries = weekData.content_by_days || {}
            const daysFormatted: string[] = []

            Object.keys(dayEntries).forEach((dayKey) => {
              const dayData = dayEntries[dayKey]
              const dayText = `${dayData.day}:\n  Subtopic: ${dayData.subtopic}\n  Quote: "${dayData.quote}"`
              daysFormatted.push(dayText)
            })

            newSubTopics.push(daysFormatted)
          })

          setMainIdeas(newMainIdeas)
          setSubTopics(newSubTopics)
        } else {
          console.warn("Unexpected API response format:", response)
          alert("Failed to extract content from the source file.")
        }
      } catch (error) {
        console.error("An error occurred while extracting content. Please try again.", error)
        setErrorMessage("An error occurred while extracting content.")
        setShowErrorDialog(true)
      } finally {
        setIsRegenerating(false)
      }

      setCurrentStep(2)
      setIsSettingsOpen(false)
      setTimeout(scrollToStepTwo, 100)
    }
  }

  const handleFinalizePlan = async () => {
    setIsRegeneratingPlan(true)

    if (!sourceFile) {
      alert("Please upload a source file before finalizing the plan.")
      setIsRegeneratingPlan(false)
      return
    }

    const platformPosts: { [key: string]: number } = {}
    activePlatforms.forEach((platform) => {
      platformPosts[platform] = Number(defaultPosts) || 1
    })

    try {
      const customScripts = await generateCustomScripts(
        sourceFile,
        Number.parseInt(numberOfWeeks),
        activeDays,
        platformPosts,
      )

      console.log("customScripts", customScripts)

      if (!customScripts || (Array.isArray(customScripts) && customScripts.length === 0)) {
        console.warn("Invalid response from generateCustomScripts:", customScripts)
        alert("Failed to generate custom scripts. Please Connect Platform First.")
        return
      }

      if (!Array.isArray(customScripts) && customScripts.status !== "success") {
        console.warn("Failed to generate custom scripts:", customScripts)
        alert("Failed to generate custom scripts. Please Connect Platform First.")
        return
      }

      const resultsByPlatform = Array.isArray(customScripts)
        ? customScripts.reduce<Record<string, any[]>>((acc, item) => {
            const platform = item.platform?.toLowerCase() || "unknown"
            if (!acc[platform]) acc[platform] = []
            acc[platform].push(item)
            return acc
          }, {})
        : customScripts.results

      console.log("Processed Results:", resultsByPlatform)

      const newTimeSlots: Record<number, Record<string, Record<string, TimeSlot[]>>> = {}

      for (let week = 1; week <= Number.parseInt(numberOfWeeks); week++) {
        newTimeSlots[week] = {}

        for (const day of activeDays) {
          newTimeSlots[week][day] = {}

          for (const platform of activePlatforms) {
            newTimeSlots[week][day][platform] = Array(Number.parseInt(defaultPosts))
              .fill(null)
              .map((_, index) => ({
                time: `${9 + index * 3}:00`,
                content: "",
                image: "",
              }))

            const platformResults = resultsByPlatform[platform.toLowerCase()] || []

            if (!platformResults || platformResults.length === 0) {
              console.warn(`No posts available for ${platform}`)
              continue
            }

            platformResults
              .filter((item: any) => item.week === week && item.day.toLowerCase() === day.toLowerCase())
              .forEach((item: any, index: number) => {
                if (index < newTimeSlots[week][day][platform].length) {
                  newTimeSlots[week][day][platform][index] = {
                    time: `${9 + index * 3}:00`,
                    content: item.content || "",
                    image: item.image || "",
                  }
                }
              })
          }
        }
      }

      setTimeSlots(newTimeSlots)

      if (!Array.isArray(customScripts) && customScripts.status === "success") {
        const updatedTimeSlots = { ...newTimeSlots }

        for (const platform in customScripts.results) {
          const normalizedPlatform = platform.toLowerCase()
          const platformContent = customScripts.results[normalizedPlatform]

          platformContent.forEach((post: any, index: number) => {
            const { week, day, content } = post
            const normalizedDay = day.trim().toLowerCase()

            if (
              updatedTimeSlots[week] &&
              updatedTimeSlots[week][normalizedDay] &&
              updatedTimeSlots[week][normalizedDay][normalizedPlatform]
            ) {
              updatedTimeSlots[week][normalizedDay][normalizedPlatform][index] = {
                time: `${9 + index * 3}:00`,
                content: content || "",
                image: "",
              }
            }
          })
        }

        setTimeSlots(updatedTimeSlots)
      }
    } catch (error) {
      console.error("Error during /generate_custom_scripts API call:", error)
      alert("An error occurred while generating custom scripts. Please try again.")
      console.error("An error occurred while generating custom scripts.", error)
      setErrorMessage("An error occurred while generating custom scripts.")
      setShowErrorDialog(true)
    }

    setIsRegeneratingPlan(false)
    setCurrentStep(3)
    setIsContentIdeasOpen(false)

    setTimeout(() => {
      if (stepThreeRef.current) {
        stepThreeRef.current.scrollIntoView({
          behavior: "smooth",
          block: "start",
        })
      }
    }, 1000)
  }

  const handleResetPlan = () => {
    setTimeSlots({})
    setCurrentStep(1)
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSourceFile(event.target.files[0])
    }
  }

  const handleRegenerate = (type: "main" | "sub", weekIndex: number, dayIndex?: number, subTopic?: string) => {
    setSelectedModification({ type, weekIndex, dayIndex })
    setSubTopic(subTopic)
    setIsModificationModalOpen(true)
  }

  const handleModificationConfirm = (modifications: string) => {
    const { type, weekIndex, dayIndex } = selectedModification
    setIsMainContent(modifications)
    if (type === "main") {
      setMainIdeas((prev) => {
        const newIdeas = [...prev]

        if (!newIdeas[weekIndex]) {
          newIdeas[weekIndex] = ""
        }

        const [weekLabel, currentContent] = newIdeas[weekIndex].split(":")

        newIdeas[weekIndex] = `${weekLabel}: ${modifications.trim()}`

        return newIdeas
      })
    } else if (type === "sub" && dayIndex !== undefined) {
      setSubTopics((prev) => {
        const newTopics = [...prev]

        if (!newTopics[weekIndex]) {
          newTopics[weekIndex] = []
        }

        const [weekLabel, currentContent] = newTopics[weekIndex][dayIndex]?.split(":") || []

        if (weekLabel) {
          newTopics[weekIndex][dayIndex] = `${weekLabel}: ${modifications.trim()}`
        }

        return newTopics
      })
    }
    setIsModificationModalOpen(false)
  }

  const handleRegeneratePlan = async () => {
    if (!sourceFile) {
      alert("Please upload a source file before regenerating the plan.")
      return
    }

    setIsRegenerating(true)

    try {
      const formData = new FormData()
      formData.append("file", sourceFile)
      formData.append("week", numberOfWeeks)
      formData.append("days", activeDays.join(","))

      const response = await Service("extract_content", "POST", formData)

      if (response?.status === "success" && response?.content) {
        const extractedContent = response.content
        const tempId = response.temp_id

        const newMainIdeas: string[] = []
        const newSubTopics: string[][] = []

        Object.keys(extractedContent).forEach((weekKey) => {
          const weekContent = extractedContent[weekKey]

          const weekTitle = weekContent?.week || weekKey
          const topic = weekContent?.topic || ""
          const weekQuote = weekContent?.quote || ""

          const mainIdea = `${weekTitle}: ${topic}\n"${weekQuote}"`
          newMainIdeas.push(mainIdea)

          const contentByDays = weekContent?.content_by_days || {}
          const dayTopics: string[] = []

          Object.keys(contentByDays).forEach((dayKey) => {
            const dayContent = contentByDays[dayKey]
            const dayName = dayContent?.day || dayKey
            const subtopic = dayContent?.subtopic || ""
            const dayQuote = dayContent?.quote || ""

            const subTopicFormatted = `${dayName}: ${subtopic}\n"${dayQuote}"`
            dayTopics.push(subTopicFormatted)
          })

          newSubTopics.push(dayTopics)
        })

        setMainIdeas(newMainIdeas)
        setSubTopics(newSubTopics)
      } else {
        console.error("Failed to generate ideas:", response.message)
        setErrorMessage(response.message || "Failed to extract content from the source file.")
        setShowErrorDialog(true)
      }
    } catch (error) {
      console.error("Error during extract_content API call:", error)
      console.error("An error occurred while extracting content.", error)
      setErrorMessage("An error occurred while extracting content.")
      setShowErrorDialog(true)
    } finally {
      setIsRegenerating(false)
      setCurrentStep(2)
    }
  }

  const scrollToStepTwo = () => {
    if (stepTwoRef.current) {
      stepTwoRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <h1 className="text-4xl font-extrabold text-white">Author Planning</h1>

          <Card className="w-full">
            <Collapsible open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" className="w-full flex justify-between items-center p-4">
                  <span className="text-lg font-semibold">Plan Settings</span>
                  {isSettingsOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <CardContent className="p-6 space-y-6">
                  <div className="md:w-1/2 space-y-4">
                    <h3 className="text-[1.1rem] font-semibold">Upload Source Material</h3>
                    <p className="text-sm text-gray-500">
                      Upload your source material here. This is what we will use to break down each post in the plan.
                      Source material should be a PDF, Text Doc, MP3 for audio or MP4 for video.
                    </p>
                    <div className="flex flex-col space-y-2">
                      <Input
                        id="source-material"
                        type="file"
                        onChange={handleFileChange}
                        accept=".pdf,.doc,.docx,.txt,.mp3,.mp4"
                        className={`flex-1 ${!sourceFile && isSubmitted ? "border-red-500" : ""}`}
                        required
                      />
                      <Button
                        type="button"
                        onClick={() => {
                          if (!sourceFile) {
                            setIsSubmitted(true)
                            console.error("File upload is required.")
                            return
                          }
                          console.log("File is uploaded:", sourceFile.name)
                        }}
                        className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                      >
                        <Upload className="w-4 h-4 mr-2" />
                        Upload
                      </Button>
                    </div>
                    {!sourceFile && isSubmitted && <p className="text-sm text-red-600">Please upload a source file.</p>}
                    {sourceFile && <p className="text-sm text-green-600">File uploaded: {sourceFile.name}</p>}
                  </div>
                  <div className="flex space-x-4">
                    <div className="w-1/2">
                      <h3 className="text-[1.1rem] font-semibold mb-1">Number of Weeks</h3>
                      <Input
                        type="number"
                        id="numberOfWeeks"
                        value={numberOfWeeks}
                        onChange={(e) => {
                          const value = e.target.value.slice(0, 3)
                          setNumberOfWeeks(value)
                        }}
                        className="w-full"
                        max="999"
                      />
                    </div>
                    <div className="w-1/2">
                      <h3 className="text-[1.1rem] font-semibold mb-1">Default Posts per Platform</h3>
                      <Input
                        type="number"
                        id="defaultPosts"
                        value={defaultPosts}
                        onChange={(e) => {
                          const value = e.target.value.slice(0, 2)
                          setDefaultPosts(value)
                        }}
                        className="w-full"
                        max="99"
                      />
                    </div>
                  </div>
                  <div>
                    <h3 className="text-[1.1rem] font-semibold mb-2">Active Days</h3>
                    <ToggleGroup
                      type="multiple"
                      value={activeDays}
                      onValueChange={handleUpdateActiveDays}
                      className="flex flex-wrap gap-2 justify-start"
                    >
                      {DAYS.map((day) => (
                        <ToggleGroupItem
                          key={day}
                          value={day}
                          aria-label={day}
                          className={`px-3 py-2 flex-1 justify-center day-button ${
                            activeDays.includes(day) ? "active-day" : ""
                          }`}
                        >
                          {day}
                        </ToggleGroupItem>
                      ))}
                    </ToggleGroup>
                  </div>
                  <div>
                    <h3 className="text-[1.1rem] font-semibold mb-2">Active Platforms</h3>
                    <ToggleGroup
                      type="multiple"
                      value={activePlatforms}
                      onValueChange={handleUpdateActivePlatforms}
                      className="flex flex-wrap gap-2 justify-start"
                    >
                      {PLATFORMS.map((platform) => (
                        <Tooltip key={platform.name}>
                          <TooltipTrigger asChild>
                            <ToggleGroupItem
                              value={platform.name}
                              aria-label={platform.name}
                              className={`p-2 flex-1 justify-center platform-button flex items-center transition${
                                activePlatforms.includes(platform.name)
                                  ? "active-platform bg-muted text-black"
                                  : "text-black hover:bg-gray-100"
                              }`}
                            >
                              <platform.icon className="w-6 h-6" />
                            </ToggleGroupItem>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{platform.name}</p>
                          </TooltipContent>
                        </Tooltip>
                      ))}
                    </ToggleGroup>
                  </div>
                  <div className="pt-4">
                    {currentStep === 1 ? (
                      <Button
                        onClick={handleNextStep}
                        className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                        disabled={isRegenerating}
                      >
                        {isRegenerating ? (
                          <>
                            <svg
                              className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                              xmlns="http://www.w3.org/2000/svg"
                              fill="none"
                              viewBox="0 0 24 24"
                            >
                              <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                              ></circle>
                              <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              ></path>
                            </svg>
                            Next Step...
                          </>
                        ) : (
                          "Next Step"
                        )}
                      </Button>
                    ) : (
                      <Button
                        onClick={handleRegeneratePlan}
                        className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                        disabled={isRegenerating}
                      >
                        {isRegenerating ? (
                          <>
                            <svg
                              className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                              xmlns="http://www.w3.org/2000/svg"
                              fill="none"
                              viewBox="0 0 24 24"
                            >
                              <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                              ></circle>
                              <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              ></path>
                            </svg>
                            Regenerating Plan...
                          </>
                        ) : (
                          "Regenerate Plan"
                        )}
                      </Button>
                    )}
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Collapsible>
          </Card>

          {currentStep >= 2 && (
            <Card className="w-full" ref={stepTwoRef}>
              <Collapsible open={isContentIdeasOpen} onOpenChange={setIsContentIdeasOpen}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" className="w-full flex justify-between items-center p-4">
                    <span className="text-lg font-semibold">Step Two: Content Ideas</span>
                    {isContentIdeasOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="p-6 space-y-6">
                    <div className="space-y-6">
                      {mainIdeas.map((mainIdea, weekIndex) => (
                        <div key={weekIndex} className="space-y-4">
                          <div className="flex items-center space-x-2">
                            <Textarea
                              value={mainIdea}
                              onChange={(e) => {
                                const newMainIdeas = [...mainIdeas]
                                newMainIdeas[weekIndex] = e.target.value
                                setMainIdeas(newMainIdeas)
                              }}
                              placeholder={`Main Idea for Week ${weekIndex + 1}`}
                              className="flex-grow"
                            />
                            <Button onClick={() => handleRegenerate("main", weekIndex, 0, mainIdea)}>Regenerate</Button>
                          </div>
                          <div className="pl-4 space-y-2">
                            {subTopics[weekIndex]?.map((subTopic, dayIndex) => (
                              <div key={dayIndex} className="flex items-center space-x-2">
                                <Textarea
                                  value={subTopic}
                                  onChange={(e) => {
                                    const newSubTopics = [...subTopics]
                                    newSubTopics[weekIndex][dayIndex] = e.target.value
                                    setSubTopics(newSubTopics)
                                  }}
                                  placeholder={`Sub-topic ${dayIndex + 1}`}
                                  className="flex-grow"
                                />
                                <Button onClick={() => handleRegenerate("sub", weekIndex, dayIndex, subTopic)}>
                                  Regenerate
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="pt-4">
                      {currentStep === 2 ? (
                        <Button
                          onClick={handleFinalizePlan}
                          className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                          disabled={isRegeneratingPlan}
                        >
                          {isRegeneratingPlan ? (
                            <>
                              <svg
                                className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                              >
                                <circle
                                  className="opacity-25"
                                  cx="12"
                                  cy="12"
                                  r="10"
                                  stroke="currentColor"
                                  strokeWidth="4"
                                ></circle>
                                <path
                                  className="opacity-75"
                                  fill="currentColor"
                                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                ></path>
                              </svg>
                              Accept and Finalize Plan...
                            </>
                          ) : (
                            "Accept and Finalize Plan"
                          )}
                        </Button>
                      ) : (
                        <Button
                          onClick={handleRegeneratePlan}
                          className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                          disabled={isRegenerating}
                        >
                          {isRegenerating ? (
                            <>
                              <svg
                                className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                              >
                                <circle
                                  className="opacity-25"
                                  cx="12"
                                  cy="12"
                                  r="10"
                                  stroke="currentColor"
                                  strokeWidth="4"
                                ></circle>
                                <path
                                  className="opacity-75"
                                  fill="currentColor"
                                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                ></path>
                              </svg>
                              Regenerating Plan...
                            </>
                          ) : (
                            "Regenerate Plan"
                          )}
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </CollapsibleContent>
              </Collapsible>
            </Card>
          )}

          {currentStep === 3 && (
            <Card className="w-full" ref={stepThreeRef}>
              <Collapsible open={isStepThreeOpen} onOpenChange={setIsStepThreeOpen}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" className="w-full flex justify-between items-center p-4">
                    <span className="text-lg font-semibold">Step Three: The Plan</span>
                    {isStepThreeOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="p-6">
                    <DayPlatformModule
                      numberOfWeeks={Number.parseInt(numberOfWeeks)}
                      activeDays={activeDays}
                      activePlatforms={activePlatforms}
                      timeSlots={timeSlots}
                      setTimeSlots={setTimeSlots}
                      onResetPlan={handleResetPlan}
                    />
                  </CardContent>
                </CollapsibleContent>
              </Collapsible>
            </Card>
          )}

          <ErrorDialog
            isOpen={showErrorDialog}
            onClose={() => setShowErrorDialog(false)}
            message={errorMessage || ""}
          />

          <ContentModificationModal
            isOpen={isModificationModalOpen}
            onClose={() => setIsModificationModalOpen(false)}
            onRegenerate={handleModificationConfirm}
            contentType={selectedModification.type === "main" ? "main" : "sub"}
            subTopic={subTopic ?? ""}
            platform={platform ?? ""}
          />
        </main>
      </div>
    </TooltipProvider>
  )
}
