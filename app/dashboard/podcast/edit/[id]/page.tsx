"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import Image from "next/image"
import { ArrowLeft, Save, Trash2, FileText, Download, Upload, RefreshCw, ImageIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Header } from "@/components/Header"
import { ContentModificationModal } from "@/components/ContentModificationModal"

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

// Sample podcast data - in a real app, this would come from an API
const SAMPLE_PODCASTS = {
  "podcast-1": {
    id: "podcast-1",
    title: "Tech Insights Weekly",
    excerpt: "A weekly deep dive into emerging technologies and their impact on business and society.",
    thumbnail: "/podcast-setup.png",
    episodeCount: 24,
    guestName: "Dr. Jane Smith",
    selectedCategories: ["Technology", "Innovation"],
    customCategory: "",
    showNotes:
      "In this episode, we discuss the latest advancements in artificial intelligence and machine learning with Dr. Jane Smith, a leading researcher in the field. We explore the ethical implications of AI development and how businesses can responsibly implement these technologies.",
    transcript:
      "Host: Welcome to Tech Insights Weekly. I'm your host, John Doe, and today we're joined by Dr. Jane Smith, a leading researcher in artificial intelligence and machine learning. Dr. Smith, thank you for joining us today.\n\nDr. Smith: Thank you for having me, John. It's a pleasure to be here.\n\nHost: Let's start by discussing the current state of AI development. Where do you see the field right now?\n\nDr. Smith: We're at an interesting inflection point. The advances in large language models and computer vision over the past few years have been remarkable. What used to be theoretical is now being deployed in practical applications across industries.\n\nHost: And what about the ethical considerations?\n\nDr. Smith: That's a critical question. As AI becomes more capable, we need robust frameworks for responsible development...",
    website: "https://example.com",
    theirPodcast: "The Example Show",
    instagram: "@exampleguest",
    youtube: "youtube.com/exampleguest",
    facebook: "facebook.com/exampleguest",
    linkedin: "linkedin.com/in/exampleguest",
    whitePaper: "AI_Ethics_Whitepaper.pdf",
    selectedWhitePaperTopics: ["Ethical Considerations", "Industry Trends and Analysis"],
    guestLinks: [
      { url: "https://example.com/guest-website", checked: true },
      { url: "https://linkedin.com/in/guest-profile", checked: true },
      { url: "https://twitter.com/guesthandle", checked: true },
      { url: "https://youtube.com/c/guestchannel", checked: true },
      { url: "https://medium.com/@guestblog", checked: true },
      { url: "https://github.com/guestdev", checked: false },
      { url: "https://slideshare.net/guestpresentations", checked: true },
    ],
  },
  "podcast-2": {
    id: "podcast-2",
    title: "Marketing Masterminds",
    excerpt: "Interviews with top marketing professionals sharing strategies that drive growth.",
    thumbnail: "/marketing-strategy-meeting.png",
    episodeCount: 18,
    guestName: "Sarah Johnson",
    selectedCategories: ["Marketing", "Business Strategy"],
    customCategory: "",
    showNotes:
      "Welcome to Marketing Masterminds. Today we're joined by Sarah Johnson, CMO of GrowthCo, who shares her insights on content-driven acquisition strategies and how they've transformed their customer journey.",
    transcript:
      "Host: Welcome to Marketing Masterminds. I'm your host, Michael Brown, and today we're joined by Sarah Johnson, CMO of GrowthCo. Sarah, welcome to the show.\n\nSarah: Thanks for having me, Michael. Excited to be here.\n\nHost: Let's dive right in. You've been leading some innovative content-driven acquisition strategies at GrowthCo. Can you tell us about your approach?",
    website: "https://growthco.com",
    theirPodcast: "Growth Insights",
    instagram: "@sarahjohnson",
    youtube: "youtube.com/sarahjohnson",
    facebook: "facebook.com/sarahjohnsonmarketing",
    linkedin: "linkedin.com/in/sarahjohnson",
    whitePaper: "Content_Acquisition_Strategy.pdf",
    selectedWhitePaperTopics: ["Case Study: Success Stories", "Strategic Planning Framework"],
    guestLinks: [
      { url: "https://growthco.com", checked: true },
      { url: "https://linkedin.com/in/sarahjohnson", checked: true },
      { url: "https://twitter.com/sarahjohnson", checked: true },
      { url: "https://medium.com/@sarahjohnson", checked: true },
    ],
  },
  "podcast-3": {
    id: "podcast-3",
    title: "Future of Work",
    excerpt: "Exploring how technology and culture are reshaping the workplace and workforce.",
    thumbnail: "/abstract-work.png",
    episodeCount: 12,
    guestName: "Alex Chen",
    selectedCategories: ["Business Strategy", "Professional Development", "Leadership"],
    customCategory: "",
    showNotes:
      "In this episode, we explore how remote work is changing company culture and what leaders can do to maintain strong teams across distributed environments with Alex Chen, founder of RemoteFirst.",
    transcript:
      "Host: Hello and welcome to Future of Work. I'm your host, Emily Davis, and today we're talking with Alex Chen, founder of RemoteFirst, a consultancy helping companies transition to distributed work models. Alex, thanks for joining us today.\n\nAlex: Thanks for having me, Emily. Great to be here discussing such a relevant topic.\n\nHost: Remote work has obviously exploded in the past few years. What are you seeing as the biggest challenges companies face when transitioning to distributed teams?",
    website: "https://remotefirst.co",
    theirPodcast: "Distributed",
    instagram: "@alexchen",
    youtube: "youtube.com/alexchen",
    facebook: "facebook.com/alexchen",
    linkedin: "linkedin.com/in/alexchen",
    whitePaper: "Remote_Work_Playbook.pdf",
    selectedWhitePaperTopics: ["Best Practices Guide", "Future Outlook"],
    guestLinks: [
      { url: "https://remotefirst.co", checked: true },
      { url: "https://linkedin.com/in/alexchen", checked: true },
      { url: "https://twitter.com/alexchen", checked: true },
      { url: "https://medium.com/@alexchen", checked: true },
      { url: "https://github.com/alexchen", checked: false },
    ],
  },
}

