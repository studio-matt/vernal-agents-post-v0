"use client"

import type React from "react"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { InfoIcon as InfoCircle } from "lucide-react"
import { TooltipProvider } from "@/components/ui/tooltip"
import { ParameterInfoModal } from "./ParameterInfoModal"

interface ParameterAdjustmentSlidersProps {
  onParametersChange: (parameters: {
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
      cutoffProbability: number
    }
    lemmatization: {
      pos: string
    }
    tokenization: {
      abbrevTypes: string
      collocations: boolean
    }
  }) => void
}

export function ParameterAdjustmentSliders({ onParametersChange }: ParameterAdjustmentSlidersProps) {
  const [decisionTreeParams, setDecisionTreeParams] = useState({
    entropyCutoff: 0.05,
    depthCutoff: 5,
    supportCutoff: 0.1,
  })

  const [maxentParams, setMaxentParams] = useState({
    maxIter: 100,
    algorithm: "gis" as "gis" | "iis",
  })

  const [posTaggingParams, setPosTaggingParams] = useState({
    backoff: "DefaultTagger",
    cutoff: 5,
    cutoffProbability: 0.9,
  })

  const [lemmatizationParams, setLemmatizationParams] = useState({
    pos: "n",
  })

  const [tokenizationParams, setTokenizationParams] = useState({
    abbrevTypes: "Dr., Prof., Inc., Ltd.",
    collocations: true,
  })

  // State for the info modal
  const [infoModal, setInfoModal] = useState<{
    isOpen: boolean
    title: string
    description: React.ReactNode
  }>({
    isOpen: false,
    title: "",
    description: "",
  })

  const openInfoModal = (title: string, description: React.ReactNode) => {
    setInfoModal({
      isOpen: true,
      title,
      description,
    })
  }

  const closeInfoModal = () => {
    setInfoModal({
      ...infoModal,
      isOpen: false,
    })
  }

  const handleDecisionTreeChange = (param: keyof typeof decisionTreeParams, value: number[]) => {
    const newParams = { ...decisionTreeParams, [param]: value[0] }
    setDecisionTreeParams(newParams)
    updateAllParameters(newParams, maxentParams, posTaggingParams, lemmatizationParams, tokenizationParams)
  }

  const handleMaxentChange = (param: keyof typeof maxentParams, value: number[] | string) => {
    const newParams = {
      ...maxentParams,
      [param]: typeof value === "string" ? value : value[0],
    }
    setMaxentParams(newParams as typeof maxentParams)
    updateAllParameters(
      decisionTreeParams,
      newParams as typeof maxentParams,
      posTaggingParams,
      lemmatizationParams,
      tokenizationParams,
    )
  }

  const handlePosTaggingChange = (param: keyof typeof posTaggingParams, value: number[] | string) => {
    const newParams = {
      ...posTaggingParams,
      [param]: typeof value === "string" ? value : value[0],
    }
    setPosTaggingParams(newParams)
    updateAllParameters(decisionTreeParams, maxentParams, newParams, lemmatizationParams, tokenizationParams)
  }

  const handleLemmatizationChange = (param: keyof typeof lemmatizationParams, value: string) => {
    const newParams = { ...lemmatizationParams, [param]: value }
    setLemmatizationParams(newParams)
    updateAllParameters(decisionTreeParams, maxentParams, posTaggingParams, newParams, tokenizationParams)
  }

  const handleTokenizationChange = (param: keyof typeof tokenizationParams, value: string | boolean) => {
    const newParams = { ...tokenizationParams, [param]: value }
    setTokenizationParams(newParams)
    updateAllParameters(decisionTreeParams, maxentParams, posTaggingParams, lemmatizationParams, newParams)
  }

  const updateAllParameters = (
    decisionTree: typeof decisionTreeParams,
    maxent: typeof maxentParams,
    posTagging: typeof posTaggingParams,
    lemmatization: typeof lemmatizationParams,
    tokenization: typeof tokenizationParams,
  ) => {
    onParametersChange({
      decisionTree,
      maxent,
      posTagging,
      lemmatization,
      tokenization,
    })
  }

  // Parameter descriptions for the info modals
  const parameterDescriptions = {
    // POS Tagging
    backoff: (
      <div className="space-y-4">
        <div>
          <strong>DefaultTagger</strong>
          <div>
            The safety net - tags every unknown word with a default label (like 'NN'). Good for baseline accuracy but
            ignores context.
          </div>
        </div>
        <div>
          <strong>RegexpTagger</strong>
          <div>
            Uses pattern matching (like 'ends with -ing = verb'). Works great for predictable words but struggles with
            exceptions.
          </div>
        </div>
        <div>
          <strong>UnigramTagger</strong>
          <div>
            Guesses tags based on single-word frequency. Fast but confused by words with multiple meanings (like 'book'
            as noun/verb).
          </div>
        </div>
        <div>
          <strong>None</strong>
          <div>
            No backup plan - returns 'None' for uncertain tags. Use this when you want strict rules and manual review of
            unknowns.
          </div>
        </div>
      </div>
    ),
    cutoff: (
      <div className="space-y-2">
        <div>How many times must a word appear to be trusted?</div>
        <div>
          <strong>Low (1-3):</strong> Learns rare words but may overfit quirks
        </div>
        <div>
          <strong>High (5+):</strong> Only uses common patterns, safer but less flexible
        </div>
        <div className="text-sm text-gray-600 mt-2">Example: Set to 5 to ignore typos and hapax legomena.</div>
      </div>
    ),
    cutoffProbability: (
      <div className="space-y-2">
        <div>How sure should the tagger be before committing?</div>
        <div>
          <strong>0.8:</strong> Labels most words but with some guesses
        </div>
        <div>
          <strong>0.95:</strong> Only tags when very confident (more 'None' results)
        </div>
        <div className="text-sm text-gray-600 mt-2">
          Like a teacher grading papers - stricter thresholds mean more "I don't know" answers.
        </div>
      </div>
    ),
    specializedTaggers: (
      <div className="space-y-4">
        <div>
          <strong>AffixTagger</strong>
          <div>
            Tags words by prefixes/suffixes. Like guessing words ending with '-ing' are verbs (but trips up on 'thing').
            Choose prefix/suffix length with affix_length:
            <ul className="mt-2 ml-4 list-disc">
              <li>Positive (e.g., 3): Checks starts of words ("un-" → "unhappy/JJ")</li>
              <li>Negative (e.g., -3): Checks ends ("-ing" → "running/VBG")</li>
            </ul>
            <div className="mt-2">
              <strong>Trade-off:</strong>
              <ul className="ml-4 list-disc">
                <li>Short affixes (2-3 letters): More coverage but less accurate</li>
                <li>Long affixes (4+ letters): More precise but misses variants</li>
              </ul>
            </div>
          </div>
        </div>
        <div>
          <strong>BigramTagger</strong>
          <div>
            Looks at the current word + the previous word's tag to decide. Like guessing 'book' is a noun if preceded by
            'the' (but might fail for 'I book tickets'). Needs lots of examples to work well.
            <div className="mt-2 p-2 bg-gray-100 rounded">
              <strong>Example:</strong>
              <ul className="ml-4 list-disc">
                <li>"the/DT book" → tags "book" as noun (NN)</li>
                <li>"I/PRP book" → misses the verb (VB) meaning without enough training</li>
              </ul>
            </div>
          </div>
        </div>
        <div>
          <strong>TrigramTagger</strong>
          <div>
            Considers two previous tags + current word. More context-aware but needs tons of data. Great for phrases
            like 'was running' (VB+VBG) but struggles with rare triplets.
            <div className="mt-2 p-2 bg-gray-100 rounded">
              <strong>Example:</strong>
              <ul className="ml-4 list-disc">
                <li>"the/DT dog/NN barked" → correctly tags "barked/VBD"</li>
                <li>"a/DT blue/JJ sea/NN" → might fail on poetic "blue sea" as adjective+noun</li>
              </ul>
            </div>
          </div>
        </div>
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
          <strong>How They Fit Together</strong>
          <div className="mt-1">
            These taggers often work in a fallback chain:
            <div className="mt-1 font-mono text-sm">
              Try Trigram → if fails → Bigram → if fails → Unigram → if fails → DefaultTagger
            </div>
            <div className="mt-2">AffixTagger can slot in anywhere (usually before DefaultTagger).</div>
            <div className="mt-2">
              <strong>Pro Tip:</strong> Use cutoff=5 to ignore rare patterns (stops overfitting to typos/oddities).
            </div>
          </div>
        </div>
      </div>
    ),

    // Lemmatization
    pos: (
      <div className="space-y-2">
        <div>Tell the lemmatizer what you're working with:</div>
        <div>
          <strong>'n' (noun):</strong> "'mice' → 'mouse'"
        </div>
        <div>
          <strong>'v' (verb):</strong> "'running' → 'run'"
        </div>
        <div>Pick wrong? It might just shrug and leave the word as-is.</div>
      </div>
    ),

    // Decision Tree
    entropyCutoff: (
      <div className="space-y-2">
        <div>How picky should the tree be before giving up?</div>
        <div>
          <strong>Low (0.1):</strong> "Splits hairs ('puppy' vs 'dog'). Great for details, but slow and nitpicky."
        </div>
        <div>
          <strong>High (0.5):</strong> "Broad strokes ('animal'). Faster, but might miss subtleties."
        </div>
      </div>
    ),
    depthCutoff: (
      <div className="space-y-2">
        <div>How many questions can it ask?</div>
        <div>
          <strong>Deep (10+):</strong> "'Is it fluffy? Does it purr? Is it plotting world domination?' (Accurate but
          exhausting.)"
        </div>
        <div>
          <strong>Shallow (1-3):</strong> "'Is it alive?' (Simple, but everything becomes 'yes' or 'no'.)"
        </div>
      </div>
    ),

    // Maxent
    maxIter: (
      <div className="space-y-2">
        <div>How long should it train?</div>
        <div>
          <strong>Low (50):</strong> "Quick but sloppy (like cramming for a test)."
        </div>
        <div>
          <strong>High (200):</strong> "Thorough but slow (like a perfectionist)."
        </div>
      </div>
    ),
    algorithm: (
      <div className="space-y-2">
        <div>GIS is the tortoise (steady). IIS is the hare (fast but might trip).</div>
      </div>
    ),

    // Tokenization
    abbrevTypes: (
      <div className="space-y-2">
        <div>
          Add shortcuts like 'Dr.' or 'e.g.' so it doesn't split them mid-sentence. (Example: 'Dr. Smith' stays
          together; without this, it might see 'Dr.' as the end of a sentence.)
        </div>
      </div>
    ),
    collocations: (
      <div className="space-y-2">
        <div>
          <strong>ON:</strong> 'New York' = one word (smart).
        </div>
        <div>
          <strong>OFF:</strong> 'New', 'York' (basic).
        </div>
      </div>
    ),
    supportCutoff: (
      <div className="space-y-2">
        <div>How many examples must a branch have to be considered trustworthy?</div>
        <div>
          <strong>Low (0.01-0.1):</strong> Keeps rare patterns (e.g., niche slang) but risks overfitting to flukes.
        </div>
        <div>
          <strong>High (0.2+):</strong> Only keeps well-supported rules (e.g., common grammar), but may miss valid edge
          cases.
        </div>
        <div className="text-sm text-gray-600 mt-2">
          Like a teacher grading essays – low support = accepting shaky arguments; high support = demanding strong
          evidence.
        </div>
      </div>
    ),
  }

  return (
    <TooltipProvider>
      <Tabs defaultValue="decision-tree" className="w-full">
        <TabsList className="w-full mb-4 grid grid-cols-5">
          <TabsTrigger value="decision-tree">DecisionTree</TabsTrigger>
          <TabsTrigger value="maxent">Maxent</TabsTrigger>
          <TabsTrigger value="pos-tagging">POS Tagging</TabsTrigger>
          <TabsTrigger value="lemmatization">Lemmatization</TabsTrigger>
          <TabsTrigger value="tokenization">Tokenization</TabsTrigger>
        </TabsList>

        <TabsContent value="decision-tree" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Decision Tree Parameters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Label htmlFor="entropy-cutoff" className="mr-2">
                      Entropy Cutoff
                    </Label>
                    <button
                      type="button"
                      onClick={() => openInfoModal("Entropy Cutoff", parameterDescriptions.entropyCutoff)}
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoCircle className="h-4 w-4" />
                    </button>
                  </div>
                  <span className="font-mono text-sm">{decisionTreeParams.entropyCutoff.toFixed(2)}</span>
                </div>
                <Slider
                  id="entropy-cutoff"
                  min={0}
                  max={0.5}
                  step={0.01}
                  value={[decisionTreeParams.entropyCutoff]}
                  onValueChange={(value) => handleDecisionTreeChange("entropyCutoff", value)}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Label htmlFor="depth-cutoff" className="mr-2">
                      Depth Cutoff
                    </Label>
                    <button
                      type="button"
                      onClick={() => openInfoModal("Depth Cutoff", parameterDescriptions.depthCutoff)}
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoCircle className="h-4 w-4" />
                    </button>
                  </div>
                  <span className="font-mono text-sm">{decisionTreeParams.depthCutoff}</span>
                </div>
                <Slider
                  id="depth-cutoff"
                  min={1}
                  max={20}
                  step={1}
                  value={[decisionTreeParams.depthCutoff]}
                  onValueChange={(value) => handleDecisionTreeChange("depthCutoff", value)}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Label htmlFor="support-cutoff" className="mr-2">
                      Support Cutoff
                    </Label>
                    <button
                      type="button"
                      onClick={() => openInfoModal("Support Cutoff", parameterDescriptions.supportCutoff)}
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoCircle className="h-4 w-4" />
                    </button>
                  </div>
                  <span className="font-mono text-sm">{decisionTreeParams.supportCutoff.toFixed(2)}</span>
                </div>
                <Slider
                  id="support-cutoff"
                  min={0.01}
                  max={0.5}
                  step={0.01}
                  value={[decisionTreeParams.supportCutoff]}
                  onValueChange={(value) => handleDecisionTreeChange("supportCutoff", value)}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="maxent" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Maxent Classifier Parameters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Label htmlFor="max-iter" className="mr-2">
                      Max Iterations
                    </Label>
                    <button
                      type="button"
                      onClick={() => openInfoModal("Max Iterations", parameterDescriptions.maxIter)}
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoCircle className="h-4 w-4" />
                    </button>
                  </div>
                  <span className="font-mono text-sm">{maxentParams.maxIter}</span>
                </div>
                <Slider
                  id="max-iter"
                  min={50}
                  max={200}
                  step={10}
                  value={[maxentParams.maxIter]}
                  onValueChange={(value) => handleMaxentChange("maxIter", value)}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center">
                  <Label className="mr-2">Algorithm</Label>
                  <button
                    type="button"
                    onClick={() => openInfoModal("Algorithm", parameterDescriptions.algorithm)}
                    className="text-gray-500 hover:text-gray-700 focus:outline-none"
                  >
                    <InfoCircle className="h-4 w-4" />
                  </button>
                </div>
                <RadioGroup
                  value={maxentParams.algorithm}
                  onValueChange={(value) => handleMaxentChange("algorithm", value as "gis" | "iis")}
                  className="flex space-x-4"
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="gis" id="gis" />
                    <Label htmlFor="gis">GIS</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="iis" id="iis" />
                    <Label htmlFor="iis">IIS</Label>
                  </div>
                </RadioGroup>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pos-tagging" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">POS Tagging Parameters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center">
                  <Label htmlFor="backoff-tagger" className="mr-2">
                    Backoff Tagger
                  </Label>
                  <button
                    type="button"
                    onClick={() => openInfoModal("Backoff Tagger", parameterDescriptions.backoff)}
                    className="text-gray-500 hover:text-gray-700 focus:outline-none"
                  >
                    <InfoCircle className="h-4 w-4" />
                  </button>
                </div>
                <Select
                  value={posTaggingParams.backoff}
                  onValueChange={(value) => handlePosTaggingChange("backoff", value)}
                >
                  <SelectTrigger id="backoff-tagger">
                    <SelectValue placeholder="Select backoff tagger" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DefaultTagger">DefaultTagger</SelectItem>
                    <SelectItem value="RegexpTagger">RegexpTagger</SelectItem>
                    <SelectItem value="UnigramTagger">UnigramTagger</SelectItem>
                    <SelectItem value="BigramTagger">BigramTagger</SelectItem>
                    <SelectItem value="TrigramTagger">TrigramTagger</SelectItem>
                    <SelectItem value="AffixTagger">AffixTagger</SelectItem>
                    <SelectItem value="None">None</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <div className="flex items-center">
                  <Label className="mr-2">Specialized Taggers</Label>
                  <button
                    type="button"
                    onClick={() => openInfoModal("Specialized Taggers", parameterDescriptions.specializedTaggers)}
                    className="text-gray-500 hover:text-gray-700 focus:outline-none"
                  >
                    <InfoCircle className="h-4 w-4" />
                  </button>
                </div>
                <div className="text-sm text-gray-500">
                  Click the info icon to learn about specialized taggers that can be used as backoff options.
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Label htmlFor="cutoff-threshold" className="mr-2">
                      Cutoff Threshold
                    </Label>
                    <button
                      type="button"
                      onClick={() => openInfoModal("Cutoff Threshold", parameterDescriptions.cutoff)}
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoCircle className="h-4 w-4" />
                    </button>
                  </div>
                  <span className="font-mono text-sm">{posTaggingParams.cutoff}</span>
                </div>
                <Slider
                  id="cutoff-threshold"
                  min={1}
                  max={10}
                  step={1}
                  value={[posTaggingParams.cutoff]}
                  onValueChange={(value) => handlePosTaggingChange("cutoff", value)}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Label htmlFor="cutoff-probability" className="mr-2">
                      Cutoff Probability
                    </Label>
                    <button
                      type="button"
                      onClick={() => openInfoModal("Cutoff Probability", parameterDescriptions.cutoffProbability)}
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoCircle className="h-4 w-4" />
                    </button>
                  </div>
                  <span className="font-mono text-sm">{posTaggingParams.cutoffProbability.toFixed(2)}</span>
                </div>
                <Slider
                  id="cutoff-probability"
                  min={0.7}
                  max={0.99}
                  step={0.01}
                  value={[posTaggingParams.cutoffProbability]}
                  onValueChange={(value) => handlePosTaggingChange("cutoffProbability", value)}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="lemmatization" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Lemmatization Parameters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center">
                  <Label htmlFor="pos-tag" className="mr-2">
                    Part of Speech
                  </Label>
                  <button
                    type="button"
                    onClick={() => openInfoModal("Part of Speech", parameterDescriptions.pos)}
                    className="text-gray-500 hover:text-gray-700 focus:outline-none"
                  >
                    <InfoCircle className="h-4 w-4" />
                  </button>
                </div>
                <Select
                  value={lemmatizationParams.pos}
                  onValueChange={(value) => handleLemmatizationChange("pos", value)}
                >
                  <SelectTrigger id="pos-tag">
                    <SelectValue placeholder="Select part of speech" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="n">n (noun)</SelectItem>
                    <SelectItem value="v">v (verb)</SelectItem>
                    <SelectItem value="a">a (adjective)</SelectItem>
                    <SelectItem value="r">r (adverb)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tokenization" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Tokenization Parameters (PunktSentenceTokenizer)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center">
                  <Label htmlFor="abbrev-types" className="mr-2">
                    Custom Abbreviations
                  </Label>
                  <button
                    type="button"
                    onClick={() => openInfoModal("Custom Abbreviations", parameterDescriptions.abbrevTypes)}
                    className="text-gray-500 hover:text-gray-700 focus:outline-none"
                  >
                    <InfoCircle className="h-4 w-4" />
                  </button>
                </div>
                <Textarea
                  id="abbrev-types"
                  value={tokenizationParams.abbrevTypes}
                  onChange={(e) => handleTokenizationChange("abbrevTypes", e.target.value)}
                  placeholder="Dr., Prof., Inc., Ltd."
                  className="min-h-[80px]"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Label htmlFor="collocations" className="mr-2">
                      Phrase Detection
                    </Label>
                    <button
                      type="button"
                      onClick={() => openInfoModal("Phrase Detection", parameterDescriptions.collocations)}
                      className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                      <InfoCircle className="h-4 w-4" />
                    </button>
                  </div>
                  <Switch
                    id="collocations"
                    checked={tokenizationParams.collocations}
                    onCheckedChange={(checked) => handleTokenizationChange("collocations", checked)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Parameter Info Modal */}
      <ParameterInfoModal
        isOpen={infoModal.isOpen}
        onClose={closeInfoModal}
        title={infoModal.title}
        description={infoModal.description}
      />
    </TooltipProvider>
  )
}
