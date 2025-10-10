import axios, { type AxiosResponse } from "axios"

// const API_BASE_URL = "https://9167-2405-201-3009-d013-b1a1-3a83-9303-f835.ngrok-free.app";
// const API_BASE_URL = "https://multiagent-933293844713.us-central1.run.app";

const API_BASE_URL = "https://themachine.vernalcontentum.com";

/**
 * Generic service for making API calls
 */

interface TrendingContentPayload {
  trendingKeyword: string
  campaign_id: string
  campaign_name: string
  description: string
}

export const Service = async (
  endpoint: string,
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH",
  formData: any = {},
  queryParams?: Record<string, string>,
  formUrlEncoded = false,
): Promise<any> => {
  const queryString = queryParams ? `?${new URLSearchParams(queryParams).toString()}` : ""

  const url = `${API_BASE_URL}/${endpoint}${queryString}`
  const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null

  console.log(`🌐 Service call: ${method} ${url}`)
  console.log(`🔑 Token present: ${!!token}`)
  console.log(`📦 Payload:`, formData)

  try {
    const headers: Record<string, string> = {
      "ngrok-skip-browser-warning": "true",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }

    let dataToSend = formData

    if (formData instanceof FormData) {
      headers["Content-Type"] = "multipart/form-data"
    } else if (formUrlEncoded) {
      headers["Content-Type"] = "application/x-www-form-urlencoded"
      dataToSend = new URLSearchParams(formData).toString()
    } else {
      headers["Content-Type"] = "application/json"
      dataToSend = formData
    }

    const response: AxiosResponse = await axios({
      method,
      url,
      data: method !== "GET" ? dataToSend : undefined,
      headers: {
        ...headers,
        Accept: "application/json",
      },
    })

    console.log(`✅ API response status: ${response.status}`)
    console.log(`📊 API response data:`, response.data)
    
    return response.data
  } catch (error) {
    console.error(`❌ Error during API call to ${endpoint}:`, error)
    throw error
  }
}


/**
 * Call the /signup endpoint
 * @param name - User full name
 * @param email - User email
 * @param password - User password
 */
export const signupUser = async ({
  username,
  email,
  password,
  contact,
}: {
  username: string
  email: string
  password: string
  contact: string
}): Promise<any> => {
  try {
    console.log("[v0] Using real backend signup")
    
    const response = await Service("auth/signup", "POST", {
      username,
      email,
      password,
      contact,
    })
    
    console.log("[v0] Signup response:", response)
    
    return {
      status: response.status === "success" ? 200 : 400,
      message: response.message || "Signup completed",
      user: response.user
    }
  } catch (error: any) {
    console.error("Error during signup:", error)
    return {
      status: "error",
      message: error.response?.data?.detail || "Signup failed. Please try again.",
    }
  }
}



export const deletePostById = async (id: string): Promise<any> => {
  try {
    const endpoint = `posts/${id}`

    const response = await Service(endpoint, "DELETE", undefined, undefined, undefined)

    return {
      status: "success",
      message: response,
    }
  } catch (error: any) {
    console.error("Error during deletion:", error)

    const errorMessage =
      error?.response?.data?.detail || error?.message || "An unexpected error occurred. Please try again."

    return {
      status: "error",
      message: errorMessage,
    }
  }
}



export const verifyEmail = async ({
  email,
  otp_code,
}: {
  email: string
  otp_code: string
}): Promise<any> => {
  try {
    console.log("[v0] Using real backend email verification")
    
    const response = await Service("auth/verify-email", "POST", {
      email,
      otp_code,
    })
    
    console.log("[v0] Email verification response:", response)
    
    return {
      status: response.status === "success" ? 200 : 400,
      message: response.message || "Email verification completed"
    }
  } catch (error: any) {
    console.error("Error during email verification:", error)
    return {
      status: "error",
      message: error.response?.data?.detail || "Email verification failed. Please try again.",
    }
  }
}



export const forgetPassword = async ({
  email,
}: {
  email: string
}): Promise<any> => {
  try {
    const endpoint = "forget-password"

    const payload = {
      email,
    }

    const response = await Service(endpoint, "POST", payload)

    return {
      status: response?.status || 200,
      message: response?.message || "OTP sent successfully",
    }
  } catch (error: any) {
    console.error("Error during forget password:", error)

    const errorMessage = error?.response?.data?.detail || error?.message || "Failed to send OTP. Please try again."

    return {
      status: "error",
      message: errorMessage,
    }
  }
}



export const resetPassword = async ({
  email,
  otp_code,
  new_password,
}: {
  email: string
  otp_code: string
  new_password: string
}): Promise<any> => {
  try {
    const endpoint = "reset-password"

    const payload = {
      email,
      otp_code,
      new_password,
    }

    const response = await Service(endpoint, "POST", payload)

    return {
      status: response?.status || 200,
      message: response?.message || "Password reset successfully",
      token: response?.token || response?.access_token,
    }
  } catch (error: any) {
    console.error("Error during password reset:", error)

    const errorMessage = error?.response?.data?.detail || error?.message || "Password reset failed. Please try again."

    return {
      status: "error",
      message: errorMessage,
    }
  }
}



