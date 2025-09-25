"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  FileText,
  User,
  Building,
  MapPin,
  Calendar,
  Layers,
  Cloud,
  BarChart2,
  GitBranch,
  Network,
  Hash,
  Trash2,
  RefreshCw,
  Wand2,
  Check,
  Loader2,
  Send,
  Clock,
  Instagram,
  Facebook,
  Youtube,
  Twitter,
  Linkedin,
  Music,
  WorkflowIcon as Wordpress,
  AlertCircle,
} from "lucide-react";

// Define the types of content items that can be in the queue
type ContentItemType =
  | "entity-person"
  | "entity-organization"
  | "entity-location"
  | "entity-date"
  | "topic"
  | "word-cloud"
  | "sentiment"
  | "topical-map"
  | "knowledge-graph"
  | "hashtag"
  | "keyword"
  | "micro-sentiment"
  | "trending-topic";

interface ContentQueueItem {
  id: string;
  type: ContentItemType;
  name: string;
  source: string;
  selected: boolean;
  generated?: boolean;
  generatedContent?: string;
  scheduled?: boolean;
  scheduledPlatform?: string;
  scheduledTime?: string;
  scheduledDate?: string;
}

// Platform icons mapping
const platformIcons = {
  Instagram,
  Facebook,
  Youtube,
  Twitter,
  Linkedin,
  Wordpress,
  TikTok: Music,
};

// Sample days and platforms (matching Author Planning)
const DAYS = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];


const PLATFORMS = [
  { name: "Instagram", icon: Instagram },
  { name: "Facebook", icon: Facebook },
  { name: "YouTube", icon: Youtube },
  { name: "Twitter", icon: Twitter },
  { name: "LinkedIn", icon: Linkedin },
  { name: "WordPress", icon: Wordpress },
  { name: "TikTok", icon: Music },
];

// Time options for scheduling
const TIME_OPTIONS = Array.from({ length: 24 }, (_, i) => `${i}:00`);

