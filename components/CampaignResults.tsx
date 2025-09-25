"use client"

import type React from "react"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Play,
  FileText,
  Loader2,
  Download,
  Link2,
  FileImage,
  Hash,
  User,
  Building,
  MapPin,
  Calendar,
  Check,
  Lightbulb,
  Bookmark,
  Layers,
  Zap,
  ChevronDown,
  ChevronUp,
  Link,
  ChevronLeft,
} from "lucide-react"
import type { Campaign } from "./ContentPlannerCampaign"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Header } from "./Header"
import { getCampaignsById } from "./Service"

interface CampaignResultsProps {
  title: string
  icon: React.ReactNode
  campaign: Campaign
  stage: "extraction" | "preprocessing" | "entity" | "topic" | "content"
  hasResults: boolean
  onRunAnalysis: () => void
}

export function CampaignResults({
  title,
  icon,
  campaign,
  stage,
  hasResults: initialHasResults,
  onRunAnalysis,
}: CampaignResultsProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [hasResults, setHasResults] = useState(true)
  const [activeTab, setActiveTab] = useState("overview")

  const handleRunAnalysis = () => {
    setIsProcessing(true)

    // Simulate API call
    setTimeout(() => {
      onRunAnalysis()
      setIsProcessing(false)
      setHasResults(true)
    }, 2000)
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center">
            <span className="mr-2">{icon}</span>
            {title}
          </CardTitle>
          <div className="flex space-x-2">
            {hasResults && (
              <Button variant="outline" className="flex items-center">
                <Download className="w-4 h-4 mr-2" />
                Export Results
              </Button>
            )}
            <Button
              onClick={handleRunAnalysis}
              disabled={isProcessing}
              className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Re-Run Analysis
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {hasResults ? (
            <div className="space-y-6">
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="w-full mb-4">
                  <TabsTrigger value="overview" className="flex-1">
                    Overview
                  </TabsTrigger>
                  <TabsTrigger value="charts" className="flex-1">
                    Charts
                  </TabsTrigger>
                  <TabsTrigger value="data" className="flex-1">
                    Data
                  </TabsTrigger>
                  {stage === "content" && (
                    <TabsTrigger value="content" className="flex-1">
                      Generated Content
                    </TabsTrigger>
                  )}
                </TabsList>

                <TabsContent value="overview">
                  {stage === "extraction" && <ExtractionOverview campaign={campaign} />}
                  {stage === "preprocessing" && <PreprocessingOverview campaign={campaign} />}
                  {stage === "entity" && <EntityOverview campaign={campaign} />}
                  {stage === "topic" && <TopicOverview campaign={campaign} />}
                  {stage === "content" && <ContentOverview campaign={campaign} />}
                </TabsContent>

                <TabsContent value="charts">
                  {stage === "extraction" && <ExtractionCharts campaign={campaign} />}
                  {stage === "preprocessing" && <PreprocessingCharts campaign={campaign} />}
                  {stage === "entity" && <EntityCharts campaign={campaign} />}
                  {stage === "topic" && <TopicCharts campaign={campaign} />}
                  {stage === "content" && <ContentCharts campaign={campaign} />}
                </TabsContent>

                <TabsContent value="data">
                  {stage === "extraction" && <ExtractionData campaign={campaign} />}
                  {stage === "preprocessing" && <PreprocessingData campaign={campaign} />}
                  {stage === "entity" && <EntityData campaign={campaign} />}
                  {stage === "topic" && <TopicData campaign={campaign} />}
                  {stage === "content" && <ContentData campaign={campaign} />}
                </TabsContent>

                {stage === "content" && (
                  <TabsContent value="content">
                    <GeneratedContent campaign={campaign} />
                  </TabsContent>
                )}
              </Tabs>
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="bg-gray-100 rounded-full p-6 inline-block mb-4">{icon}</div>
              <h3 className="text-xl font-semibold mb-2">No Results Available</h3>
              <p className="text-gray-500 mb-6 max-w-md mx-auto">
                {stage === "extraction" &&
                  "Run the information extraction process to analyze content from your sources."}
                {stage === "preprocessing" && "Run the preprocessing step to normalize and prepare your text data."}
                {stage === "entity" && "Run entity recognition to identify key entities in your content."}
                {stage === "topic" && "Run topic modeling to discover key themes in your content."}
                {stage === "content" && "Run content generation to create new content based on your analysis."}
              </p>
              <Button
                onClick={handleRunAnalysis}
                disabled={isProcessing}
                className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Run Analysis
                  </>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// Information Extraction Results Components
function ExtractionOverview({ campaign }: { campaign: Campaign }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-blue-100 mb-2">
            <Link2 className="w-6 h-6 text-blue-600" />
          </div>
          <h4 className="font-medium">URLs Processed</h4>
          <p className="text-3xl font-bold mt-1 mb-1">{campaign.type === "url" ? campaign.urls?.length || 0 : 12}</p>
          <p className="text-sm text-gray-500">100% success rate</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-green-100 mb-2">
            <FileText className="w-6 h-6 text-green-600" />
          </div>
          <h4 className="font-medium">Content Extracted</h4>
          <p className="text-3xl font-bold mt-1 mb-1">24.5 KB</p>
          <p className="text-sm text-gray-500">Across 18 pages</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-purple-100 mb-2">
            <FileImage className="w-6 h-6 text-purple-600" />
          </div>
          <h4 className="font-medium">Media Files</h4>
          <p className="text-3xl font-bold mt-1 mb-1">32</p>
          <p className="text-sm text-gray-500">Images, videos, and embeds</p>
        </CardContent>
      </Card>
    </div>
  )
}

function ExtractionCharts({ campaign }: { campaign: Campaign }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Content Distribution by Source</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[300px] flex items-center justify-center">
            <div className="w-full max-w-md">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm">Main Website</span>
                <span className="text-sm font-medium">42%</span>
              </div>
              <Progress value={42} className="h-2 mb-4" />

              <div className="flex items-center justify-between mb-2">
                <span className="text-sm">Blog Articles</span>
                <span className="text-sm font-medium">28%</span>
              </div>
              <Progress value={28} className="h-2 mb-4" />

              <div className="flex items-center justify-between mb-2">
                <span className="text-sm">Product Pages</span>
                <span className="text-sm font-medium">18%</span>
              </div>
              <Progress value={18} className="h-2 mb-4" />

              <div className="flex items-center justify-between mb-2">
                <span className="text-sm">Case Studies</span>
                <span className="text-sm font-medium">12%</span>
              </div>
              <Progress value={12} className="h-2 mb-4" />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Content Type Distribution</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="h-[200px] flex items-center justify-center">
              <div className="relative w-[200px] h-[200px] rounded-full border-8 border-gray-100">
                <div className="absolute inset-0 border-8 border-t-blue-500 border-r-green-500 border-b-yellow-500 border-l-purple-500 rounded-full"></div>
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                  <div className="text-sm font-medium">Total</div>
                  <div className="text-2xl font-bold">156</div>
                  <div className="text-xs text-gray-500">elements</div>
                </div>
              </div>
              <div className="ml-4 space-y-2">
                <div className="flex items-center">
                  <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                  <span className="text-sm">Text (65%)</span>
                </div>
                <div className="flex items-center">
                  <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                  <span className="text-sm">Images (20%)</span>
                </div>
                <div className="flex items-center">
                  <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
                  <span className="text-sm">Links (10%)</span>
                </div>
                <div className="flex items-center">
                  <div className="w-3 h-3 bg-purple-500 rounded-full mr-2"></div>
                  <span className="text-sm">Other (5%)</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Extraction Performance</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="h-[200px] flex items-center justify-center">
              <svg viewBox="0 0 300 150" className="w-full h-full">
                <path
                  d="M0,120 C20,100 40,110 60,90 C80,70 100,60 120,50 C140,40 160,30 180,20 C200,10 220,20 240,30 C260,40 280,30 300,20"
                  fill="none"
                  stroke="#3d545f"
                  strokeWidth="2"
                />
                <path
                  d="M0,120 C20,100 40,110 60,90 C80,70 100,60 120,50 C140,40 160,30 180,20 C200,10 220,20 240,30 C260,40 280,30 300,20"
                  fill="rgba(61, 84, 95, 0.1)"
                  strokeWidth="0"
                />
              </svg>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function ExtractionData({ campaign }: { campaign: Campaign }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Extracted Content Sample</CardTitle>
      </CardHeader>
      <CardContent className="p-4">
        <div className="border rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left">Source</th>
                <th className="px-4 py-2 text-left">Type</th>
                <th className="px-4 py-2 text-left">Content Preview</th>
                <th className="px-4 py-2 text-left">Size</th>
                <th className="px-4 py-2 text-left">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <Link2 className="w-4 h-4 mr-2 text-blue-500" />
                    <span className="text-blue-600 hover:underline">homepage.html</span>
                  </div>
                </td>
                <td className="px-4 py-3">HTML</td>
                <td className="px-4 py-3 max-w-xs truncate">
                  Welcome to our digital marketing platform. We help businesses grow...
                </td>
                <td className="px-4 py-3">4.2 KB</td>
                <td className="px-4 py-3">
                  <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Complete</Badge>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <Link2 className="w-4 h-4 mr-2 text-blue-500" />
                    <span className="text-blue-600 hover:underline">blog/article-1.html</span>
                  </div>
                </td>
                <td className="px-4 py-3">HTML</td>
                <td className="px-4 py-3 max-w-xs truncate">10 Ways to Improve Your Content Strategy in 2025...</td>
                <td className="px-4 py-3">6.8 KB</td>
                <td className="px-4 py-3">
                  <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Complete</Badge>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <Link2 className="w-4 h-4 mr-2 text-blue-500" />
                    <span className="text-blue-600 hover:underline">products/feature-overview.html</span>
                  </div>
                </td>
                <td className="px-4 py-3">HTML</td>
                <td className="px-4 py-3 max-w-xs truncate">
                  Our platform offers comprehensive analytics and reporting...
                </td>
                <td className="px-4 py-3">3.5 KB</td>
                <td className="px-4 py-3">
                  <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Complete</Badge>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <FileImage className="w-4 h-4 mr-2 text-purple-500" />
                    <span className="text-blue-600 hover:underline">assets/hero-image.jpg</span>
                  </div>
                </td>
                <td className="px-4 py-3">Image</td>
                <td className="px-4 py-3 max-w-xs truncate">[Image: Marketing dashboard visualization]</td>
                <td className="px-4 py-3">245 KB</td>
                <td className="px-4 py-3">
                  <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Complete</Badge>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <Link2 className="w-4 h-4 mr-2 text-blue-500" />
                    <span className="text-blue-600 hover:underline">case-studies/client-success.html</span>
                  </div>
                </td>
                <td className="px-4 py-3">HTML</td>
                <td className="px-4 py-3 max-w-xs truncate">How Company X achieved 300% ROI with our platform...</td>
                <td className="px-4 py-3">5.1 KB</td>
                <td className="px-4 py-3">
                  <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">Partial</Badge>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export default function PreprocessingOverview({ campaign }: { campaign: Campaign }) {
  const [wordCount, setWordCount] = useState<number>(0);
  const [uniqueTokenCount, setUniqueTokenCount] = useState<number>(0);
  const [qualityScore, setQualityScore] = useState<number>(0);

  function getWordCount(str: string): number {
    return str.trim().split(/\s+/).length;
  }

  function getRandomQuality(min = 90, max = 98): number {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }


  useEffect(() => {
    const text = localStorage.getItem("storeText");

    if (text) {
      const response = JSON.parse(text);
      const originalWords = getWordCount(response.text || "");
      const stopwordsRemovedWords = getWordCount(response.stopwords_removed_text || "");

      setWordCount(originalWords);
      setUniqueTokenCount(stopwordsRemovedWords);
      setQualityScore(getRandomQuality());
    }
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-blue-100 mb-2">
            <FileText className="w-6 h-6 text-blue-600" />
          </div>
          <h4 className="font-medium">Processed Text</h4>
          <p className="text-3xl font-bold mt-1 mb-1">{wordCount.toLocaleString()}</p>
          <p className="text-sm text-gray-500">After cleaning and normalization</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-green-100 mb-2">
            <Hash className="w-6 h-6 text-green-600" />
          </div>
          <h4 className="font-medium">Unique Tokens</h4>
          <p className="text-3xl font-bold mt-1 mb-1">{uniqueTokenCount.toLocaleString()}</p>
          <p className="text-sm text-gray-500">After stopword removal</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-purple-100 mb-2">
            <Check className="w-6 h-6 text-purple-600" />
          </div>
          <h4 className="font-medium">Processing Quality</h4>
          <p className="text-3xl font-bold mt-1 mb-1">{qualityScore}%</p>
          <p className="text-sm text-gray-500">Text normalization score</p>
        </CardContent>
      </Card>
    </div>
  );
}

function PreprocessingCharts({ campaign }: { campaign: Campaign }) {
  const [wordCount, setWordCount] = useState<number>(0);
  const [uniqueTokenCount, setUniqueTokenCount] = useState<number>(0);
  const [lemmatizationWordCount, setLemmatizationWordCount] = useState<number>(0);
  const [stemmedtextWordCount, setstemmedtextWordCount] = useState<number>(0);
  const [qualityScore, setQualityScore] = useState<number>(0);

  function getWordCount(str: string): number {
    return str.trim().split(/\s+/).length;
  }

  function getRandomQuality(min = 90, max = 98): number {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }


  useEffect(() => {
    const text = localStorage.getItem("storeText");

    if (text) {
      const response = JSON.parse(text);
      const originalWords = getWordCount(response.text || "");
      const stopwordsRemovedWords = getWordCount(response.stopwords_removed_text || "");
      const lemmatizationRemovedWords = getWordCount(response.stopwords_removed_text || "");
      const stemmedtextRemovedWords = getWordCount(response.stopwords_removed_text || "");

      setWordCount(originalWords);
      setUniqueTokenCount(stopwordsRemovedWords);
      setLemmatizationWordCount(lemmatizationRemovedWords)
      setstemmedtextWordCount(stemmedtextRemovedWords)
      setQualityScore(getRandomQuality());
    }
  }, []);

  // Calculate percentages
  const stopwordRemovalPercentage = ((wordCount - uniqueTokenCount) / wordCount) * 100;
  const lemmatizationRemovalPercentage = ((uniqueTokenCount - lemmatizationWordCount) / uniqueTokenCount) * 100;
  const punctuationRemovalPercentage = ((lemmatizationWordCount - stemmedtextWordCount) / lemmatizationWordCount) * 100;
  const otherPercentage = Math.floor(Math.random() * 10) + 1; // Random number between 1 and 10

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Text Transformation Impact</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[300px] flex items-center justify-center">
            <div className="w-full max-w-md space-y-6">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm">Original Text</span>
                  <span className="text-sm font-medium">{wordCount}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div className="bg-gray-500 h-4 rounded-full" style={{ width: "100%" }}></div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm">After Stopword Removal</span>
                  <span className="text-sm font-medium">{uniqueTokenCount}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div className="bg-blue-500 h-4 rounded-full" style={{ width: "82%" }}></div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm">After Lemmatization</span>
                  <span className="text-sm font-medium">{lemmatizationWordCount}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div className="bg-green-500 h-4 rounded-full" style={{ width: "74%" }}></div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm">Final Processed Text</span>
                  <span className="text-sm font-medium">{stemmedtextWordCount}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div className="bg-purple-500 h-4 rounded-full" style={{ width: "74%" }}></div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Processing Steps Impact</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[200px] flex items-center justify-center">
            <div className="relative w-[200px] h-[200px] rounded-full border-8 border-gray-100">
              <div className="absolute inset-0 border-8 border-t-blue-500 border-r-green-500 border-b-yellow-500 border-l-purple-500 rounded-full"></div>
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                <div className="text-sm font-medium">Reduction</div>
                <div className="text-2xl font-bold">
                  {Math.max(0, ((wordCount + uniqueTokenCount + lemmatizationWordCount + stemmedtextWordCount) / 100)).toFixed(2)}%
                </div>
                <div className="text-xs text-gray-500">overall</div>
              </div>
            </div>
            <div className="ml-4 space-y-2">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                {/* <span className="text-sm">Stopwords ({stopwordRemovalPercentage.toFixed(2)}%)</span> */}
                <span className="text-sm">Stopwords ({wordCount.toFixed(2)}%)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                <span className="text-sm">Lemmatization ({uniqueTokenCount.toFixed(2)}%)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
                <span className="text-sm">Punctuation ({lemmatizationWordCount.toFixed(2)}%)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-purple-500 rounded-full mr-2"></div>
                <span className="text-sm">Other ({stemmedtextWordCount}%)</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
         <Card>
          <CardHeader>
            <CardTitle className="text-base">Token Frequency Distribution</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="h-[200px] flex items-center justify-center">
              <svg viewBox="0 0 300 150" className="w-full h-full">
                <path
                  d="M0,150 L20,120 L40,100 L60,85 L80,75 L100,65 L120,60 L140,55 L160,52 L180,50 L200,48 L220,47 L240,46 L260,45 L280,44 L300,43"
                  fill="none"
                  stroke="#3d545f"
                  strokeWidth="2"
                />
                <path
                  d="M0,150 L20,120 L40,100 L60,85 L80,75 L100,65 L120,60 L140,55 L160,52 L180,50 L200,48 L220,47 L240,46 L260,45 L280,44 L300,43 L300,150 L0,150"
                  fill="rgba(61, 84, 95, 0.1)"
                  strokeWidth="0"
                />
              </svg>
            </div>
          </CardContent>
        </Card> 

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Processing Steps Impact</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[200px] flex items-center justify-center">
            <div className="relative w-[200px] h-[200px] rounded-full border-8 border-gray-100">
              <div className="absolute inset-0 border-8 border-t-blue-500 border-r-green-500 border-b-yellow-500 border-l-purple-500 rounded-full"></div>
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                <div className="text-sm font-medium">Reduction</div>
                <div className="text-2xl font-bold">{(stopwordRemovalPercentage + lemmatizationRemovalPercentage + punctuationRemovalPercentage).toFixed(2)}%</div>
                <div className="text-xs text-gray-500">overall</div>
              </div>
            </div>
            <div className="ml-4 space-y-2">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                <span className="text-sm">Stopwords ({stopwordRemovalPercentage.toFixed(2)}%)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                <span className="text-sm">Lemmatization ({lemmatizationRemovalPercentage.toFixed(2)}%)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
                <span className="text-sm">Punctuation ({punctuationRemovalPercentage.toFixed(2)}%)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-purple-500 rounded-full mr-2"></div>
                <span className="text-sm">Other ({otherPercentage}%)</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div> */}
    </div >
  )
}

function PreprocessingData({ campaign }: { campaign: Campaign }) {
  const [showRawResults, setShowRawResults] = useState(false)

  // Sample data for text transformation samples
  const sampleTransformations = [
    {
      original: "The company's marketing strategies have been improving steadily.",
      processed: "company marketing strategy improve steadily",
      transformations: ["Stopwords Removed", "Lemmatized"],
    },
    {
      original: "Our customers are extremely satisfied with the new features!",
      processed: "customer extremely satisfy new feature",
      transformations: ["Stopwords Removed", "Lemmatized", "Punctuation Removed"],
    },
    {
      original: "The 2025 Q1 report shows a 25% increase in engagement metrics.",
      processed: "2025 q1 report show 25% increase engagement metric",
      transformations: ["Stopwords Removed", "Lemmatized"],
    },
    {
      original: "Running multiple marketing campaigns simultaneously can be challenging.",
      processed: "run multiple marketing campaign simultaneously challenging",
      transformations: ["Stopwords Removed", "Lemmatized"],
    },
    {
      original: "Social media's impact on brand awareness cannot be overstated.",
      processed: "social media impact brand awareness overstate",
      transformations: ["Stopwords Removed", "Lemmatized", "Negation Handled"],
    },
  ]

  // Extended data for raw results
  // const rawTransformations = [
  //   ...sampleTransformations,
  //   {
  //     original: "Digital marketing requires a comprehensive understanding of consumer behavior.",
  //     processed: "digital marketing require comprehensive understand consumer behavior",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  //   {
  //     original: "Content creation is an essential part of any successful marketing strategy.",
  //     processed: "content creation essential part successful marketing strategy",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  //   {
  //     original: "The analytics dashboard provides real-time insights into campaign performance.",
  //     processed: "analytics dashboard provide real-time insight campaign performance",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  //   {
  //     original: "Email marketing campaigns have shown a 15% higher conversion rate this quarter.",
  //     processed: "email marketing campaign show 15% high conversion rate quarter",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  //   {
  //     original: "Search engine optimization is crucial for improving website visibility.",
  //     processed: "search engine optimization crucial improve website visibility",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  //   {
  //     original: "User-generated content helps build trust and authenticity with your audience.",
  //     processed: "user-generated content help build trust authenticity audience",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  //   {
  //     original: "Mobile-friendly websites are essential in today's smartphone-dominated market.",
  //     processed: "mobile-friendly website essential today smartphone-dominated market",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  //   {
  //     original: "Video content is becoming increasingly important for social media engagement.",
  //     processed: "video content become increasingly important social media engagement",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  //   {
  //     original: "Customer feedback should be regularly collected and analyzed for product improvements.",
  //     processed: "customer feedback regularly collect analyze product improvement",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  //   {
  //     original: "Influencer partnerships can significantly expand your brand's reach and credibility.",
  //     processed: "influencer partnership significantly expand brand reach credibility",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  //   {
  //     original: "The quarterly newsletter will be distributed to all subscribers next week.",
  //     processed: "quarterly newsletter distribute subscriber next week",
  //     transformations: ["Stopwords Removed", "Lemmatized"],
  //   },
  // ]

  const [rawTransformations, setrawTransformations] = useState([])

  const [isLoading, setIsLoading] = useState(false)
  useEffect(() => {
    // In a real app, this would be an API call
    const fetchCampaign = async () => {
      ;
      setIsLoading(true);
      const campaignId = localStorage.getItem("id")
      if (campaignId) {
        try {
          const editableCampaigns = await getCampaignsById(campaignId);
          console.log(editableCampaigns)

          if (editableCampaigns.status === "success") {
            const otherDetails = {
              organizations: editableCampaigns.message.raw_data[0].organizations || [],
              locations: editableCampaigns.message.raw_data[0].locations || [],
              persons: editableCampaigns.message.raw_data[0].persons || [],
              dates: editableCampaigns.message.raw_data[0].dates || []
            }

            const storeText = {
              text: editableCampaigns.message.raw_data[0].text || "",
              stemmed_text: editableCampaigns.message.raw_data[0].stemmed_text || "",
              lemmatized_text: editableCampaigns.message.raw_data[0].lemmatized_text || "",
              stopwords_removed_text: editableCampaigns.message.raw_data[0].stopwords_removed_text || ""
            }

            localStorage.setItem("otherDetails", JSON.stringify(otherDetails));
            localStorage.setItem("storeText", JSON.stringify(storeText));

            const newData = [{
              original: editableCampaigns.message.raw_data[0].text || "",
              processed: editableCampaigns.message.raw_data[0].lemmatized_text || "",
              transformations: ["Lemmatized"],
            },
            {
              original: editableCampaigns.message.raw_data[0].text || "",
              processed: editableCampaigns.message.raw_data[0].stemmed_text || "",
              transformations: ["stemmed_text"],
            },
            {
              original: editableCampaigns.message.raw_data[0].text || "",
              processed: editableCampaigns.message.raw_data[0].stopwords_removed_text || "",
              transformations: ["stopwords_removed_text"],
            }]

            setrawTransformations(newData);
          }
        } catch (err) {
          console.log("error", err);
        } finally {
          setIsLoading(false);
        }
      };
    }

    fetchCampaign();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <div className="flex items-center space-x-4">
            <h1 className="text-4xl font-extrabold text-white">
              Loading data...
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
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Text Transformation Samples</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="border rounded-md overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Original Text</th>
                  <th className="px-4 py-2 text-left">After Preprocessing</th>
                  <th className="px-4 py-2 text-left">Transformation</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rawTransformations?.map((item, index) => (
                  <tr key={index}>
                    <td className="px-4 py-3">{item.original}</td>
                    <td className="px-4 py-3">{item.processed}</td>
                    <td className="px-4 py-3">
                      {item.transformations.map((transform, i) => (
                        <Badge
                          key={i}
                          className={`${transform === "Stopwords Removed"
                            ? "bg-blue-100 text-blue-800"
                            : transform === "Lemmatized"
                              ? "bg-green-100 text-green-800"
                              : transform === "Punctuation Removed"
                                ? "bg-yellow-100 text-yellow-800"
                                : "bg-purple-100 text-purple-800"
                            } ${i > 0 ? "ml-1" : ""} hover:bg-opacity-90`}
                        >
                          {transform}
                        </Badge>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4">
            <Button variant="outline" onClick={() => setShowRawResults(!showRawResults)} className="flex items-center">
              {showRawResults ? (
                <>
                  <ChevronUp className="w-4 h-4 mr-2" />
                  Hide Raw Results
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4 mr-2" />
                  See Raw Results
                </>
              )}
            </Button>
          </div>

          {showRawResults && (
            <div className="mt-4 border rounded-md overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Original Text</th>
                    <th className="px-4 py-2 text-left">After Preprocessing</th>
                    <th className="px-4 py-2 text-left">Transformation</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {rawTransformations.map((item, index) => (
                    <tr key={index}>
                      <td className="px-4 py-3">{item.original}</td>
                      <td className="px-4 py-3">{item.processed}</td>
                      <td className="px-4 py-3">
                        {item.transformations.map((transform, i) => (
                          <Badge
                            key={i}
                            className={`${transform === "Stopwords Removed"
                              ? "bg-blue-100 text-blue-800"
                              : transform === "Lemmatized"
                                ? "bg-green-100 text-green-800"
                                : transform === "Punctuation Removed"
                                  ? "bg-yellow-100 text-yellow-800"
                                  : "bg-purple-100 text-purple-800"
                              } ${i > 0 ? "ml-1" : ""} hover:bg-opacity-90`}
                          >
                            {transform}
                          </Badge>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// Entity Recognition Results Components
function EntityOverview({ campaign }: { campaign: Campaign }) {
  const rawData = localStorage.getItem("otherDetails")

  if (!rawData) {
    return null // safer fallback than just `return`
  }

  const data = JSON.parse(rawData)

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-blue-100 mb-2">
            <User className="w-6 h-6 text-blue-600" />
          </div>
          <h4 className="font-medium">Persons</h4>
          <p className="text-3xl font-bold mt-1 mb-1">{data.persons?.length || 0}</p>
          <p className="text-sm text-gray-500">Identified individuals</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-green-100 mb-2">
            <Building className="w-6 h-6 text-green-600" />
          </div>
          <h4 className="font-medium">Organizations</h4>
          <p className="text-3xl font-bold mt-1 mb-1">{data.organizations?.length || 0}</p>
          <p className="text-sm text-gray-500">Companies and groups</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-purple-100 mb-2">
            <MapPin className="w-6 h-6 text-purple-600" />
          </div>
          <h4 className="font-medium">Locations</h4>
          <p className="text-3xl font-bold mt-1 mb-1">{data.locations?.length || 0}</p>
          <p className="text-sm text-gray-500">Geographic references</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-yellow-100 mb-2">
            <Calendar className="w-6 h-6 text-yellow-600" />
          </div>
          <h4 className="font-medium">Dates</h4>
          <p className="text-3xl font-bold mt-1 mb-1">{data.dates?.length || 0}</p>
          <p className="text-sm text-gray-500">Temporal references</p>
        </CardContent>
      </Card>
    </div>
  )
}

function EntityCharts({ campaign }: { campaign: Campaign }) {
  const [entities, setEntities] = useState<any>(null);

  useEffect(() => {
    const storedEntities = localStorage.getItem("otherDetails");
    if (storedEntities) {
      setEntities(JSON.parse(storedEntities));
    }
  }, []);

  if (!entities) {
    return <div>Loading...</div>; // Show loading state while fetching from localStorage
  }

  const totalEntities = entities.persons.length + entities.organizations.length + entities.locations.length + entities.dates.length;
  const personPercentage = (entities.persons.length / totalEntities) * 100;
  const organizationPercentage = (entities.organizations.length / totalEntities) * 100;
  const locationPercentage = (entities.locations.length / totalEntities) * 100;
  const datePercentage = (entities.dates.length / totalEntities) * 100;

  // Assuming you have confidence scores for each entity type
  const personConfidence = entities.personsConfidence || 92; // Default value
  const organizationConfidence = entities.organizationsConfidence || 88;
  const locationConfidence = entities.locationsConfidence || 95;
  const dateConfidence = entities.datesConfidence || 97;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Entity Distribution</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[300px] flex items-center justify-center">
            <div className="relative w-[300px] h-[300px] rounded-full border-8 border-gray-100">
              <div className="absolute inset-0 border-t-[60px] border-r-[60px] border-b-[60px] border-l-[60px] border-t-blue-500 border-r-green-500 border-b-purple-500 border-l-yellow-500 rounded-full"></div>
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                <div className="text-sm font-medium">Total</div>
                <div className="text-3xl font-bold">{totalEntities}</div>
                <div className="text-xs text-gray-500">entities</div>
              </div>
            </div>
            <div className="ml-8 space-y-4">
              <div className="flex items-center">
                <div className="w-4 h-4 bg-blue-500 rounded-full mr-3"></div>
                <div>
                  <div className="font-medium">Persons</div>
                  <div className="text-sm text-gray-500">{entities.persons.length} entities ({personPercentage.toFixed(2)}%)</div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-green-500 rounded-full mr-3"></div>
                <div>
                  <div className="font-medium">Organizations</div>
                  <div className="text-sm text-gray-500">{entities.organizations.length} entities ({organizationPercentage.toFixed(2)}%)</div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-purple-500 rounded-full mr-3"></div>
                <div>
                  <div className="font-medium">Locations</div>
                  <div className="text-sm text-gray-500">{entities.locations.length} entities ({locationPercentage.toFixed(2)}%)</div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-yellow-500 rounded-full mr-3"></div>
                <div>
                  <div className="font-medium">Dates</div>
                  <div className="text-sm text-gray-500">{entities.dates.length} entities ({datePercentage.toFixed(2)}%)</div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* <div className="grid grid-cols-1 md:grid-cols-2 gap-4"> */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Entity Confidence Scores</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="space-y-4">
            {/* Persons Confidence */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Persons</span>
                <span className="font-medium">{personConfidence.toFixed(2)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-blue-500 h-2.5 rounded-full" style={{ width: `${personConfidence}%` }}></div>
              </div>
            </div>

            {/* Organizations Confidence */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Organizations</span>
                <span className="font-medium">{organizationConfidence.toFixed(2)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-green-500 h-2.5 rounded-full" style={{ width: `${organizationConfidence}%` }}></div>
              </div>
            </div>

            {/* Locations Confidence */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Locations</span>
                <span className="font-medium">{locationConfidence.toFixed(2)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-purple-500 h-2.5 rounded-full" style={{ width: `${locationConfidence}%` }}></div>
              </div>
            </div>

            {/* Dates Confidence */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Dates</span>
                <span className="font-medium">{dateConfidence.toFixed(2)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-yellow-500 h-2.5 rounded-full" style={{ width: `${dateConfidence}%` }}></div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      {/* </div> */}
    </div>
  );
}


function EntityData({ campaign }: { campaign: Campaign }) {

  const rawData = localStorage.getItem("otherDetails")

  if (!rawData) {
    return null // safer fallback than just `return`
  }

  const data = JSON.parse(rawData);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Extracted Entities</CardTitle>
      </CardHeader>
      <CardContent className="p-4">
        <div className="border rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left">Entity</th>
                <th className="px-4 py-2 text-left">Type</th>
                {/* <th className="px-4 py-2 text-left">Context</th>
                <th className="px-4 py-2 text-left">Confidence</th>
                <th className="px-4 py-2 text-left">Occurrences</th> */}
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="px-4 py-3 font-medium">{data.persons?.join(', ') || "No data available"}
                </td>
                <td className="px-4 py-3">
                  <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Person</Badge>
                </td>
                {/* <td className="px-4 py-3 max-w-xs truncate">
                  ...our CEO John Smith discussed the future of marketing...
                </td>
                <td className="px-4 py-3">98%</td>
                <td className="px-4 py-3">5</td> */}
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">{data.organizations?.join(', ') || "No data available"}</td>
                <td className="px-4 py-3">
                  <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Organization</Badge>
                </td>
                {/* <td className="px-4 py-3 max-w-xs truncate">
                  ...partnership with Acme Corporation has led to significant growth...
                </td>
                <td className="px-4 py-3">95%</td>
                <td className="px-4 py-3">12</td> */}
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">{data.locations?.join(', ') || "No data available"}</td>
                <td className="px-4 py-3">
                  <Badge className="bg-purple-100 text-purple-800 hover:bg-purple-100">Location</Badge>
                </td>
                {/* <td className="px-4 py-3 max-w-xs truncate">
                  ...our headquarters in San Francisco hosts regular industry events...
                </td>
                <td className="px-4 py-3">99%</td>
                <td className="px-4 py-3">7</td> */}
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">{data.dates?.join(', ') || "No data available"}</td>
                <td className="px-4 py-3">
                  <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">Date</Badge>
                </td>
                {/* <td className="px-4 py-3 max-w-xs truncate">...planning to launch the new platform in Q1 2025...</td>
                <td className="px-4 py-3">97%</td>
                <td className="px-4 py-3">9</td> */}
              </tr>
              {/* <tr>
                <td className="px-4 py-3 font-medium">Sarah Johnson</td>
                <td className="px-4 py-3">
                  <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Person</Badge>
                </td>
                <td className="px-4 py-3 max-w-xs truncate">
                  ...marketing director Sarah Johnson presented the strategy...
                </td>
                <td className="px-4 py-3">96%</td>
                <td className="px-4 py-3">4</td>
              </tr> */
              }
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

// Topic Modeling Results Components
function TopicOverview({ campaign }: { campaign: Campaign }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-blue-100 mb-2">
            <Layers className="w-6 h-6 text-blue-600" />
          </div>
          <h4 className="font-medium">Topics Identified</h4>
          <p className="text-3xl font-bold mt-1 mb-1">8</p>
          <p className="text-sm text-gray-500">Distinct thematic clusters</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-green-100 mb-2">
            <Bookmark className="w-6 h-6 text-green-600" />
          </div>
          <h4 className="font-medium">Topic Coherence</h4>
          <p className="text-3xl font-bold mt-1 mb-1">0.82</p>
          <p className="text-sm text-gray-500">Average coherence score</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-purple-100 mb-2">
            <Lightbulb className="w-6 h-6 text-purple-600" />
          </div>
          <h4 className="font-medium">Topic Coverage</h4>
          <p className="text-3xl font-bold mt-1 mb-1">94%</p>
          <p className="text-sm text-gray-500">Content coverage by topics</p>
        </CardContent>
      </Card>
    </div>
  )
}

function TopicCharts({ campaign }: { campaign: Campaign }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Topic Distribution</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[300px] flex items-center justify-center">
            <div className="w-full max-w-md space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Digital Marketing Strategy</span>
                  <span className="font-medium">28%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div className="bg-blue-500 h-3 rounded-full" style={{ width: "28%" }}></div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Content Creation</span>
                  <span className="font-medium">22%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div className="bg-green-500 h-3 rounded-full" style={{ width: "22%" }}></div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Social Media Marketing</span>
                  <span className="font-medium">18%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div className="bg-purple-500 h-3 rounded-full" style={{ width: "18%" }}></div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Analytics & Reporting</span>
                  <span className="font-medium">12%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div className="bg-yellow-500 h-3 rounded-full" style={{ width: "12%" }}></div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Customer Engagement</span>
                  <span className="font-medium">8%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div className="bg-red-500 h-3 rounded-full" style={{ width: "8%" }}></div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Other Topics</span>
                  <span className="font-medium">12%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div className="bg-gray-500 h-3 rounded-full" style={{ width: "12%" }}></div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Topic Similarity</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="h-[200px] flex items-center justify-center">
              <svg viewBox="0 0 300 200" className="w-full h-full">
                {/* Topic connections */}
                <line x1="50" y1="50" x2="150" y2="50" stroke="#ccc" strokeWidth="2" />
                <line x1="50" y1="50" x2="50" y2="150" stroke="#ccc" strokeWidth="2" />
                <line x1="50" y1="50" x2="150" y2="150" stroke="#ccc" strokeWidth="3" />
                <line x1="150" y1="50" x2="250" y2="50" stroke="#ccc" strokeWidth="1" />
                <line x1="150" y1="50" x2="150" y2="150" stroke="#ccc" strokeWidth="2" />
                <line x1="150" y1="50" x2="250" y2="150" stroke="#ccc" strokeWidth="1" />
                <line x1="50" y1="150" x2="150" y2="150" stroke="#ccc" strokeWidth="2" />
                <line x1="150" y1="150" x2="250" y2="150" stroke="#ccc" strokeWidth="2" />
                <line x1="250" y1="50" x2="250" y2="150" stroke="#ccc" strokeWidth="1" />

                {/* Topic nodes */}
                <circle cx="50" cy="50" r="15" fill="#3b82f6" />
                <circle cx="150" cy="50" r="15" fill="#22c55e" />
                <circle cx="250" cy="50" r="15" fill="#a855f7" />
                <circle cx="50" cy="150" r="15" fill="#eab308" />
                <circle cx="150" cy="150" r="15" fill="#ef4444" />
                <circle cx="250" cy="150" r="15" fill="#64748b" />

                {/* Topic labels */}
                <text x="50" y="55" textAnchor="middle" fill="white" fontSize="8">
                  Topic 1
                </text>
                <text x="150" y="55" textAnchor="middle" fill="white" fontSize="8">
                  Topic 2
                </text>
                <text x="250" y="55" textAnchor="middle" fill="white" fontSize="8">
                  Topic 3
                </text>
                <text x="50" y="155" textAnchor="middle" fill="white" fontSize="8">
                  Topic 4
                </text>
                <text x="150" y="155" textAnchor="middle" fill="white" fontSize="8">
                  Topic 5
                </text>
                <text x="250" y="155" textAnchor="middle" fill="white" fontSize="8">
                  Topic 6
                </text>
              </svg>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Topic Evolution</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="h-[200px] flex items-center justify-center">
              <svg viewBox="0 0 300 150" className="w-full h-full">
                {/* Topic 1 */}
                <path
                  d="M0,120 C20,110 40,100 60,90 C80,85 100,80 120,85 C140,90 160,100 180,105 C200,110 220,115 240,110 C260,105 280,100 300,95"
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="2"
                />

                {/* Topic 2 */}
                <path
                  d="M0,100 C20,95 40,90 60,80 C80,70 100,60 120,50 C140,45 160,40 180,45 C200,50 220,60 240,65 C260,70 280,75 300,70"
                  fill="none"
                  stroke="#22c55e"
                  strokeWidth="2"
                />

                {/* Topic 3 */}
                <path
                  d="M0,80 C20,85 40,90 60,95 C80,100 100,105 120,100 C140,95 160,90 180,85 C200,80 220,75 240,80 C260,85 280,90 300,95"
                  fill="none"
                  stroke="#a855f7"
                  strokeWidth="2"
                />

                {/* X-axis */}
                <line x1="0" y1="140" x2="300" y2="140" stroke="#ccc" strokeWidth="1" />

                {/* X-axis labels */}
                <text x="0" y="150" fontSize="8" fill="#666">
                  Jan
                </text>
                <text x="60" y="150" fontSize="8" fill="#666">
                  Feb
                </text>
                <text x="120" y="150" fontSize="8" fill="#666">
                  Mar
                </text>
                <text x="180" y="150" fontSize="8" fill="#666">
                  Apr
                </text>
                <text x="240" y="150" fontSize="8" fill="#666">
                  May
                </text>
                <text x="300" y="150" fontSize="8" fill="#666">
                  Jun
                </text>
              </svg>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function TopicData({ campaign }: { campaign: Campaign }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Topic Keywords and Documents</CardTitle>
      </CardHeader>
      <CardContent className="p-4">
        <div className="border rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left">Topic</th>
                <th className="px-4 py-2 text-left">Top Keywords df</th>
                <th className="px-4 py-2 text-left">Representative Document</th>
                <th className="px-4 py-2 text-left">Coherence</th>
                <th className="px-4 py-2 text-left">Coverage</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="px-4 py-3 font-medium">Digital Marketing Strategy</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    <Badge className="bg-blue-50 text-blue-600">strategy</Badge>
                    <Badge className="bg-blue-50 text-blue-600">digital</Badge>
                    <Badge className="bg-blue-50 text-blue-600">marketing</Badge>
                    <Badge className="bg-blue-50 text-blue-600">campaign</Badge>
                    <Badge className="bg-blue-50 text-blue-600">planning</Badge>
                  </div>
                </td>
                <td className="px-4 py-3 max-w-xs truncate">
                  Our digital marketing strategy focuses on integrated campaigns across multiple channels...
                </td>
                <td className="px-4 py-3">0.87</td>
                <td className="px-4 py-3">28%</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Content Creation</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    <Badge className="bg-green-50 text-green-600">content</Badge>
                    <Badge className="bg-green-50 text-green-600">creation</Badge>
                    <Badge className="bg-green-50 text-green-600">blog</Badge>
                    <Badge className="bg-green-50 text-green-600">article</Badge>
                    <Badge className="bg-green-50 text-green-600">video</Badge>
                  </div>
                </td>
                <td className="px-4 py-3 max-w-xs truncate">
                  Creating engaging content is essential for building brand awareness and driving engagement...
                </td>
                <td className="px-4 py-3">0.85</td>
                <td className="px-4 py-3">22%</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Social Media Marketing</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    <Badge className="bg-purple-50 text-purple-600">social</Badge>
                    <Badge className="bg-purple-50 text-purple-600">media</Badge>
                    <Badge className="bg-purple-50 text-purple-600">platform</Badge>
                    <Badge className="bg-purple-50 text-purple-600">engagement</Badge>
                    <Badge className="bg-purple-50 text-purple-600">followers</Badge>
                  </div>
                </td>
                <td className="px-4 py-3 max-w-xs truncate">
                  Our social media marketing approach focuses on building authentic connections with our audience...
                </td>
                <td className="px-4 py-3">0.79</td>
                <td className="px-4 py-3">18%</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Analytics & Reporting</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    <Badge className="bg-yellow-50 text-yellow-600">analytics</Badge>
                    <Badge className="bg-yellow-50 text-yellow-600">data</Badge>
                    <Badge className="bg-yellow-50 text-yellow-600">metrics</Badge>
                    <Badge className="bg-yellow-50 text-yellow-600">reporting</Badge>
                    <Badge className="bg-yellow-50 text-yellow-600">insights</Badge>
                  </div>
                </td>
                <td className="px-4 py-3 max-w-xs truncate">
                  Data-driven decision making requires robust analytics and comprehensive reporting...
                </td>
                <td className="px-4 py-3">0.83</td>
                <td className="px-4 py-3">12%</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Customer Engagement</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    <Badge className="bg-red-50 text-red-600">customer</Badge>
                    <Badge className="bg-red-50 text-red-600">engagement</Badge>
                    <Badge className="bg-red-50 text-red-600">experience</Badge>
                    <Badge className="bg-red-50 text-red-600">journey</Badge>
                    <Badge className="bg-red-50 text-red-600">satisfaction</Badge>
                  </div>
                </td>
                <td className="px-4 py-3 max-w-xs truncate">
                  Enhancing customer engagement through personalized experiences leads to higher retention rates...
                </td>
                <td className="px-4 py-3">0.76</td>
                <td className="px-4 py-3">8%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

// Content Generation Results Components
function ContentOverview({ campaign }: { campaign: Campaign }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-blue-100 mb-2">
            <FileText className="w-6 h-6 text-blue-600" />
          </div>
          <h4 className="font-medium">Content Pieces</h4>
          <p className="text-3xl font-bold mt-1 mb-1">12</p>
          <p className="text-sm text-gray-500">Generated articles and posts</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-green-100 mb-2">
            <Hash className="w-6 h-6 text-green-600" />
          </div>
          <h4 className="font-medium">Keywords Used</h4>
          <p className="text-3xl font-bold mt-1 mb-1">86</p>
          <p className="text-sm text-gray-500">Across all content</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="p-3 rounded-full bg-purple-100 mb-2">
            <Zap className="w-6 h-6 text-purple-600" />
          </div>
          <h4 className="font-medium">Readability Score</h4>
          <p className="text-3xl font-bold mt-1 mb-1">82</p>
          <p className="text-sm text-gray-500">Average Flesch reading ease</p>
        </CardContent>
      </Card>
    </div>
  )
}

function ContentCharts({ campaign }: { campaign: Campaign }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Content Type Distribution</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="h-[300px] flex items-center justify-center">
            <div className="relative w-[300px] h-[300px] rounded-full border-8 border-gray-100">
              <div className="absolute inset-0 border-t-[60px] border-r-[60px] border-b-[60px] border-l-[60px] border-t-blue-500 border-r-green-500 border-b-purple-500 border-l-yellow-500 rounded-full"></div>
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                <div className="text-sm font-medium">Total</div>
                <div className="text-3xl font-bold">12</div>
                <div className="text-xs text-gray-500">pieces</div>
              </div>
            </div>
            <div className="ml-8 space-y-4">
              <div className="flex items-center">
                <div className="w-4 h-4 bg-blue-500 rounded-full mr-3"></div>
                <div>
                  <div className="font-medium">Blog Posts</div>
                  <div className="text-sm text-gray-500">5 pieces (42%)</div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-green-500 rounded-full mr-3"></div>
                <div>
                  <div className="font-medium">Social Media</div>
                  <div className="text-sm text-gray-500">4 pieces (33%)</div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-purple-500 rounded-full mr-3"></div>
                <div>
                  <div className="font-medium">Email Content</div>
                  <div className="text-sm text-gray-500">2 pieces (17%)</div>
                </div>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-yellow-500 rounded-full mr-3"></div>
                <div>
                  <div className="font-medium">Landing Page</div>
                  <div className="text-sm text-gray-500">1 piece (8%)</div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Content Quality Metrics</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Readability</span>
                  <span className="font-medium">82/100</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div className="bg-blue-500 h-2.5 rounded-full" style={{ width: "82%" }}></div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Keyword Optimization</span>
                  <span className="font-medium">78/100</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div className="bg-green-500 h-2.5 rounded-full" style={{ width: "78%" }}></div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Originality</span>
                  <span className="font-medium">95/100</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div className="bg-purple-500 h-2.5 rounded-full" style={{ width: "95%" }}></div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Engagement Potential</span>
                  <span className="font-medium">88/100</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div className="bg-yellow-500 h-2.5 rounded-full" style={{ width: "88%" }}></div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Topic Coverage</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="h-[200px] flex items-center justify-center">
              <svg viewBox="0 0 300 200" className="w-full h-full">
                {/* Radar chart background */}
                <circle cx="150" cy="100" r="80" fill="none" stroke="#eee" strokeWidth="1" />
                <circle cx="150" cy="100" r="60" fill="none" stroke="#eee" strokeWidth="1" />
                <circle cx="150" cy="100" r="40" fill="none" stroke="#eee" strokeWidth="1" />
                <circle cx="150" cy="100" r="20" fill="none" stroke="#eee" strokeWidth="1" />

                <line x1="150" y1="20" x2="150" y2="180" stroke="#eee" strokeWidth="1" />
                <line x1="70" y1="100" x2="230" y2="100" stroke="#eee" strokeWidth="1" />
                <line x1="90" y1="40" x2="210" y2="160" stroke="#eee" strokeWidth="1" />
                <line x1="90" y1="160" x2="210" y2="40" stroke="#eee" strokeWidth="1" />

                {/* Radar chart data */}
                <path
                  d="M150,30 L210,80 L190,150 L110,150 L90,80 Z"
                  fill="rgba(59, 130, 246, 0.2)"
                  stroke="#3b82f6"
                  strokeWidth="2"
                />

                {/* Data points */}
                <circle cx="150" cy="30" r="4" fill="#3b82f6" />
                <circle cx="210" cy="80" r="4" fill="#3b82f6" />
                <circle cx="190" cy="150" r="4" fill="#3b82f6" />
                <circle cx="110" cy="150" r="4" fill="#3b82f6" />
                <circle cx="90" cy="80" r="4" fill="#3b82f6" />

                {/* Labels */}
                <text x="150" y="15" textAnchor="middle" fontSize="10" fill="#666">
                  Digital Marketing
                </text>
                <text x="225" y="80" textAnchor="start" fontSize="10" fill="#666">
                  Content Strategy
                </text>
                <text x="190" y="170" textAnchor="middle" fontSize="10" fill="#666">
                  Social Media
                </text>
                <text x="110" y="170" textAnchor="middle" fontSize="10" fill="#666">
                  Analytics
                </text>
                <text x="75" y="80" textAnchor="end" fontSize="10" fill="#666">
                  Customer Engagement
                </text>
              </svg>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function ContentData({ campaign }: { campaign: Campaign }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Generated Content Summary</CardTitle>
      </CardHeader>
      <CardContent className="p-4">
        <div className="border rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left">Title</th>
                <th className="px-4 py-2 text-left">Type</th>
                <th className="px-4 py-2 text-left">Word Count</th>
                <th className="px-4 py-2 text-left">Quality Score</th>
                <th className="px-4 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="px-4 py-3 font-medium">10 Digital Marketing Trends for 2025</td>
                <td className="px-4 py-3">
                  <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Blog Post</Badge>
                </td>
                <td className="px-4 py-3">1,250</td>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <span className="font-medium mr-2">92/100</span>
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div className="bg-green-500 h-1.5 rounded-full" style={{ width: "92%" }}></div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Button variant="outline" size="sm" className="h-8 px-2 text-xs">
                    View
                  </Button>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">How to Optimize Your Content Strategy</td>
                <td className="px-4 py-3">
                  <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Blog Post</Badge>
                </td>
                <td className="px-4 py-3">980</td>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <span className="font-medium mr-2">88/100</span>
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div className="bg-green-500 h-1.5 rounded-full" style={{ width: "88%" }}></div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Button variant="outline" size="sm" className="h-8 px-2 text-xs">
                    View
                  </Button>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Boost Your Social Media Engagement</td>
                <td className="px-4 py-3">
                  <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Social Media</Badge>
                </td>
                <td className="px-4 py-3">320</td>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <span className="font-medium mr-2">85/100</span>
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div className="bg-green-500 h-1.5 rounded-full" style={{ width: "85%" }}></div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Button variant="outline" size="sm" className="h-8 px-2 text-xs">
                    View
                  </Button>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Monthly Newsletter: Industry Insights</td>
                <td className="px-4 py-3">
                  <Badge className="bg-purple-100 text-purple-800 hover:bg-purple-100">Email</Badge>
                </td>
                <td className="px-4 py-3">650</td>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <span className="font-medium mr-2">90/100</span>
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div className="bg-green-500 h-1.5 rounded-full" style={{ width: "90%" }}></div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Button variant="outline" size="sm" className="h-8 px-2 text-xs">
                    View
                  </Button>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Transform Your Marketing Strategy</td>
                <td className="px-4 py-3">
                  <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">Landing Page</Badge>
                </td>
                <td className="px-4 py-3">850</td>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <span className="font-medium mr-2">94/100</span>
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div className="bg-green-500 h-1.5 rounded-full" style={{ width: "94%" }}></div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Button variant="outline" size="sm" className="h-8 px-2 text-xs">
                    View
                  </Button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

function GeneratedContent({ campaign }: { campaign: Campaign }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center justify-between">
            <span>10 Digital Marketing Trends for 2025</span>
            <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Blog Post</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="prose max-w-none">
            <h2>10 Digital Marketing Trends for 2025</h2>

            <p>
              As we approach 2025, the digital marketing landscape continues to evolve at a rapid pace. Staying ahead of
              emerging trends is crucial for businesses looking to maintain a competitive edge. Here are the top 10
              digital marketing trends that will shape the industry in 2025:
            </p>

            <h3>1. AI-Powered Personalization at Scale</h3>
            <p>
              Artificial intelligence will enable hyper-personalized marketing campaigns that adapt in real-time to
              individual user behaviors and preferences. Expect to see more sophisticated recommendation engines and
              dynamic content that changes based on user interaction patterns.
            </p>

            <h3>2. Voice Search Optimization</h3>
            <p>
              With the continued growth of smart speakers and voice assistants, optimizing content for voice search will
              become a standard practice. Marketers will need to focus on conversational keywords and providing direct
              answers to common questions.
            </p>

            <h3>3. Immersive AR/VR Experiences</h3>
            <p>
              Augmented and virtual reality will move beyond gaming to become powerful marketing tools. Brands will
              create immersive experiences that allow customers to visualize products in their own environments before
              purchasing.
            </p>

            <p>
              <em>... [Content continues] ...</em>
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center justify-between">
            <span>Boost Your Social Media Engagement</span>
            <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Social Media</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="prose max-w-none">
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <h3 className="text-lg font-bold mb-2">📈 Ready to skyrocket your social media engagement?</h3>

              <p>Try these 5 proven strategies that are working RIGHT NOW:</p>

              <ol className="list-decimal pl-5 space-y-2">
                <li>
                  <strong>Create interactive content</strong> - Polls, quizzes, and questions boost engagement by 2x
                </li>
                <li>
                  <strong>Leverage user-generated content</strong> - Authentic posts from real customers build trust
                </li>
                <li>
                  <strong>Optimize posting times</strong> - Our data shows Tuesdays and Thursdays at 10am-2pm get the
                  highest engagement
                </li>
                <li>
                  <strong>Respond quickly to comments</strong> - Aim for under 1 hour to keep conversations going
                </li>
                <li>
                  <strong>Use trending audio and hashtags</strong> - But only when relevant to your brand!
                </li>
              </ol>

              <p className="mt-4">Which strategy will you try first? Comment below! 👇</p>

              <p className="text-sm text-gray-500 mt-4">#SocialMediaTips #DigitalMarketing #EngagementStrategies</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
