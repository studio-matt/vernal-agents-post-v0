"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, Loader2, Check } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import {
  plateformScriptAgent,
  plateformScriptTask,
  regenerateContentAgent,
  regenerateContentTask,
  linkedinConnect,
  twitterConnect,
  wordpressConnect,
} from "@/components/Service";
import { ErrorDialog } from "@/components/ErrorDialog";

interface PlatformConnection {
  role?: string;
  goal?: string;
  backstory?: string;
  description?: string;
  expected_output?: string;
}

const PLATFORMS_SCRIPT_REGENERATOR = [
  // "Script_Research",
  // "QC",
  // "Script_Rewriter",
  // "Regenrate_Content",
  // "Regenrate_Subcontent",
  "Instagram",
  "Facebook",
  "YouTube",
  "Twitter",
  "LinkedIn",
  "WordPress",
  "TikTok",
  "Script_Research",
  "QC",
  "Script_Rewriter",
  "Regenrate_Content",
  "Regenrate_Subcontent",
];

export default function AccountSettings() {
  const [mergedData, setMergedData] = useState<
    (PlatformConnection & { platform: string })[]
  >([]);
  const [siteUrl, setSiteUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingPlatform, setSavingPlatform] = useState<string | null>(null);
  const [connections, setConnections] = useState<
    Record<string, PlatformConnection>
  >({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showErrorDialog, setShowErrorDialog] = useState(false);

  const handleInputChange = (
    platform: string,
    key: keyof PlatformConnection,
    value: string
  ) => {
    setConnections((prev) => ({
      ...prev,
      [platform]: {
        ...prev[platform],
        [key]: value,
      },
    }));
  };

  const [linkedinConnected, setLinkedinConnected] = useState(false);
  const [twitterConnected, setTwitterConnected] = useState(false);
  const [wordpressConnected, setWordpressConnected] = useState(false);

  const [linkedinSuccessMessage, setLinkedinSuccessMessage] = useState<
    string | null
  >(null);
  const [twitterSuccessMessage, setTwitterSuccessMessage] = useState<
    string | null
  >(null);
  const [wordpressSuccessMessage, setWordpressSuccessMessage] = useState<
    string | null
  >(null);

  const [wordpressConnecting, setWordpressConnecting] = useState(false);

  const fetchAgentScripts = useCallback(async () => {
    try {
      setLoading(true);
      const [agentResponses, taskResponses] = await Promise.all([
        Promise.all(
          PLATFORMS_SCRIPT_REGENERATOR.map((platform) =>
            plateformScriptAgent(platform.toLowerCase()).catch(() => ({
              role: "",
              goal: "",
              backstory: "",
            }))
          )
        ),
        Promise.all(
          PLATFORMS_SCRIPT_REGENERATOR.map((platform) =>
            plateformScriptTask(platform.toLowerCase()).catch(() => ({
              description: "",
              expected_output: "",
            }))
          )
        ),
      ]);

      const merged = PLATFORMS_SCRIPT_REGENERATOR.map((platform, index) => ({
        platform,
        ...agentResponses[index],
        ...taskResponses[index],
      }));
      setMergedData(merged);
    } catch {
      setError("An error occurred while fetching data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgentScripts();
  }, [fetchAgentScripts]);

  const handleRegenerate = async (
    platformData: PlatformConnection & { platform: string }
  ) => {
    setSavingPlatform(platformData.platform);
    setSuccessMessage("");
    try {
      await regenerateContentAgent({
        agentName: platformData.platform.toLowerCase(),
        role: platformData.role || "",
        goal: platformData.goal || "",
        backstory: platformData.backstory || "",
      });

      await regenerateContentTask({
        agentName: platformData.platform.toLowerCase(),
        description: platformData.description || "",
        expectedOutput: platformData.expected_output || "",
      });
      setSuccessMessage(
        "Task updated successfully. Database re-initialized with latest definitions."
      );
      setTimeout(() => {
        fetchAgentScripts();
      }, 5000);
      setTimeout(() => {
        setSuccessMessage("");
      }, 4000);
    } catch (error) {
      console.error("Unexpected error in regeneration", error);
      setErrorMessage("Unexpected error in regeneration.");
      setShowErrorDialog(true); // Show dialog
    } finally {
      setSavingPlatform(null);
    }
  };

  useEffect(() => {
    const initialConnections = Object.fromEntries(
      mergedData.map((item) => [item.platform, item])
    );
    setConnections(initialConnections);
  }, [mergedData]);

  const handleLinkedInConnect = async () => {
    setLoading(true);
    try {
      await linkedinConnect();
    } catch (e) {
      console.error("Unexpected error in handleNextStep:", error);
      setErrorMessage("Something went wrong while generating ideas.");
      setShowErrorDialog(true); // Show dialog
    } finally {
      setLoading(false);
    }
  };

  const handleTwitterConnect = async () => {
    setLoading(true);
    try {
      await twitterConnect();
    } catch (e) {
      console.error("Twitter connection failed:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleWordpressConnect = async () => {
    setLoading(true);
    try {
      const result = await wordpressConnect(siteUrl, username, password);

      if (result && result.message === "WordPress connected successfully") {
        setWordpressConnected(true);
        setWordpressSuccessMessage(result.message);
        localStorage.setItem("wordpressConnected", "true");
        setWordpressConnecting(false);
      } else {
        setWordpressSuccessMessage("Connection failed. Try again.");
      }
    } catch (error) {
      console.error(error);
      setWordpressSuccessMessage("Error connecting to WordPress.");
    }
    setLoading(false);
  };

  useEffect(() => {
    const wordpressConnectedStatus = localStorage.getItem("wordpressConnected");
    if (wordpressConnectedStatus === "true") {
      setWordpressConnected(true);
    }
  }, []);

  const handleWordpressDisconnect = () => {
    setWordpressConnected(false);
    setWordpressSuccessMessage("");
    localStorage.removeItem("wordpressConnected");
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    const checkAndSetConnection = (
      key: string,
      setState: (val: boolean) => void,
      setSuccessMessage: (msg: string | null) => void
    ) => {
      const paramValue = params.get(`${key}_connected`);
      const localValue = localStorage.getItem(`${key}_connected`);

      if (paramValue === "true") {
        localStorage.setItem(`${key}_connected`, "true");
        setState(true);
        setSuccessMessage(
          `${key.charAt(0).toUpperCase() + key.slice(1)
          } connected successfully!`
        );

        setTimeout(() => {
          setSuccessMessage(null);
        }, 5000);
      } else if (localValue === "true") {
        setState(true);
      }
    };

    checkAndSetConnection(
      "linkedin",
      setLinkedinConnected,
      setLinkedinSuccessMessage
    );
    checkAndSetConnection(
      "twitter",
      setTwitterConnected,
      setTwitterSuccessMessage
    );
    checkAndSetConnection(
      "wordpress",
      setWordpressConnected,
      setWordpressSuccessMessage
    );
  }, []);

  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <Header />
      <main className="container max-w-6xl mx-auto p-6 space-y-6">
        <div className="flex items-center space-x-4">
          <Link
            href="/dashboard"
            className="flex items-center text-white hover:text-gray-200"
          >
            <ChevronLeft className="h-5 w-5 mr-1" />
            Back to Dashboard
          </Link>
          <h1 className="text-4xl font-extrabold text-white">Admin Settings</h1>
        </div>

        <div className="space-y-10">
          {/* Connect to platforms */}
          {/* <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">
              Connect to Social Media Platform
            </h2>

            <div className="flex flex-wrap gap-6">
              
              <Card className="flex-1 pt-6">
                <CardContent className="space-y-4">
                  <Button
                    className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                    onClick={handleLinkedInConnect}
                    disabled={loading}
                  >
                    {linkedinConnected
                      ? "Disconnect LinkedIn"
                      : "Connect to LinkedIn"}
                  </Button>
                  {linkedinSuccessMessage && (
                    <div className="text-green-600">
                      {linkedinSuccessMessage}
                    </div>
                  )}
                </CardContent>
              </Card>

              
              <Card className="flex-1 pt-6">
                <CardContent className="space-y-4">
                  <Button
                    className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                    onClick={handleTwitterConnect}
                    disabled={loading}
                  >
                    {twitterConnected
                      ? "Disconnect Twitter"
                      : "Connect to Twitter"}
                  </Button>
                  {twitterSuccessMessage && (
                    <div className="text-green-600">
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
                        disabled={loading}
                      >
                        {loading
                          ? "Connecting... to WordPress"
                          : "Connect to WordPress"}
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
                        <div className="text-green-600 mt-2">
                          {wordpressSuccessMessage}
                        </div>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          </div> */}

          {/* Script Regenerator */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">Script Regenerator</h2>
            <Separator className="my-4" />
            <div className="grid gap-6 md:grid-cols-2">
              {Object.entries(connections).map(([platform, platformData]) => (
                <Card key={platform}>
                  <CardHeader>
                    <CardTitle className="text-base font-medium">
                      <strong>{platform}</strong>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      {Object.entries(platformData).map(([key, value]) => {
                        if (["platform"].includes(key)) return null;
                        const label = key
                          .replace(/_/g, " ")
                          .replace(/\b\w/g, (char) => char.toUpperCase());

                        return (
                          <div key={key} className="space-y-2">
                            <h3 className="text-[1.1rem] font-semibold">
                              {label}
                            </h3>
                            <textarea
                              id={`${platform}-${key}`}
                              value={
                                platformData[key as keyof PlatformConnection] ||
                                ""
                              }
                              onChange={(e) =>
                                handleInputChange(
                                  platform,
                                  key as keyof PlatformConnection,
                                  e.target.value
                                )
                              }
                              className="resize-none p-2 border border-gray-300 rounded-md"
                              style={{ width: "100%", height: "150px" }}
                            />
                          </div>
                        );
                      })}
                    </div>
                    <div className="relative pt-10">
                      {loading ? (
                        <div className="flex justify-center items-center min-h-[200px]">
                          <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
                        </div>
                      ) : (
                        <Button
                          className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                          onClick={() =>
                            handleRegenerate({
                              ...platformData,
                              platform: platform,
                            })
                          }
                          disabled={savingPlatform === platform}
                        >
                          {savingPlatform === platform
                            ? "Regenerating..."
                            : "Regenerate Script"}
                        </Button>
                      )}
                      {successMessage && (
                        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 bg-green-100 border border-green-500 text-green-700 px-4 py-2 rounded-lg shadow-lg flex items-center">
                          <Check className="w-4 h-4 mr-2" />
                          {successMessage}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
        <div>
          <ErrorDialog
            isOpen={showErrorDialog}
            onClose={() => setShowErrorDialog(false)}
            message={errorMessage || ''}
          />
        </div>
      </main>
    </div>
  );
}
