"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Instagram,
  Facebook,
  Youtube,
  Twitter,
  Linkedin,
  Music,
  X,
  Plus,
  Wand2,
  ImageIcon,
  Trash2,
  RotateCcw,
  Upload,
  RotateCw,
} from "lucide-react";
import { TimeSlotUpdateButton } from "./TimeSlotUpdateButton";
import { WeekNavigation } from "./WeekNavigation";
import { DuplicateScheduleButton } from "./DuplicateScheduleButton";
import { DeleteConfirmationModal } from "./DeleteConfirmationModal";
import { ResetPlanModal } from "./ResetPlanModal";
import { DuplicateConfirmationModal } from "./DuplicateConfirmationModal";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { ContentModificationModal } from "./ContentModificationModal";

interface TimeSlot {
  time: string;
  content: string;
  image: string;
}

interface DayPlatformModuleProps {
  numberOfWeeks: number;
  activeDays: string[];
  activePlatforms: string[];
  timeSlots: Record<number, Record<string, Record<string, TimeSlot[]>>>;
  setTimeSlots: React.Dispatch<
    React.SetStateAction<
      Record<number, Record<string, Record<string, TimeSlot[]>>>
    >
  >;
  onResetPlan: () => void;
}

const platformIcons = {
  Instagram,
  Facebook,
  Youtube,
  Twitter,
  Linkedin,
  Music,
  X,
};

const TIME_OPTIONS = Array.from({ length: 24 }, (_, i) => `${i}:00`);

