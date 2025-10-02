"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { Header } from "@/components/Header"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Plus, User, Trash2, BookOpen } from "lucide-react"
import { ContentPlannerCampaign, type Campaign } from "@/components/ContentPlannerCampaign"
import { ContentAnalysisWorkflow } from "@/components/ContentAnalysisWorkflow"
import { Checkbox } from "@/components/ui/checkbox"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { getAllCampaigns } from "@/components/Service"
import { getAllAuthorPersonalities, deleteAuthorPersonality } from "@/components/AuthorPersonalityService"
import { toast } from "sonner"
import { LoadingModal } from "@/components/LoadingModal"

const SAMPLE_AUTHOR_PROFILES = [
  {
    id: "1",
    name: "Ernest Hemingway",
    description: "Concise, direct prose with short sentences",
  },
  {
    id: "2",
    name: "Jane Austen",
    description: "Elegant, witty social commentary",
  },
  {
    id: "3",
    name: "David Foster Wallace",
    description: "Complex, footnote-heavy postmodern style",
  },
  {
    id: "4",
    name: "Stephen King",
    description: "Suspenseful, character-driven horror and thriller",
  },
  {
    id: "5",
    name: "Toni Morrison",
    description: "Poetic, rich with metaphor and cultural depth",
  },
]

