# Frontend Loading Indicator for Code Health Scan

## Problem
The code health scan can take 30-120 seconds, but there's no visual feedback to the user that a scan is in progress. Users may think the scan isn't working or may refresh the page multiple times.

## Solution
Add a loading state to the Guard Rails component that shows:
1. A loading spinner/animation while the scan is running
2. Disable the "Run Scan" button during scan
3. Show a status message like "Scanning codebase... (this may take 1-2 minutes)"

## Implementation Location
The frontend component is likely in:
- `app/admin/page.tsx` (Guard Rails section)
- Or a separate component file for Guard Rails

## Implementation Steps

### 1. Add Loading State
```typescript
const [isScanning, setIsScanning] = useState(false);
const [scanProgress, setScanProgress] = useState<string>("");
```

### 2. Update Scan Handler
```typescript
const handleRunScan = async () => {
  setIsScanning(true);
  setScanProgress("Starting scan...");
  
  try {
    const response = await triggerCodeHealthScan();
    // Scan completed
    setScanProgress("");
    // Refresh data
    await fetchCodeHealth();
  } catch (error) {
    console.error("Scan failed:", error);
    setScanProgress("Scan failed. Please try again.");
  } finally {
    setIsScanning(false);
  }
};
```

### 3. Update UI
```tsx
<Button
  onClick={handleRunScan}
  disabled={isScanning}
  className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
>
  {isScanning ? (
    <>
      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
      Scanning...
    </>
  ) : (
    "Run Scan"
  )}
</Button>

{isScanning && (
  <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
    <div className="flex items-center">
      <Loader2 className="w-5 h-5 mr-3 animate-spin text-blue-600" />
      <div>
        <p className="font-medium text-blue-900">Scan in progress...</p>
        <p className="text-sm text-blue-700">
          {scanProgress || "Scanning codebase. This may take 1-2 minutes."}
        </p>
      </div>
    </div>
  </div>
)}
```

### 4. Optional: Progress Updates
If you want more detailed progress, you could:
- Poll the backend for scan status (requires backend changes)
- Show estimated time remaining
- Show files scanned count

## Example from Codebase
See `components/CampaignResults.tsx` lines 177-181 for a similar loading pattern:
```tsx
{isProcessing ? (
  <>
    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
    Processing...
  </>
) : (
  <>
    <Play className="w-4 h-4 mr-2" />
    Run Analysis
  </>
)}
```

## Required Imports
```typescript
import { Loader2 } from "lucide-react"; // or your icon library
```

## Notes
- The scan timeout is already set to 120 seconds in the frontend
- The backend doesn't currently support progress updates (would require streaming or polling)
- A simple loading state is sufficient for now

