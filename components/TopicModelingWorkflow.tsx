"use client"

import { Badge } from "@/components/ui/badge"

import { Checkbox } from "@/components/ui/checkbox"

import { Button } from "@/components/ui/button"

import { Slider } from "@/components/ui/slider"

import { Label } from "@/components/ui/label"

import { CardTitle } from "@/components/ui/card"

import { CardContent } from "@/components/ui/card"

import { CardHeader } from "@/components/ui/card"

import { Card } from "@/components/ui/card"

import { useState } from "react"

// Replace the placeholder implementation with a full implementation that includes checkboxes for topics

function TopicModelingWorkflow({ copyAnchorLink }: SectionProps) {
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [topicCoherence, setTopicCoherence] = useState(0.82)
  const [topicCoverage, setTopicCoverage] = useState(94)
  const [isRegenerating, setIsRegenerating] = useState(false)

  // Sample topic data
  const [topics, setTopics] = useState([
    {
      name: "Digital Marketing Strategy",
      keywords: ["strategy", "digital", "marketing", "campaign", "planning"],
      percentage: 28,
      coherence: 0.87,
    },
    {
      name: "Content Creation",
      keywords: ["content", "creation", "blog", "article", "video"],
      percentage: 22,
      coherence: 0.85,
    },
    {
      name: "Social Media Marketing",
      keywords: ["social", "media", "platform", "engagement", "followers"],
      percentage: 18,
      coherence: 0.79,
    },
    {
      name: "Analytics & Reporting",
      keywords: ["analytics", "data", "metrics", "reporting", "insights"],
      percentage: 12,
      coherence: 0.83,
    },
    {
      name: "Customer Engagement",
      keywords: ["customer", "engagement", "experience", "journey", "satisfaction"],
      percentage: 8,
      coherence: 0.76,
    },
  ])

  const handleTopicSelection = (topic: string) => {
    setSelectedTopics((prev) => {
      if (prev.includes(topic)) {
        return prev.filter((t) => t !== topic)
      } else {
        return [...prev, topic]
      }
    })
  }

  const handleSaveToContentQueue = () => {
    // In a real app, this would send the data to a global state or backend
    console.log("Saved to content queue:", selectedTopics)

    // Show success message
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3000)
  }

  const handleRegenerateTopics = async () => {
    setIsRegenerating(true)

    // Simulate API call to regenerate topics with new parameters
    await new Promise((resolve) => setTimeout(resolve, 2000))

    // Update topics with "new" data
    const newTopics = [
      ...topics.slice(0, 3),
      {
        name: "Content Distribution",
        keywords: ["distribution", "channels", "audience", "reach", "promotion"],
        percentage: 14,
        coherence: 0.81,
      },
      {
        name: "Brand Awareness",
        keywords: ["brand", "awareness", "recognition", "identity", "positioning"],
        percentage: 10,
        coherence: 0.78,
      },
    ]

    setTopics(newTopics)
    setTopicCoherence(0.85)
    setTopicCoverage(96)
    setIsRegenerating(false)
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <SectionHeader
            id="topic-modeling"
            title="Topic Modeling"
            description="The process of discovering abstract topics in a collection of documents"
            copyAnchorLink={copyAnchorLink}
          />
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Topic Overview - Keep existing content */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-4 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-blue-100 mb-2">
                  <Layers className="w-6 h-6 text-blue-600" />
                </div>
                <h4 className="font-medium">Topics Identified</h4>
                <p className="text-3xl font-bold mt-1 mb-1">{topics.length}</p>
                <p className="text-sm text-gray-500">Distinct thematic clusters</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-green-100 mb-2">
                  <Bookmark className="w-6 h-6 text-green-600" />
                </div>
                <h4 className="font-medium">Topic Coherence</h4>
                <p className="text-3xl font-bold mt-1 mb-1">{topicCoherence.toFixed(2)}</p>
                <p className="text-sm text-gray-500">Average coherence score</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-purple-100 mb-2">
                  <Lightbulb className="w-6 h-6 text-purple-600" />
                </div>
                <h4 className="font-medium">Topic Coverage</h4>
                <p className="text-3xl font-bold mt-1 mb-1">{topicCoverage}%</p>
                <p className="text-sm text-gray-500">Content coverage by topics</p>
              </CardContent>
            </Card>
          </div>

          {/* Topic Regeneration Controls */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Adjust Topic Parameters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <Label htmlFor="topic-coherence">Topic Coherence</Label>
                    <span className="text-sm font-medium">{topicCoherence.toFixed(2)}</span>
                  </div>
                  <Slider
                    id="topic-coherence"
                    min={0.5}
                    max={1}
                    step={0.01}
                    value={[topicCoherence]}
                    onValueChange={(value) => setTopicCoherence(value[0])}
                  />
                  <p className="text-sm text-gray-500">
                    Higher values prioritize more coherent topics (topics with more closely related terms)
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between">
                    <Label htmlFor="topic-coverage">Topic Coverage</Label>
                    <span className="text-sm font-medium">{topicCoverage}%</span>
                  </div>
                  <Slider
                    id="topic-coverage"
                    min={70}
                    max={100}
                    step={1}
                    value={[topicCoverage]}
                    onValueChange={(value) => setTopicCoverage(value[0])}
                  />
                  <p className="text-sm text-gray-500">
                    Higher values ensure more content is assigned to topics, but may reduce topic distinctiveness
                  </p>
                </div>

                <Button
                  onClick={handleRegenerateTopics}
                  className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                  disabled={isRegenerating}
                >
                  {isRegenerating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Regenerating Topics...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Regenerate Topics with New Parameters
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Topic Selection for Content Queue */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Add Topics to Content Queue</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="grid grid-cols-1 gap-4">
                  {topics.map((topic, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-3">
                          <Checkbox
                            id={`topic-${index}`}
                            checked={selectedTopics.includes(topic.name)}
                            onCheckedChange={() => handleTopicSelection(topic.name)}
                            className="mt-1"
                          />
                          <div>
                            <label
                              htmlFor={`topic-${index}`}
                              className="text-md font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                            >
                              {topic.name}
                            </label>
                            <div className="mt-2 flex flex-wrap gap-1">
                              {topic.keywords.map((keyword, kidx) => (
                                <Badge key={kidx} className="bg-blue-50 text-blue-600">
                                  {keyword}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-lg font-semibold">{topic.percentage}%</span>
                          <div className="text-sm text-gray-500">Coherence: {topic.coherence.toFixed(2)}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex justify-between items-center pt-4">
                  <div>
                    {saveSuccess && (
                      <div className="text-green-600 flex items-center">
                        <Check className="w-4 h-4 mr-1" />
                        Added to content queue
                      </div>
                    )}
                  </div>
                  <Button
                    onClick={handleSaveToContentQueue}
                    className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                    disabled={selectedTopics.length === 0}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Selected to Content Queue
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </CardContent>
      </Card>
    </div>
  )
}
