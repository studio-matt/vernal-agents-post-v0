# Maintenance + Diagnostics - Frontend Implementation Spec

**Purpose:** Specification for adding "Maintenance + Diagnostics" section to admin panel System tab.

**Location:** Admin Panel → System → Maintenance + Diagnostics (new left nav item)

---

## 📋 Requirements

### 1. Add Left Navigation Item

Add a new item to the System tab left navigation sidebar:

```tsx
<button
  onClick={() => setSelectedItem("maintenance-diagnostics")}
  className={`w-full text-left px-4 py-2 rounded-md transition-colors ${
    selectedItem === "maintenance-diagnostics"
      ? "bg-[#3d545f] text-white"
      : "bg-gray-100 hover:bg-gray-200 text-gray-700"
  }`}
>
  Maintenance + Diagnostics
</button>
```

**Placement:** After "Guard Rails" in the left nav list.

---

## 2. Main Content Section

### Section Header
```tsx
<div className="mb-6">
  <h1 className="text-3xl font-bold mb-2">Maintenance + Diagnostics</h1>
  <p className="text-gray-600">
    Comprehensive diagnostic system to quickly identify and resolve system issues.
    Includes 15-step diagnostic checklist, automated scripts, and direct links to all documentation.
  </p>
</div>
```

### Quick Actions Section
```tsx
<div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
  <Card>
    <CardHeader>
      <CardTitle className="flex items-center">
        <Play className="w-5 h-5 mr-2" />
        Run Full Diagnostic
      </CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-sm text-gray-600 mb-4">
        Run automated script that checks all 15 diagnostic steps (takes 2-5 minutes)
      </p>
      <Button 
        onClick={handleRunFullDiagnostic}
        disabled={isRunningDiagnostic}
        className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
      >
        {isRunningDiagnostic ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Running...
          </>
        ) : (
          "Run Full Diagnostic"
        )}
      </Button>
    </CardContent>
  </Card>

  <Card>
    <CardHeader>
      <CardTitle className="flex items-center">
        <AlertCircle className="w-5 h-5 mr-2" />
        Diagnose CORS
      </CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-sm text-gray-600 mb-4">
        Comprehensive CORS diagnostic and fix tool
      </p>
      <Button 
        onClick={() => window.open('/docs/guardrails/CORS_EMERGENCY_NET.md', '_blank')}
        variant="outline"
        className="w-full"
      >
        Open CORS Guide
      </Button>
    </CardContent>
  </Card>

  <Card>
    <CardHeader>
      <CardTitle className="flex items-center">
        <FileCode className="w-5 h-5 mr-2" />
        Check Syntax
      </CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-sm text-gray-600 mb-4">
        Find and fix syntax errors that prevent service startup
      </p>
      <Button 
        onClick={() => window.open('/docs/guardrails/SYNTAX_CHECKING.md', '_blank')}
        variant="outline"
        className="w-full"
      >
        Open Syntax Guide
      </Button>
    </CardContent>
  </Card>
</div>
```

