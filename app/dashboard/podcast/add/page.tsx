"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowLeft, Save, Upload, CheckCircle2, Loader2, Trash2, FileText, Type } from "lucide-react"
import { Header } from "@/components/Header"
import { Progress } from "@/components/ui/progress"

// Example white paper topics
const WHITE_PAPER_TOPICS = [
  "Industry Trends and Analysis",
  "Case Study: Success Stories",
  "Technology Innovation Report",
  "Market Research Findings",
  "Best Practices Guide",
  "Strategic Planning Framework",
  "Competitive Analysis",
  "Future Outlook",
  "Problem-Solution Overview",
  "Expert Insights",
]

// Example blog categories
const BLOG_CATEGORIES = [
  "Uncategorized",
  "Technology",
  "Business Strategy",
  "Leadership",
  "Marketing",
  "Innovation",
  "Industry News",
  "Professional Development",
  "Case Studies",
  "Research",
  "Thought Leadership",
]

// Example guest links found in transcript
const EXAMPLE_GUEST_LINKS = [
  "https://example.com/guest-website",
  "https://linkedin.com/in/guest-profile",
  "https://twitter.com/guesthandle",
  "https://youtube.com/c/guestchannel",
  "https://medium.com/@guestblog",
  "https://github.com/guestdev",
  "https://slideshare.net/guestpresentations",
  "https://example.com/guest-book",
  "https://example.com/guest-course",
  "https://example.com/guest-product",
]

