"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { loginUser, forgetPassword, resetPassword, signupUser, verifyEmail, resendotp } from "@/components/Service"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function Home() {
  const router = useRouter()

  // Login state
  const [loginData, setLoginData] = useState({ username: "", password: "" })
  const [resetData, setResetData] = useState({ otp_code: "", new_password: "" })
  const [isForgotMode, setIsForgotMode] = useState(false)
  const [showResetForm, setShowResetForm] = useState(false)
  const [loginLoading, setLoginLoading] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loginMessage, setLoginMessage] = useState<string | null>(null)

  // Signup state
  const [signupData, setSignupData] = useState({
    username: "",
    email: "",
    password: "",
    contact: "",
  })
  const [otp, setOtp] = useState("")
  const [showOtpField, setShowOtpField] = useState(false)
  const [signupLoading, setSignupLoading] = useState(false)
  const [signupError, setSignupError] = useState<string | null>(null)
  const [signupMessage, setSignupMessage] = useState<string | null>(null)
  const [email, setEmail] = useState("")

  // Login handlers
  const handleLoginChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLoginData({ ...loginData, [e.target.name]: e.target.value })
  }

  const handleResetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setResetData({ ...resetData, [e.target.name]: e.target.value })
  }

  const handleLogin = async () => {
    if (!loginData.username || !loginData.password) {
      setLoginError("Both username and password are required.")
      return
    }

    setLoginLoading(true)
    setLoginError(null)
    setLoginMessage(null)

    console.log("[v0] Login payload being sent:", {
      username: loginData.username,
      password: loginData.password,
    })

    try {
      const response = await loginUser({
        username: loginData.username,
        password: loginData.password,
      })

      if (response?.status === "success") {
        setLoginMessage("Login successful!")
        localStorage.setItem("token", response.token)
        localStorage.setItem("username", loginData.username)
        localStorage.setItem("email", loginData.username)
        
        // Go directly to campaigns page (onboarding is skipped for now)
        localStorage.setItem("onboarding_completed", "true")
        setTimeout(() => router.push("/dashboard/campaigns"), 1000)
      } else {
        setLoginError(response?.message || "Login failed. Please try again.")
      }
    } catch (err: any) {
      console.log("[v0] Error during login - full error:", err?.message)
      console.log("[v0] Error response data:", err?.response?.data)
      console.log("[v0] Error status:", err?.response?.status)
      console.log("[v0] Error headers:", err?.response?.headers)

      let errorMessage = "Login failed. Please try again."

      if (err?.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          // Extract messages from the detail array
          const messages = err.response.data.detail.map((error: any) => error.msg).join(", ")
          errorMessage = messages || errorMessage
        } else if (typeof err.response.data.detail === "string") {
          // Handle string detail directly
          errorMessage = err.response.data.detail
        }
      } else if (err?.response?.data?.message) {
        errorMessage = err.response.data.message
      } else if (err?.message) {
        errorMessage = err.message
      }

      setLoginError(errorMessage)
    }

    setLoginLoading(false)
  }

  const handleForgetPassword = async () => {
    setLoginLoading(true)
    setLoginError(null)
    setLoginMessage(null)

    if (!loginData.username) {
      setLoginError("Email is required to resend OTP.")
      setLoginLoading(false)
      return
    }

    try {
      const response = await forgetPassword({ email: loginData.username })

      if (response?.status === 200) {
        setLoginMessage("OTP sent for password reset.")
        setShowResetForm(true)
      } else {
        setLoginError(response?.message || "Failed to resend OTP.")
      }
    } catch (err) {
      setLoginError("Failed to resend OTP due to unexpected error.")
      console.error(err)
    }

    setLoginLoading(false)
  }

  const handleResetPassword = async () => {
    setLoginLoading(true)
    setLoginError(null)
    setLoginMessage(null)

    try {
      const response = await resetPassword({
        email: loginData.username,
        otp_code: resetData.otp_code,
        new_password: resetData.new_password,
      })

      if (response?.status === 200) {
        setLoginMessage("Password reset successfully.")
        localStorage.setItem("token", response.token)
        localStorage.setItem("username", loginData.username)
        localStorage.setItem("email", loginData.username)
        setTimeout(() => router.push("/login"), 1000)
      } else {
        setLoginError(response.message)
      }
    } catch (err) {
      setLoginError("Reset failed due to unexpected error.")
      console.error(err)
    }

    setLoginLoading(false)
  }

  // Signup handlers
  const handleSignupChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSignupData({ ...signupData, [e.target.name]: e.target.value })
  }

  const handleSignup = async () => {
    setSignupLoading(true)
    setSignupError(null)
    setSignupMessage(null)

    try {
      const response = await signupUser(signupData)

      if (response?.status === 200) {
        setSignupMessage(response?.message || "OTP sent to your email.")
        setShowOtpField(true)
      } else {
        setSignupError(response?.message || "Signup failed. Please check your inputs.")
      }
    } catch (err) {
      console.error("Signup error:", err)
      setSignupError("Signup failed due to unexpected error.")
    }

    setSignupLoading(false)
  }

  const handleVerifyOtp = async () => {
    setSignupLoading(true)
    setSignupError(null)
    setSignupMessage(null)

    try {
      const verificationResponse = await verifyEmail({
        email: signupData.email,
        otp_code: otp,
      })

      localStorage.setItem("username", signupData.username)
      localStorage.setItem("email", signupData.email)
      setSignupMessage("Email verified successfully!")

      setTimeout(() => {
        router.push("/login")
      }, 1500)
    } catch (err) {
      setSignupError("OTP verification failed.")
    }

    setSignupLoading(false)
  }

  const handleResendOtp = async () => {
    setSignupLoading(true)
    setSignupError(null)
    setSignupMessage(null)

    const currentEmail = signupData.email || email

    if (!currentEmail) {
      setSignupError("Email is required to resend OTP.")
      setSignupLoading(false)
      return
    }

    try {
      const response = await resendotp({ email: currentEmail })

      if (response?.status === 200) {
        setSignupMessage("OTP resent successfully to your email.")
      } else {
        setSignupError(response?.message || "Failed to resend OTP.")
      }
    } catch (err) {
      console.error("Resend OTP error:", err)
      setSignupError("Failed to resend OTP due to unexpected error.")
    }

    setSignupLoading(false)
  }

  // Enter key handlers for forms
  const handleLoginKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      if (isForgotMode) {
        if (showResetForm) {
          handleResetPassword()
        } else {
          handleForgetPassword()
        }
      } else {
        handleLogin()
      }
    }
  }

  const handleSignupKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      if (showOtpField) {
        handleVerifyOtp()
      } else {
        handleSignup()
      }
    }
  }

  return (
    <div className="min-h-screen bg-[#7A99A8]">
      <main className="container max-w-7xl mx-auto p-6 space-y-8">
        <div className="text-center text-white space-y-2">
          <div className="text-sm" style={{ fontSize: "14pt" }}>
            welcome to
          </div>
          <div className="font-bold" style={{ fontSize: "30pt" }}>
            Vernal Contentum
          </div>
        </div>

        <div className="flex gap-8 items-start">
          {/* Login Section - Left Side */}
          <div className="flex-1">
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
                    value={loginData.username}
                    onChange={handleLoginChange}
                    onKeyPress={handleLoginKeyPress}
                    className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                    disabled={loginLoading}
                  />
                </div>

                {!isForgotMode && (
                  <div>
                    <label className="block font-medium mb-1">Password</label>
                    <input
                      type="password"
                      name="password"
                      value={loginData.password}
                      onChange={handleLoginChange}
                      onKeyPress={handleLoginKeyPress}
                      className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                      disabled={loginLoading}
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
                        onKeyPress={handleLoginKeyPress}
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
                        onKeyPress={handleLoginKeyPress}
                        className="w-full border rounded-md px-3 py-2"
                      />
                    </div>
                    <Button
                      onClick={handleResetPassword}
                      className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                      disabled={loginLoading}
                    >
                      {loginLoading ? "Resetting Password..." : "Reset Password"}
                    </Button>
                  </>
                )}

                {!showResetForm && (
                  <Button
                    onClick={isForgotMode ? handleForgetPassword : handleLogin}
                    className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                    disabled={loginLoading}
                  >
                    {loginLoading
                      ? isForgotMode
                        ? "Sending OTP..."
                        : "Logging in..."
                      : isForgotMode
                        ? "Send OTP"
                        : "Login"}
                  </Button>
                )}

                {loginError && <div className="text-red-500 font-medium">{loginError}</div>}
                {loginMessage && !loginError && <div className="text-green-600 font-medium">{loginMessage}</div>}

                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-gray-600">
                    {isForgotMode ? "Remembered your password?" : "Didn't know the Password?"}
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setIsForgotMode(!isForgotMode)
                      setLoginError(null)
                      setLoginMessage(null)
                      setShowResetForm(false)
                    }}
                    className="text-sm text-block hover:underline"
                    disabled={loginLoading}
                  >
                    {isForgotMode ? "Back to Login" : "Forget Password"}
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="w-px bg-white/30 self-stretch mx-8"></div>

          {/* Signup Section - Right Side */}
          <div className="flex-1">
            <Card>
              <CardHeader>
                <CardTitle className="text-2xl font-bold">Create an Account</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {!showOtpField && (
                  <>
                    <div>
                      <label className="block font-medium mb-1">Username</label>
                      <input
                        type="text"
                        name="username"
                        value={signupData.username}
                        onChange={handleSignupChange}
                        onKeyPress={handleSignupKeyPress}
                        className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                        disabled={signupLoading}
                      />
                    </div>
                    <div>
                      <label className="block font-medium mb-1">Email</label>
                      <input
                        type="email"
                        name="email"
                        value={signupData.email}
                        onChange={handleSignupChange}
                        onKeyPress={handleSignupKeyPress}
                        className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                        disabled={signupLoading}
                      />
                    </div>
                    <div>
                      <label className="block font-medium mb-1">Password</label>
                      <input
                        type="password"
                        name="password"
                        value={signupData.password}
                        onChange={handleSignupChange}
                        onKeyPress={handleSignupKeyPress}
                        className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                        disabled={signupLoading}
                      />
                    </div>
                    <div>
                      <label className="block font-medium mb-1">Contact Number</label>
                      <input
                        type="text"
                        name="contact"
                        value={signupData.contact}
                        onChange={handleSignupChange}
                        onKeyPress={handleSignupKeyPress}
                        className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                        disabled={signupLoading}
                      />
                    </div>

                    <Button
                      onClick={handleSignup}
                      className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                      disabled={signupLoading}
                    >
                      {signupLoading ? "Signing up..." : "Sign Up"}
                    </Button>
                  </>
                )}

                {signupError && <div className="text-red-500 font-medium">{signupError}</div>}
                {signupMessage && !signupError && <div className="text-green-600 font-medium">{signupMessage}</div>}

                {showOtpField && (
                  <>
                    <div>
                      <label className="block font-medium mb-1">Enter Email</label>
                      <input
                        type="email"
                        value={signupData.email || email}
                        onChange={(e) =>
                          signupData.email
                            ? setSignupData({ ...signupData, email: e.target.value })
                            : setEmail(e.target.value)
                        }
                        onKeyPress={handleSignupKeyPress}
                        className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                        disabled={signupLoading}
                        required
                      />
                    </div>

                    <div className="mt-4">
                      <label className="block font-medium mb-1">Enter OTP</label>
                      <input
                        type="text"
                        value={otp}
                        onChange={(e) => setOtp(e.target.value)}
                        onKeyPress={handleSignupKeyPress}
                        className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                        disabled={signupLoading}
                      />
                    </div>

                    <Button
                      onClick={handleVerifyOtp}
                      className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90 mt-4"
                      disabled={signupLoading || !otp}
                    >
                      {signupLoading ? "Verifying..." : "Verify OTP"}
                    </Button>

                    <div className="flex items-center justify-between mt-4">
                      <p className="text-sm text-gray-600">Didn't receive the OTP?</p>
                      <button
                        type="button"
                        onClick={handleResendOtp}
                        className="text-sm text-block hover:underline"
                        disabled={signupLoading}
                      >
                        Resend OTP
                      </button>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}