### Diagnostic Phases Section
```tsx
<div className="space-y-6">
  <h2 className="text-2xl font-bold">15-Step Diagnostic Checklist</h2>
  
  {/* Phase 1: Service Health */}
  <Card>
    <CardHeader>
      <CardTitle>Phase 1: Service Health (CRITICAL - Start Here)</CardTitle>
      <CardDescription>Most issues are caused by service not running</CardDescription>
    </CardHeader>
    <CardContent className="space-y-2">
      <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
        <div>
          <p className="font-medium">Step 1: Is the Service Running?</p>
          <p className="text-sm text-gray-600">Check systemctl status</p>
        </div>
        <Button variant="outline" size="sm">
          View Guide
        </Button>
      </div>
      <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
        <div>
          <p className="font-medium">Step 2: Is Port 8000 Listening?</p>
          <p className="text-sm text-gray-600">Check port binding</p>
        </div>
        <Button variant="outline" size="sm">
          View Guide
        </Button>
      </div>
      <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
        <div>
          <p className="font-medium">Step 3: Can We Reach FastAPI Directly?</p>
          <p className="text-sm text-gray-600">Test health endpoint</p>
        </div>
        <Button variant="outline" size="sm">
          View Guide
        </Button>
      </div>
    </CardContent>
  </Card>

  {/* Phase 2: CORS Configuration */}
  <Card>
    <CardHeader>
      <CardTitle>Phase 2: CORS Configuration</CardTitle>
      <CardDescription>Frontend connectivity issues</CardDescription>
    </CardHeader>
    <CardContent>
      <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
        <div>
          <p className="font-medium">Step 4: CORS Diagnostic</p>
          <p className="text-sm text-gray-600">Check CORS headers and configuration</p>
        </div>
        <Button variant="outline" size="sm">
          View Guide
        </Button>
      </div>
    </CardContent>
  </Card>

  {/* Continue for all 7 phases... */}
</div>
```

### Documentation Links Section
```tsx
<div className="mt-8">
  <h2 className="text-2xl font-bold mb-4">Documentation Reference</h2>
  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    <Card>
      <CardHeader>
        <CardTitle>Emergency Procedures</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <Button variant="link" className="justify-start p-0 h-auto">
          Backend Emergency Net
        </Button>
        <Button variant="link" className="justify-start p-0 h-auto">
          CORS Emergency Net
        </Button>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle>Guardrails</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <Button variant="link" className="justify-start p-0 h-auto">
          CORS Quick Reference
        </Button>
        <Button variant="link" className="justify-start p-0 h-auto">
          Syntax Checking
        </Button>
        <Button variant="link" className="justify-start p-0 h-auto">
          Refactoring Guide
        </Button>
      </CardContent>
    </Card>
  </div>
</div>
```

---

## 3. Implementation Details

### State Management
```tsx
const [isRunningDiagnostic, setIsRunningDiagnostic] = useState(false);
const [diagnosticResults, setDiagnosticResults] = useState(null);
```

### Run Full Diagnostic Handler
```tsx
const handleRunFullDiagnostic = async () => {
  setIsRunningDiagnostic(true);
  try {
    // Call backend endpoint to run diagnostic script
    // Or show instructions to run: bash docs/run_full_diagnostic.sh
    // For now, show modal with instructions
    alert(`
      To run full diagnostic:
      1. SSH into server
      2. cd /home/ubuntu/vernal-agents-post-v0
      3. bash docs/run_full_diagnostic.sh
      
      Or view the guide: docs/MASTER_DIAGNOSTIC_ROUTER.md
    `);
  } finally {
    setIsRunningDiagnostic(false);
  }
};
```

### Links to Documentation
All documentation links should open in new tabs and point to:
- `/docs/MASTER_DIAGNOSTIC_ROUTER.md` - Main diagnostic guide
- `/docs/MAINTENANCE_DIAGNOSTICS_ADMIN_GUIDE.md` - This admin guide
- `/docs/guardrails/CORS_EMERGENCY_NET.md` - CORS fixes
- `/docs/guardrails/SYNTAX_CHECKING.md` - Syntax checking
- `/docs/guardrails/REFACTORING.md` - Refactoring guide

---

## 4. Required Imports

```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, Play, AlertCircle, FileCode } from "lucide-react";
```

---

## 5. Content Source

The main content should be based on:
- `docs/MAINTENANCE_DIAGNOSTICS_ADMIN_GUIDE.md` - User-friendly guide
- `docs/MASTER_DIAGNOSTIC_ROUTER.md` - Complete diagnostic checklist

---

## 6. Styling

- Use existing admin panel styling (matches Guard Rails section)
- Color scheme: `#3d545f` for primary actions
- Cards for each phase/section
- Responsive grid layout for quick actions

---

**Last Updated:** 2025-01-16  
**Status:** Ready for implementation

