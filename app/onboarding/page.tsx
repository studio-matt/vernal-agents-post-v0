"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Header } from "@/components/Header"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Check, Linkedin, Facebook, Instagram, Youtube, Twitter } from "lucide-react"
import { XIcon, TikTokIcon } from "@/components/PlatformIcons"
import {
  linkedinConnect,
  twitterConnect,
  wordpressConnect,
  storeOpenAIKey,
  getUserCredentials,
} from "@/components/Service"
import { ChevronLeft, ChevronRight } from "lucide-react"

// Enabled platforms for Step 1
const ENABLED_PLATFORMS = [
  { name: "Instagram", icon: Instagram },
  { name: "Facebook", icon: Facebook },
  { name: "WordPress", icon: () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
      <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z" />
      <path d="M12 2a10 10 0 0 1 10 10" />
      <path d="M12 2v10l4 8" />
      <path d="M12 12 8 20" />
    </svg>
  )},
  { name: "Twitter", icon: XIcon },
  { name: "LinkedIn", icon: Linkedin },
]

// Disabled platforms for Step 1
const DISABLED_PLATFORMS = [
  { name: "YouTube", icon: Youtube },
  { name: "TikTok", icon: TikTokIcon },
]

export default function Onboarding() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(0)
  const [selectedPlatforms, setSelectedPlatforms] = useState<Record<string, boolean>>({})
  
  // Step 2 state
  const [linkedinConnected, setLinkedinConnected] = useState(false)
  const [twitterConnected, setTwitterConnected] = useState(false)
  const [wordpressConnected, setWordpressConnected] = useState(false)
  const [linkedinLoading, setLinkedinLoading] = useState(false)
  const [twitterLoading, setTwitterLoading] = useState(false)
  const [wordpressLoading, setWordpressLoading] = useState(false)
  const [wordpressSiteUrl, setWordpressSiteUrl] = useState("")
  const [wordpressUsername, setWordpressUsername] = useState("")
  const [wordpressPassword, setWordpressPassword] = useState("")
  const [wordpressConnecting, setWordpressConnecting] = useState(false)
  const [showSkipWarning, setShowSkipWarning] = useState(false)
  
  // Step 3 state
  const [openaiKey, setOpenaiKey] = useState("")
  const [savingOpenAI, setSavingOpenAI] = useState(false)
  const [openaiSuccess, setOpenaiSuccess] = useState(false)

  const steps = [
    "Select Platforms",
    "Platform Settings",
    "Model Credentials",
    "Ready to Go!",
  ]
  const progress = ((currentStep + 1) / steps.length) * 100

  // Check if onboarding was already completed
  useEffect(() => {
    const onboardingCompleted = localStorage.getItem("onboarding_completed")
    if (onboardingCompleted === "true") {
      router.push("/dashboard/content-planner")
    }
  }, [router])

  // Load stored credentials on mount
  useEffect(() => {
    const loadCredentials = async () => {
      try {
        const response = await getUserCredentials()
        if (response.success && response.credentials) {
          if (response.credentials.openai_key) {
            setOpenaiKey(response.credentials.openai_key)
          }
        }
      } catch (error) {
        console.error("Failed to load credentials:", error)
      }
    }
    loadCredentials()
  }, [])

  const handlePlatformSelect = (platform: string, checked: boolean) => {
    setSelectedPlatforms((prev) => ({
      ...prev,
      [platform]: checked,
    }))
  }

  const handleLinkedInConnect = async () => {
    setLinkedinLoading(true)
    try {
      const result = await linkedinConnect()
      if (result && result.success) {
        setLinkedinConnected(true)
        localStorage.setItem("linkedin_connected", "true")
      }
    } catch (e) {
      console.error("LinkedIn connection failed:", e)
    } finally {
      setLinkedinLoading(false)
    }
  }

  const handleTwitterConnect = async () => {
    setTwitterLoading(true)
    try {
      const result = await twitterConnect()
      if (result && result.success) {
        setTwitterConnected(true)
        localStorage.setItem("twitter_connected", "true")
      }
    } catch (e) {
      console.error("Twitter connection failed:", e)
    } finally {
      setTwitterLoading(false)
    }
  }

  const handleWordpressConnect = async () => {
    if (!wordpressSiteUrl || !wordpressUsername || !wordpressPassword) {
      return
    }
    setWordpressConnecting(true)
    setWordpressLoading(true)
    try {
      const result = await wordpressConnect({
        siteUrl: wordpressSiteUrl,
        username: wordpressUsername,
        applicationPassword: wordpressPassword,
      })
      if (result && result.success) {
        setWordpressConnected(true)
        localStorage.setItem("wordpress_connected", "true")
      }
    } catch (e) {
      console.error("WordPress connection failed:", e)
    } finally {
      setWordpressConnecting(false)
      setWordpressLoading(false)
    }
  }

  const handleSaveOpenAI = async () => {
    if (!openaiKey.trim()) return
    setSavingOpenAI(true)
    try {
      const result = await storeOpenAIKey(openaiKey)
      if (result && result.success) {
        setOpenaiSuccess(true)
        setTimeout(() => setOpenaiSuccess(false), 3000)
      }
    } catch (e) {
      console.error("Failed to save OpenAI key:", e)
    } finally {
      setSavingOpenAI(false)
    }
  }

  const handleNext = () => {
    if (currentStep === 0) {
      // Step 1: At least one platform must be selected
      const hasSelection = Object.values(selectedPlatforms).some((v) => v)
      if (!hasSelection) {
        alert("Please select at least one platform to continue.")
        return
      }
    }
    setCurrentStep((prev) => Math.min(prev + 1, steps.length - 1))
  }

  const handlePrevious = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 0))
  }

  const handleSkip = () => {
    setShowSkipWarning(true)
  }

  const handleConfirmSkip = () => {
    setShowSkipWarning(false)
    handleFinish()
  }

  const handleFinish = () => {
    // Store selected platforms in localStorage
    localStorage.setItem("selected_platforms", JSON.stringify(selectedPlatforms))
    localStorage.setItem("onboarding_completed", "true")
    router.push("/dashboard/content-planner")
  }

  const renderStep1 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Select Your Platforms</h2>
        <p className="text-gray-600">Choose the platforms you want to use for content creation</p>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {ENABLED_PLATFORMS.map((platform) => {
          const Icon = platform.icon
          const isSelected = selectedPlatforms[platform.name]
          return (
            <div
              key={platform.name}
              className={`
                relative rounded-xl border-2 p-6 flex flex-col items-center justify-center space-y-3 cursor-pointer transition-all
                ${isSelected ? "border-[#3d545f] bg-[#3d545f]/10" : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"}
              `}
              onClick={() => handlePlatformSelect(platform.name, !isSelected)}
            >
              <div
                className={`
                  p-3 rounded-full
                  ${isSelected ? "bg-[#3d545f] text-white" : "bg-gray-100 text-gray-600"}
                `}
              >
                <Icon className="h-6 w-6" />
              </div>
              <span className="font-medium text-center text-sm">{platform.name}</span>
              <div className="absolute top-3 right-3">
                <Checkbox
                  checked={isSelected}
                  onCheckedChange={(checked) => handlePlatformSelect(platform.name, checked === true)}
                  className={isSelected ? "bg-[#3d545f] border-[#3d545f]" : ""}
                />
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
        {DISABLED_PLATFORMS.map((platform) => {
          const Icon = platform.icon
          return (
            <div
              key={platform.name}
              className="relative rounded-lg border-2 border-gray-200 p-6 flex flex-col items-center justify-center space-y-3 opacity-50 cursor-not-allowed bg-gray-50"
            >
              <div className="p-3 rounded-full bg-gray-200 text-gray-400">
                {platform.name === "TikTok" ? (
                  <TikTokIcon className="h-6 w-6" />
                ) : (
                  <Icon className="h-6 w-6" />
                )}
              </div>
              <span className="font-medium text-center text-sm text-gray-400">{platform.name}</span>
              <div className="absolute top-3 right-3">
                <Checkbox checked={false} disabled className="opacity-50" />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )

  const renderStep2 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Connect Your Platforms</h2>
        <p className="text-gray-600">Connect the platforms you selected in the previous step</p>
      </div>

      {selectedPlatforms["LinkedIn"] && (
        <Card>
          <CardHeader>
            <CardTitle>LinkedIn</CardTitle>
          </CardHeader>
          <CardContent>
            <Button
              onClick={handleLinkedInConnect}
              disabled={linkedinLoading || linkedinConnected}
              className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
            >
              {linkedinLoading ? "Connecting..." : linkedinConnected ? "Connected ✓" : "Connect to LinkedIn"}
            </Button>
          </CardContent>
        </Card>
      )}

      {selectedPlatforms["Twitter"] && (
        <Card>
          <CardHeader>
            <CardTitle>Twitter</CardTitle>
          </CardHeader>
          <CardContent>
            <Button
              onClick={handleTwitterConnect}
              disabled={twitterLoading || twitterConnected}
              className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
            >
              {twitterLoading ? "Connecting..." : twitterConnected ? "Connected ✓" : "Connect to Twitter"}
            </Button>
          </CardContent>
        </Card>
      )}

      {selectedPlatforms["WordPress"] && (
        <Card>
          <CardHeader>
            <CardTitle>WordPress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Site URL</label>
              <Input
                type="text"
                placeholder="https://yoursite.com"
                value={wordpressSiteUrl}
                onChange={(e) => setWordpressSiteUrl(e.target.value)}
                disabled={wordpressConnected}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Username</label>
              <Input
                type="text"
                placeholder="Your WordPress username"
                value={wordpressUsername}
                onChange={(e) => setWordpressUsername(e.target.value)}
                disabled={wordpressConnected}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Application Password</label>
              <Input
                type="password"
                placeholder="Your WordPress app password"
                value={wordpressPassword}
                onChange={(e) => setWordpressPassword(e.target.value)}
                disabled={wordpressConnected}
              />
            </div>
            <Button
              onClick={handleWordpressConnect}
              disabled={wordpressLoading || wordpressConnected || !wordpressSiteUrl || !wordpressUsername || !wordpressPassword}
              className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
            >
              {wordpressLoading ? "Connecting..." : wordpressConnected ? "Connected ✓" : "Connect to WordPress"}
            </Button>
          </CardContent>
        </Card>
      )}

      {!selectedPlatforms["LinkedIn"] && !selectedPlatforms["Twitter"] && !selectedPlatforms["WordPress"] && (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            No platforms selected. You can skip this step and configure later.
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end">
        <Button
          variant="outline"
          onClick={handleSkip}
          className="text-gray-600 hover:text-gray-800"
        >
          Skip for now
        </Button>
      </div>
    </div>
  )

  const renderStep3 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Model Credentials</h2>
        <p className="text-gray-600">Configure your AI model API keys</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>OpenAI Connection</span>
            <Checkbox checked={true} disabled className="opacity-50" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">API Key</label>
            <Input
              type="password"
              placeholder="sk-..."
              value={openaiKey}
              onChange={(e) => setOpenaiKey(e.target.value)}
            />
          </div>
          <Button
            onClick={handleSaveOpenAI}
            disabled={savingOpenAI || !openaiKey.trim()}
            className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
          >
            {savingOpenAI ? "Saving..." : openaiSuccess ? "Saved ✓" : "Save OpenAI Connection"}
          </Button>
        </CardContent>
      </Card>

      <Card className="opacity-50">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Claude Connection (Coming Soon)</span>
            <Checkbox checked={false} disabled className="opacity-50" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">API Key</label>
            <Input type="text" placeholder="Coming soon" disabled />
          </div>
          <Button disabled className="w-full bg-gray-300 text-gray-500 cursor-not-allowed">
            Coming Soon
          </Button>
        </CardContent>
      </Card>

      <Card className="opacity-50">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Eleven Labs Connection (Coming Soon)</span>
            <Checkbox checked={false} disabled className="opacity-50" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">API Key</label>
            <Input type="text" placeholder="Coming soon" disabled />
          </div>
          <Button disabled className="w-full bg-gray-300 text-gray-500 cursor-not-allowed">
            Coming Soon
          </Button>
        </CardContent>
      </Card>
    </div>
  )

  const renderStep4 = () => (
    <div className="space-y-6 text-center">
      <div className="flex justify-center">
        <div className="rounded-full bg-green-100 p-6">
          <Check className="h-12 w-12 text-green-600" />
        </div>
      </div>
      <h2 className="text-3xl font-bold">Ready to Go!</h2>
      <p className="text-gray-600 text-lg">
        Your account is set up and ready. You can start creating amazing content!
      </p>
      <Button
        onClick={handleFinish}
        className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 px-8 py-6 text-lg"
      >
        Go to Dashboard
      </Button>
    </div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#7A99A8] to-[#5d7a89]">
      <Header username={typeof window !== "undefined" ? localStorage.getItem("username") || "User" : "User"} />
      <main className="container max-w-4xl mx-auto p-6 space-y-6">
        <div className="flex items-center space-x-4 mb-4">
          <Link href="/login" className="flex items-center text-white hover:text-gray-200">
            <ChevronLeft className="h-5 w-5 mr-1" />
            Back to Login
          </Link>
        </div>

        <div className="text-center mb-8">
          <h1 className="text-4xl font-extrabold text-white mb-2">Welcome to Vernal Contentum</h1>
          <p className="text-white/80 text-lg">Let's get your account set up</p>
        </div>

        <Card className="border-none shadow-xl overflow-hidden">
          <CardHeader className="bg-[#3d545f] text-white">
            <div className="flex items-center justify-between">
              <CardTitle className="text-2xl">Step {currentStep + 1} of {steps.length}</CardTitle>
              <span className="text-sm font-normal">{steps[currentStep]}</span>
            </div>
            <Progress value={progress} className="mt-4" />
          </CardHeader>
          <CardContent className="p-8">
            {currentStep === 0 && renderStep1()}
            {currentStep === 1 && renderStep2()}
            {currentStep === 2 && renderStep3()}
            {currentStep === 3 && renderStep4()}

            <div className="flex justify-between mt-8">
              <Button
                variant="outline"
                onClick={handlePrevious}
                disabled={currentStep === 0}
                className="flex items-center"
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              {currentStep < steps.length - 1 ? (
                <Button
                  onClick={handleNext}
                  className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 flex items-center"
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </main>

      <AlertDialog open={showSkipWarning} onOpenChange={setShowSkipWarning}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Skip Platform Settings?</AlertDialogTitle>
            <AlertDialogDescription>
              You can configure your platform connections later in Account Settings. Are you sure you want to skip this step?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmSkip}>Skip</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

