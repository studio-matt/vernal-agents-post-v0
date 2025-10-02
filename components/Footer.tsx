import Link from "next/link"

export function Footer() {
  return (
    <footer className="bg-[#3d545f] text-white py-8 mt-auto">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Logo Section */}
          <div className="flex flex-col items-start">
            <div className="text-2xl font-bold mb-4">Vernal Contentum</div>
            <p className="text-gray-300 text-sm">AI-powered content creation and management platform</p>
          </div>

          {/* Navigation Links */}
          <div className="flex flex-col">
            <h3 className="font-semibold mb-4">Navigation</h3>
            <div className="space-y-2">
              <Link
                href="/dashboard/content-planner"
                className="text-gray-300 hover:text-white transition-colors text-sm"
              >
                Content Planner
              </Link>
              <Link
                href="/dashboard/author-planning"
                className="text-gray-300 hover:text-white transition-colors text-sm"
              >
                Author Planning
              </Link>
              <Link
                href="/dashboard/podcast-tools"
                className="text-gray-300 hover:text-white transition-colors text-sm"
              >
                Podcast Tools
              </Link>
              <Link href="/post" className="text-gray-300 hover:text-white transition-colors text-sm">
                View Scheduled Posts
              </Link>
            </div>
          </div>

          {/* Copyright */}
          <div className="flex flex-col items-start md:items-end">
            <div className="text-sm text-gray-300">© {new Date().getFullYear()} Vernal Contentum</div>
            <div className="text-sm text-gray-300 mt-1">All rights reserved</div>
          </div>
        </div>
      </div>
    </footer>
  )
}