export function DayPlatformModule({
  numberOfWeeks,
  activeDays,
  activePlatforms,
  timeSlots,
  setTimeSlots,
  onResetPlan,
}: DayPlatformModuleProps) {
  const [currentWeek, setCurrentWeek] = useState(1);
  const [activeTab, setActiveTab] = useState<string | undefined>(activeDays[0]);
  const [selectedTime, setSelectedTime] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState({
    isOpen: false,
    week: 0,
    day: "",
    platform: "",
    index: -1,
  });
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [duplicateConfirmation, setDuplicateConfirmation] = useState<{
    isOpen: boolean;
    week: number;
    day: string;
    platform: string;
    sourceCount: number;
    targetCounts: { [key: string]: number };
  }>({
    isOpen: false,
    week: 0,
    day: "",
    platform: "",
    sourceCount: 0,
    targetCounts: {},
  });
  const [hoveredImage, setHoveredImage] = useState<string | null>(null);
  const [regeneratingContent, setRegeneratingContent] = useState<string | null>(
    null
  );
  const [regeneratingImage, setRegeneratingImage] = useState<string | null>(
    null
  );
  const [regenerateContentSuccess, setRegenerateContentSuccess] = useState<
    string | null
  >(null);
  const [regenerateImageSuccess, setRegenerateImageSuccess] = useState<
    string | null
  >(null);
  const [isModificationModalOpen, setIsModificationModalOpen] = useState(false);
  const [selectedModification, setSelectedModification] = useState<{
    week: number;
    day: string;
    platform: string;
    index: number;
    type: "content" | "image";
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (activeDays.length > 0 && !activeDays.includes(activeTab || "")) {
      setActiveTab(activeDays[0]);
    }
  }, [activeDays, activeTab]);

  const handleAddTimeSlot = (week: number, day: string, platform: string) => {
    if (!selectedTime) return;

    setTimeSlots((prevTimeSlots) => {
      const updatedTimeSlots = { ...prevTimeSlots };
      if (!updatedTimeSlots[week]) updatedTimeSlots[week] = {};
      if (!updatedTimeSlots[week][day]) updatedTimeSlots[week][day] = {};
      if (!updatedTimeSlots[week][day][platform])
        updatedTimeSlots[week][day][platform] = [];
      updatedTimeSlots[week][day][platform].push({
        time: selectedTime,
        content: "",
        image: "/placeholder.svg?height=200&width=200",
      });
      return updatedTimeSlots;
    });
    setSelectedTime("");
  };

  const handleUpdateTimeSlot = (
    week: number,
    day: string,
    platform: string,
    index: number,
    field: "time" | "content" | "image",
    value: string
  ) => {
    setTimeSlots((prevTimeSlots) => {
      const updatedTimeSlots = { ...prevTimeSlots };
      updatedTimeSlots[week][day][platform][index][field] = value;
      return updatedTimeSlots;
    });
  };

  const handleDeleteTimeSlot = (
    week: number,
    day: string,
    platform: string,
    index: number
  ) => {
    setDeleteConfirmation({ isOpen: true, week, day, platform, index });
  };

  const handleRegenerateContent = (modifications: string) => {
    if (selectedModification) {
      const { week, day, platform, index } = selectedModification;
      const key = `${week}-${day}-${platform}-${index}`;
      setRegeneratingContent(key);
      // Simulating API call
      setTimeout(() => {
        // TODO: Implement actual AI-powered content regeneration with modifications
        console.log(
          "Regenerating content for:",
          week,
          day,
          platform,
          index,
          "with modifications:",
          modifications
        );
        setRegeneratingContent(null);
        setRegenerateContentSuccess(key);
        setTimeout(() => setRegenerateContentSuccess(null), 3000);
      }, 2000);
    }
  };

  const handleRegenerateImage = (modifications: string) => {
    if (selectedModification) {
      const { week, day, platform, index } = selectedModification;
      const key = `${week}-${day}-${platform}-${index}`;
      setRegeneratingImage(key);
      // Simulating API call
      setTimeout(() => {
        // TODO: Implement actual AI-powered image regeneration with modifications
        console.log(
          "Regenerating image for:",
          week,
          day,
          platform,
          index,
          "with modifications:",
          modifications
        );
        setRegeneratingImage(null);
        setRegenerateImageSuccess(key);
        setTimeout(() => setRegenerateImageSuccess(null), 3000);
      }, 2000);
    }
  };

  const confirmDeleteTimeSlot = () => {
    setTimeSlots((prevTimeSlots) => {
      const updatedTimeSlots = { ...prevTimeSlots };
      updatedTimeSlots[deleteConfirmation.week][deleteConfirmation.day][
        deleteConfirmation.platform
      ].splice(deleteConfirmation.index, 1);
      if (
        updatedTimeSlots[deleteConfirmation.week][deleteConfirmation.day][
          deleteConfirmation.platform
        ].length === 0
      ) {
        delete updatedTimeSlots[deleteConfirmation.week][
          deleteConfirmation.day
        ][deleteConfirmation.platform];
        if (
          Object.keys(
            updatedTimeSlots[deleteConfirmation.week][deleteConfirmation.day]
          ).length === 0
        ) {
          delete updatedTimeSlots[deleteConfirmation.week][
            deleteConfirmation.day
          ];
          if (
            Object.keys(updatedTimeSlots[deleteConfirmation.week]).length === 0
          ) {
            delete updatedTimeSlots[deleteConfirmation.week];
          }
        }
      }
      return updatedTimeSlots;
    });
    setDeleteConfirmation({
      isOpen: false,
      week: 0,
      day: "",
      platform: "",
      index: -1,
    });
  };

  const handleDuplicateSchedule = (
    week: number,
    day: string,
    platform: string
  ) => {
    const sourceCount = timeSlots[week]?.[day]?.[platform]?.length || 0;
    const targetCounts: Record<string, number> = {};

    activeDays.forEach((targetDay) => {
      if (targetDay !== day) {
        targetCounts[targetDay] =
          timeSlots[week]?.[targetDay]?.[platform]?.length || 0;
      }
    });

    const needsConfirmation = Object.values(targetCounts).some(
      (count) => count > sourceCount
    );

    if (needsConfirmation) {
      setDuplicateConfirmation({
        isOpen: true,
        week,
        day,
        platform,
        sourceCount,
        targetCounts,
      });
    } else {
      performDuplication(week, day, platform);
    }
  };

  const performDuplication = (week: number, day: string, platform: string) => {
    setTimeSlots((prevTimeSlots) => {
      const updatedTimeSlots = { ...prevTimeSlots };
      const sourceSlots = updatedTimeSlots[week][day][platform];

      activeDays.forEach((targetDay) => {
        if (targetDay !== day) {
          updatedTimeSlots[week][targetDay] =
            updatedTimeSlots[week][targetDay] || {};
          updatedTimeSlots[week][targetDay][platform] = [...sourceSlots];
        }
      });

      return updatedTimeSlots;
    });
  };

  const confirmDuplication = () => {
    performDuplication(
      duplicateConfirmation.week,
      duplicateConfirmation.day,
      duplicateConfirmation.platform
    );
    setDuplicateConfirmation({
      isOpen: false,
      week: 0,
      day: "",
      platform: "",
      sourceCount: 0,
      targetCounts: {},
    });
  };

  const handleDeleteImage = (
    week: number,
    day: string,
    platform: string,
    index: number
  ) => {
    setTimeSlots((prevTimeSlots) => {
      const updatedTimeSlots = { ...prevTimeSlots };
      updatedTimeSlots[week][day][platform][index].image =
        "/placeholder.svg?height=200&width=200";
      return updatedTimeSlots;
    });
  };

  const handleUploadImage = (
    week: number,
    day: string,
    platform: string,
    index: number
  ) => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
      fileInputRef.current.onchange = (event) => {
        const target = event.target as HTMLInputElement;
        if (target.files && target.files[0]) {
          const file = target.files[0];
          const reader = new FileReader();
          reader.onload = (e) => {
            const result = e.target?.result;
            if (typeof result === "string") {
              handleUpdateTimeSlot(week, day, platform, index, "image", result);
            }
          };
          reader.readAsDataURL(file);
        }
      };
    }
  };

  const handleOpenModificationModal = (
    week: number,
    day: string,
    platform: string,
    index: number,
    type: "content" | "image"
  ) => {
    setSelectedModification({ week, day, platform, index, type });
    setIsModificationModalOpen(true);
  };

  return (
    <TooltipProvider>
      <Card className="w-full">
        <CardContent className="p-6">
          <div className="flex justify-between items-center mb-4">
            <WeekNavigation
              currentWeek={currentWeek}
              totalWeeks={numberOfWeeks}
              onWeekChange={setCurrentWeek}
            />
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  onClick={() => setIsResetModalOpen(true)}
                  className="button"
                >
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Reset Plan
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Clear all entries and start over</p>
              </TooltipContent>
            </Tooltip>
          </div>
          <Tabs
            value={activeTab || undefined}
            onValueChange={(value) => setActiveTab(value)}
          >
            {activeDays.length > 0 ? (
              <>
                <TabsList className="w-full justify-start">
                  {activeDays.map((day) => (
                    <TabsTrigger
                      key={day}
                      value={day}
                      className="flex-1 button"
                    >
                      {day}
                    </TabsTrigger>
                  ))}
                </TabsList>
                {activeDays.map((day) => (
                  <TabsContent key={day} value={day}>
                    <CardContent className="space-y-6">
                      {activePlatforms.length > 0 ? (
                        activePlatforms.map((platform, platformIndex) => {
                          const Icon =
                            platformIcons[
                            platform as keyof typeof platformIcons
                            ];
                          return (
                            <div key={platform}>
                              <div className="space-y-4">
                                <h3 className="text-lg font-semibold flex items-center">
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <span className="inline-flex items-center cursor-help">
                                        {Icon && (
                                          <Icon className="w-6 h-6 mr-2" />
                                        )}
                                      </span>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                      <p>{platform}</p>
                                    </TooltipContent>
                                  </Tooltip>
                                  {platform}
                                </h3>
                                {timeSlots[currentWeek]?.[day]?.[platform]?.map(
                                  (timeSlot, index) => (
                                    <div
                                      key={index}
                                      className="space-y-2 p-4 border rounded-md"
                                    >
                                      <div className="flex items-center justify-between">
                                        <Select
                                          value={timeSlot.time}
                                          onValueChange={(value) =>
                                            handleUpdateTimeSlot(
                                              currentWeek,
                                              day,
                                              platform,
                                              index,
                                              "time",
                                              value
                                            )
                                          }
                                        >
                                          <SelectTrigger className="w-[180px]">
                                            <SelectValue placeholder="Select time" />
                                          </SelectTrigger>
                                          <SelectContent>
                                            {TIME_OPTIONS.map((time) => (
                                              <SelectItem
                                                key={time}
                                                value={time}
                                              >
                                                {time}
                                              </SelectItem>
                                            ))}
                                          </SelectContent>
                                        </Select>
                                        <div className="flex items-center space-x-2">
                                          <TimeSlotUpdateButton
                                            onClick={() => {
                                              // Implement update logic here
                                              console.log(
                                                "Updating time slot:",
                                                currentWeek,
                                                day,
                                                platform,
                                                index
                                              );
                                            }}
                                          />
                                          <Button
                                            variant="destructive"
                                            size="icon"
                                            onClick={() =>
                                              handleDeleteTimeSlot(
                                                currentWeek,
                                                day,
                                                platform,
                                                index
                                              )
                                            }
                                          >
                                            <Trash2 className="w-4 h-4" />
                                          </Button>
                                        </div>
                                      </div>
                                      <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                          <label className="text-sm font-medium">
                                            Content
                                          </label>
                                          <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() =>
                                              handleOpenModificationModal(
                                                currentWeek,
                                                day,
                                                platform,
                                                index,
                                                "content"
                                              )
                                            }
                                          >
                                            <Wand2 className="w-4 h-4 mr-2" />
                                            Regenerate
                                          </Button>
                                        </div>
                                        <Textarea
                                          placeholder="Enter content here..."
                                          value={timeSlot.content}
                                          onChange={(e) =>
                                            handleUpdateTimeSlot(
                                              currentWeek,
                                              day,
                                              platform,
                                              index,
                                              "content",
                                              e.target.value
                                            )
                                          }
                                          className="min-h-[100px]"
                                        />
                                        {regenerateContentSuccess ===
                                          `${currentWeek}-${day}-${platform}-${index}` && (
                                            <div className="text-green-600 mt-2">
                                              Let us know if you like this version
                                              better
                                            </div>
                                          )}
                                      </div>
                                      <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                          <label className="text-sm font-medium">
                                            Image
                                          </label>
                                        </div>
                                        <div className="flex items-start space-x-4">
                                          <div
                                            className="relative w-[200px] h-[200px] flex-shrink-0 group"
                                            onMouseEnter={() =>
                                              setHoveredImage(
                                                `${currentWeek}-${day}-${platform}-${index}`
                                              )
                                            }
                                            onMouseLeave={() =>
                                              setHoveredImage(null)
                                            }
                                          >
                                            <Image
                                              src={
                                                timeSlot.image ||
                                                "/placeholder.svg"
                                              }
                                              alt="Content image"
                                              width={200}
                                              height={200}
                                              className="w-full h-full object-cover rounded-md"
                                            />
                                            <div
                                              className={`absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center rounded-md transition-opacity duration-200 ${hoveredImage ===
                                                `${currentWeek}-${day}-${platform}-${index}`
                                                ? "opacity-100"
                                                : "opacity-0"
                                                }`}
                                            >
                                              <button
                                                onClick={() =>
                                                  handleDeleteImage(
                                                    currentWeek,
                                                    day,
                                                    platform,
                                                    index
                                                  )
                                                }
                                                className="text-red-500 hover:text-red-700 transition-colors"
                                              >
                                                <X size={32} />
                                              </button>
                                            </div>
                                          </div>
                                          <div className="flex-grow space-y-2">
                                            <Input
                                              type="text"
                                              placeholder="Image URL"
                                              value={timeSlot.image}
                                              onChange={(e) =>
                                                handleUpdateTimeSlot(
                                                  currentWeek,
                                                  day,
                                                  platform,
                                                  index,
                                                  "image",
                                                  e.target.value
                                                )
                                              }
                                              className="w-full"
                                            />
                                            <div className="flex space-x-2">
                                              <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() =>
                                                  handleOpenModificationModal(
                                                    currentWeek,
                                                    day,
                                                    platform,
                                                    index,
                                                    "image"
                                                  )
                                                }
                                              >
                                                <Wand2 className="w-4 h-4 mr-2" />
                                                Regenerate
                                              </Button>
                                              <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() =>
                                                  handleUploadImage(
                                                    currentWeek,
                                                    day,
                                                    platform,
                                                    index
                                                  )
                                                }
                                              >
                                                <Upload className="w-4 h-4 mr-2" />
                                                Upload Image
                                              </Button>
                                            </div>
                                            {regenerateImageSuccess ===
                                              `${currentWeek}-${day}-${platform}-${index}` && (
                                                <div className="text-green-600 mt-2">
                                                  Let us know if you like this
                                                  version better
                                                </div>
                                              )}
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  )
                                )}
                                <div className="flex items-center space-x-2">
                                  <Select
                                    value={selectedTime || ""}
                                    onValueChange={setSelectedTime}
                                  >
                                    <SelectTrigger className="w-[180px]">
                                      <SelectValue placeholder="Select time" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {TIME_OPTIONS.map((time) => (
                                        <SelectItem key={time} value={time}>
                                          {time}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button
                                        onClick={() =>
                                          handleAddTimeSlot(
                                            currentWeek,
                                            day,
                                            platform
                                          )
                                        }
                                        disabled={!selectedTime}
                                      >
                                        <Plus className="w-4 h-4 mr-2" />
                                        Add Time
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                      <p>
                                        Click here to add the selected time to
                                        the schedule
                                      </p>
                                    </TooltipContent>
                                  </Tooltip>
                                </div>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <div>
                                      <DuplicateScheduleButton
                                        onClick={() =>
                                          handleDuplicateSchedule(
                                            currentWeek,
                                            day,
                                            platform
                                          )
                                        }
                                      />
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>
                                      Use this to save time and duplicate this
                                      platform's schedule to the other days in
                                      the plan
                                    </p>
                                  </TooltipContent>
                                </Tooltip>
                              </div>
                              {platformIndex < activePlatforms.length - 1 && (
                                <Separator className="my-6" />
                              )}
                            </div>
                          );
                        })
                      ) : (
                        <p className="text-gray-500 italic">
                          No active platforms selected.
                        </p>
                      )}
                    </CardContent>
                  </TabsContent>
                ))}
              </>
            ) : (
              <p className="text-gray-500 italic p-4">
                No active days selected.
              </p>
            )}
          </Tabs>
        </CardContent>
        <DeleteConfirmationModal
          isOpen={deleteConfirmation.isOpen}
          onClose={() =>
            setDeleteConfirmation({
              isOpen: false,
              week: 0,
              day: "",
              platform: "",
              index: -1,
            })
          }
          onConfirm={confirmDeleteTimeSlot}
          itemToDelete={`${deleteConfirmation.platform} on ${deleteConfirmation.day
            } at ${timeSlots[deleteConfirmation.week]?.[deleteConfirmation.day]?.[
              deleteConfirmation.platform
            ]?.[deleteConfirmation.index]?.time || ""
            }`}
        />
        <ResetPlanModal
          isOpen={isResetModalOpen}
          onClose={() => setIsResetModalOpen(false)}
          onConfirm={() => {
            onResetPlan();
            setIsResetModalOpen(false);
          }}
        />
        <DuplicateConfirmationModal
          isOpen={duplicateConfirmation.isOpen}
          onClose={() =>
            setDuplicateConfirmation({
              isOpen: false,
              week: 0,
              day: "",
              platform: "",
              sourceCount: 0,
              targetCounts: {},
            })
          }
          onConfirm={confirmDuplication}
          sourceDay={duplicateConfirmation.day}
          sourceCount={duplicateConfirmation.sourceCount}
          targetCounts={duplicateConfirmation.targetCounts}
        />
        <ContentModificationModal
          isOpen={isModificationModalOpen}
          onClose={() => setIsModificationModalOpen(false)}
          onRegenerate={(modifications) => {
            if (selectedModification?.type === "content") {
              handleRegenerateContent(modifications);
            } else {
              handleRegenerateImage(modifications);
            }
          }}
          contentType={selectedModification?.type || "content"}
        />
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: "none" }}
          accept="image/*"
        />
      </Card>
    </TooltipProvider>
  );
}




