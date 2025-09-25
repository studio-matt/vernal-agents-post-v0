"use client"

import { Header } from "@/components/Header"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Plus, FileText, BookOpen, Music } from "lucide-react"
import Link from "next/link"
import Image from "next/image"

const podcastShows = [
  {
    id: "podcast-1",
    title: "Tech Insights Weekly",
    excerpt: "A weekly deep dive into emerging technologies and their impact on business and society.",
    thumbnail: "/podcast-setup.png",
    episodeCount: 24,
    category: "Technology",
  },
  {
    id: "podcast-2",
    title: "Marketing Masterminds",
    excerpt: "Interviews with top marketing professionals sharing strategies that drive growth.",
    thumbnail: "/marketing-strategy-meeting.png",
    episodeCount: 18,
    category: "Marketing",
  },
  {
    id: "podcast-3",
    title: "Future of Work",
    excerpt: "Exploring how technology and culture are reshaping the workplace and workforce.",
    thumbnail: "/abstract-work.png",
    episodeCount: 12,
    category: "Business",
  },
]

export default function PodcastToolsPage() {
  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <Header />
      <main className="p-6 max-w-7xl mx-auto space-y-6">
        <h1 className="text-4xl font-extrabold text-white">Podcast Tools</h1>

        <Card className="w-full">
          <CardContent className="p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">Podcast Shows</h2>
              <Link href="/dashboard/podcast/add">
                <Button className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90">
                  <Plus className="h-4 w-4 mr-2" />
                  Add a Show
                </Button>
              </Link>
            </div>

            <div className="space-y-4">
              {podcastShows.map((show) => (
                <div key={show.id} className="flex items-start gap-4 p-4 border rounded-lg hover:bg-gray-50">
                  <Image
                    src={show.thumbnail || "/placeholder.svg"}
                    alt={show.title}
                    width={120}
                    height={120}
                    className="rounded-md object-cover"
                  />
                  <div className="flex-1 min-w-0">
                    <h3 className="text-xl font-semibold">{show.title}</h3>
                    <p className="text-gray-600 line-clamp-2 mt-1">{show.excerpt}</p>
                    <div className="mt-2 text-sm text-gray-500">
                      <span className="inline-flex items-center mr-4">
                        <FileText className="w-4 h-4 mr-1" />
                        {show.episodeCount} Episodes
                      </span>
                      <span className="inline-flex items-center">
                        <BookOpen className="w-4 h-4 mr-1" />
                        {show.category}
                      </span>
                    </div>
                  </div>
                  <Link href={`/dashboard/podcast/edit/${show.id}`}>
                    <Button variant="outline">Edit Episode</Button>
                  </Link>
                </div>
              ))}

              {podcastShows.length === 0 && (
                <div className="text-center py-12 border rounded-lg">
                  <Music className="mx-auto h-12 w-12 text-gray-300 mb-2" />
                  <p className="text-gray-500">No podcast shows yet</p>
                  <p className="text-sm text-gray-400">Add your first show to get started</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
