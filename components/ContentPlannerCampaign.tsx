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
  createCampaign,
} from "./Service";
import { toast } from "sonner";

export interface Campaign {
  id: string;
  name: string;
  description: string;
  query?: string;
  type: "keyword" | "url" | "trending";
  keywords?: string[];
  urls?: string[];
  trendingTopics?: string[];
  topics?: string[];
  persons?: string[];
  organizations?: string[];
  locations?: string[];
  dates?: string[];
  posts?: {
    url?: string;
    title?: string;
    text: string;
    lemmatized_text?: string;
    stemmed_text?: string;
    stopwords_removed_text?: string;
    persons?: string[];
    organizations?: string[];
    locations?: string[];
    dates?: string[];
    topics?: string[];
    entities?: {
      persons?: string[];
      organizations?: string[];
      locations?: string[];
      dates?: string[];
    };
  }[];
  summary?: {
    total_urls_scraped: number;
    total_content_size: string;
    extraction_settings_used: {
      depth: number;
      max_pages: number;
      batch_size: number;
      include_links: boolean;
    };
  };
  createdAt: Date;
  updatedAt: Date;
  status?: "INCOMPLETE" | "PROCESSING" | "READY_TO_ACTIVATE" | "ACTIVE";
  // Progress tracking fields
  progress?: number;
  currentStep?: string;
  progressMessage?: string;
  taskId?: string;
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
  onRefreshCampaigns?: () => void;
}