export function ContentGenerationQueue() {
  // Sample queue items - in a real app, this would come from a global state or context
  const [queueItems, setQueueItems] = useState<ContentQueueItem[]>([
    {
      id: "1",
      type: "entity-person",
      name: "John Smith",
      source: "Entity Recognition",
      selected: false,
    },
    {
      id: "2",
      type: "entity-organization",
      name: "Acme Corporation",
      source: "Entity Recognition",
      selected: false,
    },
    {
      id: "3",
      type: "entity-location",
      name: "San Francisco",
      source: "Entity Recognition",
      selected: false,
    },
    {
      id: "4",
      type: "topic",
      name: "Digital Marketing Strategy",
      source: "Topic Modeling",
      selected: false,
    },
    {
      id: "5",
      type: "word-cloud",
      name: "Content",
      source: "Word Clouds",
      selected: false,
    },
    {
      id: "6",
      type: "sentiment",
      name: "Positive Sentiment",
      source: "Micro Sentiments",
      selected: false,
    },
    {
      id: "7",
      type: "hashtag",
      name: "#DigitalMarketing",
      source: "Hashtag Generator",
      selected: false,
    },
    {
      id: "8",
      type: "keyword",
      name: "content strategy",
      source: "Keywords",
      selected: false,
    },
    {
      id: "9",
      type: "micro-sentiment",
      name: "Excitement about new features",
      source: "Micro Sentiments",
      selected: false,
    },
    {
      id: "10",
      type: "topical-map",
      name: "Content Creation Process",
      source: "Topical Map",
      selected: false,
    },
    {
      id: "11",
      type: "hashtag",
      name: "#DigitalMarketing",
      source: "Hashtag Generator",
      selected: false,
      generated: true,
      generatedContent:
        "Digital marketing continues to evolve in 2025, with new strategies emerging for content creators and marketers. #DigitalMarketing",
    },
    {
      id: "12",
      type: "topic",
      name: "Content Creation",
      source: "Topic Modeling",
      selected: false,
      generated: true,
      generatedContent:
        "Creating engaging content requires understanding your audience's needs and preferences. Here are 5 tips for effective content creation in the digital age...",
    },
    {
      id: "13",
      type: "keyword",
      name: "social media strategy",
      source: "Keywords",
      selected: false,
      generated: true,
      generatedContent:
        "A comprehensive social media strategy involves understanding platform-specific audiences, creating engaging content, and measuring performance metrics to continuously improve your approach.",
      scheduled: true,
      scheduledPlatform: "Instagram",
      scheduledTime: "9:00",
      scheduledDate: "Mon",
    },
    {
      id: "14",
      type: "entity-organization",
      name: "TechCorp",
      source: "Entity Recognition",
      selected: false,
      generated: true,
      generatedContent:
        "TechCorp has been at the forefront of innovation in the software industry, with groundbreaking products that have transformed how businesses operate.",
      scheduled: true,
      scheduledPlatform: "LinkedIn",
      scheduledTime: "12:00",
      scheduledDate: "Wed",
    },
  ]);

  const [activeTab, setActiveTab] = useState<
    "queue" | "generated" | "scheduled"
  >("queue");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationSuccess, setGenerationSuccess] = useState(false);
  const [schedulingSuccess, setSchedulingSuccess] = useState(false);

  // Scheduling state
  const [selectedPlatform, setSelectedPlatform] = useState<string>("");
  const [selectedTime, setSelectedTime] = useState<string>("");
  const [selectedDays, setSelectedDays] = useState<string[]>([]);

  // Get counts for the tabs
  const queueCount = queueItems.filter(
    (item) => !item.generated && !item.scheduled
  ).length;
  const generatedCount = queueItems.filter(
    (item) => item.generated && !item.scheduled
  ).length;
  const scheduledCount = queueItems.filter((item) => item.scheduled).length;

  // Get selected items for icon display
  const selectedItems = queueItems.filter(
    (item) => item.selected && !item.generated && !item.scheduled
  );

  // Handle selecting/deselecting all items
  const handleSelectAll = (selected: boolean) => {
    setQueueItems((items) =>
      items.map((item) => {
        if (activeTab === "queue" && !item.generated && !item.scheduled) {
          return { ...item, selected };
        } else if (
          activeTab === "generated" &&
          item.generated &&
          !item.scheduled
        ) {
          return { ...item, selected };
        } else if (activeTab === "scheduled" && item.scheduled) {
          return { ...item, selected };
        }
        return item;
      })
    );
  };

  // Handle selecting/deselecting individual items
  const handleSelectItem = (id: string, selected: boolean) => {
    setQueueItems((items) =>
      items.map((item) => (item.id === id ? { ...item, selected } : item))
    );
  };

  // Handle removing items from the queue
  const handleRemoveSelected = () => {
    setQueueItems((items) => {
      if (activeTab === "queue") {
        return items.filter(
          (item) => !(item.selected && !item.generated && !item.scheduled)
        );
      } else if (activeTab === "generated") {
        return items.filter(
          (item) => !(item.selected && item.generated && !item.scheduled)
        );
      } else if (activeTab === "scheduled") {
        return items.filter((item) => !(item.selected && item.scheduled));
      }
      return items;
    });
  };

  // Handle generating content for selected items
  const handleGenerateContent = async () => {
    setIsGenerating(true);

    // Simulate API call to generate content
    await new Promise((resolve) => setTimeout(resolve, 3000));

    // Update items with generated content
    setQueueItems((items) =>
      items.map((item) => {
        if (item.selected && !item.generated && !item.scheduled) {
          return {
            ...item,
            generated: true,
            generatedContent: generateSampleContent(item),
            selected: false,
          };
        }
        return item;
      })
    );

    setIsGenerating(false);
    setGenerationSuccess(true);
    setTimeout(() => setGenerationSuccess(false), 3000);
  };

  // Handle sending to production (scheduling)
  const handleSendToProduction = async () => {
    if (!selectedPlatform || !selectedTime || selectedDays.length === 0) {
      return;
    }

    setIsGenerating(true);

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Update items with scheduling information
    setQueueItems((items) =>
      items.map((item) => {
        if (item.selected && item.generated && !item.scheduled) {
          return {
            ...item,
            scheduled: true,
            scheduledPlatform: selectedPlatform,
            scheduledTime: selectedTime,
            scheduledDate: selectedDays[0], // For simplicity, just use the first selected day
            selected: false,
          };
        }
        return item;
      })
    );

    setIsGenerating(false);
    setSchedulingSuccess(true);
    setTimeout(() => setSchedulingSuccess(false), 3000);

    // Reset scheduling form
    setSelectedPlatform("");
    setSelectedTime("");
    setSelectedDays([]);
  };

  // Generate sample content based on item type
  const generateSampleContent = (item: ContentQueueItem): string => {
    switch (item.type) {
      case "entity-person":
        return `${item.name} is a key figure in the industry, known for innovative approaches to digital marketing and content strategy.`;
      case "entity-organization":
        return `${item.name} has been leading the market with cutting-edge solutions and customer-focused strategies.`;
      case "entity-location":
        return `${item.name} is becoming a hub for digital innovation, with numerous startups and established companies choosing it as their base.`;
      case "topic":
        return `${item.name} is evolving rapidly in 2025, with new approaches and technologies transforming how businesses connect with their audiences.`;
      case "word-cloud":
        return `The concept of "${item.name}" is central to modern marketing strategies, influencing how brands communicate their value propositions.`;
      case "sentiment":
        return `Understanding ${item.name.toLowerCase()} in customer feedback provides valuable insights for improving products and services.`;
      case "hashtag":
        return `${item.name} is trending among industry professionals, highlighting the growing interest in innovative marketing approaches.`;
      case "keyword":
        return `"${item.name}" is a crucial keyword for SEO optimization in the current digital landscape, with high search volume and moderate competition.`;
      case "micro-sentiment":
        return `The micro-sentiment "${item.name}" appears frequently in customer feedback, indicating an area where your brand is performing well.`;
      case "topical-map":
        return `"${item.name}" encompasses several interconnected concepts that form the foundation of effective content strategy in today's digital ecosystem.`;
      default:
        return `Content generated about ${item.name} based on analysis from ${item.source}.`;
    }
  };

  // Get the appropriate icon for each item type
  const getItemIcon = (type: ContentItemType) => {
    switch (type) {
      case "entity-person":
        return <User className="h-4 w-4 text-blue-500" />;
      case "entity-organization":
        return <Building className="h-4 w-4 text-green-500" />;
      case "entity-location":
        return <MapPin className="h-4 w-4 text-purple-500" />;
      case "entity-date":
        return <Calendar className="h-4 w-4 text-yellow-500" />;
      case "topic":
        return <Layers className="h-4 w-4 text-indigo-500" />;
      case "word-cloud":
        return <Cloud className="h-4 w-4 text-blue-500" />;
      case "sentiment":
        return <BarChart2 className="h-4 w-4 text-green-500" />;
      case "topical-map":
        return <GitBranch className="h-4 w-4 text-purple-500" />;
      case "knowledge-graph":
        return <Network className="h-4 w-4 text-yellow-500" />;
      case "hashtag":
        return <Hash className="h-4 w-4 text-pink-500" />;
      case "keyword":
        return <Hash className="h-4 w-4 text-orange-500" />;
      case "micro-sentiment":
        return <BarChart2 className="h-4 w-4 text-teal-500" />;
      case "trending-topic":
        return <Twitter className="h-4 w-4 text-blue-500" />;
      default:
        return <FileText className="h-4 w-4 text-gray-500" />;
    }
  };

  // Get the appropriate badge color for each source
  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case "Entity Recognition":
        return "bg-blue-100 text-blue-800";
      case "Topic Modeling":
        return "bg-indigo-100 text-indigo-800";
      case "Word Clouds":
        return "bg-cyan-100 text-cyan-800";
      case "Micro Sentiments":
        return "bg-green-100 text-green-800";
      case "Topical Map":
        return "bg-purple-100 text-purple-800";
      case "Knowledge Graph":
        return "bg-yellow-100 text-yellow-800";
      case "Hashtag Generator":
        return "bg-pink-100 text-pink-800";
      case "Keywords":
        return "bg-orange-100 text-orange-800";
      case "Trending on X":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  // Get platform icon
  const getPlatformIcon = (platform: string) => {
    const PlatformIcon = platformIcons[platform as keyof typeof platformIcons];
    return PlatformIcon ? <PlatformIcon className="h-4 w-4" /> : null;
  };

  return (
    <div className="space-y-6">
      {/* Selected items icons */}
      {selectedItems.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {selectedItems.map((item) => (
            <div
              key={item.id}
              className="flex items-center bg-white rounded-full px-3 py-1 shadow-sm border"
            >
              {getItemIcon(item.type)}
              <span className="ml-2 text-sm font-medium">{item.name}</span>
            </div>
          ))}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Content Generation Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeTab}
            onValueChange={(value) =>
              setActiveTab(value as "queue" | "generated" | "scheduled")
            }
          >
            <TabsList className="w-full mb-6">
              <TabsTrigger value="queue" className="flex-1">
                Queue ({queueCount})
              </TabsTrigger>
              <TabsTrigger value="generated" className="flex-1">
                Generated Content ({generatedCount})
              </TabsTrigger>
              <TabsTrigger value="scheduled" className="flex-1">
                Production Schedule ({scheduledCount})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="queue" className="space-y-4">
              {queueItems.filter((item) => !item.generated && !item.scheduled)
                .length > 0 ? (
                <>
                  <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="select-all-queue"
                        onCheckedChange={(checked) =>
                          handleSelectAll(!!checked)
                        }
                      />
                      <Label htmlFor="select-all-queue">Select All</Label>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRemoveSelected}
                        disabled={
                          !queueItems.some(
                            (item) =>
                              item.selected &&
                              !item.generated &&
                              !item.scheduled
                          )
                        }
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Remove Selected
                      </Button>
                      <Button
                        className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                        size="sm"
                        onClick={handleGenerateContent}
                        disabled={
                          isGenerating ||
                          !queueItems.some(
                            (item) =>
                              item.selected &&
                              !item.generated &&
                              !item.scheduled
                          )
                        }
                      >
                        {isGenerating ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Generating...
                          </>
                        ) : (
                          <>
                            <Wand2 className="h-4 w-4 mr-2" />
                            Generate Content
                          </>
                        )}
                      </Button>
                    </div>
                  </div>

                  {generationSuccess && (
                    <div className="bg-green-50 border border-green-200 rounded-md p-3 mb-4 flex items-center">
                      <Check className="h-5 w-5 text-green-500 mr-2" />
                      <p className="text-green-700">
                        Content successfully generated! View in the Generated
                        Content tab.
                      </p>
                    </div>
                  )}

                  <div className="space-y-2">
                    {queueItems
                      .filter((item) => !item.generated && !item.scheduled)
                      .map((item) => (
                        <div
                          key={item.id}
                          className="flex items-start p-3 border rounded-md"
                        >
                          <Checkbox
                            id={`item-${item.id}`}
                            className="mt-1"
                            checked={item.selected}
                            onCheckedChange={(checked) =>
                              handleSelectItem(item.id, !!checked)
                            }
                          />
                          <div className="ml-3 flex-1">
                            <div className="flex items-center">
                              {getItemIcon(item.type)}
                              <Label
                                htmlFor={`item-${item.id}`}
                                className="ml-2 font-medium cursor-pointer"
                              >
                                {item.name}
                              </Label>
                            </div>
                            <Badge
                              className={`mt-1 ${getSourceBadgeColor(
                                item.source
                              )}`}
                            >
                              {item.source}
                            </Badge>
                          </div>
                        </div>
                      ))}
                  </div>
                </>
              ) : (
                <div className="text-center py-12">
                  <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold mb-2">
                    Content Queue Empty
                  </h3>
                  <p className="text-gray-500 mb-6 max-w-md mx-auto">
                    Add items to the queue from Entity Recognition, Topic
                    Modeling, or Research Assistant tabs.
                  </p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="generated" className="space-y-4">
              {queueItems.filter((item) => item.generated && !item.scheduled)
                .length > 0 ? (
                <>
                  <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="select-all-generated"
                        onCheckedChange={(checked) =>
                          handleSelectAll(!!checked)
                        }
                      />
                      <Label htmlFor="select-all-generated">Select All</Label>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRemoveSelected}
                        disabled={
                          !queueItems.some(
                            (item) =>
                              item.selected && item.generated && !item.scheduled
                          )
                        }
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Remove Selected
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={
                          !queueItems.some(
                            (item) =>
                              item.selected && item.generated && !item.scheduled
                          )
                        }
                      >
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Regenerate Selected
                      </Button>
                    </div>
                  </div>

                  {/* Production scheduling form */}
                  {queueItems.some(
                    (item) => item.selected && item.generated && !item.scheduled
                  ) && (
                      <Card className="mb-6 border-dashed border-2">
                        <CardContent className="p-4">
                          <h3 className="text-lg font-semibold mb-4 flex items-center">
                            <Send className="h-5 w-5 mr-2 text-blue-500" />
                            Send to Production
                          </h3>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                            <div>
                              <Label htmlFor="platform" className="mb-2 block">
                                Platform
                              </Label>
                              <Select
                                value={selectedPlatform}
                                onValueChange={setSelectedPlatform}
                              >
                                <SelectTrigger id="platform">
                                  <SelectValue placeholder="Select platform" />
                                </SelectTrigger>
                                <SelectContent>
                                  {PLATFORMS.map((platform) => (
                                    <SelectItem
                                      key={platform.name}
                                      value={platform.name}
                                    >
                                      <div className="flex items-center">
                                        <platform.icon className="h-4 w-4 mr-2" />
                                        {platform.name}
                                      </div>
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>

                            <div>
                              <Label htmlFor="time" className="mb-2 block">
                                Time
                              </Label>
                              <Select
                                value={selectedTime}
                                onValueChange={setSelectedTime}
                              >
                                <SelectTrigger id="time">
                                  <SelectValue placeholder="Select time" />
                                </SelectTrigger>
                                <SelectContent>
                                  {TIME_OPTIONS.map((time) => (
                                    <SelectItem key={time} value={time}>
                                      {time}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>

                            <div>
                              <Label className="mb-2 block">Days</Label>
                              <ToggleGroup
                                type="multiple"
                                value={selectedDays}
                                onValueChange={setSelectedDays}
                                className="flex flex-wrap gap-1 justify-start"
                              >
                                {DAYS.map((day) => (
                                  <ToggleGroupItem
                                    key={day}
                                    value={day}
                                    aria-label={day}
                                    className="px-2 py-1 text-xs"
                                  >
                                    {day}
                                  </ToggleGroupItem>
                                ))}
                              </ToggleGroup>
                            </div>
                          </div>

                          {(!selectedPlatform ||
                            !selectedTime ||
                            selectedDays.length === 0) && (
                              <div className="flex items-center text-amber-600 mb-4 text-sm">
                                <AlertCircle className="h-4 w-4 mr-2" />
                                Please select a platform, time, and at least one day
                                to schedule content.
                              </div>
                            )}

                          <Button
                            className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 w-full"
                            onClick={handleSendToProduction}
                            disabled={
                              isGenerating ||
                              !selectedPlatform ||
                              !selectedTime ||
                              selectedDays.length === 0
                            }
                          >
                            {isGenerating ? (
                              <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Scheduling...
                              </>
                            ) : (
                              <>
                                <Send className="h-4 w-4 mr-2" />
                                Send to Production
                              </>
                            )}
                          </Button>

                          {schedulingSuccess && (
                            <div className="bg-green-50 border border-green-200 rounded-md p-3 mt-4 flex items-center">
                              <Check className="h-5 w-5 text-green-500 mr-2" />
                              <p className="text-green-700">
                                Content successfully scheduled! View in the
                                Production Schedule tab.
                              </p>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    )}

                  <div className="space-y-4">
                    {queueItems
                      .filter((item) => item.generated && !item.scheduled)
                      .map((item) => (
                        <Card key={item.id} className="overflow-hidden">
                          <div className="flex items-start p-4">
                            <Checkbox
                              id={`generated-${item.id}`}
                              className="mt-1"
                              checked={item.selected}
                              onCheckedChange={(checked) =>
                                handleSelectItem(item.id, !!checked)
                              }
                            />
                            <div className="ml-3 flex-1">
                              <div className="flex items-center">
                                {getItemIcon(item.type)}
                                <Label
                                  htmlFor={`generated-${item.id}`}
                                  className="ml-2 font-medium cursor-pointer"
                                >
                                  {item.name}
                                </Label>
                              </div>
                              <Badge
                                className={`mt-1 ${getSourceBadgeColor(
                                  item.source
                                )}`}
                              >
                                {item.source}
                              </Badge>
                            </div>
                          </div>
                          <div className="px-4 pb-4 pt-2">
                            <Textarea
                              value={item.generatedContent}
                              onChange={(e) => {
                                setQueueItems((items) =>
                                  items.map((i) =>
                                    i.id === item.id
                                      ? {
                                        ...i,
                                        generatedContent: e.target.value,
                                      }
                                      : i
                                  )
                                );
                              }}
                              className="min-h-[100px] mt-2"
                            />
                            <div className="flex justify-end mt-2">
                              <Button size="sm" variant="outline">
                                <Wand2 className="h-4 w-4 mr-2" />
                                Regenerate
                              </Button>
                            </div>
                          </div>
                        </Card>
                      ))}
                  </div>
                </>
              ) : (
                <div className="text-center py-12">
                  <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold mb-2">
                    No Generated Content
                  </h3>
                  <p className="text-gray-500 mb-6 max-w-md mx-auto">
                    Select items from the queue tab and click "Generate Content"
                    to create content.
                  </p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="scheduled" className="space-y-4">
              {queueItems.filter((item) => item.scheduled).length > 0 ? (
                <>
                  <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="select-all-scheduled"
                        onCheckedChange={(checked) =>
                          handleSelectAll(!!checked)
                        }
                      />
                      <Label htmlFor="select-all-scheduled">Select All</Label>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRemoveSelected}
                        disabled={
                          !queueItems.some(
                            (item) => item.selected && item.scheduled
                          )
                        }
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Remove Selected
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {queueItems
                      .filter((item) => item.scheduled)
                      .map((item) => (
                        <Card key={item.id} className="overflow-hidden">
                          <div className="flex items-start p-4">
                            <Checkbox
                              id={`scheduled-${item.id}`}
                              className="mt-1"
                              checked={item.selected}
                              onCheckedChange={(checked) =>
                                handleSelectItem(item.id, !!checked)
                              }
                            />
                            <div className="ml-3 flex-1">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center">
                                  {getItemIcon(item.type)}
                                  <Label
                                    htmlFor={`scheduled-${item.id}`}
                                    className="ml-2 font-medium cursor-pointer"
                                  >
                                    {item.name}
                                  </Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                  {item.scheduledPlatform &&
                                    getPlatformIcon(item.scheduledPlatform)}
                                  <Badge className="bg-blue-100 text-blue-800">
                                    {item.scheduledDate} at {item.scheduledTime}
                                  </Badge>
                                </div>
                              </div>
                              <Badge
                                className={`mt-1 ${getSourceBadgeColor(
                                  item.source
                                )}`}
                              >
                                {item.source}
                              </Badge>
                            </div>
                          </div>
                          <div className="px-4 pb-4 pt-2">
                            <Textarea
                              value={item.generatedContent}
                              readOnly
                              className="min-h-[100px] mt-2"
                            />
                            <div className="flex justify-between mt-2">
                              <div className="flex items-center">
                                <Clock className="h-4 w-4 mr-1 text-blue-500" />
                                <span className="text-sm text-gray-600">
                                  Scheduled for {item.scheduledPlatform} on{" "}
                                  {item.scheduledDate} at {item.scheduledTime}
                                </span>
                              </div>
                              <Button size="sm" variant="outline">
                                <RefreshCw className="h-4 w-4 mr-2" />
                                Reschedule
                              </Button>
                            </div>
                          </div>
                        </Card>
                      ))}
                  </div>
                </>
              ) : (
                <div className="text-center py-12">
                  <Clock className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold mb-2">
                    No Scheduled Content
                  </h3>
                  <p className="text-gray-500 mb-6 max-w-md mx-auto">
                    Select items from the Generated Content tab and use "Send to
                    Production" to schedule content.
                  </p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
