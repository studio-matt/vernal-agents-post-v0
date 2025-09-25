"use client";

import { useState, useRef, useEffect } from "react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Plus, Trash2, Edit, ExternalLink, Key, Twitter } from "lucide-react";
import { ErrorDialog } from "./ErrorDialog";
import { CampaignSettings } from "./CampaignSettings";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  deleteCampaignsById,
  getAllCampaigns,
  getTrendingContent,
} from "./Service";
import { toast } from "sonner";

export interface Campaign {
  id: string;
  name: string;
  description: string;
  type: "keyword" | "url" | "trending";
  keywords?: string[];
  urls?: string[];
  trendingTopics?: string[];
  topics?: string[];
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

interface ContentPlannerCampaignProps {
  campaigns: Campaign[];
  onAddCampaign: (
    campaign: Omit<Campaign, "id" | "createdAt" | "updatedAt">
  ) => void;
  onEditCampaign: (id: string, campaign: Partial<Campaign>) => void;
  onDeleteCampaign: (id: string) => void;
}

export function ContentPlannerCampaign({
  campaigns,
  onAddCampaign,
  onEditCampaign,
  onDeleteCampaign,
}: ContentPlannerCampaignProps) {
  const router = useRouter();
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [campaignName, setCampaignName] = useState("");
  const [campaignDescription, setCampaignDescription] = useState("");
  const [query, setQuery] = useState("");
  const [campaignType, setCampaignType] = useState<
    "keyword" | "url" | "trending"
  >("keyword");
  const [keywordInput, setKeywordInput] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [settings, setSettings] = useState<Campaign[]>(campaigns);
  const [urlInput, setUrlInput] = useState("");
  const [urls, setUrls] = useState<string[]>([]);
  const [error, setError] = useState<{ isOpen: boolean; message: string }>({
    isOpen: false,
    message: "",
  });
  const [isSettingsMode, setIsSettingsMode] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [extractionSettings, setExtractionSettings] = useState({
    webScrapingDepth: 2,
    includeImages: true,
    includeLinks: true,
    maxPages: 10,
    batchSize: 10,
  });

  const [preprocessingSettings, setPreprocessingSettings] = useState({
    removeStopwords: true,
    stemming: true,
    lemmatization: true,
    caseSensitive: false,
  });

  const [entitySettings, setEntitySettings] = useState({
    extractPersons: true,
    extractOrganizations: true,
    extractLocations: true,
    extractDates: true,
    confidenceThreshold: 0.7,
  });

  const [modelingSettings, setModelingSettings] = useState({
    algorithm: "lda",
    numTopics: 5,
    iterations: 100,
    passThreshold: 0.5,
  });

  const [isMergeMode, setIsMergeMode] = useState(false);
  const [selectedCampaigns, setSelectedCampaigns] = useState<string[]>([]);
  const [isMergeModalOpen, setIsMergeModalOpen] = useState(false);
  const [trendingKeyword, setTrendingKeyword] = useState("");
  const [trendingTopics, setTrendingTopics] = useState<string[]>([]);
  const [topics, setTTopics] = useState<string[]>([]);
  const formRef = useRef<HTMLDivElement>(null);
  const campaignsListRef = useRef<HTMLDivElement>(null); // Ref for the campaigns list container
  const [campaignDisplay, setCampaignDisplay] = useState<Campaign | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showErrorDialog, setShowErrorDialog] = useState(false);

  // Sync settings with campaigns prop whenever campaigns change
  useEffect(() => {
    setSettings(campaigns);
  }, [campaigns]);

  // Fetch campaigns on mount and sort them
  useEffect(() => {
    const getAllCampaign = async () => {
      setIsLoading(true);
      try {
        const response = await getAllCampaigns();
        if (response.status === "success") {
          const sortedCampaigns = (response.message.campaigns || []).sort(
            (a: Campaign, b: Campaign) =>
              new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          );
          setSettings(sortedCampaigns);
        } else {
          console.error(
            "API Error Details:",
            JSON.stringify(response, null, 2)
          );
          throw new Error(response.message || "Failed to analyze trends");
        }
      } catch (error) {
        console.error("Error building campaign:", error);
        setErrorMessage("Error building campaign.");
        setShowErrorDialog(true); // Show dialog
      } finally {
        setIsLoading(false);
      }
    };
    getAllCampaign();
  }, []);

