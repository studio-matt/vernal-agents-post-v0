// Simple in-memory database for development
// In production, replace this with your actual database (PostgreSQL, MongoDB, etc.)

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
  status?: "INCOMPLETE" | "READY_TO_ACTIVATE" | "ACTIVE";
}

class Database {
  private campaigns: Campaign[] = [];
  private initialized = false;

  async initialize() {
    if (this.initialized) return;
    
    // First try to load from localStorage (for locally created campaigns)
    if (typeof window !== 'undefined') {
      try {
        const localCampaigns = localStorage.getItem('localCampaigns');
        if (localCampaigns) {
          this.campaigns = JSON.parse(localCampaigns);
          console.log(`Loaded ${this.campaigns.length} campaigns from localStorage`);
        }
      } catch (error) {
        console.error('Error loading campaigns from localStorage:', error);
      }
    }
    
    // Then load existing campaigns from external API directly
    try {
      const response = await fetch('https://themachine.vernalcontentum.com/campaigns', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',
          ...(typeof window !== 'undefined' && localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
        },
      });
      
      const data = await response.json();
      if (data.status === 'success') {
        const externalCampaigns = data.campaigns || [];
        
        // Filter out old test campaigns that should not be shown
        const oldCampaignIds = ['435r90vfcv', 'campaign-1758732158002', 'campaign-1758806475277'];
        const filteredExternalCampaigns = externalCampaigns.filter((c: Campaign) => !oldCampaignIds.includes(c.id));
        
        // Merge external campaigns with local campaigns, avoiding duplicates
        const externalCampaignIds = new Set(filteredExternalCampaigns.map((c: Campaign) => c.id));
        const localOnlyCampaigns = this.campaigns.filter(c => !externalCampaignIds.has(c.id));
        
        this.campaigns = [...filteredExternalCampaigns, ...localOnlyCampaigns];
        console.log(`Loaded ${filteredExternalCampaigns.length} campaigns from external API (filtered), ${localOnlyCampaigns.length} from localStorage`);
      }
    } catch (error) {
      console.error('Error loading campaigns from external API:', error);
    }
    
    this.initialized = true;
  }

  async getAllCampaigns(): Promise<Campaign[]> {
    await this.initialize();
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
    
    // Persist to localStorage as backup
    if (typeof window !== 'undefined') {
      localStorage.setItem('localCampaigns', JSON.stringify(this.campaigns));
    }
    
    return newCampaign;
  }

  async updateCampaign(id: string, updateData: Partial<Campaign>): Promise<Campaign | null> {
    await this.initialize();
    
    const index = this.campaigns.findIndex(c => c.id === id);
    if (index === -1) return null;

    this.campaigns[index] = {
      ...this.campaigns[index],
      ...updateData,
      updatedAt: new Date().toISOString(),
    };

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
  }
}

export const db = new Database();
export type { Campaign };
