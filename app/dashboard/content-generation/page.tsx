"use client"
import Link from "next/link"
import { Header } from "@/components/Header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChevronLeft, FileText, Lightbulb } from "lucide-react"
import { ContentGenerationQueue } from "@/components/ContentGenerationQueue"

export default function ContentGenerationPage() {
  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <Header username="John Doe" />
      <main className="p-6 max-w-7xl mx-auto space-y-6">
        <div className="flex items-center space-x-4">
          <Link href="/dashboard" className="flex items-center text-white hover:text-gray-200">
            <ChevronLeft className="h-5 w-5 mr-1" />
            Back to Campaign
          </Link>
          <h1 className="text-4xl font-extrabold text-white">Content Generation</h1>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Content Generation</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <ContentGenerationQueue />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Content Generation Tips</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-6">
              <div className="flex items-start">
                <Lightbulb className="w-5 h-5 text-blue-500 mt-0.5 mr-2 flex-shrink-0" />
                <div className="space-y-2">
                  <p className="text-blue-700">
                    <strong>How to use the Content Generation Queue:</strong>
                  </p>
                  <ol className="list-decimal ml-5 text-blue-700 space-y-1">
                    <li>Add items to the queue from Entity Recognition, Topic Modeling, or Research Assistant tabs</li>
                    <li>Select the items you want to generate content for</li>
                    <li>Click "Generate Content" to create AI-generated content based on your selections</li>
                    <li>Review and edit the generated content in the "Generated Content" tab</li>
                    <li>Schedule content for production using the platform and time options</li>
                    <li>View your scheduled content in the "Production Schedule" tab</li>
                  </ol>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="border rounded-md p-4">
                <FileText className="h-6 w-6 text-blue-500 mb-2" />
                <h3 className="font-semibold mb-1">Combine Multiple Sources</h3>
                <p className="text-sm text-gray-600">
                  Select items from different analysis sources to create more comprehensive and nuanced content.
                </p>
              </div>

              <div className="border rounded-md p-4">
                <FileText className="h-6 w-6 text-green-500 mb-2" />
                <h3 className="font-semibold mb-1">Edit for Brand Voice</h3>
                <p className="text-sm text-gray-600">
                  Always review and edit generated content to ensure it matches your brand's unique voice and style.
                </p>
              </div>

              <div className="border rounded-md p-4">
                <FileText className="h-6 w-6 text-purple-500 mb-2" />
                <h3 className="font-semibold mb-1">Schedule Strategically</h3>
                <p className="text-sm text-gray-600">
                  Plan your content schedule to align with your audience's activity patterns on each platform.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