  // Scroll to top of campaigns list whenever settings change
  useEffect(() => {
    if (campaignsListRef.current && !isCreating) {
      campaignsListRef.current.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [settings, isCreating]);

  const resetForm = () => {
    setCampaignName("");
    setCampaignDescription("");
    setCampaignType("keyword");
    setKeywordInput("");
    setKeywords([]);
    setUrlInput("");
    setUrls([]);
    setTrendingKeyword("");
    setTrendingTopics([]);
    setTTopics([]);
    setIsCreating(false);
    setEditingId(null);
    setIsSettingsMode(false);
    setExtractionSettings({
      webScrapingDepth: 2,
      includeImages: true,
      includeLinks: true,
      maxPages: 10,
      batchSize: 10,
    });
    setPreprocessingSettings({
      removeStopwords: true,
      stemming: true,
      lemmatization: true,
      caseSensitive: false,
    });
    setEntitySettings({
      extractPersons: true,
      extractOrganizations: true,
      extractLocations: true,
      extractDates: true,
      confidenceThreshold: 0.7,
    });
    setModelingSettings({
      algorithm: "lda",
      numTopics: 5,
      iterations: 100,
      passThreshold: 0.5,
    });
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
        setUrls((prevState) => [...prevState, urlToAdd]);
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

  const handleSubmit = () => {
    if (!campaignName.trim()) {
      setError({
        isOpen: true,
        message: "Please enter a campaign name",
      });
      return;
    }
    if (campaignType === "keyword" && keywords.length === 0) {
      setError({
        isOpen: true,
        message: "Please add at least one keyword or phrase",
      });
      return;
    }
    if (campaignType === "url" && urls.length === 0) {
      setError({
        isOpen: true,
        message: "Please add at least one URL",
      });
      return;
    }
    if (campaignType === "trending" && trendingTopics.length === 0) {
      setError({
        isOpen: true,
        message: "Please add at least one trending topic",
      });
      return;
    }
    const campaignData = {
      name: campaignName,
      description: campaignDescription,
      type: campaignType,
      keywords: campaignType === "keyword" ? keywords : undefined,
      urls: campaignType === "url" ? urls : undefined,
      trendingTopics: campaignType === "trending" ? trendingTopics : undefined,
      topics,
      extractionSettings,
      preprocessingSettings,
      entitySettings,
      modelingSettings,
    };
    if (editingId) {
      onEditCampaign(editingId, campaignData);
    } else {
      onAddCampaign(campaignData);
    }
    resetForm();
  };

  const handleEditCampaign = (campaign: Campaign) => {
    setEditingId(campaign.id);
    setCampaignName(campaign.name);
    setCampaignDescription(campaign.description);
    setCampaignType(campaign.type);
    setKeywords(campaign.keywords || []);
    setUrls(campaign.urls || []);
    setTrendingTopics(campaign.trendingTopics || []);
    setTTopics(campaign.topics || []);
    if (campaign.extractionSettings) {
      setExtractionSettings(campaign.extractionSettings);
    }
    if (campaign.preprocessingSettings) {
      setPreprocessingSettings(campaign.preprocessingSettings);
    }
    if (campaign.entitySettings) {
      setEntitySettings(campaign.entitySettings);
    }
    if (campaign.modelingSettings) {
      setModelingSettings(campaign.modelingSettings);
    }
    setIsSettingsMode(true);
    setIsCreating(true);
    setTimeout(() => {
      if (formRef.current) {
        formRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 100);
  };

  const closeErrorDialog = () => {
    setError({ isOpen: false, message: "" });
  };

  const handleCreateCampaign = () => {
    setIsCreating(true);
    setTimeout(() => {
      if (formRef.current) {
        formRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 100);
  };

  const handleCampaignSelection = (campaignId: string) => {
    setSelectedCampaigns((prev) =>
      prev.includes(campaignId)
        ? prev.filter((id) => id !== campaignId)
        : [...prev, campaignId]
    );
  };

  const handleMergeCampaigns = () => {
    if (selectedCampaigns.length < 2) {
      setError({
        isOpen: true,
        message: "Please select at least two campaigns to merge",
      });
      return;
    }
    setIsMergeModalOpen(true);
  };

  const confirmMergeCampaigns = () => {
    const selectedCampaignData = settings?.filter((campaign) =>
      selectedCampaigns.includes(campaign.id)
    );
    const mergedCampaignNames = selectedCampaignData
      .map((c) => c.name)
      .join(", ");
    const mergedCampaign: Omit<Campaign, "id" | "createdAt" | "updatedAt"> = {
      name: "Merged Research",
      description: `This campaign is a merge of the following campaigns: ${mergedCampaignNames}`,
      type: "keyword",
      keywords: Array.from(
        new Set(
          selectedCampaignData
            .filter((c) => c.type === "keyword" && c.keywords)
            .flatMap((c) => c.keywords || [])
        )
      ),
      urls: Array.from(
        new Set(
          selectedCampaignData
            .filter((c) => c.type === "url" && c.urls)
            .flatMap((c) => c.urls || [])
        )
      ),
      trendingTopics: Array.from(
        new Set(
          selectedCampaignData
            .filter((c) => c.type === "trending" && c.trendingTopics)
            .flatMap((c) => c.trendingTopics || [])
        )
      ),
      topics: Array.from(
        new Set(
          selectedCampaignData
            .filter((c) => c.topics)
            .flatMap((c) => c.topics || [])
        )
      ),
      extractionSettings: selectedCampaignData[0].extractionSettings,
      preprocessingSettings: selectedCampaignData[0].preprocessingSettings,
      entitySettings: selectedCampaignData[0].entitySettings,
      modelingSettings: selectedCampaignData[0].modelingSettings,
    };
    onAddCampaign(mergedCampaign);
    setIsMergeModalOpen(false);
    setIsMergeMode(false);
    setSelectedCampaigns([]);
  };

  const cancelMerge = () => {
    setIsMergeMode(false);
    setSelectedCampaigns([]);
  };

  const deleteCampaign = async (id: string) => {
    setIsLoading(true);
    try {
      const response = await deleteCampaignsById(id);

      if (response.status === "success") {
        setSettings((prevCampaigns) => {
          const updatedCampaigns = prevCampaigns.filter(
            (campaign) => campaign.id !== id
          );
          updatedCampaigns.sort(
            (a: Campaign, b: Campaign) =>
              new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          );
          return updatedCampaigns;
        });
        onDeleteCampaign(id);
      } else {
        setError({
          isOpen: true,
          message: "Error in deleting: Campaign couldn't be deleted",
        });
      }
    } catch (error) {
      console.error("Error deleting campaign:", error);
      setError({
        isOpen: true,
        message: "Unexpected error occurred while deleting campaign.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#7A99A8]">
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <div className="flex items-center space-x-4">
            <h1 className="text-4xl font-extrabold text-white">
              Loading campaigns...
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

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-semibold">Campaigns</h2>
        {!isCreating && (
          <div className="flex space-x-2">
            {isMergeMode ? (
              <div className="flex space-x-2">
                <Button onClick={cancelMerge} variant="outline">
                  Cancel
                </Button>
                <Button
                  onClick={handleMergeCampaigns}
                  className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                  disabled={selectedCampaigns.length < 2}
                >
                  Merge Selected ({selectedCampaigns.length})
                </Button>
              </div>
            ) : (
              <>
                <Button onClick={() => setIsMergeMode(true)} variant="outline">
                  Merge Research
                </Button>
                <Button
                  onClick={handleCreateCampaign}
                  className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create Campaign
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {isCreating && (
        <div ref={formRef}>
          {isSettingsMode ? (
            <CampaignSettings
              setSettings={setSettings}
              trendingKeyword={trendingKeyword}
              campaign={{
                id: editingId || "",
                name: campaignName,
                description: campaignDescription,
                query: query,
                type: campaignType,
                keywords: keywords,
                urls: urls,
                trendingTopics: trendingTopics,
                topics: topics,
                createdAt: new Date(),
                updatedAt: new Date(),
                extractionSettings: extractionSettings,
                preprocessingSettings: preprocessingSettings,
                entitySettings: entitySettings,
                modelingSettings: modelingSettings,
              }}
              onSave={(updatedCampaign) => {
                if (editingId) {
                  onEditCampaign(editingId, updatedCampaign);
                } else {
                  onAddCampaign(updatedCampaign);
                }
                resetForm();
                setIsSettingsMode(false);
              }}
              onCancel={() => {
                resetForm();
                setIsSettingsMode(false);
              }}
            />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>
                  {editingId ? "Edit Campaign" : "Create New Campaign"}
                </CardTitle>
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
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Enter the query you want to scrape using LLM"
                  />
                </div>
                <Tabs
                  value={campaignType}
                  onValueChange={(value) =>
                    setCampaignType(value as "keyword" | "url" | "trending")
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
                    <TabsTrigger value="trending" className="flex-1">
                      <Twitter className="w-4 h-4 mr-2" />
                      Trending on X
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
                                <Trash2 className="w-3 h-3" />
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
                                className="text-blue-600 hover:underline truncate break-words"
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
                  <TabsContent value="trending" className="space-y-4">
                    <div className="space-y-4">
                      <div className="flex space-x-2">
                        <Input
                          value={trendingKeyword}
                          onChange={(e) => setTrendingKeyword(e.target.value)}
                          placeholder="Enter keyword to find trending topics"
                        />
                      </div>
                      {trendingTopics.length > 0 && (
                        <div className="border rounded-md p-4">
                          <Label className="mb-2 block">Trending Topics:</Label>
                          <div className="flex flex-wrap gap-2">
                            {trendingTopics.map((topic: any, index) => (
                              <div
                                key={index}
                                className="flex items-center bg-secondary text-secondary-foreground px-3 py-1 rounded-full"
                              >
                                <span>{topic.text}</span>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-auto p-1 ml-1"
                                  onClick={() => {
                                    setTrendingTopics(
                                      trendingTopics.filter(
                                        (_, i) => i !== index
                                      )
                                    );
                                  }}
                                >
                                  <Trash2 className="w-3 h-3" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
                <div className="mt-6">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setIsSettingsMode(true)}
                    className="w-full"
                  >
                    Configure Advanced Settings
                  </Button>
                  <p className="text-sm text-gray-500 mt-2 text-center">
                    Configure extraction, preprocessing, entity recognition, and
                    topic modeling settings
                  </p>
                </div>
              </CardContent>
              <div className="text-center mt-2 mb-4">
                <span className="text-xs text-gray-500">
                  Building a Base starts your plan
                </span>
              </div>
            </Card>
          )}
        </div>
      )}

      <div ref={campaignsListRef} className="space-y-4">
        {settings?.map((campaign) => (
          <Card key={campaign.id}>
            <CardContent className="p-6">
              <div className="flex justify-between items-start">
                <div className="flex items-start">
                  {isMergeMode && (
                    <div className="mr-3 mt-1">
                      <input
                        type="checkbox"
                        id={`select-${campaign.id}`}
                        checked={selectedCampaigns.includes(campaign.id)}
                        onChange={() => handleCampaignSelection(campaign.id)}
                        className="h-5 w-5 rounded border-gray-300 text-[#3d545f] focus:ring-[#3d545f]"
                      />
                    </div>
                  )}
                  <div>
                    <div className="flex items-center space-x-2">
                      <h3 className="text-xl font-semibold">{campaign.name}</h3>
                      <span className="bg-secondary text-secondary-foreground text-xs px-2 py-1 rounded-full">
                        {campaign.type === "keyword"
                          ? "Keywords"
                          : campaign.type === "url"
                            ? "URLs"
                            : "Trending"}
                      </span>
                    </div>
                    <p className="text-gray-500 mt-1">{campaign.description}</p>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <Link href={`/dashboard/campaigns/edit/${campaign.id}`}>
                    <Button variant="outline" size="sm">
                      <Edit className="w-4 h-4 mr-2" />
                      Edit
                    </Button>
                  </Link>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => deleteCampaign(campaign.id)}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </Button>
                </div>
              </div>
              <div className="mt-4 space-y-4">
                {campaign.type === "keyword" &&
                  campaign.keywords &&
                  campaign.keywords.length > 0 && (
                    <div>
                      <Label className="mb-2 block">Keywords/Phrases:</Label>
                      <div className="flex flex-wrap gap-2 keywodd">
                        {campaign.keywords.map((keyword, index) => (
                          <div
                            key={index}
                            className="bg-secondary text-secondary-foreground px-3 py-1 rounded-full"
                          >
                            {keyword}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                {campaign.type === "url" &&
                  campaign.keywords &&
                  campaign.keywords.length > 0 && (
                    <div>
                      <Label className="mb-2 block">Keyword:</Label>
                      <div className="space-y-2 urlll">
                        {campaign.keywords.map((keyword, index) => (
                          <div
                            key={index}
                            className="bg-secondary text-secondary-foreground p-2 rounded"
                          >
                            {keyword}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                {campaign.type === "url" &&
                  campaign.urls &&
                  campaign.urls.length > 0 && (
                    <div>
                      <Label className="mb-2 block">URLs:</Label>
                      <div className="space-y-2 urlll">
                        {campaign.urls.map((url, index) => (
                          <div
                            key={index}
                            className="bg-secondary text-secondary-foreground p-2 rounded"
                          >
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline break-words"
                            >
                              {url}
                            </a>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                {campaign.type === "trending" &&
                  campaign.trendingTopics &&
                  campaign.trendingTopics.length > 0 && (
                    <div>
                      <Label className="mb-2 block">Trending Topics:</Label>
                      <div className="flex flex-wrap gap-2">
                        {campaign.trendingTopics.map((topic, index) => (
                          <div
                            key={index}
                            className="bg-secondary text-secondary-foreground px-3 py-1 rounded-full"
                          >
                            {topic}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
              </div>
            </CardContent>
          </Card>
        ))}
        {!isCreating && !isMergeMode && (
          <Card>
            <CardContent className="p-6 flex flex-col items-center justify-center text-center">
              <button
                onClick={handleCreateCampaign}
                className="p-6 rounded-full bg-secondary mb-4 hover:bg-secondary/80 transition-colors cursor-pointer"
              >
                <Plus className="w-10 h-10" />
              </button>
              <h3 className="text-xl font-semibold">Add New Campaign</h3>
              <p className="text-gray-500 mt-1 mb-4">
                Create a new campaign to analyze content and generate insights
              </p>
              <Button
                onClick={handleCreateCampaign}
                className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
              >
                Create Campaign
              </Button>
            </CardContent>
          </Card>
        )}
        {isMergeMode && (
          <div className="flex justify-center mt-4">
            <Button
              onClick={handleMergeCampaigns}
              className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 mr-2"
            >
              Merge Selected Campaigns
            </Button>
            <Button variant="outline" onClick={cancelMerge}>
              Cancel Merge
            </Button>
          </div>
        )}
      </div>
      <AlertDialog open={isMergeModalOpen} onOpenChange={setIsMergeModalOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Merge Selected Campaigns</AlertDialogTitle>
            <AlertDialogDescription>
              This will create a new campaign that combines the keywords, URLs,
              and settings from the selected campaigns. Are you sure you want to
              merge {selectedCampaigns.length} campaigns?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setIsMergeModalOpen(false)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={confirmMergeCampaigns}>
              Merge Campaigns
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <ErrorDialog
        isOpen={error.isOpen}
        onClose={closeErrorDialog}
        message={error.message}
      />
    </div>
  );
}