export default function ContentPlannerPage() {
  console.log("[v0] ContentPlannerPage component rendering")

  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [savedProfiles, setSavedProfiles] = useState<typeof SAMPLE_AUTHOR_PROFILES>([])
  const [checkedProfiles, setCheckedProfiles] = useState<string[]>([])
  const [showContentPlanner, setShowContentPlanner] = useState(true)
  const [profilesLoading, setProfilesLoading] = useState(false)
  const [campaignsLoading, setCampaignsLoading] = useState(true)

  const searchParams = useSearchParams()
  const viewParam = searchParams.get("view")

  const [contentPlannerTab, setContentPlannerTab] = useState<"campaigns" | "workflow" | "author-personalities">(
    viewParam === "workflow" ? "workflow" : viewParam === "author-personalities" ? "author-personalities" : "campaigns",
  )

  // Fetch campaigns on component mount and sort by createdAt (newest first)
  useEffect(() => {
    const fetchCampaigns = async () => {
      try {
        console.log("🔍 ContentPlannerPage: Starting to fetch campaigns...");
        setCampaignsLoading(true)
        const response = await getAllCampaigns()
        console.log("🔍 ContentPlannerPage: Response from getAllCampaigns:", response);
        if (response.status === "success") {
          const fetchedCampaigns = response.message.campaigns || []
          console.log("🔍 ContentPlannerPage: Fetched campaigns:", fetchedCampaigns.length, "campaigns");
          // Sort campaigns by createdAt in descending order (newest first)
          fetchedCampaigns.sort(
            (a: Campaign, b: Campaign) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
          )
          setCampaigns(fetchedCampaigns)
          console.log("🔍 ContentPlannerPage: Set campaigns in state:", fetchedCampaigns);
          setShowContentPlanner(true) // Show content planner by default
        } else {
          console.error("Failed to fetch campaigns:", response.message)
          toast.error("Failed to load campaigns. Please try again.")
        }
      } catch (error) {
        console.error("Error fetching campaigns:", error)
        toast.error("An unexpected error occurred while loading campaigns.")
      } finally {
        setCampaignsLoading(false)
      }
    }
    fetchCampaigns()
  }, [])

  // Function to fetch author personalities
  const fetchAuthorPersonalities = async () => {
    try {
      setProfilesLoading(true)
      const response = await getAllAuthorPersonalities()
      console.log("Author personalities response:", response)

      if (response.status === "success") {
        setSavedProfiles(response.message.personalities || [])
      } else {
        console.error("Failed to fetch author personalities:", response.message)
        // Fallback to sample data if API fails
        setSavedProfiles(SAMPLE_AUTHOR_PROFILES)
      }
    } catch (error) {
      console.error("Error fetching author personalities:", error)
      // Fallback to sample data if API fails
      setSavedProfiles(SAMPLE_AUTHOR_PROFILES)
    } finally {
      setProfilesLoading(false)
    }
  }

  // Fetch author personalities on component mount
  useEffect(() => {
    fetchAuthorPersonalities()
  }, [])

  // Refresh author personalities when returning to author-personalities tab
  useEffect(() => {
    if (contentPlannerTab === "author-personalities") {
      fetchAuthorPersonalities()
    }
  }, [contentPlannerTab])

  const handleAddCampaign = async (campaign: Omit<Campaign, "id" | "createdAt" | "updatedAt">) => {
    console.log("handleAddCampaign called with:", campaign);
    
    try {
      const { createCampaign } = await import('@/components/Service');
      const response = await createCampaign(campaign);
      
      if (response.status === 'success') {
        const newCampaign = response.message.message;
        console.log("Created new campaign:", newCampaign);

        setCampaigns((prev) => {
          const updatedCampaigns = [...prev, newCampaign]
          // Sort campaigns by createdAt in descending order (newest first)
          updatedCampaigns.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
          return updatedCampaigns
        })
        
        toast.success("Campaign created successfully!");
      } else {
        console.error("Failed to create campaign:", response.message);
        toast.error(response.message || "Failed to create campaign");
      }
    } catch (error) {
      console.error("Error creating campaign:", error);
      toast.error("An unexpected error occurred while creating the campaign");
    }
  }

  const refreshCampaigns = async () => {
    try {
      console.log("Refreshing campaigns...");
      setCampaignsLoading(true)
      const response = await getAllCampaigns()
      console.log("Refresh response:", response);
      if (response.status === "success") {
        const fetchedCampaigns = response.message.campaigns || []
        console.log("Fetched campaigns:", fetchedCampaigns.length, "campaigns");
        // Sort campaigns by createdAt in descending order (newest first)
        fetchedCampaigns.sort(
          (a: Campaign, b: Campaign) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
        )
        setCampaigns(fetchedCampaigns)
        console.log("Campaigns updated in state");
      } else {
        console.error("Failed to refresh campaigns:", response.message)
        toast.error("Failed to refresh campaigns. Please try again.")
      }
    } catch (error) {
      console.error("Error refreshing campaigns:", error)
      toast.error("An unexpected error occurred while refreshing campaigns.")
    } finally {
      setCampaignsLoading(false)
    }
  }

  const handleEditCampaign = async (id: string, updatedCampaign: Partial<Campaign>) => {
    try {
      const { updateCampaign } = await import('@/components/Service');
      const response = await updateCampaign(id, updatedCampaign);
      
      if (response.status === 'success') {
        const updatedCampaignData = response.message.message;
        console.log("Updated campaign:", updatedCampaignData);

        setCampaigns((prev) => {
          const updatedCampaigns = prev.map((campaign) =>
            campaign.id === id ? { ...campaign, ...updatedCampaignData, updatedAt: new Date() } : campaign,
          )
          // Sort campaigns by createdAt in descending order (newest first)
          updatedCampaigns.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
          return updatedCampaigns
        })
        
        toast.success("Campaign updated successfully!");
      } else {
        console.error("Failed to update campaign:", response.message);
        toast.error(response.message || "Failed to update campaign");
      }
    } catch (error) {
      console.error("Error updating campaign:", error);
      toast.error("An unexpected error occurred while updating the campaign");
    }
  }

  const handleDeleteCampaign = (id: string) => {
    setCampaigns((prev) => {
      const updatedCampaigns = prev.filter((campaign) => campaign.id !== id)
      // Sort campaigns by createdAt in descending order (newest first)
      updatedCampaigns.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      return updatedCampaigns
    })
  }


  const handleProfileCheckChange = (profileId: string) => {
    setCheckedProfiles((prev) => {
      if (prev.includes(profileId)) {
        return prev.filter((id) => id !== profileId)
      } else {
        return [...prev, profileId]
      }
    })
  }

  const handleSelectProfile = () => {
    if (checkedProfiles.length === 1) {
      alert(`Profile "${savedProfiles.find((p) => p.id === checkedProfiles[0])?.name}" selected for use`)
      setCheckedProfiles([])
    }
  }

  const handleDeleteProfile = async (profileId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    console.log("Attempting to delete profile:", profileId)
    try {
      const response = await deleteAuthorPersonality(profileId)
      console.log("Delete response:", response)
      if (response.status === "success") {
        setSavedProfiles(savedProfiles.filter((profile) => profile.id !== profileId))
        if (checkedProfiles.includes(profileId)) {
          setCheckedProfiles((prev) => prev.filter((id) => id !== profileId))
        }
        toast.success("Author personality deleted successfully.")
      } else {
        console.error("Delete failed:", response.message)
        toast.error("Failed to delete author personality. Please try again.")
      }
    } catch (error) {
      console.error("Error deleting author personality:", error)
      toast.error("An unexpected error occurred while deleting the author personality.")
    }
  }

  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <Header />
      <main className="p-6 max-w-7xl mx-auto space-y-6">
        <h1 className="text-4xl font-extrabold text-white">Content Planner</h1>

          <Card className="w-full">
            <CardContent className="p-6">
              <Tabs
                value={contentPlannerTab}
                onValueChange={(value) => setContentPlannerTab(value as "campaigns" | "workflow" | "author-personalities")}
              >
                <TabsList className="w-full mb-6">
                  <TabsTrigger value="campaigns" className="flex-1">
                    Campaigns
                  </TabsTrigger>
                  <TabsTrigger value="author-personalities" className="flex-1">
                    Author Personalities
                  </TabsTrigger>
                  <TabsTrigger value="workflow" className="flex-1">
                    Workflow Explained
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="campaigns">
                  <ContentPlannerCampaign
                    campaigns={campaigns && campaigns.length > 0 ? campaigns : []}
                    onAddCampaign={handleAddCampaign}
                    onEditCampaign={handleEditCampaign}
                    onDeleteCampaign={handleDeleteCampaign}
                    onRefreshCampaigns={refreshCampaigns}
                  />
                </TabsContent>

                <TabsContent value="author-personalities">
                  <div className="space-y-6">
                    <div className="flex justify-between items-center">
                      <h2 className="text-2xl font-bold">Author Personalities</h2>
                      <Link href="/dashboard/author-personality/add">
                        <Button className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">
                          <Plus className="h-4 w-4 mr-2" />
                          Add Personality
                        </Button>
                      </Link>
                    </div>

                    {profilesLoading ? (
                      <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70" style={{ 
                        backdropFilter: 'blur(6px)',
                        WebkitBackdropFilter: 'blur(6px)'
                      }}>
                        <div className="bg-white rounded-lg shadow-2xl p-8 max-w-sm w-full mx-4 border border-gray-200">
                          <div className="flex flex-col items-center space-y-4">
                            <div className="relative">
                              <svg
                                className="animate-spin h-12 w-12 text-[#3d545f]"
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
                                />
                                <path
                                  className="opacity-75"
                                  fill="currentColor"
                                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                />
                              </svg>
                            </div>
                            <h3 className="text-lg font-medium text-gray-900 text-center">
                              Loading author personalities...
                            </h3>
                          </div>
                        </div>
                      </div>
                    ) : savedProfiles.length > 0 ? (
                      <div className="space-y-4">
                        <div className="space-y-2">
                          {savedProfiles.map((profile) => (
                            <div
                              key={profile.id}
                              className="p-3 border rounded-md flex items-center justify-between hover:bg-gray-50"
                            >
                              <div className="flex items-center space-x-3">
                                <Checkbox
                                  id={`profile-${profile.id}`}
                                  checked={checkedProfiles.includes(profile.id)}
                                  onCheckedChange={() => handleProfileCheckChange(profile.id)}
                                  className="h-5 w-5"
                                />
                                <div>
                                  <h4 className="font-medium">{profile.name}</h4>
                                  <p className="text-sm text-gray-500">{profile.description}</p>
                                </div>
                              </div>
                              <div className="flex space-x-2">
                                <Link href={`/dashboard/author-personality/edit/${profile.id}`}>
                                  <Button variant="outline" size="sm">
                                    Edit
                                  </Button>
                                </Link>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => handleDeleteProfile(profile.id, e)}
                                  className="opacity-70 hover:opacity-100"
                                >
                                  <Trash2 className="h-4 w-4 text-red-500" />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>

                        <div className="flex justify-end">
                          <Button
                            onClick={handleSelectProfile}
                            disabled={checkedProfiles.length !== 1}
                            className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                          >
                            <User className="mr-2 h-4 w-4" />
                            Use Selected Personality
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500 border rounded-md">
                        <BookOpen className="mx-auto h-12 w-12 text-gray-300 mb-2" />
                        <p>No saved author profiles yet</p>
                        <p className="text-sm">Add a personality to get started</p>
                        <Link href="/dashboard/author-personality/add" className="mt-4 inline-block">
                          <Button className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 mt-4">
                            <Plus className="h-4 w-4 mr-2" />
                            Add Your First Personality
                          </Button>
                        </Link>
                      </div>
                    )}
                  </div>

                  {/* Add Personality Module */}
                  <div className="mt-8 pt-6 border-t border-gray-200">
                    <div className="text-center">
                      <button
                        onClick={() => window.location.href = '/dashboard/author-personality/add'}
                        className="p-6 rounded-full bg-gray-100 mb-4 hover:bg-gray-200 transition-colors cursor-pointer mx-auto block"
                      >
                        <Plus className="w-10 h-10 text-gray-600" />
                      </button>
                      <h3 className="text-xl font-semibold text-gray-900">Add New Personality</h3>
                      <p className="text-gray-500 mt-1 mb-4">
                        Create a new author personality to use for content generation
                      </p>
                      <Link href="/dashboard/author-personality/add">
                        <Button className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">
                          <Plus className="h-4 w-4 mr-2" />
                          Add Personality
                        </Button>
                      </Link>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="workflow">
                  <ContentAnalysisWorkflow />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
      </main>
      
      {/* Loading modal for campaigns */}
      <LoadingModal 
        isOpen={campaignsLoading} 
        title="Loading campaigns..." 
      />
    </div>
  )
}
