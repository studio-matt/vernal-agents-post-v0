# Campaign Merge Functionality - Re-implementation Guide

## Overview
The campaign merge functionality has been temporarily disabled due to issues with the refresh mechanism. This document provides a complete guide for re-implementing the feature.

## What Was Disabled
The following UI elements and functionality have been commented out in `/components/ContentPlannerCampaign.tsx`:

1. **"Merge Research" button** - Button to enter merge mode
2. **Checkboxes in campaign cards** - For selecting campaigns to merge
3. **Merge mode conditional rendering** - UI changes when in merge mode
4. **Merge action buttons** - "Merge Selected Campaigns" and "Cancel Merge" buttons

## Files Modified
- `/components/ContentPlannerCampaign.tsx` - Main component with merge functionality
- `/app/api/campaigns/route.ts` - API endpoint for creating campaigns
- `/app/api/campaigns/[id]/route.ts` - API endpoint for individual campaigns
- `/lib/database.ts` - In-memory database service
- `/components/Service.tsx` - API service functions

## Re-implementation Steps

### Step 1: Uncomment UI Elements

In `/components/ContentPlannerCampaign.tsx`, uncomment the following sections:

#### 1.1 Merge Research Button
```tsx
// Line ~539-542: Uncomment the Merge Research button
<Button onClick={() => setIsMergeMode(true)} variant="outline">
  Merge Research
</Button>
```

#### 1.2 Checkboxes in Campaign Cards
```tsx
// Line ~805-816: Uncomment the checkbox rendering
{isMergeMode && (
  <div className="mr-3 mt-1">
    <input
      type="checkbox"
      id={`select-${campaign.id}`}
      checked={selectedCampaigns.includes(campaign.id)}
      onChange={() => handleCampaignSelection(campaign.id)}
      className="h-5 w-5 rounded border-gray-300 text-[#3d545f] focus:ring-[#3d545f]"
    />
  </div>
)}
```

#### 1.3 Merge Mode Conditional Rendering
```tsx
// Line ~928: Restore the merge mode condition
{!isCreating && !isMergeMode && (
  // ... existing content
)}
```

#### 1.4 Merge Action Buttons
```tsx
// Line ~950-963: Uncomment the merge action buttons
{isMergeMode && (
  <div className="flex justify-center mt-4">
    <Button
      onClick={handleMergeCampaigns}
      className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90 mr-2"
    >
      Merge Selected Campaigns
    </Button>
    <Button variant="outline" onClick={cancelMerge}>
      Cancel Merge
    </Button>
  </div>
)}
```

### Step 2: Verify State Management

Ensure these state variables are properly initialized:

```tsx
const [isMergeMode, setIsMergeMode] = useState(false);
const [selectedCampaigns, setSelectedCampaigns] = useState<string[]>([]);
const [isMergeModalOpen, setIsMergeModalOpen] = useState(false);
```

### Step 3: Verify Handler Functions

Ensure these handler functions are present and working:

```tsx
// Campaign selection handler
const handleCampaignSelection = (campaignId: string) => {
  setSelectedCampaigns(prev => 
    prev.includes(campaignId) 
      ? prev.filter(id => id !== campaignId)
      : [...prev, campaignId]
  );
};

// Cancel merge handler
const cancelMerge = () => {
  setIsMergeMode(false);
  setSelectedCampaigns([]);
};

// Merge campaigns handler
const handleMergeCampaigns = () => {
  if (selectedCampaigns.length >= 2) {
    setIsMergeModalOpen(true);
  }
};
```

### Step 4: Verify Merge Logic

The merge confirmation logic should be in the `confirmMergeCampaigns` function:

