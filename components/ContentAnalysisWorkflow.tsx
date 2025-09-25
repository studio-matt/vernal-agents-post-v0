"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Database,
  Code,
  Network,
  Brain,
  FileText,
  Info,
  Settings,
  Lightbulb,
  ArrowRight,
  ChevronRight,
  Download,
  ExternalLink,
  List,
  LinkIcon,
} from "lucide-react"
import Link from "next/link"

export function ContentAnalysisWorkflow() {
  const [activeTab, setActiveTab] = useState("overview")
  const [showTableOfContents, setShowTableOfContents] = useState(true)

  // Function to create anchor links
  const createAnchorLink = (id: string) => {
    return `#${id}`
  }

  // Function to copy anchor link to clipboard
  const copyAnchorLink = (id: string) => {
    const url = `${window.location.origin}${window.location.pathname}${createAnchorLink(id)}`
    navigator.clipboard
      .writeText(url)
      .then(() => {
        alert("Link copied to clipboard!")
      })
      .catch((err) => {
        console.error("Could not copy text: ", err)
      })
  }

  // Table of contents data
  const tableOfContents = {
    overview: [
      { id: "workflow-overview", title: "Workflow Overview" },
      { id: "key-concepts", title: "Key Concepts and Terminology" },
    ],
    extraction: [
      { id: "information-extraction", title: "Information Extraction" },
      { id: "extraction-parameters", title: "Extraction Parameters" },
      { id: "extraction-best-practices", title: "Best Practices" },
    ],
    preprocessing: [
      { id: "text-preprocessing", title: "Text Preprocessing" },
      { id: "preprocessing-parameters", title: "Preprocessing Parameters" },
      { id: "preprocessing-best-practices", title: "Best Practices" },
    ],
    entity: [
      { id: "entity-recognition", title: "Entity Recognition" },
      { id: "entity-parameters", title: "Entity Recognition Parameters" },
      { id: "entity-best-practices", title: "Best Practices" },
    ],
    topic: [
      { id: "topic-modeling", title: "Topic Modeling" },
      { id: "topic-parameters", title: "Topic Modeling Parameters" },
      { id: "topic-best-practices", title: "Best Practices" },
    ],
    content: [
      { id: "content-generation", title: "Content Generation" },
      { id: "content-parameters", title: "Content Generation Parameters" },
      { id: "content-best-practices", title: "Best Practices" },
    ],
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-semibold">Content Analysis Workflow Guide</h2>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            className="flex items-center"
            onClick={() => setShowTableOfContents(!showTableOfContents)}
          >
            <List className="w-4 h-4 mr-2" />
            {showTableOfContents ? "Hide" : "Show"} Table of Contents
          </Button>
          <Button variant="outline" className="flex items-center">
            <Download className="w-4 h-4 mr-2" />
            Download Guide
          </Button>
          <Link href="https://example.com/documentation" target="_blank">
            <Button variant="outline" className="flex items-center">
              <ExternalLink className="w-4 h-4 mr-2" />
              Full Documentation
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {showTableOfContents && (
          <div className="md:col-span-1">
            <Card className="sticky top-4">
              <CardHeader>
                <CardTitle className="text-lg">Table of Contents</CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                <nav className="space-y-4">
                  {Object.entries(tableOfContents).map(([tab, sections]) => (
                    <div key={tab} className="space-y-2">
                      <h4 className="font-medium text-sm uppercase text-gray-500">
                        {tab === "overview"
                          ? "Overview"
                          : tab === "extraction"
                            ? "Information Extraction"
                            : tab === "preprocessing"
                              ? "Preprocessing"
                              : tab === "entity"
                                ? "Entity Recognition"
                                : tab === "topic"
                                  ? "Topic Modeling"
                                  : "Content Generation"}
                      </h4>
                      <ul className="space-y-1 pl-2">
                        {sections.map((section) => (
                          <li key={section.id}>
                            <a
                              href={createAnchorLink(section.id)}
                              className="text-sm text-blue-600 hover:underline flex items-center"
                              onClick={() => {
                                setActiveTab(tab)
                                setTimeout(() => {
                                  document.getElementById(section.id)?.scrollIntoView({ behavior: "smooth" })
                                }, 100)
                              }}
                            >
                              <ChevronRight className="w-3 h-3 mr-1" />
                              {section.title}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </nav>
              </CardContent>
            </Card>
          </div>
        )}

        <div className={showTableOfContents ? "md:col-span-3" : "md:col-span-4"}>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full mb-6 grid grid-cols-2 md:grid-cols-6">
              <TabsTrigger value="overview" className="flex items-center">
                <Info className="h-4 w-4 mr-2" />
                <span>Overview</span>
              </TabsTrigger>
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
              <TabsTrigger value="topic" className="flex items-center">
                <Brain className="h-4 w-4 mr-2" />
                <span>Topic Modeling</span>
              </TabsTrigger>
              <TabsTrigger value="content" className="flex items-center">
                <FileText className="h-4 w-4 mr-2" />
                <span>Content Generation</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview">
              <WorkflowOverview copyAnchorLink={copyAnchorLink} />
            </TabsContent>

            <TabsContent value="extraction">
              <ExtractionWorkflow copyAnchorLink={copyAnchorLink} />
            </TabsContent>

            <TabsContent value="preprocessing">
              <PreprocessingWorkflow copyAnchorLink={copyAnchorLink} />
            </TabsContent>

            <TabsContent value="entity">
              <EntityRecognitionWorkflow copyAnchorLink={copyAnchorLink} />
            </TabsContent>

            <TabsContent value="topic">
              <TopicModelingWorkflow copyAnchorLink={copyAnchorLink} />
            </TabsContent>

            <TabsContent value="content">
              <ContentGenerationWorkflow copyAnchorLink={copyAnchorLink} />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

interface SectionProps {
  copyAnchorLink: (id: string) => void
}

function SectionHeader({
  id,
  title,
  description,
  copyAnchorLink,
}: { id: string; title: string; description?: string; copyAnchorLink: (id: string) => void }) {
  return (
    <div className="flex items-start justify-between" id={id}>
      <div>
        <h3 className="text-xl font-semibold">{title}</h3>
        {description && <p className="text-gray-600 mt-1">{description}</p>}
      </div>
      <button
        onClick={() => copyAnchorLink(id)}
        className="text-gray-400 hover:text-gray-600 focus:outline-none"
        title="Copy link to this section"
      >
        <LinkIcon className="w-4 h-4" />
      </button>
    </div>
  )
}

function WorkflowOverview({ copyAnchorLink }: SectionProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <SectionHeader
            id="workflow-overview"
            title="Content Analysis Workflow Overview"
            description="Understanding the end-to-end process of content analysis and generation"
            copyAnchorLink={copyAnchorLink}
          />
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="relative">
            <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gray-200"></div>

            <div className="relative z-10 flex mb-8">
              <div className="flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 text-blue-600">
                <Database className="w-8 h-8" />
              </div>
              <div className="ml-4 flex-1">
                <h3 className="text-xl font-semibold">1. Information Extraction</h3>
                <p className="text-gray-600 mt-1">
                  Extract and preprocess content from the selected sources, including web scraping, content extraction,
                  and initial organization.
                </p>
                <div className="mt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex items-center"
                    onClick={() => document.querySelector('[data-value="extraction"]')?.click()}
                  >
                    Learn More <ChevronRight className="ml-1 w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>

            <div className="relative z-10 flex mb-8">
              <div className="flex items-center justify-center w-16 h-16 rounded-full bg-green-100 text-green-600">
                <Code className="w-8 h-8" />
              </div>
              <div className="ml-4 flex-1">
                <h3 className="text-xl font-semibold">2. Preprocessing</h3>
                <p className="text-gray-600 mt-1">
                  Clean and normalize the extracted text through tokenization, stopword removal, lemmatization, and
                  other text normalization techniques.
                </p>
                <div className="mt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex items-center"
                    onClick={() => document.querySelector('[data-value="preprocessing"]')?.click()}
                  >
                    Learn More <ChevronRight className="ml-1 w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>

            <div className="relative z-10 flex mb-8">
              <div className="flex items-center justify-center w-16 h-16 rounded-full bg-purple-100 text-purple-600">
                <Network className="w-8 h-8" />
              </div>
              <div className="ml-4 flex-1">
                <h3 className="text-xl font-semibold">3. Entity Recognition</h3>
                <p className="text-gray-600 mt-1">
                  Identify and extract key entities such as people, organizations, locations, and dates from the
                  processed text to understand key components.
                </p>
                <div className="mt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex items-center"
                    onClick={() => document.querySelector('[data-value="entity"]')?.click()}
                  >
                    Learn More <ChevronRight className="ml-1 w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>

            <div className="relative z-10 flex mb-8">
              <div className="flex items-center justify-center w-16 h-16 rounded-full bg-yellow-100 text-yellow-600">
                <Brain className="w-8 h-8" />
              </div>
              <div className="ml-4 flex-1">
                <h3 className="text-xl font-semibold">4. Topic Modeling</h3>
                <p className="text-gray-600 mt-1">
                  Discover key themes and topics within the content using advanced algorithms like LDA, BERTopic, and
                  other statistical methods.
                </p>
                <div className="mt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex items-center"
                    onClick={() => document.querySelector('[data-value="topic"]')?.click()}
                  >
                    Learn More <ChevronRight className="ml-1 w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>

            <div className="relative z-10 flex">
              <div className="flex items-center justify-center w-16 h-16 rounded-full bg-red-100 text-red-600">
                <FileText className="w-8 h-8" />
              </div>
              <div className="ml-4 flex-1">
                <h3 className="text-xl font-semibold">5. Content Generation</h3>
                <p className="text-gray-600 mt-1">
                  Create new, optimized content based on the analysis results, including blog posts, social media
                  content, and other marketing materials.
                </p>
                <div className="mt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex items-center"
                    onClick={() => document.querySelector('[data-value="content"]')?.click()}
                  >
                    Learn More <ChevronRight className="ml-1 w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="p-4">
              <div className="flex">
                <Lightbulb className="w-6 h-6 text-blue-600 mr-3 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-blue-800">Pro Tip: Workflow Optimization</h4>
                  <p className="text-blue-700 text-sm mt-1">
                    For best results, complete each step sequentially and review the outputs before proceeding to the
                    next step. This ensures that any issues are caught early in the process and allows for parameter
                    adjustments to optimize results.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <SectionHeader
            id="key-concepts"
            title="Key Concepts and Terminology"
            description="Essential terms and concepts to understand the content analysis process"
            copyAnchorLink={copyAnchorLink}
          />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold text-lg">Natural Language Processing (NLP)</h4>
                <p className="text-gray-600 text-sm">
                  A field of artificial intelligence that gives computers the ability to understand text and spoken
                  words in much the same way human beings can.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-lg">Tokenization</h4>
                <p className="text-gray-600 text-sm">
                  The process of breaking down text into smaller units called tokens, which can be words, characters, or
                  subwords.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-lg">Lemmatization</h4>
                <p className="text-gray-600 text-sm">
                  The process of reducing words to their base or dictionary form (lemma), e.g., "running" to "run".
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-lg">Named Entity Recognition (NER)</h4>
                <p className="text-gray-600 text-sm">
                  The process of identifying and classifying named entities in text into predefined categories such as
                  person names, organizations, locations, etc.
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <h4 className="font-semibold text-lg">Topic Modeling</h4>
                <p className="text-gray-600 text-sm">
                  A type of statistical model for discovering abstract "topics" that occur in a collection of documents.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-lg">Latent Dirichlet Allocation (LDA)</h4>
                <p className="text-gray-600 text-sm">
                  A generative statistical model that allows sets of observations to be explained by unobserved groups
                  that explain why some parts of the data are similar.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-lg">BERTopic</h4>
                <p className="text-gray-600 text-sm">
                  A topic modeling technique that leverages BERT embeddings and a class-based TF-IDF to create dense
                  clusters allowing for easily interpretable topics.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-lg">Content Optimization</h4>
                <p className="text-gray-600 text-sm">
                  The process of improving content to increase its visibility, engagement, and conversion rates through
                  various techniques like keyword optimization and readability improvements.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function ExtractionWorkflow({ copyAnchorLink }: SectionProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <SectionHeader
            id="information-extraction"
            title="Information Extraction"
            description="The process of extracting structured information from unstructured or semi-structured sources"
            copyAnchorLink={copyAnchorLink}
          />
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="prose max-w-none">
            <p>
              Information extraction is the first step in the content analysis workflow. It involves collecting and
              organizing content from various sources, such as websites, documents, or databases. This step is crucial
              as it forms the foundation for all subsequent analysis.
            </p>

            <h3>Key Components of Information Extraction</h3>

            <ol>
              <li>
                <strong>Web Scraping</strong>: Automated extraction of data from websites, including text, images, and
                metadata.
              </li>
              <li>
                <strong>Content Parsing</strong>: Breaking down the extracted content into manageable and structured
                formats.
              </li>
              <li>
                <strong>Data Cleaning</strong>: Initial cleaning of the extracted data to remove HTML tags, scripts, and
                other non-content elements.
              </li>
              <li>
                <strong>Content Organization</strong>: Organizing the extracted content into a structured format for
                further processing.
              </li>
            </ol>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
            <h3 className="text-lg font-semibold mb-2">Information Extraction Process Flow</h3>

            <div className="flex flex-col md:flex-row gap-4 items-start">
              <div className="flex-1 flex flex-col items-center text-center p-3 bg-white rounded-lg border border-gray-200">
                <Database className="w-8 h-8 text-blue-500 mb-2" />
                <h4 className="font-medium">Source Selection</h4>
                <p className="text-sm text-gray-600 mt-1">Choose URLs or keywords to analyze</p>
                <ArrowRight className="w-5 h-5 text-gray-400 my-2 transform rotate-90 md:rotate-0" />
              </div>

              <div className="flex-1 flex flex-col items-center text-center p-3 bg-white rounded-lg border border-gray-200">
                <Database className="w-8 h-8 text-blue-500 mb-2" />
                <h4 className="font-medium">Data Fetching</h4>
                <p className="text-sm text-gray-600 mt-1">Retrieve content from sources</p>
                <ArrowRight className="w-5 h-5 text-gray-400 my-2 transform rotate-90 md:rotate-0" />
              </div>

              <div className="flex-1 flex flex-col items-center text-center p-3 bg-white rounded-lg border border-gray-200">
                <Database className="w-8 h-8 text-blue-500 mb-2" />
                <h4 className="font-medium">Content Extraction</h4>
                <p className="text-sm text-gray-600 mt-1">Extract relevant content</p>
                <ArrowRight className="w-5 h-5 text-gray-400 my-2 transform rotate-90 md:rotate-0" />
              </div>

              <div className="flex-1 flex flex-col items-center text-center p-3 bg-white rounded-lg border border-gray-200">
                <Database className="w-8 h-8 text-blue-500 mb-2" />
                <h4 className="font-medium">Initial Cleaning</h4>
                <p className="text-sm text-gray-600 mt-1">Remove non-content elements</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <SectionHeader
            id="extraction-parameters"
            title="Information Extraction Parameters"
            description="Configurable settings that control the extraction process"
            copyAnchorLink={copyAnchorLink}
          />
        </CardHeader>
        <CardContent>
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="web-scraping-depth">
              <AccordionTrigger>
                <div className="flex items-center">
                  <span>Web Scraping Depth</span>
                  <Badge className="ml-2 bg-blue-100 text-blue-800">Configuration</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-4">
                  <p className="text-gray-600">
                    Controls how many clicks away from the homepage the scraper will follow links.
                  </p>

                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-medium mb-2">Settings Impact:</h4>
                    <ul className="space-y-2">
                      <li className="flex items-start">
                        <span className="font-medium mr-2">1:</span>
                        <span>Only the homepage (great for news sites).</span>
                      </li>
                      <li className="flex items-start">
                        <span className="font-medium mr-2">2:</span>
                        <span>Homepage and direct links (good for small websites).</span>
                      </li>
                      <li className="flex items-start">
                        <span className="font-medium mr-2">3:</span>
                        <span>Homepage → Category → Product (common for e-commerce).</span>
                      </li>
                      <li className="flex items-start">
                        <span className="font-medium mr-2">4-5:</span>
                        <span>Deep crawling (for comprehensive analysis but may take longer).</span>
                      </li>
                    </ul>
                  </div>

                  <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                    <div className="flex">
                      <Lightbulb className="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0" />
                      <p className="text-yellow-800 text-sm">
                        <strong>Recommendation:</strong> Start with a depth of 2 for initial analysis, then increase if
                        needed for more comprehensive results.
                      </p>
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="max-pages">
              <AccordionTrigger>
                <div className="flex items-center">
                  <span>Maximum Pages</span>
                  <Badge className="ml-2 bg-blue-100 text-blue-800">Configuration</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-4">
                  <p className="text-gray-600">
                    Limits the total number of pages that will be scraped during the extraction process.
                  </p>

                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-medium mb-2">Settings Impact:</h4>
                    <ul className="space-y-2">
                      <li className="flex items-start">
                        <span className="font-medium mr-2">Low (50):</span>
                        <span>Good for quick tests (like sampling a blog).</span>
                      </li>
                      <li className="flex items-start">
                        <span className="font-medium mr-2">Medium (100-500):</span>
                        <span>Balanced approach for most websites.</span>
                      </li>
                      <li className="flex items-start">
                        <span className="font-medium mr-2">High (1000+):</span>
                        <span>Full site crawl (might take hours).</span>
                      </li>
                    </ul>
                  </div>

                  <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                    <div className="flex">
                      <Lightbulb className="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0" />
                      <p className="text-yellow-800 text-sm">
                        <strong>Recommendation:</strong> Set to 100 to avoid overwhelming small websites. For larger
                        sites, consider increasing gradually while monitoring performance.
                      </p>
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="batch-size">
              <AccordionTrigger>
                <div className="flex items-center">
                  <span>Batch Size</span>
                  <Badge className="ml-2 bg-blue-100 text-blue-800">Configuration</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-4">
                  <p className="text-gray-600">
                    Determines how many pages are processed simultaneously during extraction.
                  </p>

                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-medium mb-2">Settings Impact:</h4>
                    <ul className="space-y-2">
                      <li className="flex items-start">
                        <span className="font-medium mr-2">Small (5-10):</span>
                        <span>Gentle on servers (avoids bans).</span>
                      </li>
                      <li className="flex items-start">
                        <span className="font-medium mr-2">Medium (20-50):</span>
                        <span>Balanced approach for most websites.</span>
                      </li>
                      <li className="flex items-start">
                        <span className="font-medium mr-2">Large (100+):</span>
                        <span>Fast but risky (might get blocked).</span>
                      </li>
                    </ul>
                  </div>

                  <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                    <div className="flex">
                      <Lightbulb className="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0" />
                      <p className="text-yellow-800 text-sm">
                        <strong>Recommendation:</strong> Like checkout lanes – more lanes speed things up but annoy the
                        store manager. Start with 10 for most websites to avoid being blocked.
                      </p>
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="include-images">
              <AccordionTrigger>
                <div className="flex items-center">
                  <span>Include Images</span>
                  <Badge className="ml-2 bg-green-100 text-green-800">Toggle</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-4">
                  <p className="text-gray-600">Determines whether images are extracted along with text content.</p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-medium mb-2">When to Enable:</h4>
                      <ul className="space-y-1 text-sm">
                        <li>• Visual content analysis is important</li>
                        <li>• Creating image-heavy content</li>
                        <li>• Analyzing product images</li>
                        <li>• Visual brand analysis</li>
                      </ul>
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-medium mb-2">When to Disable:</h4>
                      <ul className="space-y-1 text-sm">
                        <li>• Text-only analysis is sufficient</li>
                        <li>• Limited storage capacity</li>
                        <li>• Faster processing is needed</li>
                        <li>• Bandwidth constraints</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="include-links">
              <AccordionTrigger>
                <div className="flex items-center">
                  <span>Include Links</span>
                  <Badge className="ml-2 bg-green-100 text-green-800">Toggle</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-4">
                  <p className="text-gray-600">Determines whether hyperlinks are extracted and analyzed.</p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-medium mb-2">When to Enable:</h4>
                      <ul className="space-y-1 text-sm">
                        <li>• Analyzing site structure</li>
                        <li>• Examining external references</li>
                        <li>• SEO analysis</li>
                        <li>• Content relationship mapping</li>
                      </ul>
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-medium mb-2">When to Disable:</h4>
                      <ul className="space-y-1 text-sm">
                        <li>• Pure content analysis only</li>
                        <li>• Simplified data structure needed</li>
                        <li>• Reducing extraction complexity</li>
                        <li>• Focusing on on-page content only</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>

      <Card className="bg-blue-50 border-blue-200">
        <CardHeader>
          <SectionHeader
            id="extraction-best-practices"
            title="Best Practices for Information Extraction"
            description="Guidelines for effective and ethical information extraction"
            copyAnchorLink={copyAnchorLink}
          />
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex">
            <Settings className="w-8 h-8 text-blue-600 mr-4 flex-shrink-0" />
            <div>
              <ul className="mt-4 space-y-3">
                <li className="flex items-start">
                  <div className="bg-blue-200 rounded-full p-1 mr-3 mt-0.5">
                    <ChevronRight className="w-3 h-3 text-blue-800" />
                  </div>
                  <p className="text-blue-700">
                    <strong>Respect robots.txt:</strong> Always configure your extraction to respect website robots.txt
                    files and terms of service.
                  </p>
                </li>
                <li className="flex items-start">
                  <div className="bg-blue-200 rounded-full p-1 mr-3 mt-0.5">
                    <ChevronRight className="w-3 h-3 text-blue-800" />
                  </div>
                  <p className="text-blue-700">
                    <strong>Start small and scale:</strong> Begin with a small batch size and depth, then gradually
                    increase as needed.
                  </p>
                </li>
                <li className="flex items-start">
                  <div className="bg-blue-200 rounded-full p-1 mr-3 mt-0.5">
                    <ChevronRight className="w-3 h-3 text-blue-800" />
                  </div>
                  <p className="text-blue-700">
                    <strong>Add delays between requests:</strong> Implement reasonable delays between requests to avoid
                    overwhelming servers.
                  </p>
                </li>
                <li className="flex items-start">
                  <div className="bg-blue-200 rounded-full p-1 mr-3 mt-0.5">
                    <ChevronRight className="w-3 h-3 text-blue-800" />
                  </div>
                  <p className="text-blue-700">
                    <strong>Focus on relevant content:</strong> Configure extraction to target the most relevant content
                    for your analysis goals.
                  </p>
                </li>
                <li className="flex items-start">
                  <div className="bg-blue-200 rounded-full p-1 mr-3 mt-0.5">
                    <ChevronRight className="w-3 h-3 text-blue-800" />
                  </div>
                  <p className="text-blue-700">
                    <strong>Monitor extraction quality:</strong> Regularly check the quality of extracted content to
                    ensure it meets your analysis needs.
                  </p>
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function PreprocessingWorkflow({ copyAnchorLink }: SectionProps) {
  // Implementation for preprocessing workflow
  // This would be similar to the ExtractionWorkflow component
  return (
    <div className="space-y-6">
      {/* Content for preprocessing workflow */}
      <p>Preprocessing workflow content would go here</p>
    </div>
  )
}

function EntityRecognitionWorkflow({ copyAnchorLink }: SectionProps) {
  // Implementation for entity recognition workflow
  // This would be similar to the ExtractionWorkflow component
  return (
    <div className="space-y-6">
      {/* Content for entity recognition workflow */}
      <p>Entity recognition workflow content would go here</p>
    </div>
  )
}

function TopicModelingWorkflow({ copyAnchorLink }: SectionProps) {
  // Implementation for topic modeling workflow
  // This would be similar to the ExtractionWorkflow component
  return (
    <div className="space-y-6">
      {/* Content for topic modeling workflow */}
      <p>Topic modeling workflow content would go here</p>
    </div>
  )
}

function ContentGenerationWorkflow({ copyAnchorLink }: SectionProps) {
  // Implementation for content generation workflow
  // This would be similar to the ExtractionWorkflow component
  return (
    <div className="space-y-6">
      {/* Content for content generation workflow */}
      <p>Content generation workflow content would go here</p>
    </div>
  )
}
