"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Textarea } from "@/components/ui/textarea";
import {
  ArrowLeft,
  ArrowRight,
  Calendar,
  RefreshCw,
  X,
  Wand2,
  Upload,
  AlertCircle, // Import AlertCircle for error icon
} from "lucide-react";
import {
  Tooltip,
  TooltipProvider,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import Image from "next/image";
import { Instagram, Facebook, Twitter, Linkedin, Music } from "lucide-react";
import {
  generateContentAPI,
  regenerateContentAPI,
  generateImageMachineContent,
  generateIdeas,
  scheduleTime,
} from "./Service";
import { Header } from "./Header";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle, // Use AlertDialogTitle
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { ErrorDialog } from "./ErrorDialog";

interface ContentCreationFlowProps {
  selectedItems: Array<{
    id: string;
    type: string;
    name: string;
    source: string;
  }>;
  onClose: () => void;
}

export function ContentCreationFlow({
  selectedItems,
  onClose,
}: ContentCreationFlowProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [showTime, setShowTime] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [contentIdeas, setContentIdeas] = useState([]);
  const [defaultPosts, setDefaultPosts] = useState("3");
  const [ideas, setIdeas] = useState([]);
  const [hoveredImage, setHoveredImage] = useState<string | null>(null);
  const [regeneratingContent, setRegeneratingContent] = useState<string | null>(
    null
  );
  // State to store the selected time
  const [selectedTime, setSelectedTime] = useState<string>('09:00');
  const [regeneratingImage, setRegeneratingImage] = useState(null);
  // const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // const [errormsg, setErrorMsg] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showErrorDialog, setShowErrorDialog] = useState(false);

  const [contentGenPayload, setContentGenPayload] = useState(() => {
    const stored = localStorage.getItem("contentGenPayload");
    return stored ? JSON.parse(stored) : {};
  });

  type Platform = "Instagram" | "Facebook" | "Twitter" | "LinkedIn" | "TikTok";

  const platformIcons: Record<Platform, JSX.Element> = {
    Instagram: <Instagram className="h-5 w-5" />,
    Facebook: <Facebook className="h-5 w-5" />,
    Twitter: <Twitter className="h-5 w-5" />,
    LinkedIn: <Linkedin className="h-5 w-5" />,
    TikTok: <Music className="h-5 w-5" />,
  };

  const isValidPlatform = (platform: string): platform is Platform =>
    platform in platformIcons;


  const handleNextStep = async () => {
    if (currentStep == 1) {
      try {
        setIsLoading(true);
        const response = await generateIdeas();

        if (response.status === 'success') {
          setIdeas(response.message.ideas); // Update the ideas in the UI

          const data = localStorage.getItem("contentGenPayload") || "{}";
          const parsed = JSON.parse(data);
          const newData = { ...parsed, ideas: response.message.ideas?.map(item => item) };
          localStorage.setItem("contentGenPayload", JSON.stringify(newData));

          // Proceed to the next step
          setCurrentStep((prev) => Math.min(prev + 1, 3));
        } else {
          // Handle the error case, optionally show a message to the user
          console.error("Failed to generate ideas:", response.message);
          setErrorMessage(response.message || "Unexpected error occurred.");
          setShowErrorDialog(true); // Show dialog
        }
      } catch (error) {
        console.error("Unexpected error in handleNextStep:", error);
        setErrorMessage("Something went wrong while generating ideas.");
        setShowErrorDialog(true); // Show dialog
      } finally {
        setIsLoading(false);
      }
    } else if (currentStep === 2) {
      setIsLoading(true);
      try {
        const response = await generateContentAPI();
        console.log("response message - ", response.message);
        if (response?.message === "Request failed with status code 401") {
          setErrorMessage("Invalid token, Please login again.");
          return;
        }

        if (response?.status === "success" && Array.isArray(response.message)) {
          const mappedIdeas = response.message.map((item, index) => ({
            id: item.id,
            title: item.title || "Untitled",
            description: item.content || "",
            keywords: [item.topic, item.day].filter(Boolean),
            platforms: item.platform ? [item.platform] : [],
            image: "",
          }));

          setContentIdeas(mappedIdeas);
          setCurrentStep((prev) => Math.min(prev + 1, 3));
        } else {
          console.error("Failed to generate ideas:", response.message);
          setErrorMessage(response.message || response.message || "Unexpected error occurred.");
          setShowErrorDialog(true); // Show dialog
        }
      } catch (e) {
        console.error("Unexpected error in handleNextStep:", e);
        setErrorMessage("Something went wrong while generating posts.");
        setShowErrorDialog(true); // Show dialog
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handlePreviousStep = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  const handleRegenerateIdeas = async () => {
    try {
      setIsLoading(true);
      const response = await generateIdeas();

      if (response.status === 'success') {
        setIdeas(response.message.ideas); // Update the ideas in the UI

        const data = localStorage.getItem("contentGenPayload") || "{}";
        const parsed = JSON.parse(data);
        const newData = { ...parsed, ideas: response.message.ideas?.map(item => item) };
        localStorage.setItem("contentGenPayload", JSON.stringify(newData));
      } else {
        // Handle the error case, optionally show a message to the user
        console.error("Failed to generate ideas:", response.message);
        setErrorMessage(response.message || "Unexpected error occurred.");
        setShowErrorDialog(true); // Show dialog
      }
    } catch (error) {
      console.error("Unexpected error in handleNextStep:", error);
      setErrorMessage("Something went wrong while generating ideas.");
      setShowErrorDialog(true); // Show dialog
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveIdea = (ideaId: string) => {
    setContentIdeas((prev) => prev.filter((idea) => idea.id !== ideaId));
  };

  const handleRegenerateContent = async (ideaId) => {
    setRegeneratingContent(ideaId);
    try {
      const idea = contentIdeas.find((item) => item.id === ideaId);
      if (!idea) {
        console.error("Idea not found:", ideaId);
        return;
      }

      const platform = idea.platforms[0] || "Twitter";
      const response = await regenerateContentAPI({
        id: ideaId,
        query: idea.description,
        platform,
      });

      if (response.status === "success") {
        setContentIdeas((prev) =>
          prev.map((item) =>
            item.id === ideaId
              ? {
                ...item,
                title: response.message.title || item.title,
                description: response.message.topic || item.description,
                platforms: [response.message.platform] || item.platforms,
                keywords: item.keywords,
              }
              : item
          )
        );
      } else {
        console.error("Regeneration failed:", response.message);
      }
    } catch (error) {
      console.error("Error regenerating content:", error);
      setErrorMessage("Error regenerating content.");
      setShowErrorDialog(true); // Show dialog
    }
    finally {
      setRegeneratingContent(null);
    }
  };

  const handleRegenerateImage = async (ideaId: string, content: string) => {
    setRegeneratingImage(ideaId);
    try {
      const response = await generateImageMachineContent({
        id: ideaId,
        query: content,
      });
      if (response.status === "success") {
        setContentIdeas((prevIdeas) => {
          const updatedIdeas = prevIdeas.map((idea) => {
            const isMatch = idea.id === Number(ideaId);

            if (isMatch) {
              const updated = {
                ...idea,
                image: `${response.message}?t=${Date.now()}`,
              };
              return updated;
            }

            return idea;
          });
          return updatedIdeas;
        });
      } else {
        // Handle the error case, optionally show a message to the user
        console.error("Failed to regenerate images:", response.message);
        setErrorMessage(response.message || "Failed to regenerate images.");
        setShowErrorDialog(true); // Show dialog
      }
    } catch (e) {
      console.error("Failed to regenerate images:", e);
      setErrorMessage("Failed to regenerate images.");
      setShowErrorDialog(true); // Show dialog
    } finally {
      setRegeneratingImage(null);
    }
  };

  const getContentGenPayload = (): any => {
    const data = localStorage.getItem("contentGenPayload") || "{}";
    return JSON.parse(data);
  };

  const [activeDays, setActiveDays] = useState<string[]>(() => {
    const payload = getContentGenPayload();
    return payload.activeDays || ["Monday"];
  });

  const [activePlatforms, setActivePlatforms] = useState<string[]>(() => {
    const payload = getContentGenPayload();
    return payload.activePlatforms || ["Twitter"];
  });

  const [loader, setLoader] = useState(false)
  const [showScheduledMessage, setShowScheduledMessage] = useState(false)

  const updateContentGenPayload = (updates: Partial<any>) => {
    const current = getContentGenPayload();
    const updated = { ...current, ...updates };
    localStorage.setItem("contentGenPayload", JSON.stringify(updated));
    setContentGenPayload(updated);
  };

  useEffect(() => {
    const handleStorageChange = () => {
      const stored = localStorage.getItem("contentGenPayload");
      setContentGenPayload(stored ? JSON.parse(stored) : {});
    };

    window.addEventListener("storage", handleStorageChange);
    return () => {
      window.removeEventListener("storage", handleStorageChange);
    };
  }, []);

  useEffect(() => {
    updateContentGenPayload({ activeDays });
  }, [activeDays]);

  useEffect(() => {
    updateContentGenPayload({ activePlatforms });
  }, [activePlatforms]);

  useEffect(() => {
    updateContentGenPayload({ defaultPosts });
  }, [defaultPosts]);


  useEffect(() => {
    //useeffet commented
  }, [currentStep, contentIdeas.length]);

  console.log("contentIdeas", contentIdeas);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <div className="flex items-center space-x-4">
            <h1 className="text-4xl font-extrabold text-white">
              Loading Content Creation Flow...
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

  // Generate the time options from 00:00 to 23:00
  const timeOptions: string[] = [];
  for (let i = 0; i < 24; i++) {
    // Format time as 00:00, 01:00, ..., 23:00
    const time = i < 10 ? `0${i}:00` : `${i}:00`;
    timeOptions.push(time);
  }

  // Handle change in selected time
  const handleTimeChange = async (
    event: React.ChangeEvent<HTMLSelectElement>,
    content: string
  ) => {
    const newTime = event.target.value;
    setSelectedTime(newTime);
    console.log('newTime', newTime);
    console.log('content', content);
    try {
      const response = await scheduleTime({ newTime, content });
      if (response) {
        console.log('Time scheduled successfully:', response.message);
        setShowTime(response.message)

        setTimeout(() => {
          setShowTime("")
        }, 5000);
      } else {
        console.error('Failed to schedule the time.');
      }
    } catch (error) {
      console.error('Error scheduling time:', error);
    }
  };


  const scheduledContentLoader = () => {
    setLoader(true)
    setTimeout(() => {
      setLoader(false)
      setShowScheduledMessage(true)
    }, 3000);
  }

  if (loader) {
    return (
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <div className="flex items-center space-x-4">
            <h1 className="text-4xl font-extrabold text-white">
              Scheduling...please wait
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

  if (loader) {
    return (
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <div className="flex items-center space-x-4">
            <h1 className="text-4xl font-extrabold text-white">
              Scheduling post..Please wait
            </h1>
          </div>
          <Card>
            <CardContent className="p-6 flex justify-center items-center min-h-[400px]">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </CardContent>
          </Card>
        </main>
      </div>
    )
  }

  return (
    <TooltipProvider>
      <Card className="w-full">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Content Creation Flow</CardTitle>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">
                Step {currentStep}:{" "}
                {currentStep === 1
                  ? "Plan Settings"
                  : currentStep === 2
                    ? "Content Ideas"
                    : "The Plan"}
              </h2>
              <div className="flex space-x-2">
                <span
                  className={`w-3 h-3 rounded-full ${currentStep === 1 ? "bg-blue-600" : "bg-gray-300"
                    }`}
                ></span>
                <span
                  className={`w-3 h-3 rounded-full ${currentStep === 2 ? "bg-blue-600" : "bg-gray-300"
                    }`}
                ></span>
                <span
                  className={`w-3 h-3 rounded-full ${currentStep === 3 ? "bg-blue-600" : "bg-gray-300"
                    }`}
                ></span>
              </div>
            </div>

            {currentStep === 1 && (
              <div className="space-y-6">
                <div >
                  <h3 className="text-[1.1rem] font-semibold mb-1">
                    Default Posts per Platform
                  </h3>
                  <Input
                    type="number"
                    id="defaultPosts"
                    value={defaultPosts}
                    onChange={(e) => {
                      const value = e.target.value.slice(0, 2);
                      setDefaultPosts(value);
                    }}
                    className="w-full"
                    max="99"
                  />
                </div>
                <div>
                  <h3 className="text-[1.1rem] font-semibold mb-2">
                    Active Days
                  </h3>
                  <ToggleGroup
                    type="multiple"
                    value={activeDays}
                    onValueChange={setActiveDays}
                    className="flex flex-wrap gap-2 justify-start"
                  >
                    {[
                      "Sunday",
                      "Monday",
                      "Tuesday",
                      "Wednesday",
                      "Thursday",
                      "Friday",
                      "Saturday",
                    ].map((day) => (
                      <ToggleGroupItem
                        key={day}
                        value={day}
                        aria-label={day}
                        className={`px-3 py-2 flex-1 justify-center day-button ${activeDays.includes(day) ? "active-day" : ""
                          }`}
                      >
                        {day}
                      </ToggleGroupItem>
                    ))}
                  </ToggleGroup>
                </div>

                <div>
                  <h3 className="text-[1.1rem] font-semibold mb-2">
                    Active Platforms
                  </h3>
                  <ToggleGroup
                    type="multiple"
                    value={activePlatforms}
                    onValueChange={setActivePlatforms}
                    className="flex flex-wrap gap-2 justify-start"
                  >
                    {Object.entries({
                      Instagram: <Instagram className="h-5 w-5" />,
                      Facebook: <Facebook className="h-5 w-5" />,
                      Twitter: <Twitter className="h-5 w-5" />,
                      LinkedIn: <Linkedin className="h-5 w-5" />,
                      TikTok: <Music className="h-5 w-5" />,
                    }).map(([platform, icon]) => (
                      <Tooltip key={platform}>
                        <TooltipTrigger asChild>
                          <ToggleGroupItem
                            value={platform}
                            aria-label={platform}
                            className={`p-2 flex-1 justify-center platform-button flex items-center transition${activePlatforms.includes(platform)
                              ? "active-platform bg-muted text-black"
                              : "text-black hover:bg-gray-100"
                              }`}
                          >
                            {icon}
                            <span className="ml-2">{platform}</span>
                          </ToggleGroupItem>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{platform}</p>
                        </TooltipContent>
                      </Tooltip>
                    ))}
                  </ToggleGroup>
                </div>

                <div className="bg-blue-50 p-4 rounded-md border border-blue-100">
                  <h3 className="text-md font-medium text-blue-800 mb-2">
                    Selected Research Items
                  </h3>
                  <div className="max-h-40 overflow-y-auto">
                    <ul className="space-y-1">
                      {contentGenPayload.keywords?.length > 0 && (
                        <li className="text-sm text-blue-700">
                          Topics:
                          <ul className="ml-4 mt-1 list-disc text-blue-500">
                            {contentGenPayload.keywords.map(
                              (topic: string, index: number) => (
                                <li key={index}>{topic}</li>
                              )
                            )}
                          </ul>
                        </li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {currentStep === 2 && (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-md font-medium">
                    Generated Content Ideas
                  </h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRegenerateIdeas}
                    className="flex items-center text-blue-600"
                  >
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Regenerate Ideas
                  </Button>
                </div>

                <div className="space-y-4">
                  {(ideas || []).map((idea, index) => {
                    console.log("idea", idea);
                    return (
                      <Card key={idea?.id || index} className="overflow-hidden">
                        <CardContent className="p-4">
                          <div className="flex items-start">
                            {/* <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleRemoveIdea(idea?.id)}
                              className="text-red-500 hover:text-red-700 hover:bg-red-50 -ml-2 mr-1"
                            >
                              <X className="h-4 w-4" />
                            </Button> */}
                            <div className="flex-grow">
                              <h4 className="font-medium text-lg mb-2">
                                {idea || "Untitled"}
                              </h4>
                              {/* <p className="text-gray-600 text-sm mb-3">
                                {idea?.description || "No description provided."}
                              </p>
                              <div className="flex flex-wrap gap-2 mb-3">
                                {(idea?.keywords || []).map((keyword, kIdx) => (
                                  <span
                                    key={keyword || kIdx}
                                    className="bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded-full"
                                  >
                                    {idea}
                                  </span>
                                ))}
                              </div> */}
                              {/* <div className="flex flex-wrap gap-2">
                                {(idea?.platforms || []).map((platform, pIdx) =>
                                  isValidPlatform(platform) ? (
                                    <span
                                      key={platform || pIdx}
                                      className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full inline-flex items-center"
                                    >
                                      <span className="inline-block mr-1">
                                        {platformIcons[platform] || null}
                                      </span>
                                      {platform}
                                    </span>
                                  ) : null
                                )}
                              </div> */}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>

              </div>
            )}

            {currentStep === 3 && (
              <div className="space-y-6">
                <div className="bg-blue-50 p-4 rounded-md border border-blue-100">
                  <h3 className="text-md font-medium text-blue-800 mb-2">
                    Content Plan Summary
                  </h3>
                  <div className="space-y-2">
                    <p className="text-sm text-blue-700">
                      <span className="font-medium">Active Days:</span>{" "}
                      {activeDays.join(", ")}
                    </p>
                    <p className="text-sm text-blue-700">
                      <span className="font-medium">Platforms:</span>{" "}
                      {activePlatforms.join(", ")}
                    </p>
                    <p className="text-sm text-blue-700">
                      <span className="font-medium">Content Ideas:</span>{" "}
                      {contentIdeas.length}
                    </p>
                  </div>
                </div>

                <div>
                  <h3 className="text-md font-medium mb-3">
                    Weekly Content Calendar
                  </h3>
                  <div className="space-y-6">
                    {contentIdeas?.map((idea) => {
                      console.log("idea", idea);
                      return (
                        <div
                          key={idea.id}
                          className="border rounded-md p-4 space-y-4"
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <h4 className="font-medium text-lg">
                                {idea.title}
                              </h4>
                              <div className="flex items-center space-x-2 mt-1">
                                <span className="text-sm text-gray-500">
                                  Platforms:
                                </span>
                                {(idea.platforms || []).map((platform) =>
                                  isValidPlatform(platform) ? (
                                    <span
                                      key={platform}
                                      className="inline-flex items-center"
                                    >
                                      {platformIcons[platform]}
                                    </span>
                                  ) : null
                                )}
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleRemoveIdea(idea.id)}
                              className="text-red-500 hover:text-red-700 hover:bg-red-50"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>

                          <div>
                            <select
                              id="time"
                              value={selectedTime}
                              onChange={(e) => handleTimeChange(e, idea.description)} // Ensure 'idea' or 'content' is passed correctly
                              className="w-[180px] px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 appearance-none bg-white text-gray-700 cursor-pointer bg-no-repeat bg-[right_0.75rem_center] bg-[length:1rem]"
                              style={{
                                backgroundImage: `url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" fill="gray" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>')`,
                              }}
                            >
                              {timeOptions.map((time) => (
                                <option key={time} value={time}>
                                  {time}
                                </option>
                              ))}
                            </select>
                          </div>

                          {showTime && <p className="text-green-500">{showTime}</p>}

                          <div className="grid md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <label className="text-sm font-medium">
                                  Content
                                </label>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleRegenerateContent(idea.id)}
                                  disabled={regeneratingContent === idea.id}
                                >
                                  {regeneratingContent === idea.id ? (
                                    <span className="flex items-center">
                                      <svg
                                        className="animate-spin -ml-1 mr-2 h-4 w-4"
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
                                        ></circle>
                                        <path
                                          className="opacity-75"
                                          fill="currentColor"
                                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                        ></path>
                                      </svg>
                                      {idea.description
                                        ? "Regenerating..."
                                        : "Generating..."}
                                    </span>
                                  ) : (
                                    <>
                                      <Wand2 className="w-4 h-4 mr-2" />
                                      {idea.description
                                        ? "Regenerate"
                                        : "Generate"}
                                    </>
                                  )}
                                </Button>
                              </div>
                              <Textarea
                                placeholder="Enter content here..."
                                value={idea.description}
                                onChange={(e) => {
                                  setContentIdeas((prev) =>
                                    prev.map((item) =>
                                      item.id === idea.id
                                        ? { ...item, description: e.target.value }
                                        : item
                                    )
                                  );
                                }}
                                className="min-h-[100px]"
                              />
                            </div>

                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <label className="text-sm font-medium">
                                  Image
                                </label>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    handleRegenerateImage(
                                      idea.id,
                                      idea.description
                                    );
                                  }}
                                >
                                  {regeneratingImage === idea.id ? (
                                    <span className="flex items-center">
                                      <svg
                                        className="animate-spin -ml-1 mr-2 h-4 w-4"
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
                                        ></circle>
                                        <path
                                          className="opacity-75"
                                          fill="currentColor"
                                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                        ></path>
                                      </svg>
                                      {idea.image
                                        ? "Regenerating..."
                                        : "Generating..."}
                                    </span>
                                  ) : (
                                    <>
                                      <Wand2 className="w-4 h-4 mr-2" />
                                      {idea.image ? "Regenerate" : "Generate"}
                                    </>
                                  )}
                                </Button>
                              </div>
                              <div className="flex items-start space-x-4">
                                <div
                                  className="relative w-[200px] h-[200px] flex-shrink-0 group"
                                  onMouseEnter={() => setHoveredImage(idea.id)}
                                  onMouseLeave={() => setHoveredImage(null)}
                                >
                                  <Image
                                    key={idea.image}
                                    src={idea.image || "/placeholder.svg"}
                                    alt="Content image"
                                    width={200}
                                    height={200}
                                    className="w-full h-full object-cover rounded-md"
                                  />
                                  <div
                                    className={`absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center rounded-md transition-opacity duration-200 ${hoveredImage === idea.id
                                      ? "opacity-100"
                                      : "opacity-0"
                                      }`}
                                  >
                                    <button className="text-red-500 hover:text-red-700 transition-colors">
                                      <X size={32} />
                                    </button>
                                  </div>
                                </div>
                                <div className="flex-grow space-y-2">
                                  <div className="flex space-x-2">
                                    <Button variant="outline" size="sm">
                                      <Upload className="w-4 h-4 mr-2" />
                                      Upload Image
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
                {showScheduledMessage && <div className="text-center text-green-800">
                  <p>Post was scheduled successfully</p>
                </div>}
              </div>
            )}
          </div>
        </CardContent>
        <CardFooter className="flex justify-between">
          {currentStep > 1 ? (
            <Button variant="outline" onClick={handlePreviousStep}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          ) : (
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
          )}
          {currentStep < 3 ? (
            <Button
              onClick={handleNextStep}
              className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
            >
              Next
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          ) : (
            <Button
              onClick={scheduledContentLoader}
              className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">

              <Calendar className="h-4 w-4 mr-2" />
              Schedule Content
            </Button>
          )}
        </CardFooter>
      </Card>

      {/* AlertDialog for Error Message */}
      {/* <AlertDialog
        open={!!errorMessage}
        onOpenChange={() => setErrorMessage(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-500 hover:text-red-700" />
              {errorMessage || "Error"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              You will be redirected to the login page.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction
              onClick={() => {
                window.location.href = "/login";
              }}
            >
              Login
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog> */}
      <ErrorDialog
        isOpen={showErrorDialog}
        onClose={() => setShowErrorDialog(false)}
        message={errorMessage || ''}
      />
    </TooltipProvider >
  );
}
