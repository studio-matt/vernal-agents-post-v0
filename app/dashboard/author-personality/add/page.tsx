"use client";

import { AuthorMimicry } from "@/components/AuthorMimicry";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Header } from "@/components/Header";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRouter } from "next/navigation";

export default function AddAuthorPersonalityPage() {
  const router = useRouter();

  // Handle top-level tab changes
  const handleTopTabChange = (value: string) => {
    if (value === "author-planning") {
      router.push("/dashboard?tab=author-planning");
    } else if (value === "content-planner") {
      router.push("/dashboard?tab=content-planner");
    }
  };

  // Handle second-level tab changes
  const handleSecondTabChange = (value: string) => {
    if (value === "campaigns") {
      router.push("/dashboard?tab=content-planner&view=campaigns");
    } else if (value === "workflow") {
      router.push("/dashboard?tab=content-planner&view=workflow");
    } else if (value === "settings") {
      router.push("/dashboard?tab=content-planner&view=settings");
    }
  };

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <h1 className="text-4xl font-extrabold text-white">
            Admin Dashboard
          </h1>

          {/* Top-level tabs */}
          <Tabs
            defaultValue="content-planner"
            className="w-full"
            onValueChange={handleTopTabChange}
          >
            <TabsList className="w-full mb-4 bg-white">
              <TabsTrigger value="author-planning" className="flex-1">
                Author Planning
              </TabsTrigger>
              <TabsTrigger value="content-planner" className="flex-1">
                Content Planner
              </TabsTrigger>
            </TabsList>

            {/* Content Planner tab content */}
            <TabsContent value="content-planner" className="space-y-6">
              <Card className="w-full">
                <CardContent className="p-6">
                  {/* Second-level tabs */}
                  <Tabs
                    defaultValue="settings"
                    onValueChange={handleSecondTabChange}
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

                    {/* Settings tab content */}
                    <TabsContent value="settings">
                      <div className="space-y-6">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Link href="/dashboard?tab=content-planner&view=settings">
                              <Button variant="outline" size="icon">
                                <ArrowLeft className="h-4 w-4" />
                              </Button>
                            </Link>
                            <h2 className="text-2xl font-bold">
                              Add Author Personality
                            </h2>
                          </div>
                        </div>

                        <Card>
                          <CardHeader>
                            <CardTitle>Create New Author Personality</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <p className="text-gray-500 mb-6">
                              Upload writing samples and analyze the author's
                              style to create a new personality profile that can
                              be used for content generation.
                            </p>
                            <AuthorMimicry
                              showSavedProfiles={false}
                              defaultOpenSections={{
                                writingSamples: true,
                                modelConfig: false,
                                results: false,
                                profiles: false,
                              }}
                            />
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </main>
      </div>
    </TooltipProvider>
  );
}
