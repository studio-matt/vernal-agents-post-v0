"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { User, Building, MapPin, Calendar, Check, PlusCircle } from "lucide-react"

// Sample entity data
const SAMPLE_ENTITIES = {
  persons: [
    { id: "p1", name: "John Smith", frequency: 12 },
    { id: "p2", name: "Sarah Johnson", frequency: 8 },
    { id: "p3", name: "Michael Brown", frequency: 5 },
    { id: "p4", name: "Emily Davis", frequency: 3 },
  ],
  organizations: [
    { id: "o1", name: "Acme Corporation", frequency: 15 },
    { id: "o2", name: "TechCorp", frequency: 9 },
    { id: "o3", name: "Global Industries", frequency: 7 },
    { id: "o4", name: "Innovative Solutions", frequency: 4 },
  ],
  locations: [
    { id: "l1", name: "San Francisco", frequency: 10 },
    { id: "l2", name: "New York", frequency: 8 },
    { id: "l3", name: "London", frequency: 6 },
    { id: "l4", name: "Tokyo", frequency: 3 },
  ],
  dates: [
    { id: "d1", name: "January 2025", frequency: 7 },
    { id: "d2", name: "Q2 2025", frequency: 5 },
    { id: "d3", name: "March 15, 2025", frequency: 3 },
    { id: "d4", name: "Holiday Season 2025", frequency: 2 },
  ],
}

export function EntityRecognitionResults() {
  const [activeTab, setActiveTab] = useState<"persons" | "organizations" | "locations" | "dates">("persons")
  const [selectedEntities, setSelectedEntities] = useState<Record<string, boolean>>({})
  const [addSuccess, setAddSuccess] = useState(false)

  // Handle selecting/deselecting entities
  const handleSelectEntity = (id: string, checked: boolean) => {
    setSelectedEntities((prev) => ({
      ...prev,
      [id]: checked,
    }))
  }

  // Handle selecting all entities in the current tab
  const handleSelectAll = (checked: boolean) => {
    const newSelected = { ...selectedEntities }

    SAMPLE_ENTITIES[activeTab].forEach((entity) => {
      newSelected[entity.id] = checked
    })

    setSelectedEntities(newSelected)
  }

  // Handle adding selected entities to content queue
  const handleAddToQueue = () => {
    // In a real app, this would dispatch to a global state or make an API call
    console.log(
      "Adding to queue:",
      Object.entries(selectedEntities)
        .filter(([_, isSelected]) => isSelected)
        .map(([id]) => id),
    )

    // Show success message
    setAddSuccess(true)
    setTimeout(() => setAddSuccess(false), 3000)

    // Reset selections
    setSelectedEntities({})
  }

  // Count selected entities
  const selectedCount = Object.values(selectedEntities).filter(Boolean).length

  // Get icon for current entity type
  const getEntityIcon = () => {
    switch (activeTab) {
      case "persons":
        return <User className="h-5 w-5 text-blue-500" />
      case "organizations":
        return <Building className="h-5 w-5 text-green-500" />
      case "locations":
        return <MapPin className="h-5 w-5 text-purple-500" />
      case "dates":
        return <Calendar className="h-5 w-5 text-yellow-500" />
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          {getEntityIcon()}
          <span className="ml-2">Entity Recognition Results</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)}>
          <TabsList className="w-full mb-6">
            <TabsTrigger value="persons" className="flex-1">
              Persons ({SAMPLE_ENTITIES.persons.length})
            </TabsTrigger>
            <TabsTrigger value="organizations" className="flex-1">
              Organizations ({SAMPLE_ENTITIES.organizations.length})
            </TabsTrigger>
            <TabsTrigger value="locations" className="flex-1">
              Locations ({SAMPLE_ENTITIES.locations.length})
            </TabsTrigger>
            <TabsTrigger value="dates" className="flex-1">
              Dates ({SAMPLE_ENTITIES.dates.length})
            </TabsTrigger>
          </TabsList>

          {addSuccess && (
            <div className="bg-green-50 border border-green-200 rounded-md p-3 mb-4 flex items-center">
              <Check className="h-5 w-5 text-green-500 mr-2" />
              <p className="text-green-700">Entities successfully added to content queue!</p>
            </div>
          )}

          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center space-x-2">
              <Checkbox id="select-all" onCheckedChange={(checked) => handleSelectAll(!!checked)} />
              <Label htmlFor="select-all">Select All</Label>
            </div>
            <Button
              size="sm"
              onClick={handleAddToQueue}
              disabled={selectedCount === 0}
              className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
            >
              <PlusCircle className="h-4 w-4 mr-2" />
              Add Selected to Content Queue ({selectedCount})
            </Button>
          </div>

          <TabsContent value="persons" className="space-y-2">
            {SAMPLE_ENTITIES.persons.map((person) => (
              <div key={person.id} className="flex items-center justify-between p-3 border rounded-md">
                <div className="flex items-center">
                  <Checkbox
                    id={person.id}
                    checked={selectedEntities[person.id] || false}
                    onCheckedChange={(checked) => handleSelectEntity(person.id, !!checked)}
                  />
                  <Label htmlFor={person.id} className="ml-3 cursor-pointer">
                    {person.name}
                  </Label>
                </div>
                <Badge variant="outline">Frequency: {person.frequency}</Badge>
              </div>
            ))}
          </TabsContent>

          <TabsContent value="organizations" className="space-y-2">
            {SAMPLE_ENTITIES.organizations.map((org) => (
              <div key={org.id} className="flex items-center justify-between p-3 border rounded-md">
                <div className="flex items-center">
                  <Checkbox
                    id={org.id}
                    checked={selectedEntities[org.id] || false}
                    onCheckedChange={(checked) => handleSelectEntity(org.id, !!checked)}
                  />
                  <Label htmlFor={org.id} className="ml-3 cursor-pointer">
                    {org.name}
                  </Label>
                </div>
                <Badge variant="outline">Frequency: {org.frequency}</Badge>
              </div>
            ))}
          </TabsContent>

          <TabsContent value="locations" className="space-y-2">
            {SAMPLE_ENTITIES.locations.map((location) => (
              <div key={location.id} className="flex items-center justify-between p-3 border rounded-md">
                <div className="flex items-center">
                  <Checkbox
                    id={location.id}
                    checked={selectedEntities[location.id] || false}
                    onCheckedChange={(checked) => handleSelectEntity(location.id, !!checked)}
                  />
                  <Label htmlFor={location.id} className="ml-3 cursor-pointer">
                    {location.name}
                  </Label>
                </div>
                <Badge variant="outline">Frequency: {location.frequency}</Badge>
              </div>
            ))}
          </TabsContent>

          <TabsContent value="dates" className="space-y-2">
            {SAMPLE_ENTITIES.dates.map((date) => (
              <div key={date.id} className="flex items-center justify-between p-3 border rounded-md">
                <div className="flex items-center">
                  <Checkbox
                    id={date.id}
                    checked={selectedEntities[date.id] || false}
                    onCheckedChange={(checked) => handleSelectEntity(date.id, !!checked)}
                  />
                  <Label htmlFor={date.id} className="ml-3 cursor-pointer">
                    {date.name}
                  </Label>
                </div>
                <Badge variant="outline">Frequency: {date.frequency}</Badge>
              </div>
            ))}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
