"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { storeOpenAIKey, storeClaudeKey, getUserCredentials } from "./Service";

interface ApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface ValidationResult {
  isValid: boolean;
  message: string;
}

export function ApiKeyModal({ isOpen, onClose, onSuccess }: ApiKeyModalProps) {
  const [openaiKey, setOpenaiKey] = useState("");
  const [claudeKey, setClaudeKey] = useState("");
  const [isValidating, setIsValidating] = useState(false);
  const [validationResults, setValidationResults] = useState<{
    openai?: ValidationResult;
    claude?: ValidationResult;
  }>({});
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);
  const [isCheckingStoredKeys, setIsCheckingStoredKeys] = useState(false);

  // Check for stored keys when modal opens
  useEffect(() => {
    if (isOpen) {
      checkStoredKeys();
    }
  }, [isOpen]);

  // Auto-validate keys when they change (with debounce)
  useEffect(() => {
    if (openaiKey.trim() || claudeKey.trim()) {
      const timeoutId = setTimeout(() => {
        if (openaiKey.trim().length > 10 || claudeKey.trim().length > 10) {
          handleValidateKeys();
        }
      }, 1000); // 1 second debounce
      
      return () => clearTimeout(timeoutId);
    }
  }, [openaiKey, claudeKey]);

  const checkStoredKeys = async () => {
    setIsCheckingStoredKeys(true);
    
    // Check localStorage first
    const localOpenAIKey = localStorage.getItem("openai_api_key");
    const localClaudeKey = localStorage.getItem("claude_api_key");
    
    if (localOpenAIKey || localClaudeKey) {
      console.log("🔍 Found stored keys in localStorage");
      setOpenaiKey(localOpenAIKey || "");
      setClaudeKey(localClaudeKey || "");
    } else {
      // Check backend for stored keys
      try {
        const response = await getUserCredentials();
        if (response.success && response.credentials) {
          const { openai_key, claude_key } = response.credentials;
          
          if (openai_key || claude_key) {
            console.log("🔍 Found backend keys");
            setOpenaiKey(openai_key || "");
            setClaudeKey(claude_key || "");
          }
        }
      } catch (error) {
        console.error("Failed to check stored credentials:", error);
      }
    }
    
    setIsCheckingStoredKeys(false);
  };

  const validateOpenAIKey = async (key: string): Promise<ValidationResult> => {
    try {
      console.log("🔍 Validating OpenAI key:", key ? "***" + key.slice(-4) : "empty");
      const response = await fetch("https://api.openai.com/v1/models", {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${key}`,
          "Content-Type": "application/json",
        },
      });

      console.log("🔍 OpenAI validation response:", response.status, response.statusText);
      
      if (response.ok) {
        console.log("✅ OpenAI API key is valid");
        return { isValid: true, message: "OpenAI API key is valid" };
      } else {
        console.log("❌ OpenAI API key is invalid");
        return { isValid: false, message: "Invalid OpenAI API key" };
      }
    } catch (error) {
      console.log("❌ OpenAI validation error:", error);
      return { isValid: false, message: "Failed to validate OpenAI API key" };
    }
  };

  const validateClaudeKey = async (key: string): Promise<ValidationResult> => {
    try {
      console.log("🔍 Validating Claude key:", key ? "***" + key.slice(-4) : "empty");
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "x-api-key": key,
          "Content-Type": "application/json",
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: "claude-3-haiku-20240307",
          max_tokens: 10,
          messages: [{ role: "user", content: "test" }],
        }),
      });

      console.log("🔍 Claude validation response:", response.status, response.statusText);
      
      if (response.ok) {
        console.log("✅ Claude API key is valid");
        return { isValid: true, message: "Claude API key is valid" };
      } else {
        console.log("❌ Claude API key is invalid");
        return { isValid: false, message: "Invalid Claude API key" };
      }
    } catch (error) {
      console.log("❌ Claude validation error:", error);
      return { isValid: false, message: "Failed to validate Claude API key" };
    }
  };

  const handleValidateKeys = async () => {
    setIsValidating(true);
    setValidationResults({});

    const results: { openai?: ValidationResult; claude?: ValidationResult } = {};

    // Validate OpenAI key if provided
    if (openaiKey.trim()) {
      const openaiResult = await validateOpenAIKey(openaiKey.trim());
      results.openai = openaiResult;
      
      // If OpenAI key is valid, don't validate Claude key
      if (openaiResult.isValid) {
        setValidationResults(results);
        setIsValidating(false);
        await handleValidKeysFound(results);
        return;
      }
    }

    // Only validate Claude key if OpenAI key is not provided or invalid
    if (claudeKey.trim()) {
      const claudeResult = await validateClaudeKey(claudeKey.trim());
      results.claude = claudeResult;
    }

    setValidationResults(results);
    setIsValidating(false);

    // Check if at least one key is valid
    const hasValidKey = Object.values(results).some(result => result.isValid);
    
    if (hasValidKey) {
      await handleValidKeysFound(results);
    } else {
      // Show error message if no valid keys
      console.log("No valid API keys provided");
      // Don't auto-close if no valid keys - let user enter new ones
    }
  };

  const handleValidKeysFound = async (results: { openai?: ValidationResult; claude?: ValidationResult }) => {
    // Store valid keys in localStorage and backend
    const storagePromises = [];
    
    if (results.openai?.isValid) {
      localStorage.setItem("openai_api_key", openaiKey.trim());
      console.log("✅ OpenAI API key stored in localStorage");
      storagePromises.push(storeOpenAIKey(openaiKey.trim()));
    }
    if (results.claude?.isValid) {
      localStorage.setItem("claude_api_key", claudeKey.trim());
      console.log("✅ Claude API key stored in localStorage");
      storagePromises.push(storeClaudeKey(claudeKey.trim()));
    }
    
    // Store keys in backend
    try {
      console.log("🔄 Storing API keys in backend...");
      const backendResults = await Promise.all(storagePromises);
      console.log("✅ Backend storage results:", backendResults);
      
      // Check if any backend storage failed
      const failedStorages = backendResults.filter(result => !result.success);
      if (failedStorages.length > 0) {
        console.error("❌ Some API keys failed to store in backend:", failedStorages);
      } else {
        console.log("✅ All API keys stored in backend successfully");
      }
    } catch (error) {
      console.error("❌ Failed to store API keys in backend:", error);
      // Continue anyway since keys are stored locally
    }
    
    // Show success message for a moment before closing
    setShowSuccessMessage(true);
    setTimeout(() => {
      onSuccess();
    }, 2000);
  };

  const handleClose = () => {
    setOpenaiKey("");
    setClaudeKey("");
    setValidationResults({});
    onClose();
  };

  const hasValidKey = Object.values(validationResults).some(result => result.isValid);
  const hasAnyKey = openaiKey.trim() || claudeKey.trim();

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>API Key Configuration Required</DialogTitle>
          <DialogDescription>
            In order to build a campaign, you need to connect at least one AI model to your account. 
            Please provide your API keys below. At least one valid key is required.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Loading state for checking stored keys */}
          {isCheckingStoredKeys && (
            <div className="flex items-center justify-center py-8">
              <div className="flex items-center space-x-2">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm text-gray-600">Validating stored LLM credentials...</span>
              </div>
            </div>
          )}

          {/* API Key Inputs - only show when not checking stored keys */}
          {!isCheckingStoredKeys && (
            <>
              {/* OpenAI Key */}
          <div className="space-y-2">
            <Label htmlFor="openai-key">OpenAI API Key</Label>
            <div className="flex items-center space-x-2">
              <Input
                id="openai-key"
                type="password"
                placeholder="sk-..."
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                className="flex-1"
              />
              {validationResults.openai && (
                <div className="flex items-center">
                  {validationResults.openai.isValid ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </div>
              )}
            </div>
            {validationResults.openai && (
              <p className={`text-sm ${
                validationResults.openai.isValid ? "text-green-600" : "text-red-600"
              }`}>
                {validationResults.openai.message}
              </p>
            )}
          </div>

          {/* Claude Key */}
          <div className="space-y-2">
            <Label htmlFor="claude-key">Claude API Key</Label>
            <div className="flex items-center space-x-2">
              <Input
                id="claude-key"
                type="password"
                placeholder="sk-ant-..."
                value={claudeKey}
                onChange={(e) => setClaudeKey(e.target.value)}
                className="flex-1"
              />
              {validationResults.claude && (
                <div className="flex items-center">
                  {validationResults.claude.isValid ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </div>
              )}
            </div>
            {validationResults.claude && (
              <p className={`text-sm ${
                validationResults.claude.isValid ? "text-green-600" : "text-red-600"
              }`}>
                {validationResults.claude.message}
              </p>
            )}
          </div>

          {/* Success Message */}
          {showSuccessMessage && (
            <div className="bg-green-50 border border-green-200 p-3 rounded-md">
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                <p className="text-sm text-green-800 font-medium">
                  API keys validated successfully! Starting campaign build...
                </p>
              </div>
            </div>
          )}

              {/* Help Text */}
              <div className="bg-blue-50 p-3 rounded-md">
                <p className="text-sm text-blue-800">
                  <strong>Need API keys?</strong><br />
                  • OpenAI: Get your key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="underline">platform.openai.com</a><br />
                  • Claude: Get your key from <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className="underline">console.anthropic.com</a>
                </p>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button 
            onClick={handleValidateKeys} 
            disabled={!hasAnyKey || isValidating}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isValidating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Validating...
              </>
            ) : (
              "Validate & Continue"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
