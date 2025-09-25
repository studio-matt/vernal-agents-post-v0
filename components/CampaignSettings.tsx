"use client";

import type React from "react";
import { useState, Dispatch, SetStateAction, useEffect } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import {
  Key,
  ExternalLink,
  Database,
  Brain,
  Code,
  Network,
  InfoIcon,
  Loader2,
  CheckCircle,
} from "lucide-react";
import { ParameterInfoModal } from "./ParameterInfoModal";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import {
  analyzeTrends,
  AnalyzeTrendsInput,
  AnalyzeTrendsResponse,
  getAllCampaigns,
  getTrendingContent,
} from "@/components/Service";
import { Campaign as CampaignBase } from "@/components/ContentPlannerCampaign";

// Extend the Campaign type to include topics and posts
interface Campaign extends CampaignBase {
  id: string;
  name: string;
  description: string;
  type: "keyword" | "url" | "trending";
  keywords?: string[];
  urls?: string[];
  trendingTopics?: string[];
  createdAt: Date;
  updatedAt: Date;
  extractionSettings?: {
    webScrapingDepth: number;
    includeImages: boolean;
    includeLinks: boolean;
    maxPages: number;
    batchSize: number;
  };
  preprocessingSettings?: {
    removeStopwords: boolean;
    stemming: boolean;
    lemmatization: boolean;
    caseSensitive: boolean;
  };
  entitySettings?: {
    extractPersons: boolean;
    extractOrganizations: boolean;
    extractLocations: boolean;
    extractDates: boolean;
    confidenceThreshold: number;
  };
  modelingSettings?: {
    algorithm: string;
    numTopics: number;
    iterations: number;
    passThreshold: number;
  };
}

interface Campaign1 extends CampaignBase {
  topics?: string[];
  posts?: {
    text: string;
    lemmatized_text: string | null;
    stemmed_text: string | null;
    stopwords_removed_text: string | null;
    persons: string[];
    organizations: string[];
    locations: string[];
    dates: string[];
    topics: string[];
  }[];
}

interface CampaignSettingsProps {
  setSettings: Dispatch<SetStateAction<Campaign[]>>;
  campaign: Campaign;
  trendingKeyword?: string;
  onSave: (
    updatedCampaign: Omit<Campaign, "id" | "createdAt" | "updatedAt">
  ) => void;
  onCancel: () => void;
}