// MLLM code:
// "use client";

// import { useState, useEffect, useRef } from "react";
// import Image from "next/image";
// import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
// import { Card, CardContent } from "@/components/ui/card";
// import { Textarea } from "@/components/ui/textarea";
// import { Button } from "@/components/ui/button";
// import { Separator } from "@/components/ui/separator";
// import {
//   Select,
//   SelectContent,
//   SelectItem,
//   SelectTrigger,
//   SelectValue,
// } from "@/components/ui/select";
// import {
//   Instagram,
//   Facebook,
//   Youtube,
//   Twitter,
//   Linkedin,
//   Music,
//   X,
//   Plus,
//   Wand2,
//   ImageIcon,
//   Trash2,
//   RotateCcw,
//   Upload,
//   RotateCw,
//   Check,
// } from "lucide-react";
// import { TimeSlotUpdateButton } from "./TimeSlotUpdateButton";
// import { WeekNavigation } from "./WeekNavigation";
// import { DuplicateScheduleButton } from "./DuplicateScheduleButton";
// import { DeleteConfirmationModal } from "./DeleteConfirmationModal";
// import { ResetPlanModal } from "./ResetPlanModal";
// import { DuplicateConfirmationModal } from "./DuplicateConfirmationModal";
// import {
//   Tooltip,
//   TooltipContent,
//   TooltipTrigger,
//   TooltipProvider,
// } from "@/components/ui/tooltip";
// import { Input } from "@/components/ui/input";
// import { ContentModificationModal } from "./ContentModificationModal";