export default function AddPodcastPage() {
  const router = useRouter()

  // Form state
  const [formState, setFormState] = useState({
    transcriptUploaded: false,
    processingTranscript: false,
    processingComplete: false,
    currentStep: 1,
    progress: 0,
    includeWhitePaper: false,
    createNewCategory: false,
    transcriptInputMethod: "paste" as "paste" | "upload",
  })

  // Podcast data
  const [podcast, setPodcast] = useState({
    guestName: "Dr. Jane Smith",
    selectedCategories: [] as string[],
    customCategory: "",
    title: "",
    showNotes: "Please enter your show notes here or upload a text file of them below.",
    website: "https://example.com",
    theirPodcast: "The Example Show",
    instagram: "@exampleguest",
    youtube: "youtube.com/exampleguest",
    facebook: "facebook.com/exampleguest",
    linkedin: "linkedin.com/in/exampleguest",
    selectedWhitePaperTopics: [] as string[],
    pastedTranscript: "",
  })

  // Guest links state with checked status
  const [guestLinks, setGuestLinks] = useState(
    EXAMPLE_GUEST_LINKS.map((link) => ({
      url: link,
      checked: true,
    })),
  )

  // File state
  const [transcriptFile, setTranscriptFile] = useState<File | null>(null)
  const [showNotesFile, setShowNotesFile] = useState<File | null>(null)

  // Handle transcript upload
  const handleTranscriptChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setTranscriptFile(e.target.files[0])
      setFormState((prev) => ({
        ...prev,
        transcriptUploaded: true,
        transcriptInputMethod: "upload",
      }))
    }
  }

  // Handle pasted transcript
  const handlePastedTranscriptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value
    setPodcast((prev) => ({
      ...prev,
      pastedTranscript: text,
    }))

    setFormState((prev) => ({
      ...prev,
      transcriptUploaded: text.trim().length > 0,
      transcriptInputMethod: "paste",
    }))
  }

  // Handle show notes file upload
  const handleShowNotesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setShowNotesFile(e.target.files[0])
      // In a real app, you'd parse the file and update the show notes
      setPodcast((prev) => ({
        ...prev,
        showNotes: `Content from ${e.target.files![0].name}`,
      }))
    }
  }

  // Toggle white paper inclusion
  const toggleWhitePaper = (checked: boolean) => {
    setFormState((prev) => ({
      ...prev,
      includeWhitePaper: checked,
    }))

    if (!checked) {
      setPodcast((prev) => ({
        ...prev,
        selectedWhitePaperTopics: [],
      }))
    }
  }

  // Toggle white paper topic selection
  const toggleWhitePaperTopic = (topic: string, checked: boolean) => {
    setPodcast((prev) => {
      if (checked) {
        return {
          ...prev,
          selectedWhitePaperTopics: [...prev.selectedWhitePaperTopics, topic],
        }
      } else {
        return {
          ...prev,
          selectedWhitePaperTopics: prev.selectedWhitePaperTopics.filter((t) => t !== topic),
        }
      }
    })
  }

  // Toggle blog category selection
  const toggleCategory = (category: string, checked: boolean) => {
    setPodcast((prev) => {
      if (checked) {
        return {
          ...prev,
          selectedCategories: [...prev.selectedCategories, category],
        }
      } else {
        return {
          ...prev,
          selectedCategories: prev.selectedCategories.filter((c) => c !== category),
        }
      }
    })
  }

  // Toggle create new category
  const toggleCreateNewCategory = (checked: boolean) => {
    setFormState((prev) => ({
      ...prev,
      createNewCategory: checked,
    }))

    if (checked) {
      setPodcast((prev) => ({
        ...prev,
        customCategory: `${prev.guestName}'s Category`,
      }))
    } else {
      setPodcast((prev) => ({
        ...prev,
        customCategory: "",
      }))
    }
  }

  // Handle guest link change
  const handleGuestLinkChange = (index: number, value: string) => {
    setGuestLinks((prev) => {
      const newLinks = [...prev]
      newLinks[index] = { ...newLinks[index], url: value }
      return newLinks
    })
  }

  // Toggle guest link checked status
  const toggleGuestLink = (index: number, checked: boolean) => {
    setGuestLinks((prev) => {
      const newLinks = [...prev]
      newLinks[index] = { ...newLinks[index], checked }
      return newLinks
    })
  }

  // Delete guest link
  const deleteGuestLink = (index: number) => {
    setGuestLinks((prev) => prev.filter((_, i) => i !== index))
  }

  // Simulate transcript processing
  const processTranscript = () => {
    setFormState((prev) => ({
      ...prev,
      processingTranscript: true,
      progress: 0,
    }))

    // Simulate progress updates
    const interval = setInterval(() => {
      setFormState((prev) => {
        if (prev.progress >= 100) {
          clearInterval(interval)
          return {
            ...prev,
            processingTranscript: false,
            processingComplete: true,
            currentStep: 2,
          }
        }
        return {
          ...prev,
          progress: prev.progress + 10,
        }
      })
    }, 300)
  }

  // Handle form submission
  const handleSave = async () => {
    // In a real app, this would save to an API
    console.log("Saving new podcast:", podcast)
    console.log(
      "Guest links:",
      guestLinks.filter((link) => link.checked),
    )
    console.log("Files to upload:", { transcriptFile, showNotesFile })
    console.log("Include white paper:", formState.includeWhitePaper)

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))

    // Navigate back to podcast list
    router.push("/dashboard?tab=podcast-tools")
  }

  // Determine if form can be submitted
  const canSubmit = formState.processingComplete && podcast.title.trim() !== ""

  // Check if transcript is ready to process
  const canProcessTranscript =
    (formState.transcriptInputMethod === "paste" && podcast.pastedTranscript.trim().length > 0) ||
    (formState.transcriptInputMethod === "upload" && transcriptFile !== null)

  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <Header username="John Doe" />
      <main className="p-6 max-w-5xl mx-auto space-y-6">
        <div className="flex items-center space-x-4">
          <Button variant="outline" className="bg-white" onClick={() => router.push("/dashboard?tab=podcast-tools")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Shows
          </Button>
          <h1 className="text-3xl font-bold text-white">Add New Show</h1>
        </div>

        <Card>
          <CardContent className="p-6 space-y-8">
            {/* Step indicator */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center">
                <div
                  className={`rounded-full w-8 h-8 flex items-center justify-center ${formState.currentStep >= 1 ? "bg-[#3d545f] text-white" : "bg-gray-200 text-gray-500"}`}
                >
                  1
                </div>
                <div className={`h-1 w-12 ${formState.currentStep >= 2 ? "bg-[#3d545f]" : "bg-gray-200"}`}></div>
                <div
                  className={`rounded-full w-8 h-8 flex items-center justify-center ${formState.currentStep >= 2 ? "bg-[#3d545f] text-white" : "bg-gray-200 text-gray-500"}`}
                >
                  2
                </div>
                <div className={`h-1 w-12 ${formState.currentStep >= 3 ? "bg-[#3d545f]" : "bg-gray-200"}`}></div>
                <div
                  className={`rounded-full w-8 h-8 flex items-center justify-center ${formState.currentStep >= 3 ? "bg-[#3d545f] text-white" : "bg-gray-200 text-gray-500"}`}
                >
                  3
                </div>
              </div>
              <div className="text-sm text-gray-500">
                {formState.currentStep === 1 && "Upload Transcript"}
                {formState.currentStep === 2 && "Show Details"}
                {formState.currentStep === 3 && "Review & Submit"}
              </div>
            </div>

            {/* Step 1: Transcript Upload */}
            <div className="border rounded-lg p-6 bg-white">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-[#3d545f]">Add Transcript</h2>
                {formState.processingComplete && <CheckCircle2 className="h-6 w-6 text-green-500" />}
              </div>

              <p className="text-gray-600 mb-4">
                Add your podcast transcript to begin. You can paste the text directly or upload a file.
              </p>

              <Tabs
                defaultValue="paste"
                value={formState.transcriptInputMethod}
                onValueChange={(value) =>
                  setFormState((prev) => ({ ...prev, transcriptInputMethod: value as "paste" | "upload" }))
                }
                className="mb-6"
              >
                <TabsList className="grid w-full grid-cols-2 mb-4">
                  <TabsTrigger value="paste" className="flex items-center gap-2">
                    <Type className="h-4 w-4" />
                    Paste Text
                  </TabsTrigger>
                  <TabsTrigger value="upload" className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Upload File
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="paste" className="space-y-4">
                  <Textarea
                    placeholder="Paste your transcript here..."
                    className="min-h-[200px] font-mono text-sm"
                    value={podcast.pastedTranscript}
                    onChange={handlePastedTranscriptChange}
                    disabled={formState.processingTranscript || formState.processingComplete}
                  />
                </TabsContent>

                <TabsContent value="upload" className="space-y-4">
                  <div className="flex items-center space-x-4">
                    <Input
                      id="transcript"
                      type="file"
                      accept=".txt,.doc,.docx,.pdf"
                      onChange={handleTranscriptChange}
                      className="flex-1"
                      disabled={formState.processingTranscript || formState.processingComplete}
                    />
                  </div>
                  {transcriptFile && <p className="text-sm text-green-600">File selected: {transcriptFile.name}</p>}
                </TabsContent>
              </Tabs>

              <div className="flex flex-col space-y-4">
                <Button
                  type="button"
                  className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 w-full md:w-auto md:self-end"
                  onClick={processTranscript}
                  disabled={!canProcessTranscript || formState.processingTranscript || formState.processingComplete}
                >
                  {formState.processingTranscript ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : formState.processingComplete ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Processed
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2" />
                      Process Transcript
                    </>
                  )}
                </Button>

                {formState.processingTranscript && (
                  <div className="space-y-2">
                    <Progress value={formState.progress} className="h-2" />
                    <p className="text-sm text-gray-500">Analyzing transcript... {formState.progress}%</p>
                  </div>
                )}
              </div>
            </div>

            {/* Step 2: Show Details */}
            <div className={`space-y-6 ${!formState.processingComplete ? "opacity-50 pointer-events-none" : ""}`}>
              {/* Guest Information */}
              <div className="border rounded-lg p-6 bg-white">
                <h2 className="text-xl font-semibold text-[#3d545f] mb-4">Guest Information</h2>

                <div className="space-y-6">
                  <div>
                    <Label htmlFor="guestName" className="text-base font-medium mb-2 block">
                      Guest Name
                    </Label>
                    <Input
                      id="guestName"
                      value={podcast.guestName}
                      onChange={(e) => setPodcast((prev) => ({ ...prev, guestName: e.target.value }))}
                      className="w-full"
                    />
                    <p className="text-xs text-gray-500 mt-1">Auto-detected from transcript</p>
                  </div>

                  <div>
                    <Label className="text-base font-medium mb-2 block">Blog Categories</Label>
                    <p className="text-sm text-gray-600 mb-3">
                      Select categories for this episode. You can select multiple categories.
                    </p>

                    <div className="grid grid-cols-2 gap-3 mb-4">
                      {BLOG_CATEGORIES.map((category) => (
                        <div key={category} className="flex items-center space-x-2">
                          <Checkbox
                            id={`category-${category}`}
                            checked={podcast.selectedCategories.includes(category)}
                            onCheckedChange={(checked) => toggleCategory(category, checked as boolean)}
                          />
                          <Label htmlFor={`category-${category}`} className="text-sm text-gray-700 cursor-pointer">
                            {category}
                          </Label>
                        </div>
                      ))}
                    </div>

                    <div className="flex items-center space-x-2 mt-4 pt-4 border-t">
                      <Checkbox
                        id="createNewCategory"
                        checked={formState.createNewCategory}
                        onCheckedChange={toggleCreateNewCategory}
                      />
                      <Label htmlFor="createNewCategory" className="text-sm text-gray-700 cursor-pointer">
                        Create New Category Based on Guest Name
                      </Label>
                    </div>

                    {formState.createNewCategory && (
                      <div className="mt-3">
                        <Input
                          value={podcast.customCategory}
                          onChange={(e) => setPodcast((prev) => ({ ...prev, customCategory: e.target.value }))}
                          className="w-full"
                          placeholder="Enter custom category name"
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Show Information */}
              <div className="border rounded-lg p-6 bg-white">
                <h2 className="text-xl font-semibold text-[#3d545f] mb-4">Show Information</h2>

                <div className="space-y-6">
                  <div>
                    <Label htmlFor="title" className="text-base font-medium mb-2 block">
                      Show Title
                    </Label>
                    <Input
                      id="title"
                      value={podcast.title}
                      onChange={(e) => setPodcast((prev) => ({ ...prev, title: e.target.value }))}
                      className="w-full"
                      placeholder="Enter a title for this episode"
                    />
                  </div>

                  <div>
                    <Label htmlFor="showNotes" className="text-base font-medium mb-2 block">
                      Show Notes
                    </Label>
                    <Textarea
                      id="showNotes"
                      value={podcast.showNotes}
                      onChange={(e) => setPodcast((prev) => ({ ...prev, showNotes: e.target.value }))}
                      className="w-full h-32"
                    />

                    <div className="flex items-center space-x-4 mt-4">
                      <Input
                        id="showNotesFile"
                        type="file"
                        accept=".txt,.doc,.docx"
                        onChange={handleShowNotesChange}
                        className="flex-1"
                      />
                      <Button type="button" className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">
                        <Upload className="w-4 h-4 mr-2" />
                        Upload Notes
                      </Button>
                    </div>

                    {showNotesFile && (
                      <p className="text-sm text-green-600 mt-2">File selected: {showNotesFile.name}</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Social Outlets */}
              <div className="border rounded-lg p-6 bg-white">
                <h2 className="text-xl font-semibold text-[#3d545f] mb-4">Social Outlets</h2>

                <p className="text-gray-600 mb-6 p-3 bg-blue-50 border border-blue-100 rounded-md">
                  These are the links we found in the transcript. You can edit or add more prior to posting by filling
                  in the appropriate fields.
                </p>

                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <Label htmlFor="website" className="text-base font-medium mb-2 block">
                      Website
                    </Label>
                    <Input
                      id="website"
                      value={podcast.website}
                      onChange={(e) => setPodcast((prev) => ({ ...prev, website: e.target.value }))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <Label htmlFor="theirPodcast" className="text-base font-medium mb-2 block">
                      Their Podcast
                    </Label>
                    <Input
                      id="theirPodcast"
                      value={podcast.theirPodcast}
                      onChange={(e) => setPodcast((prev) => ({ ...prev, theirPodcast: e.target.value }))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <Label htmlFor="instagram" className="text-base font-medium mb-2 block">
                      Instagram
                    </Label>
                    <Input
                      id="instagram"
                      value={podcast.instagram}
                      onChange={(e) => setPodcast((prev) => ({ ...prev, instagram: e.target.value }))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <Label htmlFor="youtube" className="text-base font-medium mb-2 block">
                      YouTube
                    </Label>
                    <Input
                      id="youtube"
                      value={podcast.youtube}
                      onChange={(e) => setPodcast((prev) => ({ ...prev, youtube: e.target.value }))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <Label htmlFor="facebook" className="text-base font-medium mb-2 block">
                      Facebook
                    </Label>
                    <Input
                      id="facebook"
                      value={podcast.facebook}
                      onChange={(e) => setPodcast((prev) => ({ ...prev, facebook: e.target.value }))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <Label htmlFor="linkedin" className="text-base font-medium mb-2 block">
                      LinkedIn
                    </Label>
                    <Input
                      id="linkedin"
                      value={podcast.linkedin}
                      onChange={(e) => setPodcast((prev) => ({ ...prev, linkedin: e.target.value }))}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>

              {/* Top 10 Guest Links */}
              <div className="border rounded-lg p-6 bg-white">
                <div className="flex items-center space-x-2 mb-6">
                  <Checkbox id="includeGuestLinks" checked={true} defaultChecked={true} />
                  <Label htmlFor="includeGuestLinks" className="text-xl font-semibold text-[#3d545f] cursor-pointer">
                    Top 10 Guest Links
                  </Label>
                </div>

                <div className="space-y-4 pl-6 border-l-2 border-[#3d545f]/20">
                  <p className="text-gray-600 mb-2">
                    These are the top links we found online for this guest. Uncheck any links you don't want to include
                    in the list.
                  </p>

                  {guestLinks.map((link, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <Checkbox
                        id={`link-${index}`}
                        checked={link.checked}
                        onCheckedChange={(checked) => toggleGuestLink(index, checked as boolean)}
                      />
                      <Input
                        value={link.url}
                        onChange={(e) => handleGuestLinkChange(index, e.target.value)}
                        className="flex-1"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteGuestLink(index)}
                        className="h-9 w-9 text-red-500 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                        <span className="sr-only">Delete link</span>
                      </Button>
                    </div>
                  ))}
                </div>
              </div>

              {/* White Paper Section */}
              <div className="border rounded-lg p-6 bg-white">
                <div className="flex items-center space-x-2 mb-6">
                  <Checkbox
                    id="includeWhitePaper"
                    checked={formState.includeWhitePaper}
                    onCheckedChange={toggleWhitePaper}
                  />
                  <Label htmlFor="includeWhitePaper" className="text-xl font-semibold text-[#3d545f] cursor-pointer">
                    Add a White Paper
                  </Label>
                </div>

                {formState.includeWhitePaper && (
                  <div className="space-y-6 pl-6 border-l-2 border-[#3d545f]/20">
                    <p className="text-gray-600">
                      Create a white paper based on this podcast episode. Select one or more topics.
                    </p>

                    <div className="grid grid-cols-2 gap-3">
                      {WHITE_PAPER_TOPICS.map((topic) => (
                        <div key={topic} className="flex items-center space-x-2">
                          <Checkbox
                            id={`topic-${topic}`}
                            checked={podcast.selectedWhitePaperTopics.includes(topic)}
                            onCheckedChange={(checked) => toggleWhitePaperTopic(topic, checked as boolean)}
                          />
                          <Label htmlFor={`topic-${topic}`} className="text-sm text-gray-700 cursor-pointer">
                            {topic}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-4 flex justify-end">
              <Button
                onClick={handleSave}
                className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 px-8"
                disabled={!canSubmit}
              >
                <Save className="w-4 h-4 mr-2" />
                Save Episode
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
