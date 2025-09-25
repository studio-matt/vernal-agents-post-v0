"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { Header } from "@/components/Header"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FileText, BarChart, ArrowRight, Plus, User, Trash2, BookOpen } from "lucide-react"
import { ContentPlannerCampaign, type Campaign } from "@/components/ContentPlannerCampaign"
import { ContentAnalysisWorkflow } from "@/components/ContentAnalysisWorkflow"
import { Checkbox } from "@/components/ui/checkbox"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { getAllCampaigns } from "@/components/Service"
import { toast } from "sonner"

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
  const [savedProfiles, setSavedProfiles] = useState(SAMPLE_AUTHOR_PROFILES)
  const [checkedProfiles, setCheckedProfiles] = useState<string[]>([])
  const [showContentPlanner, setShowContentPlanner] = useState(false)

  const searchParams = useSearchParams()
  const viewParam = searchParams.get("view")

  const [contentPlannerTab, setContentPlannerTab] = useState<"campaigns" | "workflow" | "settings">(
    viewParam === "workflow" ? "workflow" : viewParam === "settings" ? "settings" : "campaigns",
  )

  // Fetch campaigns on component mount and sort by createdAt (newest first)
  useEffect(() => {
    const fetchCampaigns = async () => {
      try {
        const response = await getAllCampaigns()
        if (response.status === "success") {
          const fetchedCampaigns = response.message.campaigns || []
          // Sort campaigns by createdAt in descending order (newest first)
          fetchedCampaigns.sort(
            (a: Campaign, b: Campaign) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
          )
          setCampaigns(fetchedCampaigns)
          setShowContentPlanner(true) // Show content planner by default
        } else {
          console.error("Failed to fetch campaigns:", response.message)
          toast({
            variant: "destructive",
            title: "Error",
            description: "Failed to load campaigns. Please try again.",
          })
        }
      } catch (error) {
        console.error("Error fetching campaigns:", error)
        toast({
          variant: "destructive",
          title: "Error",
          description: "An unexpected error occurred while loading campaigns.",
        })
      }
    }
    fetchCampaigns()
  }, [])

  const handleAddCampaign = (campaign: Omit<Campaign, "id" | "createdAt" | "updatedAt">) => {
    const newCampaign: Campaign = {
      ...campaign,
      id: `campaign-${Date.now()}`,
      createdAt: new Date(),
      updatedAt: new Date(),
    }

    setCampaigns((prev) => {
      const updatedCampaigns = [...prev, newCampaign]
      // Sort campaigns by createdAt in descending order (newest first)
      updatedCampaigns.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      return updatedCampaigns
    })
  }

  const handleEditCampaign = (id: string, updatedCampaign: Partial<Campaign>) => {
    setCampaigns((prev) => {
      const updatedCampaigns = prev.map((campaign) =>
        campaign.id === id ? { ...campaign, ...updatedCampaign, updatedAt: new Date() } : campaign,
      )
      // Sort campaigns by createdAt in descending order (newest first)
      updatedCampaigns.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      return updatedCampaigns
    })
  }

  const handleDeleteCampaign = (id: string) => {
    setCampaigns((prev) => {
      const updatedCampaigns = prev.filter((campaign) => campaign.id !== id)
      // Sort campaigns by createdAt in descending order (newest first)
      updatedCampaigns.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      return updatedCampaigns
    })
  }

  const handleStartPlanning = () => {
    setShowContentPlanner(true)
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

  const handleDeleteProfile = (profileId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSavedProfiles(savedProfiles.filter((profile) => profile.id !== profileId))
    if (checkedProfiles.includes(profileId)) {
      setCheckedProfiles((prev) => prev.filter((id) => id !== profileId))
    }
  }

  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <Header />
      <main className="p-6 max-w-7xl mx-auto space-y-6">
        <h1 className="text-4xl font-extrabold text-white">Content Planner</h1>

        {!showContentPlanner ? (
          <Card>
            <CardContent className="p-6 flex flex-col items-center justify-center text-center py-16">
              <div className="flex space-x-8 mb-8">
                <div className="flex flex-col items-center">
                  <div className="p-4 rounded-full bg-blue-100 mb-4">
                    <FileText className="w-8 h-8 text-blue-600" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">Content Planning</h3>
                  <p className="text-gray-500 max-w-xs">
                    Create campaigns based on keywords or URLs to analyze and generate content
                  </p>
                </div>
                <div className="flex flex-col items-center">
                  <div className="p-4 rounded-full bg-green-100 mb-4">
                    <BarChart className="w-8 h-8 text-green-600" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">Content Analysis</h3>
                  <p className="text-gray-500 max-w-xs">
                    Extract insights from your content sources using advanced NLP techniques
                  </p>
                </div>
              </div>
              <Button onClick={handleStartPlanning} size="lg" className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">
                Let's Start Planning
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="w-full">
            <CardContent className="p-6">
              <Tabs
                value={contentPlannerTab}
                onValueChange={(value) => setContentPlannerTab(value as "campaigns" | "workflow" | "settings")}
              >
                <TabsList className="w-full mb-6">
                  <TabsTrigger value="campaigns" className="flex-1">
                    Campaigns
                  </TabsTrigger>
                  <TabsTrigger value="workflow" className="flex-1">
                    Content Analysis Workflow
                  </TabsTrigger>
                  <TabsTrigger value="settings" className="flex-1">
                    Settings
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="campaigns">
                  <ContentPlannerCampaign
                    campaigns={campaigns && campaigns.length > 0 ? campaigns : []}
                    onAddCampaign={handleAddCampaign}
                    onEditCampaign={handleEditCampaign}
                    onDeleteCampaign={handleDeleteCampaign}
                  />
                </TabsContent>

                <TabsContent value="workflow">
                  <ContentAnalysisWorkflow />
                </TabsContent>

                <TabsContent value="settings">
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

                    {savedProfiles.length > 0 ? (
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
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
