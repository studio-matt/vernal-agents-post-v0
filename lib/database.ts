// Simple in-memory database for development
// In production, replace this with your actual database (PostgreSQL, MongoDB, etc.)
import fs from 'fs';
import path from 'path';

interface Campaign {
  id: string;
  name: string;
  description: string;
  query?: string;
  type: 'keyword' | 'url' | 'trending';
  keywords?: string[];
  urls?: string[];
  trendingTopics?: string[];
  topics?: string[];
  extractionSettings?: any;
  preprocessingSettings?: any;
  entitySettings?: any;
  modelingSettings?: any;
  createdAt: string;
  updatedAt: string;
  status?: "INCOMPLETE" | "PROCESSING" | "READY_TO_ACTIVATE" | "ACTIVE";
  taskId?: string;
}

interface UserCredentials {
  openai_key?: string;
  claude_key?: string;
}

class Database {
  private campaigns: Campaign[] = [];
  private credentials: UserCredentials = {};
  private initialized = false;
  private hasLoadedFromExternal = false;
  private static instance: Database;
  private credentialsFile = path.join(process.cwd(), 'data', 'credentials.json');
  private campaignsFile = path.join(process.cwd(), 'data', 'campaigns.json');
  private externalLoadedFlagFile = path.join(process.cwd(), 'data', 'external_loaded.flag');

  static getInstance(): Database {
    if (!Database.instance) {
      console.log("🔍 Database: Creating new instance");
      Database.instance = new Database();
    } else {
      console.log("🔍 Database: Using existing instance");
    }
    return Database.instance;
  }

  async initialize() {
    if (this.initialized) {
      console.log("🔍 Database: Already initialized, skipping");
      return;
    }
    console.log("🔍 Database: Initializing...");
    
    // First load campaigns from file (server-side persistence)
    this.campaigns = this.loadCampaignsFromFile();
    console.log(`🔍 Database: Loaded ${this.campaigns.length} campaigns from file`);
    
    // If we have campaigns from file, mark as loaded from external to prevent re-fetching
    if (this.campaigns.length > 0) {
      this.hasLoadedFromExternal = true;
      console.log("🔍 Database: Marked as loaded from external due to file campaigns");
    }
    
    // Then try to load from localStorage (for locally created campaigns)
    if (typeof window !== 'undefined') {
      try {
        const localCampaigns = localStorage.getItem('localCampaigns');
        if (localCampaigns) {
          const localCampaignsArray = JSON.parse(localCampaigns);
          // Merge with file-based campaigns, avoiding duplicates
          // File data takes priority over localStorage data
          const fileIds = new Set(this.campaigns.map(c => c.id));
          const newLocalCampaigns = localCampaignsArray.filter((c: Campaign) => !fileIds.has(c.id));
          this.campaigns = [...this.campaigns, ...newLocalCampaigns];
          console.log(`Merged ${newLocalCampaigns.length} campaigns from localStorage (file data takes priority)`);
        }
        
        // Load credentials from localStorage
        const localCredentials = localStorage.getItem('userCredentials');
        if (localCredentials) {
          this.credentials = JSON.parse(localCredentials);
          console.log(`Loaded credentials from localStorage:`, this.credentials);
        }
      } catch (error) {
        console.error('Error loading data from localStorage:', error);
      }
    }
    
    // Only load from external API if we don't have any campaigns from file/localStorage
    // AND we haven't loaded from external API before (to prevent restoring deleted campaigns)
    console.log(`🔍 Database: Checking external API - campaigns.length: ${this.campaigns.length}, hasExternalBeenLoaded: ${this.hasExternalBeenLoaded()}`);
    if (this.campaigns.length === 0 && !this.hasExternalBeenLoaded()) {
      console.log("🔍 Database: No campaigns from file, loading from external API");
      try {
        const response = await fetch('https://themachine.vernalcontentum.com/campaigns', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            ...(typeof window !== 'undefined' && localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
          },
        });
        
        const data = await response.json();
        if (data.status === 'success') {
          const externalCampaigns = data.campaigns || [];
          
          // Filter out old test campaigns that should not be shown
          const oldCampaignIds = ['435r90vfcv', 'campaign-1758732158002', 'campaign-1758806475277'];
          const filteredExternalCampaigns = externalCampaigns.filter((c: Campaign) => !oldCampaignIds.includes(c.id));
          
          this.campaigns = filteredExternalCampaigns;
          this.hasLoadedFromExternal = true;
          console.log(`Loaded ${filteredExternalCampaigns.length} campaigns from external API (fallback)`);
          
          // Save external campaigns to file for future use
          this.saveCampaignsToFile();
          // Set flag to prevent future external API calls
          this.setExternalLoadedFlag();
        }
      } catch (error) {
        console.error('Error loading campaigns from external API:', error);
      }
    } else if (this.campaigns.length === 0) {
      console.log("🔍 Database: No campaigns from file, but already loaded from external API - keeping empty");
    } else {
      console.log(`Using ${this.campaigns.length} campaigns from file/localStorage`);
    }
    
