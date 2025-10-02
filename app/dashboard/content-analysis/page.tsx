"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ResearchAssistant } from "@/components/ResearchAssistant"
import { ContentQueue } from "@/components/ContentQueue"

// Sample campaign data
const campaign = {
  id: "1",
  name: "Q1 Marketing Campaign",
  description: "Comprehensive marketing campaign for Q1 2023",
  startDate: "2023-01-01",
  endDate: "2023-03-31",
  status: "active",
  platforms: ["Instagram", "Facebook", "Twitter", "LinkedIn"],
  budget: 5000,
  goals: ["Increase brand awareness", "Generate leads", "Drive website traffic"],
  targetAudience: ["25-34", "35-44"],
  keywords: ["marketing", "digital", "strategy", "content"],
  metrics: {
    impressions: 250000,
    clicks: 15000,
    conversions: 500,
    engagement: 8.5,
  },
}

export default function ContentAnalysisPage() {
  const [activeTab, setActiveTab] = useState("basic-settings")
  const [queueItems, setQueueItems] = useState<Array<{ id: string; type: string; name: string; source: string }>>([
    {
      id: "demo-keyword-marketing",
      type: "keyword",
      name: "marketing",
      source: "Word Cloud",
    },
    {
      id: "demo-sentiment-content",
      type: "micro-sentiment",
      name: "Content: Positive Sentiment",
      source: "Micro Sentiments",
    },
    {
      id: "demo-topic-digital-channels",
      type: "topic",
      name: "Digital Channels",
      source: "Topical Map",
    },
    {
      id: "demo-hashtag-digitalMarketing",
      type: "hashtag",
      name: "#DigitalMarketing",
      source: "Hashtag Generator",
    },
  ])

  const handleAddToQueue = (items: Array<{ id: string; type: string; name: string; source: string }>) => {
    setQueueItems((prev) => {
      // Filter out duplicates
      const newItems = items.filter((item) => !prev.some((prevItem) => prevItem.id === item.id))
      return [...prev, ...newItems]
    })
    // Switch to the content queue tab
    setActiveTab("content-queue")
  }

  const handleClearQueue = () => {
    setQueueItems([])
  }

  return (
    <div className="container mx-auto py-6">
      <h1 className="text-3xl font-bold mb-6">Content Analysis</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid grid-cols-4 mb-6">
          <TabsTrigger value="basic-settings">Basic Settings</TabsTrigger>
          <TabsTrigger value="advanced-settings">Advanced Settings</TabsTrigger>
          <TabsTrigger value="research-assistant">Research Assistant</TabsTrigger>
          <TabsTrigger value="content-queue">Content Queue</TabsTrigger>
        </TabsList>

        <TabsContent value="basic-settings">
          <div className="p-6 bg-white rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">Basic Settings</h2>
            <p className="text-gray-500">Configure the basic settings for your content analysis.</p>
          </div>
        </TabsContent>

        <TabsContent value="advanced-settings">
          <div className="p-6 bg-white rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">Advanced Settings</h2>
            <p className="text-gray-500">Configure advanced settings for your content analysis.</p>
          </div>
        </TabsContent>

        <TabsContent value="research-assistant">
          <ResearchAssistant campaign={campaign} onAddToQueue={handleAddToQueue} />
        </TabsContent>

        <TabsContent value="content-queue">
          <ContentQueue queueItems={queueItems} onClearQueue={handleClearQueue} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