// import { scheduleTime, duplicateScheduleTime } from "@/components/Service";

// interface TimeSlot {
//   time: string;
//   content: string;
//   image: string;
// }

// interface DayPlatformModuleProps {
//   numberOfWeeks: number;
//   activeDays: string[];
//   activePlatforms: string[];
//   timeSlots: Record<number, Record<string, Record<string, TimeSlot[]>>>;
//   setTimeSlots: React.Dispatch<
//     React.SetStateAction<
//       Record<number, Record<string, Record<string, TimeSlot[]>>>
//     >
//   >;
//   onResetPlan: () => void;
// }

// const platformIcons = {
//   Instagram,
//   Facebook,
//   Youtube,
//   Twitter,
//   Linkedin,
//   Music,
//   X,
// };

// const TIME_OPTIONS = Array.from({ length: 24 }, (_, i) => `${i}:00`);

// export function DayPlatformModule({
//   numberOfWeeks,
//   activeDays,
//   activePlatforms,
//   timeSlots,
//   setTimeSlots,
//   onResetPlan,
// }: DayPlatformModuleProps) {
//   const [currentWeek, setCurrentWeek] = useState(1);
//   const [activeTab, setActiveTab] = useState<string | undefined>(activeDays[0]);
//   const [selectedTime, setSelectedTime] = useState("");
//   const [selectedTimeMsg, setSelectedTimeMsg] = useState("");
//   const [duplicateMsg, setDuplicateMsg] = useState("");
//   const [deleteConfirmation, setDeleteConfirmation] = useState({
//     isOpen: false,
//     week: 0,
//     day: "",
//     platform: "",
//     index: -1,
//   });
//   const [isResetModalOpen, setIsResetModalOpen] = useState(false);
//   const [isRegenerateContent, setIsRegenerateContent] = useState("");
//   const [duplicateConfirmation, setDuplicateConfirmation] = useState<{
//     isOpen: boolean;
//     week: number;
//     day: string;
//     platform: string;
//     sourceCount: number;
//     targetCounts: { [key: string]: number };
//   }>({
//     isOpen: false,
//     week: 0,
//     day: "",
//     platform: "",
//     sourceCount: 0,
//     targetCounts: {},
//   });
//   const [hoveredImage, setHoveredImage] = useState<string | null>(null);
//   const [regeneratingContent, setRegeneratingContent] = useState<string | null>(
//     null
//   );
//   const [regeneratingImage, setRegeneratingImage] = useState<string | null>(
//     null
//   );
//   const [regenerateContentSuccess, setRegenerateContentSuccess] = useState<
//     string | null
//   >(null);
//   const [regenerateImageSuccess, setRegenerateImageSuccess] = useState<
//     string | null
//   >(null);
//   const [isModificationModalOpen, setIsModificationModalOpen] = useState(false);
//   const [topic, setTopic] = useState<string | undefined>(undefined);
//   const [platform, setPlatform] = useState<string | undefined>(undefined);
//   const [selectedModification, setSelectedModification] = useState<{
//     week: number;
//     day: string;
//     platform: string;
//     index: number;
//     type: "content" | "image";
//   } | null>(null);
//   const fileInputRef = useRef<HTMLInputElement>(null);
//   const [refresh, setRefresh] = useState(0);
//   useEffect(() => {
//     if (activeDays.length > 0 && !activeDays.includes(activeTab || "")) {
//       setActiveTab(activeDays[0]);
//     }
//   }, [activeDays, activeTab]);

