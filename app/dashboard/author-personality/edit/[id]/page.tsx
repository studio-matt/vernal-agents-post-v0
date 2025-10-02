"use client";

import { AuthorMimicry } from "@/components/AuthorMimicry";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Header } from "@/components/Header";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRouter, useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getAllAuthorPersonalities, updateAuthorPersonality } from "@/components/AuthorPersonalityService";
import { toast } from "sonner";

interface AuthorPersonality {
  id: string;
  name: string;
  description: string;
  created_at?: string;
  updated_at?: string;
}

export default function EditAuthorPersonalityPage() {
  const router = useRouter();
  const params = useParams();
  const personalityId = params.id as string;
  
  const [personality, setPersonality] = useState<AuthorPersonality | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch the specific personality data
  useEffect(() => {
    const fetchPersonality = async () => {
      try {
        setLoading(true);
        const response = await getAllAuthorPersonalities();
        
        if (response.status === "success") {
          const personalities = response.message.personalities || [];
          const foundPersonality = personalities.find((p: AuthorPersonality) => p.id === personalityId);
          
          if (foundPersonality) {
            setPersonality(foundPersonality);
          } else {
            setError("Author personality not found");
          }
        } else {
          setError("Failed to load author personality");
        }
      } catch (error) {
        console.error("Error fetching personality:", error);
        setError("An error occurred while loading the author personality");
      } finally {
        setLoading(false);
      }
    };

    if (personalityId) {
      fetchPersonality();
    }
  }, [personalityId]);

  // Handle top-level tab changes
  const handleTopTabChange = (value: string) => {
    if (value === "author-planning") {
      router.push("/dashboard/author-planning");
    } else if (value === "content-planner") {
      router.push("/dashboard/content-planner");
    }
  };

  // Handle second-level tab changes
  const handleSecondTabChange = (value: string) => {
    if (value === "campaigns") {
      router.push("/dashboard/content-planner?view=campaigns");
    } else if (value === "workflow") {
      router.push("/dashboard/content-planner?view=workflow");
    } else if (value === "author-personalities") {
      router.push("/dashboard/content-planner?view=author-personalities");
    }
  };

  // Handle saving the updated personality
  const handleSavePersonality = async (updatedData: { name: string; description: string }) => {
    try {
      const response = await updateAuthorPersonality(personalityId, updatedData);
      
      if (response.status === "success") {
        toast.success("Author personality updated successfully!");
        // Navigate back to settings
        router.push("/dashboard/content-planner?view=author-personalities");
      } else {
        toast.error("Failed to update author personality. Please try again.");
      }
    } catch (error) {
      console.error("Error updating personality:", error);
      toast.error("An error occurred while updating the author personality.");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto">
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-blue-500"></div>
          </div>
        </main>
      </div>
    );
  }

  if (error || !personality) {
    return (
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto">
          <div className="text-center py-10">
            <h1 className="text-2xl font-bold text-white mb-4">Error</h1>
            <p className="text-white/80 mb-6">{error || "Author personality not found"}</p>
            <Link href="/dashboard/content-planner?view=author-personalities">
              <Button variant="outline" className="bg-white text-gray-700 hover:bg-gray-50">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Settings
              </Button>
            </Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto">
          <Card className="w-full">
            <CardContent className="p-6">
              <Tabs defaultValue="content-planner" onValueChange={handleTopTabChange}>
                <TabsList className="grid w-full grid-cols-2 mb-6">
                  <TabsTrigger value="author-planning">Author Planning</TabsTrigger>
                  <TabsTrigger value="content-planner">Content Planner</TabsTrigger>
                </TabsList>

                <TabsContent value="content-planner">
                  <Tabs defaultValue="author-personalities" onValueChange={handleSecondTabChange}>
                    <TabsList className="grid w-full grid-cols-3 mb-6">
                      <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
                      <TabsTrigger value="author-personalities">Author Personalities</TabsTrigger>
                      <TabsTrigger value="workflow">Workflow Explained</TabsTrigger>
                    </TabsList>

                    {/* Author Personalities tab content */}
                    <TabsContent value="author-personalities">
                      <div className="space-y-6">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Link href="/dashboard/content-planner?view=author-personalities">
                              <Button variant="outline" size="icon">
                                <ArrowLeft className="h-4 w-4" />
                              </Button>
                            </Link>
                            <h2 className="text-2xl font-bold">
                              Edit Author Personality
                            </h2>
                          </div>
                        </div>

                        <Card>
                          <CardHeader>
                            <CardTitle>Edit: {personality.name}</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <p className="text-gray-500 mb-6">
                              Modify the author personality settings and style characteristics.
                            </p>
                            <AuthorMimicry
                              showSavedProfiles={false}
                              defaultOpenSections={{
                                writingSamples: true,
                                modelConfig: false,
                                results: false,
                                profiles: false,
                              }}
                              onSavePersonality={handleSavePersonality}
                              initialPersonality={personality}
                            />
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>
                  </Tabs>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </main>
      </div>
    </TooltipProvider>
  );
}
