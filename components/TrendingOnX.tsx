"use client";

import { useState } from "react";
import { Search, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface TrendingOnXProps {
  trendingContent: string[];
  onAddToQueue: (
    items: Array<{ id: string; type: string; name: string; source: string }>
  ) => void;
}

export function TrendingOnX({
  trendingContent,
  onAddToQueue,
}: TrendingOnXProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);

  const handleSearch = () => {
    console.log("Searching for:", searchQuery);
  };

  const handleRemoveTopic = (index: number) => {
    const topic = trendingContent[index];
    setSelectedTopics((prev) => prev.filter((t) => t !== topic));
  };

  const handleAddToQueue = () => {
    if (selectedTopics.length === 0) return;

    const existingPayload = localStorage.getItem("contentGenPayload") || "{}";
    let parsedPayload = {};
    try {
      parsedPayload = JSON.parse(existingPayload);
    } catch (e) {
      
      console.error("Failed to parse contentGenPayload:", e);
    }

    const updatedPayload = {
      ...parsedPayload,
      trendingTopic: selectedTopics,
    };
    localStorage.setItem("contentGenPayload", JSON.stringify(updatedPayload));
    console.log("Saved to localStorage:", updatedPayload);

    const queueItems = selectedTopics.map((topic, index) => ({
      id: `trending-x-${index}-${Date.now()}`,
      type: "tweet",
      name: topic,
      source: "X Trending",
    }));

    onAddToQueue(queueItems);
    setSelectedTopics([]);
  };

  const handleToggleTopic = (topic: string) => {
    setSelectedTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic]
    );
  };

  const filteredTopics = searchQuery
    ? trendingContent.filter((topic) =>
      topic.toLowerCase().includes(searchQuery.toLowerCase())
    )
    : trendingContent;

  return (
    <div className="space-y-6">
      <div className="flex space-x-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search trending topics on X..."
            className="w-full pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleSearch();
              }
            }}
          />
        </div>
        <Button onClick={handleSearch}>Search</Button>
      </div>

      <div className="border rounded-md p-4">
        <Label className="mb-2 block">Twitter Trending Posts:</Label>
        {filteredTopics.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {filteredTopics.map((topic, index) => (
              <div
                key={index}
                className={`flex items-center px-3 py-1 rounded-full max-w-lg ${selectedTopics.includes(topic)
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground"
                  }`}
                onClick={() => handleToggleTopic(topic)} // Toggle selection on click
                style={{ cursor: "pointer" }}
              >
                <span className="truncate" title={topic}>
                  {topic.length > 50 ? topic.slice(0, 50) + "..." : topic}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-1 ml-1"
                  onClick={(e) => {
                    e.stopPropagation(); // Prevent triggering toggle
                    handleRemoveTopic(index);
                  }}
                >
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            No trending posts available. Try adjusting your search.
          </p>
        )}
      </div>

      <div className="flex justify-end">
        <Button
          onClick={handleAddToQueue}
          disabled={selectedTopics.length === 0}
        >
          Add Selected to Queue
        </Button>
      </div>
    </div>
  );
}