//   const handleAddTimeSlot = (week: number, day: string, platform: string) => {
//     if (!selectedTime) return;

//     setTimeSlots((prevTimeSlots) => {
//       const updatedTimeSlots = { ...prevTimeSlots };
//       if (!updatedTimeSlots[week]) updatedTimeSlots[week] = {};
//       if (!updatedTimeSlots[week][day]) updatedTimeSlots[week][day] = {};
//       if (!updatedTimeSlots[week][day][platform])
//         updatedTimeSlots[week][day][platform] = [];
//       updatedTimeSlots[week][day][platform].push({
//         time: selectedTime,
//         content: "",
//         image: "/placeholder.svg?height=200&width=200",
//       });
//       return updatedTimeSlots;
//     });
//     setSelectedTime("");
//   };

//   const handleUpdateTimeSlot = async (
//     week: number,
//     day: string,
//     platform: string,
//     index: number,
//     field: "time" | "content" | "image",
//     value: string,
//     content: string
//   ) => {
//     const regeneratedResponse = await scheduleTime({
//       newTime: value,
//       content,
//     });

//     setSelectedTimeMsg(regeneratedResponse.message);
//     setTimeSlots((prevTimeSlots) => {
//       const updatedTimeSlots = { ...prevTimeSlots };
//       updatedTimeSlots[week][day][platform][index][field] = value;
//       return updatedTimeSlots;
//     });
//   };

//   const handleDeleteTimeSlot = (
//     week: number,
//     day: string,
//     platform: string,
//     index: number
//   ) => {
//     setDeleteConfirmation({ isOpen: true, week, day, platform, index });
//   };

//   const handleRegenerateContent = (modifications: string) => {
//     if (selectedModification) {
//       const { week, day, platform, index } = selectedModification;
//       const key = `${week}-${day}-${platform}-${index}`;

//       setRegeneratingContent(key);

//       setTimeout(() => {
//         console.log(
//           "Regenerating content for:",
//           week,
//           day,
//           platform,
//           index,
//           "with modifications:",
//           modifications
//         );

//         setIsRegenerateContent(modifications);

//         setTimeSlots((prevTimeSlots) => {
//           const updatedTimeSlots = structuredClone(prevTimeSlots);

//           if (!updatedTimeSlots[week]) updatedTimeSlots[week] = {};
//           if (!updatedTimeSlots[week][day]) updatedTimeSlots[week][day] = {};
//           if (!updatedTimeSlots[week][day][platform])
//             updatedTimeSlots[week][day][platform] = [];

//           if (modifications && modifications.trim() !== "") {
//             if (!updatedTimeSlots[week][day][platform][index]) {
//               updatedTimeSlots[week][day][platform][index] = {
//                 time: `${9 + index * 3}:00`,
//                 content: "",
//                 image: "",
//               };
//             } else {
//               updatedTimeSlots[week][day][platform][index] = {
//                 ...updatedTimeSlots[week][day][platform][index],
//                 content: modifications,
//               };
//             }
//           }

//           return { ...updatedTimeSlots };
//         });

//         setRegeneratingContent(null);
//         setRegenerateContentSuccess(key);

//         setTimeout(() => setRegenerateContentSuccess(null), 3000);
//       }, 2000);
//     }
//   };

//   useEffect(() => {}, [timeSlots]);

//   const handleRegenerateImage = (modifications: string) => {
//     if (selectedModification) {
//       const { week, day, platform, index } = selectedModification;
//       const key = `${week}-${day}-${platform}-${index}`;
//       setRegeneratingImage(key);
//       setTimeout(() => {
//         console.log(
//           "Regenerating image for:",
//           week,
//           day,
//           platform,
//           index,
//           "with modifications:",
//           modifications
//         );

//         setTimeSlots((prevTimeSlots) => {
//           const updatedTimeSlots = structuredClone(prevTimeSlots);

//           if (!updatedTimeSlots[week]) updatedTimeSlots[week] = {};
//           if (!updatedTimeSlots[week][day]) updatedTimeSlots[week][day] = {};
//           if (!updatedTimeSlots[week][day][platform])
//             updatedTimeSlots[week][day][platform] = [];

//           if (modifications && modifications.trim() !== "") {
//             if (!updatedTimeSlots[week][day][platform][index]) {
//               updatedTimeSlots[week][day][platform][index] = {
//                 time: `${9 + index * 3}:00`,
//                 content: "",
//                 image: "",
//               };
//             } else {
//               updatedTimeSlots[week][day][platform][index] = {
//                 ...updatedTimeSlots[week][day][platform][index],
//                 image: modifications,
//               };
//             }
//           }

//           return { ...updatedTimeSlots };
//         });

//         setRegeneratingImage(null);
//         setRegenerateImageSuccess(key);
//         setTimeout(() => setRegenerateImageSuccess(null), 3000);
//       }, 2000);
//     }
//   };

//   const confirmDeleteTimeSlot = () => {
//     setTimeSlots((prevTimeSlots) => {
//       const updatedTimeSlots = { ...prevTimeSlots };
//       updatedTimeSlots[deleteConfirmation.week][deleteConfirmation.day][
//         deleteConfirmation.platform
//       ].splice(deleteConfirmation.index, 1);
//       if (
//         updatedTimeSlots[deleteConfirmation.week][deleteConfirmation.day][
//           deleteConfirmation.platform
//         ].length === 0
//       ) {
//         delete updatedTimeSlots[deleteConfirmation.week][
//           deleteConfirmation.day
//         ][deleteConfirmation.platform];
//         if (
//           Object.keys(
//             updatedTimeSlots[deleteConfirmation.week][deleteConfirmation.day]
//           ).length === 0
//         ) {
//           delete updatedTimeSlots[deleteConfirmation.week][
//             deleteConfirmation.day
//           ];
//           if (
//             Object.keys(updatedTimeSlots[deleteConfirmation.week]).length === 0
//           ) {
//             delete updatedTimeSlots[deleteConfirmation.week];
//           }
//         }
//       }
//       return updatedTimeSlots;
//     });
//     setDeleteConfirmation({
//       isOpen: false,
//       week: 0,
//       day: "",
//       platform: "",
//       index: -1,
//     });
//   };

