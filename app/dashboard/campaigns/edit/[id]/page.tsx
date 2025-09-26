"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  ChevronLeft,
  Save,
  Settings,
  Database,
  Code,
  Network,
  Brain,
  BarChart,
  FileText,
  BookOpen,
  Twitter,
  Instagram,
  Video,
  Linkedin,
  Key,
  ExternalLink,
  Trash2,
  TrendingUp,
  Search,
} from "lucide-react";
import { CampaignResults } from "@/components/CampaignResults";
import { ErrorDialog } from "@/components/ErrorDialog";
import type { Campaign } from "@/components/ContentPlannerCampaign";
import { ResearchAssistant } from "@/components/ResearchAssistant";
import { ContentQueue } from "@/components/ContentQueue";
import { AuthorMimicry } from "@/components/AuthorMimicry";
import { TrendingOnX } from "@/components/TrendingOnX";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { getCampaignsById } from "@/components/Service";

const SAMPLE_CAMPAIGNS: Campaign[] = [
  {
    id: "campaign-1",
    name: "Q1 Marketing Strategy",
    description: "Content strategy for Q1 product launches and promotions",
    type: "keyword",
    keywords: [
      "product launch",
      "spring promotion",
      "new features",
      "customer testimonials",
    ],
    createdAt: new Date("2025-01-15"),
    updatedAt: new Date("2025-01-20"),
    extractionSettings: {
      webScrapingDepth: 2,
      includeImages: true,
      includeLinks: true,
      maxPages: 20,
      batchSize: 10,
    },
    preprocessingSettings: {
      removeStopwords: true,
      stemming: true,
      lemmatization: true,
      caseSensitive: false,
    },
    entitySettings: {
      extractPersons: true,
      extractOrganizations: true,
      extractLocations: true,
      extractDates: true,
      confidenceThreshold: 0.7,
    },
    modelingSettings: {
      algorithm: "lda",
      numTopics: 5,
      iterations: 100,
      passThreshold: 0.5,
    },
  },
  {
    id: "campaign-2",
    name: "Competitor Analysis",
    description: "Analysis of competitor content and positioning",
    type: "url",
    urls: [
      "https://competitor1.com/blog",
      "https://competitor2.com/products",
      "https://competitor3.com/features",
    ],
    createdAt: new Date("2025-02-01"),
    updatedAt: new Date("2025-02-10"),
  },
  {
    id: "campaign-3",
    name: "Industry Trends 2025",
    description: "Research on emerging industry trends for content planning",
    type: "keyword",
    keywords: [
      "industry trends",
      "future technology",
      "market predictions",
      "innovation",
    ],
    createdAt: new Date("2025-02-15"),
    updatedAt: new Date("2025-02-18"),
  },
  {
    id: "campaign-4",
    name: "Customer Success Stories",
    description:
      "Collection of customer success stories for content repurposing",
    type: "url",
    urls: [
      "https://ourwebsite.com/case-studies/customer1",
      "https://ourwebsite.com/case-studies/customer2",
      "https://ourwebsite.com/testimonials",
    ],
    createdAt: new Date("2025-03-01"),
    updatedAt: new Date("2025-03-05"),
  },
  {
    id: "campaign-5",
    name: "Social Media Trends",
    description: "Monitoring trending topics on X for content ideas",
    type: "trending",
    trendingTopics: [
      "#AITrends",
      "Digital Marketing",
      "Content Strategy",
      "Social Media Analytics",
    ],
    createdAt: new Date("2025-03-10"),
    updatedAt: new Date("2025-03-12"),
  },
];

