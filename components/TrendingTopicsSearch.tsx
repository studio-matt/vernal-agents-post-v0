"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Twitter, TrendingUp, Search } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"

interface TrendingTopic {
  id: string
  name: string
  volume: number
  sentiment: "positive" | "neutral" | "negative"
  category: string
}

interface TrendingTopicsSearchProps {
  onAddTopics: (topics: string[]) => void
}

export function TrendingTopicsSearch({ onAddTopics }: TrendingTopicsSearchProps) {
  const [searchKeyword, setSearchKeyword] = useState("")
  const [isSearching, setIsSearching] = useState(false)
  const [trendingTopics, setTrendingTopics] = useState<TrendingTopic[]>([])
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])

  const handleSearch = () => {
    if (!searchKeyword.trim()) return

    setIsSearching(true)

    // Simulate API call with timeout
    setTimeout(() => {
      // Mock data - in a real app, this would come from the X API
      const mockTopics: TrendingTopic[] = [
        {
          id: `${searchKeyword}-1`,
          name: `#${searchKeyword}Trends`,
          volume: 12500,
          sentiment: "positive",
          category: "Technology",
        },
        {
          id: `${searchKeyword}-2`,
          name: `${searchKeyword} News`,
          volume: 8700,
          sentiment: "neutral",
          category: "News",
        },
        {
          id: `${searchKeyword}-3`,
          name: `${searchKeyword} Updates`,
          volume: 5300,
          sentiment: "positive",
          category: "Updates",
        },
        {
          id: `${searchKeyword}-4`,
          name: `${searchKeyword} 2025`,
          volume: 3200,
          sentiment: "neutral",
          category: "Future",
        },
        {
          id: `${searchKeyword}-5`,
          name: `${searchKeyword} Problems`,
          volume: 2100,
          sentiment: "negative",
          category: "Issues",
        },
        {
          id: `${searchKeyword}-6`,
          name: `${searchKeyword} Solutions`,
          volume: 1800,
          sentiment: "positive",
          category: "Solutions",
        },
      ]

      setTrendingTopics(mockTopics)
      setIsSearching(false)
    }, 1500)
  }

  const handleTopicSelection = (topicName: string) => {
    setSelectedTopics((prev) =>
      prev.includes(topicName) ? prev.filter((name) => name !== topicName) : [...prev, topicName],
    )
  }

  const handleAddSelectedTopics = () => {
    if (selectedTopics.length > 0) {
      onAddTopics(selectedTopics)
      setSelectedTopics([])
    }
  }

  const getSentimentColor = (sentiment: "positive" | "neutral" | "negative") => {
    switch (sentiment) {
      case "positive":
        return "text-green-500"
      case "negative":
        return "text-red-500"
      default:
        return "text-gray-500"
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-2">
        <div className="relative flex-1">
          <Input
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            placeholder="Enter keyword to find trending topics on X"
            className="pr-10"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault()
                handleSearch()
              }
            }}
          />
          <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        </div>
        <Button
          onClick={handleSearch}
          disabled={isSearching || !searchKeyword.trim()}
          className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
        >
          {isSearching ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Searching...
            </>
          ) : (
            <>
              <Twitter className="w-4 h-4 mr-2" />
              Search
            </>
          )}
        </Button>
      </div>

      {isSearching && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-6 w-3/4 mb-2" />
                <Skeleton className="h-4 w-1/2 mb-2" />
                <Skeleton className="h-4 w-1/4" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!isSearching && trendingTopics.length > 0 && (
        <>
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium">Trending Topics for "{searchKeyword}"</h3>
            {selectedTopics.length > 0 && (
              <Button onClick={handleAddSelectedTopics} className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">
                <TrendingUp className="w-4 h-4 mr-2" />
                Add Selected ({selectedTopics.length})
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {trendingTopics.map((topic) => (
              <Card
                key={topic.id}
                className={`cursor-pointer transition-all ${
                  selectedTopics.includes(topic.name) ? "ring-2 ring-[#3d545f] ring-opacity-50" : "hover:shadow-md"
                }`}
                onClick={() => handleTopicSelection(topic.name)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-medium">{topic.name}</h4>
                      <div className="flex items-center mt-1 text-sm text-gray-500">
                        <span className="bg-secondary text-secondary-foreground text-xs px-2 py-1 rounded-full mr-2">
                          {topic.category}
                        </span>
                        <span className={`flex items-center ${getSentimentColor(topic.sentiment)}`}>
                          {topic.sentiment === "positive" && "↑"}
                          {topic.sentiment === "negative" && "↓"}
                          {topic.sentiment}
                        </span>
                      </div>
                      <p className="text-sm mt-2">
                        <span className="font-semibold">{topic.volume.toLocaleString()}</span> engagements
                      </p>
                    </div>
                    <div className="flex items-center h-5">
                      <input
                        type="checkbox"
                        checked={selectedTopics.includes(topic.name)}
                        onChange={() => {}} // Handled by the card click
                        onClick={(e) => e.stopPropagation()}
                        className="h-4 w-4 rounded border-gray-300 text-[#3d545f] focus:ring-[#3d545f]"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      {!isSearching && searchKeyword && trendingTopics.length === 0 && (
        <div className="text-center py-8">
          <Twitter className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium mb-2">No trending topics found</h3>
          <p className="text-gray-500">Try a different keyword or check back later</p>
        </div>
      )}
    </div>
  )
}
