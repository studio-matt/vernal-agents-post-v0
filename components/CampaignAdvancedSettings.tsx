"use client";

import type React from "react";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
// Add the InfoIcon import
import { Database, Code, Network, Brain, InfoIcon } from "lucide-react";
import type { Campaign } from "./ContentPlannerCampaign";
import { ParameterInfoModal } from "./ParameterInfoModal";

interface CampaignAdvancedSettingsProps {
  campaign: Campaign;
  onSave: (updatedSettings: Partial<Campaign>) => void;
}

export function CampaignAdvancedSettings({
  campaign,
  onSave,
}: CampaignAdvancedSettingsProps) {
  // Initialize state with campaign settings or defaults
  const [extractionSettings, setExtractionSettings] = useState({
    webScrapingDepth: campaign.extractionSettings?.webScrapingDepth || 2,
    includeImages: campaign.extractionSettings?.includeImages || true,
    includeLinks: campaign.extractionSettings?.includeLinks || true,
    maxPages: campaign.extractionSettings?.maxPages || 10,
    batchSize: campaign.extractionSettings?.batchSize || 10,
  });

  const [preprocessingSettings, setPreprocessingSettings] = useState({
    removeStopwords: campaign.preprocessingSettings?.removeStopwords || true,
    stemming: campaign.preprocessingSettings?.stemming || true,
    lemmatization: campaign.preprocessingSettings?.lemmatization || true,
    caseSensitive: campaign.preprocessingSettings?.caseSensitive || false,
  });

  const [entitySettings, setEntitySettings] = useState({
    extractPersons: campaign.entitySettings?.extractPersons || true,
    extractOrganizations: campaign.entitySettings?.extractOrganizations || true,
    extractLocations: campaign.entitySettings?.extractLocations || true,
    extractDates: campaign.entitySettings?.extractDates || true,
    confidenceThreshold: campaign.entitySettings?.confidenceThreshold || 0.7,
  });

  // Update the algorithm state initialization to include the new options
  const [modelingSettings, setModelingSettings] = useState({
    algorithm: campaign.modelingSettings?.algorithm || "lda",
    numTopics: campaign.modelingSettings?.numTopics || 5,
    iterations: campaign.modelingSettings?.iterations || 10,
    passThreshold: campaign.modelingSettings?.passThreshold || 0.5,
  });

  const [activeTab, setActiveTab] = useState("extraction");

  // Add the info modal state after the other state declarations
  const [infoModal, setInfoModal] = useState<{
    isOpen: boolean;
    title: string;
    description: React.ReactNode;
  }>({
    isOpen: false,
    title: "",
    description: "",
  });

  // Add the openInfoModal and closeInfoModal functions
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

  // Add the parameter descriptions object
  const parameterDescriptions = {
    // Web Scraping
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
        <div>Should images be extracted along with text?</div>
        <div>
          <strong>ON:</strong> Captures images for visual content analysis.
        </div>
        <div>
          <strong>OFF:</strong> Text-only extraction (faster, smaller dataset).
        </div>
      </div>
    ),
    includeLinks: (
      <div className="space-y-2">
        <div>Should hyperlinks be preserved in the extracted content?</div>
        <div>
          <strong>ON:</strong> Maintains link structure for relationship
          analysis.
        </div>
        <div>
          <strong>OFF:</strong> Strips links for cleaner text analysis.
        </div>
      </div>
    ),

    // Text Processing
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

    // Entity Extraction
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

    // Topic Modeling
    algorithm: (
      <div className="space-y-4">
        <div>
          <strong>LDA:</strong> Classic method (like sorting docs into folders).
          Needs 10-20 topics.
        </div>
        <div>
          <strong>NMF:</strong> Lightweight for small datasets (avoids gibberish
          topics).
        </div>
        <div>
          <strong>BERTopic:</strong> Uses AI (groups by meaning, not just
          words). Great for long texts.
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

  const handleSaveSettings = () => {
    onSave({
      extractionSettings,
      preprocessingSettings,
      entitySettings,
      modelingSettings,
    });
  };

  return (
    <div className="space-y-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full mb-6 grid grid-cols-4 gap-2">
          <TabsTrigger value="extraction" className="flex items-center">
            <Database className="h-4 w-4 mr-2" />
            <span>Extraction</span>
          </TabsTrigger>
          <TabsTrigger value="preprocessing" className="flex items-center">
            <Code className="h-4 w-4 mr-2" />
            <span>Preprocessing</span>
          </TabsTrigger>
          <TabsTrigger value="entity" className="flex items-center">
            <Network className="h-4 w-4 mr-2" />
            <span>Entity Recognition</span>
          </TabsTrigger>
          <TabsTrigger value="modeling" className="flex items-center">
            <Brain className="h-4 w-4 mr-2" />
            <span>Topic Modeling</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="extraction">
          <Card>
            <CardContent className="p-6 space-y-4">
              <div className="space-y-4">
                <div className="space-y-2">
                  {/* Update the Web Scraping Depth label with info icon */}
                  <div className="flex justify-between items-center">
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
                    <span className="text-sm text-muted-foreground">
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
                  <p className="text-xs text-muted-foreground">
                    Controls how many levels deep the scraper will follow links
                    from the starting URL.
                  </p>
                </div>

                <div className="space-y-2">
                  {/* Update the Maximum Pages label with info icon */}
                  <div className="flex justify-between items-center">
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
                    <span className="text-sm text-muted-foreground">
                      {extractionSettings.maxPages}
                    </span>
                  </div>
                  <Slider
                    id="max-pages"
                    min={1}
                    max={20}
                    step={10}
                    value={[extractionSettings.maxPages]}
                    onValueChange={(value) =>
                      setExtractionSettings({
                        ...extractionSettings,
                        maxPages: value[0],
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Maximum number of pages to scrape in total.
                  </p>
                </div>

                <div className="space-y-2">
                  {/* Update the Batch Size label with info icon */}
                  <div className="flex justify-between items-center">
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
                    <span className="text-sm text-muted-foreground">
                      {extractionSettings.batchSize}
                    </span>
                  </div>
                  <Slider
                    id="batch-size"
                    min={5}
                    max={50}
                    step={5}
                    value={[extractionSettings.batchSize]}
                    onValueChange={(value) =>
                      setExtractionSettings({
                        ...extractionSettings,
                        batchSize: value[0],
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Number of pages to process in parallel.
                  </p>
                </div>

                {/* Update the Include Images label with info icon */}
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
                    onCheckedChange={(checked) =>
                      setExtractionSettings({
                        ...extractionSettings,
                        includeImages: checked,
                      })
                    }
                  />
                </div>

                {/* Update the Include Links label with info icon */}
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
                    onCheckedChange={(checked) =>
                      setExtractionSettings({
                        ...extractionSettings,
                        includeLinks: checked,
                      })
                    }
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preprocessing">
          <Card>
            <CardContent className="p-6 space-y-4">
              <div className="space-y-4">
                {/* Update the Remove Stopwords label with info icon */}
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
                    onCheckedChange={(checked) =>
                      setPreprocessingSettings({
                        ...preprocessingSettings,
                        removeStopwords: checked,
                      })
                    }
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Remove common words that don't add meaning (e.g., "the",
                  "and", "is").
                </p>

                {/* Update the Stemming label with info icon */}
                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="stemming" className="mr-2">
                      Stemming
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Stemming",
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
                    onCheckedChange={(checked) =>
                      setPreprocessingSettings({
                        ...preprocessingSettings,
                        stemming: checked,
                      })
                    }
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Reduce words to their root form (e.g., "running" → "run").
                </p>

                {/* Update the Lemmatization label with info icon */}
                <div className="flex items-center justify-between space-x-2">
                  <div className="flex items-center">
                    <Label htmlFor="lemmatization" className="mr-2">
                      Lemmatization
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Lemmatization",
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
                    onCheckedChange={(checked) =>
                      setPreprocessingSettings({
                        ...preprocessingSettings,
                        lemmatization: checked,
                      })
                    }
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Convert words to their dictionary form (e.g., "better" →
                  "good").
                </p>

                {/* Update the Case Sensitive label with info icon */}
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
                    onCheckedChange={(checked) =>
                      setPreprocessingSettings({
                        ...preprocessingSettings,
                        caseSensitive: checked,
                      })
                    }
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Treat uppercase and lowercase words as different.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="entity">
          <Card>
            <CardContent className="p-6 space-y-4">
              <div className="space-y-4">
                {/* Update the Extract Persons label with info icon */}
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
                    onCheckedChange={(checked) =>
                      setEntitySettings({
                        ...entitySettings,
                        extractPersons: checked,
                      })
                    }
                  />
                </div>

                {/* Update the Extract Organizations label with info icon */}
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
                    onCheckedChange={(checked) =>
                      setEntitySettings({
                        ...entitySettings,
                        extractOrganizations: checked,
                      })
                    }
                  />
                </div>

                {/* Update the Extract Locations label with info icon */}
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
                    onCheckedChange={(checked) =>
                      setEntitySettings({
                        ...entitySettings,
                        extractLocations: checked,
                      })
                    }
                  />
                </div>

                {/* Update the Extract Dates label with info icon */}
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
                    onCheckedChange={(checked) =>
                      setEntitySettings({
                        ...entitySettings,
                        extractDates: checked,
                      })
                    }
                  />
                </div>

                {/* Update the Confidence Threshold label with info icon */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
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
                    <span className="text-sm text-muted-foreground">
                      {entitySettings.confidenceThreshold.toFixed(1)}
                    </span>
                  </div>
                  <Slider
                    id="confidence-threshold"
                    min={0.1}
                    max={1.0}
                    step={0.1}
                    value={[entitySettings.confidenceThreshold]}
                    onValueChange={(value) =>
                      setEntitySettings({
                        ...entitySettings,
                        confidenceThreshold: value[0],
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Minimum confidence score required to include an entity
                    (0.1-1.0).
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="modeling">
          <Card>
            <CardContent className="p-6 space-y-4">
              <div className="space-y-4">
                {/* Update the algorithm grid in the Topic Modeling tab to include BERTopic and LSA */}
                {/* Replace the existing 2-column grid with this 4-column grid: */}
                <div className="space-y-2">
                  <div className="flex items-center">
                    <Label htmlFor="algorithm" className="mr-2">
                      Algorithm
                    </Label>
                    <button
                      type="button"
                      onClick={() =>
                        openInfoModal(
                          "Algorithm",
                          parameterDescriptions.algorithm
                        )
                      }
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                    <Button
                      type="button"
                      variant={
                        modelingSettings.algorithm === "lda"
                          ? "default"
                          : "outline"
                      }
                      onClick={() =>
                        setModelingSettings({
                          ...modelingSettings,
                          algorithm: "lda",
                        })
                      }
                    >
                      LDA
                    </Button>
                    <Button
                      type="button"
                      variant={
                        modelingSettings.algorithm === "nmf"
                          ? "default"
                          : "outline"
                      }
                      onClick={() =>
                        setModelingSettings({
                          ...modelingSettings,
                          algorithm: "nmf",
                        })
                      }
                    >
                      NMF
                    </Button>
                    <Button
                      type="button"
                      variant={
                        modelingSettings.algorithm === "bertopic"
                          ? "default"
                          : "outline"
                      }
                      onClick={() =>
                        setModelingSettings({
                          ...modelingSettings,
                          algorithm: "bertopic",
                        })
                      }
                    >
                      BERTopic
                    </Button>
                    <Button
                      type="button"
                      variant={
                        modelingSettings.algorithm === "lsa"
                          ? "default"
                          : "outline"
                      }
                      onClick={() =>
                        setModelingSettings({
                          ...modelingSettings,
                          algorithm: "lsa",
                        })
                      }
                    >
                      LSA
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Choose between LDA, NMF, BERTopic, or LSA algorithms for
                    topic modeling.
                  </p>
                </div>

                <div className="space-y-2">
                  {/* Update the Number of Topics label with info icon */}
                  <div className="flex justify-between items-center">
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
                    <span className="text-sm text-muted-foreground">
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
                  <p className="text-xs text-muted-foreground">
                    Number of topics to extract from the content.
                  </p>
                </div>

                <div className="space-y-2">
                  {/* Update the Iterations label with info icon */}
                  <div className="flex justify-between items-center">
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
                    <span className="text-sm text-muted-foreground">
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
                  <p className="text-xs text-muted-foreground">
                    Number of training iterations for the model.
                  </p>
                </div>

                <div className="space-y-2">
                  {/* Update the Pass Threshold label with info icon */}
                  <div className="flex justify-between items-center">
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
                    <span className="text-sm text-muted-foreground">
                      {modelingSettings.passThreshold.toFixed(1)}
                    </span>
                  </div>
                  <Slider
                    id="pass-threshold"
                    min={0.1}
                    max={1.0}
                    step={0.1}
                    value={[modelingSettings.passThreshold]}
                    onValueChange={(value) =>
                      setModelingSettings({
                        ...modelingSettings,
                        passThreshold: value[0],
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Minimum probability threshold for topic assignment.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex justify-end">
        <Button
          onClick={handleSaveSettings}
          className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
        >
          Save Advanced Settings
        </Button>
      </div>
      {/* Add the ParameterInfoModal at the end of the component, just before the closing div */}
      {/* Parameter Info Modal */}
      <ParameterInfoModal
        isOpen={infoModal.isOpen}
        onClose={closeInfoModal}
        title={infoModal.title}
        description={infoModal.description}
      />
    </div>
  );
}