export function ContentPlannerCampaign({
  campaigns,
  onAddCampaign,
  onEditCampaign,
  onDeleteCampaign,
  onRefreshCampaigns,
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
  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    campaignId: string | null;
    campaignName: string;
  }>({
    isOpen: false,
    campaignId: null,
    campaignName: "",
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
  const [campaignDisplay, setCampaignDisplay] = useState<Campaign | null>(null);
  const [processingStartTimes, setProcessingStartTimes] = useState<Record<string, number>>({});
  const [pollingIntervals, setPollingIntervals] = useState<Record<string, NodeJS.Timeout>>({});

  // Helper function to get elapsed time for processing campaigns
  const getElapsedTime = (campaign: Campaign): string => {
    if (getCampaignStatus(campaign) !== "PROCESSING") return "";
    
    // Use updatedAt if available (for re-processing), otherwise createdAt
    const startTime = processingStartTimes[campaign.id] || 
                     new Date(campaign.updatedAt || campaign.createdAt).getTime();
    const now = Date.now();
    const elapsed = now - startTime;
    const minutes = Math.floor(elapsed / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    
    return `${minutes}m ${seconds}s`;
  };

  // Helper function to get progress percentage
  const getProgressPercentage = (campaign: Campaign): number => {
    if (getCampaignStatus(campaign) !== "PROCESSING") return 0;
    
    // Use real API progress if available, otherwise fall back to time-based
    if (campaign.progress !== undefined) {
      console.log(`[Progress] Using API progress: ${campaign.progress}% for campaign ${campaign.id}`);
      return campaign.progress;
    }
    
    // Fallback to time-based progress
    const startTime = processingStartTimes[campaign.id] || 
                     new Date(campaign.updatedAt || campaign.createdAt).getTime();
    const now = Date.now();
    const elapsed = now - startTime;
    const minutes = elapsed / 60000;
    
    // Progress in meaningful increments over 5 minutes
    let timeBasedProgress = 0;
    if (minutes < 0.5) timeBasedProgress = 5;      // 0-30 seconds: 5%
    else if (minutes < 1) timeBasedProgress = 15;   // 30-60 seconds: 15%
    else if (minutes < 2) timeBasedProgress = 25;   // 1-2 minutes: 25%
    else if (minutes < 3) timeBasedProgress = 50;   // 2-3 minutes: 50%
    else if (minutes < 4) timeBasedProgress = 70;   // 3-4 minutes: 70%
    else if (minutes < 5) timeBasedProgress = 85;   // 4-5 minutes: 85%
    else timeBasedProgress = 90;                    // 5+ minutes: 90%
    
    console.log(`[Progress] Using time-based progress: ${timeBasedProgress}% for campaign ${campaign.id} (${minutes.toFixed(1)} minutes elapsed)`);
    return timeBasedProgress;
  };

  // Helper function to determine campaign status
  const getCampaignStatus = (campaign: Campaign): "INCOMPLETE" | "PROCESSING" | "READY_TO_ACTIVATE" | "ACTIVE" => {
    // If campaign has topics, it's ready to activate (successfully built)
    if (campaign.topics && campaign.topics.length > 0) {
      return "READY_TO_ACTIVATE";
    }
    
    // If campaign is marked as processing but has no topics, it might have failed
    // Check if it's been processing for more than 5 minutes since last update
    if (campaign.status === "PROCESSING") {
      const updatedAt = new Date(campaign.updatedAt);
      const now = new Date();
      const minutesSinceUpdate = (now.getTime() - updatedAt.getTime()) / (1000 * 60);
      
      // If it's been processing for more than 5 minutes since last update, mark as incomplete
      if (minutesSinceUpdate > 5) {
        return "INCOMPLETE";
      }
      
      return "PROCESSING";
    }
    
    // If campaign has no topics, it's incomplete (not built yet)
    return "INCOMPLETE";
  };
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showErrorDialog, setShowErrorDialog] = useState(false);

  // Sync settings with campaigns prop whenever campaigns change
  useEffect(() => {
    setSettings(campaigns);
  }, [campaigns]);

  // Polling function for progress updates
  const pollProgress = async (campaignId: string, taskId: string) => {
    try {
      const { getAnalysisStatus } = await import('@/components/Service');
      const status = await getAnalysisStatus(taskId);
      
      if (status.status === "error") {
        console.error("Error polling progress:", status.message);
        return;
      }

      // Update campaign with progress data
      console.log(`[Progress] Campaign ${campaignId}: ${status.progress}% - ${status.current_step} - ${status.message}`);
      setSettings(prev => prev.map(campaign => 
        campaign.id === campaignId 
          ? {
              ...campaign,
              progress: status.progress,
              currentStep: status.current_step,
              progressMessage: status.message,
              status: status.status === "completed" ? "READY_TO_ACTIVATE" : 
                      status.status === "failed" ? "INCOMPLETE" : "PROCESSING"
            }
          : campaign
      ));

      // Stop polling if completed or failed
      if (status.status === "completed" || status.status === "failed") {
        if (pollingIntervals[campaignId]) {
          clearInterval(pollingIntervals[campaignId]);
          setPollingIntervals(prev => {
            const newIntervals = { ...prev };
            delete newIntervals[campaignId];
            return newIntervals;
          });
        }
      }
    } catch (error) {
      console.error("Error polling progress:", error);
    }
  };

  // Update processing start times and start polling when campaigns change to PROCESSING
  useEffect(() => {
    campaigns.forEach(campaign => {
      if (getCampaignStatus(campaign) === "PROCESSING" && campaign.taskId) {
        // Always update start time for PROCESSING campaigns to handle re-processing
        const startTime = new Date(campaign.updatedAt || campaign.createdAt).getTime();
        setProcessingStartTimes(prev => ({
          ...prev,
          [campaign.id]: startTime
        }));

        // Start polling if not already polling
        if (!pollingIntervals[campaign.id]) {
          const interval = setInterval(() => {
            pollProgress(campaign.id, campaign.taskId!);
          }, 2000); // Poll every 2 seconds

          setPollingIntervals(prev => ({
            ...prev,
            [campaign.id]: interval
          }));
        }
      }
    });
  }, [campaigns, pollingIntervals]);

  // Update elapsed time every second for processing campaigns
  useEffect(() => {
    const hasProcessingCampaigns = campaigns.some(campaign => getCampaignStatus(campaign) === "PROCESSING");
    
    if (!hasProcessingCampaigns) return;

    const interval = setInterval(() => {
      // Force re-render to update elapsed time
      setSettings(prev => [...prev]);
    }, 1000);

    return () => clearInterval(interval);
  }, [campaigns]);

  // Remove duplicate campaign fetching - campaigns are already passed as props


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

  const confirmMergeCampaigns = async () => {
    console.log("confirmMergeCampaigns function called!");
    try {
      console.log("Starting merge process...", { selectedCampaigns, settings });
      setIsLoading(true);
      
      const selectedCampaignData = settings?.filter((campaign) =>
        selectedCampaigns.includes(campaign.id)
      );
      console.log("Selected campaign data:", selectedCampaignData);
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

      // Create campaign via API
      console.log("Creating merged campaign via API:", mergedCampaign);
      try {
        const response = await createCampaign(mergedCampaign);
        console.log("API response:", response);
        
        if (response.status === "success") {
          toast.success("Campaigns merged successfully!");
          
          // Refresh campaigns from API to get the server-assigned ID
          if (onRefreshCampaigns) {
            console.log("Calling onRefreshCampaigns...");
            onRefreshCampaigns();
          } else {
            console.log("onRefreshCampaigns not available");
          }
        } else {
          toast.error("Failed to create merged campaign");
        }
      } catch (apiError) {
        console.error("API error:", apiError);
        toast.error("Failed to create merged campaign");
      }
      
      // Close modal and reset state
      setIsMergeModalOpen(false);
      setIsMergeMode(false);
      setSelectedCampaigns([]);
    } catch (error) {
      console.error("Error merging campaigns:", error);
      toast.error("An unexpected error occurred while merging campaigns");
    } finally {
      setIsLoading(false);
    }
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

  const openDeleteModal = (id: string, name: string) => {
    setDeleteModal({
      isOpen: true,
      campaignId: id,
      campaignName: name,
    });
  };

  const closeDeleteModal = () => {
    setDeleteModal({
      isOpen: false,
      campaignId: null,
      campaignName: "",
    });
  };

  const confirmDelete = async () => {
    if (deleteModal.campaignId) {
      await deleteCampaign(deleteModal.campaignId);
      closeDeleteModal();
    }
  };

  const resetCampaignStatus = async (campaignId: string) => {
    try {
      // Update campaign status to INCOMPLETE
      const response = await fetch(`/api/campaigns/${campaignId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: "INCOMPLETE" })
      });

      if (response.ok) {
        // Update local state
        setSettings((prevCampaigns) => {
          const updatedCampaigns = prevCampaigns.map((campaign) =>
            campaign.id === campaignId
              ? { ...campaign, status: "INCOMPLETE" as const }
              : campaign
          );
          return updatedCampaigns;
        });
        
        toast.success("Campaign status reset to incomplete. You can now try building it again.");
      } else {
        toast.error("Failed to reset campaign status");
      }
    } catch (error) {
      console.error("Error resetting campaign status:", error);
      toast.error("Error resetting campaign status");
    }
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70" style={{ 
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)'
      }}>
        <div className="bg-white rounded-lg shadow-2xl p-8 max-w-sm w-full mx-4 border border-gray-200">
          <div className="flex flex-col items-center space-y-4">
            <div className="relative">
              <svg
                className="animate-spin h-12 w-12 text-[#3d545f]"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 text-center">
              Loading campaigns...
            </h3>
          </div>
        </div>
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
                {/* MERGE FUNCTIONALITY TEMPORARILY DISABLED - See hiddenForNow.md for re-implementation guide */}
                {/* <Button onClick={() => setIsMergeMode(true)} variant="outline">
                  Merge Research
                </Button> */}
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
                <div className="flex justify-between items-center">
                  <CardTitle>
                    {editingId ? "Edit Campaign" : "Create New Campaign"}
                  </CardTitle>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      resetForm();
                      setIsCreating(false);
                    }}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    Cancel, return to Campaigns
                  </Button>
                </div>
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

      <div className="space-y-4">
        {settings?.map((campaign) => (
          <Card key={campaign.id}>
            <CardContent className="p-6">
              <div className="flex justify-between items-start">
                <div className="flex items-start">
                  {/* MERGE FUNCTIONALITY TEMPORARILY DISABLED - See hiddenForNow.md for re-implementation guide */}
                  {/* {isMergeMode && (
                    <div className="mr-3 mt-1">
                      <input
                        type="checkbox"
                        id={`select-${campaign.id}`}
                        checked={selectedCampaigns.includes(campaign.id)}
                        onChange={() => handleCampaignSelection(campaign.id)}
                        className="h-5 w-5 rounded border-gray-300 text-[#3d545f] focus:ring-[#3d545f]"
                      />
                    </div>
                  )} */}
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
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        getCampaignStatus(campaign) === "INCOMPLETE" 
                          ? "bg-orange-100 text-orange-800" 
                          : getCampaignStatus(campaign) === "PROCESSING"
                            ? "bg-yellow-100 text-yellow-800"
                            : getCampaignStatus(campaign) === "READY_TO_ACTIVATE"
                              ? "bg-blue-100 text-blue-800"
                              : "bg-green-100 text-green-800"
                      }`}>
                        {getCampaignStatus(campaign) === "INCOMPLETE" 
                          ? "INCOMPLETE" 
                          : getCampaignStatus(campaign) === "PROCESSING"
                            ? "PROCESSING"
                            : getCampaignStatus(campaign) === "READY_TO_ACTIVATE"
                              ? "READY TO ACTIVATE"
                              : "ACTIVE"}
                      </span>
                    </div>
                    <p className="text-gray-500 mt-1">{campaign.description}</p>
                    
                    {/* Progress indicator for processing campaigns */}
                    {getCampaignStatus(campaign) === "PROCESSING" && (
                      <div className="mt-3 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg shadow-sm">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-2">
                            <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
                            <span className="text-sm font-semibold text-blue-800">Building Campaign...</span>
                          </div>
                          <div className="text-sm font-mono text-blue-600 bg-blue-100 px-2 py-1 rounded">
                            ⏱️ {getElapsedTime(campaign)}
                          </div>
                        </div>
                        
                        <div className="text-xs text-blue-700 mb-3 p-2 bg-blue-100 rounded border-l-4 border-blue-400">
                          <strong>⏱️ Important:</strong> This process can take 2-5 minutes as it has a lot to do! Please be patient as we collect all we need.
                        </div>
                        
                        <div className="w-full bg-blue-200 rounded-full h-2.5 mb-3">
                          <div 
                            className="bg-gradient-to-r from-blue-500 to-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
                            style={{ width: `${getProgressPercentage(campaign)}%` }}
                          ></div>
                        </div>
                        
                        <div className="flex items-center justify-between text-xs text-blue-600">
                          <span>{campaign.progressMessage || "🔄 Processing keywords, extracting content, and analyzing topics..."}</span>
                          <span className="font-medium">{Math.round(getProgressPercentage(campaign))}%</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex space-x-2">
                  <Link href={`/dashboard/campaigns/edit/${campaign.id}`}>
                    <Button variant="outline" size="sm">
                      <Edit className="w-4 h-4 mr-2" />
                      Edit
                    </Button>
                  </Link>
                  {getCampaignStatus(campaign) === "PROCESSING" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => resetCampaignStatus(campaign.id)}
                      className="text-orange-600 border-orange-300 hover:bg-orange-50"
                    >
                      <Key className="w-4 h-4 mr-2" />
                      Reset Status
                    </Button>
                  )}
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => openDeleteModal(campaign.id, campaign.name)}
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
        {!isCreating && (
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
        {/* MERGE FUNCTIONALITY TEMPORARILY DISABLED - See hiddenForNow.md for re-implementation guide */}
        {/* {isMergeMode && (
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
        )} */}
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

      <AlertDialog open={deleteModal.isOpen} onOpenChange={closeDeleteModal}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-500" />
              Delete Campaign
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>
                Are you sure you want to delete the campaign <strong>"{deleteModal.campaignName}"</strong>?
              </p>
              <p className="text-red-600 font-medium">
                ⚠️ This action cannot be undone. All campaign data and settings will be permanently deleted.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={closeDeleteModal}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={confirmDelete}
              className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete Campaign
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
