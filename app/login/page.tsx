"use client"

import type React from "react"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { loginUser, forgetPassword, resetPassword } from "@/components/Service"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChevronLeft } from "lucide-react"

export default function Login() {
  const router = useRouter()

  const [formData, setFormData] = useState({ username: "", password: "" })
  const [resetData, setResetData] = useState({
    otp_code: "",
    new_password: "",
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const [isForgotMode, setIsForgotMode] = useState(false)
  const [showResetForm, setShowResetForm] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleResetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setResetData({ ...resetData, [e.target.name]: e.target.value })
  }

  const handleLogin = async () => {
    if (!formData.username || !formData.password) {
      setError("Both username and password are required.")
      return
    }

    setLoading(true)
    setError(null)
    setMessage(null)

    console.log("[v0] Login form data:", formData)

    try {
      const response = await loginUser({
        username: formData.username,
        password: formData.password,
      })

      console.log("[v0] Login response received:", response)

      if (response?.status === "success") {
        setMessage("Login successful!")
        localStorage.setItem("token", response.token)
        localStorage.setItem("username", formData.username)
        localStorage.setItem("email", formData.username)
        
        // Check if onboarding is completed
        const onboardingCompleted = localStorage.getItem("onboarding_completed")
        if (onboardingCompleted === "true") {
          setTimeout(() => router.push("/dashboard/content-planner"), 1000)
        } else {
          setTimeout(() => router.push("/onboarding"), 1000)
        }
      } else {
        setError(response?.message || "Login failed. Please try again.")
      }
    } catch (err: any) {
      console.error("[v0] Login error caught:", err)
      const errorMessage =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "User does not exist. Please register first."
      setError(errorMessage)
    }

    setLoading(false)
  }

  const handleForgetPassword = async () => {
    setLoading(true)
    setError(null)
    setMessage(null)

    if (!formData.username) {
      setError("Email is required to resend OTP.")
      setLoading(false)
      return
    }

    try {
      const response = await forgetPassword({ email: formData.username })

      if (response?.status === 200) {
        setMessage("OTP sent for password reset.")
        setShowResetForm(true)
      } else {
        setError(response?.message || "Failed to resend OTP.")
      }
    } catch (err) {
      setError("Failed to resend OTP due to unexpected error.")
      console.error(err)
    }

    setLoading(false)
  }

  const handleResetPassword = async () => {
    setLoading(true)
    setError(null)
    setMessage(null)

    try {
      const response = await resetPassword({
        email: formData.username,
        otp_code: resetData.otp_code,
        new_password: resetData.new_password,
      })

      if (response?.status === 200) {
        setMessage("Password reset successfully.")
        localStorage.setItem("token", response.token)

        localStorage.setItem("username", formData.username)
        localStorage.setItem("email", formData.username)
        setTimeout(() => router.push("/login"), 1000)
      } else {
        setError(response.message)
      }
    } catch (err) {
      setError("Reset failed due to unexpected error.")
      console.error(err)
    }

    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <main className="container max-w-2xl mx-auto p-6 space-y-6">
        <div className="flex items-center space-x-4">
          <Link href="/signup" className="flex items-center text-white hover:text-gray-200">
            <ChevronLeft className="h-5 w-5 mr-1" />
            Back to Signup
          </Link>
          <h1 className="text-4xl font-extrabold text-white">Login</h1>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-2xl font-bold">Welcome Back</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block font-medium mb-1">Email</label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                disabled={loading}
              />
            </div>

            {!isForgotMode && (
              <div>
                <label className="block font-medium mb-1">Password</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                  disabled={loading}
                />
              </div>
            )}

            {isForgotMode && showResetForm && (
              <>
                <div>
                  <label className="block font-medium mb-1">OTP Code</label>
                  <input
                    type="text"
                    name="otp_code"
                    value={resetData.otp_code}
                    onChange={handleResetChange}
                    className="w-full border rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block font-medium mb-1">New Password</label>
                  <input
                    type="password"
                    name="new_password"
                    value={resetData.new_password}
                    onChange={handleResetChange}
                    className="w-full border rounded-md px-3 py-2"
                  />
                </div>
                <Button
                  onClick={handleResetPassword}
                  className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                  disabled={loading}
                >
                  {loading ? "Resetting Password..." : "Reset Password"}
                </Button>
              </>
            )}

            {!showResetForm && (
              <Button
                onClick={isForgotMode ? handleForgetPassword : handleLogin}
                className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                disabled={loading}
              >
                {loading ? (isForgotMode ? "Sending OTP..." : "Logging in...") : isForgotMode ? "Send OTP" : "Login"}
              </Button>
            )}

            {error && <div className="text-red-500 font-medium">{error}</div>}
            {message && !error && <div className="text-green-600 font-medium">{message}</div>}

            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-gray-600">
                {isForgotMode ? "Remembered your password?" : "Didn't know the Password?"}
              </p>
              <button
                type="button"
                onClick={() => {
                  setIsForgotMode(!isForgotMode)
                  setError(null)
                  setMessage(null)
                  setShowResetForm(false)
                }}
                className="text-sm text-block hover:underline"
                disabled={loading}
              >
                {isForgotMode ? "Back to Login" : "Forget Password"}
              </button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
