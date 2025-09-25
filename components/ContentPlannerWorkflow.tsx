"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Globe,
  FileText,
  Layers,
  Cpu,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  Eye,
  Database,
  Code,
  Brain,
  Settings,
  Network,
} from "lucide-react"
import type { Campaign } from "./ContentPlannerCampaign"
import { ErrorDialog } from "./ErrorDialog"
// Add this import at the top of the file
import { ParameterAdjustmentSliders } from "./ParameterAdjustmentSliders"
import Link from "next/link"

interface ContentPlannerWorkflowProps {
  selectedCampaign: Campaign | null
  onStartAnalysis: (campaignId: string) => Promise<void>
}

export function ContentPlannerWorkflow({ selectedCampaign, onStartAnalysis }: ContentPlannerWorkflowProps) {
  const router = useRouter()
  const [activeStep, setActiveStep] = useState(0)
  const [activeSubStep, setActiveSubStep] = useState(0)
  const [isProcessing, setIsProcessing] = useState(false)

  const [stepStatus, setStepStatus] = useState<("idle" | "processing" | "completed" | "error")[]>([
    "idle",
    "idle",
    "idle",
    "idle",
  ])
  const [subStepStatus, setSubStepStatus] = useState<{
    [key: number]: ("idle" | "processing" | "completed" | "error")[]
  }>({
    0: ["idle", "idle", "idle"], // Information Extraction sub-steps
    1: ["idle", "idle", "idle"], // Topic Modeling sub-steps
  })
  const [showResults, setShowResults] = useState<{
    [key: number]: boolean[]
  }>({
    0: [false, false, false], // Information Extraction sub-steps results
    1: [false, false, false], // Topic Modeling sub-steps results
  })
  const [error, setError] = useState<{ isOpen: boolean; message: string }>({ isOpen: false, message: "" })

  // Add this state inside the ContentPlannerWorkflow component
  const [modelParameters, setModelParameters] = useState<{
    decisionTree: {
      entropyCutoff: number
      depthCutoff: number
      supportCutoff: number
    }
    maxent: {
      maxIter: number
      algorithm: "gis" | "iis"
    }
    posTagging: {
      backoff: string
      cutoff: number
    }
    lemmatization: {
      pos: string
    }
    tokenization: {
      abbrevTypes: string
      collocations: boolean
    }
  }>({
    entropyCutoff: 0.05,
    depthCutoff: 5,
    supportCutoff: 0.1,
    maxent: {
      maxIter: 100,
      algorithm: "gis",
    },
    posTagging: {
      backoff: "DefaultTagger",
      cutoff: 5,
    },
    lemmatization: {
      pos: "n",
    },
    tokenization: {
      abbrevTypes: "Dr., Prof., Inc., Ltd.",
      collocations: true,
    },
  })

  const steps = [
    {
      title: "Information Extraction",
      icon: Globe,
      description: "Extract and preprocess content from the selected sources",
      subSteps: [
        {
          title: "Web Scraping",
          icon: Database,
          description: "Extract content from URLs or process keywords",
          details: [
            "Fetch HTML content from provided URLs",
            "Extract main text content and remove boilerplate",
            "Organize content for further processing",
          ],
        },
        {
          title: "Preprocessing",
          icon: Code,
          description: "Apply lemmatization and stemming to normalize text",
          details: [
            "Tokenize text into words and sentences",
            "Apply lemmatization to reduce words to base forms",
            "Remove stop words and normalize text",
          ],
        },
        {
          title: "Entity Recognition",
          icon: Network,
          description: "Identify key entities within the content",
          details: [
            "Identify named entities (people, organizations, locations)",
            "Extract key phrases and concepts",
            "Build entity relationships map",
          ],
        },
      ],
    },
    {
      title: "Topic Modeling",
      icon: Layers,
      description: "Identify key topics and subtopics within the content",
      subSteps: [
        {
          title: "Input Preparation",
          icon: Database,
          description: "Process SAL content for topic modeling",
          details: [
            "Convert text to document-term matrix",
            "Apply TF-IDF transformation",
            "Prepare data structures for modeling algorithms",
          ],
        },
        {
          title: "Modeling",
          icon: Brain,
          description: "Apply LDA or BERTopic algorithms",
          details: [
            "Run Latent Dirichlet Allocation (LDA)",
            "Apply BERTopic for contextual topic modeling",
            "Generate initial topic clusters",
          ],
        },
        {
          title: "Parameter Adjustment",
          icon: Settings,
          description: "Fine-tune model parameters for optimal results",
          details: ["Adjust number of topics", "Tune hyperparameters for coherence", "Finalize topic model structure"],
        },
      ],
    },
    {
      title: "Content Analysis",
      icon: Cpu,
      description: "Analyze the extracted content and topics",
      subSteps: [],
    },
    {
      title: "Content Generation",
      icon: FileText,
      description: "Generate new content based on the analysis",
      subSteps: [],
    },
  ]

  // Add this function inside the ContentPlannerWorkflow component
  const handleParametersChange = (parameters: typeof modelParameters) => {
    setModelParameters(parameters)
    console.log("Parameters updated:", parameters)
    // In a real implementation, you would use these parameters to update the model
  }

  const closeErrorDialog = () => {
    setError({ isOpen: false, message: "" })
  }

  const handleStartAnalysis = async () => {
    if (!selectedCampaign) {
      setError({
        isOpen: true,
        message: "Please select a campaign before starting the analysis",
      })
      return
    }

    // For URL campaigns, check if URLs are provided
    if (selectedCampaign.type === "url" && (!selectedCampaign.urls || selectedCampaign.urls.length === 0)) {
      setError({
        isOpen: true,
        message:
          "The selected campaign does not have any URLs. Please edit the campaign to add URLs before starting the analysis.",
      })
      return
    }

    // For keyword campaigns, check if keywords are provided
    if (selectedCampaign.type === "keyword" && (!selectedCampaign.keywords || selectedCampaign.keywords.length === 0)) {
      setError({
        isOpen: true,
        message:
          "The selected campaign does not have any keywords. Please edit the campaign to add keywords before starting the analysis.",
      })
      return
    }

    setIsProcessing(true)
    setActiveStep(0)
    setActiveSubStep(0)
    setStepStatus(["processing", "idle", "idle", "idle"])

    // Reset all sub-step statuses
    setSubStepStatus({
      0: ["processing", "idle", "idle"],
      1: ["idle", "idle", "idle"],
    })

    // Reset all results views
    setShowResults({
      0: [false, false, false],
      1: [false, false, false],
    })

    try {
      // Process the first sub-step of the first step
      await processSubStep(0, 0)
    } catch (error) {
      // Handle error
      const newSubStepStatus = { ...subStepStatus }
      newSubStepStatus[0][0] = "error"
      setSubStepStatus(newSubStepStatus)
      setIsProcessing(false)

      setError({
        isOpen: true,
        message: "An error occurred while processing. Please try again.",
      })
    }
  }

  const processSubStep = async (stepIndex: number, subStepIndex: number) => {
    if (stepIndex >= steps.length) return
    if (stepIndex < 2 && subStepIndex >= steps[stepIndex].subSteps.length) return

    setIsProcessing(true)
    setActiveStep(stepIndex)
    setActiveSubStep(subStepIndex)

    // Update sub-step status to processing
    const newSubStepStatus = { ...subStepStatus }
    if (!newSubStepStatus[stepIndex]) {
      newSubStepStatus[stepIndex] = []
    }
    newSubStepStatus[stepIndex][subStepIndex] = "processing"
    setSubStepStatus(newSubStepStatus)

    // Simulate processing time
    await new Promise((resolve) => setTimeout(resolve, 2000))

    // Mark sub-step as completed
    newSubStepStatus[stepIndex][subStepIndex] = "completed"
    setSubStepStatus(newSubStepStatus)

    // If all sub-steps are completed, mark the main step as completed
    if (
      stepIndex < 2 &&
      newSubStepStatus[stepIndex].every((status) => status === "completed") &&
      newSubStepStatus[stepIndex].length === steps[stepIndex].subSteps.length
    ) {
      const newStepStatus = [...stepStatus]
      newStepStatus[stepIndex] = "completed"
      setStepStatus(newStepStatus)
    }

    setIsProcessing(false)
  }

  const handleContinueSubStep = async (stepIndex: number, subStepIndex: number) => {
    if (stepIndex >= steps.length) return
    if (stepIndex < 2 && subStepIndex >= steps[stepIndex].subSteps.length - 1) {
      // If this is the last sub-step of the current step, prepare to move to the next step
      if (stepIndex === 0) {
        // Move to Topic Modeling (first sub-step)
        const newStepStatus = [...stepStatus]
        newStepStatus[stepIndex] = "completed"
        newStepStatus[stepIndex + 1] = "processing"
        setStepStatus(newStepStatus)

        await processSubStep(stepIndex + 1, 0)
      } else if (stepIndex === 1) {
        // Move to Content Analysis (which launches a new page)
        const newStepStatus = [...stepStatus]
        newStepStatus[stepIndex] = "completed"
        newStepStatus[stepIndex + 1] = "completed"
        setStepStatus(newStepStatus)

        // Navigate to content analysis page
        router.push("/dashboard/content-analysis")
      }
    } else {
      // Move to the next sub-step
      await processSubStep(stepIndex, subStepIndex + 1)
    }
  }

  const handleReviewResults = (stepIndex: number, subStepIndex: number) => {
    const newShowResults = { ...showResults }
    if (!newShowResults[stepIndex]) {
      newShowResults[stepIndex] = []
    }
    newShowResults[stepIndex][subStepIndex] = true
    setShowResults(newShowResults)
  }

  const handleGenerateContent = () => {
    // Navigate to the content generation page
    router.push("/dashboard/content-generation")
  }

  const getStepIcon = (index: number) => {
    const Icon = steps[index].icon

    if (stepStatus[index] === "processing") {
      return <Loader2 className="w-6 h-6 animate-spin" />
    } else if (stepStatus[index] === "completed") {
      return <CheckCircle2 className="w-6 h-6 text-green-500" />
    } else if (stepStatus[index] === "error") {
      return <AlertCircle className="w-6 h-6 text-red-500" />
    }

    return <Icon className="w-6 h-6" />
  }

  const getSubStepIcon = (stepIndex: number, subStepIndex: number) => {
    if (!steps[stepIndex].subSteps[subStepIndex]) return null

    const Icon = steps[stepIndex].subSteps[subStepIndex].icon

    if (subStepStatus[stepIndex]?.[subStepIndex] === "processing") {
      return <Loader2 className="w-5 h-5 animate-spin" />
    } else if (subStepStatus[stepIndex]?.[subStepIndex] === "completed") {
      return <CheckCircle2 className="w-5 h-5 text-green-500" />
    } else if (subStepStatus[stepIndex]?.[subStepIndex] === "error") {
      return <AlertCircle className="w-5 h-5 text-red-500" />
    }

    return <Icon className="w-5 h-5" />
  }

  const isStepActive = (index: number) => {
    return activeStep === index || stepStatus[index] === "completed" || stepStatus[index] === "processing"
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Content Analysis Workflow</h2>

      {selectedCampaign ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Selected Campaign: {selectedCampaign.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4">{selectedCampaign.description}</p>
              <div className="mb-4">
                <span className="font-medium">Type:</span>{" "}
                {selectedCampaign.type === "keyword" ? "Keywords/Phrases" : "URLs"}
              </div>

              {selectedCampaign.type === "keyword" && selectedCampaign.keywords && (
                <div className="mb-4">
                  <span className="font-medium">Keywords:</span>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedCampaign.keywords.map((keyword, index) => (
                      <div key={index} className="bg-secondary text-secondary-foreground px-3 py-1 rounded-full">
                        {keyword}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedCampaign.type === "url" && selectedCampaign.urls && (
                <div className="mb-4">
                  <span className="font-medium">URLs:</span>
                  <div className="space-y-2 mt-2">
                    {selectedCampaign.urls.map((url, index) => (
                      <div key={index} className="bg-secondary text-secondary-foreground p-2 rounded">
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          {url}
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-4">
            <h3 className="text-xl font-semibold">Workflow Steps</h3>

            <div className="space-y-4">
              {steps.map((step, index) => (
                <Card
                  key={index}
                  className={`transition-all ${activeStep === index ? "ring-2 ring-primary" : ""} ${
                    !isStepActive(index) ? "opacity-50" : ""
                  }`}
                >
                  <CardContent className="p-6">
                    <div className="flex items-start">
                      <div
                        className={`p-2 rounded-full mr-4 ${
                          stepStatus[index] === "completed"
                            ? "bg-green-100"
                            : stepStatus[index] === "processing"
                              ? "bg-blue-100"
                              : stepStatus[index] === "error"
                                ? "bg-red-100"
                                : "bg-secondary"
                        }`}
                      >
                        {getStepIcon(index)}
                      </div>
                      <div className="flex-1">
                        <h4 className="text-lg font-medium">{step.title}</h4>
                        <p className="text-gray-500 mt-1">{step.description}</p>

                        {/* Sub-steps for Information Extraction and Topic Modeling */}
                        {(index === 0 || index === 1) && isStepActive(index) && (
                          <div className="mt-4 space-y-4">
                            {/* Show Start Analysis button if this is the Information Extraction step and all sub-steps are idle */}
                            {index === 0 && subStepStatus[0]?.every((status) => status === "idle") && (
                              <Button
                                onClick={handleStartAnalysis}
                                disabled={isProcessing}
                                className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90 mb-4"
                              >
                                {isProcessing ? (
                                  <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Processing...
                                  </>
                                ) : (
                                  "Start Content Analysis"
                                )}
                              </Button>
                            )}
                            {step.subSteps.map((subStep, subIndex) => (
                              <Card
                                key={subIndex}
                                className={`border ${
                                  activeStep === index && activeSubStep === subIndex
                                    ? "border-primary"
                                    : "border-gray-200"
                                } ${
                                  subStepStatus[index]?.[subIndex] === "idle" &&
                                  subStepStatus[index]?.slice(0, subIndex).some((s) => s !== "completed")
                                    ? "opacity-50"
                                    : ""
                                }`}
                              >
                                <CardContent className="p-4">
                                  <div className="flex items-start">
                                    <div
                                      className={`p-1.5 rounded-full mr-3 ${
                                        subStepStatus[index]?.[subIndex] === "completed"
                                          ? "bg-green-100"
                                          : subStepStatus[index]?.[subIndex] === "processing"
                                            ? "bg-blue-100"
                                            : subStepStatus[index]?.[subIndex] === "error"
                                              ? "bg-red-100"
                                              : "bg-secondary"
                                      }`}
                                    >
                                      {getSubStepIcon(index, subIndex)}
                                    </div>
                                    <div className="flex-1">
                                      <h5 className="text-base font-medium">{subStep.title}</h5>
                                      <p className="text-sm text-gray-500">{subStep.description}</p>

                                      {(activeStep === index && activeSubStep === subIndex) ||
                                      subStepStatus[index]?.[subIndex] === "completed" ||
                                      showResults[index]?.[subIndex] ? (
                                        <>
                                          <ul className="mt-2 space-y-1">
                                            {subStep.details.map((detail, detailIndex) => (
                                              <li key={detailIndex} className="flex items-center text-sm">
                                                <div className="w-1.5 h-1.5 rounded-full bg-gray-400 mr-2"></div>
                                                {detail}
                                              </li>
                                            ))}
                                          </ul>

                                          {/* Add parameter adjustment sliders for the Parameter Adjustment sub-step */}
                                          {index === 1 && subIndex === 2 && (
                                            <div className="mt-4">
                                              <ParameterAdjustmentSliders onParametersChange={handleParametersChange} />
                                            </div>
                                          )}
                                        </>
                                      ) : null}

                                      {showResults[index]?.[subIndex] && (
                                        <div className="mt-3 p-3 bg-gray-50 rounded-md border">
                                          <h6 className="font-medium text-sm mb-2">Results</h6>
                                          <div className="space-y-2 text-sm">
                                            {index === 1 && subIndex === 2 ? (
                                              <>
                                                <div className="p-2 bg-white rounded border">
                                                  <span className="font-medium">Parameter Settings:</span>
                                                  <div className="mt-1 space-y-1 text-xs">
                                                    <div className="font-medium mt-2">Decision Tree:</div>
                                                    <div>
                                                      - Entropy Cutoff:{" "}
                                                      {modelParameters.decisionTree.entropyCutoff.toFixed(2)}
                                                    </div>
                                                    <div>
                                                      - Depth Cutoff: {modelParameters.decisionTree.depthCutoff}
                                                    </div>
                                                    <div>
                                                      - Support Cutoff:{" "}
                                                      {modelParameters.decisionTree.supportCutoff.toFixed(2)}
                                                    </div>

                                                    <div className="font-medium mt-2">Maxent:</div>
                                                    <div>- Max Iterations: {modelParameters.maxent.maxIter}</div>
                                                    <div>
                                                      - Algorithm: {modelParameters.maxent.algorithm.toUpperCase()}
                                                    </div>

                                                    <div className="font-medium mt-2">POS Tagging:</div>
                                                    <div>- Backoff Tagger: {modelParameters.posTagging.backoff}</div>
                                                    <div>- Cutoff Threshold: {modelParameters.posTagging.cutoff}</div>

                                                    <div className="font-medium mt-2">Lemmatization:</div>
                                                    <div>- Part of Speech: {modelParameters.lemmatization.pos}</div>

                                                    <div className="font-medium mt-2">Tokenization:</div>
                                                    <div>
                                                      - Phrase Detection:{" "}
                                                      {modelParameters.tokenization.collocations
                                                        ? "Enabled"
                                                        : "Disabled"}
                                                    </div>
                                                    <div>
                                                      - Custom Abbreviations:{" "}
                                                      {modelParameters.tokenization.abbrevTypes.split(",").length}{" "}
                                                      defined
                                                    </div>
                                                  </div>
                                                </div>
                                                <div className="p-2 bg-white rounded border">
                                                  <span className="font-medium">Model Performance:</span>
                                                  <div className="mt-1">
                                                    Optimized parameters have improved topic coherence by 23%
                                                  </div>
                                                </div>
                                              </>
                                            ) : (
                                              <>
                                                <div className="p-2 bg-white rounded border">
                                                  <span className="font-medium">Finding 1:</span> Lorem ipsum dolor sit
                                                  amet
                                                </div>
                                                <div className="p-2 bg-white rounded border">
                                                  <span className="font-medium">Finding 2:</span> Consectetur adipiscing
                                                  elit
                                                </div>
                                              </>
                                            )}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                    <div className="ml-3">
                                      <span
                                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                          subStepStatus[index]?.[subIndex] === "completed"
                                            ? "bg-green-100 text-green-800"
                                            : subStepStatus[index]?.[subIndex] === "processing"
                                              ? "bg-blue-100 text-blue-800"
                                              : subStepStatus[index]?.[subIndex] === "error"
                                                ? "bg-red-100 text-red-800"
                                                : "bg-gray-100 text-gray-800"
                                        }`}
                                      >
                                        {subStepStatus[index]?.[subIndex] === "completed"
                                          ? "Completed"
                                          : subStepStatus[index]?.[subIndex] === "processing"
                                            ? "Processing"
                                            : subStepStatus[index]?.[subIndex] === "error"
                                              ? "Error"
                                              : "Pending"}
                                      </span>
                                    </div>
                                  </div>
                                </CardContent>

                                {subStepStatus[index]?.[subIndex] === "completed" && (
                                  <CardFooter className="px-4 py-3 bg-gray-50 flex justify-end space-x-2">
                                    {!showResults[index]?.[subIndex] && (
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => handleReviewResults(index, subIndex)}
                                        className="flex items-center"
                                      >
                                        <Eye className="w-3.5 h-3.5 mr-1.5" />
                                        Review Results
                                      </Button>
                                    )}

                                    <Button
                                      size="sm"
                                      onClick={() => handleContinueSubStep(index, subIndex)}
                                      disabled={
                                        isProcessing ||
                                        (subIndex < step.subSteps.length - 1 &&
                                          subStepStatus[index]?.[subIndex + 1] !== "idle")
                                      }
                                      className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                                    >
                                      {subIndex < step.subSteps.length - 1 &&
                                      subStepStatus[index]?.[subIndex + 1] !== "idle" ? (
                                        "Already Processed"
                                      ) : (
                                        <>
                                          Continue
                                          <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                                        </>
                                      )}
                                    </Button>
                                  </CardFooter>
                                )}
                              </Card>
                            ))}
                          </div>
                        )}

                        {/* Content Analysis and Content Generation */}
                        {(index === 2 || index === 3) && isStepActive(index) && (
                          <div className="mt-4">
                            {index === 2 ? (
                              <Button
                                onClick={() => router.push("/dashboard/content-analysis")}
                                className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 mt-2"
                              >
                                Launch Content Analysis
                              </Button>
                            ) : (
                              <Button
                                onClick={handleGenerateContent}
                                className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 mt-2"
                              >
                                Let's Generate Some Content
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="ml-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            stepStatus[index] === "completed"
                              ? "bg-green-100 text-green-800"
                              : stepStatus[index] === "processing"
                                ? "bg-blue-100 text-blue-800"
                                : stepStatus[index] === "error"
                                  ? "bg-red-100 text-red-800"
                                  : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {stepStatus[index] === "completed"
                            ? "Completed"
                            : stepStatus[index] === "processing"
                              ? "Processing"
                              : stepStatus[index] === "error"
                                ? "Error"
                                : "Pending"}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
          <Link href="/dashboard?tab=content-planner&view=campaigns">
            <Button className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">Return to Campaigns</Button>
          </Link>
        </>
      ) : (
        <Card>
          <CardContent className="p-6 flex flex-col items-center justify-center text-center">
            <div className="p-4 rounded-full bg-secondary mb-4">
              <BookOpen className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold">No Campaign Selected</h3>
            <p className="text-gray-500 mt-1 mb-4">
              Please select a campaign from the list to start the content analysis workflow
            </p>
          </CardContent>
        </Card>
      )}
      <ErrorDialog isOpen={error.isOpen} onClose={closeErrorDialog} message={error.message} />
    </div>
  )
}
