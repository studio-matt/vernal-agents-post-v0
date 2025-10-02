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
import { useState, useRef, useEffect } from "react";

export default function AddAuthorPersonalityPage() {
  const router = useRouter();
  const [contentPlannerTab, setContentPlannerTab] = useState<"campaigns" | "workflow" | "author-personalities">("author-personalities");
  const formRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to form when page loads (mirroring create campaign behavior)
  useEffect(() => {
    setTimeout(() => {
      if (formRef.current) {
        formRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 100);
  }, []);

  // Handle content planner tab changes
  const handleContentPlannerTabChange = (value: string) => {
    if (value === "campaigns") {
      router.push("/dashboard/content-planner");
    } else if (value === "workflow") {
      router.push("/dashboard/content-planner?tab=workflow");
    } else if (value === "author-personalities") {
      // Stay on current page
      setContentPlannerTab("author-personalities");
    }
  };

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[#7A99A8]">
        <Header />
        <main className="p-6 max-w-7xl mx-auto space-y-6">
          <h1 className="text-4xl font-extrabold text-white">
            Content Planner
          </h1>

          <Card>
            <CardHeader>
              <CardTitle>Add Author Personality</CardTitle>
            </CardHeader>

            <CardContent className="p-6">
              {/* Content Planner tabs */}
              <Tabs
                value={contentPlannerTab}
                onValueChange={handleContentPlannerTabChange}
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

              <TabsContent value="author-personalities">
                <div ref={formRef} className="space-y-6">
                  <Card>
                    <CardHeader>
                      <div className="flex justify-between items-center">
                        <CardTitle>Create New Author Personality</CardTitle>
                        <Button
                          variant="ghost"
                          onClick={() => {
                            router.push("/dashboard/content-planner");
                          }}
                          className="text-gray-500 hover:text-gray-700"
                        >
                          Cancel, return to Content Planner
                        </Button>
                      </div>
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

              <TabsContent value="workflow">
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Workflow Explained</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-gray-500 mb-6">
                        This section explains the content analysis workflow process.
                      </p>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </main>
      </div>
    </TooltipProvider>
  );
}
