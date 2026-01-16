# QC Strictness Preset Info Modal - Frontend Implementation Spec

**Purpose:** Specification for adding info icon and modal to show QC strictness preset configurations.

**Location:** Admin Panel → QC Agents → Strictness Preset dropdown (info icon next to it)

---

## 📋 Requirements

### 1. Add Info Icon

Add an info icon next to the "Strictness Preset" label/select:

```tsx
<div className="flex items-center space-x-2">
  <Label htmlFor="strictness-preset">Strictness Preset</Label>
  <Info 
    className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-pointer"
    onClick={() => setIsPresetModalOpen(true)}
  />
</div>
```

**Placement:** Next to the "Strictness Preset" label, before the dropdown.

---

## 2. Modal Component

### Modal Structure
```tsx
<Dialog open={isPresetModalOpen} onOpenChange={setIsPresetModalOpen}>
  <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
    <DialogHeader>
      <DialogTitle className="flex items-center justify-between">
        <span>Strictness Presets</span>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsPresetModalOpen(false)}
          className="h-6 w-6"
        >
          <X className="h-4 w-4" />
        </Button>
      </DialogTitle>
      <DialogDescription>
        Configuration details for each strictness preset. These settings control how QC agents handle content violations.
      </DialogDescription>
    </DialogHeader>

    <div className="space-y-6 mt-4">
      {/* Balanced Preset */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            Balanced
            <Badge className="ml-2 bg-blue-500">DEFAULT</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-semibold mb-2">General Settings</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="font-medium">max_rejections:</span> 5</div>
              <div><span className="font-medium">warnings_break_loop:</span> true</div>
              <div><span className="font-medium">allow_speculative_medical_language:</span> true</div>
              <div><span className="font-medium">require_legal_risk_line_for_regulated_topics:</span> false</div>
            </div>
          </div>
          <div>
            <h4 className="font-semibold mb-2">Category Actions</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="font-medium">legal:</span> <Badge variant="outline">warn</Badge></div>
              <div><span className="font-medium">medical_claims:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">regulated_goods:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">illegal_activity:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">misinformation:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">hate_harassment:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">self_harm:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">privacy:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">deceptive_media:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">sexual_content:</span> <Badge variant="destructive">deny</Badge></div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Strict Preset */}
      <Card>
        <CardHeader>
          <CardTitle>Strict</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-semibold mb-2">General Settings</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="font-medium">max_rejections:</span> 5</div>
              <div><span className="font-medium">warnings_break_loop:</span> true</div>
              <div><span className="font-medium">allow_speculative_medical_language:</span> false</div>
              <div><span className="font-medium">require_legal_risk_line_for_regulated_topics:</span> true</div>
            </div>
          </div>
          <div>
            <h4 className="font-semibold mb-2">Category Actions</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="font-medium">legal:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">medical_claims:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">regulated_goods:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">illegal_activity:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">misinformation:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">hate_harassment:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">self_harm:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">privacy:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">deceptive_media:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">sexual_content:</span> <Badge variant="destructive">deny</Badge></div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Permissive Preset */}
      <Card>
        <CardHeader>
          <CardTitle>Permissive</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-semibold mb-2">General Settings</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="font-medium">max_rejections:</span> 3</div>
              <div><span className="font-medium">warnings_break_loop:</span> true</div>
              <div><span className="font-medium">allow_speculative_medical_language:</span> true</div>
              <div><span className="font-medium">require_legal_risk_line_for_regulated_topics:</span> false</div>
            </div>
          </div>
          <div>
            <h4 className="font-semibold mb-2">Category Actions</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="font-medium">legal:</span> <Badge variant="outline">warn</Badge></div>
              <div><span className="font-medium">medical_claims:</span> <Badge variant="outline">warn</Badge></div>
              <div><span className="font-medium">regulated_goods:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">illegal_activity:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">misinformation:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">hate_harassment:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">self_harm:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">privacy:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">deceptive_media:</span> <Badge variant="destructive">deny</Badge></div>
              <div><span className="font-medium">sexual_content:</span> <Badge variant="destructive">deny</Badge></div>
            </div>
          </div>
          <p className="text-xs text-gray-500 italic">
            Note: Permissive preset allows warnings for legal and medical_claims, but still denies all other categories.
          </p>
        </CardContent>
      </Card>
    </div>
  </DialogContent>
</Dialog>
```

---

## 3. Preset Data Structure

```tsx
const STRICTNESS_PRESETS = {
  balanced: {
    name: "Balanced",
    isDefault: true,
    general: {
      max_rejections: 5,
      warnings_break_loop: true,
      allow_speculative_medical_language: true,
      require_legal_risk_line_for_regulated_topics: false,
    },
    categoryActions: {
      legal: "warn",
      medical_claims: "deny",
      regulated_goods: "deny",
      illegal_activity: "deny",
      misinformation: "deny",
      hate_harassment: "deny",
      self_harm: "deny",
      privacy: "deny",
      deceptive_media: "deny",
      sexual_content: "deny",
    },
  },
  strict: {
    name: "Strict",
    isDefault: false,
    general: {
      max_rejections: 5,
      warnings_break_loop: true,
      allow_speculative_medical_language: false,
      require_legal_risk_line_for_regulated_topics: true,
    },
    categoryActions: {
      legal: "deny",
      medical_claims: "deny",
      regulated_goods: "deny",
      illegal_activity: "deny",
      misinformation: "deny",
      hate_harassment: "deny",
      self_harm: "deny",
      privacy: "deny",
      deceptive_media: "deny",
      sexual_content: "deny",
    },
  },
  permissive: {
    name: "Permissive",
    isDefault: false,
    general: {
      max_rejections: 3,
      warnings_break_loop: true,
      allow_speculative_medical_language: true,
      require_legal_risk_line_for_regulated_topics: false,
    },
    categoryActions: {
      legal: "warn",
      medical_claims: "warn",
      regulated_goods: "deny",
      illegal_activity: "deny",
      misinformation: "deny",
      hate_harassment: "deny",
      self_harm: "deny",
      privacy: "deny",
      deceptive_media: "deny",
      sexual_content: "deny",
    },
  },
};
```

---

## 4. Modal Behavior

### Opening
- Click info icon → Opens modal
- Modal shows all three presets with their configurations

### Closing
- Click X button in top right → Closes modal
- Click outside modal (backdrop) → Closes modal
- Press Escape key → Closes modal

### State Management
```tsx
const [isPresetModalOpen, setIsPresetModalOpen] = useState(false);
```

---

## 5. Required Imports

```tsx
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Info, X } from "lucide-react";
```

---

## 6. Styling

- Modal: Max width 4xl, scrollable if content is long
- Cards: One card per preset with clear separation
- Badges: 
  - `variant="destructive"` for "deny"
  - `variant="outline"` for "warn"
  - `bg-blue-500` for "DEFAULT" badge
- Grid layout: 2 columns for settings display
- Info icon: Gray, hover to darker gray, cursor pointer

---

## 7. Placement

The info icon should be placed:
- Next to the "Strictness Preset" label
- Before the dropdown/select component
- Same line as the label

Example:
```
Strictness Preset [ℹ️] [Dropdown ▼]
```

---

## 8. Accessibility

- Info icon should have `aria-label="Show strictness preset details"`
- Modal should have proper focus management
- Close button should be keyboard accessible

---

**Last Updated:** 2025-01-16  
**Status:** Ready for implementation