export const resendotp = async ({
  email,
}: {
  email: string
}): Promise<any> => {
  try {
    const endpoint = "resend-otp"

    const payload = {
      email,
    }

    const response = await Service(endpoint, "POST", payload)

    return {
      status: response?.status || 200,
      message: response?.message || "OTP resent successfully",
    }
  } catch (error: any) {
    console.error("Error during OTP resend:", error)

    const errorMessage = error?.response?.data?.detail || error?.message || "Failed to resend OTP. Please try again."

    return {
      status: "error",
      message: errorMessage,
    }
  }
}



/**
 * Call the /login endpoint
 * @param email - User email
 * @param password - User password
 */
export const loginUser = async ({
  username,
  password,
}: {
  username: string
  password: string
}): Promise<any> => {
  try {
    console.log("[v0] Using real backend login")
    
    const response = await Service("auth/login", "POST", {
      username,
      password,
    })
    
    console.log("[v0] Login response:", response)
    
    return {
      status: response.status,
      token: response.token,
      user: response.user
    }
  } catch (error: any) {
    console.error("[v0] Error during login:", error)
    return {
      status: "error",
      message: error.response?.data?.detail || "Login failed. Please try again.",
    }
  }
}



export const deleteCampaignsById = async (campaign_id: string) => {
  try {
    console.log("🗑️ Deleting campaign:", campaign_id);
    // Use local API instead of external API
    const response = await fetch(`/api/campaigns/${campaign_id}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(typeof window !== 'undefined' && localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
      },
    });

    console.log("🗑️ Delete response status:", response.status);
    const data = await response.json();
    console.log("🗑️ Delete response data:", data);

    if (data?.status === "success") {
      console.log("✅ Campaign deleted successfully from backend");
      return {
        status: "success",
        message: "Deleted Successfully",
      }
    } else {
      console.error("❌ Error in deleting campaign:", data?.message || data?.error)
      return {
        status: "error",
        message: data?.message || data?.error || "Error in deleting campaign",
      }
    }
  } catch (error) {
    console.error("❌ Error in deleting campaign", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred while deleting campaigns.",
    }
  }
}



export const getTrendingContent = async (payload: TrendingContentPayload) => {
  try {
    const { trendingKeyword, campaign_id, campaign_name, description } = payload

    const queryParams = new URLSearchParams({
      query: trendingKeyword,
      campaign_id,
      campaign_name,
      description,
    }).toString()

    const endpoint = `search?${queryParams}`

    const response = await Service(endpoint, "GET", undefined, undefined, false)

    if (response?.status === "success") {
      return {
        status: "success",
        message: response.tweets,
      }
    } else {
      console.error("Analyze failed:", response?.message || response?.error)
      return {
        status: "error",
        message: response?.message || response?.error || "Failed to get trending topics.",
      }
    }
  } catch (error) {
    console.error("Error during analyze:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred in trending topics.",
    }
  }
}



export const generateContent = async ({
  campaign_name,
  campaign_id,
  urls = [],
  query = "",
  description = "",
  keywords = [],
  type = "keyword",
  depth = 3,
  max_pages = 10,
  batch_size = 1,
  include_links = true,
  stem = false,
  lemmatize = false,
  remove_stopwords_toggle = false,
  extract_persons = false,
  extract_organizations = false,
  extract_locations = false,
  extract_dates = false,
  topic_tool = "lda",
  num_topics = 3,
  iterations = 25,
  pass_threshold = 0.7,
}: AnalyzeTrendsInput): Promise<AnalyzeTrendsResponse> => {
  try {
    const endpoint = "analyze"

    const payload: AnalyzeTrendsInput = {
      campaign_name,
      campaign_id,
      urls,
      query,
      description,
      keywords,
      type,
      depth,
      max_pages,
      batch_size,
      include_links,
      stem,
      lemmatize,
      remove_stopwords_toggle,
      extract_persons,
      extract_organizations,
      extract_locations,
      extract_dates,
      topic_tool,
      num_topics,
      iterations,
      pass_threshold,
    }

    const response = await Service(endpoint, "POST", payload, undefined, false)

    if (response?.status === "success") {
      return {
        status: "success",
        task: response.task,
        campaign_name: response.campaign_name,
        campaign_id: response.campaign_id,
        keywords: response.keywords || keywords,
        posts: response.posts,
        topics: response.topics,
      }
    } else {
      console.error("Analyze failed:", response?.message || response?.error)
      return {
        status: "error",
        message: response?.message || response?.error || "Unexpected analyze response",
      }
    }
  } catch (error) {
    console.error("Error during analyze:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred during analysis.",
    }
  }
}



export const getScheduledPosts = async () => {
  try {
    // Use local API instead of external API
    const response = await fetch('/api/scheduled-posts', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(typeof window !== 'undefined' && localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
      },
    });

    const data = await response.json();
    console.log("getScheduledPosts", data);

    if (data?.status === "success") {
      return {
        status: "success",
        message: data,
      }
    } else {
      console.error("Failed to get scheduled posts:", data?.message || data?.error)
      return {
        status: "error",
        message: data?.message || data?.error || "Failed to get scheduled posts.",
      }
    }
  } catch (error) {
    console.error("Error during getScheduledPosts:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred in getScheduledPosts.",
    }
  }
}



export const generateIdeas = async () => {
  try {
    const endpoint = "generate-ideas"

    const dataRaw = (typeof window !== 'undefined' ? localStorage.getItem("contentGenPayload") : null) || "{}"
    const textData = (typeof window !== 'undefined' ? localStorage.getItem("text") : null) || ""

    const data = JSON.parse(dataRaw)

    // Format: "Topic A", "Topic B"
    const formattedTopics = Array.isArray(data.keywords) ? data.keywords.map((t: string) => `"${t}"`).join(" ,") : ""

    // Format: "\"Your post here\""
    const formattedPost = `"${textData}"`

    // Format: Monday, Tuesday
    const formattedDays = Array.isArray(data.activeDays) ? data.activeDays.join(", ") : ""

    const formBody = new URLSearchParams()
    formBody.append("topics", formattedTopics)
    formBody.append("posts", formattedPost)
    formBody.append("days", formattedDays)

    const response = await fetch(`${API_BASE_URL}/generate-ideas`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
      },
      body: formBody.toString(),
    })

    const result = await response.json()

    if (result?.status === "success") {
      return {
        status: "success",
        message: result,
      }
    } else {
      console.error("Analyze failed:", result?.message || result?.error)
      return {
        status: "error",
        message: result?.message || result?.error || "Unexpected analyze response",
      }
    }
  } catch (error) {
    console.error("Error during analyze:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred during analysis.",
    }
  }
}



export const generateContentAPI = async () => {
  try {
    const endpoint = "generate_content"

    // Retrieve data from localStorage
    // let payloadData = localStorage.getItem("contentGenPayload");
    const payloadData = typeof window !== 'undefined' ? localStorage.getItem("contentGenPayload") : null
    const payloadTextData = typeof window !== 'undefined' ? localStorage.getItem("text") : null

    let newPayloadData
    let newPayloadTextData

    if (payloadData && payloadTextData) {
      newPayloadData = JSON.parse(payloadData)
      newPayloadTextData = JSON.parse(payloadTextData)
    }

    // Dynamically create the payload from the data
    const payload = {
      platforms: newPayloadData?.activePlatforms.join(", "),
      no_of_posts_per_day: Number.parseInt(newPayloadData?.defaultPosts) || 3,
      feature_weight: newPayloadData.featureWeight || 0.1,
      syntactic_patterns: newPayloadData.syntacticPatterns || false,
      sample_text: newPayloadTextData || "Concise", // Default to "Concise" if no text is provided
      complexity_level: newPayloadData.complexityLevel || "medium",
      topics: newPayloadData.ideas.join(", "), // Concatenate ideas into a single string
      configuration_preset: newPayloadData.configurationPreset || "balanced",
      author: newPayloadData.author || "Ernest Hemingway", // Use default author if not available
      rhetorical_devices: newPayloadData.rhetoricalDevices || false,
      text: payloadTextData || "", // Include the provided text data
      max_tokens: newPayloadData.maxTokens || 500,
      sample_size: newPayloadData.sampleSize || 10,
      days: newPayloadData.activeDays.join(", "), // Join active days with commas
      lexical_features: newPayloadData.lexicalFeatures || false,
      structural_elements: newPayloadData.structuralElements || false,
      creativity_level: newPayloadData.creativityLevel || 0.1,
      semantic_characteristics: newPayloadData.semanticCharacteristics || false,
    }

    // Sending the request to the API
    const response = await Service(endpoint, "POST", payload, undefined, true)
    console.log("API Response:", response)

    if (response?.status === "success") {
      return {
        status: "success",
        message: response.generated_content,
      }
    } else {
      console.error("Content generation failed:", response?.message || response?.error)
      return {
        status: "error",
        message: response?.message || response?.error || "Failed to generate content.",
      }
    }
  } catch (error) {
    console.error("Error during content generation:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred during content generation.",
    }
  }
}



export const regenerateContentAPI = async ({ id, query, platform }: { id: string; query: string; platform: string }) => {
  try {
    const endpoint = `regenerate_script_machine_content?id=${id}&query=${encodeURIComponent(
      query,
    )}&platform=${platform}`

    const response = await Service(endpoint, "PUT", null, undefined, true)

    if (response?.status === "success") {
      return {
        status: "success",
        message: response.content,
      }
    } else {
      console.error("Regenerate failed:", response?.message || response?.error)
      return {
        status: "error",
        message: response?.message || response?.error || "Unexpected regenerate response",
      }
    }
  } catch (error) {
    console.error("Error during regenerate:", error)
    return {
      status: "error",
      message: "Content regeneration failed due to unexpected error.",
    }
  }
}



export const generateImageMachineContent = async (payload: {
  id: string
  query: string
}) => {
  try {
    const { id, query } = payload

    const queryParams = new URLSearchParams({
      id,
      query,
    }).toString()

    const endpoint = `generate_image_machine_content?${queryParams}`

    const response = await Service(
      endpoint,
      "POST",
      undefined,
      {
        accept: "application/json",
      },
      false,
    )
    if (response?.status === "success") {
      return {
        status: "success",
        message: response.image_url,
      }
    } else {
      console.error("Image generation failed:", response?.message || response?.error)
      return {
        status: "error",
        message: response?.message || response?.error || "Failed to generate image.",
      }
    }
  } catch (error) {
    console.error("Error during image generation:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred during image generation.",
    }
  }
}



export const storeClaudeKey = async (apiKey: string): Promise<any> => {
  try {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null

    if (!token) {
      console.error("No token found in localStorage.")
      return { success: false, message: "No token found" }
    }

    if (!apiKey) {
      console.error("No API key provided.")
      return { success: false, message: "API key is required" }
    }

    console.log("🔄 Storing Claude key via local API...");
    const response = await fetch('/api/credentials/claude', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ api_key: apiKey }),
    });

    const data = await response.json();
    console.log("🔄 Claude key storage response:", data);

    if (data?.status === "success") {
      return {
        success: true,
        message: data.message || "Claude key stored successfully",
      }
    } else {
      const errorMessage = data?.message || "Failed to store Claude API key"
      console.error("Failed to store Claude key:", data)
      return { success: false, message: errorMessage }
    }
  } catch (error: any) {
    console.error("Error during Claude key storage:", error)
    return {
      success: false,
      message: error?.message || "Failed to store Claude API key",
    }
  }
}



// Function to fetch stored user credentials
export const getUserCredentials = async (): Promise<any> => {
  try {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null
    console.log("🔍 getUserCredentials: Token exists:", !!token)

    if (!token) {
      console.error("No token found in localStorage.")
      return { success: false, message: "No token found" }
    }

    console.log("🔍 getUserCredentials: Calling local API...");
    const response = await fetch('/api/credentials', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await response.json();
    console.log("🔍 getUserCredentials: API response:", data);

    if (data?.status === "success") {
      console.log("✅ getUserCredentials: Success, credentials:", data.credentials);
      return {
        success: true,
        credentials: data.credentials || {},
      }
    } else {
      const errorMessage = data?.message || "Failed to fetch credentials"
      console.error("❌ getUserCredentials: Failed to fetch credentials:", data)
      return { success: false, message: errorMessage }
    }
  } catch (error: any) {
    console.error("❌ getUserCredentials: Error during credentials fetch:", error)
    return {
      success: false,
      message: error?.message || "Failed to fetch credentials",
    }
  }
}



export const storeElevenLabsKey = async (apiKey: string): Promise<any> => {
  try {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null

    if (!token) {
      console.error("No token found in localStorage.")
      return { success: false, message: "No token found" }
    }

    if (!apiKey) {
      console.error("No API key provided.")
      return { success: false, message: "API key is required" }
    }

    const response = await Service("store_elevenlabs_key", "POST", { api_key: apiKey }, undefined, true)

    if (response?.status === "success") {
      return {
        success: true,
        message: response.message || "ElevenLabs key stored successfully",
      }
    } else {
      const errorMessage = response?.detail?.[0]?.msg || response?.message || "Failed to store ElevenLabs API key"
      console.error("Failed to store ElevenLabs key:", response)
      return { success: false, message: errorMessage }
    }
  } catch (error: any) {
    console.error("Error during ElevenLabs key storage:", error)
    return {
      success: false,
      message: error?.detail?.[0]?.msg || "Failed to store ElevenLabs API key",
    }
  }
}



export const storeMidjourneyKey = async (apiKey: string): Promise<any> => {
  try {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null

    if (!token) {
      console.error("No token found in localStorage.")
      return { success: false, message: "No token found" }
    }

    if (!apiKey) {
      console.error("No API key provided.")
      return { success: false, message: "API key is required" }
    }

    const response = await Service("store_midjourney_key", "POST", { api_key: apiKey }, undefined, true)

    if (response?.status === "success") {
      return {
        success: true,
        message: response.message || "Midjourney key stored successfully",
      }
    } else {
      const errorMessage = response?.detail?.[0]?.msg || response?.message || "Failed to store Midjourney API key"
      console.error("Failed to store Midjourney key:", response)
      return { success: false, message: errorMessage }
    }
  } catch (error: any) {
    console.error("Error during Midjourney key storage:", error)
    return {
      success: false,
      message: error?.detail?.[0]?.msg || "Failed to store Midjourney API key",
    }
  }
}



export const storeOpenAIKey = async (apiKey: string): Promise<any> => {
  try {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null

    if (!token) {
      console.error("No token found in localStorage.")
      return { success: false, message: "No token found" }
    }

    if (!apiKey) {
      console.error("No API key provided.")
      return { success: false, message: "API key is required" }
    }

    console.log("🔄 Storing OpenAI key via local API...");
    const response = await fetch('/api/credentials/openai', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ api_key: apiKey }),
    });

    const data = await response.json();
    console.log("🔄 OpenAI key storage response:", data);

    if (data?.status === "success") {
      return {
        success: true,
        message: data.message || "OpenAI key stored successfully",
      }
    } else {
      const errorMessage = data?.message || "Failed to store OpenAI API key"
      console.error("Failed to store OpenAI key:", data)
      return { success: false, message: errorMessage }
    }
  } catch (error: any) {
    console.error("Error during OpenAI key storage:", error)
    return {
      success: false,
      message: error?.message || "Failed to store OpenAI API key",
    }
  }
}



// MLLM code:
/**
 * Call the /extract_content endpoint
 * @param file - File to upload
 * @param week - Week parameter
 * @param days - Days parameter
 */
export const extractContent = async (file: File, week: number, days: string): Promise<any> => {
  const endpoint = "extract_content"

  const formData = new FormData()
  formData.append("file", file)
  formData.append("week", week.toString())
  formData.append("days", days)

  return await Service(endpoint, "POST", formData)
}

/**
 * Call the /generate_custom_scripts endpoint
 * @param file - File to upload
 * @param weeks - Weeks parameter
 * @param days - Days parameter
 * @param platformPosts - Object representing platform posts (e.g., { instagram: 1 })
 */
export const generateCustomScripts = async (
  file: File,
  weeks: number,
  days: string[],
  platformPosts: { [key: string]: number },
): Promise<any> => {
  const endpoint = "generate_custom_scripts_v2"
  const formData = new FormData()
  formData.append("file", file)

  const queryParams = {
    weeks: weeks.toString(),
    days: days.join(","),
    platform_posts: Object.entries(platformPosts)
      .map(([key, value]) => `${key}:${value}`)
      .join(","),
  }

  return await Service(endpoint, "POST", formData, queryParams)
}

// (async () => {
//   try {
//     const fileInput = document.createElement("input");
//     fileInput.type = "file";

//     fileInput.onchange = async (event: Event) => {
//       const file = (event.target as HTMLInputElement)?.files?.[0];
//       if (!file) {
//         console.error("No file selected!");
//         return;
//       }

//       const weeks = Number(prompt("Enter the number of weeks:", "1"));
//       const days = prompt("Enter the days (comma-separated):", "Monday,Tuesday")
//         ?.split(",")
//         .map((day) => day.trim()) || ["Monday"];
//       const platformPosts = prompt(
//         'Enter platform posts as JSON (e.g., {"instagram": 1}):',
//         '{"instagram": 1}'
//       );
//       const platformPostsObj = platformPosts ? JSON.parse(platformPosts) : {};

//       const extractedContent = await extractContent(file, weeks, days[0]);

//       const customScripts = await generateCustomScripts(
//         file,
//         weeks,
//         days,
//         platformPostsObj
//       );
//     };

//     fileInput.click();
//   } catch (error) {
//     console.error("Error during API calls:", error);
//   }
// })();

export const handleFileUpload = async () => {
  if (typeof document === "undefined") {
    console.warn("Cannot run file upload logic on the server.")
    return
  }

  try {
    const fileInput = document.createElement("input")
    fileInput.type = "file"

    fileInput.onchange = async (event: Event) => {
      const file = (event.target as HTMLInputElement)?.files?.[0]
      if (!file) {
        console.error("No file selected!")
        return
      }

      const weeks = Number(prompt("Enter the number of weeks:", "1"))
      const days = prompt("Enter the days (comma-separated):", "Monday,Tuesday")
        ?.split(",")
        .map((day) => day.trim()) || ["Monday"]
      const platformPosts = prompt('Enter platform posts as JSON (e.g., {"instagram": 1}):', '{"instagram": 1}')
      const platformPostsObj = platformPosts ? JSON.parse(platformPosts) : {}

      const extractedContent = await extractContent(file, weeks, days[0])
      const customScripts = await generateCustomScripts(file, weeks, days, platformPostsObj)
    }

    fileInput.click()
  } catch (error) {
    console.error("Error during API calls:", error)
  }
}


/**
 * Call the /regenerate_script_v1 endpoint
 * @param params - Object containing content, query, and platform
 */

export const regenerateScript = async ({
  subTopic,
  modifications,
  platform,
}: {
  subTopic: string
  modifications: string
  platform: string
}): Promise<any> => {
  try {
    const endpoint = "regenerate_script_v1"

    const timestamp = new Date().getTime().toString()
    const cleanedContent = decodeURIComponent(subTopic)

    const queryParams: Record<string, string> = {
      content: cleanedContent,
      query: modifications,
      platform,
      timestamp,
    }

    const response = await Service(endpoint, "PUT", {}, queryParams)

    if (response?.status === "success") {
      const decodedContent =
        typeof response.content === "object" ? response.content.content || "" : response.content || ""

      return { ...response, content: decodedContent }
    } else {
      console.error("Failed to regenerate script:", response?.message)
      return null
    }
  } catch (error) {
    console.error("Error during script regeneration:", error)
    return null
  }
}


/**
 * Call the /regenerate_content endpoint
 * @param week_content - The week_content to regenerate
 */
export const regenerateContent = async (content: string): Promise<any> => {
  try {
    const endpoint = "regenerate_content"

    const timestamp = new Date().getTime().toString()

    const cleanedContent = decodeURIComponent(content)

    const queryParams: Record<string, string> = {
      week_content: cleanedContent,
      timestamp,
    }

    const response = await Service(endpoint, "POST", {}, queryParams)

    if (response?.status === "success") {
      if (typeof response.week_content === "string") {
        const decodedContent = decodeURIComponent(response.week_content)
        return { ...response, week_content: decodedContent }
      }
    } else {
      console.error("Failed to regenerate script:", response?.message)
      return null
    }
  } catch (error) {
    console.error("Error during script regeneration:", error)
    return null
  }
}


/**
 * Call the /regenerate_subcontent endpoint
 * @param subcontent - The subcontent to regenerate
 */
export const regenerateSubContent = async (content: string): Promise<any> => {
  try {
    const endpoint = "regenerate_subcontent"

    const timestamp = new Date().getTime().toString()

    const cleanedContent = decodeURIComponent(content)

    const queryParams: Record<string, string> = {
      subcontent: cleanedContent,
      timestamp,
    }

    const response = await Service(endpoint, "POST", {}, queryParams)

    if (response?.status === "success") {
      if (typeof response.subcontent === "string") {
        const decodedContent = decodeURIComponent(response.subcontent)
        return { ...response, subcontent: decodedContent }
      }
    } else {
      console.error("Failed to regenerate script:", response?.message)
      return null
    }
  } catch (error) {
    console.error("Error during script regeneration:", error)
    return null
  }
}


/**
 * Call the /config/${agent_name}_agent endpoint
 * @param Role
 * @param goal
 * @param backstory
 */
export const plateformScriptAgent = async (agent_name: string): Promise<any> => {
  try {
    const endpoint = `config/${agent_name}_agent`
    const response = await Service(endpoint, "GET", {})

    return response.current
  } catch (error) {
    if (error instanceof Error) {
      console.error(`Error during script regeneration for ${agent_name}:`, error.message)
    } else {
      console.error(`Unknown error during script regeneration for ${agent_name}:`, error)
    }
    return null
  }
}


/**
 * Call the /config/${agent_name}_task endpoint
 * @param Role
 * @param goal
 * @param backstory
 */
export const plateformScriptTask = async (agent_name: string): Promise<any> => {
  try {
    const endpoint = `config/${agent_name}_task`
    const response = await Service(endpoint, "GET", {})

    return response.current
  } catch (error) {
    if (error instanceof Error) {
      console.error(`Error during script regeneration for ${agent_name}:`, error.message)
    } else {
      console.error(`Unknown error during script regeneration for ${agent_name}:`, error)
    }
    return null
  }
}


/**
 * Call the /regenrate_subcontent_task endpoint
 * @param params - Object containing agentName, description, and expectedOutput
 */

export const regenerateContentTask = async ({
  agentName,
  description,
  expectedOutput,
}: {
  agentName: string
  description: string
  expectedOutput: string
}): Promise<any> => {
  try {
    const endpoint = `tasks/${agentName}_task`

    const payload = {
      description,
      expected_output: expectedOutput,
    }

    const response = await Service(endpoint, "PUT", payload, {})

    if (response?.status === "success") {
      return response
    } else {
      console.error("Failed to regenerate subcontent:", response?.message)
      return null
    }
  } catch (error) {
    console.error("Error during subcontent regeneration:", error)
    return null
  }
}


/**
 * Call the /regenrate_subcontent_agent endpoint
 * @param params - Object containing agentName, role, goal, and backstory
 */

export const regenerateContentAgent = async ({
  agentName,
  role,
  goal,
  backstory,
}: {
  agentName: string
  role: string
  goal: string
  backstory: string
}): Promise<any> => {
  try {
    const endpoint = `agents/${agentName}_agent`

    const payload = {
      role,
      goal,
      backstory,
    }

    const response = await Service(endpoint, "PUT", payload, {})

    if (response?.status === "success") {
      return response
    } else {
      console.error("Failed to regenerate subcontent:", response?.message)
      return null
    }
  } catch (error) {
    console.error("Error during subcontent agent regeneration:", error)
    return null
  }
}


/**
 * Call the /generate_image endpoint
 * @param params - Object containing content, query, and platform
 */
export const generateImage = async ({
  subTopic,
  modifications,
}: {
  subTopic: string
  modifications: string
}): Promise<any> => {
  try {
    const endpoint = "generate_image"

    const timestamp = new Date().getTime().toString()
    const cleanedContent = decodeURIComponent(subTopic)

    const queryParams: Record<string, string> = {
      content: cleanedContent,
      query: modifications,
      timestamp,
    }

    const response = await Service(endpoint, "POST", {}, queryParams)

    if (response?.status === "success") {
      return response
    } else {
      console.error("Failed to generate image:", response?.message)
      return null
    }
  } catch (error) {
    console.error("Error during image generation:", error)
    return null
  }
}


/**
 * Call the /content/schedule-time endpoint
 * @param content - The text content to be scheduled
 * @param newTime - The new time for scheduling
 */
export const scheduleTime = async ({
  newTime,
  content,
}: {
  newTime: string
  content: string
}): Promise<any> => {
  try {
    const encodedContent = encodeURIComponent(content)

    const endpoint = `content/schedule-time?content=${encodedContent}`
    const body = {
      new_time: newTime,
    }

    const response = await Service(endpoint, "PATCH", body)
    return response
  } catch (error) {
    console.error("Error scheduling content:", error)
    return null
  }
}


/**
 * Call the /content/schedule-time endpoint
 * @param content - The text content to be scheduled
 * @param newTime - The new time for scheduling
 */
export const duplicateScheduleTime = async ({
  source_week,
  source_day,
  platform,
}: {
  source_week: number
  source_day: string
  platform: string
}): Promise<any> => {
  try {
    const endpoint = `duplicate-schedule-times`

    const body = {
      source_week,
      source_day,
      platform,
    }

    const response = await Service(endpoint, "POST", body)
    return response
  } catch (error) {
    console.error("Error scheduling content:", error)
    return null
  }
}


export const getAllCampaigns = async () => {
  try {
    console.log("🔍 getAllCampaigns: Starting to fetch campaigns...");
    // Use local API instead of external API
    const response = await fetch('/api/campaigns', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(typeof window !== 'undefined' && localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
      },
    });

    console.log("🔍 getAllCampaigns: Response status:", response.status);
    const data = await response.json();
    console.log("🔍 getAllCampaigns: Response data:", data);

    if (data?.status === "success") {
      console.log("🔍 getAllCampaigns: Success! Found", data.campaigns?.length || 0, "campaigns");
      return {
        status: "success",
        message: {
          campaigns: data.campaigns
        },
      }
    } else {
      console.error("Failed to fetch campaigns:", data?.message || data?.error)
      return {
        status: "error",
        message: data?.message || data?.error || "campaigns couldn't be fetched",
      }
    }
  } catch (error) {
    console.error("Error during fetch:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred during fetch.",
    }
  }
}



export const createCampaign = async (campaignData: any) => {
  try {
    // Use local API instead of external API
    const response = await fetch('/api/campaigns', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(typeof window !== 'undefined' && localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
      },
      body: JSON.stringify(campaignData),
    });

    const data = await response.json();

    if (data?.status === "success") {
      return {
        status: "success",
        message: data,
      }
    } else {
      console.error("Campaign creation failed:", data?.message || data?.error)
      return {
        status: "error",
        message: data?.message || data?.error || "Campaign couldn't be created",
      }
    }
  } catch (error) {
    console.error("Error creating campaign:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred during campaign creation.",
    }
  }
}



export const updateCampaign = async (campaignId: string, campaignData: any) => {
  try {
    // Use local API instead of external API
    const response = await fetch(`/api/campaigns/${campaignId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(typeof window !== 'undefined' && localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
      },
      body: JSON.stringify(campaignData),
    });

    const data = await response.json();

    if (data?.status === "success") {
      return {
        status: "success",
        message: data,
      }
    } else {
      console.error("Campaign update failed:", data?.message || data?.error)
      return {
        status: "error",
        message: data?.message || data?.error || "Campaign couldn't be updated",
      }
    }
  } catch (error) {
    console.error("Error updating campaign:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred during campaign update.",
    }
  }
}



