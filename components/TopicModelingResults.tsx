"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Check, PlusCircle, RefreshCw, Layers, Info } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

// Sample topic data
const SAMPLE_TOPICS = [
  {
    id: "t1",
    name: "Digital Marketing Strategy",
    keywords: ["marketing", "digital", "strategy", "campaign", "audience"],
    coherence: 0.85,
    coverage: 0.28,
    documents: 12,
  },
  {
    id: "t2",
    name: "Content Creation",
    keywords: ["content", "creation", "writing", "blog", "article"],
    coherence: 0.78,
    coverage: 0.22,
    documents: 9,
  },
  {
    id: "t3",
    name: "Social Media Engagement",
    keywords: ["social", "media", "engagement", "followers", "platform"],
    coherence: 0.72,
    coverage: 0.18,
    documents: 7,
  },
  {
    id: "t4",
    name: "SEO Optimization",
    keywords: ["seo", "search", "optimization", "ranking", "keywords"],
    coherence: 0.68,
    coverage: 0.12,
    documents: 5,
  },
  {
    id: "t5",
    name: "Analytics and Measurement",
    keywords: ["analytics", "measurement", "metrics", "performance", "data"],
    coherence: 0.65,
    coverage: 0.08,
    documents: 3,
  },
  {
    id: "t6",
    name: "Customer Experience",
    keywords: ["customer", "experience", "journey", "satisfaction", "service"],
    coherence: 0.81,
    coverage: 0.06,
    documents: 2,
  },
  {
    id: "t7",
    name: "Brand Development",
    keywords: ["brand", "identity", "awareness", "positioning", "messaging"],
    coherence: 0.76,
    coverage: 0.04,
    documents: 2,
  },
  {
    id: "t8",
    name: "Market Research",
    keywords: ["research", "market", "competitor", "analysis", "trends"],
    coherence: 0.7,
    coverage: 0.02,
    documents: 1,
  },
]