//   const handleDuplicateSchedule = async (
//     week: number,
//     day: string,
//     platform: string
//   ) => {
//     const regeneratedResponse = await duplicateScheduleTime({
//       source_week: week,
//       source_day: day,
//       platform: platform,
//     });
//     setDuplicateMsg(regeneratedResponse.message);
//     console.log("message", regeneratedResponse.message);
//     const sourceCount = timeSlots[week]?.[day]?.[platform]?.length || 0;
//     const targetCounts: Record<string, number> = {};

//     activeDays.forEach((targetDay) => {
//       if (targetDay !== day) {
//         targetCounts[targetDay] =
//           timeSlots[week]?.[targetDay]?.[platform]?.length || 0;
//       }
//     });

//     const needsConfirmation = Object.values(targetCounts).some(
//       (count) => count > sourceCount
//     );

//     if (needsConfirmation) {
//       setDuplicateConfirmation({
//         isOpen: true,
//         week,
//         day,
//         platform,
//         sourceCount,
//         targetCounts,
//       });
//     } else {
//       performDuplication(week, day, platform);
//     }
//   };

//   const performDuplication = (week: number, day: string, platform: string) => {
//     setTimeSlots((prevTimeSlots) => {
//       const updatedTimeSlots = { ...prevTimeSlots };
//       const sourceSlots = updatedTimeSlots[week][day][platform];

//       activeDays.forEach((targetDay) => {
//         if (targetDay !== day) {
//           updatedTimeSlots[week][targetDay] =
//             updatedTimeSlots[week][targetDay] || {};
//           updatedTimeSlots[week][targetDay][platform] = [...sourceSlots];
//         }
//       });

//       return updatedTimeSlots;
//     });
//   };

//   const confirmDuplication = () => {
//     performDuplication(
//       duplicateConfirmation.week,
//       duplicateConfirmation.day,
//       duplicateConfirmation.platform
//     );
//     setDuplicateConfirmation({
//       isOpen: false,
//       week: 0,
//       day: "",
//       platform: "",
//       sourceCount: 0,
//       targetCounts: {},
//     });
//   };

//   const handleDeleteImage = (
//     week: number,
//     day: string,
//     platform: string,
//     index: number
//   ) => {
//     setTimeSlots((prevTimeSlots) => {
//       const updatedTimeSlots = { ...prevTimeSlots };
//       updatedTimeSlots[week][day][platform][index].image =
//         "/placeholder.svg?height=200&width=200";
//       return updatedTimeSlots;
//     });
//   };

//   const handleUploadImage = (
//     week: number,
//     day: string,
//     platform: string,
//     index: number
//   ) => {
//     if (fileInputRef.current) {
//       fileInputRef.current.click();
//       fileInputRef.current.onchange = (event) => {
//         const target = event.target as HTMLInputElement;
//         if (target.files && target.files[0]) {
//           const file = target.files[0];
//           const reader = new FileReader();
//           reader.onload = (e) => {
//             const result = e.target?.result;
//             if (typeof result === "string") {
//               handleUpdateTimeSlot(
//                 week,
//                 day,
//                 platform,
//                 index,
//                 "image",
//                 result,
//                 ""
//               );
//             }
//           };
//           reader.readAsDataURL(file);
//         }
//       };
//     }
//   };

//   const handleOpenModificationModal = (
//     week: number,
//     day: string,
//     platform: string,
//     index: number,
//     type: "content" | "image",
//     topic: string
//   ) => {
//     setSelectedModification({ week, day, platform, index, type });
//     setTopic(topic);
//     console.log("topic", topic);
//     setIsModificationModalOpen(true);
//     setPlatform(platform);
//   };

//   useEffect(() => {
//     if (duplicateMsg) {
//       const timer = setTimeout(() => {
//         setDuplicateMsg("");
//         setDuplicateMsg("");
//       }, 2000);

//       return () => clearTimeout(timer);
//     }
//   }, [duplicateMsg]);

//   useEffect(() => {
//     if (selectedTimeMsg) {
//       const timer = setTimeout(() => {
//         setSelectedTimeMsg("");
//       }, 3000);

//       return () => clearTimeout(timer);
//     }
//   }, [selectedTimeMsg]);