```tsx
const confirmMergeCampaigns = async () => {
  try {
    // Get selected campaign data
    const selectedCampaignData = settings.filter(campaign => 
      selectedCampaigns.includes(campaign.id)
    );

    // Create merged campaign object
    const mergedCampaign = {
      name: `Merged: ${selectedCampaignData.map(c => c.name).join(' + ')}`,
      description: `Merged campaign combining: ${selectedCampaignData.map(c => c.name).join(', ')}`,
      type: selectedCampaignData[0].type,
      keywords: selectedCampaignData.flatMap(c => c.keywords || []),
      urls: selectedCampaignData.flatMap(c => c.urls || []),
      trendingTopics: selectedCampaignData.flatMap(c => c.trendingTopics || []),
      topics: selectedCampaignData.flatMap(c => c.topics || []),
      extractionSettings: selectedCampaignData[0].extractionSettings,
      preprocessingSettings: selectedCampaignData[0].preprocessingSettings,
      entitySettings: selectedCampaignData[0].entitySettings,
      modelingSettings: selectedCampaignData[0].modelingSettings,
    };

    // Create campaign via API
    const response = await createCampaign(mergedCampaign);
    
    if (response.status === "success") {
      toast.success("Campaigns merged successfully!");
      
      // Refresh campaigns from API
      if (onRefreshCampaigns) {
        onRefreshCampaigns();
      }
    } else {
      toast.error("Failed to create merged campaign");
    }
    
    // Close modal and reset state
    setIsMergeModalOpen(false);
    setIsMergeMode(false);
    setSelectedCampaigns([]);
  } catch (error) {
    console.error("Error merging campaigns:", error);
    toast.error("An unexpected error occurred while merging campaigns");
  }
};
```

### Step 5: Verify API Endpoints

Ensure these API endpoints are working:

- `POST /api/campaigns` - Create new campaign
- `GET /api/campaigns` - Fetch all campaigns
- `GET /api/campaigns/[id]` - Get specific campaign

### Step 6: Test the Functionality

1. **Enter Merge Mode**: Click "Merge Research" button
2. **Select Campaigns**: Check boxes next to campaigns you want to merge
3. **Merge Campaigns**: Click "Merge Selected Campaigns" button
4. **Confirm Merge**: In the modal, click "Merge Campaigns"
5. **Verify Result**: Check that the merged campaign appears in the list
6. **Test Edit**: Click "Edit" on the merged campaign to ensure it's accessible

## Known Issues and Solutions

### Issue 1: Campaigns Not Refreshing After Merge
**Problem**: Merged campaigns don't appear in the list after creation
**Solution**: Ensure `onRefreshCampaigns` is properly passed as a prop and calls the API

### Issue 2: "Campaign Not Found" When Editing
**Problem**: Edit page can't find merged campaigns
**Solution**: Verify the campaign ID is properly generated and stored

### Issue 3: Merge Modal Not Closing
**Problem**: Modal stays open after successful merge
**Solution**: Ensure `setIsMergeModalOpen(false)` is called in the success handler

### Issue 4: Selected Campaigns Not Clearing
**Problem**: Checkboxes remain selected after merge
**Solution**: Ensure `setSelectedCampaigns([])` is called in the cleanup

## Debugging Tips

1. **Check Console Logs**: Look for error messages in browser console
2. **Verify API Calls**: Check Network tab for failed API requests
3. **Test API Endpoints**: Use curl to test endpoints directly
4. **Check State**: Use React DevTools to inspect component state
5. **Verify Props**: Ensure all required props are passed correctly

## Dependencies

The merge functionality depends on:

- `createCampaign` function in `/components/Service.tsx`
- `onRefreshCampaigns` prop from parent component
- `toast` notifications for user feedback
- Campaign data structure with proper fields

## Testing Checklist

- [ ] Merge Research button appears and works
- [ ] Checkboxes appear when in merge mode
- [ ] Can select multiple campaigns
- [ ] Merge button is disabled when < 2 campaigns selected
- [ ] Merge modal opens with correct campaign names
- [ ] Merge confirmation creates new campaign
- [ ] New campaign appears in list after merge
- [ ] Can edit the merged campaign
- [ ] Modal closes after successful merge
- [ ] Checkboxes clear after merge
- [ ] Exit merge mode works correctly

## Notes

- The merge functionality creates a new campaign with combined data from selected campaigns
- The merged campaign gets a unique ID and timestamp
- Original campaigns are not deleted, only a new merged campaign is created
- The merge combines keywords, URLs, trending topics, and other settings
- The merged campaign name follows the pattern: "Merged: Campaign1 + Campaign2"