export default function EditPodcastPage() {
  const params = useParams()
  const router = useRouter()
  const podcastId = params.id as string

  const [podcast, setPodcast] = useState({
    id: "",
    title: "",
    excerpt: "",
    thumbnail: "",
    guestName: "",
    selectedCategories: [] as string[],
    customCategory: "",
    showNotes: "",
    transcript: "",
    website: "",
    theirPodcast: "",
    instagram: "",
    youtube: "",
    facebook: "",
    linkedin: "",
    whitePaper: "",
    selectedWhitePaperTopics: [] as string[],
    guestLinks: [] as { url: string; checked: boolean }[],
  })

  const [isLoading, setIsLoading] = useState(true)
  const [hasWhitePaper, setHasWhitePaper] = useState(false)

  // Modal state
  const [isModificationModalOpen, setIsModificationModalOpen] = useState(false)
  const [modificationContentType, setModificationContentType] = useState<"content" | "image" | "main" | "sub">(
    "content",
  )
  const [modificationTarget, setModificationTarget] = useState<string>("")

  useEffect(() => {
    // In a real app, this would be an API call
    if (podcastId && SAMPLE_PODCASTS[podcastId]) {
      const podcastData = SAMPLE_PODCASTS[podcastId]
      setPodcast(podcastData)
      setHasWhitePaper(!!podcastData.whitePaper)
    }
    setIsLoading(false)
  }, [podcastId])

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

  // Handle guest link change
  const handleGuestLinkChange = (index: number, value: string) => {
    setPodcast((prev) => {
      const newLinks = [...prev.guestLinks]
      newLinks[index] = { ...newLinks[index], url: value }
      return {
        ...prev,
        guestLinks: newLinks,
      }
    })
  }

  // Toggle guest link checked status
  const toggleGuestLink = (index: number, checked: boolean) => {
    setPodcast((prev) => {
      const newLinks = [...prev.guestLinks]
      newLinks[index] = { ...newLinks[index], checked }
      return {
        ...prev,
        guestLinks: newLinks,
      }
    })
  }

  // Delete guest link
  const deleteGuestLink = (index: number) => {
    setPodcast((prev) => ({
      ...prev,
      guestLinks: prev.guestLinks.filter((_, i) => i !== index),
    }))
  }

  // Delete white paper
  const deleteWhitePaper = () => {
    setPodcast((prev) => ({
      ...prev,
      whitePaper: "",
      selectedWhitePaperTopics: [],
    }))
    setHasWhitePaper(false)
  }

  // Open modification modal for different content types
  const openModificationModal = (contentType: "content" | "image" | "main" | "sub", target: string) => {
    setModificationContentType(contentType)
    setModificationTarget(target)
    setIsModificationModalOpen(true)
  }

  // Handle regeneration based on user input
  const handleRegenerate = (modifications: string) => {
    console.log(
      `Regenerating ${modificationContentType} for ${modificationTarget} with modifications: ${modifications}`,
    )

    // In a real app, this would call an API to regenerate content
    // For now, we'll simulate the regeneration with placeholder content

    switch (modificationContentType) {
      case "image":
        // Simulate regenerating the thumbnail
        setPodcast((prev) => ({
          ...prev,
          thumbnail: `/placeholder.svg?height=400&width=600&query=${encodeURIComponent(`podcast with ${podcast.guestName} - ${modifications}`)}`,
        }))
        break
      case "content":
        // Handle content regeneration based on target
        if (modificationTarget === "showNotes") {
          setPodcast((prev) => ({
            ...prev,
            showNotes: `${prev.showNotes} (Modified based on: ${modifications})`,
          }))
        } else if (modificationTarget === "transcript") {
          setPodcast((prev) => ({
            ...prev,
            transcript: `${prev.transcript.substring(0, 100)}... (Modified based on: ${modifications})`,
          }))
        } else if (modificationTarget === "excerpt") {
          setPodcast((prev) => ({
            ...prev,
            excerpt: `${prev.excerpt} (Modified based on: ${modifications})`,
          }))
        }
        break
      default:
        break
    }
  }

  // Handle form submission
  const handleSave = async () => {
    // In a real app, this would save to an API
    console.log("Saving podcast:", podcast)

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))

    // Navigate back to podcast list
    router.push("/dashboard?tab=podcast-tools")
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#7A99A8]">
        <Header username="John Doe" />
        <main className="p-6 max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"></div>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <Header username="John Doe" />
      <main className="p-6 max-w-5xl mx-auto space-y-6">
        <div className="flex items-center space-x-4">
          <Button variant="outline" className="bg-white" onClick={() => router.push("/dashboard?tab=podcast-tools")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Shows
          </Button>
          <h1 className="text-3xl font-bold text-white">Edit Episode: {podcast.title}</h1>
        </div>

        <Card>
          <CardContent className="p-6 space-y-8">
            {/* Guest Information */}
            <div className="border rounded-lg p-6 bg-white">
              <h2 className="text-xl font-semibold text-[#3d545f] mb-4">Guest Information</h2>

              <div className="grid md:grid-cols-2 gap-6">
                {/* Thumbnail Section */}
                <div>
                  <Label htmlFor="thumbnail" className="text-base font-medium mb-2 block">
                    Show Thumbnail
                  </Label>
                  <div className="space-y-4">
                    <div className="relative w-full h-48 bg-gray-100 rounded-md overflow-hidden border">
                      {podcast.thumbnail ? (
                        <Image
                          src={podcast.thumbnail || "/placeholder.svg"}
                          alt={podcast.title}
                          fill
                          className="object-cover"
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full">
                          <ImageIcon className="h-12 w-12 text-gray-300" />
                          <span className="sr-only">No image</span>
                        </div>
                      )}
                    </div>
                    <div className="flex space-x-2">
                      <label htmlFor="thumbnail-upload" className="flex-1">
                        <Button
                          type="button"
                          variant="outline"
                          className="w-full"
                          onClick={() => document.getElementById("thumbnail-upload")?.click()}
                        >
                          <Upload className="w-4 h-4 mr-2" />
                          Upload Image
                        </Button>
                        <input
                          id="thumbnail-upload"
                          type="file"
                          accept="image/*"
                          className="hidden"
                          onChange={(e) => {
                            if (e.target.files && e.target.files[0]) {
                              // In a real app, you'd upload the file and get a URL back
                              const objectUrl = URL.createObjectURL(e.target.files[0])
                              setPodcast((prev) => ({ ...prev, thumbnail: objectUrl }))
                            }
                          }}
                        />
                      </label>
                      <Button
                        type="button"
                        variant="outline"
                        className="flex-1"
                        onClick={() => openModificationModal("image", "thumbnail")}
                      >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Regenerate
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        className="aspect-square p-0 h-10 text-red-500"
                        onClick={() => setPodcast((prev) => ({ ...prev, thumbnail: "" }))}
                      >
                        <Trash2 className="w-4 h-4" />
                        <span className="sr-only">Delete</span>
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Guest Name and Categories */}
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

                    {podcast.customCategory && (
                      <div className="mt-4 pt-4 border-t">
                        <Label htmlFor="customCategory" className="text-base font-medium mb-2 block">
                          Custom Category
                        </Label>
                        <Input
                          id="customCategory"
                          value={podcast.customCategory}
                          onChange={(e) => setPodcast((prev) => ({ ...prev, customCategory: e.target.value }))}
                          className="w-full"
                        />
                      </div>
                    )}
                  </div>
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
                  />
                </div>

                <div>
                  <Label htmlFor="excerpt" className="text-base font-medium mb-2 block">
                    Excerpt
                  </Label>
                  <div className="flex space-x-2">
                    <Textarea
                      id="excerpt"
                      value={podcast.excerpt}
                      onChange={(e) => setPodcast((prev) => ({ ...prev, excerpt: e.target.value }))}
                      className="w-full h-24"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      className="h-10"
                      onClick={() => openModificationModal("content", "excerpt")}
                    >
                      <RefreshCw className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            {/* Transcript */}
            <div className="border rounded-lg p-6 bg-white">
              <h2 className="text-xl font-semibold text-[#3d545f] mb-4">Transcript</h2>
              <div className="flex space-x-2">
                <Textarea
                  value={podcast.transcript}
                  onChange={(e) => setPodcast((prev) => ({ ...prev, transcript: e.target.value }))}
                  className="w-full h-64 font-mono text-sm"
                />
                <Button
                  type="button"
                  variant="outline"
                  className="h-10"
                  onClick={() => openModificationModal("content", "transcript")}
                >
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Show Notes */}
            <div className="border rounded-lg p-6 bg-white">
              <h2 className="text-xl font-semibold text-[#3d545f] mb-4">Show Notes</h2>
              <div className="flex space-x-2">
                <Textarea
                  value={podcast.showNotes}
                  onChange={(e) => setPodcast((prev) => ({ ...prev, showNotes: e.target.value }))}
                  className="w-full h-32"
                />
                <Button
                  type="button"
                  variant="outline"
                  className="h-10"
                  onClick={() => openModificationModal("content", "showNotes")}
                >
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Social Outlets */}
            <div className="border rounded-lg p-6 bg-white">
              <h2 className="text-xl font-semibold text-[#3d545f] mb-4">Social Outlets</h2>

              <p className="text-gray-600 mb-6 p-3 bg-blue-50 border border-blue-100 rounded-md">
                These are the links we found in the transcript. You can edit or add more prior to posting by filling in
                the appropriate fields.
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

            {/* Top Guest Links */}
            <div className="border rounded-lg p-6 bg-white">
              <h2 className="text-xl font-semibold text-[#3d545f] mb-4">Top Guest Links</h2>

              <div className="space-y-4">
                <p className="text-gray-600 mb-2">
                  These are the top links we found online for this guest. Uncheck any links you don't want to include in
                  the list.
                </p>

                {podcast.guestLinks.map((link, index) => (
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
            {hasWhitePaper && (
              <div className="border rounded-lg p-6 bg-white">
                <h2 className="text-xl font-semibold text-[#3d545f] mb-4">White Paper</h2>

                <div className="space-y-6">
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-md border">
                    <div className="flex items-center space-x-3">
                      <FileText className="h-8 w-8 text-[#3d545f]" />
                      <div>
                        <p className="font-medium">{podcast.whitePaper}</p>
                        <p className="text-sm text-gray-500">White paper PDF</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button variant="outline" size="sm" className="flex items-center space-x-1">
                        <Download className="h-4 w-4" />
                        <span>Download</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-500 hover:text-red-700 hover:bg-red-50"
                        onClick={deleteWhitePaper}
                      >
                        <Trash2 className="h-4 w-4" />
                        <span className="sr-only">Delete</span>
                      </Button>
                    </div>
                  </div>

                  <div>
                    <Label className="text-base font-medium mb-2 block">White Paper Topics</Label>
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
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div className="pt-4 flex justify-end">
              <Button onClick={handleSave} className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 px-8">
                <Save className="w-4 h-4 mr-2" />
                Save Changes
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>

      {/* Content Modification Modal */}
      <ContentModificationModal
        isOpen={isModificationModalOpen}
        onClose={() => setIsModificationModalOpen(false)}
        onRegenerate={handleRegenerate}
        contentType={modificationContentType}
      />
    </div>
  )
}