    this.initialized = true;
  }

  async getAllCampaigns(): Promise<Campaign[]> {
    await this.initialize();
    console.log(`🔍 Database: getAllCampaigns returning ${this.campaigns.length} campaigns`);
    return [...this.campaigns];
  }

  async getCampaignById(id: string): Promise<Campaign | null> {
    await this.initialize();
    return this.campaigns.find(c => c.id === id) || null;
  }

  async createCampaign(campaignData: Omit<Campaign, 'id' | 'createdAt' | 'updatedAt'>): Promise<Campaign> {
    await this.initialize();
    
    const newCampaign: Campaign = {
      ...campaignData,
      id: `campaign-${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    this.campaigns.push(newCampaign);
    
    // Save to file for persistence
    this.saveCampaignsToFile();
    
    // Persist to localStorage as backup
    if (typeof window !== 'undefined') {
      localStorage.setItem('localCampaigns', JSON.stringify(this.campaigns));
    }
    
    return newCampaign;
  }

  async updateCampaign(id: string, updateData: Partial<Campaign>): Promise<Campaign | null> {
    await this.initialize();
    
    console.log(`🔄 Database: Updating campaign ${id} with data:`, updateData);
    
    const index = this.campaigns.findIndex(c => c.id === id);
    if (index === -1) {
      console.error(`❌ Database: Campaign ${id} not found`);
      return null;
    }

    console.log(`✅ Database: Found campaign at index ${index}, updating...`);
    
    this.campaigns[index] = {
      ...this.campaigns[index],
      ...updateData,
      updatedAt: new Date().toISOString(),
    };

    console.log(`✅ Database: Campaign updated, new data:`, this.campaigns[index]);

    // Save to file for persistence
    this.saveCampaignsToFile();

    // Persist to localStorage as backup
    if (typeof window !== 'undefined') {
      localStorage.setItem('localCampaigns', JSON.stringify(this.campaigns));
    }

    return this.campaigns[index];
  }

  async deleteCampaign(id: string): Promise<boolean> {
    await this.initialize();
    
    const index = this.campaigns.findIndex(c => c.id === id);
    if (index === -1) return false;

    this.campaigns.splice(index, 1);
    
    // Save to file for persistence
    this.saveCampaignsToFile();
    
    // Persist to localStorage as backup
    if (typeof window !== 'undefined') {
      localStorage.setItem('localCampaigns', JSON.stringify(this.campaigns));
    }
    
    return true;
  }

  // Method to sync with external API (for production)
  async syncWithExternalAPI() {
    try {
      const { Service } = await import('@/components/Service');
      const response = await Service('campaigns', 'GET');
      if (response.status === 'success') {
        this.campaigns = response.campaigns || [];
        console.log(`Synced ${this.campaigns.length} campaigns with external API`);
      }
    } catch (error) {
      console.error('Error syncing with external API:', error);
    }
    
    this.initialized = true;
    console.log("🔍 Database: Initialization complete");
  }

  // Check if external API has been loaded before
  private hasExternalBeenLoaded(): boolean {
    try {
      return fs.existsSync(this.externalLoadedFlagFile);
    } catch (error) {
      console.error("Error checking external loaded flag:", error);
      return false;
    }
  }

  // Set external loaded flag
  private setExternalLoadedFlag(): void {
    try {
      // Ensure data directory exists
      const dataDir = path.dirname(this.externalLoadedFlagFile);
      if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
      }
      
      fs.writeFileSync(this.externalLoadedFlagFile, 'true');
      console.log("🔍 Database: Set external loaded flag");
    } catch (error) {
      console.error("Error setting external loaded flag:", error);
    }
  }

  // Load campaigns from file
  private loadCampaignsFromFile(): Campaign[] {
    try {
      console.log("🔍 Database: Looking for campaigns file at:", this.campaignsFile);
      if (fs.existsSync(this.campaignsFile)) {
        const data = fs.readFileSync(this.campaignsFile, 'utf8');
        const campaigns = JSON.parse(data);
        console.log("🔍 Database: Loaded campaigns from file:", campaigns.length);
        return campaigns;
      } else {
        console.log("🔍 Database: Campaigns file does not exist at:", this.campaignsFile);
      }
    } catch (error) {
      console.error("Error loading campaigns from file:", error);
    }
    return [];
  }

  // Save campaigns to file
  private saveCampaignsToFile(): void {
    try {
      // Ensure data directory exists
      const dataDir = path.dirname(this.campaignsFile);
      if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
      }
      
      fs.writeFileSync(this.campaignsFile, JSON.stringify(this.campaigns, null, 2));
      console.log("🔍 Database: Saved campaigns to file:", this.campaigns.length);
    } catch (error) {
      console.error("Error saving campaigns to file:", error);
    }
  }

  // Load credentials from file
  private loadCredentialsFromFile(): UserCredentials {
    try {
      if (fs.existsSync(this.credentialsFile)) {
        const data = fs.readFileSync(this.credentialsFile, 'utf8');
        const credentials = JSON.parse(data);
        console.log("🔍 Database: Loaded credentials from file:", credentials);
        return credentials;
      }
    } catch (error) {
      console.error("Error loading credentials from file:", error);
    }
    return {};
  }

  // Save credentials to file
  private saveCredentialsToFile(credentials: UserCredentials): void {
    try {
      // Ensure data directory exists
      const dataDir = path.dirname(this.credentialsFile);
      if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
      }
      
      fs.writeFileSync(this.credentialsFile, JSON.stringify(credentials, null, 2));
      console.log("🔍 Database: Saved credentials to file:", credentials);
    } catch (error) {
      console.error("Error saving credentials to file:", error);
    }
  }

  // User credentials methods
  async getUserCredentials(): Promise<UserCredentials> {
    await this.initialize();
    
    // Load from file if not already loaded
    if (Object.keys(this.credentials).length === 0) {
      this.credentials = this.loadCredentialsFromFile();
    }
    
    console.log("🔍 Database: Current credentials:", this.credentials);
    return this.credentials;
  }

  async storeUserCredentials(credentials: Partial<UserCredentials>): Promise<UserCredentials> {
    await this.initialize();
    
    console.log("🔍 Database: Storing credentials:", credentials);
    console.log("🔍 Database: Previous credentials:", this.credentials);
    
    this.credentials = {
      ...this.credentials,
      ...credentials
    };
    
    console.log("🔍 Database: Updated credentials:", this.credentials);
    
    // Save to file for persistence
    this.saveCredentialsToFile(this.credentials);
    
    // Persist to localStorage as backup (client-side only)
    if (typeof window !== 'undefined') {
      localStorage.setItem('userCredentials', JSON.stringify(this.credentials));
      console.log("🔍 Database: Stored in localStorage");
    }
    
    return this.credentials;
  }
}

export const db = Database.getInstance();
export type { Campaign, UserCredentials };
