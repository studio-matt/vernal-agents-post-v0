"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Loader2,
  CloudRain,
  BarChart2,
  Network,
  Hash,
  Brain,
} from "lucide-react";
import type { Campaign } from "./ContentPlannerCampaign";
import { Checkbox } from "@/components/ui/checkbox";

interface ResearchAssistantProps {
  campaign: Campaign;
  onAddToQueue: (
    items: Array<{ id: string; type: string; name: string; source: string }>
  ) => void;
}

export function ResearchAssistant({
  campaign,
  onAddToQueue,
}: ResearchAssistantProps) {
  const [activeTab, setActiveTab] = useState("word-cloud");
  const [isLoading, setIsLoading] = useState(false);
  const [hasResults, setHasResults] = useState(true);
  const [selectedItems, setSelectedItems] = useState<
    Array<{ id: string; type: string; name: string; source: string }>
  >([
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
  ]);
  const [showAddToQueueButton, setShowAddToQueueButton] = useState(true);
  const [storeAllValues, setstoreAllValues] = useState<{ [key: string]: any }>(
    {}
  );

  const handleRunAnalysis = () => {
    setIsLoading(true);

    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      setHasResults(true);
    }, 2000);
  };

  const handleItemSelect = (
    item: { id: string; type: string; name: string; source: string },
    isSelected: boolean
  ) => {
    if (isSelected) {
      setSelectedItems((prev) => [...prev, item]);
      setShowAddToQueueButton(true);
    } else {
      setSelectedItems((prev) => prev.filter((i) => i.id !== item.id));
      if (selectedItems.length <= 1) {
        setShowAddToQueueButton(false);
      }
    }
  };

  const handleAddToQueue = () => {
    // Pass the selected items to the parent component
    onAddToQueue(selectedItems);
    setSelectedItems([]);
    setShowAddToQueueButton(false);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center">
            <Brain className="w-5 h-5 mr-2" />
            Research Assistant
          </CardTitle>
          <div className="flex space-x-2">
            <Button
              onClick={handleRunAnalysis}
              disabled={isLoading}
              className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>{hasResults ? "Re-Run Analysis" : "Run Analysis"}</>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {hasResults ? (
            <div className="space-y-6">
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="w-full mb-4">
                  <TabsTrigger value="word-cloud" className="flex-1">
                    <CloudRain className="w-4 h-4 mr-2" />
                    Word Cloud
                  </TabsTrigger>
                  <TabsTrigger value="micro-sentiment" className="flex-1">
                    <BarChart2 className="w-4 h-4 mr-2" />
                    Micro Sentiment
                  </TabsTrigger>
                  <TabsTrigger value="topical-map" className="flex-1">
                    <Network className="w-4 h-4 mr-2" />
                    Topical Map
                  </TabsTrigger>
                  <TabsTrigger value="knowledge-graph" className="flex-1">
                    <Network className="w-4 h-4 mr-2" />
                    Knowledge Graph
                  </TabsTrigger>
                  <TabsTrigger value="hashtag-generator" className="flex-1">
                    <Hash className="w-4 h-4 mr-2" />
                    Hashtag Generator
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="word-cloud">
                  <WordCloudContent
                    campaign={campaign}
                    handleItemSelect={handleItemSelect}
                    setstoreAllValues={setstoreAllValues}
                  />
                </TabsContent>

                <TabsContent value="micro-sentiment">
                  <MicroSentimentContent
                    campaign={campaign}
                    handleItemSelect={handleItemSelect}
                    setstoreAllValues={setstoreAllValues}
                  />
                </TabsContent>

                <TabsContent value="topical-map">
                  <TopicalMapContent
                    campaign={campaign}
                    onSelectItem={handleItemSelect}
                    setstoreAllValues={setstoreAllValues}
                  />
                </TabsContent>

                <TabsContent value="knowledge-graph">
                  <KnowledgeGraphContent
                    campaign={campaign}
                    handleItemSelect={handleItemSelect}
                    setstoreAllValues={setstoreAllValues}
                  />
                </TabsContent>

                <TabsContent value="hashtag-generator">
                  <HashtagGeneratorContent
                    campaign={campaign}
                    handleItemSelect={handleItemSelect}
                    setstoreAllValues={setstoreAllValues}
                  />
                </TabsContent>
              </Tabs>
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="bg-gray-100 rounded-full p-6 inline-block mb-4">
                <Brain className="w-12 h-12 text-gray-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Research Assistant</h3>
              <p className="text-gray-500 mb-6 max-w-md mx-auto">
                Run the research assistant to analyze your campaign content and
                generate insights, visualizations, and recommendations.
              </p>
              <Button
                onClick={handleRunAnalysis}
                disabled={isLoading}
                className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  "Run Analysis"
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
      {showAddToQueueButton && (
        <div className="fixed bottom-6 right-6 z-50">
          <Button
            onClick={handleAddToQueue}
            className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 shadow-lg"
          >
            Add {selectedItems.length} item
            {selectedItems.length !== 1 ? "s" : ""} to Content Queue
          </Button>
        </div>
      )}
    </div>
  );
}

interface ContentProps {
  campaign: Campaign;
  onSelectItem?: (
    item: { id: string; type: string; name: string; source: string },
    isSelected: boolean
  ) => void;
}

function WordCloudContent({
  campaign,
  handleItemSelect,
  setstoreAllValues,
}: {
  campaign: Campaign;
  handleItemSelect: (item: any, isSelected: boolean) => void;
  setstoreAllValues: React.Dispatch<
    React.SetStateAction<{ [key: string]: any }>
  >;
}) {
  // Add useEffect to trigger handleItemSelect for all items on initial render
  const [checkedItems, setCheckedItems] = useState<{ [key: string]: boolean }>(
    {}
  );
  const keywords = [
    { id: "marketing", name: "marketing", count: 42 },
    { id: "content", name: "content", count: 36 },
    { id: "strategy", name: "strategy", count: 31 },
    { id: "digital", name: "digital", count: 28 },
    { id: "social", name: "social", count: 24 },
    { id: "analytics", name: "analytics", count: 21 },
    { id: "engagement", name: "engagement", count: 18 },
    { id: "audience", name: "audience", count: 15 },
    { id: "campaign", name: "campaign", count: 12 },
    { id: "brand", name: "brand", count: 9 },
    { id: "conversion", name: "conversion", count: 6 },
    { id: "optimization", name: "optimization", count: 3 },
  ];

  const [allTopics, setAllTopics] = useState([]);

  useEffect(() => {
    const stored = localStorage.getItem("topics");
    if (stored) {
      const parsed: string[] = JSON.parse(stored);
      setAllTopics(parsed);

      // // Initialize all keywords as unchecked
      // const initialCheckedState = parsed.reduce((acc, keyword) => {
      //   acc[`keyword-${keyword}`] = false
      //   return acc
      // }, {} as { [key: string]: boolean })

      // setCheckedItems(initialCheckedState)
    }
  }, []);

  const handleCheckboxChange = (keyword: string, checked: boolean) => {
    const id = `keyword-${keyword}`;
    setCheckedItems((prev) => ({ ...prev, [id]: checked }));

    const keywordData = {
      id,
      type: "keyword",
      name: keyword,
      source: "Word Cloud",
    };

    handleItemSelect(keywordData, checked);

    setstoreAllValues((prev: any) => {
      const prevTopics: string[] = prev.topics || [];

      if (checked) {
        // Add keyword if not already present
        if (!prevTopics.includes(keyword)) {
          return {
            ...prev,
            topKeyword: [...prevTopics, keyword],
          };
        }
        return prev; // No change if already present
      } else {
        // Remove keyword if it exists
        return {
          ...prev,
          topics: prevTopics.filter((item) => item !== keyword),
        };
      }
    });
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Keyword Word Cloud</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[400px] flex items-center justify-center bg-gray-50 rounded-md border">
            <div className="relative w-full h-full p-8">
              {/* Simulated word cloud */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-4xl font-bold text-blue-600">
                marketing
              </div>
              <div className="absolute top-[30%] left-[30%] -translate-x-1/2 -translate-y-1/2 text-3xl font-bold text-green-600">
                content
              </div>
              <div className="absolute top-[40%] left-[60%] -translate-x-1/2 -translate-y-1/2 text-3xl font-bold text-purple-600">
                strategy
              </div>
              <div className="absolute top-[60%] left-[40%] -translate-x-1/2 -translate-y-1/2 text-2xl font-bold text-yellow-600">
                digital
              </div>
              <div className="absolute top-[70%] left-[70%] -translate-x-1/2 -translate-y-1/2 text-2xl font-bold text-red-600">
                social
              </div>
              <div className="absolute top-[20%] left-[50%] -translate-x-1/2 -translate-y-1/2 text-xl font-bold text-teal-600">
                analytics
              </div>
              <div className="absolute top-[80%] left-[30%] -translate-x-1/2 -translate-y-1/2 text-xl font-bold text-indigo-600">
                engagement
              </div>
              <div className="absolute top-[50%] left-[20%] -translate-x-1/2 -translate-y-1/2 text-lg font-bold text-orange-600">
                audience
              </div>
              <div className="absolute top-[40%] left-[80%] -translate-x-1/2 -translate-y-1/2 text-lg font-bold text-pink-600">
                campaign
              </div>
              <div className="absolute top-[25%] left-[75%] -translate-x-1/2 -translate-y-1/2 text-base font-bold text-gray-600">
                brand
              </div>
              <div className="absolute top-[65%] left-[60%] -translate-x-1/2 -translate-y-1/2 text-base font-bold text-cyan-600">
                conversion
              </div>
              <div className="absolute top-[75%] left-[50%] -translate-x-1/2 -translate-y-1/2 text-base font-bold text-emerald-600">
                optimization
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Keywords</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center">
                  <Checkbox
                    id="keyword-marketing"
                    checked={checkedItems["keyword-marketing"]}
                    onCheckedChange={(checked) => {
                      setCheckedItems((prev) => ({ ...prev, "keyword-marketing": !!checked }))
                      handleItemSelect(
                        {
                          id: "keyword-marketing",
                          type: "keyword",
                          name: "marketing",
                          source: "Word Cloud",
                        },
                        !!checked,
                      )
                    }}
                    className="mr-2"
                  />
                  <label htmlFor="keyword-marketing">marketing</label>
                </div>
                <span className="font-medium">42</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full" style={{ width: "100%" }}></div>
              </div>

              <div className="flex justify-between items-center">
                <div className="flex items-center">
                  <Checkbox
                    id="keyword-content"
                    checked={checkedItems["keyword-content"]}
                    onCheckedChange={(checked) => {
                      setCheckedItems((prev) => ({ ...prev, "keyword-content": !!checked }))
                      handleItemSelect(
                        {
                          id: "keyword-content",
                          type: "keyword",
                          name: "content",
                          source: "Word Cloud",
                        },
                        !!checked,
                      )
                    }}
                    className="mr-2"
                  />
                  <label htmlFor="keyword-content">content</label>
                </div>
                <span className="font-medium">36</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-green-600 h-2 rounded-full" style={{ width: "85%" }}></div>
              </div>

              <div className="flex justify-between items-center">
                <div className="flex items-center">
                  <Checkbox
                    id="keyword-strategy"
                    checked={checkedItems["keyword-strategy"]}
                    onCheckedChange={(checked) => {
                      setCheckedItems((prev) => ({ ...prev, "keyword-strategy": !!checked }))
                      handleItemSelect(
                        {
                          id: "keyword-strategy",
                          type: "keyword",
                          name: "strategy",
                          source: "Word Cloud",
                        },
                        !!checked,
                      )
                    }}
                    className="mr-2"
                  />
                  <label htmlFor="keyword-strategy">strategy</label>
                </div>
                <span className="font-medium">31</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-purple-600 h-2 rounded-full" style={{ width: "74%" }}></div>
              </div>

              <div className="flex justify-between items-center">
                <div className="flex items-center">
                  <Checkbox
                    id="keyword-digital"
                    checked={checkedItems["keyword-digital"]}
                    onCheckedChange={(checked) => {
                      setCheckedItems((prev) => ({ ...prev, "keyword-digital": !!checked }))
                      handleItemSelect(
                        {
                          id: "keyword-digital",
                          type: "keyword",
                          name: "digital",
                          source: "Word Cloud",
                        },
                        !!checked,
                      )
                    }}
                    className="mr-2"
                  />
                  <label htmlFor="keyword-digital">digital</label>
                </div>
                <span className="font-medium">28</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-yellow-600 h-2 rounded-full" style={{ width: "67%" }}></div>
              </div>

              <div className="flex justify-between items-center">
                <div className="flex items-center">
                  <Checkbox
                    id="keyword-social"
                    checked={checkedItems["keyword-social"]}
                    onCheckedChange={(checked) => {
                      setCheckedItems((prev) => ({ ...prev, "keyword-social": !!checked }))
                      handleItemSelect(
                        {
                          id: "keyword-social",
                          type: "keyword",
                          name: "social",
                          source: "Word Cloud",
                        },
                        !!checked,
                      )
                    }}
                    className="mr-2"
                  />
                  <label htmlFor="keyword-social">social</label>
                </div>
                <span className="font-medium">24</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-red-600 h-2 rounded-full" style={{ width: "57%" }}></div>
              </div>
            </div>
          </CardContent>
        </Card> */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Keywordsff</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-3">
              {allTopics.map((keyword, index) => {
                const id = `keyword-${keyword}`;
                return (
                  <div key={id}>
                    <div className="flex justify-between items-center">
                      <div className="flex items-center">
                        <Checkbox
                          id={id}
                          checked={!!checkedItems[id]}
                          onCheckedChange={(checked) =>
                            handleCheckboxChange(keyword, !!checked)
                          }
                          className="mr-2"
                        />
                        <label htmlFor={id}>{keyword}</label>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Keyword Insights</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                The word cloud analysis reveals a strong focus on{" "}
                <span className="font-medium">marketing strategy</span> and{" "}
                <span className="font-medium">content creation</span> in your
                campaign materials.
              </p>
              <p className="text-sm text-gray-600">
                Consider expanding your content to include more about{" "}
                <span className="font-medium">analytics</span> and{" "}
                <span className="font-medium">audience engagement</span> to
                create a more balanced approach.
              </p>
              <p className="text-sm text-gray-600">
                The term <span className="font-medium">digital</span> appears
                frequently, but specific digital channels like{" "}
                <span className="font-medium">email</span> and{" "}
                <span className="font-medium">mobile</span> are
                underrepresented.
              </p>
              <div className="bg-blue-50 p-3 rounded-md border border-blue-100">
                <h4 className="font-medium text-blue-800 mb-1">
                  Recommendation
                </h4>
                <p className="text-sm text-blue-700">
                  Consider creating content that specifically addresses digital
                  marketing channels and their unique strategies to provide more
                  comprehensive coverage.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MicroSentimentContent({
  campaign,
  handleItemSelect,
}: {
  campaign: Campaign;
  handleItemSelect: (item: any, isSelected: boolean) => void;
}) {
  // Add state for checked items
  const [checkedItems, setCheckedItems] = useState({
    "sentiment-marketing": true,
    "sentiment-content": true,
    "sentiment-strategy": true,
    "sentiment-digital": true,
    "sentiment-social": true,
    positive: true,
    neutral: true,
    negative: true,
  });

  const sentiments = [
    { id: "positive", name: "Positive", percentage: 68 },
    { id: "neutral", name: "Neutral", percentage: 24 },
    { id: "negative", name: "Negative", percentage: 8 },
  ];

  const topicSentiments = [
    { id: "marketing", name: "Marketing", score: 70 },
    { id: "content", name: "Content", score: 75 },
    { id: "strategy", name: "Strategy", score: 55 },
    { id: "digital", name: "Digital", score: 60 },
    { id: "social", name: "Social", score: 50 },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sentiment Analysis</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[400px] flex items-center justify-center bg-gray-50 rounded-md border">
            <div className="w-full max-w-md">
              <div className="mb-8 text-center">
                <div className="text-2xl font-bold mb-2">Overall Sentiment</div>
                <div className="flex items-center justify-center">
                  <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                    <span className="text-2xl text-green-600">+72</span>
                  </div>
                  <div className="ml-4 text-left">
                    <div className="font-medium">Positive</div>
                    <div className="text-sm text-gray-500">
                      Strong positive sentiment
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-6">
                {sentiments.map((sentiment) => (
                  <div key={sentiment.id}>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm">{sentiment.name}</span>
                      <span className="text-sm font-medium">
                        {sentiment.percentage}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div
                        className={`bg-${sentiment.name === "Positive"
                          ? "green-600"
                          : sentiment.name === "Neutral"
                            ? "gray-400"
                            : "red-600"
                          } h-2.5 rounded-full`}
                        style={{ width: `${sentiment.percentage}%` }}
                      ></div>
                    </div>
                    <Checkbox
                      type="checkbox"
                      id={sentiment.id}
                      className="mr-2"
                      checked={checkedItems[sentiment.id]}
                      onChange={(e) => {
                        setCheckedItems((prev) => ({
                          ...prev,
                          [sentiment.id]: !!e.target.checked,
                        }));
                        if (handleItemSelect) {
                          handleItemSelect(
                            {
                              id: sentiment.id,
                              type: "sentiment",
                              name: sentiment.name,
                              source: "micro-sentiment",
                            },
                            e.target.checked
                          );
                        }
                      }}
                    />
                    <label
                      htmlFor={sentiment.id}
                      className="text-sm text-gray-500"
                    >
                      Add to Content Queue
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Sentiment by Topic</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-4">
              <Checkbox
                id="sentiment-marketing"
                checked={checkedItems["sentiment-marketing"]}
                onCheckedChange={(checked) => {
                  setCheckedItems((prev) => ({
                    ...prev,
                    "sentiment-marketing": !!checked,
                  }));
                  handleItemSelect(
                    {
                      id: "sentiment-marketing",
                      type: "micro-sentiment",
                      name: "Marketing: Positive Sentiment",
                      source: "Micro Sentiments",
                    },
                    !!checked
                  );
                }}
                className="mr-2"
              />
              <div className="flex items-center">
                <div className="w-24 text-sm">Marketing</div>
                <div className="flex-1 h-4 bg-gray-200 rounded-full overflow-hidden">
                  <div className="flex h-full">
                    <div
                      className="bg-green-500 h-full"
                      style={{ width: "75%" }}
                    ></div>
                    <div
                      className="bg-gray-400 h-full"
                      style={{ width: "20%" }}
                    ></div>
                    <div
                      className="bg-red-500 h-full"
                      style={{ width: "5%" }}
                    ></div>
                  </div>
                </div>
                <div className="w-10 text-right text-sm font-medium">+70</div>
              </div>

              <Checkbox
                id="sentiment-content"
                checked={checkedItems["sentiment-content"]}
                onCheckedChange={(checked) => {
                  setCheckedItems((prev) => ({
                    ...prev,
                    "sentiment-content": !!checked,
                  }));
                  handleItemSelect(
                    {
                      id: "sentiment-content",
                      type: "micro-sentiment",
                      name: "Content: Positive Sentiment",
                      source: "Micro Sentiments",
                    },
                    !!checked
                  );
                }}
                className="mr-2"
              />
              <div className="flex items-center">
                <div className="w-24 text-sm">Content</div>
                <div className="flex-1 h-4 bg-gray-200 rounded-full overflow-hidden">
                  <div className="flex h-full">
                    <div
                      className="bg-green-500 h-full"
                      style={{ width: "80%" }}
                    ></div>
                    <div
                      className="bg-gray-400 h-full"
                      style={{ width: "15%" }}
                    ></div>
                    <div
                      className="bg-red-500 h-full"
                      style={{ width: "5%" }}
                    ></div>
                  </div>
                </div>
                <div className="w-10 text-right text-sm font-medium">+75</div>
              </div>

              <Checkbox
                id="sentiment-strategy"
                checked={checkedItems["sentiment-strategy"]}
                onCheckedChange={(checked) => {
                  setCheckedItems((prev) => ({
                    ...prev,
                    "sentiment-strategy": !!checked,
                  }));
                  handleItemSelect(
                    {
                      id: "sentiment-strategy",
                      type: "micro-sentiment",
                      name: "Strategy: Positive Sentiment",
                      source: "Micro Sentiments",
                    },
                    !!checked
                  );
                }}
                className="mr-2"
              />
              <div className="flex items-center">
                <div className="w-24 text-sm">Strategy</div>
                <div className="flex-1 h-4 bg-gray-200 rounded-full overflow-hidden">
                  <div className="flex h-full">
                    <div
                      className="bg-green-500 h-full"
                      style={{ width: "65%" }}
                    ></div>
                    <div
                      className="bg-gray-400 h-full"
                      style={{ width: "25%" }}
                    ></div>
                    <div
                      className="bg-red-500 h-full"
                      style={{ width: "10%" }}
                    ></div>
                  </div>
                </div>
                <div className="w-10 text-right text-sm font-medium">+55</div>
              </div>

              <Checkbox
                id="sentiment-digital"
                checked={checkedItems["sentiment-digital"]}
                onCheckedChange={(checked) => {
                  setCheckedItems((prev) => ({
                    ...prev,
                    "sentiment-digital": !!checked,
                  }));
                  handleItemSelect(
                    {
                      id: "sentiment-digital",
                      type: "micro-sentiment",
                      name: "Digital: Positive Sentiment",
                      source: "Micro Sentiments",
                    },
                    !!checked
                  );
                }}
                className="mr-2"
              />
              <div className="flex items-center">
                <div className="w-24 text-sm">Digital</div>
                <div className="flex-1 h-4 bg-gray-200 rounded-full overflow-hidden">
                  <div className="flex h-full">
                    <div
                      className="bg-green-500 h-full"
                      style={{ width: "70%" }}
                    ></div>
                    <div
                      className="bg-gray-400 h-full"
                      style={{ width: "20%" }}
                    ></div>
                    <div
                      className="bg-red-500 h-full"
                      style={{ width: "10%" }}
                    ></div>
                  </div>
                </div>
                <div className="w-10 text-right text-sm font-medium">+60</div>
              </div>

              <Checkbox
                id="sentiment-social"
                checked={checkedItems["sentiment-social"]}
                onCheckedChange={(checked) => {
                  setCheckedItems((prev) => ({
                    ...prev,
                    "sentiment-social": !!checked,
                  }));
                  handleItemSelect(
                    {
                      id: "sentiment-social",
                      type: "micro-sentiment",
                      name: "Social: Positive Sentiment",
                      source: "Micro Sentiments",
                    },
                    !!checked
                  );
                }}
                className="mr-2"
              />
              <div className="flex items-center">
                <div className="w-24 text-sm">Social</div>
                <div className="flex-1 h-4 bg-gray-200 rounded-full overflow-hidden">
                  <div className="flex h-full">
                    <div
                      className="bg-green-500 h-full"
                      style={{ width: "60%" }}
                    ></div>
                    <div
                      className="bg-gray-400 h-full"
                      style={{ width: "30%" }}
                    ></div>
                    <div
                      className="bg-red-500 h-full"
                      style={{ width: "10%" }}
                    ></div>
                  </div>
                </div>
                <div className="w-10 text-right text-sm font-medium">+50</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Sentiment Insights</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Your campaign content shows a strong positive sentiment overall,
                with particularly positive associations around{" "}
                <span className="font-medium">content creation</span> and{" "}
                <span className="font-medium">marketing</span>.
              </p>
              <p className="text-sm text-gray-600">
                The topic of <span className="font-medium">strategy</span> shows
                a slightly lower positive sentiment score, with more neutral and
                negative mentions compared to other topics.
              </p>
              <p className="text-sm text-gray-600">
                The most positive sentiment is associated with discussions of{" "}
                <span className="font-medium">content quality</span> and{" "}
                <span className="font-medium">audience engagement</span>.
              </p>
              <div className="bg-blue-50 p-3 rounded-md border border-blue-100">
                <h4 className="font-medium text-blue-800 mb-1">
                  Recommendation
                </h4>
                <p className="text-sm text-blue-700">
                  Consider addressing some of the concerns or challenges
                  mentioned in relation to strategy implementation to improve
                  sentiment in this area.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function TopicalMapContent({
  campaign,
  onSelectItem,
}: {
  campaign: Campaign;
  onSelectItem: (item: any, isSelected: boolean) => void;
}) {
  // Add state for checked items
  const [checkedItems, setCheckedItems] = useState({
    "topic-marketing-strategy": true,
    "topic-content-creation": true,
    "topic-digital-channels": true,
    "topic-analytics-metrics": true,
    "topic-audience-engagement": true,
  });

  const topics = [
    { id: "marketingStrategy", name: "Marketing Strategy", coverage: 28 },
    { id: "contentCreation", name: "Content Creation", coverage: 24 },
    { id: "digitalChannels", name: "Digital Channels", coverage: 22 },
    { id: "analyticsMetrics", name: "Analytics & Metrics", coverage: 18 },
    { id: "audienceEngagement", name: "Audience Engagement", coverage: 8 },
  ];

  [
    { "keyword": "React", "color": "#61dafb" },
    { "keyword": "TypeScript", "color": "#3178c6" }
  ]


  const [allTopics, setAllTopics] = useState([]);

  const colorPalette = [
    "#FF5733", // Red-Orange
    "#33C1FF", // Sky Blue
    "#33FF57", // Green
    "#FF33A8", // Pink
    "#8D33FF", // Purple
    "#FFC133", // Orange
    "#4BFFDB", // Teal
    "#FFD733", // Yellow
  ];


  useEffect(() => {
    const stored = localStorage.getItem("topics");
    if (stored) {
      const parsed: string[] = JSON.parse(stored);

      const colorPalette = [
        "#FF5733", "#33C1FF", "#33FF57", "#FF33A8",
        "#8D33FF", "#FFC133", "#4BFFDB", "#FFD733",
      ];

      const parsedData = parsed.map((item, index) => ({
        keyword: item,
        color: colorPalette[index % colorPalette.length],
      }));

      setAllTopics(parsedData);
    }
  }, []);



  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Topical Map Visualization</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[400px] flex items-center justify-center bg-gray-50 rounded-md border">
            <div className="relative w-full h-full">
              {/* Main topic clusters */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px]">
                {/* Marketing Strategy Cluster */}
                <div className="absolute top-[20%] left-[30%] -translate-x-1/2 -translate-y-1/2">
                  <div className="w-20 h-20 rounded-full bg-blue-100 flex items-center justify-center text-center p-1">
                    <span className="text-sm font-medium text-blue-800">
                      Marketing Strategy
                    </span>
                  </div>
                  <div className="absolute top-[0%] left-[120%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center">
                    <span className="text-xs text-blue-600">Planning</span>
                  </div>
                  <div className="absolute top-[100%] left-[120%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center">
                    <span className="text-xs text-blue-600">Goals</span>
                  </div>
                </div>

                {/* Content Creation Cluster */}
                <div className="absolute top-[70%] left-[30%] -translate-x-1/2 -translate-y-1/2">
                  <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center text-center p-1">
                    <span className="text-sm font-medium text-green-800">
                      Content Creation
                    </span>
                  </div>
                  <div className="absolute top-[0%] left-[120%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-green-50 flex items-center justify-center">
                    <span className="text-xs text-green-600">Blogs</span>
                  </div>
                  <div className="absolute top-[100%] left-[120%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-green-50 flex items-center justify-center">
                    <span className="text-xs text-green-600">Videos</span>
                  </div>
                </div>

                {/* Digital Channels Cluster */}
                <div className="absolute top-[20%] left-[70%] -translate-x-1/2 -translate-y-1/2">
                  <div className="w-20 h-20 rounded-full bg-purple-100 flex items-center justify-center text-center p-1">
                    <span className="text-sm font-medium text-purple-800">
                      Digital Channels
                    </span>
                  </div>
                  <div className="absolute top-[0%] left-[-20%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-purple-50 flex items-center justify-center">
                    <span className="text-xs text-purple-600">Social</span>
                  </div>
                  <div className="absolute top-[100%] left-[-20%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-purple-50 flex items-center justify-center">
                    <span className="text-xs text-purple-600">Email</span>
                  </div>
                </div>

                {/* Analytics Cluster */}
                <div className="absolute top-[70%] left-[70%] -translate-x-1/2 -translate-y-1/2">
                  <div className="w-20 h-20 rounded-full bg-yellow-100 flex items-center justify-center text-center p-1">
                    <span className="text-sm font-medium text-yellow-800">
                      Analytics & Metrics
                    </span>
                  </div>
                  <div className="absolute top-[0%] left-[-20%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-yellow-50 flex items-center justify-center">
                    <span className="text-xs text-yellow-600">KPIs</span>
                  </div>
                  <div className="absolute top-[100%] left-[-20%] -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-yellow-50 flex items-center justify-center">
                    <span className="text-xs text-yellow-600">ROI</span>
                  </div>
                </div>

                {/* Connection lines */}
                <svg
                  className="absolute inset-0 w-full h-full"
                  style={{ zIndex: -1 }}
                >
                  <line
                    x1="30%"
                    y1="20%"
                    x2="70%"
                    y2="20%"
                    stroke="#ddd"
                    strokeWidth="2"
                  />
                  <line
                    x1="30%"
                    y1="20%"
                    x2="30%"
                    y2="70%"
                    stroke="#ddd"
                    strokeWidth="2"
                  />
                  <line
                    x1="70%"
                    y1="20%"
                    x2="70%"
                    y2="70%"
                    stroke="#ddd"
                    strokeWidth="2"
                  />
                  <line
                    x1="30%"
                    y1="70%"
                    x2="70%"
                    y2="70%"
                    stroke="#ddd"
                    strokeWidth="2"
                  />
                  <line
                    x1="30%"
                    y1="20%"
                    x2="70%"
                    y2="70%"
                    stroke="#ddd"
                    strokeWidth="2"
                    strokeDasharray="5,5"
                  />
                  <line
                    x1="70%"
                    y1="20%"
                    x2="30%"
                    y2="70%"
                    stroke="#ddd"
                    strokeWidth="2"
                    strokeDasharray="5,5"
                  />
                </svg>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Topic Relationships</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-3">
              {allTopics?.map(({ keyword, color }) => {
                const id = `keyword-${keyword}`;
                return (
                  <div key={id}>
                    <div className="flex items-center space-x-2">
                      <span
                        className="w-3 h-3 rounded-full inline-block"
                        style={{ backgroundColor: color }}
                        title={color}
                      ></span>
                      <span>{keyword}</span>
                    </div>
                  </div>
                );
              })}


            </div>
            {/* <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <Checkbox
                    id="topic-marketing-strategy"
                    checked={checkedItems["topic-marketing-strategy"]}
                    onCheckedChange={(checked) => {
                      setCheckedItems((prev) => ({
                        ...prev,
                        "topic-marketing-strategy": !!checked,
                      }));
                      onSelectItem(
                        {
                          id: "topic-marketing-strategy",
                          type: "topic",
                          name: "Marketing Strategy",
                          source: "Topical Map",
                        },
                        !!checked
                      );
                    }}
                    className="mr-2"
                  />
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-blue-500 mr-2"></div>
                    <span>Marketing Strategy</span>
                  </div>
                </div>
                <span className="text-sm font-medium">28% coverage</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <Checkbox
                    id="topic-content-creation"
                    checked={checkedItems["topic-content-creation"]}
                    onCheckedChange={(checked) => {
                      setCheckedItems((prev) => ({
                        ...prev,
                        "topic-content-creation": !!checked,
                      }));
                      onSelectItem(
                        {
                          id: "topic-content-creation",
                          type: "topic",
                          name: "Content Creation",
                          source: "Topical Map",
                        },
                        !!checked
                      );
                    }}
                    className="mr-2"
                  />
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
                    <span>Content Creation</span>
                  </div>
                </div>
                <span className="text-sm font-medium">24% coverage</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <Checkbox
                    id="topic-digital-channels"
                    checked={checkedItems["topic-digital-channels"]}
                    onCheckedChange={(checked) => {
                      setCheckedItems((prev) => ({
                        ...prev,
                        "topic-digital-channels": !!checked,
                      }));
                      onSelectItem(
                        {
                          id: "topic-digital-channels",
                          type: "topic",
                          name: "Digital Channels",
                          source: "Topical Map",
                        },
                        !!checked
                      );
                    }}
                    className="mr-2"
                  />
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-purple-500 mr-2"></div>
                    <span>Digital Channels</span>
                  </div>
                </div>
                <span className="text-sm font-medium">22% coverage</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <Checkbox
                    id="topic-analytics-metrics"
                    checked={checkedItems["topic-analytics-metrics"]}
                    onCheckedChange={(checked) => {
                      setCheckedItems((prev) => ({
                        ...prev,
                        "topic-analytics-metrics": !!checked,
                      }));
                      onSelectItem(
                        {
                          id: "topic-analytics-metrics",
                          type: "topic",
                          name: "Analytics & Metrics",
                          source: "Topical Map",
                        },
                        !!checked
                      );
                    }}
                    className="mr-2"
                  />
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-yellow-500 mr-2"></div>
                    <span>Analytics & Metrics</span>
                  </div>
                </div>
                <span className="text-sm font-medium">18% coverage</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <Checkbox
                    id="topic-audience-engagement"
                    checked={checkedItems["topic-audience-engagement"]}
                    onCheckedChange={(checked) => {
                      setCheckedItems((prev) => ({
                        ...prev,
                        "topic-audience-engagement": !!checked,
                      }));
                      onSelectItem(
                        {
                          id: "topic-audience-engagement",
                          type: "topic",
                          name: "Audience Engagement",
                          source: "Topical Map",
                        },
                        !!checked
                      );
                    }}
                    className="mr-2"
                  />
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full bg-red-500 mr-2"></div>
                    <span>Audience Engagement</span>
                  </div>
                </div>
                <span className="text-sm font-medium">8% coverage</span>
              </div>
            </div>
            <div className="mt-6 pt-4 border-t">
              <h4 className="font-medium mb-2">Strongest Connections</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Marketing Strategy → Content Creation</span>
                  <span className="font-medium">High</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Content Creation → Digital Channels</span>
                  <span className="font-medium">High</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Digital Channels → Analytics</span>
                  <span className="font-medium">Medium</span>
                </div>
              </div>
            </div> */}
          </CardContent>
        </Card>
        {/* <Card>
          <CardHeader>
            <CardTitle className="text-base">Topical Insights</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Your campaign content shows strong connections between{" "}
                <span className="font-medium">marketing strategy</span> and{" "}
                <span className="font-medium">content creation</span>,
                indicating a well-integrated approach.
              </p>
              <p className="text-sm text-gray-600">
                The topic of{" "}
                <span className="font-medium">audience engagement</span> has the
                lowest coverage but connects to multiple other topics,
                suggesting it's an underlying theme rather than a standalone
                focus.
              </p>
              <p className="text-sm text-gray-600">
                <span className="font-medium">Analytics & metrics</span> are
                well-represented but could be more strongly connected to{" "}
                <span className="font-medium">marketing strategy</span> to
                create a more data-driven approach to campaign planning.
              </p>
              <div className="bg-blue-50 p-3 rounded-md border border-blue-100">
                <h4 className="font-medium text-blue-800 mb-1">
                  Recommendation
                </h4>
                <p className="text-sm text-blue-700">
                  Consider creating more content that explicitly connects
                  analytics insights to strategic decision-making to strengthen
                  this relationship in your campaign narrative.
                </p>
              </div>
            </div>
          </CardContent>
        </Card> */}
      </div>
    </div>
  );
}

function KnowledgeGraphContent({
  campaign,
  handleItemSelect,
}: {
  campaign: Campaign;
  handleItemSelect: (item: any, isSelected: boolean) => void;
}) {
  // Add state for checked items
  const [checkedItems, setCheckedItems] = useState({
    "entity-digital-marketing": true,
    "entity-content-strategy": true,
    "entity-channel-distribution": true,
    "entity-performance-analytics": true,
    "entity-blog-articles": true,
  });

  const entities = [
    {
      id: "digitalMarketing",
      name: "Digital Marketing",
      type: "Concept",
      connections: 3,
    },
    {
      id: "contentStrategy",
      name: "Content Strategy",
      type: "Process",
      connections: 3,
    },
    {
      id: "channelDistribution",
      name: "Channel Distribution",
      type: "Process",
      connections: 3,
    },
    {
      id: "performanceAnalytics",
      name: "Performance Analytics",
      type: "Process",
      connections: 2,
    },
    {
      id: "blogArticles",
      name: "Blog Articles",
      type: "Content Type",
      connections: 1,
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Knowledge Graph</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[400px] flex items-center justify-center bg-gray-50 rounded-md border">
            <div className="relative w-full h-full">
              {/* Knowledge graph visualization */}
              <svg className="absolute inset-0 w-full h-full">
                {/* Connections */}
                <line
                  x1="50%"
                  y1="30%"
                  x2="30%"
                  y2="50%"
                  stroke="#ddd"
                  strokeWidth="2"
                />
                <line
                  x1="50%"
                  y1="30%"
                  x2="70%"
                  y2="50%"
                  stroke="#ddd"
                  strokeWidth="2"
                />
                <line
                  x1="50%"
                  y1="30%"
                  x2="50%"
                  y2="70%"
                  stroke="#ddd"
                  strokeWidth="2"
                />
                <line
                  x1="30%"
                  y1="50%"
                  x2="50%"
                  y2="70%"
                  stroke="#ddd"
                  strokeWidth="2"
                />
                <line
                  x1="70%"
                  y1="50%"
                  x2="50%"
                  y2="70%"
                  stroke="#ddd"
                  strokeWidth="2"
                />
                <line
                  x1="30%"
                  y1="50%"
                  x2="20%"
                  y2="70%"
                  stroke="#ddd"
                  strokeWidth="2"
                />
                <line
                  x1="30%"
                  y1="50%"
                  x2="40%"
                  y2="70%"
                  stroke="#ddd"
                  strokeWidth="2"
                />
                <line
                  x1="70%"
                  y1="50%"
                  x2="60%"
                  y2="70%"
                  stroke="#ddd"
                  strokeWidth="2"
                />
                <line
                  x1="70%"
                  y1="50%"
                  x2="80%"
                  y2="70%"
                  stroke="#ddd"
                  strokeWidth="2"
                />
              </svg>

              {/* Nodes */}
              <div className="absolute top-[30%] left-[50%] -translate-x-1/2 -translate-y-1/2">
                <div className="w-24 h-24 rounded-full bg-blue-100 border-2 border-blue-300 flex items-center justify-center text-center p-2">
                  <span className="text-sm font-medium text-blue-800">
                    Digital Marketing
                  </span>
                </div>
              </div>

              <div className="absolute top-[50%] left-[30%] -translate-x-1/2 -translate-y-1/2">
                <div className="w-20 h-20 rounded-full bg-green-100 border-2 border-green-300 flex items-center justify-center text-center p-2">
                  <span className="text-sm font-medium text-green-800">
                    Content Strategy
                  </span>
                </div>
              </div>

              <div className="absolute top-[50%] left-[70%] -translate-x-1/2 -translate-y-1/2">
                <div className="w-20 h-20 rounded-full bg-purple-100 border-2 border-purple-300 flex items-center justify-center text-center p-2">
                  <span className="text-sm font-medium text-purple-800">
                    Channel Distribution
                  </span>
                </div>
              </div>

              <div className="absolute top-[70%] left-[50%] -translate-x-1/2 -translate-y-1/2">
                <div className="w-20 h-20 rounded-full bg-yellow-100 border-2 border-yellow-300 flex items-center justify-center text-center p-2">
                  <span className="text-sm font-medium text-yellow-800">
                    Performance Analytics
                  </span>
                </div>
              </div>

              <div className="absolute top-[70%] left-[20%] -translate-x-1/2 -translate-y-1/2">
                <div className="w-16 h-16 rounded-full bg-green-50 border-2 border-green-200 flex items-center justify-center text-center p-1">
                  <span className="text-xs font-medium text-green-700">
                    Blog Articles
                  </span>
                </div>
              </div>

              <div className="absolute top-[70%] left-[40%] -translate-x-1/2 -translate-y-1/2">
                <div className="w-16 h-16 rounded-full bg-green-50 border-2 border-green-200 flex items-center justify-center text-center p-1">
                  <span className="text-xs font-medium text-green-700">
                    Video Content
                  </span>
                </div>
              </div>

              <div className="absolute top-[70%] left-[60%] -translate-x-1/2 -translate-y-1/2">
                <div className="w-16 h-16 rounded-full bg-purple-50 border-2 border-purple-200 flex items-center justify-center text-center p-1">
                  <span className="text-xs font-medium text-purple-700">
                    Social Media
                  </span>
                </div>
              </div>

              <div className="absolute top-[70%] left-[80%] -translate-x-1/2 -translate-y-1/2">
                <div className="w-16 h-16 rounded-full bg-purple-50 border-2 border-purple-200 flex items-center justify-center text-center p-1">
                  <span className="text-xs font-medium text-purple-700">
                    Email Marketing
                  </span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Entity Relationships</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-4">
              <div className="border rounded-md overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-4 py-2 text-left">Entity</th>
                      <th className="px-4 py-2 text-left">Type</th>
                      <th className="px-4 py-2 text-left">Connections</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    <tr>
                      <td className="px-4 py-2 font-medium">
                        <div className="flex items-center">
                          <Checkbox
                            id="entity-digital-marketing"
                            checked={checkedItems["entity-digital-marketing"]}
                            onCheckedChange={(checked) => {
                              setCheckedItems((prev) => ({
                                ...prev,
                                "entity-digital-marketing": !!checked,
                              }));
                              handleItemSelect(
                                {
                                  id: "entity-digital-marketing",
                                  type: "knowledge-graph",
                                  name: "Digital Marketing",
                                  source: "Knowledge Graph",
                                },
                                !!checked
                              );
                            }}
                            className="mr-2"
                          />
                          Digital Marketing
                        </div>
                      </td>
                      <td className="px-4 py-2">Concept</td>
                      <td className="px-4 py-2">3</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-2 font-medium">
                        <div className="flex items-center">
                          <Checkbox
                            id="entity-content-strategy"
                            checked={checkedItems["entity-content-strategy"]}
                            onCheckedChange={(checked) => {
                              setCheckedItems((prev) => ({
                                ...prev,
                                "entity-content-strategy": !!checked,
                              }));
                              handleItemSelect(
                                {
                                  id: "entity-content-strategy",
                                  type: "knowledge-graph",
                                  name: "Content Strategy",
                                  source: "Knowledge Graph",
                                },
                                !!checked
                              );
                            }}
                            className="mr-2"
                          />
                          Content Strategy
                        </div>
                      </td>
                      <td className="px-4 py-2">Process</td>
                      <td className="px-4 py-2">3</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-2 font-medium">
                        <div className="flex items-center">
                          <Checkbox
                            id="entity-channel-distribution"
                            checked={
                              checkedItems["entity-channel-distribution"]
                            }
                            onCheckedChange={(checked) => {
                              setCheckedItems((prev) => ({
                                ...prev,
                                "entity-channel-distribution": !!checked,
                              }));
                              handleItemSelect(
                                {
                                  id: "entity-channel-distribution",
                                  type: "knowledge-graph",
                                  name: "Channel Distribution",
                                  source: "Knowledge Graph",
                                },
                                !!checked
                              );
                            }}
                            className="mr-2"
                          />
                          Channel Distribution
                        </div>
                      </td>
                      <td className="px-4 py-2">Process</td>
                      <td className="px-4 py-2">3</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-2 font-medium">
                        <div className="flex items-center">
                          <Checkbox
                            id="entity-performance-analytics"
                            checked={
                              checkedItems["entity-performance-analytics"]
                            }
                            onCheckedChange={(checked) => {
                              setCheckedItems((prev) => ({
                                ...prev,
                                "entity-performance-analytics": !!checked,
                              }));
                              handleItemSelect(
                                {
                                  id: "entity-performance-analytics",
                                  type: "knowledge-graph",
                                  name: "Performance Analytics",
                                  source: "Knowledge Graph",
                                },
                                !!checked
                              );
                            }}
                            className="mr-2"
                          />
                          Performance Analytics
                        </div>
                      </td>
                      <td className="px-4 py-2">Process</td>
                      <td className="px-4 py-2">2</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-2 font-medium">
                        <div className="flex items-center">
                          <Checkbox
                            id="entity-blog-articles"
                            checked={checkedItems["entity-blog-articles"]}
                            onCheckedChange={(checked) => {
                              setCheckedItems((prev) => ({
                                ...prev,
                                "entity-blog-articles": !!checked,
                              }));
                              handleItemSelect(
                                {
                                  id: "entity-blog-articles",
                                  type: "knowledge-graph",
                                  name: "Blog Articles",
                                  source: "Knowledge Graph",
                                },
                                !!checked
                              );
                            }}
                            className="mr-2"
                          />
                          Blog Articles
                        </div>
                      </td>
                      <td className="px-4 py-2">Content Type</td>
                      <td className="px-4 py-2">1</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Knowledge Graph Insights
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                The knowledge graph reveals a well-structured understanding of
                digital marketing concepts in your campaign content, with clear
                hierarchical relationships.
              </p>
              <p className="text-sm text-gray-600">
                <span className="font-medium">Content Strategy</span> and{" "}
                <span className="font-medium">Channel Distribution</span> are
                equally connected to other entities, showing a balanced approach
                to these aspects.
              </p>
              <p className="text-sm text-gray-600">
                <span className="font-medium">Performance Analytics</span> has
                fewer connections than other main concepts, suggesting an
                opportunity to strengthen how analytics integrates with other
                marketing processes.
              </p>
              <div className="bg-blue-50 p-3 rounded-md border border-blue-100">
                <h4 className="font-medium text-blue-800 mb-1">
                  Recommendation
                </h4>
                <p className="text-sm text-blue-700">
                  Consider creating content that explicitly connects performance
                  metrics to specific content types and distribution channels to
                  strengthen these relationships in your knowledge graph.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function HashtagGeneratorContent({
  campaign,
  handleItemSelect,
}: {
  campaign: Campaign;
  handleItemSelect: (item: any, isSelected: boolean) => void;
}) {
  // Add state for checked items
  const [checkedItems, setCheckedItems] = useState({
    "hashtag-digitalMarketing": true,
    "hashtag-contentStrategy": true,
    "hashtag-marketingTips": true,
    "hashtag-brandGrowth": true,
    "hashtag-socialMediaMarketing": true,
    "hashtag-contentCreation": true,
    "hashtag-marketingStrategy": true,
    "hashtag-digitalSuccess": true,
    "hashtag-businessGrowth": true,
    "hashtag-marketingAnalytics": true,
    "hashtag-contentMarketing": true,
    "hashtag-brandAwareness": true,
  });

  const hashtags = [
    { id: "digitalMarketing", name: "#DigitalMarketing", category: "Industry" },
    { id: "contentStrategy", name: "#ContentStrategy", category: "Trending" },
    { id: "marketingTips", name: "#MarketingTips", category: "Trending" },
    { id: "brandGrowth", name: "#BrandGrowth", category: "Campaign-Specific" },
    {
      id: "socialMediaMarketing",
      name: "#SocialMediaMarketing",
      category: "Niche",
    },
    {
      id: "contentCreation",
      name: "#ContentCreation",
      category: "Campaign-Specific",
    },
    {
      id: "marketingStrategy",
      name: "#MarketingStrategy",
      category: "Industry",
    },
    { id: "digitalSuccess", name: "#DigitalSuccess", category: "Trending" },
    {
      id: "businessGrowth",
      name: "#BusinessGrowth",
      category: "Campaign-Specific",
    },
    {
      id: "marketingAnalytics",
      name: "#MarketingAnalytics",
      category: "Niche",
    },
    { id: "contentMarketing", name: "#ContentMarketing", category: "Industry" },
    { id: "brandAwareness", name: "#BrandAwareness", category: "Niche" },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Generated Hashtags</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {hashtags.map((hashtag) => (
              <div
                key={hashtag.id}
                className="bg-blue-50 p-3 rounded-md border border-blue-100 flex items-center"
              >
                <Checkbox
                  id={`hashtag-${hashtag.id}`}
                  checked={checkedItems[`hashtag-${hashtag.id}`]}
                  onCheckedChange={(checked) => {
                    setCheckedItems((prev) => ({
                      ...prev,
                      [`hashtag-${hashtag.id}`]: !!checked,
                    }));
                    handleItemSelect(
                      {
                        id: `hashtag-${hashtag.id}`,
                        type: "hashtag",
                        name: hashtag.name,
                        source: "Hashtag Generator",
                      },
                      !!checked
                    );
                  }}
                  className="mr-2"
                />
                <Hash className="w-4 h-4 text-blue-500 mr-2" />
                <span className="text-blue-700 font-medium">
                  {hashtag.name.substring(1)}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Hashtag Categories</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Hashtag Insights</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                The generated hashtags cover a balanced mix of
                industry-standard, trending, niche, and campaign-specific tags
                to maximize visibility and engagement.
              </p>
              <p className="text-sm text-gray-600">
                <span className="font-medium">#ContentStrategy</span> and{" "}
                <span className="font-medium">#MarketingTips</span> are
                currently trending and have high engagement rates on platforms
                like Twitter and LinkedIn.
              </p>
              <p className="text-sm text-gray-600">
                Niche hashtags like{" "}
                <span className="font-medium">#MarketingAnalytics</span> have
                lower volume but higher relevance, making them valuable for
                reaching targeted audiences.
              </p>
              <div className="bg-blue-50 p-3 rounded-md border border-blue-100">
                <h4 className="font-medium text-blue-800 mb-1">
                  Recommendation
                </h4>
                <p className="text-sm text-blue-700">
                  Use a mix of 3-5 hashtags per post, combining high-volume
                  industry tags with more specific niche tags. Monitor
                  performance and adjust your hashtag strategy based on
                  engagement metrics.
                </p>
              </div>
              <div className="mt-4">
                <h4 className="font-medium mb-2">
                  Suggested Hashtag Combinations:
                </h4>
                <div className="space-y-2">
                  <div className="bg-gray-50 p-2 rounded border text-sm">
                    #DigitalMarketing #ContentStrategy #MarketingAnalytics
                  </div>
                  <div className="bg-gray-50 p-2 rounded border text-sm">
                    #MarketingTips #BrandGrowth #SocialMediaMarketing
                  </div>
                  <div className="bg-gray-50 p-2 rounded border text-sm">
                    #ContentCreation #BusinessGrowth #BrandAwareness
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
