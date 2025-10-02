"use client"

import { Button } from "@/components/ui/button"

import { Checkbox } from "@/components/ui/checkbox"

import { CardTitle } from "@/components/ui/card"

import { Calendar } from "@/components/ui/calendar"

import { CardContent } from "@/components/ui/card"

import { CardHeader } from "@/components/ui/card"

import { Card } from "@/components/ui/card"

import { useState } from "react"

// Replace the placeholder implementation with a full implementation that includes checkboxes for entities

function EntityRecognitionWorkflow({ copyAnchorLink }: SectionProps) {
  const [selectedEntities, setSelectedEntities] = useState<{
    persons: string[]
    organizations: string[]
    locations: string[]
    dates: string[]
  }>({
    persons: [],
    organizations: [],
    locations: [],
    dates: [],
  })

  const [contentQueue, setContentQueue] = useState<string[]>([])
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Sample entity data
  const entityData = {
    persons: ["John Smith", "Sarah Johnson", "Michael Brown", "Emily Davis", "Robert Wilson"],
    organizations: ["Acme Corporation", "Global Tech", "Innovative Solutions", "Market Leaders", "Tech Pioneers"],
    locations: ["San Francisco", "New York", "London", "Tokyo", "Berlin"],
    dates: ["Q1 2025", "March 15, 2025", "Summer 2025", "January 2026", "Q4 2024"],
  }

  const handleEntitySelection = (category: keyof typeof selectedEntities, entity: string) => {
    setSelectedEntities((prev) => {
      const updated = { ...prev }
      if (updated[category].includes(entity)) {
        updated[category] = updated[category].filter((e) => e !== entity)
      } else {
        updated[category] = [...updated[category], entity]
      }
      return updated
    })
  }

  const handleSaveToContentQueue = () => {
    // Combine all selected entities into a single array
    const allSelected = [
      ...selectedEntities.persons,
      ...selectedEntities.organizations,
      ...selectedEntities.locations,
      ...selectedEntities.dates,
    ]

    // In a real app, this would send the data to a global state or backend
    setContentQueue(allSelected)

    // Show success message
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3000)

    console.log("Saved to content queue:", allSelected)
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <SectionHeader
            id="entity-recognition"
            title="Entity Recognition"
            description="The process of identifying and classifying named entities in text"
            copyAnchorLink={copyAnchorLink}
          />
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Entity Overview - Keep existing content */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-blue-100 mb-2">
                  <User className="w-6 h-6 text-blue-600" />
                </div>
                <h4 className="font-medium">Persons</h4>
                <p className="text-3xl font-bold mt-1 mb-1">{entityData.persons.length}</p>
                <p className="text-sm text-gray-500">Identified individuals</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-green-100 mb-2">
                  <Building className="w-6 h-6 text-green-600" />
                </div>
                <h4 className="font-medium">Organizations</h4>
                <p className="text-3xl font-bold mt-1 mb-1">{entityData.organizations.length}</p>
                <p className="text-sm text-gray-500">Companies and groups</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-purple-100 mb-2">
                  <MapPin className="w-6 h-6 text-purple-600" />
                </div>
                <h4 className="font-medium">Locations</h4>
                <p className="text-3xl font-bold mt-1 mb-1">{entityData.locations.length}</p>
                <p className="text-sm text-gray-500">Geographic references</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-yellow-100 mb-2">
                  <Calendar className="w-6 h-6 text-yellow-600" />
                </div>
                <h4 className="font-medium">Dates</h4>
                <p className="text-3xl font-bold mt-1 mb-1">{entityData.dates.length}</p>
                <p className="text-sm text-gray-500">Temporal references</p>
              </CardContent>
            </Card>
          </div>

          {/* New section: Entity Selection for Content Queue */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Add Entities to Content Queue</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Persons */}
                <div>
                  <h3 className="text-md font-semibold flex items-center mb-2">
                    <User className="w-5 h-5 text-blue-600 mr-2" />
                    Persons
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {entityData.persons.map((person, index) => (
                      <div key={index} className="flex items-center space-x-2 p-2 border rounded-md">
                        <Checkbox
                          id={`person-${index}`}
                          checked={selectedEntities.persons.includes(person)}
                          onCheckedChange={() => handleEntitySelection("persons", person)}
                        />
                        <label
                          htmlFor={`person-${index}`}
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                        >
                          {person}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Organizations */}
                <div>
                  <h3 className="text-md font-semibold flex items-center mb-2">
                    <Building className="w-5 h-5 text-green-600 mr-2" />
                    Organizations
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {entityData.organizations.map((org, index) => (
                      <div key={index} className="flex items-center space-x-2 p-2 border rounded-md">
                        <Checkbox
                          id={`org-${index}`}
                          checked={selectedEntities.organizations.includes(org)}
                          onCheckedChange={() => handleEntitySelection("organizations", org)}
                        />
                        <label
                          htmlFor={`org-${index}`}
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                        >
                          {org}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Locations */}
                <div>
                  <h3 className="text-md font-semibold flex items-center mb-2">
                    <MapPin className="w-5 h-5 text-purple-600 mr-2" />
                    Locations
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {entityData.locations.map((location, index) => (
                      <div key={index} className="flex items-center space-x-2 p-2 border rounded-md">
                        <Checkbox
                          id={`location-${index}`}
                          checked={selectedEntities.locations.includes(location)}
                          onCheckedChange={() => handleEntitySelection("locations", location)}
                        />
                        <label
                          htmlFor={`location-${index}`}
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                        >
                          {location}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Dates */}
                <div>
                  <h3 className="text-md font-semibold flex items-center mb-2">
                    <Calendar className="w-5 h-5 text-yellow-600 mr-2" />
                    Dates
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {entityData.dates.map((date, index) => (
                      <div key={index} className="flex items-center space-x-2 p-2 border rounded-md">
                        <Checkbox
                          id={`date-${index}`}
                          checked={selectedEntities.dates.includes(date)}
                          onCheckedChange={() => handleEntitySelection("dates", date)}
                        />
                        <label
                          htmlFor={`date-${index}`}
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                        >
                          {date}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-between items-center pt-4">
                  <div>
                    {saveSuccess && (
                      <div className="text-green-600 flex items-center">
                        <Check className="w-4 h-4 mr-1" />
                        Added to content queue
                      </div>
                    )}
                  </div>
                  <Button
                    onClick={handleSaveToContentQueue}
                    className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                    disabled={Object.values(selectedEntities).every((arr) => arr.length === 0)}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Selected to Content Queue
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </CardContent>
      </Card>
    </div>
  )
}
