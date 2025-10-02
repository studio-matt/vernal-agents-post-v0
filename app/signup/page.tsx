"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signupUser, verifyEmail, resendotp } from "@/components/Service";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft } from "lucide-react";

export default function Signup() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    contact: "",
  });

  const [otp, setOtp] = useState("");
  const [showOtpField, setShowOtpField] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSignup = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const response = await signupUser(formData);
      console.log("Signup API response:", response);

      if (response?.status === 200) {
        setMessage(response?.message || "OTP sent to your email.");
        setShowOtpField(true);
      } else {
        setError(
          response?.message || "Signup failed. Please check your inputs."
        );
      }
    } catch (err) {
      console.error("Signup error:", err);
      setError("Signup failed due to unexpected error.");
    }

    setLoading(false);
  };

  const handleVerifyOtp = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const verificationResponse = await verifyEmail({
        email: formData.email,
        otp_code: otp,
      });

      localStorage.setItem("username", formData.username);
      localStorage.setItem("email", formData.email);
      setMessage("Email verified successfully!");

      setTimeout(() => {
        router.push("/login");
      }, 1500);
    } catch (err) {
      setError("OTP verification failed.");
    }

    setLoading(false);
  };

  const handleResendOtp = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);

    const currentEmail = formData.email || email;

    if (!currentEmail) {
      setError("Email is required to resend OTP.");
      setLoading(false);
      return;
    }

    try {
      const response = await resendotp({ email: currentEmail });

      if (response?.status === 200) {
        setMessage("OTP resent successfully to your email.");
      } else {
        setError(response?.message || "Failed to resend OTP.");
      }
    } catch (err) {
      console.error("Resend OTP error:", err);
      setError("Failed to resend OTP due to unexpected error.");
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#7A99A8]">
      {/* <Header /> */}
      {/* <Header username="John Doe" /> */}
      <main className="container max-w-2xl mx-auto p-6 space-y-6">
        <div className="flex items-center space-x-4">
          <Link
            href="/login"
            className="flex items-center text-white hover:text-gray-200"
          >
            <ChevronLeft className="h-5 w-5 mr-1" />
            Back to Login
          </Link>
          <h1 className="text-4xl font-extrabold text-white">Signup</h1>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-2xl font-bold">
              Create an Account
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Registration Form */}
            {!showOtpField && (
              <>
                <div>
                  <label className="block font-medium mb-1">Username</label>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                    disabled={loading}
                  />
                </div>
                <div>
                  <label className="block font-medium mb-1">Email</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                    disabled={loading}
                  />
                </div>
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
                <div>
                  <label className="block font-medium mb-1">
                    Contact Number
                  </label>
                  <input
                    type="text"
                    name="contact"
                    value={formData.contact}
                    onChange={handleChange}
                    className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                    disabled={loading}
                  />
                </div>

                <Button
                  onClick={handleSignup}
                  className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                  disabled={loading}
                >
                  {loading ? "Signing up..." : "Sign Up"}
                </Button>
              </>
            )}

            {/* Display error or success message */}
            {error && <div className="text-red-500 font-medium">{error}</div>}
            {message && !error && (
              <div className="text-green-600 font-medium">{message}</div>
            )}

            {/* OTP Form (show only after successful signup) */}
            {showOtpField && (
              <>
                <div>
                  <label className="block font-medium mb-1">Enter Email</label>
                  <input
                    type="email"
                    value={formData.email || email}
                    onChange={(e) =>
                      formData.email
                        ? setFormData({ ...formData, email: e.target.value })
                        : setEmail(e.target.value)
                    }
                    className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                    disabled={loading}
                    required
                  />
                </div>

                <div className="mt-4">
                  <label className="block font-medium mb-1">Enter OTP</label>
                  <input
                    type="text"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    className="w-full border rounded-md px-3 py-2 focus:ring-1 focus:ring-[#020817] focus:border-transparent"
                    disabled={loading}
                  />
                </div>

                <Button
                  onClick={handleVerifyOtp}
                  className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90 mt-4"
                  disabled={loading || !otp}
                >
                  {loading ? "Verifying..." : "Verify OTP"}
                </Button>

                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-gray-600">
                    Didn't receive the OTP?
                  </p>
                  <button
                    type="button"
                    onClick={handleResendOtp}
                    className="text-sm text-block hover:underline"
                    disabled={loading}
                  >
                    Resend OTP
                  </button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
