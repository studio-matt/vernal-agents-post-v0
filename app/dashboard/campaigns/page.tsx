"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { BookOpen, Plus } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const SAMPLE_AUTHOR_PROFILES = [
  { id: "1", name: "Profile 1" },
  { id: "2", name: "Profile 2" },
]

export default function CampaignsPage() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to the content planner page
    router.push("/dashboard/content-planner")
  }, [router])

  return (
    <Tabs defaultValue="campaigns" className="w-full">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="campaigns">Campaignszfsd</TabsTrigger>
        <TabsTrigger value="content-analysis">Content Analysis Workflow</TabsTrigger>
        <TabsTrigger value="settings">Settings</TabsTrigger>
      </TabsList>

      <TabsContent value="settings" className="mt-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">Campaign Settings</h2>
          <Link href="/dashboard/campaigns/settings">
            <Button variant="outline">View All Settings</Button>
          </Link>
        </div>

        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <BookOpen className="mr-2 h-5 w-5" />
                Author Personalities
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-gray-500">Manage author personalities to use for content generation.</p>
                <div className="flex justify-between">
                  <p>{SAMPLE_AUTHOR_PROFILES.length} personalities available</p>
                  <Link href="/dashboard/author-personality/add">
                    <Button className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">
                      <Plus className="mr-2 h-4 w-4" />
                      Add Personality
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </TabsContent>
    </Tabs>
  )
}