export default function EditCampaignPage() {
  const router = useRouter();
  const params = useParams();
  const campaignId = params.id as string;
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<{ isOpen: boolean; message: string }>({
    isOpen: false,
    message: "",
  });
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("settings");
  const [trendingPlatform, setTrendingPlatform] = useState("x");
  const [queueItems, setQueueItems] = useState<
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

  const [instagramSearch, setInstagramSearch] = useState("");
  const [tiktokSearch, setTiktokSearch] = useState("");
  const [linkedinSearch, setLinkedinSearch] = useState("");
  const [campaignQuery, setCampaignQuery] = useState("");

  const [selectedInstagramTopics, setSelectedInstagramTopics] = useState<
    string[]
  >([]);
  const [selectedTiktokTopics, setSelectedTiktokTopics] = useState<string[]>(
    []
  );
  const [selectedLinkedinTopics, setSelectedLinkedinTopics] = useState<
    string[]
  >([]);

  const [campaignName, setCampaignName] = useState("");
  const [campaignDescription, setCampaignDescription] = useState("");
  const [campaignType, setCampaignType] = useState<
    "keyword" | "url" | "trending"
  >("keyword");
  const [keywordInput, setKeywordInput] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [urls, setUrls] = useState<string[]>([]);
  const [trendingKeyword, setTrendingKeyword] = useState("");
  const [trendingTopics, setTrendingTopics] = useState<string[]>([]);

  const instagramTrendingTopics = [
    {
      id: "ig-1",
      name: "#ContentCreation",
      engagement: "1.2M posts",
      relevance: 95,
    },
    {
      id: "ig-2",
      name: "#DigitalMarketing",
      engagement: "850K posts",
      relevance: 88,
    },
    {
      id: "ig-3",
      name: "#BrandStrategy",
      engagement: "620K posts",
      relevance: 76,
    },
    {
      id: "ig-4",
      name: "#SocialMediaTips",
      engagement: "1.5M posts",
      relevance: 92,
    },
    {
      id: "ig-5",
      name: "#MarketingStrategy",
      engagement: "780K posts",
      relevance: 84,
    },
  ];

  const tiktokTrendingTopics = [
    {
      id: "tt-1",
      name: "#MarketingTips",
      engagement: "2.3B views",
      relevance: 89,
    },
    {
      id: "tt-2",
      name: "#ContentStrategy",
      engagement: "1.7B views",
      relevance: 93,
    },
    {
      id: "tt-3",
      name: "#BusinessGrowth",
      engagement: "890M views",
      relevance: 78,
    },
    {
      id: "tt-4",
      name: "#SocialMediaMarketing",
      engagement: "3.1B views",
      relevance: 91,
    },
    {
      id: "tt-5",
      name: "#BrandAwareness",
      engagement: "1.2B views",
      relevance: 82,
    },
  ];

  const linkedinTrendingTopics = [
    {
      id: "li-1",
      name: "Content Marketing Strategy",
      engagement: "12K discussions",
      relevance: 96,
    },
    {
      id: "li-2",
      name: "B2B Marketing Trends",
      engagement: "8.5K discussions",
      relevance: 87,
    },
    {
      id: "li-3",
      name: "Digital Transformation",
      engagement: "15K discussions",
      relevance: 79,
    },
    {
      id: "li-4",
      name: "Marketing Automation",
      engagement: "7.2K discussions",
      relevance: 85,
    },
    {
      id: "li-5",
      name: "Thought Leadership",
      engagement: "9.8K discussions",
      relevance: 90,
    },
  ];

  useEffect(() => {
    if (!campaignId) return;
    const fetchCampaign = async () => {
      localStorage.removeItem("contentGenPayload");
      localStorage.removeItem("id");

      setIsLoading(true);
      try {
        // Fetch campaign from API
        const editableCampaigns = await getCampaignsById(campaignId);
        localStorage.setItem("id", campaignId);

        if (editableCampaigns.status === "success") {
          const editableCampaignsFound = editableCampaigns.message.raw_data[0];

          localStorage.setItem(
            "topics",
            JSON.stringify(editableCampaignsFound.topics)
          );
          localStorage.setItem(
            "text",
            JSON.stringify(editableCampaignsFound.lemmatized_text)
          );

          const storeText = {
            text: editableCampaigns.message.raw_data[0].text || "",
            stemmed_text: editableCampaigns.message.raw_data[0].stemmed_text || "",
            lemmatized_text: editableCampaigns.message.raw_data[0].lemmatized_text || "",
            stopwords_removed_text: editableCampaigns.message.raw_data[0].stopwords_removed_text || ""
          }

          localStorage.setItem(
            "storeText",
            JSON.stringify(storeText)
          );

          setCampaign(editableCampaignsFound);
          setCampaignName(editableCampaignsFound.campaign_name);
          setCampaignDescription(editableCampaignsFound.description);
          setCampaignQuery(editableCampaignsFound.query);
          setCampaignType(
            editableCampaignsFound.type === "twitter"
              ? "trending"
              : editableCampaignsFound.type || "keyword"
          );
          setKeywords(editableCampaignsFound.keywords || []);
          setUrls(editableCampaignsFound.urls || []);

          const trendingData = editableCampaignsFound.trending_content || [];
          const trendingTopicsArray = trendingData
            .map((item) => item.text)
            .filter((text) => text && typeof text === "string");
          setTrendingTopics(trendingTopicsArray);
        } else {
          setError({
            isOpen: true,
            message:
              "Campaign not found. Please try again or create a new campaign.",
          });
        }
      } catch (err) {
        setError({
          isOpen: true,
          message: "Failed to load campaign. Please try again later.",
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchCampaign();
  }, [campaignId]);

  useEffect(() => { }, [trendingTopics]);

  const handleSaveCampaign = () => {
    if (!campaign) return;

    setIsSaving(true);

    const updatedCampaign = {
      name: campaignName,
      description: campaignDescription,
      type: campaignType,
    };

    if (campaignType === "keyword") {
      updatedCampaign.keywords = keywords;
      updatedCampaign.urls = undefined;
      updatedCampaign.trendingTopics = undefined;
    } else if (campaignType === "url") {
      updatedCampaign.keywords = undefined;
      updatedCampaign.urls = urls;
      updatedCampaign.trendingTopics = undefined;
    } else if (campaignType === "trending") {
      updatedCampaign.keywords = undefined;
      updatedCampaign.urls = undefined;
      updatedCampaign.trendingTopics = trendingTopics;

      const existingPayload = localStorage.getItem("contentGenPayload") || "{}";
      let parsedPayload = {};
      try {
        parsedPayload = JSON.parse(existingPayload);
      } catch (e) {
        console.error("Failed to parse contentGenPayload:", e);
      }
      const updatedPayload = {
        ...parsedPayload,
        trendingTopic: trendingTopics,
      };
      localStorage.setItem("contentGenPayload", JSON.stringify(updatedPayload));
      console.log("Saved trendingTopics to localStorage:", updatedPayload);
    }

    setTimeout(() => {
      try {
        setCampaign({
          ...campaign,
          ...updatedCampaign,
          updatedAt: new Date(),
        });
        router.push("/dashboard/content-planner");
      } catch (err) {
        setError({
          isOpen: true,
          message: "Failed to save campaign. Please try again later.",
        });
      } finally {
        setIsSaving(false);
      }
    }, 1000);
  };

  const closeErrorDialog = () => {
    setError({ isOpen: false, message: "" });
  };

  const handleAddToQueue = (
    items: Array<{ id: string; type: string; name: string; source: string }>
  ) => {
    setQueueItems((prev) => {
      const newItems = items.filter(
        (item) => !prev.some((prevItem) => prevItem.id === item.id)
      );
      return [...prev, ...newItems];
    });
    setActiveTab("content-queue");
  };

  const handleClearQueue = () => {
    setQueueItems([]);
  };

  const handleAddKeyword = () => {
    if (keywordInput.trim()) {
      setKeywords([...keywords, keywordInput.trim()]);
      setKeywordInput("");
    }
  };

  const handleRemoveKeyword = (index: number) => {
    setKeywords(keywords.filter((_, i) => i !== index));
  };

  const handleAddUrl = () => {
    if (urlInput.trim()) {
      try {
        let urlToAdd = urlInput.trim();
        if (!/^https?:\/\//i.test(urlToAdd)) {
          urlToAdd = "https://" + urlToAdd;
        }

        new URL(urlToAdd);

        setUrls((PrevUrls) => [...PrevUrls, urlToAdd]);
        setUrlInput("");
      } catch (e) {
        setError({
          isOpen: true,
          message:
            "Please enter a valid URL (e.g., example.com or https://example.com)",
        });
      }
    }
  };

  const handleRemoveUrl = (index: number) => {
    setUrls(urls.filter((_, i) => i !== index));
  };

  const handleAddTrendingTopic = () => {
    if (trendingKeyword.trim()) {
      setTrendingTopics([...trendingTopics, trendingKeyword.trim()]);
      setTrendingKeyword("");
    }
  };

  const handleRemoveTrendingTopic = (index: number) => {
    setTrendingTopics(trendingTopics.filter((_, i) => i !== index));
  };

  const handleInstagramCheckboxChange = (topicId: string) => {
    setSelectedInstagramTopics((prev) =>
      prev.includes(topicId)
        ? prev.filter((id) => id !== topicId)
        : [...prev, topicId]
    );
  };

  const handleTiktokCheckboxChange = (topicId: string) => {
    setSelectedTiktokTopics((prev) =>
      prev.includes(topicId)
        ? prev.filter((id) => id !== topicId)
        : [...prev, topicId]
    );
  };

  const handleLinkedinCheckboxChange = (topicId: string) => {
    setSelectedLinkedinTopics((prev) =>
      prev.includes(topicId)
        ? prev.filter((id) => id !== topicId)
        : [...prev, topicId]
    );
  };

  const handleAddInstagramToQueue = () => {
    const selectedItems = instagramTrendingTopics
      .filter((topic) => selectedInstagramTopics.includes(topic.id))
      .map((topic) => ({
        id: topic.id,
        type: "hashtag",
        name: topic.name,
        source: "Instagram Trending",
      }));

    if (selectedItems.length > 0) {
      handleAddToQueue(selectedItems);
      setSelectedInstagramTopics([]);
    }
  };

  const handleAddTiktokToQueue = () => {
    const selectedItems = tiktokTrendingTopics
      .filter((topic) => selectedTiktokTopics.includes(topic.id))
      .map((topic) => ({
        id: topic.id,
        type: "hashtag",
        name: topic.name,
        source: "TikTok Trending",
      }));

    if (selectedItems.length > 0) {
      handleAddToQueue(selectedItems);
      setSelectedTiktokTopics([]);
    }
  };

  const handleAddLinkedinToQueue = () => {
    const selectedItems = linkedinTrendingTopics
      .filter((topic) => selectedLinkedinTopics.includes(topic.id))
      .map((topic) => ({
        id: topic.id,
        type: "topic",
        name: topic.name,
        source: "LinkedIn Trending",
      }));

    if (selectedItems.length > 0) {
      handleAddToQueue(selectedItems);
      setSelectedLinkedinTopics([]);
    }
  };

  const handleInstagramSearch = () => {
    console.log("Searching Instagram for:", instagramSearch);
  };

  const handleTiktokSearch = () => {
    console.log("Searching TikTok for:", tiktokSearch);
  };

  const handleLinkedinSearch = () => {
    console.log("Searching LinkedIn for:", linkedinSearch);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <div className="flex items-center space-x-4">
            <Link
              href="/dashboard/content-planner"
              className="flex items-center text-white hover:text-gray-200"
            >
              <ChevronLeft className="h-5 w-5 mr-1" />
              Back to Campaigns
            </Link>
            <h1 className="text-4xl font-extrabold text-white">
              Loading Campaign...
            </h1>
          </div>
          <Card>
            <CardContent className="p-6 flex justify-center items-center min-h-[400px]">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </CardContent>
          </Card>
        </main>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <div className="flex items-center space-x-4">
            <Link
              href="/dashboard/content-planner"
              className="flex items-center text-white hover:text-gray-200"
            >
              <ChevronLeft className="h-5 w-5 mr-1" />
              Back to Campaigns
            </Link>
            <h1 className="text-4xl font-extrabold text-white">
              Campaign Not Found
            </h1>
          </div>
          <Card>
            <CardContent className="p-6 flex flex-col items-center justify-center min-h-[400px]">
              <h2 className="text-2xl font-semibold mb-4">
                Campaign Not Found
              </h2>
              <p className="text-gray-500 mb-6">
                The campaign you're looking for doesn't exist or has been
                deleted.
              </p>
              <Link href="/dashboard/content-planner">
                <Button className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">
                  Return to Campaigns
                </Button>
              </Link>
            </CardContent>
          </Card>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <Header />
      <main className="p-6 max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link
              href="/dashboard/content-planner"
              className="flex items-center text-white hover:text-gray-200"
            >
              <ChevronLeft className="h-5 w-5 mr-1" />
              Back to Campaigns
            </Link>
            <h1 className="text-4xl font-extrabold text-white">
              Edit Campaign
            </h1>
          </div>
          {/* <Button
            onClick={handleSaveCampaign}
            disabled={isSaving}
            className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
          >
            {isSaving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Campaign
              </>
            )}
          </Button> */}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>
              {campaign.name}
              <span className="ml-2 text-sm bg-secondary text-secondary-foreground px-2 py-1 rounded-full">
                {campaign.type === "keyword"
                  ? "Keywords"
                  : campaign.type === "url"
                    ? "URLs"
                    : "Trending"}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-8 px-6 pb-6">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="w-full mb-12 grid grid-cols-1 gap-4">
                {/* Settings Section */}
                <div className="grid grid-cols-5 gap-2">
                  <TabsTrigger value="settings" className="flex items-center">
                    <Settings className="h-4 w-4 mr-2" />
                    <span>Settings</span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="author-personality"
                    className="flex items-center"
                  >
                    <BookOpen className="h-4 w-4 mr-2" />
                    <span>Author Personality</span>
                  </TabsTrigger>
                  <TabsTrigger value="research" className="flex items-center">
                    <BarChart className="h-4 w-4 mr-2" />
                    <span>Research Assistant</span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="content-queue"
                    className="flex items-center"
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    <span> Content Queue</span>
                  </TabsTrigger>
                  <TabsTrigger value="trending" className="flex items-center">
                    <TrendingUp className="h-4 w-4 mr-2" />
                    <span>Trending</span>
                  </TabsTrigger>
                </div>

                {/* Data Processing Section */}
                <div className="grid grid-cols-3 gap-2">
                  <TabsTrigger
                    value="extraction-results"
                    className="flex items-center"
                  >
                    <Database className="h-4 w-4 mr-2" />
                    <span className="hidden sm:inline">Extraction</span>
                    <span className="sm:hidden">Extract</span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="preprocessing-results"
                    className="flex items-center"
                  >
                    <Code className="h-4 w-4 mr-2" />
                    <span className="hidden sm:inline">Preprocessing</span>
                    <span className="sm:hidden">Preprocess</span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="entity-results"
                    className="flex items-center"
                  >
                    <Network className="h-4 w-4 mr-2" />
                    <span className="hidden sm:inline">Entities</span>
                    <span className="sm:hidden">Entities</span>
                  </TabsTrigger>
                </div>

                {/* Analysis Section */}
                <div className="grid grid-cols-2 gap-2">
                  <TabsTrigger
                    value="topic-results"
                    className="flex items-center"
                  >
                    <Brain className="h-4 w-4 mr-2" />
                    <span className="hidden sm:inline">Topic Modeling</span>
                    <span className="sm:hidden">Topics</span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="content-results"
                    className="flex items-center"
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    <span className="hidden sm:inline">Content</span>
                    <span className="sm:hidden">Content</span>
                  </TabsTrigger>
                </div>
              </TabsList>

              <TabsContent value="settings" className="relative z-10 mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Campaign Settings</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="space-y-2">
                      <Label htmlFor="campaign-name">Campaign Name</Label>
                      <Input
                        id="campaign-name"
                        value={campaignName}
                        onChange={(e) => setCampaignName(e.target.value)}
                        placeholder="Enter campaign name"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="campaign-description">Description</Label>
                      <Textarea
                        id="campaign-description"
                        value={campaignDescription}
                        onChange={(e) => setCampaignDescription(e.target.value)}
                        placeholder="Enter campaign description"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="campaign-description">Query</Label>
                      <Textarea
                        id="campaign-description"
                        value={campaignQuery}
                        onChange={(e) => setCampaignQuery(e.target.value)}
                        placeholder="Enter campaign description"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Campaign Type</Label>
                      <Tabs
                        value={campaignType}
                        onValueChange={(value) =>
                          setCampaignType(
                            value as "keyword" | "url" | "trending"
                          )
                        }
                        className="w-full mt-2"
                      >
                        <TabsList className="w-full">
                          <TabsTrigger value="keyword" className="flex-1">
                            <Key className="w-4 h-4 mr-2" />
                            Keywords/Phrases
                          </TabsTrigger>
                          <TabsTrigger value="url" className="flex-1">
                            <ExternalLink className="w-4 h-4 mr-2" />
                            URLs
                          </TabsTrigger>
                          <TabsTrigger value="trending" className="flex-1">
                            <Twitter className="w-4 h-4 mr-2" />
                            Trending on X
                          </TabsTrigger>
                        </TabsList>

                        <TabsContent value="keyword" className="space-y-4 mt-4">
                          <div className="flex space-x-2">
                            <Input
                              value={keywordInput}
                              onChange={(e) => setKeywordInput(e.target.value)}
                              placeholder="Enter keyword or phrase"
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.preventDefault();
                                  handleAddKeyword();
                                }
                              }}
                            />
                            <Button onClick={handleAddKeyword}>Add</Button>
                          </div>

                          {keywords.length > 0 && (
                            <div className="border rounded-md p-4">
                              <Label className="mb-2 block">
                                Keywords/Phrases:
                              </Label>
                              <div className="flex flex-wrap gap-2">
                                {keywords.map((keyword, index) => (
                                  <div
                                    key={index}
                                    className="flex items-center bg-secondary text-secondary-foreground px-3 py-1 rounded-full"
                                  >
                                    <span>{keyword}</span>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-auto p-1 ml-1"
                                      onClick={() => handleRemoveKeyword(index)}
                                    >
                                      <Trash2 className="w-3 h-3" />
                                    </Button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </TabsContent>

                        <TabsContent value="url" className="space-y-4 mt-4">
                          <div className="flex space-x-2">
                            <Input
                              value={urlInput}
                              onChange={(e) => setUrlInput(e.target.value)}
                              placeholder="Enter URL (e.g., https://example.com)"
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.preventDefault();
                                  handleAddUrl();
                                }
                              }}
                            />
                            <Button onClick={handleAddUrl}>Add</Button>
                          </div>

                          {urls.length > 0 && (
                            <div className="border rounded-md p-4">
                              <Label className="mb-2 block">URLs:</Label>
                              <div className="space-y-2">
                                {urls?.map((url, index) => (
                                  <div
                                    key={index}
                                    className="flex items-center justify-between bg-secondary text-secondary-foreground p-2 rounded"
                                  >
                                    <a
                                      href={url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-blue-600 hover:underline truncate"
                                    >
                                      {url}
                                    </a>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-auto p-1 ml-1"
                                      onClick={() => handleRemoveUrl(index)}
                                    >
                                      <Trash2 className="w-4 h-4" />
                                    </Button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </TabsContent>

                        <TabsContent
                          value="trending"
                          className="space-y-4 mt-4"
                        >
                          <div className="flex space-x-2">
                            <Input
                              value={trendingKeyword}
                              onChange={(e) =>
                                setTrendingKeyword(e.target.value)
                              }
                              placeholder="Enter trending topic"
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.preventDefault();
                                  handleAddTrendingTopic();
                                }
                              }}
                            />
                            <Button onClick={handleAddTrendingTopic}>
                              Add
                            </Button>
                          </div>

                          {trendingTopics.length > 0 && (
                            <div className="border rounded-md p-4">
                              <Label className="mb-2 block">
                                Trending Topics:
                              </Label>
                              <div className="flex flex-wrap gap-2">
                                {trendingTopics.map((topic, index) => (
                                  <div
                                    key={index}
                                    className="flex items-center bg-secondary text-secondary-foreground px-3 py-1 rounded-full"
                                  >
                                    <span>{topic}</span>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-auto p-1 ml-1"
                                      onClick={() =>
                                        handleRemoveTrendingTopic(index)
                                      }
                                    >
                                      <Trash2 className="w-3 h-3" />
                                    </Button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </TabsContent>
                      </Tabs>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent
                value="author-personality"
                className="relative z-10 mt-6"
              >
                <AuthorMimicry />
              </TabsContent>

              <TabsContent value="research" className="relative z-10 mt-6">
                <ResearchAssistant
                  campaign={campaign}
                  onAddToQueue={handleAddToQueue}
                />
              </TabsContent>

              <TabsContent value="content-queue" className="relative z-10 mt-6">
                <ContentQueue
                  queueItems={queueItems}
                  onClearQueue={handleClearQueue}
                />
              </TabsContent>

              <TabsContent value="trending" className="relative z-10 mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Trending Topics</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Tabs
                      defaultValue="x"
                      value={trendingPlatform}
                      onValueChange={setTrendingPlatform}
                    >
                      {/* <TabsList className="w-full mb-6">
                        <TabsTrigger value="x" className="flex-1">
                          <Twitter className="w-4 h-4 mr-2" />X
                        </TabsTrigger>
                        <TabsTrigger value="instagram" className="flex-1">
                          <Instagram className="w-4 h-4 mr-2" />
                          Instagram
                        </TabsTrigger>
                        <TabsTrigger value="tiktok" className="flex-1">
                          <Video className="w-4 h-4 mr-2" />
                          TikTok
                        </TabsTrigger>
                        <TabsTrigger value="linkedin" className="flex-1">
                          <Linkedin className="w-4 h-4 mr-2" />
                          LinkedIn
                        </TabsTrigger>
                      </TabsList> */}

                      <TabsContent value="x">
                        <TrendingOnX
                          onAddToQueue={handleAddToQueue}
                          trendingContent={trendingTopics}
                        />
                      </TabsContent>

                      <TabsContent value="instagram">
                        <div className="space-y-6">
                          <div className="flex space-x-2">
                            <div className="relative flex-1">
                              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                              <Input
                                type="search"
                                placeholder="Search trending topics on Instagram..."
                                className="w-full pl-8"
                                value={instagramSearch}
                                onChange={(e) =>
                                  setInstagramSearch(e.target.value)
                                }
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    e.preventDefault();
                                    handleInstagramSearch();
                                  }
                                }}
                              />
                            </div>
                            <Button onClick={handleInstagramSearch}>
                              Search
                            </Button>
                          </div>

                          <div className="border rounded-lg p-4">
                            <h3 className="font-medium mb-4">
                              Trending on Instagram
                            </h3>
                            <div className="space-y-4">
                              {instagramTrendingTopics.map((topic) => (
                                <div
                                  key={topic.id}
                                  className="flex items-center justify-between"
                                >
                                  <div className="flex items-center gap-2">
                                    <Checkbox
                                      id={`ig-check-${topic.id}`}
                                      checked={selectedInstagramTopics.includes(
                                        topic.id
                                      )}
                                      onCheckedChange={() =>
                                        handleInstagramCheckboxChange(topic.id)
                                      }
                                    />
                                    <div>
                                      <Label
                                        htmlFor={`ig-check-${topic.id}`}
                                        className="font-medium"
                                      >
                                        {topic.name}
                                      </Label>
                                      <p className="text-sm text-muted-foreground">
                                        {topic.engagement}
                                      </p>
                                    </div>
                                  </div>
                                  <Badge variant="secondary">
                                    {topic.relevance}% relevant
                                  </Badge>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="flex justify-end">
                            <Button
                              onClick={handleAddInstagramToQueue}
                              disabled={selectedInstagramTopics.length === 0}
                            >
                              Add Selected to Queue
                            </Button>
                          </div>
                        </div>
                      </TabsContent>

                      <TabsContent value="tiktok">
                        <div className="space-y-6">
                          <div className="flex space-x-2">
                            <div className="relative flex-1">
                              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                              <Input
                                type="search"
                                placeholder="Search trending topics on TikTok..."
                                className="w-full pl-8"
                                value={tiktokSearch}
                                onChange={(e) =>
                                  setTiktokSearch(e.target.value)
                                }
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    e.preventDefault();
                                    handleTiktokSearch();
                                  }
                                }}
                              />
                            </div>
                            <Button onClick={handleTiktokSearch}>Search</Button>
                          </div>

                          <div className="border rounded-lg p-4">
                            <h3 className="font-medium mb-4">
                              Trending on TikTok
                            </h3>
                            <div className="space-y-4">
                              {tiktokTrendingTopics.map((topic) => (
                                <div
                                  key={topic.id}
                                  className="flex items-center justify-between"
                                >
                                  <div className="flex items-center gap-2">
                                    <Checkbox
                                      id={`tt-check-${topic.id}`}
                                      checked={selectedTiktokTopics.includes(
                                        topic.id
                                      )}
                                      onCheckedChange={() =>
                                        handleTiktokCheckboxChange(topic.id)
                                      }
                                    />
                                    <div>
                                      <Label
                                        htmlFor={`tt-check-${topic.id}`}
                                        className="font-medium"
                                      >
                                        {topic.name}
                                      </Label>
                                      <p className="text-sm text-muted-foreground">
                                        {topic.engagement}
                                      </p>
                                    </div>
                                  </div>
                                  <Badge variant="secondary">
                                    {topic.relevance}% relevant
                                  </Badge>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="flex justify-end">
                            <Button
                              onClick={handleAddTiktokToQueue}
                              disabled={selectedTiktokTopics.length === 0}
                            >
                              Add Selected to Queuedfd
                            </Button>
                          </div>
                        </div>
                      </TabsContent>

                      <TabsContent value="linkedin">
                        <div className="space-y-6">
                          <div className="flex space-x-2">
                            <div className="relative flex-1">
                              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                              <Input
                                type="search"
                                placeholder="Search trending topics on LinkedIn..."
                                className="w-full pl-8"
                                value={linkedinSearch}
                                onChange={(e) =>
                                  setLinkedinSearch(e.target.value)
                                }
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    e.preventDefault();
                                    handleLinkedinSearch();
                                  }
                                }}
                              />
                            </div>
                            <Button onClick={handleLinkedinSearch}>
                              Search
                            </Button>
                          </div>

                          <div className="border rounded-lg p-4">
                            <h3 className="font-medium mb-4">
                              Trending on LinkedIn
                            </h3>
                            <div className="space-y-4">
                              {linkedinTrendingTopics.map((topic) => (
                                <div
                                  key={topic.id}
                                  className="flex items-center justify-between"
                                >
                                  <div className="flex items-center gap-2">
                                    <Checkbox
                                      id={`li-check-${topic.id}`}
                                      checked={selectedLinkedinTopics.includes(
                                        topic.id
                                      )}
                                      onCheckedChange={() =>
                                        handleLinkedinCheckboxChange(topic.id)
                                      }
                                    />
                                    <div>
                                      <Label
                                        htmlFor={`li-check-${topic.id}`}
                                        className="font-medium"
                                      >
                                        {topic.name}
                                      </Label>
                                      <p className="text-sm text-muted-foreground">
                                        {topic.engagement}
                                      </p>
                                    </div>
                                  </div>
                                  <Badge variant="secondary">
                                    {topic.relevance}% relevant
                                  </Badge>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="flex justify-end">
                            <Button
                              onClick={handleAddLinkedinToQueue}
                              disabled={selectedLinkedinTopics.length === 0}
                            >
                              Add Selected to Queuef
                            </Button>
                          </div>
                        </div>
                      </TabsContent>
                    </Tabs>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent
                value="extraction-results"
                className="relative z-10 mt-6"
              >
                <CampaignResults
                  title="Information Extraction Results"
                  icon={<Database className="h-5 w-5" />}
                  campaign={campaign}
                  stage="extraction"
                  hasResults={false}
                  onRunAnalysis={() => {
                    // In a real app, this would trigger the extraction process
                    console.log(
                      "Running extraction for campaign:",
                      campaign.id
                    );
                  }}
                />
              </TabsContent>

              <TabsContent
                value="preprocessing-results"
                className="relative z-10 mt-6"
              >
                <CampaignResults
                  title="Preprocessing Results"
                  icon={<Code className="h-5 w-5" />}
                  campaign={campaign}
                  stage="preprocessing"
                  hasResults={false}
                  onRunAnalysis={() => {
                    // In a real app, this would trigger the preprocessing
                    console.log(
                      "Running preprocessing for campaign:",
                      campaign.id
                    );
                  }}
                />
              </TabsContent>

              <TabsContent
                value="entity-results"
                className="relative z-10 mt-6"
              >
                <CampaignResults
                  title="Entity Recognition Results"
                  icon={<Network className="h-5 w-5" />}
                  campaign={campaign}
                  stage="entity"
                  hasResults={false}
                  onRunAnalysis={() => {
                    // In a real app, this would trigger the entity recognition
                    console.log(
                      "Running entity recognition for campaign:",
                      campaign.id
                    );
                  }}
                />
              </TabsContent>

              <TabsContent value="topic-results" className="relative z-10 mt-6">
                <CampaignResults
                  title="Topic Modeling Results"
                  icon={<Brain className="h-5 w-5" />}
                  campaign={campaign}
                  stage="topic"
                  hasResults={false}
                  onRunAnalysis={() => {
                    // In a real app, this would trigger the topic modeling
                    console.log(
                      "Running topic modeling for campaign:",
                      campaign.id
                    );
                  }}
                />
              </TabsContent>

              <TabsContent
                value="content-results"
                className="relative z-10 mt-6"
              >
                <CampaignResults
                  title="Content Generation Results"
                  icon={<FileText className="h-5 w-5" />}
                  campaign={campaign}
                  stage="content"
                  hasResults={false}
                  onRunAnalysis={() => {
                    // In a real app, this would trigger the content generation
                    console.log(
                      "Running content generation for campaign:",
                      campaign.id
                    );
                  }}
                />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </main>
      <ErrorDialog
        isOpen={error.isOpen}
        onClose={closeErrorDialog}
        message={error.message}
      />
    </div>
  );
}