export const getCampaignsById = async (campaign_id: string) => {
  try {
    // Use local API instead of external API
    const response = await fetch(`/api/campaigns/${campaign_id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(typeof window !== 'undefined' && localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
      },
    });

    const data = await response.json();

    if (data?.status === "success") {
      return {
        status: "success",
        message: data.message,
      }
    } else {
      console.error("Failed to get campaigns for edit:", data?.message || data?.error)
      return {
        status: "error",
        message: data?.message || data?.error || "Failed to get campaigns for edit.",
      }
    }
  } catch (error) {
    console.error("Failed to get campaigns for edit.", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred.",
    }
  }
}



/**
 * Call the /linkedin/auth endpoint
 * @param urls - List of LinkedIn URLs
 */
export const linkedinConnect = async (): Promise<any> => {
  try {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null

    if (!token) {
      console.error("No token found in localStorage.")
      return
    }

    const response = await Service("linkedin/auth-v2", "GET", {})

    if (response?.auth_url) {
      window.location.href = response.auth_url
    } else {
      console.error("No auth_url in response")
    }
  } catch (error) {
    console.error("Error during LinkedIn connection:", error)
  }
}


/**
 * Call the /twitter/auth endpoint
 * @param urls - List of LinkedIn URLs
 */
export const twitterConnect = async (): Promise<any> => {
  try {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null

    if (!token) {
      console.error("No token found in localStorage.")
      return
    }

    const response = await Service("twitter/auth-v2", "GET", {})
    console.log("Twitter auth response:", response)

    if (response?.redirect_url) {
      window.location.href = response.redirect_url
    } else {
      console.error("No redirect_url in response")
    }
  } catch (error) {
    console.error("Error during LinkedIn connection:", error)
  }
}


/**
 * Call the /wordpress/auth endpoint
 * @param site_url - WordPress site URL
 * @param username - WordPress username
 * @param password - WordPress password
 */

export const wordpressConnect = async (site_url: string, username: string, password: string): Promise<any> => {
  try {
    const token = typeof window !== 'undefined' ? localStorage.getItem("token") : null

    if (!token) {
      console.error("No token found in localStorage.")
      return
    }

    const formBody = new URLSearchParams()
    formBody.append("site_url", site_url)
    formBody.append("username", username)
    formBody.append("password", password)

    const response = await fetch(`${API_BASE_URL}/wordpress/auth-v2`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formBody,
    })

    const data = await response.json()

    if (response.ok) {
      console.log("WordPress connected successfully:", data)
    } else {
      console.error("Failed to connect to WordPress:", data)
    }

    return data
  } catch (error) {
    console.error("Error during WordPress connection:", error)
  }
}


/**
 * Input parameters for the analyzeTrends API
 */
export interface AnalyzeTrendsInput {
  campaign_name: string
  campaign_id: string
  urls: string[]
  query: string
  description: string
  keywords: string[]
  type?: "keyword" | "url" | "trending"
  depth: number
  max_pages: number
  batch_size: number
  include_links: boolean
  stem: boolean
  lemmatize: boolean
  remove_stopwords_toggle: boolean
  extract_persons: boolean
  extract_organizations: boolean
  extract_locations: boolean
  extract_dates: boolean
  topic_tool: string
  num_topics: number
  iterations: number
  pass_threshold: number
}

/**
 * Post structure in the response
 */
interface Post {
  url?: string
  title?: string
  text?: string
  lemmatized_text?: string | null
  stemmed_text?: string | null
  stopwords_removed_text?: string | null
  persons?: string[]
  organizations?: string[]
  locations?: string[]
  dates?: string[]
  topics?: string[]
  entities?: {
    persons?: string[]
    organizations?: string[]
    locations?: string[]
    dates?: string[]
  }
}


/**
 * Response structure for the analyzeTrends API
 */
export interface AnalyzeTrendsResponse {
  status: "success" | "error" | "started"
  task?: string
  task_id?: string
  campaign_name?: string
  campaign_id?: string
  keywords?: string[]
  posts?: Post[]
  topics?: string[]
  summary?: {
    total_urls_scraped: number
    total_content_size: string
    extraction_settings_used: {
      depth: number
      max_pages: number
      batch_size: number
      include_links: boolean
    }
  }
  persons?: string[]
  organizations?: string[]
  locations?: string[]
  dates?: string[]
  message?: string
}

/**
 * Call the /analyze endpoint
 * @param input - Analyze input data
 * @throws Error if validation fails
 */
export const analyzeTrends = async ({
  campaign_name,
  campaign_id,
  urls = [],
  query = "",
  description = "",
  keywords = [],
  type = "keyword",
  depth = 3,
  max_pages = 10,
  batch_size = 1,
  include_links = true,
  stem = false,
  lemmatize = false,
  remove_stopwords_toggle = false,
  extract_persons = false,
  extract_organizations = false,
  extract_locations = false,
  extract_dates = false,
  topic_tool = "lda",
  num_topics = 3,
  iterations = 25,
  pass_threshold = 0.7,
}: AnalyzeTrendsInput): Promise<AnalyzeTrendsResponse> => {
  try {
    const endpoint = "analyze"

    const payload: AnalyzeTrendsInput = {
      campaign_name,
      campaign_id,
      urls,
      query,
      description,
      keywords,
      type,
      depth,
      max_pages,
      batch_size,
      include_links,
      stem,
      lemmatize,
      remove_stopwords_toggle,
      extract_persons,
      extract_organizations,
      extract_locations,
      extract_dates,
      topic_tool,
      num_topics,
      iterations,
      pass_threshold,
    }

    console.log("API Payload:", JSON.stringify(payload, null, 2))
    const response = await Service(endpoint, "POST", payload, undefined, false)

    if (response?.status === "started") {
      return {
        status: "started",
        task_id: response.task_id,
        message: response.message,
      }
    } else {
      console.error("Analyze failed:", response?.message || response?.error)
      return {
        status: "error",
        message: response?.message || response?.error || "Unexpected analyze response",
      }
    }
  } catch (error) {
    console.error("Error during analyze:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred during analysis.",
    }
  }
}




export const getAnalysisStatus = async (taskId: string): Promise<any> => {
  try {
    const response = await fetch(`${API_BASE_URL}/analyze/status/${taskId}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return await response.json()
  } catch (error: any) {
    console.error("Error getting analysis status:", error)
    return {
      status: "error",
      message: error.message || "Failed to get analysis status",
    }
  }
}