export function CampaignSettings({
  campaign,
  trendingKeyword = "",
  setSettings,
  onSave,
  onCancel,
}: CampaignSettingsProps) {
  const [name, setName] = useState(campaign.name);
  const [description, setDescription] = useState(campaign.description);
  const [query, setQuery] = useState(campaign.query);
  const [type, setType] = useState<"keyword" | "url" | "trending">(
    campaign.type
  );
  const [keywordInput, setKeywordInput] = useState("");
  const [keywords, setKeywords] = useState<string[]>(campaign.keywords || []);
  const [urlInput, setUrlInput] = useState("");
  const [urls, setUrls] = useState<string[]>(campaign.urls || []);
  const [isSaving, setIsSaving] = useState(false);
  const [showSavedModal, setShowSavedModal] = useState(false);
  const [isBuilding, setIsBuilding] = useState(false);
  const [showCampaignBuildingMessage, setShowCampaignBuildingMessage] = useState("");

  // Advanced settings with enforced false defaults for toggles
  const [extractionSettings, setExtractionSettings] = useState({
    webScrapingDepth: 2,
    includeImages: false,
    includeLinks: false,
    maxPages: 10,
    batchSize: 10,
  });

  const [preprocessingSettings, setPreprocessingSettings] = useState({
    removeStopwords: true,
    stemming: true,
    lemmatization: true,
    caseSensitive: true,
  });

  const [entitySettings, setEntitySettings] = useState({
    extractPersons: true,
    extractOrganizations: true,
    extractLocations: true,
    extractDates: true,
    confidenceThreshold: 0.7,
  });

  const [modelingSettings, setModelingSettings] = useState({
    algorithm: "llm", // Enforce "llm" as default
    numTopics: 5,
    iterations: 10,
    passThreshold: 0.5,
  });

  // Add a flag to control rendering after setting defaults
  const [isMounted, setIsMounted] = useState(false);

  // Sync non-toggle state with campaign prop changes, but enforce "llm" as default
  useEffect(() => {
    setName(campaign.name);
    setDescription(campaign.description);
    setQuery(campaign.query);
    setType(campaign.type);
    setKeywords(campaign.keywords || []);
    setUrls(campaign.urls || []);
    // Only sync non-toggle settings to avoid overriding defaults
    setExtractionSettings({
      webScrapingDepth: campaign.extractionSettings?.webScrapingDepth ?? 2,
      includeImages: false, // Enforce false
      includeLinks: false, // Enforce false
      maxPages: campaign.extractionSettings?.maxPages ?? 10,
      batchSize: campaign.extractionSettings?.batchSize ?? 10,
    });
    setPreprocessingSettings({
      removeStopwords: true, // Enforce false
      stemming: true, // Enforce false
      lemmatization: true, // Enforce false
      caseSensitive: true, // Enforce false
    });
    setEntitySettings({
      extractPersons: true, // Enforce true
      extractOrganizations: true, // Enforce true
      extractLocations: true, // Enforce true
      extractDates: true, // Enforce true
      confidenceThreshold: campaign.entitySettings?.confidenceThreshold ?? 0.7,
    });
    // Always set algorithm to "llm" on initial mount to enforce default
    setModelingSettings({
      algorithm: "llm", // Force "llm" as default, ignoring campaign prop
      numTopics: campaign.modelingSettings?.numTopics ?? 5,
      iterations: campaign.modelingSettings?.iterations ?? 10,
      passThreshold: campaign.modelingSettings?.passThreshold ?? 0.5,
    });
    setIsMounted(true); // Allow rendering after setting defaults
  }, [campaign]);

  // Log initial state for debugging
  // useEffect(() => {
  //   console.log("Initial State:", {
  //     extractionSettings,
  //     preprocessingSettings,
  //     entitySettings,
  //     modelingSettings,
  //   });
  // }, [
  //   extractionSettings,
  //   preprocessingSettings,
  //   entitySettings,
  //   modelingSettings,
  // ]);

  const { toast } = useToast();

  const openInfoModal = (title: string, description: React.ReactNode) => {
    setInfoModal({
      isOpen: true,
      title,
      description,
    });
  };

  const closeInfoModal = () => {
    setInfoModal({
      ...infoModal,
      isOpen: false,
    });
  };

  const [infoModal, setInfoModal] = useState<{
    isOpen: boolean;
    title: string;
    description: React.ReactNode;
  }>({
    isOpen: false,
    title: "",
    description: "",
  });

  const parameterDescriptions = {
    maxPages: (
      <div className="space-y-2">
        <div>How many pages total should we scrape?</div>
        <div>
          <strong>Low (50):</strong> Good for quick tests (like sampling a
          blog).
        </div>
        <div>
          <strong>High (1000+):</strong> Full site crawl (might take hours).
        </div>
        <div className="text-sm text-gray-600 mt-2">
          Example: Set to 100 to avoid overwhelming small websites.
        </div>
      </div>
    ),
    webScrapingDepth: (
      <div className="space-y-2">
        <div>How many clicks away from the homepage?</div>
        <div>
          <strong>1:</strong> Only the homepage (great for news sites).
        </div>
        <div>
          <strong>3:</strong> Homepage → Category → Product → Reviews (common
          for e-commerce).
        </div>
      </div>
    ),
    batchSize: (
      <div className="space-y-2">
        <div>How many pages to process at once?</div>
        <div>
          <strong>10:</strong> Gentle on servers (avoids bans).
        </div>
        <div>
          <strong>100:</strong> Fast but risky (might get blocked).
        </div>
        <div className="text-sm text-gray-600 mt-2">
          Like checkout lanes – more lanes speed things up but annoy the store
          manager.
        </div>
      </div>
    ),
    includeImages: (
      <div className="space-y-2">
        <div>Determines whether images are included in the scraped data.</div>
        <div>
          <strong>ON:</strong> Scrapes image URLs and metadata (increases data
          size).
        </div>
        <div>
          <strong>OFF:</strong> Ignores images (faster scraping).
        </div>
      </div>
    ),
    includeLinks: (
      <div className="space-y-2">
        <div>
          Determines whether hyperlinks are included in the scraped data.
        </div>
        <div>
          <strong>ON:</strong> Extracts all URLs found on the page.
        </div>
        <div>
          <strong>OFF:</strong> Ignores links (reduces noise in data).
        </div>
      </div>
    ),
    removeStopwords: (
      <div className="space-y-2">
        <div>
          <strong>ON:</strong> Filters out 'the', 'and', 'is' (focuses on meaty
          words).
        </div>
        <div>
          <strong>OFF:</strong> Keeps all words (better for phrases like 'to be
          or not to be').
        </div>
      </div>
    ),
    stemming: (
      <div className="space-y-2">
        <div>Chops word endings – 'running' → 'run', 'happily' → 'happy'.</div>
        <div>Fast but crude (might turn 'pony' → 'pon').</div>
      </div>
    ),
    lemmatization: (
      <div className="space-y-2">
        <div>
          Uses dictionaries to find base forms – 'better' → 'good', 'mice' →
          'mouse'.
        </div>
        <div>Slower but more accurate.</div>
      </div>
    ),
    caseSensitive: (
      <div className="space-y-2">
        <div>
          <strong>ON:</strong> Treats 'Apple' (company) ≠ 'apple' (fruit).
        </div>
        <div>
          <strong>OFF:</strong> Merges them (good for casual text).
        </div>
      </div>
    ),
    extractPersons: (
      <div className="space-y-2">
        <div>
          Finds names like 'Alice' or 'Dr. Smith' (may miss nicknames like 'Big
          Al').
        </div>
      </div>
    ),
    extractLocations: (
      <div className="space-y-2">
        <div>
          Detects cities ('Paris'), countries ('Canada'), but not informal
          addresses ('my backyard').
        </div>
      </div>
    ),
    extractOrganizations: (
      <div className="space-y-2">
        <div>
          Tags companies ('Google') and institutions ('UN') – might confuse
          abbreviations ('NASA' vs 'nasa').
        </div>
      </div>
    ),
    extractDates: (
      <div className="space-y-2">
        <div>
          Catches 'March 2025' or 'next Tuesday' but not relative times ('a few
          days ago').
        </div>
      </div>
    ),
    confidenceThreshold: (
      <div className="space-y-2">
        <div>How sure should the model be?</div>
        <div>
          <strong>Low (0.5):</strong> Tags more guesses ('Jordan' = person or
          country?).
        </div>
        <div>
          <strong>High (0.9):</strong> Only crystal-clear matches (misses tricky
          cases).
        </div>
      </div>
    ),
    algorithm: (
      <div className="space-y-4">
        <div>
          <strong>LLM:</strong> Uses advanced large language models for
          context-aware topic modeling. Ideal for nuanced and complex datasets.
        </div>
        <div>
          <strong>LDA:</strong> Classic method (like sorting docs into folders).
          Needs 10-20 topics.
        </div>
        <div>
          <strong>BERTopic:</strong> Uses AI (groups by meaning, not just
          words). Great for long texts.
        </div>
        <div>
          <strong>NMF:</strong> Lightweight for small datasets (avoids gibberish
          topics).
        </div>
        <div>
          <strong>LSA:</strong> Old-school (fast but vague). Use for quick
          drafts.
        </div>
      </div>
    ),
    numTopics: (
      <div className="space-y-2">
        <div>How many themes to look for?</div>
        <div>
          <strong>5:</strong> Broad categories (e.g., 'Sports', 'Tech').
        </div>
        <div>
          <strong>20:</strong> Niche subtopics (e.g., 'Vintage Baseball Cards',
          'AI Ethics').
        </div>
      </div>
    ),
    iterations: (
      <div className="space-y-2">
        <div>How long to refine topics?</div>
        <div>
          <strong>50:</strong> Quick draft (coffee break speed).
        </div>
        <div>
          <strong>500:</strong> Polished results (overnight run).
        </div>
      </div>
    ),
    passThreshold: (
      <div className="space-y-2">
        <div>How clear must a topic be?</div>
        <div>
          <strong>0.1:</strong> Allows fuzzy themes ('misc tech stuff').
        </div>
        <div>
          <strong>0.7:</strong> Only distinct topics ('Python vs Java
          tutorials').
        </div>
      </div>
    ),
  };

  const handleAddKeyword = () => {
    if (keywordInput.trim()) {
      setKeywords((prevState) => [...prevState, keywordInput.trim()]);
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
        if (urlToAdd.includes("grok.com")) {
          toast({
            title: "Warning",
            description:
              "Grok.com is protected by Cloudflare and may not be scrapeable.",
          });
        }
        setUrls((prevState) => [...prevState, urlToAdd]);
        setUrlInput("");
      } catch (e) {
        toast({
          variant: "destructive",
          title: "Invalid URL",
          description: "Please enter a valid URL (e.g., https://example.com).",
        });
      }
    }
  };

  const handleRemoveUrl = (index: number) => {
    setUrls(urls.filter((_, i) => i !== index));
  };

  const handleSaveSettings = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
      setShowSavedModal(true);
    }, 1000);
  };

  const handleBuildCampaign = async () => {
    console.log("keywords", keywords);
    console.log("urls", urls);
    if (keywords.length === 0 && urls.length === 0) {
      alert("Enter either url or keyword")
      return
    }

    setIsBuilding(true);
    try {
      const keywordArray = keywords;

      const payload: AnalyzeTrendsInput = {
        campaign_name: name.trim(),
        campaign_id: campaign.id || `campaign-${Date.now()}`,
        urls: urls,
        query: query.trim(),
        description: description,
        keywords: keywordArray,
        type: type,
        depth: extractionSettings.webScrapingDepth,
        max_pages: extractionSettings.maxPages,
        batch_size: extractionSettings.batchSize,
        include_links: extractionSettings.includeLinks,
        stem: preprocessingSettings.stemming,
        lemmatize: preprocessingSettings.lemmatization,
        remove_stopwords_toggle: preprocessingSettings.removeStopwords,
        extract_persons: entitySettings.extractPersons,
        extract_organizations: entitySettings.extractOrganizations,
        extract_locations: entitySettings.extractLocations,
        extract_dates: entitySettings.extractDates,
        topic_tool: modelingSettings.algorithm || "llm",
        num_topics: modelingSettings.numTopics,
        iterations: modelingSettings.iterations,
        pass_threshold: modelingSettings.passThreshold,
      };

      setShowCampaignBuildingMessage("The campaign is being built; it will take a while.In the meantime, you can continue with the other tasks.")

      let response;
      if (trendingKeyword.trim()) {
        const Trendingpayload = {
          trendingKeyword,
          campaign_id: campaign.id || `campaign-${Date.now()}`,
          campaign_name: name.trim(),
          description: query,
        };
        response = await getTrendingContent(Trendingpayload);
      } else {
        response = await analyzeTrends(payload);
      }

      if (response.status === "success") {
        const campaignDescription =
          Array.isArray(response.posts) &&
            response.posts.length > 0 &&
            response.posts[0].text
            ? response.posts[0].text
            : description.trim();

        const normalizeTopics = (topics?: string[]): string[] => {
          if (!topics || !Array.isArray(topics)) return [];
          return topics
            .flatMap((t) =>
              t.includes(",") ? t.split(",").map((s) => s.trim()) : t.trim()
            )
            .filter(Boolean);
        };

        const campaignTopics =
          Array.isArray(response.posts) &&
            response.posts.length > 0 &&
            response.posts[0].topics &&
            Array.isArray(response.posts[0].topics)
            ? normalizeTopics(response.posts[0].topics)
              .map((t) => t.trim().charAt(0).toUpperCase() + t.slice(1))
              .filter((t) => !["non", "com"].includes(t.toLowerCase()))
            : response.topics &&
              Array.isArray(response.topics) &&
              response.topics.length > 0
              ? normalizeTopics(response.topics).map(
                (t) => t.charAt(0).toUpperCase() + t.slice(1)
              )
              : type === "keyword"
                ? keywords
                : type === "trending"
                  ? campaign.trendingTopics || []
                  : [];

        const newCampaign: Campaign = {
          id: campaign.id || `campaign-${Date.now()}`,
          name: name.trim(),
          description: campaignDescription,
          type,
          keywords: type === "keyword" ? keywords : undefined,
          urls: type === "url" ? urls : undefined,
          trendingTopics:
            type === "trending" ? campaign.trendingTopics || [] : undefined,
          createdAt: campaign.createdAt || new Date(),
          updatedAt: new Date(),
          topics: campaignTopics,
          extractionSettings,
          preprocessingSettings,
          entitySettings,
          modelingSettings,
        };

        setSettings((prevCampaigns) => {
          let updatedCampaigns;
          if (campaign.id) {
            updatedCampaigns = prevCampaigns.map((c) =>
              c.id === campaign.id ? newCampaign : c
            );
          } else {
            updatedCampaigns = [...prevCampaigns, newCampaign];
          }
          // Sort campaigns by createdAt in descending order (newest first)
          updatedCampaigns.sort(
            (a: Campaign, b: Campaign) =>
              new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          );
          return updatedCampaigns;
        });

        const updatedCampaign: Omit<
          Campaign,
          "id" | "createdAt" | "updatedAt"
        > = {
          name: name.trim(),
          description: campaignDescription,
          type,
          keywords: type === "keyword" ? keywords : undefined,
          urls: type === "url" ? urls : undefined,
          trendingTopics:
            type === "trending" ? campaign.trendingTopics || [] : undefined,
          topics: campaignTopics,
          extractionSettings,
          preprocessingSettings,
          entitySettings,
          modelingSettings,
        };

        onSave(updatedCampaign);

        // Fetch updated campaigns from API
        const apiResponse = await getAllCampaigns();
        if (apiResponse.status === "success") {
          // Sort campaigns by createdAt in descending order (newest first)
          const sortedCampaigns = (apiResponse.message.campaigns || []).sort(
            (a: Campaign, b: Campaign) =>
              new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          );
          setSettings(sortedCampaigns);
        } else {
          console.error(
            "Failed to fetch updated campaigns:",
            apiResponse.message
          );
        }

        toast({
          title: "Campaign Built Successfully",
          description:
            "Your campaign base has been created with the analyzed trends.",
        });

        onCancel();
      } else {
        console.error("API Error Details:", JSON.stringify(response, null, 2));
        throw new Error(response.message || "Failed to analyze trends");
      }
    } catch (error) {
      console.error("Error building campaign:", error);
      toast({
        variant: "destructive",
        title: "Error Building Campaign",
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred.",
      });
    } finally {
      setShowCampaignBuildingMessage("")
      setIsBuilding(false);
    }
  };

  // Render a loading state until defaults are set
  if (!isMounted) {
    return <div>Loading settings...</div>;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="campaign-name">Campaign Name</Label>
            <Input
              id="campaign-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter campaign name"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="campaign-description">Description</Label>
            <Textarea
              id="campaign-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter campaign description"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="campaign-description">Query</Label>
            <Textarea
              id="campaign-description"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter campaign description"
            />
          </div>

          <Tabs
            value={type}
            onValueChange={(value) =>
              setType(value as "keyword" | "url" | "trending")
            }
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
            </TabsList>

            <TabsContent value="keyword" className="space-y-4">
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
                  disabled={type === "url"}
                />
                <Button onClick={handleAddKeyword}>Add</Button>
              </div>

              {keywords.length > 0 && (
                <div className="border rounded-md p-4">
                  <Label className="mb-2 block">Keywords/Phrases:</Label>
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
                          <span className="sr-only">Remove</span>
                          <span aria-hidden="true">×</span>
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="url" className="space-y-4">
              <div className="flex space-x-2">
                <Input
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="Enter URL (e.g., https://example.com)"
                  pattern="https?://.+"
                  title="Please enter a valid URL starting with http:// or https://"
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
                    {urls.map((url, index) => (
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
                          <span className="sr-only">Remove</span>
                          <span aria-hidden="true">×</span>
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Advanced Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="extraction">
            <TabsList className="w-full mb-4">
              <TabsTrigger value="extraction" className="flex-1">
                <Database className="w-4 h-4 mr-2" />
                Information Extraction
              </TabsTrigger>
              <TabsTrigger value="preprocessing" className="flex-1">
                <Code className="w-4 h-4 mr-2" />
                Preprocessing
              </TabsTrigger>
              <TabsTrigger value="entity" className="flex-1">
                <Network className="w-4 h-4 mr-2" />
                Entity Recognition
              </TabsTrigger>
              <TabsTrigger value="modeling" className="flex-1">
                <Brain className="w-4 h-4 mr-2" />
                Topic Modeling
              </TabsTrigger>
            </TabsList>

            <TabsContent value="extraction" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <Label htmlFor="web-scraping-depth" className="mr-2">
                        Web Scraping Depth
                      </Label>
                      <button
                        type="button"
                        onClick={() =>
                          openInfoModal(
                            "Web Scraping Depth",
                            parameterDescriptions.webScrapingDepth
                          )
                        }
                        className="text-gray-500 hover:text-gray-700 focus:outline-none"
                      >
                        <InfoIcon className="h-4 w-4" />
                      </button>
                    </div>
                    <span className="text-sm text-gray-500">
                      {extractionSettings.webScrapingDepth}
                    </span>
                  </div>
                  <Slider
                    id="web-scraping-depth"
                    min={1}
                    max={5}
                    step={1}
                    value={[extractionSettings.webScrapingDepth]}
                    onValueChange={(value) =>
                      setExtractionSettings({
                        ...extractionSettings,
                        webScrapingDepth: value[0],
                      })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <Label htmlFor="max-pages" className="mr-2">
                        Maximum Pages
                      </Label>
                      <button
                        type="button"
                        onClick={() =>
                          openInfoModal(
                            "Maximum Pages",
                            parameterDescriptions.maxPages
                          )
                        }
                        className="text-gray-500 hover:text-gray-700 focus:outline-none"
                      >
                        <InfoIcon className="h-4 w-4" />
                      </button>
                    </div>
                    <span className="text-sm text-gray-500">
                      {extractionSettings.maxPages}
                    </span>
                  </div>
                  <Slider
                    id="max-pages"
                    min={1}
                    max={20}
                    step={1}
                    value={[extractionSettings.maxPages]}
                    onValueChange={(value) =>
                      setExtractionSettings({
                        ...extractionSettings,
                        maxPages: value[0],
                      })
                    }
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Label htmlFor="batch-size" className="mr-2">
                      Batch Size
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Batch Size",
                          parameterDescriptions.batchSize
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <span className="text-sm text-gray-500">
                    {extractionSettings.batchSize}
                  </span>
                </div>
                <Slider
                  id="batch-size"
                  min={5}
                  max={100}
                  step={5}
                  value={[extractionSettings.batchSize]}
                  onValueChange={(value) =>
                    setExtractionSettings({
                      ...extractionSettings,
                      batchSize: value[0],
                    })
                  }
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="include-images" className="mr-2">
                      Include Images
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Include Images",
                          parameterDescriptions.includeImages
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="include-images"
                    checked={extractionSettings.includeImages}
                    defaultChecked={false}
                    onCheckedChange={(checked) =>
                      setExtractionSettings({
                        ...extractionSettings,
                        includeImages: checked,
                      })
                    }
                  />
                </div>

                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="include-links" className="mr-2">
                      Include Links
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Include Links",
                          parameterDescriptions.includeLinks
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="include-links"
                    checked={extractionSettings.includeLinks}
                    defaultChecked={false}
                    onCheckedChange={(checked) =>
                      setExtractionSettings({
                        ...extractionSettings,
                        includeLinks: checked,
                      })
                    }
                  />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="preprocessing" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="remove-stopwords" className="mr-2">
                      Remove Stopwords
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Remove Stopwords",
                          parameterDescriptions.removeStopwords
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="remove-stopwords"
                    checked={preprocessingSettings.removeStopwords}
                    defaultChecked={false}
                    onCheckedChange={(checked) =>
                      setPreprocessingSettings({
                        ...preprocessingSettings,
                        removeStopwords: checked,
                      })
                    }
                  />
                </div>

                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="stemming" className="mr-2">
                      Apply Stemming
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Apply Stemming",
                          parameterDescriptions.stemming
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="stemming"
                    checked={preprocessingSettings.stemming}
                    defaultChecked={false}
                    onCheckedChange={(checked) =>
                      setPreprocessingSettings({
                        ...preprocessingSettings,
                        stemming: checked,
                      })
                    }
                  />
                </div>

                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="lemmatization" className="mr-2">
                      Apply Lemmatization
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Apply Lemmatization",
                          parameterDescriptions.lemmatization
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="lemmatization"
                    checked={preprocessingSettings.lemmatization}
                    defaultChecked={false}
                    onCheckedChange={(checked) =>
                      setPreprocessingSettings({
                        ...preprocessingSettings,
                        lemmatization: checked,
                      })
                    }
                  />
                </div>

                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="case-sensitive" className="mr-2">
                      Case Sensitive
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Case Sensitive",
                          parameterDescriptions.caseSensitive
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="case-sensitive"
                    checked={preprocessingSettings.caseSensitive}
                    defaultChecked={false}
                    onCheckedChange={(checked) =>
                      setPreprocessingSettings({
                        ...preprocessingSettings,
                        caseSensitive: checked,
                      })
                    }
                  />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="entity" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="extract-persons" className="mr-2">
                      Extract Persons
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Extract Persons",
                          parameterDescriptions.extractPersons
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="extract-persons"
                    checked={entitySettings.extractPersons}
                    defaultChecked={false}
                    onCheckedChange={(checked) =>
                      setEntitySettings({
                        ...entitySettings,
                        extractPersons: checked,
                      })
                    }
                  />
                </div>

                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="extract-organizations" className="mr-2">
                      Extract Organizations
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Extract Organizations",
                          parameterDescriptions.extractOrganizations
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="extract-organizations"
                    checked={entitySettings.extractOrganizations}
                    defaultChecked={false}
                    onCheckedChange={(checked) =>
                      setEntitySettings({
                        ...entitySettings,
                        extractOrganizations: checked,
                      })
                    }
                  />
                </div>

                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="extract-locations" className="mr-2">
                      Extract Locations
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Extract Locations",
                          parameterDescriptions.extractLocations
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="extract-locations"
                    checked={entitySettings.extractLocations}
                    defaultChecked={false}
                    onCheckedChange={(checked) =>
                      setEntitySettings({
                        ...entitySettings,
                        extractLocations: checked,
                      })
                    }
                  />
                </div>

                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="extract-dates" className="mr-2">
                      Extract Dates
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Extract Dates",
                          parameterDescriptions.extractDates
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="extract-dates"
                    checked={entitySettings.extractDates}
                    defaultChecked={false}
                    onCheckedChange={(checked) =>
                      setEntitySettings({
                        ...entitySettings,
                        extractDates: checked,
                      })
                    }
                  />
                </div>
              </div>

              <div className="space-y-2 pt-2">
                <div className="flex justify-between">
                  <div className="flex items-center">
                    <Label htmlFor="confidence-threshold" className="mr-2">
                      Confidence Threshold
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Confidence Threshold",
                          parameterDescriptions.confidenceThreshold
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <span className="text-sm text-gray-500">
                    {entitySettings.confidenceThreshold.toFixed(1)}
                  </span>
                </div>
                <Slider
                  id="confidence-threshold"
                  min={0.1}
                  max={0.9}
                  step={0.1}
                  value={[entitySettings.confidenceThreshold]}
                  onValueChange={(value) =>
                    setEntitySettings({
                      ...entitySettings,
                      confidenceThreshold: value[0],
                    })
                  }
                />
              </div>
            </TabsContent>

            <TabsContent value="modeling" className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center">
                  <Label htmlFor="algorithm" className="mr-2">
                    Topic Modeling Algorithm
                  </Label>
                  <button
                    type="button"
                    onClick={() =>
                      openInfoModal(
                        "Topic Modeling Algorithm",
                        parameterDescriptions.algorithm
                      )
                    }
                    className="text-gray-500 hover:text-gray-700 focus:outline-none"
                  >
                    <InfoIcon className="h-4 w-4" />
                  </button>
                </div>
                <Select
                  value={modelingSettings.algorithm}
                  onValueChange={(value) =>
                    setModelingSettings({
                      ...modelingSettings,
                      algorithm: value,
                    })
                  }
                >
                  <SelectTrigger id="algorithm">
                    <SelectValue placeholder="Select algorithm" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="llm">
                      Large Language Model (LLM)
                    </SelectItem>
                    <SelectItem value="lda">
                      Latent Dirichlet Allocation (LDA)
                    </SelectItem>
                    <SelectItem value="bertopic">BERTopic</SelectItem>
                    <SelectItem value="nmf">
                      Non-negative Matrix Factorization (NMF)
                    </SelectItem>
                    <SelectItem value="lsa">
                      Latent Semantic Analysis (LSA)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <div className="flex items-center">
                      <Label htmlFor="num-topics" className="mr-2">
                        Number of Topics
                      </Label>
                      <button
                        type="button"
                        onClick={() =>
                          openInfoModal(
                            "Number of Topics",
                            parameterDescriptions.numTopics
                          )
                        }
                        className="text-gray-500 hover:text-gray-700 focus:outline-none"
                      >
                        <InfoIcon className="h-4 w-4" />
                      </button>
                    </div>
                    <span className="text-sm text-gray-500">
                      {modelingSettings.numTopics}
                    </span>
                  </div>
                  <Slider
                    id="num-topics"
                    min={2}
                    max={20}
                    step={1}
                    value={[modelingSettings.numTopics]}
                    onValueChange={(value) =>
                      setModelingSettings({
                        ...modelingSettings,
                        numTopics: value[0],
                      })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between">
                    <div className="flex items-center">
                      <Label htmlFor="iterations" className="mr-2">
                        Iterations
                      </Label>
                      <button
                        type="button"
                        onClick={() =>
                          openInfoModal(
                            "Iterations",
                            parameterDescriptions.iterations
                          )
                        }
                        className="text-gray-500 hover:text-gray-700 focus:outline-none"
                      >
                        <InfoIcon className="h-4 w-4" />
                      </button>
                    </div>
                    <span className="text-sm text-gray-500">
                      {modelingSettings.iterations}
                    </span>
                  </div>
                  <Slider
                    id="iterations"
                    min={50}
                    max={500}
                    step={50}
                    value={[modelingSettings.iterations]}
                    onValueChange={(value) =>
                      setModelingSettings({
                        ...modelingSettings,
                        iterations: value[0],
                      })
                    }
                  />
                </div>
              </div>

              <div className="space-y-2 pt-2">
                <div className="flex justify-between">
                  <div className="flex items-center">
                    <Label htmlFor="pass-threshold" className="mr-2">
                      Pass Threshold
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Pass Threshold",
                          parameterDescriptions.passThreshold
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <span className="text-sm text-gray-500">
                    {modelingSettings.passThreshold.toFixed(1)}
                  </span>
                </div>
                <Slider
                  id="pass-threshold"
                  min={0.1}
                  max={0.9}
                  step={0.1}
                  value={[modelingSettings.passThreshold]}
                  onValueChange={(value) =>
                    setModelingSettings({
                      ...modelingSettings,
                      passThreshold: value[0],
                    })
                  }
                />
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
        <CardFooter className="flex flex-col space-y-2">
          <div className="flex justify-end space-x-4 w-full">
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveSettings}
              className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Settings"
              )}
            </Button>
            <Button
              onClick={handleBuildCampaign}
              className="bg-green-600 text-white hover:bg-green-700"
              disabled={isBuilding}
            >
              {isBuilding ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Building...
                </>
              ) : (
                "Build Campaign Base"
              )}
            </Button>
          </div>
          <div className="w-full flex justify-end">
            <div className="text-right">
              <p className="text-xs text-gray-500 mb-1">
                Building a base starts your plan.
              </p>
              {showCampaignBuildingMessage && (
                <p className="text-sm text-blue-600 animate-pulse">
                  The campaign is being built; it will take a while. In the meantime, you can continue with the other tasks.
                </p>
              )}
            </div>
          </div>

        </CardFooter>
      </Card>

      <Dialog open={showSavedModal} onOpenChange={setShowSavedModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              Settings Saved
            </DialogTitle>
            <DialogDescription className="text-center pt-2">
              Your settings have been saved. Please build your Campaign Base to
              continue.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-center mt-4">
            <Button
              onClick={() => setShowSavedModal(false)}
              className="bg-green-600 text-white hover:bg-green-700"
            >
              OK
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <ParameterInfoModal
        isOpen={infoModal.isOpen}
        onClose={closeInfoModal}
        title={infoModal.title}
        description={infoModal.description}
      />
    </div>
  );
}
