"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Header } from "@/components/Header"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { ChevronLeft, RotateCw, Check } from "lucide-react"
import { Separator } from "@/components/ui/separator"
import {
  linkedinConnect,
  twitterConnect,
  wordpressConnect,
  storeClaudeKey,
  storeOpenAIKey,
  getUserCredentials,
} from "@/components/Service"

interface PlatformConnection {
  apiKey?: string
  secretKey?: string
  accessToken?: string
  appSecret?: string
  clientSecret?: string
  applicationPassword?: string
}

const MODEL_PLATFORMS = ["OpenAI", "Claude"] // "Midjourney", "Eleven Labs" - commented out for now
const SOCIAL_PLATFORMS = ["Instagram", "Facebook", "YouTube", "Twitter", "LinkedIn", "WordPress", "TikTok"]
const ALL_PLATFORMS = [...MODEL_PLATFORMS, ...SOCIAL_PLATFORMS]

export default function AccountSettings() {
  const [connections, setConnections] = useState<Record<string, PlatformConnection>>({})
  const [successMessage, setSuccessMessage] = useState<Record<string, string | null>>({})
  const [savingPlatform, setSavingPlatform] = useState<string | null>(null)
  const [activePlatforms, setActivePlatforms] = useState<Record<string, boolean>>(
    ALL_PLATFORMS.reduce(
      (acc, platform) => ({
        ...acc,
        [platform]: false,
      }),
      {},
    ),
  )
  
  // Load selected platforms from onboarding
  useEffect(() => {
    const selectedPlatformsStr = localStorage.getItem("selected_platforms")
    if (selectedPlatformsStr) {
      try {
        const selectedPlatforms = JSON.parse(selectedPlatformsStr)
        // Set active platforms based on onboarding selections
        setActivePlatforms((prev) => {
          const updated = { ...prev }
          ALL_PLATFORMS.forEach((platform) => {
            // Enable if selected in onboarding, or if already enabled
            updated[platform] = selectedPlatforms[platform] === true || prev[platform] === true
          })
          return updated
        })
      } catch (e) {
        console.error("Failed to parse selected platforms:", e)
      }
    }
  }, [])

  const [mergedData, setMergedData] = useState<(PlatformConnection & { platform: string })[]>([])
  const [siteUrl, setSiteUrl] = useState("")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")

  const [linkedinConnected, setLinkedinConnected] = useState(false)
  const [twitterConnected, setTwitterConnected] = useState(false)
  const [wordpressConnected, setWordpressConnected] = useState(false)

  const [linkedinLoading, setLinkedinLoading] = useState(false)
  const [twitterLoading, setTwitterLoading] = useState(false)
  const [wordpressLoading, setWordpressLoading] = useState(false)

  const [linkedinSuccessMessage, setLinkedinSuccessMessage] = useState<string | null>(null)
  const [twitterSuccessMessage, setTwitterSuccessMessage] = useState<string | null>(null)
  const [wordpressSuccessMessage, setWordpressSuccessMessage] = useState<string | null>(null)

  const [linkedinMessageType, setLinkedinMessageType] = useState<"success" | "error" | null>(null)
  const [twitterMessageType, setTwitterMessageType] = useState<"success" | "error" | null>(null)
  const [wordpressMessageType, setWordpressMessageType] = useState<"success" | "error" | null>(null)

  const [wordpressConnecting, setWordpressConnecting] = useState(true)

  const [isSignInPhase, setIsSignInPhase] = useState(true)

  useEffect(() => {
    const initialConnections = Object.fromEntries(mergedData.map((item) => [item.platform, item]))
    setConnections(initialConnections)
  }, [mergedData])

  useEffect(() => {
    // Check if user has connected any platforms to determine if still in sign-in phase
    const hasConnections = linkedinConnected || twitterConnected || wordpressConnected
    if (hasConnections) {
      setIsSignInPhase(false)
    }
  }, [linkedinConnected, twitterConnected, wordpressConnected])

  // Fetch stored credentials on component mount
  useEffect(() => {
    const fetchStoredCredentials = async () => {
      try {
        console.log("🔍 Fetching stored credentials...");
        const response = await getUserCredentials()
        console.log("🔍 getUserCredentials response:", response);
        
        if (response.success && response.credentials) {
          const { openai_key, claude_key } = response.credentials
          console.log("🔍 Found credentials:", { openai_key: openai_key ? "***" : "null", claude_key: claude_key ? "***" : "null" });
          
          // Update connections with stored API keys
          setConnections(prev => ({
            ...prev,
            "OpenAI": { apiKey: openai_key || "" },
            "Claude": { apiKey: claude_key || "" },
          }))
          
          // Update active platforms based on stored keys
          setActivePlatforms(prev => ({
            ...prev,
            "OpenAI": !!openai_key,
            "Claude": !!claude_key,
          }))
        } else {
          console.log("🔍 No credentials found or error:", response);
        }
      } catch (error) {
        console.error("Failed to fetch stored credentials:", error)
      }
    }

    fetchStoredCredentials()
  }, [])

  // Add a function to refresh credentials (can be called manually)
  const refreshCredentials = async () => {
    try {
      console.log("🔄 Refreshing credentials...");
      const response = await getUserCredentials()
      console.log("🔄 Refresh response:", response);
      
      if (response.success && response.credentials) {
        const { openai_key, claude_key } = response.credentials
        console.log("🔄 Refreshed credentials:", { openai_key: openai_key ? "***" : "null", claude_key: claude_key ? "***" : "null" });
        
        setConnections(prev => {
          const newConnections = {
            ...prev,
            "OpenAI": { apiKey: openai_key || "" },
            "Claude": { apiKey: claude_key || "" },
          };
          console.log("🔄 Updated connections:", newConnections);
          return newConnections;
        })
        
        setActivePlatforms(prev => {
          const newActivePlatforms = {
            ...prev,
            "OpenAI": !!openai_key,
            "Claude": !!claude_key,
          };
          console.log("🔄 Updated active platforms:", newActivePlatforms);
          return newActivePlatforms;
        })
      } else {
        console.log("❌ No credentials found or error in response");
      }
    } catch (error) {
      console.error("Failed to refresh credentials:", error)
    }
  }

  const handleLinkedInConnect = async () => {
    setLinkedinLoading(true)
    try {
      const result = await linkedinConnect()
      if (result && result.success) {
        setLinkedinConnected(true)
        setLinkedinSuccessMessage("LinkedIn connected successfully!")
        setLinkedinMessageType("success")
        localStorage.setItem("linkedin_connected", "true")

        setTimeout(() => {
          setLinkedinSuccessMessage(null)
          setLinkedinMessageType(null)
        }, 5000)
      } else {
        // setLinkedinSuccessMessage("LinkedIn connection failed.");
        // setLinkedinMessageType("error");
        setTimeout(() => {
          setLinkedinSuccessMessage(null)
          setLinkedinMessageType(null)
        }, 5000)
      }
    } catch (e) {
      console.error("LinkedIn connection failed:", e)
      setLinkedinSuccessMessage("Error connecting to LinkedIn.")
      setLinkedinMessageType("error")
      setTimeout(() => {
        setLinkedinSuccessMessage(null)
        setLinkedinMessageType(null)
      }, 5000)
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
        setTwitterSuccessMessage("Twitter connected successfully!")
        setTwitterMessageType("success")
        localStorage.setItem("twitter_connected", "true")
        setTimeout(() => {
          setTwitterSuccessMessage(null)
          setTwitterMessageType(null)
        }, 5000)
      } else {
        // setTwitterSuccessMessage("Twitter connection failed.");
        // setTwitterMessageType("error");
        setTimeout(() => {
          setTwitterSuccessMessage(null)
          setTwitterMessageType(null)
        }, 5000)
      }
    } catch (e) {
      console.error("Twitter connection failed:", e)
      setTwitterSuccessMessage("Error connecting to Twitter.")
      setTwitterMessageType("error")
      setTimeout(() => {
        setTwitterSuccessMessage(null)
        setTwitterMessageType(null)
      }, 5000)
    } finally {
      setTwitterLoading(false)
    }
  }

  const handleWordpressConnect = async () => {
    setWordpressLoading(true)
    try {
      const result = await wordpressConnect(siteUrl, username, password)
      if (result && result.message === "WordPress connected successfully") {
        setWordpressConnected(true)
        setWordpressSuccessMessage(result.message)
        setWordpressMessageType("success")
        localStorage.setItem("wordpress_connected", "true")
        setWordpressConnecting(false)
        setTimeout(() => {
          setWordpressSuccessMessage(null)
          setWordpressMessageType(null)
        }, 5000)
      } else {
        setWordpressSuccessMessage("Connection failed. Try again.")
        setWordpressMessageType("error")
        setTimeout(() => {
          setWordpressSuccessMessage(null)
          setWordpressMessageType(null)
        }, 5000)
      }
    } catch (error) {
      console.error("WordPress connection failed:", error)
      setWordpressSuccessMessage("Error connecting to WordPress.")
      setWordpressMessageType("error")
      setTimeout(() => {
        setWordpressSuccessMessage(null)
        setWordpressMessageType(null)
      }, 5000)
    } finally {
      setWordpressLoading(false)
    }
  }

  const handleLinkedInDisconnect = () => {
    setLinkedinConnected(false)
    setLinkedinSuccessMessage(null)
    setLinkedinMessageType(null)
    localStorage.removeItem("linkedin_connected")
  }

  const handleTwitterDisconnect = () => {
    setTwitterConnected(false)
    setTwitterSuccessMessage(null)
    setTwitterMessageType(null)
    localStorage.removeItem("twitter_connected")
  }

  const handleWordpressDisconnect = () => {
    setWordpressConnected(false)
    setWordpressSuccessMessage(null)
    setWordpressMessageType(null)
    localStorage.removeItem("wordpress_connected")
    setSiteUrl("")
    setUsername("")
    setPassword("")
  }

  const handleLogout = () => {
    localStorage.removeItem("token")
    setWordpressConnected(false)
    setLinkedinConnected(false)
    setTwitterConnected(false)
    setWordpressSuccessMessage(null)
    setLinkedinSuccessMessage(null)
    setTwitterSuccessMessage(null)
    setWordpressMessageType(null)
    setLinkedinMessageType(null)
    setTwitterMessageType(null)
    window.location.href = "/login"
  }

  useEffect(() => {
    const linkedinStored = localStorage.getItem("linkedin_connected")
    const twitterStored = localStorage.getItem("twitter_connected")
    const wordpressStored = localStorage.getItem("wordpress_connected")

    if (linkedinStored === "true") setLinkedinConnected(true)
    if (twitterStored === "true") setTwitterConnected(true)
    if (wordpressStored === "true") setWordpressConnected(true)
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)

    const handleConnectionCallback = (
      key: string,
      setState: (val: boolean) => void,
      setSuccessMessage: (msg: string | null) => void,
      setMessageType: (type: "success" | "error" | null) => void,
    ) => {
      if (params.get(`${key}_connected`) === "true") {
        localStorage.setItem(`${key}_connected`, "true")
        setState(true)
        setSuccessMessage(`${key.charAt(0).toUpperCase() + key.slice(1)} connected successfully!`)
        setMessageType("success")
        setTimeout(() => {
          setSuccessMessage(null)
          setMessageType(null)
        }, 5000)

        params.delete(`${key}_connected`)
        window.history.replaceState({}, "", `${window.location.pathname}`)
      }
    }

    handleConnectionCallback("linkedin", setLinkedinConnected, setLinkedinSuccessMessage, setLinkedinMessageType)
    handleConnectionCallback("twitter", setTwitterConnected, setTwitterSuccessMessage, setTwitterMessageType)
    handleConnectionCallback("wordpress", setWordpressConnected, setWordpressSuccessMessage, setWordpressMessageType)
  }, [])

  const handleInputChange = (platform: string, field: keyof PlatformConnection, value: string) => {
    setConnections((prev) => ({
      ...prev,
      [platform]: {
        ...prev[platform],
        [field]: value,
      },
    }))
  }

  const handleCheckboxChange = (platform: string, checked: boolean) => {
    setActivePlatforms((prev) => ({
      ...prev,
      [platform]: checked,
    }))
  }

  const handleSave = async (platform: string) => {
    if (!activePlatforms[platform]) return
    setSavingPlatform(platform)

    try {
      let result
      const apiKey = connections[platform]?.apiKey?.trim() || ""

      if (!apiKey) {
        setSuccessMessage((prev) => ({
          ...prev,
          [platform]: "API key is required",
        }))
        setTimeout(() => {
          setSuccessMessage((prev) => ({ ...prev, [platform]: null }))
        }, 3000)
        setSavingPlatform(null)
        return
      }

      switch (platform) {
        case "Claude":
          result = await storeClaudeKey(apiKey)
          break
        case "Eleven Labs":
          // result = await storeElevenLabsKey(apiKey) // Function not available
          result = { success: false, message: "ElevenLabs key storage not implemented" }
          break
        case "Midjourney":
          // result = await storeMidjourneyKey(apiKey) // Function not available
          result = { success: false, message: "Midjourney key storage not implemented" }
          break
        case "OpenAI":
          result = await storeOpenAIKey(apiKey)
          break
        default:
          console.log(`Saving connection for ${platform}:`, connections[platform])
          await new Promise((resolve) => setTimeout(resolve, 2000))
          result = { success: true, message: `${platform} settings saved` }
      }

      setSuccessMessage((prev) => ({
        ...prev,
        [platform]: result.message,
      }))
      setTimeout(() => {
        setSuccessMessage((prev) => ({ ...prev, [platform]: null }))
      }, 3000)
    } catch (error: any) {
      console.error(`Error saving ${platform} settings:`, error)
      const errorMessage = error?.detail?.[0]?.msg || `Failed to save ${platform} settings`
      setSuccessMessage((prev) => ({
        ...prev,
        [platform]: errorMessage,
      }))
      setTimeout(() => {
        setSuccessMessage((prev) => ({ ...prev, [platform]: null }))
      }, 3000)
    } finally {
      setSavingPlatform(null)
    }
  }

  const handleEnablePlatform = (platform: string) => {
    setActivePlatforms((prev) => ({
      ...prev,
      [platform]: true,
    }))
    // Update selected platforms in localStorage
    const selectedPlatformsStr = localStorage.getItem("selected_platforms")
    if (selectedPlatformsStr) {
      try {
        const selectedPlatforms = JSON.parse(selectedPlatformsStr)
        selectedPlatforms[platform] = true
        localStorage.setItem("selected_platforms", JSON.stringify(selectedPlatforms))
      } catch (e) {
        console.error("Failed to update selected platforms:", e)
      }
    }
  }

  const renderPlatformCard = (platform: string) => {
    const isDisabled = ["YouTube", "TikTok", "Claude", "Eleven Labs"].includes(platform)
    const isActive = activePlatforms[platform] && !isDisabled
    const fields = (() => {
      switch (platform) {
        case "OpenAI":
        case "Claude":
        case "Eleven Labs":
        case "YouTube":
          return [{ key: "apiKey", label: "API Key" }]
        case "Instagram":
        case "Facebook":
        case "TikTok":
          return [
            { key: "accessToken", label: "Access Token" },
            { key: "appSecret", label: "App Secret" },
          ]
        case "Twitter":
          return [
            { key: "apiKey", label: "API Key" },
            { key: "secretKey", label: "API Secret Key" },
          ]
        case "LinkedIn":
          return [
            { key: "accessToken", label: "Access Token" },
            { key: "clientSecret", label: "Client Secret" },
          ]
        case "WordPress":
          return [{ key: "applicationPassword", label: "Application Password" }]
        default:
          return [
            { key: "apiKey", label: "API Key" },
            { key: "secretKey", label: "Secret Key" },
          ]
      }
    })()

    return (
      <Card
        key={platform}
        className={`transition-all duration-300 ${isActive ? "opacity-100" : "opacity-50"}`}
      >
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-base font-medium">
            {platform} Connection
            {isDisabled && <span className="ml-2 text-sm text-gray-500">(Coming Soon)</span>}
          </CardTitle>
          <Checkbox
            checked={isActive}
            onCheckedChange={(checked) => !isDisabled && handleCheckboxChange(platform, checked as boolean)}
            disabled={isDisabled}
          />
        </CardHeader>
        <CardContent className="space-y-4">
          {isActive ? (
            <>
              {fields.map(({ key, label }) => (
                <div key={key} className="space-y-2">
                  <h3 className="text-[1.1rem] font-semibold">{label}</h3>
                  <Input
                    id={`${platform}-${key}`}
                    type="password"
                    value={connections[platform]?.[key as keyof PlatformConnection] || ""}
                    onChange={(e) => handleInputChange(platform, key as keyof PlatformConnection, e.target.value)}
                    disabled={isDisabled}
                  />
                </div>
              ))}
              <div className="relative pt-10">
                <Button
                  onClick={() => handleSave(platform)}
                  disabled={savingPlatform === platform || isDisabled}
                  className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90 disabled:opacity-50"
                >
                  {savingPlatform === platform ? (
                    <>
                      <RotateCw className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    `Save ${platform} Connection`
                  )}
                </Button>
                {successMessage[platform] && (
                  <div
                    className={`absolute left-0 right-0 top-0 flex items-center justify-center font-medium ${
                      successMessage[platform]?.toLowerCase().includes("error") ||
                      successMessage[platform]?.toLowerCase().includes("failed") ||
                      successMessage[platform]?.toLowerCase().includes("required")
                        ? "text-red-600"
                        : "text-green-600"
                    }`}
                  >
                    <Check className="w-4 h-4 mr-1" />
                    {successMessage[platform]}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="py-4 text-center">
              <p className="text-gray-500 mb-4">
                {isDisabled
                  ? "This platform is not yet available."
                  : "This platform is not enabled. Enable it to configure settings."}
              </p>
              {!isDisabled && (
                <Button
                  onClick={() => handleEnablePlatform(platform)}
                  className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                >
                  Enable this Platform
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <Header />
      <main className="container max-w-6xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href="/dashboard/content-planner" className="flex items-center text-white hover:text-gray-200">
              <ChevronLeft className="h-5 w-5 mr-1" />
              Back to Dashboard
            </Link>
            <h1 className="text-4xl font-extrabold text-white">Account Settings</h1>
          </div>
          <div className="flex space-x-2">
            <Button 
              onClick={refreshCredentials}
              variant="outline"
              className="bg-white text-gray-700 hover:bg-gray-100"
            >
              <RotateCw className="h-4 w-4 mr-2" />
              Refresh Credentials
            </Button>
            <Button 
              onClick={async () => {
                try {
                  const response = await fetch('/api/test-credentials');
                  const data = await response.json();
                  console.log("🧪 Test endpoint response:", data);
                  alert(`Test response: ${JSON.stringify(data, null, 2)}`);
                } catch (error) {
                  console.error("Test endpoint error:", error);
                  alert(`Test error: ${error}`);
                }
              }}
              variant="outline"
              className="bg-blue-100 text-blue-700 hover:bg-blue-200"
            >
              Test API
            </Button>
          </div>
        </div>

        <div className="space-y-10">
          <div className="bg-white p-6 rounded-lg shadow">
            {isSignInPhase && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
                <h2 className="text-2xl font-bold text-blue-900 mb-2">Welcome to Vernal Contentum</h2>
                <p className="text-blue-800 mb-4">
                  Please take a moment to connect the platforms you intend to use when creating content. If you are not
                  ready, simply skip for now.
                </p>
                <Link href="/dashboard/content-planner">
                  <Button className="bg-blue-600 text-white hover:bg-blue-700">Skip to Dashboard</Button>
                </Link>
              </div>
            )}

            <h2 className="text-2xl font-semibold mb-4">Connect to Social Media Platforms</h2>

            <div className="flex flex-wrap gap-6">
              <Card className="flex-1 pt-6">
                <CardContent className="space-y-4">
                  <Button
                    className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                    onClick={linkedinConnected ? handleLinkedInDisconnect : handleLinkedInConnect}
                    disabled={linkedinLoading}
                  >
                    {linkedinLoading ? (
                      <>
                        <RotateCw className="mr-2 h-4 w-4 animate-spin" />
                        Connecting to LinkedIn...
                      </>
                    ) : linkedinConnected ? (
                      "Disconnect LinkedIn"
                    ) : (
                      "Connect to LinkedIn"
                    )}
                  </Button>
                  {linkedinSuccessMessage && (
                    <div className={linkedinMessageType === "success" ? "text-green-600" : "text-red-600"}>
                      {linkedinSuccessMessage}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="flex-1 pt-6">
                <CardContent className="space-y-4">
                  <Button
                    className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                    onClick={twitterConnected ? handleTwitterDisconnect : handleTwitterConnect}
                    disabled={twitterLoading}
                  >
                    {twitterLoading ? (
                      <>
                        <RotateCw className="mr-2 h-4 w-4 animate-spin" />
                        Connecting to Twitter...
                      </>
                    ) : twitterConnected ? (
                      "Disconnect Twitter"
                    ) : (
                      "Connect to Twitter"
                    )}
                  </Button>
                  {twitterSuccessMessage && (
                    <div className={twitterMessageType === "success" ? "text-green-600" : "text-red-600"}>
                      {twitterSuccessMessage}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="flex-1 pt-6">
                <CardContent className="space-y-4">
                  {!wordpressConnected && !wordpressConnecting && (
                    <Button
                      className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                      onClick={() => setWordpressConnecting(true)}
                    >
                      Connect to WordPress
                    </Button>
                  )}

                  {wordpressConnecting && !wordpressConnected && (
                    <>
                      <div className="space-y-2">
                        <input
                          type="text"
                          className="border rounded p-2 w-full"
                          placeholder="WordPress Site URL"
                          value={siteUrl}
                          onChange={(e) => setSiteUrl(e.target.value)}
                        />
                        <input
                          type="text"
                          className="border rounded p-2 w-full"
                          placeholder="Username"
                          value={username}
                          onChange={(e) => setUsername(e.target.value)}
                        />
                        <input
                          type="password"
                          className="border rounded p-2 w-full"
                          placeholder="App Password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                        />
                      </div>

                      <Button
                        className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90 mt-4"
                        onClick={handleWordpressConnect}
                        disabled={wordpressLoading}
                      >
                        {wordpressLoading ? (
                          <>
                            <RotateCw className="mr-2 h-4 w-4 animate-spin" />
                            Connecting to WordPress...
                          </>
                        ) : (
                          "Connect to WordPress"
                        )}
                      </Button>
                    </>
                  )}

                  {wordpressConnected && (
                    <>
                      <Button
                        className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                        onClick={handleWordpressDisconnect}
                      >
                        Disconnect WordPress
                      </Button>
                      {wordpressSuccessMessage && (
                        <div
                          className={wordpressMessageType === "success" ? "text-green-600 mt-2" : "text-red-600 mt-2"}
                        >
                          {wordpressSuccessMessage}
                        </div>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">Model Credentials</h2>
            <Separator className="my-4" />
            <div className="grid gap-6 md:grid-cols-2">{MODEL_PLATFORMS.map(renderPlatformCard)}</div>
          </div>
        </div>
      </main>
    </div>
  )
}