//   return (
//     <TooltipProvider>
//       <Card className="w-full">
//         <CardContent className="p-6">
//           <div className="flex justify-between items-center mb-4">
//             <WeekNavigation
//               currentWeek={currentWeek}
//               totalWeeks={numberOfWeeks}
//               onWeekChange={setCurrentWeek}
//             />
//             <Tooltip>
//               <TooltipTrigger asChild>
//                 <Button
//                   variant="outline"
//                   onClick={() => setIsResetModalOpen(true)}
//                   className="button"
//                 >
//                   <RotateCcw className="w-4 h-4 mr-2" />
//                   Reset Plan
//                 </Button>
//               </TooltipTrigger>
//               <TooltipContent>
//                 <p>Clear all entries and start over</p>
//               </TooltipContent>
//             </Tooltip>
//           </div>
//           <Tabs
//             value={activeTab || undefined}
//             onValueChange={(value) => setActiveTab(value)}
//           >
//             {activeDays.length > 0 ? (
//               <>
//                 <TabsList className="w-full justify-start">
//                   {activeDays.map((day) => (
//                     <TabsTrigger
//                       key={day}
//                       value={day}
//                       className="flex-1 button"
//                     >
//                       {day}
//                     </TabsTrigger>
//                   ))}
//                 </TabsList>
//                 {activeDays.map((day) => (
//                   <TabsContent key={day} value={day}>
//                     <CardContent className="space-y-6">
//                       {activePlatforms.length > 0 ? (
//                         activePlatforms.map((platform, platformIndex) => {
//                           const Icon =
//                             platformIcons[
//                               platform as keyof typeof platformIcons
//                             ];
//                           return (
//                             <div key={platform}>
//                               <div className="space-y-4">
//                                 <h3 className="text-lg font-semibold flex items-center">
//                                   <Tooltip>
//                                     <TooltipTrigger asChild>
//                                       <span className="inline-flex items-center cursor-help">
//                                         {Icon && (
//                                           <Icon className="w-6 h-6 mr-2" />
//                                         )}
//                                       </span>
//                                     </TooltipTrigger>
//                                     <TooltipContent>
//                                       <p>{platform}</p>
//                                     </TooltipContent>
//                                   </Tooltip>
//                                   {platform}
//                                 </h3>
//                                 {timeSlots[currentWeek]?.[day]?.[platform]?.map(
//                                   (timeSlot, index) => (
//                                     <div
//                                       key={index}
//                                       className="space-y-2 p-4 border rounded-md"
//                                     >
//                                       <div className="flex items-center justify-between">
//                                         <Select
//                                           value={timeSlot.time}
//                                           onValueChange={(value) =>
//                                             handleUpdateTimeSlot(
//                                               currentWeek,
//                                               day,
//                                               platform,
//                                               index,
//                                               "time",
//                                               value,
//                                               timeSlots[currentWeek]?.[day]?.[
//                                                 platform
//                                               ]?.[index]?.content
//                                             )
//                                           }
//                                         >
//                                           <div>
//                                             <SelectTrigger className="w-[180px]">
//                                               <SelectValue placeholder="Select time" />
//                                             </SelectTrigger>
//                                             {selectedTimeMsg && (
//                                               <div className="pt-2 left-0 right-0 top-0 flex items-center justify-left text-green-600 font-medium">
//                                                 <Check className="w-4 h-4 mr-1" />
//                                                 {selectedTimeMsg}
//                                               </div>
//                                             )}
//                                           </div>
//                                           <SelectContent>
//                                             {TIME_OPTIONS.map((time) => (
//                                               <SelectItem
//                                                 key={time}
//                                                 value={time}
//                                               >
//                                                 {time}
//                                               </SelectItem>
//                                             ))}
//                                           </SelectContent>
//                                         </Select>
//                                         <div className="flex items-center space-x-2">
//                                           <TimeSlotUpdateButton
//                                             onClick={() => {
//                                               console.log(
//                                                 "Updating time slot:",
//                                                 currentWeek,
//                                                 day,
//                                                 platform,
//                                                 index
//                                               );
//                                             }}
//                                           />
//                                           <Button
//                                             variant="destructive"
//                                             size="icon"
//                                             onClick={() =>
//                                               handleDeleteTimeSlot(
//                                                 currentWeek,
//                                                 day,
//                                                 platform,
//                                                 index
//                                               )
//                                             }
//                                           >
//                                             <Trash2 className="w-4 h-4" />
//                                           </Button>
//                                         </div>
//                                       </div>

//                                       <div className="space-y-2">
//                                         <div className="flex items-center justify-between">
//                                           <label className="text-sm font-medium">
//                                             Content
//                                           </label>
//                                           <Button
//                                             variant="outline"
//                                             size="sm"
//                                             onClick={() =>
//                                               handleOpenModificationModal(
//                                                 currentWeek,
//                                                 day,
//                                                 platform,
//                                                 index,
//                                                 "content",
//                                                 timeSlots[currentWeek]?.[day]?.[
//                                                   platform
//                                                 ]?.[index]?.content
//                                               )
//                                             }
//                                           >
//                                             <Wand2 className="w-4 h-4 mr-2" />
//                                             Regenerate
//                                           </Button>
//                                         </div>
//                                         <Textarea
//                                           key={refresh}
//                                           placeholder="Enter content here..."
//                                           value={
//                                             timeSlots?.[currentWeek]?.[day]?.[
//                                               platform
//                                             ]?.[index]?.content ?? ""
//                                           }
//                                           onChange={(e) =>
//                                             handleUpdateTimeSlot(
//                                               currentWeek,
//                                               day,
//                                               platform,
//                                               index,
//                                               "content",
//                                               e.target.value,
//                                               ""
//                                             )
//                                           }
//                                           className="min-h-[100px]"
//                                         />

