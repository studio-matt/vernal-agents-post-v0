"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Header } from "@/components/Header"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
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
import { Check, Loader2, Linkedin, Facebook, Instagram, Youtube } from "lucide-react"
import { XIcon, TikTokIcon, SnapchatIcon } from "@/components/PlatformIcons"

const SOCIAL_PLATFORMS = [
  { name: "LinkedIn", icon: Linkedin },
  { name: "X", icon: XIcon },
  { name: "Facebook", icon: Facebook },
  { name: "Instagram", icon: Instagram },
  { name: "YouTube", icon: Youtube },
  { name: "TikTok", icon: TikTokIcon },
  { name: "SnapChat", icon: SnapchatIcon },
  {
    name: "WordPress",
    icon: () => (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-5 w-5"
      >
        <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z" />
        <path d="M12 2a10 10 0 0 1 10 10" />
        <path d="M12 2v10l4 8" />
        <path d="M12 12 8 20" />
      </svg>
    ),
  },
]

const MODEL_PLATFORMS = ["OpenAI", "Claude", "Midjourney", "Eleven Labs"]

export default function FirstTimeSetup() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(0)
  const [selectedPlatforms, setSelectedPlatforms] = useState<Record<string, boolean>>({})
  const [platformStatus, setPlatformStatus] = useState<Record<string, "idle" | "loading" | "connected">>({})
  const [wordpressConfig, setWordpressConfig] = useState({
    siteUrl: "",
    username: "",
    appPassword: "",
  })
  const [modelCredentials, setModelCredentials] = useState<Record<string, { apiKey: string }>>({})
  const [showIncompleteModal, setShowIncompleteModal] = useState(false)
  const [showWordpressHelp, setShowWordpressHelp] = useState(false)

  const steps = ["Desired Platforms", "Authorize Platforms", "Add Models", "Ready to go!"]
  const progress = ((currentStep + 1) / steps.length) * 100

  const handlePlatformSelect = (platform: string, checked: boolean) => {
    setSelectedPlatforms((prev) => ({
      ...prev,
      [platform]: checked,
    }))
  }

  const handleConnectPlatform = (platform: string) => {
    if (platformStatus[platform] === "connected") {
      // Disconnect logic
      setPlatformStatus((prev) => ({
        ...prev,
        [platform]: "idle",
      }))
      return
    }

    // Connect logic with simulated loading
    setPlatformStatus((prev) => ({
      ...prev,
      [platform]: "loading",
    }))

    setTimeout(() => {
      setPlatformStatus((prev) => ({
        ...prev,
        [platform]: "connected",
      }))
    }, 1500)
  }

  const handleWordpressChange = (field: string, value: string) => {
    setWordpressConfig((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleModelCredentialChange = (platform: string, value: string) => {
    setModelCredentials((prev) => ({
      ...prev,
      [platform]: { apiKey: value },
    }))
  }

  const handleNext = () => {
    if (currentStep === 1) {
      // Check if any selected platforms are not connected
      const hasIncomplete = Object.entries(selectedPlatforms).some(
        ([platform, selected]) => selected && platformStatus[platform] !== "connected",
      )

      if (hasIncomplete) {
        setShowIncompleteModal(true)
        return
      }
    }

    setCurrentStep((prev) => Math.min(prev + 1, steps.length - 1))
  }

  const handlePrevious = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 0))
  }

  const handleFinish = () => {
    router.push("/dashboard/content-planner")
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#7A99A8] to-[#5d7a89]">
      <Header username="John Doe" />
      <main className="container max-w-4xl mx-auto p-6 space-y-6">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-extrabold text-white mb-2">First Time Setup</h1>
          <p className="text-white/80 text-lg">Let's get your account ready to create amazing content</p>
        </div>

        <Card className="border-none shadow-xl overflow-hidden">
          <div className="bg-gradient-to-r from-[#3d545f] to-[#4a6573] p-4">
            <Progress value={progress} className="h-3 bg-white/20" />
            <div className="flex justify-between mt-3 text-sm text-white/80">
              {steps.map((step, index) => (
                <div
                  key={index}
                  className={`${
                    currentStep >= index ? "font-medium text-white" : "text-white/60"
                  } transition-all duration-300`}
                >
                  {step}
                </div>
              ))}
            </div>
          </div>
          <CardContent className="p-8">
            <Tabs value={currentStep.toString()} onValueChange={(value) => setCurrentStep(Number.parseInt(value))}>
              <TabsList className="hidden">
                {steps.map((step, index) => (
                  <TabsTrigger key={index} value={index.toString()}>
                    {step}
                  </TabsTrigger>
                ))}
              </TabsList>

              {/* Step 1: Desired Platforms */}
              <TabsContent value="0" className="space-y-8 mt-2">
                <div className="text-center max-w-2xl mx-auto">
                  <h2 className="text-2xl font-semibold mb-2">Choose Your Platforms</h2>
                  <p className="text-gray-600">
                    Which platforms would you like to use most immediately? You can add more at any time.
                  </p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {SOCIAL_PLATFORMS.map((platform) => {
                    const Icon = platform.icon
                    return (
                      <div
                        key={platform.name}
                        className={`
                          relative rounded-xl border-2 p-6 flex flex-col items-center justify-center space-y-3 cursor-pointer transition-all
                          ${
                            selectedPlatforms[platform.name]
                              ? "border-[#3d545f] bg-[#3d545f]/10"
                              : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                          }
                        `}
                        onClick={() => handlePlatformSelect(platform.name, !selectedPlatforms[platform.name])}
                      >
                        <div
                          className={`
                          p-3 rounded-full 
                          ${selectedPlatforms[platform.name] ? "bg-[#3d545f] text-white" : "bg-gray-100 text-gray-600"}
                        `}
                        >
                          <Icon />
                        </div>
                        <span className="font-medium text-center">{platform.name}</span>
                        <div className="absolute top-3 right-3">
                          <Checkbox
                            id={`platform-${platform.name}`}
                            checked={selectedPlatforms[platform.name] || false}
                            onCheckedChange={(checked) => handlePlatformSelect(platform.name, checked === true)}
                            className={`${selectedPlatforms[platform.name] ? "bg-[#3d545f] border-[#3d545f]" : ""}`}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>

                <div className="flex justify-end mt-8">
                  <Button
                    onClick={handleNext}
                    className="bg-[#3d545f] hover:bg-[#4a6573] text-white px-8 py-2 rounded-md"
                  >
                    Next
                  </Button>
                </div>
              </TabsContent>

              {/* Step 2: Authorize Platforms */}
              <TabsContent value="1" className="space-y-6 mt-2">
                <div className="text-center max-w-2xl mx-auto mb-8">
                  <h2 className="text-2xl font-semibold mb-2">Connect Your Platforms</h2>
                  <p className="text-gray-600">
                    Authorize access to your selected platforms to enable content publishing.
                  </p>
                </div>

                <div className="space-y-4">
                  {Object.entries(selectedPlatforms)
                    .filter(([_, selected]) => selected)
                    .map(([platformName]) => {
                      const platform = SOCIAL_PLATFORMS.find((p) => p.name === platformName)
                      const Icon = platform?.icon || (() => null)
                      const isWordPress = platformName === "WordPress"

                      return (
                        <div key={platformName} className="border rounded-lg bg-white shadow-sm overflow-hidden">
                          <div className="flex items-center justify-between p-4">
                            <div className="flex items-center space-x-3">
                              <div className="p-2 bg-gray-100 rounded-full">
                                <Icon />
                              </div>
                              <span className="font-medium">{platformName}</span>
                            </div>

                            {!isWordPress && (
                              <Button
                                onClick={() => handleConnectPlatform(platformName)}
                                variant={platformStatus[platformName] === "connected" ? "outline" : "default"}
                                className={`
                                  min-w-[150px] flex items-center justify-center space-x-2
                                  ${
                                    platformStatus[platformName] === "connected"
                                      ? "border-green-500 text-green-600"
                                      : "bg-[#3d545f] hover:bg-[#4a6573] text-white"
                                  }
                                `}
                              >
                                {platformStatus[platformName] === "loading" && (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                )}
                                {platformStatus[platformName] === "connected" && (
                                  <Check className="h-4 w-4 text-green-500" />
                                )}
                                <span>
                                  {platformStatus[platformName] === "connected"
                                    ? `Disconnect ${platformName}`
                                    : `Connect to ${platformName}`}
                                </span>
                              </Button>
                            )}
                          </div>

                          {/* WordPress Configuration - Always visible when WordPress is selected */}
                          {isWordPress && (
                            <div className="border-t p-4 space-y-4 bg-gray-50">
                              <div className="flex items-center justify-between mb-2">
                                <h3 className="font-medium">WordPress Configuration</h3>
                                <Button
                                  variant="link"
                                  onClick={() => setShowWordpressHelp(true)}
                                  className="text-blue-600 text-sm"
                                >
                                  How to find app password
                                </Button>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="space-y-2">
                                  <label className="text-sm font-medium">Site URL</label>
                                  <Input
                                    value={wordpressConfig.siteUrl}
                                    onChange={(e) => handleWordpressChange("siteUrl", e.target.value)}
                                    placeholder="https://yoursite.com"
                                    className="border-gray-300 focus:border-[#3d545f] focus:ring-[#3d545f]"
                                  />
                                </div>
                                <div className="space-y-2">
                                  <label className="text-sm font-medium">Username</label>
                                  <Input
                                    value={wordpressConfig.username}
                                    onChange={(e) => handleWordpressChange("username", e.target.value)}
                                    placeholder="admin"
                                    className="border-gray-300 focus:border-[#3d545f] focus:ring-[#3d545f]"
                                  />
                                </div>
                                <div className="space-y-2">
                                  <label className="text-sm font-medium">Application Password</label>
                                  <Input
                                    type="password"
                                    value={wordpressConfig.appPassword}
                                    onChange={(e) => handleWordpressChange("appPassword", e.target.value)}
                                    placeholder="xxxx xxxx xxxx xxxx xxxx xxxx"
                                    className="border-gray-300 focus:border-[#3d545f] focus:ring-[#3d545f]"
                                  />
                                </div>
                              </div>

                              <div className="flex justify-end mt-2">
                                <Button
                                  onClick={() => handleConnectPlatform("WordPress")}
                                  variant={platformStatus["WordPress"] === "connected" ? "outline" : "default"}
                                  className={`
                                    min-w-[150px] flex items-center justify-center space-x-2
                                    ${
                                      platformStatus["WordPress"] === "connected"
                                        ? "border-green-500 text-green-600"
                                        : "bg-[#3d545f] hover:bg-[#4a6573] text-white"
                                    }
                                  `}
                                >
                                  {platformStatus["WordPress"] === "loading" && (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                  )}
                                  {platformStatus["WordPress"] === "connected" && (
                                    <Check className="h-4 w-4 text-green-500" />
                                  )}
                                  <span>
                                    {platformStatus["WordPress"] === "connected" ? "Verified" : "Verify Credentials"}
                                  </span>
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                </div>

                <div className="flex justify-between mt-8">
                  <Button variant="outline" onClick={handlePrevious}>
                    Previous
                  </Button>
                  <Button onClick={handleNext} className="bg-[#3d545f] hover:bg-[#4a6573] text-white">
                    Save and Continue
                  </Button>
                </div>
              </TabsContent>

              {/* Step 3: Add Models */}
              <TabsContent value="2" className="space-y-6 mt-2">
                <div className="text-center max-w-2xl mx-auto mb-8">
                  <h2 className="text-2xl font-semibold mb-2">Connect AI Models</h2>
                  <p className="text-gray-600">Add your AI model credentials to enable powerful content generation.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {MODEL_PLATFORMS.map((platform) => (
                    <div key={platform} className="border p-6 rounded-lg space-y-4 bg-white shadow-sm">
                      <div className="flex items-center justify-between">
                        <h3 className="font-medium text-lg">{platform}</h3>
                        <div
                          className={`
                          h-3 w-3 rounded-full 
                          ${modelCredentials[platform]?.apiKey ? "bg-green-500" : "bg-gray-300"}
                        `}
                        ></div>
                      </div>
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium text-gray-600">API Key</h4>
                        <Input
                          type="password"
                          value={modelCredentials[platform]?.apiKey || ""}
                          onChange={(e) => handleModelCredentialChange(platform, e.target.value)}
                          placeholder={`Enter your ${platform} API key`}
                          className="border-gray-300 focus:border-[#3d545f] focus:ring-[#3d545f]"
                        />
                      </div>
                      <Button className="w-full bg-[#3d545f] text-white hover:bg-[#4a6573]">
                        Save {platform} Connection
                      </Button>
                    </div>
                  ))}
                </div>

                <div className="flex justify-between mt-8">
                  <Button variant="outline" onClick={handlePrevious}>
                    Previous
                  </Button>
                  <Button onClick={handleNext} className="bg-[#3d545f] hover:bg-[#4a6573] text-white">
                    Save and Finalize
                  </Button>
                </div>
              </TabsContent>

              {/* Step 4: Ready to go! */}
              <TabsContent value="3" className="space-y-6 text-center mt-2">
                <div className="py-10 max-w-md mx-auto">
                  <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Check className="h-12 w-12 text-green-600" />
                  </div>
                  <h2 className="text-3xl font-semibold mb-4">Ready to begin</h2>
                  <p className="text-gray-600 mb-8">
                    That's all we need for now to get rolling. Let's start creating together.
                  </p>

                  <Button
                    size="lg"
                    onClick={handleFinish}
                    className="bg-[#3d545f] hover:bg-[#4a6573] text-white px-8 py-6 text-lg"
                  >
                    Start your Plan
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </main>

      {/* Incomplete Platforms Modal */}
      <AlertDialog open={showIncompleteModal} onOpenChange={setShowIncompleteModal}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Incomplete Platform Configuration</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to continue? You have one or more platforms that has not been configured. If you
              continue, you will have to authorize them prior to being able to use them in this system.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>No, keep editing</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setShowIncompleteModal(false)
                setCurrentStep((prev) => prev + 1)
              }}
              className="bg-[#3d545f] hover:bg-[#4a6573]"
            >
              Yes, please continue
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* WordPress Help Dialog */}
      <Dialog open={showWordpressHelp} onOpenChange={setShowWordpressHelp}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>How to Find and Create an Application Password in WordPress</DialogTitle>
          </DialogHeader>
          <div className="prose max-w-none">
            <p>
              Follow these simple steps to generate an application password, which allows other services (like Zapier or
              publishing tools) to post directly to your WordPress site:
            </p>

            <ol>
              <li>Log in to your WordPress site as an administrator.</li>
              <li>
                In the dashboard, go to <strong>Users</strong> &gt; <strong>Profile</strong> (sometimes labeled as "Your
                Profile").
              </li>
              <li>
                Scroll down until you see the <strong>Application Passwords</strong> section.
              </li>
              <li>
                In the field provided, enter a descriptive name for the app or service you want to connect (e.g.,
                "Zapier" or "Mobile App").
              </li>
              <li>
                Click the <strong>Add New Application Password</strong> button.
              </li>
              <li>
                A new password will appear on the screen. <strong>Copy and save it immediately</strong>—you won't be
                able to see it again once you leave the page.
              </li>
              <li>
                Use this password (along with your WordPress username) in the third-party service to authenticate and
                connect to your site.
              </li>
            </ol>

            <h3>Tips:</h3>
            <ul>
              <li>Create a separate application password for each service you connect.</li>
              <li>
                If you ever want to remove access, return to this section and click "Revoke" next to the app password
                you want to disable.
              </li>
              <li>
                If you don't see the Application Passwords section, make sure your WordPress version is 5.6 or higher
                and that you have the right permissions.
              </li>
            </ul>

            <p>This process makes connecting apps secure and easy—no need to share your main WordPress password!</p>
          </div>
          <DialogFooter>
            <Button onClick={() => setShowWordpressHelp(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