export function TopicModelingResults() {
  const [topics, setTopics] = useState(SAMPLE_TOPICS)
  const [selectedTopics, setSelectedTopics] = useState<Record<string, boolean>>({})
  const [addSuccess, setAddSuccess] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)

  // Parameters for topic modeling
  const [topicCoherence, setTopicCoherence] = useState([0.7])
  const [topicCoverage, setTopicCoverage] = useState([0.6])

  // Handle selecting/deselecting topics
  const handleSelectTopic = (id: string, checked: boolean) => {
    setSelectedTopics((prev) => ({
      ...prev,
      [id]: checked,
    }))
  }

  // Handle selecting all topics
  const handleSelectAll = (checked: boolean) => {
    const newSelected = { ...selectedTopics }

    topics.forEach((topic) => {
      newSelected[topic.id] = checked
    })

    setSelectedTopics(newSelected)
  }

  // Handle adding selected topics to content queue
  const handleAddToQueue = () => {
    // In a real app, this would dispatch to a global state or make an API call
    console.log(
      "Adding to queue:",
      Object.entries(selectedTopics)
        .filter(([_, isSelected]) => isSelected)
        .map(([id]) => id),
    )

    // Show success message
    setAddSuccess(true)
    setTimeout(() => setAddSuccess(false), 3000)

    // Reset selections
    setSelectedTopics({})
  }

  // Handle regenerating topics with new parameters
  const handleRegenerateTopics = async () => {
    setIsRegenerating(true)

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000))

    // Generate new topics based on parameters
    // In a real app, this would call an API with the parameters
    const newTopics = [...SAMPLE_TOPICS].sort(() => 0.5 - Math.random())
    newTopics.forEach((topic) => {
      topic.coherence = Math.max(0.5, Math.min(0.95, topic.coherence + (Math.random() * 0.2 - 0.1)))
    })

    setTopics(newTopics)
    setIsRegenerating(false)
  }

  // Count selected topics
  const selectedCount = Object.values(selectedTopics).filter(Boolean).length

  // Calculate average coherence
  const avgCoherence = topics.reduce((sum, topic) => sum + topic.coherence, 0) / topics.length

  // Calculate total coverage
  const totalCoverage = topics.reduce((sum, topic) => sum + topic.coverage, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <Layers className="h-5 w-5 text-indigo-500" />
          <span className="ml-2">Topic Modeling Results</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {addSuccess && (
          <div className="bg-green-50 border border-green-200 rounded-md p-3 mb-4 flex items-center">
            <Check className="h-5 w-5 text-green-500 mr-2" />
            <p className="text-green-700">Topics successfully added to content queue!</p>
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
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
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="flex items-center">
                        <span className="w-6 h-6 text-green-600 font-bold flex items-center justify-center">C</span>
                        <Info className="w-3 h-3 text-green-600 ml-1" />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">
                        Topic coherence measures how semantically similar the words within a topic are to each other.
                        Higher values indicate more coherent, interpretable topics.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <h4 className="font-medium">Topic Coherence</h4>
              <p className="text-3xl font-bold mt-1 mb-1">{avgCoherence.toFixed(2)}</p>
              <p className="text-sm text-gray-500">Average coherence score</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex flex-col items-center text-center">
              <div className="p-3 rounded-full bg-purple-100 mb-2">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="flex items-center">
                        <span className="w-6 h-6 text-purple-600 font-bold flex items-center justify-center">%</span>
                        <Info className="w-3 h-3 text-purple-600 ml-1" />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">
                        Topic coverage indicates what percentage of your content is represented by each topic. Higher
                        total coverage means your topics capture more of your content's themes.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <h4 className="font-medium">Topic Coverage</h4>
              <p className="text-3xl font-bold mt-1 mb-1">{(totalCoverage * 100).toFixed(0)}%</p>
              <p className="text-sm text-gray-500">Content coverage by topics</p>
            </CardContent>
          </Card>
        </div>

        {/* Topics Identified Section */}
        <div className="mb-6 border rounded-md">
          <div className="bg-gray-50 px-4 py-3 border-b">
            <h3 className="font-medium">Topics Identified</h3>
          </div>
          <div className="p-4">
            <div className="space-y-4">
              {topics.map((topic, index) => (
                <div key={topic.id} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Badge className="mr-2 bg-blue-100 text-blue-800 hover:bg-blue-100">{index + 1}</Badge>
                    <span className="font-medium">{topic.name}</span>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-sm text-gray-500">
                      <span className="font-medium text-gray-700">{(topic.coverage * 100).toFixed(0)}%</span> coverage
                    </div>
                    <div className="text-sm text-gray-500">
                      <span className="font-medium text-gray-700">{topic.coherence.toFixed(2)}</span> coherence
                    </div>
                    <div className="text-sm text-gray-500">
                      <span className="font-medium text-gray-700">{topic.documents}</span> documents
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mb-6 p-4 border rounded-md bg-gray-50">
          <h3 className="text-sm font-medium mb-3">Topic Modeling Parameters</h3>

          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between">
                <Label htmlFor="topic-coherence">Topic Coherence: {topicCoherence[0].toFixed(2)}</Label>
              </div>
              <Slider
                id="topic-coherence"
                min={0.1}
                max={1}
                step={0.01}
                value={topicCoherence}
                onValueChange={setTopicCoherence}
              />
              <p className="text-xs text-gray-500">
                Higher values produce more coherent topics with closely related terms.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <Label htmlFor="topic-coverage">Topic Coverage: {topicCoverage[0].toFixed(2)}</Label>
              </div>
              <Slider
                id="topic-coverage"
                min={0.1}
                max={1}
                step={0.01}
                value={topicCoverage}
                onValueChange={setTopicCoverage}
              />
              <p className="text-xs text-gray-500">
                Higher values ensure broader coverage of the content in the identified topics.
              </p>
            </div>

            <Button onClick={handleRegenerateTopics} disabled={isRegenerating} variant="outline" className="w-full">
              {isRegenerating ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Regenerating Topics...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Regenerate Topics
                </>
              )}
            </Button>
          </div>
        </div>

        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center space-x-2">
            <Checkbox id="select-all-topics" onCheckedChange={(checked) => handleSelectAll(!!checked)} />
            <Label htmlFor="select-all-topics">Select All</Label>
          </div>
          <Button
            size="sm"
            onClick={handleAddToQueue}
            disabled={selectedCount === 0}
            className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
          >
            <PlusCircle className="h-4 w-4 mr-2" />
            Add Selected to Content Queue ({selectedCount})
          </Button>
        </div>

        <div className="space-y-3">
          {topics.map((topic) => (
            <div key={topic.id} className="p-3 border rounded-md">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <Checkbox
                    id={topic.id}
                    checked={selectedTopics[topic.id] || false}
                    onCheckedChange={(checked) => handleSelectTopic(topic.id, !!checked)}
                  />
                  <Label htmlFor={topic.id} className="ml-3 font-medium cursor-pointer">
                    {topic.name}
                  </Label>
                </div>
                <Badge variant="outline" className="bg-indigo-50">
                  Coherence: {topic.coherence.toFixed(2)}
                </Badge>
              </div>
              <div className="ml-7">
                <div className="flex flex-wrap gap-1 mt-1">
                  {topic.keywords.map((keyword, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
