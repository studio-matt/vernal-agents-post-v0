"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Trash2, FileText } from "lucide-react";
import { ContentCreationFlow } from "./ContentCreationFlow";
import { Checkbox } from "@/components/ui/checkbox";

interface ContentQueueProps {
  queueItems: Array<{ id: string; type: string; name: string; source: string }>;
  onClearQueue: () => void;
}

export function ContentQueue({ queueItems, onClearQueue }: ContentQueueProps) {
  const [showContentCreationFlow, setShowContentCreationFlow] = useState(false);
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>(
    queueItems.reduce((acc, item) => ({ ...acc, [item.id]: true }), {})
  );

  const handleConfigureContentCreation = () => {
    const selectedItems = queueItems.filter((item) => checkedItems[item.id]);
    setShowContentCreationFlow(true);
  };

  const handleCloseContentCreationFlow = () => {
    setShowContentCreationFlow(false);
  };

  const handleCheckChange = (id: string, checked: boolean) => {
    setCheckedItems((prev) => ({ ...prev, [id]: checked }));
  };

  const [allTopics, setAllTopics] = useState([]);

  useEffect(() => {
    const stored = localStorage.getItem("topics");
    if (stored) {
      const parsed: string[] = JSON.parse(stored);
      setAllTopics(parsed);
    }
  }, []);

  useEffect(() => {
    const storedItems = JSON.parse(localStorage.getItem("topics") || "{}");
    const restoredCheckedItems: Record<string, boolean> = {};

    if (storedItems.topKeyword) {
      storedItems.topKeyword.forEach((keyword: string) => {
        restoredCheckedItems[`keyword-${keyword}`] = true;
      });
    }

    setCheckedItems(restoredCheckedItems);
  }, []);

  const handleCheckboxChange = (keyword: string, checked: boolean) => {
    const id = `keyword-${keyword}`;
    setCheckedItems((prev) => ({ ...prev, [id]: checked }));

    const keywordData = {
      id,
      type: "keyword",
      name: keyword,
      source: "Word Cloud",
    };

    // handleItemSelect(keywordData, checked);

    // Update localStorage
    const data = localStorage.getItem("contentGenPayload") || "{}";
    const parsed = JSON.parse(data);
    const prevKeywords: string[] = parsed.keywords || [];

    let updatedKeywords: string[];
    if (checked) {
      // Add keyword if not already present
      updatedKeywords = prevKeywords.includes(keyword)
        ? prevKeywords
        : [...prevKeywords, keyword];
    } else {
      // Remove keyword
      updatedKeywords = prevKeywords.filter((item) => item !== keyword);
    }

    const newData = {
      ...parsed,
      keywords: updatedKeywords,
    };

    localStorage.setItem("contentGenPayload", JSON.stringify(newData));
  };

  useEffect(() => {
    const data = localStorage.getItem("contentGenPayload") || "{}";
    const parsed = JSON.parse(data);
    const keywords: string[] = parsed.keywords || [];

    const initialCheckedItems: Record<string, boolean> = {};
    keywords.forEach((keyword) => {
      initialCheckedItems[`keyword-${keyword}`] = true;
    });

    setCheckedItems(initialCheckedItems);
  }, []);

  return (
    <div className="space-y-6">
      {showContentCreationFlow ? (
        <ContentCreationFlow
          onClose={handleCloseContentCreationFlow}
          selectedItems={queueItems}
        />
      ) : (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center">
              <FileText className="w-5 h-5 mr-2" />
              Content Queue
            </CardTitle>
            {queueItems.length > 0 && (
              <Button
                onClick={onClearQueue}
                variant="outline"
                size="sm"
                className="text-red-500 border-red-200 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Clear Queue
              </Button>
            )}
          </CardHeader>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Top Keywords</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              <div className="space-y-3">
                {allTopics.map((keyword, index) => {
                  const id = `keyword-${keyword}`;
                  return (
                    <div key={id}>
                      <div className="flex justify-between items-center">
                        <div className="flex items-center">
                          <Checkbox
                            id={id}
                            checked={!!checkedItems[id]}
                            onCheckedChange={(checked) =>
                              handleCheckboxChange(keyword, !!checked)
                            }
                            className="mr-2"
                          />
                          <label htmlFor={id}>{keyword}</label>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-end mt-4">
                <Button
                  className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                  onClick={handleConfigureContentCreation}
                >
                  Continue & Configure Content Creation with Checked
                </Button>
              </div>
            </CardContent>
          </Card>
        </Card>
      )}
    </div>
  );
}
