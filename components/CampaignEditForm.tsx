"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Trash2, ExternalLink, Key } from "lucide-react";
import { ErrorDialog } from "./ErrorDialog";
import type { Campaign } from "./ContentPlannerCampaign";

interface CampaignEditFormProps {
  campaign: Campaign;
  onSave: (updatedCampaign: Partial<Campaign>) => void;
}

export function CampaignEditForm({ campaign, onSave }: CampaignEditFormProps) {
  const [name, setName] = useState(campaign.name);
  const [description, setDescription] = useState(campaign.description);
  const [type, setType] = useState<"keyword" | "url">(campaign.type);
  const [keywordInput, setKeywordInput] = useState("");
  const [keywords, setKeywords] = useState<string[]>(campaign.keywords || []);
  const [urlInput, setUrlInput] = useState("");
  const [urls, setUrls] = useState<string[]>(campaign.urls || []);
  const [error, setError] = useState<{ isOpen: boolean; message: string }>({
    isOpen: false,
    message: "",
  });

  const handleAddKeyword = () => {
    if (keywordInput.trim()) {
      setKeywords([...keywords, keywordInput.trim()]);
      setKeywordInput("");
    }
  };

  const handleRemoveKeyword = (index: number) => {
    setKeywords(keywords.filter((_, i) => i !== index));
  };

  const handleAddUrl = () => {
    if (urlInput.trim()) {
      try {
        // Add protocol if missing
        let urlToAdd = urlInput.trim();
        if (!/^https?:\/\//i.test(urlToAdd)) {
          urlToAdd = "https://" + urlToAdd;
        }

        // Validate URL
        new URL(urlToAdd);

        // If validation passes, add the URL
        setUrls([...urls, urlToAdd]);
        setUrlInput("");
      } catch (e) {
        setError({
          isOpen: true,
          message:
            "Please enter a valid URL (e.g., example.com or https://example.com)",
        });
      }
    }
  };

  const handleRemoveUrl = (index: number) => {
    setUrls(urls.filter((_, i) => i !== index));
  };

  const handleSave = () => {
    if (!name.trim()) {
      setError({
        isOpen: true,
        message: "Please enter a campaign name",
      });
      return;
    }

    if (type === "keyword" && keywords.length === 0) {
      setError({
        isOpen: true,
        message: "Please add at least one keyword or phrase",
      });
      return;
    }

    if (type === "url" && urls.length === 0) {
      setError({
        isOpen: true,
        message: "Please add at least one URL",
      });
      return;
    }

    onSave({
      name,
      description,
      type,
      keywords: type === "keyword" ? keywords : undefined,
      urls: type === "url" ? urls : undefined,
    });
  };

  const closeErrorDialog = () => {
    setError({ isOpen: false, message: "" });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-6 space-y-6">
          <div className="space-y-2">
            <Label htmlFor="campaign-name">Campaign Name</Label>
            <Input
              id="campaign-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter campaign name"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="campaign-description">Description</Label>
            <Textarea
              id="campaign-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter campaign description"
            />
          </div>

          <Tabs
            value={type}
            onValueChange={(value) => setType(value as "keyword" | "url")}
          >
            <TabsList className="w-full">
              <TabsTrigger value="keyword" className="flex-1">
                <Key className="w-4 h-4 mr-2" />
                Keywords/Phrases
              </TabsTrigger>
              <TabsTrigger value="url" className="flex-1">
                <ExternalLink className="w-4 h-4 mr-2" />
                URLs
              </TabsTrigger>
            </TabsList>

            <TabsContent value="keyword" className="space-y-4">
              <div className="flex space-x-2">
                <Input
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  placeholder="Enter keyword or phrase"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddKeyword();
                    }
                  }}
                />
                <Button onClick={handleAddKeyword}>Add</Button>
              </div>

              {keywords.length > 0 && (
                <div className="border rounded-md p-4">
                  <Label className="mb-2 block">Keywords/Phrases:</Label>
                  <div className="flex flex-wrap gap-2">
                    {keywords.map((keyword, index) => (
                      <div
                        key={index}
                        className="flex items-center bg-secondary text-secondary-foreground px-3 py-1 rounded-full"
                      >
                        <span>{keyword}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-auto p-1 ml-1"
                          onClick={() => handleRemoveKeyword(index)}
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="url" className="space-y-4">
              <div className="flex space-x-2">
                <Input
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="Enter URL (e.g., https://example.com)"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddUrl();
                    }
                  }}
                />
                <Button onClick={handleAddUrl}>Add</Button>
              </div>

              {urls.length > 0 && (
                <div className="border rounded-md p-4">
                  <Label className="mb-2 block">URLs:</Label>
                  <div className="space-y-2">
                    {urls.map((url, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between bg-secondary text-secondary-foreground p-2 rounded"
                      >
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline truncate"
                        >
                          {url}
                        </a>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-auto p-1 ml-1"
                          onClick={() => handleRemoveUrl(index)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>

          <div className="flex justify-end pt-4">
            <Button
              onClick={handleSave}
              className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
            >
              Save Basic Settings
            </Button>
          </div>
        </CardContent>
      </Card>
      <ErrorDialog
        isOpen={error.isOpen}
        onClose={closeErrorDialog}
        message={error.message}
      />
    </div>
  );
}
