import { Service } from "./Service"

// Author Personality API functions with local storage fallback
export const getAllAuthorPersonalities = async () => {
  try {
    const endpoint = "author_personalities"

    const response = await Service(endpoint, "GET", undefined, undefined, false)

    console.log("getAllAuthorPersonalities", response)

    if (response?.status === "success") {
      return {
        status: "success",
        message: response,
      }
    } else {
      console.error("Failed to fetch author personalities:", response?.message || response?.error)
      // Fallback to local storage
      return getLocalAuthorPersonalities()
    }
  } catch (error) {
    console.error("Error during fetch author personalities:", error)
    // Fallback to local storage
    return getLocalAuthorPersonalities()
  }
}

// Local storage fallback functions
const getLocalAuthorPersonalities = () => {
  try {
    const stored = localStorage.getItem("author_personalities")
    const personalities = stored ? JSON.parse(stored) : []
    return {
      status: "success",
      message: { personalities }
    }
  } catch (error) {
    console.error("Error reading from local storage:", error)
    return {
      status: "error",
      message: "Failed to load author personalities from local storage"
    }
  }
}

const saveLocalAuthorPersonalities = (personalities: any[]) => {
  try {
    localStorage.setItem("author_personalities", JSON.stringify(personalities))
    return true
  } catch (error) {
    console.error("Error saving to local storage:", error)
    return false
  }
}

export const createAuthorPersonality = async (personalityData: {
  name: string
  description: string
}) => {
  try {
    const endpoint = "author_personalities"

    const response = await Service(endpoint, "POST", personalityData, undefined, false)

    console.log("createAuthorPersonality", response)

    if (response?.status === "success") {
      return {
        status: "success",
        message: response,
      }
    } else {
      console.error("Failed to create author personality:", response?.message || response?.error)
      // Fallback to local storage
      return createLocalAuthorPersonality(personalityData)
    }
  } catch (error) {
    console.error("Error during create author personality:", error)
    // Fallback to local storage
    return createLocalAuthorPersonality(personalityData)
  }
}

const createLocalAuthorPersonality = (personalityData: { name: string; description: string }) => {
  try {
    const stored = localStorage.getItem("author_personalities")
    const personalities = stored ? JSON.parse(stored) : []
    
    const newPersonality = {
      id: `personality-${Date.now()}`,
      name: personalityData.name,
      description: personalityData.description,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    
    personalities.push(newPersonality)
    
    if (saveLocalAuthorPersonalities(personalities)) {
      return {
        status: "success",
        message: { personality: newPersonality }
      }
    } else {
      return {
        status: "error",
        message: "Failed to save to local storage"
      }
    }
  } catch (error) {
    console.error("Error creating local author personality:", error)
    return {
      status: "error",
      message: "Failed to create author personality in local storage"
    }
  }
}

export const updateAuthorPersonality = async (id: string, personalityData: {
  name: string
  description: string
}) => {
  try {
    const endpoint = `author_personalities/${id}`

    const response = await Service(endpoint, "PUT", personalityData, undefined, false)

    console.log("updateAuthorPersonality", response)

    if (response?.status === "success") {
      return {
        status: "success",
        message: response,
      }
    } else {
      console.error("Failed to update author personality:", response?.message || response?.error)
      return {
        status: "error",
        message: response?.message || response?.error || "Failed to update author personality",
      }
    }
  } catch (error) {
    console.error("Error during update author personality:", error)
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unexpected error occurred while updating author personality.",
    }
  }
}

export const deleteAuthorPersonality = async (id: string) => {
  try {
    const endpoint = `author_personalities/${id}`

    const response = await Service(endpoint, "DELETE", undefined, undefined, false)

    console.log("deleteAuthorPersonality", response)

    if (response?.status === "success") {
      return {
        status: "success",
        message: response,
      }
    } else {
      console.error("Failed to delete author personality:", response?.message || response?.error)
      // Fallback to local storage
      return deleteLocalAuthorPersonality(id)
    }
  } catch (error) {
    console.error("Error during delete author personality:", error)
    // Fallback to local storage
    return deleteLocalAuthorPersonality(id)
  }
}

const deleteLocalAuthorPersonality = (id: string) => {
  try {
    const stored = localStorage.getItem("author_personalities")
    const personalities = stored ? JSON.parse(stored) : []
    
    const filteredPersonalities = personalities.filter((p: any) => p.id !== id)
    
    if (saveLocalAuthorPersonalities(filteredPersonalities)) {
      return {
        status: "success",
        message: { id }
      }
    } else {
      return {
        status: "error",
        message: "Failed to delete from local storage"
      }
    }
  } catch (error) {
    console.error("Error deleting local author personality:", error)
    return {
      status: "error",
      message: "Failed to delete author personality from local storage"
    }
  }
}
