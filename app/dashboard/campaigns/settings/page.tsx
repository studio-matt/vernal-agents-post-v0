"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { BookOpen, Plus, Trash2, User } from "lucide-react"
import Link from "next/link"
import { useState } from "react"
import { PersonalityConfirmationModal } from "@/components/PersonalityConfirmationModal"

// Sample author profiles for demonstration
const SAMPLE_AUTHOR_PROFILES = [
  { id: "1", name: "Ernest Hemingway", description: "Concise, direct prose with short sentences" },
  { id: "2", name: "Jane Austen", description: "Elegant, witty social commentary" },
  { id: "3", name: "David Foster Wallace", description: "Complex, footnote-heavy postmodern style" },
  { id: "4", name: "Stephen King", description: "Suspenseful, character-driven horror and thriller" },
  { id: "5", name: "Toni Morrison", description: "Poetic, rich with metaphor and cultural depth" },
]

export default function CampaignSettingsPage() {
  const [savedProfiles, setSavedProfiles] = useState(SAMPLE_AUTHOR_PROFILES)
  const [checkedProfiles, setCheckedProfiles] = useState<string[]>([])
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false)
  const [selectedPersonalityName, setSelectedPersonalityName] = useState("")

  // Handle profile checkbox selection
  const handleProfileCheckChange = (profileId: string) => {
    setCheckedProfiles((prev) => {
      if (prev.includes(profileId)) {
        return prev.filter((id) => id !== profileId)
      } else {
        return [profileId] // Only allow one selection at a time
      }
    })
  }

  // Handle selecting a profile for use
  const handleSelectProfile = () => {
    if (checkedProfiles.length === 1) {
      const selectedProfile = savedProfiles.find((p) => p.id === checkedProfiles[0])
      if (selectedProfile) {
        setSelectedPersonalityName(selectedProfile.name)
        setIsConfirmModalOpen(true)
      }
    }
  }

  // Handle confirmation
  const handleConfirmSelection = () => {
    // In a real app, this would apply the selected profile
    setIsConfirmModalOpen(false)
    setCheckedProfiles([])
  }

  // Handle deleting a profile
  const handleDeleteProfile = (profileId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSavedProfiles(savedProfiles.filter((profile) => profile.id !== profileId))
    if (checkedProfiles.includes(profileId)) {
      setCheckedProfiles((prev) => prev.filter((id) => id !== profileId))
    }
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Campaign Settings</h1>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center">
            <BookOpen className="mr-2 h-5 w-5" />
            Author Personalities
          </CardTitle>
          <Link href="/dashboard/author-personality/add">
            <Button className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">
              <Plus className="mr-2 h-4 w-4" />
              Add Personality
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {savedProfiles.length > 0 ? (
            <div className="space-y-4">
              <div className="space-y-2">
                {savedProfiles.map((profile) => (
                  <div
                    key={profile.id}
                    className={`p-3 border rounded-md flex items-center justify-between ${
                      checkedProfiles.includes(profile.id) ? "bg-gray-100 border-gray-400" : "hover:bg-gray-50"
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <input
                        type="radio"
                        id={`profile-${profile.id}`}
                        checked={checkedProfiles.includes(profile.id)}
                        onChange={() => handleProfileCheckChange(profile.id)}
                        className="h-4 w-4"
                      />
                      <div>
                        <label htmlFor={`profile-${profile.id}`} className="font-medium cursor-pointer">
                          {profile.name}
                        </label>
                        <p className="text-sm text-gray-500">{profile.description}</p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => handleDeleteProfile(profile.id, e)}
                      className="opacity-70 hover:opacity-100"
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
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
            <div className="text-center py-8 text-gray-500">
              <BookOpen className="mx-auto h-12 w-12 text-gray-300 mb-2" />
              <p>No saved author profiles yet</p>
              <p className="text-sm">Add a personality to get started</p>
            </div>
          )}
        </CardContent>
      </Card>

      <PersonalityConfirmationModal
        isOpen={isConfirmModalOpen}
        onClose={() => setIsConfirmModalOpen(false)}
        onConfirm={handleConfirmSelection}
        personalityName={selectedPersonalityName}
      />
    </div>
  )
}