//                                         {regenerateContentSuccess ===
//                                           `${currentWeek}-${day}-${platform}-${index}` && (
//                                           <div className="text-green-600 mt-2">
//                                             Let us know if you like this version
//                                             better
//                                           </div>
//                                         )}
//                                       </div>
//                                       <div className="space-y-2">
//                                         <div className="flex items-center justify-between">
//                                           <label className="text-sm font-medium">
//                                             Image
//                                           </label>
//                                         </div>
//                                         <div className="flex items-start space-x-4">
//                                           <div
//                                             className="relative w-[200px] h-[200px] flex-shrink-0 group"
//                                             onMouseEnter={() =>
//                                               setHoveredImage(
//                                                 `${currentWeek}-${day}-${platform}-${index}`
//                                               )
//                                             }
//                                             onMouseLeave={() =>
//                                               setHoveredImage(null)
//                                             }
//                                           >
//                                             <Image
//                                               src={
//                                                 timeSlot.image ||
//                                                 "/placeholder.svg"
//                                               }
//                                               alt="Content image"
//                                               width={200}
//                                               height={200}
//                                               className="w-full h-full object-cover rounded-md"
//                                             />
//                                             <div
//                                               className={`absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center rounded-md transition-opacity duration-200 ${
//                                                 hoveredImage ===
//                                                 `${currentWeek}-${day}-${platform}-${index}`
//                                                   ? "opacity-100"
//                                                   : "opacity-0"
//                                               }`}
//                                             >
//                                               <button
//                                                 onClick={() =>
//                                                   handleDeleteImage(
//                                                     currentWeek,
//                                                     day,
//                                                     platform,
//                                                     index
//                                                   )
//                                                 }
//                                                 className="text-red-500 hover:text-red-700 transition-colors"
//                                               >
//                                                 <X size={32} />
//                                               </button>
//                                             </div>
//                                           </div>
//                                           <div className="flex-grow space-y-2">
//                                             <Input
//                                               type="text"
//                                               placeholder="Image URL"
//                                               value={timeSlot.image}
//                                               onChange={(e) =>
//                                                 handleUpdateTimeSlot(
//                                                   currentWeek,
//                                                   day,
//                                                   platform,
//                                                   index,
//                                                   "image",
//                                                   e.target.value,
//                                                   ""
//                                                 )
//                                               }
//                                               className="w-full"
//                                             />
//                                             <div className="flex space-x-2">
//                                               <Button
//                                                 variant="outline"
//                                                 size="sm"
//                                                 onClick={() =>
//                                                   handleOpenModificationModal(
//                                                     currentWeek,
//                                                     day,
//                                                     platform,
//                                                     index,
//                                                     "image",
//                                                     timeSlots[currentWeek]?.[
//                                                       day
//                                                     ]?.[platform]?.[index]
//                                                       ?.content
//                                                   )
//                                                 }
//                                               >
//                                                 <Wand2 className="w-4 h-4 mr-2" />
//                                                 {timeSlot.image
//                                                   ? "Regenerate"
//                                                   : "Generate"}
//                                               </Button>
//                                               <Button
//                                                 variant="outline"
//                                                 size="sm"
//                                                 onClick={() =>
//                                                   handleUploadImage(
//                                                     currentWeek,
//                                                     day,
//                                                     platform,
//                                                     index
//                                                   )
//                                                 }
//                                               >
//                                                 <Upload className="w-4 h-4 mr-2" />
//                                                 Upload Image
//                                               </Button>
//                                             </div>
//                                             {regenerateImageSuccess ===
//                                               `${currentWeek}-${day}-${platform}-${index}` && (
//                                               <div className="text-green-600 mt-2">
//                                                 Let us know if you like this
//                                                 version better
//                                               </div>
//                                             )}
//                                           </div>
//                                         </div>
//                                       </div>
//                                     </div>
//                                   )
//                                 )}
//                                 <div className="flex items-center space-x-2">
//                                   <Select
//                                     value={selectedTime || ""}
//                                     onValueChange={setSelectedTime}
//                                   >
//                                     <SelectTrigger className="w-[180px]">
//                                       <SelectValue placeholder="Select time" />
//                                     </SelectTrigger>
//                                     <SelectContent>
//                                       {TIME_OPTIONS.map((time) => (
//                                         <SelectItem key={time} value={time}>
//                                           {time}
//                                         </SelectItem>
//                                       ))}
//                                     </SelectContent>
//                                   </Select>
//                                   <Tooltip>
//                                     <TooltipTrigger asChild>
//                                       <Button
//                                         onClick={() =>
//                                           handleAddTimeSlot(
//                                             currentWeek,
//                                             day,
//                                             platform
//                                           )
//                                         }
//                                         disabled={!selectedTime}
//                                       >
//                                         <Plus className="w-4 h-4 mr-2" />
//                                         Add Time
//                                       </Button>
//                                     </TooltipTrigger>
//                                     <TooltipContent>
//                                       <p>
//                                         Click here to add the selected time to
//                                         the schedule
//                                       </p>
//                                     </TooltipContent>
//                                   </Tooltip>
//                                 </div>
//                                 <Tooltip>
//                                   <TooltipTrigger asChild>
//                                     <div>
//                                       <DuplicateScheduleButton
//                                         onClick={() =>
//                                           handleDuplicateSchedule(
//                                             currentWeek,
//                                             day,
//                                             platform
//                                           )
//                                         }
//                                       />
//                                       {duplicateMsg && (
//                                         <div className="pt-10 left-0 right-0 top-0 flex items-center justify-left text-green-600 font-medium">
//                                           <Check className="w-4 h-4 mr-1" />
//                                           {duplicateMsg}
//                                         </div>
//                                       )}
//                                     </div>
//                                   </TooltipTrigger>
//                                   <TooltipContent>
//                                     <p>
//                                       Use this to save time and duplicate this
//                                       platform's schedule to the other days in
//                                       the plan
//                                     </p>
//                                   </TooltipContent>
//                                 </Tooltip>
//                               </div>
//                               {platformIndex < activePlatforms.length - 1 && (
//                                 <Separator className="my-6" />
//                               )}
//                             </div>
//                           );
//                         })
//                       ) : (
//                         <p className="text-gray-500 italic">
//                           No active platforms selected.
//                         </p>
//                       )}
//                     </CardContent>
//                   </TabsContent>
//                 ))}
//               </>
//             ) : (
//               <p className="text-gray-500 italic p-4">
//                 No active days selected.
//               </p>
//             )}
//           </Tabs>
//         </CardContent>
//         <DeleteConfirmationModal
//           isOpen={deleteConfirmation.isOpen}
//           onClose={() =>
//             setDeleteConfirmation({
//               isOpen: false,
//               week: 0,
//               day: "",
//               platform: "",
//               index: -1,
//             })
//           }
//           onConfirm={confirmDeleteTimeSlot}
//           itemToDelete={`${deleteConfirmation.platform} on ${
//             deleteConfirmation.day
//           } at ${
//             timeSlots[deleteConfirmation.week]?.[deleteConfirmation.day]?.[
//               deleteConfirmation.platform
//             ]?.[deleteConfirmation.index]?.time || ""
//           }`}
//         />
//         <ResetPlanModal
//           isOpen={isResetModalOpen}
//           onClose={() => setIsResetModalOpen(false)}
//           onConfirm={() => {
//             onResetPlan();
//             setIsResetModalOpen(false);
//           }}
//         />
//         <DuplicateConfirmationModal
//           isOpen={duplicateConfirmation.isOpen}
//           onClose={() =>
//             setDuplicateConfirmation({
//               isOpen: false,
//               week: 0,
//               day: "",
//               platform: "",
//               sourceCount: 0,
//               targetCounts: {},
//             })
//           }
//           onConfirm={confirmDuplication}
//           sourceDay={duplicateConfirmation.day}
//           sourceCount={duplicateConfirmation.sourceCount}
//           targetCounts={duplicateConfirmation.targetCounts}
//         />
//         <ContentModificationModal
//           isOpen={isModificationModalOpen}
//           onClose={() => setIsModificationModalOpen(false)}
//           onRegenerate={(modifications) => {
//             if (selectedModification?.type === "content") {
//               handleRegenerateContent(modifications);
//             } else {
//               handleRegenerateImage(modifications);
//             }
//           }}
//           contentType={selectedModification?.type || "content"}
//           subTopic={topic ?? ""}
//           platform={platform ?? ""}
//         />
//         <input
//           type="file"
//           ref={fileInputRef}
//           style={{ display: "none" }}
//           accept="image/*"
//         />
//       </Card>
//     </TooltipProvider>
//   );
// }
