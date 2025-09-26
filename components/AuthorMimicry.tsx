// "use client";

// import type React from "react";

// import { useState, useRef, useEffect } from "react";
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";
// import { Textarea } from "@/components/ui/textarea";
// import { Label } from "@/components/ui/label";
// import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
// import {
//   Select,
//   SelectContent,
//   SelectItem,
//   SelectTrigger,
//   SelectValue,
// } from "@/components/ui/select";
// import { Slider } from "@/components/ui/slider";
// import { Checkbox } from "@/components/ui/checkbox";
// import { Progress } from "@/components/ui/progress";
// import {
//   Upload,
//   FileText,
//   BarChart,
//   Brain,
//   Sparkles,
//   RefreshCw,
//   Save,
//   BookOpen,
//   Trash2,
//   PenTool,
//   Wand2,
//   Layers,
//   Bookmark,
//   Check,
//   User,
// } from "lucide-react";
// import {
//   Collapsible,
//   CollapsibleContent,
//   CollapsibleTrigger,
// } from "@/components/ui/collapsible";

// // First, import the new modal component
// import { PersonalityConfirmationModal } from "./PersonalityConfirmationModal";

// // Sample author profiles for demonstration
// const SAMPLE_AUTHOR_PROFILES = [
//   {
//     id: "1",
//     name: "Ernest Hemingway",
//     description: "Concise, direct prose with short sentences",
//   },
//   {
//     id: "2",
//     name: "Jane Austen",
//     description: "Elegant, witty social commentary",
//   },
//   {
//     id: "3",
//     name: "David Foster Wallace",
//     description: "Complex, footnote-heavy postmodern style",
//   },
//   {
//     id: "4",
//     name: "Stephen King",
//     description: "Suspenseful, character-driven horror and thriller",
//   },
//   {
//     id: "5",
//     name: "Toni Morrison",
//     description: "Poetic, rich with metaphor and cultural depth",
//   },
// ];

// // Sample feature analysis results
// const SAMPLE_LEXICAL_FEATURES = [
//   { name: "Average Word Length", value: "4.8 characters", percentile: 68 },
//   { name: "Vocabulary Richness", value: "0.72 (high)", percentile: 85 },
//   { name: "Function Word Ratio", value: "0.38", percentile: 42 },
//   { name: "Unique Words", value: "1,245", percentile: 76 },
//   {
//     name: "Word Frequency Distribution",
//     value: "Power law (α=1.2)",
//     percentile: 55,
//   },
//   { name: "Adjective Usage", value: "12% of content words", percentile: 63 },
//   { name: "Adverb Frequency", value: "8% of content words", percentile: 47 },
//   { name: "Noun-Verb Ratio", value: "1.4:1", percentile: 72 },
// ];

// const SAMPLE_SYNTACTIC_FEATURES = [
//   { name: "Average Sentence Length", value: "18.3 words", percentile: 62 },
//   { name: "Clause Density", value: "2.4 per sentence", percentile: 78 },
//   { name: "Passive Voice Usage", value: "12%", percentile: 35 },
//   { name: "Punctuation Patterns", value: "Comma-heavy", percentile: 82 },
//   {
//     name: "Part-of-Speech Distribution",
//     value: "Noun-dominant",
//     percentile: 68,
//   },
//   {
//     name: "Complex Sentence Ratio",
//     value: "42% of all sentences",
//     percentile: 76,
//   },
//   { name: "Question Frequency", value: "5% of sentences", percentile: 58 },
//   {
//     name: "Subordinate Clause Usage",
//     value: "1.8 per paragraph",
//     percentile: 65,
//   },
// ];

// const SAMPLE_STRUCTURAL_FEATURES = [
//   { name: "Paragraph Length", value: "4.2 sentences", percentile: 58 },
//   { name: "Discourse Markers", value: "Moderate usage", percentile: 65 },
//   { name: "Topic Progression", value: "Linear", percentile: 72 },
//   { name: "Rhetorical Structure", value: "Problem-Solution", percentile: 80 },
//   { name: "Cohesion Score", value: "0.68 (medium-high)", percentile: 74 },
//   {
//     name: "Transition Word Frequency",
//     value: "3.2 per paragraph",
//     percentile: 67,
//   },
//   { name: "Paragraph Coherence", value: "Strong (0.81)", percentile: 88 },
//   { name: "Narrative Structure", value: "Chronological", percentile: 70 },
// ];

// const SAMPLE_SEMANTIC_FEATURES = [
//   {
//     name: "Sentiment Polarity",
//     value: "Slightly positive (0.2)",
//     percentile: 62,
//   },
//   { name: "Emotional Tone", value: "Reflective", percentile: 75 },
//   { name: "Concreteness Rating", value: "Medium-high (0.68)", percentile: 64 },
//   { name: "Subjectivity Score", value: "0.45 (balanced)", percentile: 52 },
//   { name: "Metaphor Density", value: "1.8 per 100 words", percentile: 83 },
//   { name: "Thematic Consistency", value: "High (0.85)", percentile: 91 },
//   {
//     name: "Semantic Field Diversity",
//     value: "Moderate (0.62)",
//     percentile: 58,
//   },
// ];

// const SAMPLE_RHETORICAL_FEATURES = [
//   { name: "Persuasive Techniques", value: "Ethos-dominant", percentile: 77 },
//   { name: "Rhetorical Questions", value: "1.2 per 500 words", percentile: 65 },
//   { name: "Repetition Patterns", value: "Anaphora common", percentile: 82 },
//   { name: "Irony/Sarcasm Detection", value: "Low (0.15)", percentile: 32 },
//   { name: "Figurative Language", value: "Moderate usage", percentile: 58 },
//   { name: "Appeal Types", value: "Logical > Emotional", percentile: 71 },
//   {
//     name: "Audience Engagement",
//     value: "Direct address frequent",
//     percentile: 84,
//   },
// ];

// // Model configuration presets
// const MODEL_PRESETS = [
//   {
//     name: "Balanced",
//     sampleSize: 50,
//     featureWeight: 0.7,
//     complexityLevel: "medium",
//     creativityLevel: 0.5,
//     maxTokens: 500,
//   },
//   {
//     name: "High Fidelity",
//     sampleSize: 80,
//     featureWeight: 0.9,
//     complexityLevel: "complex",
//     creativityLevel: 0.3,
//     maxTokens: 800,
//   },
//   {
//     name: "Creative Adaptation",
//     sampleSize: 40,
//     featureWeight: 0.5,
//     complexityLevel: "medium",
//     creativityLevel: 0.8,
//     maxTokens: 600,
//   },
//   {
//     name: "Simplified Style",
//     sampleSize: 60,
//     featureWeight: 0.8,
//     complexityLevel: "simple",
//     creativityLevel: 0.4,
//     maxTokens: 400,
//   },
//   {
//     name: "Complex Elaboration",
//     sampleSize: 70,
//     featureWeight: 0.6,
//     complexityLevel: "very-complex",
//     creativityLevel: 0.7,
//     maxTokens: 1000,
//   },
// ];

// interface WritingSample {
//   id: number;
//   text: string;
//   file: File | null;
//   isUploaded: boolean;
// }

// // Add props interface to control which sections are displayed
// interface AuthorMimicryProps {
//   showSavedProfiles?: boolean;
//   defaultOpenSections?: {
//     writingSamples?: boolean;
//     modelConfig?: boolean;
//     results?: boolean;
//     profiles?: boolean;
//   };
// }

// export function AuthorMimicry({
//   showSavedProfiles = true,
//   defaultOpenSections = {
//     writingSamples: true,
//     modelConfig: false,
//     results: false,
//     profiles: true,
//   },
// }: AuthorMimicryProps) {
//   // State for writing samples
//   const [writingSamples, setWritingSamples] = useState<WritingSample[]>(
//     Array(10)
//       .fill(null)
//       .map((_, index) => ({
//         id: index + 1,
//         text: "",
//         file: null,
//         isUploaded: false,
//       }))
//   );

//   // State for feature selection
//   const [selectedFeatures, setSelectedFeatures] = useState({
//     lexical: true,
//     syntactic: true,
//     structural: true,
//     semantic: true,
//     rhetorical: true,
//   });

//   // State for model configuration
//   const [modelConfig, setModelConfig] = useState({
//     sampleSize: 50,
//     featureWeight: 0.7,
//     complexityLevel: "medium",
//     creativityLevel: 0.5,
//     maxTokens: 500,
//   });

//   // State for selected preset
//   const [selectedPreset, setSelectedPreset] = useState<string | null>(null);

//   // State for process status
//   const [analysisStatus, setAnalysisStatus] = useState({
//     isAnalyzing: false,
//     progress: 0,
//     isComplete: false,
//   });

//   const [trainingStatus, setTrainingStatus] = useState({
//     isTraining: false,
//     progress: 0,
//     isComplete: false,
//   });

//   const [generationStatus, setGenerationStatus] = useState({
//     isGenerating: false,
//     isComplete: false,
//   });

//   // State for results
//   const [featureResults, setFeatureResults] = useState({
//     lexical: SAMPLE_LEXICAL_FEATURES,
//     syntactic: SAMPLE_SYNTACTIC_FEATURES,
//     structural: SAMPLE_STRUCTURAL_FEATURES,
//     semantic: SAMPLE_SEMANTIC_FEATURES,
//     rhetorical: SAMPLE_RHETORICAL_FEATURES,
//   });

//   const [generatedText, setGeneratedText] = useState("");

//   // State for saved profiles
//   const [savedProfiles, setSavedProfiles] = useState(SAMPLE_AUTHOR_PROFILES);
//   const [selectedProfile, setSelectedProfile] = useState<string | null>(null);
//   const [checkedProfiles, setCheckedProfiles] = useState<string[]>([]);
//   const [newProfileName, setNewProfileName] = useState("");

//   // State for UI sections - use the props for default values
//   const [isWritingSamplesOpen, setIsWritingSamplesOpen] = useState(
//     defaultOpenSections.writingSamples ?? true
//   );
//   const [isConfigOpen, setIsConfigOpen] = useState(
//     defaultOpenSections.modelConfig ?? false
//   );
//   const [isResultsOpen, setIsResultsOpen] = useState(
//     defaultOpenSections.results ?? false
//   );
//   const [isProfilesOpen, setIsProfilesOpen] = useState(
//     defaultOpenSections.profiles ?? true
//   );

//   // Refs for scrolling
//   const configSectionRef = useRef<HTMLDivElement>(null);
//   const resultsSectionRef = useRef<HTMLDivElement>(null);

//   // Add a new state for the confirmation modal
//   const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
//   const [selectedPersonalityName, setSelectedPersonalityName] = useState("");

//   // Check if any sample is uploaded
//   const hasAnySample = writingSamples.some(
//     (sample) => sample.isUploaded || sample.text.trim().length > 0
//   );

//   // Handle text input for a sample
//   const handleSampleTextChange = (id: number, text: string) => {
//     setWritingSamples((prev) =>
//       prev.map((sample) => (sample.id === id ? { ...sample, text } : sample))
//     );
//   };

//   // Handle text sample submission
//   const handleSubmitTextSample = (id: number) => {
//     setWritingSamples((prev) =>
//       prev.map((sample) =>
//         sample.id === id && sample.text.trim().length > 0
//           ? { ...sample, isUploaded: true }
//           : sample
//       )
//     );
//   };

//   // Handle file upload for a sample
//   const handleFileChange = (
//     id: number,
//     event: React.ChangeEvent<HTMLInputElement>
//   ) => {
//     if (event.target.files && event.target.files[0]) {
//       setWritingSamples((prev) =>
//         prev.map((sample) =>
//           sample.id === id
//             ? { ...sample, file: event.target.files![0], isUploaded: true }
//             : sample
//         )
//       );
//     }
//   };

//   // Handle feature selection
//   const handleFeatureChange = (feature: keyof typeof selectedFeatures) => {
//     setSelectedFeatures({
//       ...selectedFeatures,
//       [feature]: !selectedFeatures[feature],
//     });
//   };

//   // Handle model configuration changes
//   const handleModelConfigChange = (
//     key: keyof typeof modelConfig,
//     value: number | string
//   ) => {
//     setModelConfig({
//       ...modelConfig,
//       [key]: value,
//     });
//     setSelectedPreset(null); // Clear preset selection when manually changing settings
//   };

//   // Handle preset selection
//   const handlePresetChange = (presetName: string) => {
//     const preset = MODEL_PRESETS.find((p) => p.name === presetName);
//     if (preset) {
//       setModelConfig(preset);
//       setSelectedPreset(presetName);
//     }
//   };

//   // Simulate analysis process
//   const handleAnalyze = async () => {
//     if (!hasAnySample) return;

//     setAnalysisStatus({
//       isAnalyzing: true,
//       progress: 0,
//       isComplete: false,
//     });

//     // Simulate progress
//     for (let i = 0; i <= 100; i += 5) {
//       await new Promise((resolve) => setTimeout(resolve, 100));
//       setAnalysisStatus((prev) => ({
//         ...prev,
//         progress: i,
//       }));
//     }

//     setAnalysisStatus({
//       isAnalyzing: false,
//       progress: 100,
//       isComplete: true,
//     });

//     // Open results section
//     setIsResultsOpen(true);
//     setTimeout(() => {
//       resultsSectionRef.current?.scrollIntoView({ behavior: "smooth" });
//     }, 100);
//   };

//   // Simulate training process
//   const handleTrain = async () => {
//     if (!analysisStatus.isComplete) return;

//     setTrainingStatus({
//       isTraining: true,
//       progress: 0,
//       isComplete: false,
//     });

//     // Simulate progress
//     for (let i = 0; i <= 100; i += 5) {
//       await new Promise((resolve) => setTimeout(resolve, 100));
//       setTrainingStatus((prev) => ({
//         ...prev,
//         progress: i,
//       }));
//     }

//     setTrainingStatus({
//       isTraining: false,
//       progress: 100,
//       isComplete: true,
//     });
//   };

//   // Simulate text generation
//   const handleGenerate = async () => {
//     if (!trainingStatus.isComplete) return;

//     setGenerationStatus({
//       isGenerating: true,
//       isComplete: false,
//     });

//     // Simulate API call
//     await new Promise((resolve) => setTimeout(resolve, 2000));

//     setGeneratedText(
//       "The sun rose over the distant hills, casting long shadows across the valley. John watched from his porch, coffee in hand, contemplating the day ahead. The morning air was crisp, carrying the scent of pine and possibility. He had waited for this moment, this perfect stillness before the world fully awakened. Today would be different, he decided. Today would be the day everything changed.\n\nHe took a sip of coffee, savoring the bitter warmth as it spread through him. The newspaper lay unopened on the table beside him, its headlines screaming of a world in chaos. But here, in this moment, there was only peace. The birds began their morning chorus, a symphony of chirps and calls that seemed to celebrate the new day.\n\nJohn's thoughts drifted to the letter in his pocket. He'd read it a dozen times since yesterday, memorizing every word, every curve of her handwriting. After fifteen years, she wanted to meet. Fifteen years of silence, and now this. He wasn't sure if he was ready, but he knew he couldn't refuse. Some doors, once opened, couldn't be closed again."
//     );

//     setGenerationStatus({
//       isGenerating: false,
//       isComplete: true,
//     });
//   };

//   // Handle saving a profile
//   const handleSaveProfile = () => {
//     console.log("newProfileName", newProfileName);
//     if (!analysisStatus.isComplete || !newProfileName.trim()) return;

//     const newProfile = {
//       id: Date.now().toString(),
//       name: newProfileName.trim(),
//       description: `Based on ${writingSamples.filter((s) => s.isUploaded).length
//         } writing samples`,
//     };

//     setSavedProfiles([...savedProfiles, newProfile]);
//     setSelectedProfile(newProfile.id);
//     setNewProfileName("");
//   };

//   // Handle loading a profile
//   const handleLoadProfile = (profileId: string) => {
//     console.log("sd");
//     setSelectedProfile(profileId);

//     // Simulate loading profile data
//     setAnalysisStatus({
//       isAnalyzing: false,
//       progress: 100,
//       isComplete: true,
//     });

//     setTrainingStatus({
//       isTraining: false,
//       progress: 100,
//       isComplete: true,
//     });

//     // Open results section
//     setIsResultsOpen(true);
//     setTimeout(() => {
//       resultsSectionRef.current?.scrollIntoView({ behavior: "smooth" });
//     }, 100);
//   };

//   // Handle profile checkbox selection
//   const handleProfileCheckChange = (profileId: string) => {
//     console.log("asdas", profileId);
//     setCheckedProfiles((prev) => {
//       if (prev.includes(profileId)) {
//         return prev.filter((id) => id !== profileId);
//       } else {
//         return [...prev, profileId];
//       }
//     });
//   };

//   // Replace the handleSelectProfile function with this updated version
//   const handleSelectProfile = () => {
//     if (checkedProfiles.length === 1) {
//       const selectedProfile = savedProfiles.find(
//         (p) => p.id === checkedProfiles[0]
//       );
//       if (selectedProfile) {
//         // Save to localStorage
//         const data = localStorage.getItem("contentGenPayload") || "{}";
//         const parsed = JSON.parse(data);
//         const newData = { ...parsed, author: selectedProfile.name };

//         localStorage.setItem("contentGenPayload", JSON.stringify(newData));

//         // Set personality name and open modal
//         setSelectedPersonalityName(selectedProfile.name);
//         setIsConfirmModalOpen(true);
//       }
//     }
//   };

//   // Add a new function to handle the confirmation
//   const handleConfirmSelection = () => {
//     // In a real app, this would apply the selected profile
//     // For now we'll just close the modal and clear the selection
//     setIsConfirmModalOpen(false);
//     setCheckedProfiles([]);
//   };

//   // Handle deleting a profile
//   const handleDeleteProfile = (profileId: string, e: React.MouseEvent) => {
//     e.stopPropagation();
//     setSavedProfiles(
//       savedProfiles.filter((profile) => profile.id !== profileId)
//     );
//     if (selectedProfile === profileId) {
//       setSelectedProfile(null);
//     }
//     if (checkedProfiles.includes(profileId)) {
//       setCheckedProfiles((prev) => prev.filter((id) => id !== profileId));
//     }
//   };

//   // Handle regenerating text
//   const handleRegenerateText = async () => {
//     setGenerationStatus({
//       isGenerating: true,
//       isComplete: false,
//     });

//     // Simulate API call
//     await new Promise((resolve) => setTimeout(resolve, 1500));

//     setGeneratedText(
//       "The rain fell steadily against the windowpane, creating a rhythmic pattern that matched her heartbeat. Sarah closed her book and gazed outside, watching the world transform under the downpour. There was something cleansing about the rain, washing away the past and nourishing new beginnings. She made her decision then, as the storm intensified. It was time to embrace change, to step into the unknown with courage and determination.\n\nThe letter sat on her desk, the edges crisp and white against the dark wood. She hadn't opened it yet, though it had arrived three days ago. Some part of her knew that once she broke the seal, nothing would be the same. The sender's name was printed in the corner, a name she hadn't seen in years but had never truly forgotten.\n\nSarah stood and walked to the window, pressing her palm against the cool glass. The city beyond was blurred by the rain, buildings reduced to hazy outlines and lights to soft glows. Like memories, she thought, clear in essence but fuzzy around the edges. She turned back to the desk, her mind made up. It was time to read what he had to say."
//     );

//     setGenerationStatus({
//       isGenerating: false,
//       isComplete: true,
//     });
//   };

//   useEffect(() => {
//     const data = localStorage.getItem("contentGenPayload") || "{}";
//     const parsed = JSON.parse(data);
//     const savedAuthor = parsed.author;

//     if (savedAuthor) {
//       const matchedProfile = savedProfiles.find(
//         (profile) => profile.name === savedAuthor
//       );
//       if (matchedProfile) {
//         setCheckedProfiles([matchedProfile.id]);
//         setSelectedProfile(matchedProfile.id);
//         setSelectedPersonalityName(matchedProfile.name);
//       }
//     }
//   }, [savedProfiles]); // Run this after savedProfiles are available

//   return (
//     <div className="space-y-6">
//       {/* Conditionally render the Saved Author Profiles Section */}
//       {showSavedProfiles && (
//         <Card>
//           <Collapsible open={isProfilesOpen} onOpenChange={setIsProfilesOpen}>
//             <CollapsibleTrigger asChild>
//               <CardHeader className="cursor-pointer">
//                 <CardTitle className="flex items-center">
//                   <BookOpen className="mr-2 h-5 w-5" />
//                   Saved Author Profiles d
//                 </CardTitle>
//               </CardHeader>
//             </CollapsibleTrigger>
//             <CollapsibleContent>
//               <CardContent>
//                 {savedProfiles.length > 0 ? (
//                   <div className="space-y-4">
//                     <div className="space-y-2">
//                       {savedProfiles.map((profile) => (
//                         <div
//                           key={profile.id}
//                           className={`p-3 border rounded-md flex items-center justify-between ${selectedProfile === profile.id
//                             ? "bg-gray-100 border-gray-400"
//                             : "hover:bg-gray-50"
//                             }`}
//                         >
//                           <div className="flex items-center space-x-3">
//                             <Checkbox
//                               id={`profile-${profile.id}`}
//                               checked={checkedProfiles.includes(profile.id)}
//                               onCheckedChange={() =>  
//                                 handleProfileCheckChange(profile.id)
//                               }
//                               className="h-5 w-5"
//                             />
//                             <div
//                               className="cursor-pointer"
//                               onClick={() => handleLoadProfile(profile.id)}
//                             >
//                               <h4 className="font-medium">{profile.name}</h4>
//                               <p className="text-sm text-gray-500">
//                                 {profile.description}
//                               </p>
//                             </div>
//                           </div>
//                           <Button
//                             variant="ghost"
//                             size="sm"
//                             onClick={(e) => handleDeleteProfile(profile.id, e)}
//                             className="opacity-70 hover:opacity-100"
//                           >
//                             <Trash2 className="h-4 w-4 text-red-500" />
//                           </Button>
//                         </div>
//                       ))}
//                     </div>

//                     <div className="flex justify-end">
//                       <Button
//                         onClick={handleSelectProfile}
//                         disabled={checkedProfiles.length !== 1}
//                         className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
//                       >
//                         <User className="mr-2 h-4 w-4" />
//                         Use Selected Personality
//                       </Button>
//                     </div>
//                   </div>
//                 ) : (
//                   <div className="text-center py-8 text-gray-500">
//                     <BookOpen className="mx-auto h-12 w-12 text-gray-300 mb-2" />
//                     <p>No saved author profiles yet</p>
//                     <p className="text-sm">
//                       Analyze text and save profiles to see them here
//                     </p>
//                   </div>
//                 )}
//               </CardContent>
//             </CollapsibleContent>
//           </Collapsible>
//         </Card>
//       )}

//       {/* Writing Samples Section */}
//       <Card>
//         <Collapsible
//           open={isWritingSamplesOpen}
//           onOpenChange={setIsWritingSamplesOpen}
//         >
//           <CollapsibleTrigger asChild>
//             <CardHeader className="cursor-pointer">
//               <CardTitle className="flex items-center">
//                 <FileText className="mr-2 h-5 w-5" />
//                 Writing Samples
//               </CardTitle>
//             </CardHeader>
//           </CollapsibleTrigger>
//           <CollapsibleContent>
//             <CardContent className="space-y-6">
//               <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
//                 {/* First row of 5 samples */}
//                 {writingSamples.slice(0, 5).map((sample) => (
//                   <div
//                     key={sample.id}
//                     className="space-y-2 border rounded-md p-4"
//                   >
//                     <div className="flex items-center justify-between">
//                       <Label
//                         htmlFor={`sample-${sample.id}`}
//                         className="font-medium flex items-center"
//                       >
//                         Writing Sample {sample.id}
//                         {sample.isUploaded && (
//                           <Check className="ml-2 h-4 w-4 text-green-500" />
//                         )}
//                       </Label>
//                     </div>
//                     <Textarea
//                       id={`sample-${sample.id}`}
//                       placeholder={`Enter sample text #${sample.id}...`}
//                       className={`min-h-[100px] ${sample.isUploaded ? "border-green-500" : ""
//                         }`}
//                       value={sample.text}
//                       onChange={(e) =>
//                         handleSampleTextChange(sample.id, e.target.value)
//                       }
//                     />
//                     <div className="flex space-x-2">
//                       <Button
//                         type="button"
//                         variant="outline"
//                         size="sm"
//                         className={`flex-1 ${sample.isUploaded && sample.text
//                           ? "border-green-500 text-green-600"
//                           : ""
//                           }`}
//                         onClick={() => handleSubmitTextSample(sample.id)}
//                         disabled={!sample.text.trim()}
//                       >
//                         {sample.isUploaded && sample.text ? (
//                           <>
//                             <Check className="mr-1 h-4 w-4" />
//                             Saved
//                           </>
//                         ) : (
//                           <>
//                             <FileText className="mr-1 h-4 w-4" />
//                             Save Text
//                           </>
//                         )}
//                       </Button>
//                       <div className="relative flex-1">
//                         <Input
//                           id={`file-${sample.id}`}
//                           type="file"
//                           accept=".txt,.doc,.docx,.pdf"
//                           onChange={(e) => handleFileChange(sample.id, e)}
//                           className="absolute inset-0 opacity-0 cursor-pointer"
//                         />
//                         <Button
//                           type="button"
//                           variant="outline"
//                           size="sm"
//                           className={`w-full ${sample.file ? "border-green-500 text-green-600" : ""
//                             }`}
//                         >
//                           {sample.file ? (
//                             <>
//                               <Check className="mr-1 h-4 w-4" />
//                               Uploaded
//                             </>
//                           ) : (
//                             <>
//                               <Upload className="mr-1 h-4 w-4" />
//                               Upload
//                             </>
//                           )}
//                         </Button>
//                       </div>
//                     </div>
//                     {sample.file && (
//                       <p className="text-xs text-green-600 truncate">
//                         File: {sample.file.name}
//                       </p>
//                     )}
//                   </div>
//                 ))}

//                 {/* Second row of 5 samples */}
//                 {writingSamples.slice(5, 10).map((sample) => (
//                   <div
//                     key={sample.id}
//                     className="space-y-2 border rounded-md p-4"
//                   >
//                     <div className="flex items-center justify-between">
//                       <Label
//                         htmlFor={`sample-${sample.id}`}
//                         className="font-medium flex items-center"
//                       >
//                         Writing Sample {sample.id}
//                         {sample.isUploaded && (
//                           <Check className="ml-2 h-4 w-4 text-green-500" />
//                         )}
//                       </Label>
//                     </div>
//                     <Textarea
//                       id={`sample-${sample.id}`}
//                       placeholder={`Enter sample text #${sample.id}...`}
//                       className={`min-h-[100px] ${sample.isUploaded ? "border-green-500" : ""
//                         }`}
//                       value={sample.text}
//                       onChange={(e) =>
//                         handleSampleTextChange(sample.id, e.target.value)
//                       }
//                     />
//                     <div className="flex space-x-2">
//                       <Button
//                         type="button"
//                         variant="outline"
//                         size="sm"
//                         className={`flex-1 ${sample.isUploaded && sample.text
//                           ? "border-green-500 text-green-600"
//                           : ""
//                           }`}
//                         onClick={() => handleSubmitTextSample(sample.id)}
//                         disabled={!sample.text.trim()}
//                       >
//                         {sample.isUploaded && sample.text ? (
//                           <>
//                             <Check className="mr-1 h-4 w-4" />
//                             Saved
//                           </>
//                         ) : (
//                           <>
//                             <FileText className="mr-1 h-4 w-4" />
//                             Save Text
//                           </>
//                         )}
//                       </Button>
//                       <div className="relative flex-1">
//                         <Input
//                           id={`file-${sample.id}`}
//                           type="file"
//                           accept=".txt,.doc,.docx,.pdf"
//                           onChange={(e) => handleFileChange(sample.id, e)}
//                           className="absolute inset-0 opacity-0 cursor-pointer"
//                         />
//                         <Button
//                           type="button"
//                           variant="outline"
//                           size="sm"
//                           className={`w-full ${sample.file ? "border-green-500 text-green-600" : ""
//                             }`}
//                         >
//                           {sample.file ? (
//                             <>
//                               <Check className="mr-1 h-4 w-4" />
//                               Uploaded
//                             </>
//                           ) : (
//                             <>
//                               <Upload className="mr-1 h-4 w-4" />
//                               Upload
//                             </>
//                           )}
//                         </Button>
//                       </div>
//                     </div>
//                     {sample.file && (
//                       <p className="text-xs text-green-600 truncate">
//                         File: {sample.file.name}
//                       </p>
//                     )}
//                   </div>
//                 ))}
//               </div>

//               <div className="space-y-2">
//                 <Label>Feature Selection</Label>
//                 <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
//                   <div className="flex items-center space-x-2">
//                     <Checkbox
//                       id="lexical"
//                       checked={selectedFeatures.lexical}
//                       onCheckedChange={() => handleFeatureChange("lexical")}
//                     />
//                     <Label htmlFor="lexical" className="cursor-pointer">
//                       Lexical Features
//                     </Label>
//                   </div>
//                   <div className="flex items-center space-x-2">
//                     <Checkbox
//                       id="syntactic"
//                       checked={selectedFeatures.syntactic}
//                       onCheckedChange={() => handleFeatureChange("syntactic")}
//                     />
//                     <Label htmlFor="syntactic" className="cursor-pointer">
//                       Syntactic Patterns
//                     </Label>
//                   </div>
//                   <div className="flex items-center space-x-2">
//                     <Checkbox
//                       id="structural"
//                       checked={selectedFeatures.structural}
//                       onCheckedChange={() => handleFeatureChange("structural")}
//                     />
//                     <Label htmlFor="structural" className="cursor-pointer">
//                       Structural Elements
//                     </Label>
//                   </div>
//                   <div className="flex items-center space-x-2">
//                     <Checkbox
//                       id="semantic"
//                       checked={selectedFeatures.semantic}
//                       onCheckedChange={() => handleFeatureChange("semantic")}
//                     />
//                     <Label htmlFor="semantic" className="cursor-pointer">
//                       Semantic Characteristics
//                     </Label>
//                   </div>
//                   <div className="flex items-center space-x-2">
//                     <Checkbox
//                       id="rhetorical"
//                       checked={selectedFeatures.rhetorical}
//                       onCheckedChange={() => handleFeatureChange("rhetorical")}
//                     />
//                     <Label htmlFor="rhetorical" className="cursor-pointer">
//                       Rhetorical Devices
//                     </Label>
//                   </div>
//                 </div>
//               </div>

//               <Button
//                 onClick={handleAnalyze}
//                 className={`w-full ${hasAnySample
//                   ? "bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
//                   : "bg-gray-300 text-gray-600 cursor-not-allowed"
//                   }`}
//                 disabled={analysisStatus.isAnalyzing || !hasAnySample}
//               >
//                 {analysisStatus.isAnalyzing ? (
//                   <>
//                     <svg
//                       className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
//                       xmlns="http://www.w3.org/2000/svg"
//                       fill="none"
//                       viewBox="0 0 24 24"
//                     >
//                       <circle
//                         className="opacity-25"
//                         cx="12"
//                         cy="12"
//                         r="10"
//                         stroke="currentColor"
//                         strokeWidth="4"
//                       ></circle>
//                       <path
//                         className="opacity-75"
//                         fill="currentColor"
//                         d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
//                       ></path>
//                     </svg>
//                     Analyzing...
//                   </>
//                 ) : (
//                   <>
//                     <BarChart className="mr-2 h-5 w-5" />
//                     Analyze Features
//                   </>
//                 )}
//               </Button>

//               {analysisStatus.isAnalyzing && (
//                 <div className="space-y-2">
//                   <div className="flex justify-between text-sm">
//                     <span>Analyzing text features</span>
//                     <span>{analysisStatus.progress}%</span>
//                   </div>
//                   <Progress value={analysisStatus.progress} />
//                 </div>
//               )}
//             </CardContent>
//           </CollapsibleContent>
//         </Collapsible>
//       </Card>

//       {/* Model Configuration Section */}
//       <Card ref={configSectionRef}>
//         <Collapsible open={isConfigOpen} onOpenChange={setIsConfigOpen}>
//           <CollapsibleTrigger asChild>
//             <CardHeader className="cursor-pointer">
//               <CardTitle className="flex items-center">
//                 <Brain className="mr-2 h-5 w-5" />
//                 Model Configuration
//               </CardTitle>
//             </CardHeader>
//           </CollapsibleTrigger>
//           <CollapsibleContent>
//             <CardContent className="space-y-4">
//               <div className="space-y-2">
//                 <Label htmlFor="preset">Configuration Preset</Label>
//                 <Select
//                   value={selectedPreset || ""}
//                   onValueChange={handlePresetChange}
//                 >
//                   <SelectTrigger id="preset">
//                     <SelectValue placeholder="Select a preset or customize below" />
//                   </SelectTrigger>
//                   <SelectContent>
//                     <SelectItem value="custom">Custom Configuration</SelectItem>
//                     {MODEL_PRESETS.map((preset) => (
//                       <SelectItem key={preset.name} value={preset.name}>
//                         {preset.name}
//                       </SelectItem>
//                     ))}
//                   </SelectContent>
//                 </Select>
//                 <p className="text-xs text-muted-foreground">
//                   Choose a preset or customize the settings below
//                 </p>
//               </div>

//               <div className="space-y-2">
//                 <div className="flex justify-between">
//                   <Label htmlFor="sample-size">Sample Size</Label>
//                   <span className="text-sm text-muted-foreground">
//                     {modelConfig.sampleSize}%
//                   </span>
//                 </div>
//                 <Slider
//                   id="sample-size"
//                   min={10}
//                   max={100}
//                   step={10}
//                   value={[modelConfig.sampleSize]}
//                   onValueChange={(value) =>
//                     handleModelConfigChange("sampleSize", value[0])
//                   }
//                 />
//                 <p className="text-xs text-muted-foreground">
//                   Percentage of input text to use for training (higher = more
//                   accurate but slower)
//                 </p>
//               </div>

//               <div className="space-y-2">
//                 <div className="flex justify-between">
//                   <Label htmlFor="feature-weight">Feature Weight</Label>
//                   <span className="text-sm text-muted-foreground">
//                     {modelConfig.featureWeight.toFixed(1)}
//                   </span>
//                 </div>
//                 <Slider
//                   id="feature-weight"
//                   min={0.1}
//                   max={1.0}
//                   step={0.1}
//                   value={[modelConfig.featureWeight]}
//                   onValueChange={(value) =>
//                     handleModelConfigChange("featureWeight", value[0])
//                   }
//                 />
//                 <p className="text-xs text-muted-foreground">
//                   How strongly to enforce author style (higher = more similar to
//                   original)
//                 </p>
//               </div>

//               <div className="space-y-2">
//                 <Label htmlFor="complexity-level">Complexity Level</Label>
//                 <Select
//                   value={modelConfig.complexityLevel}
//                   onValueChange={(value) =>
//                     handleModelConfigChange("complexityLevel", value)
//                   }
//                 >
//                   <SelectTrigger id="complexity-level">
//                     <SelectValue placeholder="Select complexity" />
//                   </SelectTrigger>
//                   <SelectContent>
//                     <SelectItem value="simple">Simple</SelectItem>
//                     <SelectItem value="medium">Medium</SelectItem>
//                     <SelectItem value="complex">Complex</SelectItem>
//                     <SelectItem value="very-complex">Very Complex</SelectItem>
//                   </SelectContent>
//                 </Select>
//                 <p className="text-xs text-muted-foreground">
//                   Determines sentence and paragraph complexity in generated text
//                 </p>
//               </div>

//               <div className="space-y-2">
//                 <div className="flex justify-between">
//                   <Label htmlFor="creativity-level">Creativity Level</Label>
//                   <span className="text-sm text-muted-foreground">
//                     {modelConfig.creativityLevel.toFixed(1)}
//                   </span>
//                 </div>
//                 <Slider
//                   id="creativity-level"
//                   min={0.1}
//                   max={1.0}
//                   step={0.1}
//                   value={[modelConfig.creativityLevel]}
//                   onValueChange={(value) =>
//                     handleModelConfigChange("creativityLevel", value[0])
//                   }
//                 />
//                 <p className="text-xs text-muted-foreground">
//                   Controls randomness in generation (higher = more creative but
//                   less predictable)
//                 </p>
//               </div>

//               <div className="space-y-2">
//                 <div className="flex justify-between">
//                   <Label htmlFor="max-tokens">Max Tokens</Label>
//                   <span className="text-sm text-muted-foreground">
//                     {modelConfig.maxTokens}
//                   </span>
//                 </div>
//                 <Slider
//                   id="max-tokens"
//                   min={100}
//                   max={2000}
//                   step={100}
//                   value={[modelConfig.maxTokens]}
//                   onValueChange={(value) =>
//                     handleModelConfigChange("maxTokens", value[0])
//                   }
//                 />
//                 <p className="text-xs text-muted-foreground">
//                   Maximum length of generated text (approximately{" "}
//                   {Math.round(modelConfig.maxTokens / 4)} words)
//                 </p>
//               </div>

//               <Button
//                 onClick={handleTrain}
//                 className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
//                 disabled={
//                   trainingStatus.isTraining || !analysisStatus.isComplete
//                 }
//               >
//                 {trainingStatus.isTraining ? (
//                   <>
//                     <svg
//                       className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
//                       xmlns="http://www.w3.org/2000/svg"
//                       fill="none"
//                       viewBox="0 0 24 24"
//                     >
//                       <circle
//                         className="opacity-25"
//                         cx="12"
//                         cy="12"
//                         r="10"
//                         stroke="currentColor"
//                         strokeWidth="4"
//                       ></circle>
//                       <path
//                         className="opacity-75"
//                         fill="currentColor"
//                         d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
//                       ></path>
//                     </svg>
//                     Training...
//                   </>
//                 ) : (
//                   <>
//                     <Sparkles className="mr-2 h-5 w-5" />
//                     Train Model
//                   </>
//                 )}
//               </Button>

//               {trainingStatus.isTraining && (
//                 <div className="space-y-2">
//                   <div className="flex justify-between text-sm">
//                     <span>Training model</span>
//                     <span>{trainingStatus.progress}%</span>
//                   </div>
//                   <Progress value={trainingStatus.progress} />
//                 </div>
//               )}
//             </CardContent>
//           </CollapsibleContent>
//         </Collapsible>
//       </Card>

//       {/* Results Section */}
//       <Card ref={resultsSectionRef}>
//         <Collapsible open={isResultsOpen} onOpenChange={setIsResultsOpen}>
//           <CollapsibleTrigger asChild>
//             <CardHeader className="cursor-pointer">
//               <CardTitle className="flex items-center">
//                 <BarChart className="mr-2 h-5 w-5" />
//                 Analysis Results & Generated Text
//               </CardTitle>
//             </CardHeader>
//           </CollapsibleTrigger>
//           <CollapsibleContent>
//             <CardContent className="space-y-6">
//               {analysisStatus.isComplete && (
//                 <div className="space-y-4">
//                   <h3 className="text-lg font-medium">Feature Analysis</h3>

//                   <Tabs defaultValue="lexical">
//                     <TabsList className="w-full">
//                       <TabsTrigger
//                         value="lexical"
//                         disabled={!selectedFeatures.lexical}
//                       >
//                         Lexical
//                       </TabsTrigger>
//                       <TabsTrigger
//                         value="syntactic"
//                         disabled={!selectedFeatures.syntactic}
//                       >
//                         Syntactic
//                       </TabsTrigger>
//                       <TabsTrigger
//                         value="structural"
//                         disabled={!selectedFeatures.structural}
//                       >
//                         Structural
//                       </TabsTrigger>
//                       <TabsTrigger
//                         value="semantic"
//                         disabled={!selectedFeatures.semantic}
//                       >
//                         Semantic
//                       </TabsTrigger>
//                       <TabsTrigger
//                         value="rhetorical"
//                         disabled={!selectedFeatures.rhetorical}
//                       >
//                         Rhetorical
//                       </TabsTrigger>
//                     </TabsList>

//                     <TabsContent value="lexical" className="pt-4">
//                       <div className="space-y-4">
//                         {featureResults.lexical.map((feature, index) => (
//                           <div key={index} className="space-y-1">
//                             <div className="flex justify-between">
//                               <span className="font-medium">
//                                 {feature.name}
//                               </span>
//                               <span>{feature.value}</span>
//                             </div>
//                             <div className="relative h-2 w-full bg-gray-200 rounded-full overflow-hidden">
//                               <div
//                                 className="absolute top-0 left-0 h-full bg-[#3d545f]"
//                                 style={{ width: `${feature.percentile}%` }}
//                               ></div>
//                             </div>
//                             <div className="flex justify-between text-xs text-gray-500">
//                               <span>0%</span>
//                               <span>Percentile: {feature.percentile}%</span>
//                               <span>100%</span>
//                             </div>
//                           </div>
//                         ))}
//                       </div>
//                     </TabsContent>

//                     <TabsContent value="syntactic" className="pt-4">
//                       <div className="space-y-4">
//                         {featureResults.syntactic.map((feature, index) => (
//                           <div key={index} className="space-y-1">
//                             <div className="flex justify-between">
//                               <span className="font-medium">
//                                 {feature.name}
//                               </span>
//                               <span>{feature.value}</span>
//                             </div>
//                             <div className="relative h-2 w-full bg-gray-200 rounded-full overflow-hidden">
//                               <div
//                                 className="absolute top-0 left-0 h-full bg-[#3d545f]"
//                                 style={{ width: `${feature.percentile}%` }}
//                               ></div>
//                             </div>
//                             <div className="flex justify-between text-xs text-gray-500">
//                               <span>0%</span>
//                               <span>Percentile: {feature.percentile}%</span>
//                               <span>100%</span>
//                             </div>
//                           </div>
//                         ))}
//                       </div>
//                     </TabsContent>

//                     <TabsContent value="structural" className="pt-4">
//                       <div className="space-y-4">
//                         {featureResults.structural.map((feature, index) => (
//                           <div key={index} className="space-y-1">
//                             <div className="flex justify-between">
//                               <span className="font-medium">
//                                 {feature.name}
//                               </span>
//                               <span>{feature.value}</span>
//                             </div>
//                             <div className="relative h-2 w-full bg-gray-200 rounded-full overflow-hidden">
//                               <div
//                                 className="absolute top-0 left-0 h-full bg-[#3d545f]"
//                                 style={{ width: `${feature.percentile}%` }}
//                               ></div>
//                             </div>
//                             <div className="flex justify-between text-xs text-gray-500">
//                               <span>0%</span>
//                               <span>Percentile: {feature.percentile}%</span>
//                               <span>100%</span>
//                             </div>
//                           </div>
//                         ))}
//                       </div>
//                     </TabsContent>

//                     <TabsContent value="semantic" className="pt-4">
//                       <div className="space-y-4">
//                         {featureResults.semantic.map((feature, index) => (
//                           <div key={index} className="space-y-1">
//                             <div className="flex justify-between">
//                               <span className="font-medium">
//                                 {feature.name}
//                               </span>
//                               <span>{feature.value}</span>
//                             </div>
//                             <div className="relative h-2 w-full bg-gray-200 rounded-full overflow-hidden">
//                               <div
//                                 className="absolute top-0 left-0 h-full bg-[#3d545f]"
//                                 style={{ width: `${feature.percentile}%` }}
//                               ></div>
//                             </div>
//                             <div className="flex justify-between text-xs text-gray-500">
//                               <span>0%</span>
//                               <span>Percentile: {feature.percentile}%</span>
//                               <span>100%</span>
//                             </div>
//                           </div>
//                         ))}
//                       </div>
//                     </TabsContent>

//                     <TabsContent value="rhetorical" className="pt-4">
//                       <div className="space-y-4">
//                         {featureResults.rhetorical.map((feature, index) => (
//                           <div key={index} className="space-y-1">
//                             <div className="flex justify-between">
//                               <span className="font-medium">
//                                 {feature.name}
//                               </span>
//                               <span>{feature.value}</span>
//                             </div>
//                             <div className="relative h-2 w-full bg-gray-200 rounded-full overflow-hidden">
//                               <div
//                                 className="absolute top-0 left-0 h-full bg-[#3d545f]"
//                                 style={{ width: `${feature.percentile}%` }}
//                               ></div>
//                             </div>
//                             <div className="flex justify-between text-xs text-gray-500">
//                               <span>0%</span>
//                               <span>Percentile: {feature.percentile}%</span>
//                               <span>100%</span>
//                             </div>
//                           </div>
//                         ))}
//                       </div>
//                     </TabsContent>
//                   </Tabs>
//                 </div>
//               )}

//               {trainingStatus.isComplete && (
//                 <div className="space-y-4">
//                   <div className="flex items-center justify-between">
//                     <h3 className="text-lg font-medium">Generated Text</h3>
//                     <Button
//                       variant="outline"
//                       size="sm"
//                       onClick={handleGenerate}
//                       disabled={generationStatus.isGenerating}
//                     >
//                       {generationStatus.isGenerating ? (
//                         <svg
//                           className="animate-spin h-4 w-4"
//                           xmlns="http://www.w3.org/2000/svg"
//                           fill="none"
//                           viewBox="0 0 24 24"
//                         >
//                           <circle
//                             className="opacity-25"
//                             cx="12"
//                             cy="12"
//                             r="10"
//                             stroke="currentColor"
//                             strokeWidth="4"
//                           ></circle>
//                           <path
//                             className="opacity-75"
//                             fill="currentColor"
//                             d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
//                           ></path>
//                         </svg>
//                       ) : (
//                         <PenTool className="h-4 w-4" />
//                       )}
//                     </Button>
//                   </div>

//                   {generationStatus.isComplete ? (
//                     <div className="space-y-4">
//                       <div className="p-4 border rounded-md bg-gray-50">
//                         <p className="whitespace-pre-line">{generatedText}</p>
//                       </div>

//                       <div className="flex space-x-2">
//                         <Button
//                           variant="outline"
//                           size="sm"
//                           onClick={handleRegenerateText}
//                           disabled={generationStatus.isGenerating}
//                           className="flex-1"
//                         >
//                           {generationStatus.isGenerating ? (
//                             <svg
//                               className="animate-spin -ml-1 mr-2 h-4 w-4"
//                               xmlns="http://www.w3.org/2000/svg"
//                               fill="none"
//                               viewBox="0 0 24 24"
//                             >
//                               <circle
//                                 className="opacity-25"
//                                 cx="12"
//                                 cy="12"
//                                 r="10"
//                                 stroke="currentColor"
//                                 strokeWidth="4"
//                               ></circle>
//                               <path
//                                 className="opacity-75"
//                                 fill="currentColor"
//                                 d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
//                               ></path>
//                             </svg>
//                           ) : (
//                             <RefreshCw className="mr-2 h-4 w-4" />
//                           )}
//                           Regenerate
//                         </Button>

//                         <Button variant="outline" size="sm" className="flex-1">
//                           <Save className="mr-2 h-4 w-4" />
//                           Save to Content Queue
//                         </Button>
//                       </div>
//                     </div>
//                   ) : (
//                     <div className="p-8 border rounded-md bg-gray-50 text-center text-gray-500">
//                       {generationStatus.isGenerating ? (
//                         <div className="flex flex-col items-center space-y-2">
//                           <svg
//                             className="animate-spin h-8 w-8 text-[#3d545f]"
//                             xmlns="http://www.w3.org/2000/svg"
//                             fill="none"
//                             viewBox="0 0 24 24"
//                           >
//                             <circle
//                               className="opacity-25"
//                               cx="12"
//                               cy="12"
//                               r="10"
//                               stroke="currentColor"
//                               strokeWidth="4"
//                             ></circle>
//                             <path
//                               className="opacity-75"
//                               fill="currentColor"
//                               d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
//                             ></path>
//                           </svg>
//                           <p>Generating text in author's style...</p>
//                         </div>
//                       ) : (
//                         <div className="flex flex-col items-center space-y-2">
//                           <Wand2 className="h-8 w-8 text-gray-400" />
//                           <p>
//                             Click "Generate" to create text in the author's
//                             style
//                           </p>
//                         </div>
//                       )}
//                     </div>
//                   )}
//                 </div>
//               )}

//               {analysisStatus.isComplete && (
//                 <div className="space-y-4 pt-4 border-t">
//                   <h3 className="text-lg font-medium">Save Author Profile</h3>
//                   <div className="flex space-x-2">
//                     <Input
//                       placeholder="Enter profile name"
//                       value={newProfileName}
//                       onChange={(e) => setNewProfileName(e.target.value)}
//                       className="flex-1"
//                     />
//                     <Button
//                       onClick={handleSaveProfile}
//                       disabled={!newProfileName.trim()}
//                       className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
//                     >
//                       <Bookmark className="mr-2 h-4 w-4" />
//                       Save Profile
//                     </Button>
//                   </div>
//                 </div>
//               )}

//               <div className="flex justify-between pt-4">
//                 <Button
//                   variant="outline"
//                   onClick={() => {
//                     setIsConfigOpen(true);
//                     setTimeout(() => {
//                       configSectionRef.current?.scrollIntoView({
//                         behavior: "smooth",
//                       });
//                     }, 100);
//                   }}
//                   disabled={!analysisStatus.isComplete}
//                 >
//                   <Layers className="mr-2 h-4 w-4" />
//                   Adjust Model
//                 </Button>
//               </div>
//             </CardContent>
//           </CollapsibleContent>
//         </Collapsible>
//       </Card>
//       {/* Add this right before the final closing div */}
//       <PersonalityConfirmationModal
//         isOpen={isConfirmModalOpen}
//         onClose={() => setIsConfirmModalOpen(false)}
//         onConfirm={handleConfirmSelection}
//         personalityName={selectedPersonalityName}
//       />
//     </div>
//   );
// }


"use client";

import type React from "react";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Upload,
  FileText,
  BarChart,
  Brain,
  Sparkles,
  RefreshCw,
  Save,
  BookOpen,
  Trash2,
  PenTool,
  Wand2,
  Layers,
  Bookmark,
  Check,
  User,
  Plus,
} from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

import { PersonalityConfirmationModal } from "./PersonalityConfirmationModal";
import { LoadingModal } from "./LoadingModal";
import { createAuthorPersonality } from "./AuthorPersonalityService";

const SAMPLE_AUTHOR_PROFILES = [
  {
    id: "1",
    name: "Ernest Hemingway",
    description: "Concise, direct prose with short sentences",
  },
  {
    id: "2",
    name: "Jane Austen",
    description: "Elegant, witty social commentary",
  },
  {
    id: "3",
    name: "David Foster Wallace",
    description: "Complex, footnote-heavy postmodern style",
  },
  {
    id: "4",
    name: "Stephen King",
    description: "Suspenseful, character-driven horror and thriller",
  },
  {
    id: "5",
    name: "Toni Morrison",
    description: "Poetic, rich with metaphor and cultural depth",
  },
];

const SAMPLE_LEXICAL_FEATURES = [
  { name: "Average Word Length", value: "4.8 characters", percentile: 68 },
  { name: "Vocabulary Richness", value: "0.72 (high)", percentile: 85 },
  { name: "Function Word Ratio", value: "0.38", percentile: 42 },
  { name: "Unique Words", value: "1,245", percentile: 76 },
  {
    name: "Word Frequency Distribution",
    value: "Power law (α=1.2)",
    percentile: 55,
  },
  { name: "Adjective Usage", value: "12% of content words", percentile: 63 },
  { name: "Adverb Frequency", value: "8% of content words", percentile: 47 },
  { name: "Noun-Verb Ratio", value: "1.4:1", percentile: 72 },
];

const SAMPLE_SYNTACTIC_FEATURES = [
  { name: "Average Sentence Length", value: "18.3 words", percentile: 62 },
  { name: "Clause Density", value: "2.4 per sentence", percentile: 78 },
  { name: "Passive Voice Usage", value: "12%", percentile: 35 },
  { name: "Punctuation Patterns", value: "Comma-heavy", percentile: 82 },
  {
    name: "Part-of-Speech Distribution",
    value: "Noun-dominant",
    percentile: 68,
  },
  {
    name: "Complex Sentence Ratio",
    value: "42% of all sentences",
    percentile: 76,
  },
  { name: "Question Frequency", value: "5% of sentences", percentile: 58 },
  {
    name: "Subordinate Clause Usage",
    value: "1.8 per paragraph",
    percentile: 65,
  },
];

const SAMPLE_STRUCTURAL_FEATURES = [
  { name: "Paragraph Length", value: "4.2 sentences", percentile: 58 },
  { name: "Discourse Markers", value: "Moderate usage", percentile: 65 },
  { name: "Topic Progression", value: "Linear", percentile: 72 },
  { name: "Rhetorical Structure", value: "Problem-Solution", percentile: 80 },
  { name: "Cohesion Score", value: "0.68 (medium-high)", percentile: 74 },
  {
    name: "Transition Word Frequency",
    value: "3.2 per paragraph",
    percentile: 67,
  },
  { name: "Paragraph Coherence", value: "Strong (0.81)", percentile: 88 },
  { name: "Narrative Structure", value: "Chronological", percentile: 70 },
];

const SAMPLE_SEMANTIC_FEATURES = [
  {
    name: "Sentiment Polarity",
    value: "Slightly positive (0.2)",
    percentile: 62,
  },
  { name: "Emotional Tone", value: "Reflective", percentile: 75 },
  { name: "Concreteness Rating", value: "Medium-high (0.68)", percentile: 64 },
  { name: "Subjectivity Score", value: "0.45 (balanced)", percentile: 52 },
  { name: "Metaphor Density", value: "1.8 per 100 words", percentile: 83 },
  { name: "Thematic Consistency", value: "High (0.85)", percentile: 91 },
  {
    name: "Semantic Field Diversity",
    value: "Moderate (0.62)",
    percentile: 58,
  },
];

const SAMPLE_RHETORICAL_FEATURES = [
  { name: "Persuasive Techniques", value: "Ethos-dominant", percentile: 77 },
  { name: "Rhetorical Questions", value: "1.2 per 500 words", percentile: 65 },
  { name: "Repetition Patterns", value: "Anaphora common", percentile: 82 },
  { name: "Irony/Sarcasm Detection", value: "Low (0.15)", percentile: 32 },
  { name: "Figurative Language", value: "Moderate usage", percentile: 58 },
  { name: "Appeal Types", value: "Logical > Emotional", percentile: 71 },
  {
    name: "Audience Engagement",
    value: "Direct address frequent",
    percentile: 84,
  },
];

const MODEL_PRESETS = [
  {
    name: "Balanced",
    sampleSize: 50,
    featureWeight: 0.7,
    complexityLevel: "medium",
    creativityLevel: 0.5,
    maxTokens: 500,
  },
  {
    name: "High Fidelity",
    sampleSize: 80,
    featureWeight: 0.9,
    complexityLevel: "complex",
    creativityLevel: 0.3,
    maxTokens: 800,
  },
  {
    name: "Creative Adaptation",
    sampleSize: 40,
    featureWeight: 0.5,
    complexityLevel: "medium",
    creativityLevel: 0.8,
    maxTokens: 600,
  },
  {
    name: "Simplified Style",
    sampleSize: 60,
    featureWeight: 0.8,
    complexityLevel: "simple",
    creativityLevel: 0.4,
    maxTokens: 400,
  },
  {
    name: "Complex Elaboration",
    sampleSize: 70,
    featureWeight: 0.6,
    complexityLevel: "very-complex",
    creativityLevel: 0.7,
    maxTokens: 1000,
  },
];

interface WritingSample {
  id: number;
  text: string;
  file: File | null;
  isUploaded: boolean;
}

interface AuthorMimicryProps {
  showSavedProfiles?: boolean;
  defaultOpenSections?: {
    writingSamples?: boolean;
    modelConfig?: boolean;
    results?: boolean;
    profiles?: boolean;
  };
  onSavePersonality?: (data: { name: string; description: string }) => void;
  initialPersonality?: {
    id: string;
    name: string;
    description: string;
  };
}

export function AuthorMimicry({
  showSavedProfiles = true,
  defaultOpenSections = {
    writingSamples: true,
    modelConfig: false,
    results: false,
    profiles: true,
  },
  onSavePersonality,
  initialPersonality,
}: AuthorMimicryProps) {
  const [writingSamples, setWritingSamples] = useState<WritingSample[]>(
    Array(10)
      .fill(null)
      .map((_, index) => ({
        id: index + 1,
        text: "",
        file: null,
        isUploaded: false,
      }))
  );

  const [visibleSamplesCount, setVisibleSamplesCount] = useState(1);

  const [selectedFeatures, setSelectedFeatures] = useState({
    lexical: true,
    syntactic: true,
    structural: true,
    semantic: true,
    rhetorical: true,
  });

  const [modelConfig, setModelConfig] = useState({
    sampleSize: 50,
    featureWeight: 0.7,
    complexityLevel: "medium",
    creativityLevel: 0.5,
    maxTokens: 500,
  });

  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);

  const [analysisStatus, setAnalysisStatus] = useState({
    isAnalyzing: false,
    progress: 0,
    isComplete: false,
  });

  const [trainingStatus, setTrainingStatus] = useState({
    isTraining: false,
    progress: 0,
    isComplete: false,
  });

  const [generationStatus, setGenerationStatus] = useState({
    isGenerating: false,
    isComplete: false,
  });

  const [featureResults, setFeatureResults] = useState({
    lexical: SAMPLE_LEXICAL_FEATURES,
    syntactic: SAMPLE_SYNTACTIC_FEATURES,
    structural: SAMPLE_STRUCTURAL_FEATURES,
    semantic: SAMPLE_SEMANTIC_FEATURES,
    rhetorical: SAMPLE_RHETORICAL_FEATURES,
  });

  const [generatedText, setGeneratedText] = useState("");

  const [savedProfiles, setSavedProfiles] = useState(SAMPLE_AUTHOR_PROFILES);
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null);
  const [checkedProfiles, setCheckedProfiles] = useState<string[]>([]);
  const [newProfileName, setNewProfileName] = useState(initialPersonality?.name || "");

  const [isWritingSamplesOpen, setIsWritingSamplesOpen] = useState(
    defaultOpenSections.writingSamples ?? true
  );
  const [isConfigOpen, setIsConfigOpen] = useState(
    defaultOpenSections.modelConfig ?? false
  );
  const [isResultsOpen, setIsResultsOpen] = useState(
    defaultOpenSections.results ?? false
  );
  const [isProfilesOpen, setIsProfilesOpen] = useState(
    defaultOpenSections.profiles ?? true
  );

  const configSectionRef = useRef<HTMLDivElement>(null);
  const resultsSectionRef = useRef<HTMLDivElement>(null);

  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [selectedPersonalityName, setSelectedPersonalityName] = useState("");

  const hasAnySample = writingSamples.some(
    (sample) => sample.isUploaded || sample.text.trim().length > 0
  );

  const handleSampleTextChange = (id: number, text: string) => {
    setWritingSamples((prev) =>
      prev.map((sample) => (sample.id === id ? { ...sample, text } : sample))
    );
  };

  const handleSubmitTextSample = (id: number) => {
    setWritingSamples((prev) =>
      prev.map((sample) =>
        sample.id === id && sample.text.trim().length > 0
          ? { ...sample, isUploaded: true }
          : sample
      )
    );
  };

  const handleFileChange = (
    id: number,
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (event.target.files && event.target.files[0]) {
      setWritingSamples((prev) =>
        prev.map((sample) =>
          sample.id === id
            ? { ...sample, file: event.target.files![0], isUploaded: true }
            : sample
        )
      );
    }
  };

  const handleAddWritingSample = () => {
    if (visibleSamplesCount < 10) {
      setVisibleSamplesCount(prev => prev + 1);
    }
  };

  const handleFeatureChange = (feature: keyof typeof selectedFeatures) => {
    setSelectedFeatures({
      ...selectedFeatures,
      [feature]: !selectedFeatures[feature],
    });
  };

  const handleModelConfigChange = (
    key: keyof typeof modelConfig,
    value: number | string
  ) => {
    setModelConfig({
      ...modelConfig,
      [key]: value,
    });
    setSelectedPreset(null);
  };

  const handlePresetChange = (presetName: string) => {
    const preset = MODEL_PRESETS.find((p) => p.name === presetName);
    if (preset) {
      setModelConfig(preset);
      setSelectedPreset(presetName);
    }
  };

  const handleAnalyze = async () => {
    if (!hasAnySample) return;

    setAnalysisStatus({
      isAnalyzing: true,
      progress: 0,
      isComplete: false,
    });

    for (let i = 0; i <= 100; i += 5) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      setAnalysisStatus((prev) => ({
        ...prev,
        progress: i,
      }));
    }

    setAnalysisStatus({
      isAnalyzing: false,
      progress: 100,
      isComplete: true,
    });

    setIsResultsOpen(true);
    setTimeout(() => {
      resultsSectionRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  const handleTrain = async () => {
    if (!analysisStatus.isComplete) return;

    setTrainingStatus({
      isTraining: true,
      progress: 0,
      isComplete: false,
    });

    const storedData = JSON.parse(localStorage.getItem("contentGenPayload") || "{}");
    const authorName = storedData.author || newProfileName.trim() || "Unnamed Author";

    // Create the payload
    const payload = {
      author: authorName,
      writingSamples: writingSamples
        .filter((sample) => sample.isUploaded && sample.text.trim().length > 0)
        .map((sample) => sample.text),
      lexicalFeatures: selectedFeatures.lexical,
      syntacticPatterns: selectedFeatures.syntactic,
      structuralElements: selectedFeatures.structural,
      semanticCharacteristics: selectedFeatures.semantic,
      rhetoricalDevices: selectedFeatures.rhetorical,
      configurationPreset: selectedPreset?.toLocaleLowerCase() || "balanced",
      sampleSize: modelConfig.sampleSize,
      featureWeight: modelConfig.featureWeight,
      complexityLevel: modelConfig.complexityLevel?.toLocaleLowerCase() || "medium",
      creativityLevel: modelConfig.creativityLevel,
      maxTokens: modelConfig.maxTokens,
    };

    // Save payload to localStorage
    localStorage.setItem("contentGenPayload", JSON.stringify(payload));

    // Simulate training progress
    for (let i = 0; i <= 100; i += 5) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      setTrainingStatus((prev) => ({
        isTraining: true,
        progress: i,
        isComplete: false,
      }));
    }

    setTrainingStatus({
      isTraining: false,
      progress: 100,
      isComplete: true,
    });
  };

  const handleGenerate = async () => {
    if (!trainingStatus.isComplete) return;

    setGenerationStatus({
      isGenerating: true,
      isComplete: false,
    });

    await new Promise((resolve) => setTimeout(resolve, 2000));

    setGeneratedText(
      "The sun rose over the distant hills, casting long shadows across the valley. John watched from his porch, coffee in hand, contemplating the day ahead. The morning air was crisp, carrying the scent of pine and possibility. He had waited for this moment, this perfect stillness before the world fully awakened. Today would be different, he decided. Today would be the day everything changed.\n\nHe took a sip of coffee, savoring the bitter warmth as it spread through him. The newspaper lay unopened on the table beside him, its headlines screaming of a world in chaos. But here, in this moment, there was only peace. The birds began their morning chorus, a symphony of chirps and calls that seemed to celebrate the new day.\n\nJohn's thoughts drifted to the letter in his pocket. He'd read it a dozen times since yesterday, memorizing every word, every curve of her handwriting. After fifteen years, she wanted to meet. Fifteen years of silence, and now this. He wasn't sure if he was ready, but he knew he couldn't refuse. Some doors, once opened, couldn't be closed again."
    );

    setGenerationStatus({
      isGenerating: false,
      isComplete: true,
    });
  };

  const handleSaveProfile = async () => {
    if (!analysisStatus.isComplete || !newProfileName.trim()) return;

    const personalityData = {
      name: newProfileName.trim(),
      description: `Based on ${writingSamples.filter((s) => s.isUploaded).length} writing samples`,
    };

    // If we have a callback for saving (edit mode), use it
    if (onSavePersonality) {
      onSavePersonality(personalityData);
      return;
    }

    // Otherwise, use the create API (add mode)
    try {
      const response = await createAuthorPersonality(personalityData);
      
      if (response.status === "success") {
        const newProfile = {
          id: response.message.personality?.id || Date.now().toString(),
          name: personalityData.name,
          description: personalityData.description,
        };

        setSavedProfiles([...savedProfiles, newProfile]);
        setSelectedProfile(newProfile.id);
        setNewProfileName("");
        
        // Show success message
        alert("Author personality saved successfully!");
      } else {
        console.error("Failed to save author personality:", response.message);
        alert("Failed to save author personality. Please try again.");
      }
    } catch (error) {
      console.error("Error saving author personality:", error);
      alert("An error occurred while saving the author personality.");
    }
  };

  const handleLoadProfile = (profileId: string) => {
    setSelectedProfile(profileId);
    setAnalysisStatus({
      isAnalyzing: false,
      progress: 100,
      isComplete: true,
    });

    setTrainingStatus({
      isTraining: false,
      progress: 100,
      isComplete: true,
    });

    setIsResultsOpen(true);
    setTimeout(() => {
      resultsSectionRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };


  const handleProfileCheckChange = (profileId: string) => {
    if (checkedProfiles.includes(profileId)) {
      setCheckedProfiles([]);  // Uncheck the checkbox if it's already selected
    } else {
      setCheckedProfiles([profileId]);  // Set only this checkbox as checked
    }

    // Automatically update the payload when selecting a profile
    const selectedProfile = savedProfiles.find(p => p.id === profileId);
    if (selectedProfile) {
      const data = localStorage.getItem("contentGenPayload") || "{}";
      const parsed = JSON.parse(data);
      const newData = { ...parsed, author: selectedProfile.name };
      localStorage.setItem("contentGenPayload", JSON.stringify(newData));
      setSelectedPersonalityName(selectedProfile.name);
    }
  };

  const handleConfirmSelection = () => {
    setIsConfirmModalOpen(false);
    setCheckedProfiles([]);
  };

  const handleDeleteProfile = (profileId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSavedProfiles(
      savedProfiles.filter((profile) => profile.id !== profileId)
    );
    if (selectedProfile === profileId) {
      setSelectedProfile(null);
    }
    if (checkedProfiles.includes(profileId)) {
      setCheckedProfiles((prev) => prev.filter((id) => id !== profileId));
    }
  };

  const handleRegenerateText = async () => {
    setGenerationStatus({
      isGenerating: true,
      isComplete: false,
    });

    await new Promise((resolve) => setTimeout(resolve, 1500));

    setGeneratedText(
      "The rain fell steadily against the windowpane, creating a rhythmic pattern that matched her heartbeat. Sarah closed her book and gazed outside, watching the world transform under the downpour. There was something cleansing about the rain, washing away the past and nourishing new beginnings. She made her decision then, as the storm intensified. It was time to embrace change, to step into the unknown with courage and determination.\n\nThe letter sat on her desk, the edges crisp and white against the dark wood. She hadn't opened it yet, though it had arrived three days ago. Some part of her knew that once she broke the seal, nothing would be the same. The sender's name was printed in the corner, a name she hadn't seen in years but had never truly forgotten.\n\nSarah stood and walked to the window, pressing her palm against the cool glass. The city beyond was blurred by the rain, buildings reduced to hazy outlines and lights to soft glows. Like memories, she thought, clear in essence but fuzzy around the edges. She turned back to the desk, her mind made up. It was time to read what he had to say."
    );

    setGenerationStatus({
      isGenerating: false,
      isComplete: true,
    });
  };

  useEffect(() => {
    const data = localStorage.getItem("contentGenPayload") || "{}";
    const parsed = JSON.parse(data);
    const savedAuthor = parsed.author;

    if (savedAuthor) {
      const matchedProfile = savedProfiles.find(
        (profile) => profile.name === savedAuthor
      );
      if (matchedProfile) {
        setCheckedProfiles([matchedProfile.id]);
        setSelectedProfile(matchedProfile.id);
        setSelectedPersonalityName(matchedProfile.name);
      }
    }
  }, [savedProfiles]);

  return (
    <div className="space-y-6">
      {showSavedProfiles && (
        <Card>
          <Collapsible open={isProfilesOpen} onOpenChange={setIsProfilesOpen}>
            <CollapsibleTrigger asChild>
              <CardHeader className="cursor-pointer">
                <CardTitle className="flex items-center">
                  <BookOpen className="mr-2 h-5 w-5" />
                  Saved Author Profiles
                </CardTitle>
              </CardHeader>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <CardContent>
                {savedProfiles.length > 0 ? (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      {savedProfiles.map((profile) => (
                        <div
                          key={profile.id}
                          className={`p-3 border rounded-md flex items-center justify-between ${selectedProfile === profile.id
                            ? "bg-gray-100 border-gray-400"
                            : "hover:bg-gray-50"
                            }`}
                        >
                          <div className="flex items-center space-x-3">
                            <Checkbox
                              id={`profile-${profile.id}`}
                              checked={checkedProfiles.length === 1 && checkedProfiles[0] === profile.id}
                              onCheckedChange={() => handleProfileCheckChange(profile.id)}
                              className="h-5 w-5"
                            />
                            <div
                              className="cursor-pointer"
                              onClick={() => handleLoadProfile(profile.id)}
                            >
                              <h4 className="font-medium">{profile.name}</h4>
                              <p className="text-sm text-gray-500">
                                {profile.description}
                              </p>
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => handleDeleteProfile(profile.id, e)}
                            className="opacity-70 hover:opacity-100"
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <BookOpen className="mx-auto h-12 w-12 text-gray-300 mb-2" />
                    <p>No saved author profiles yet</p>
                    <p className="text-sm">
                      Analyze text and save profiles to see them here
                    </p>
                  </div>
                )}
              </CardContent>

            </CollapsibleContent>
          </Collapsible>
        </Card>
      )}

      <Card>
        <Collapsible
          open={isWritingSamplesOpen}
          onOpenChange={setIsWritingSamplesOpen}
        >
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer">
              <CardTitle className="flex items-center">
                <FileText className="mr-2 h-5 w-5" />
                Writing Samples
              </CardTitle>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {writingSamples.slice(0, visibleSamplesCount).map((sample) => (
                  <div
                    key={sample.id}
                    className="space-y-2 border rounded-md p-4"
                  >
                    <div className="flex items-center justify-between">
                      <Label
                        htmlFor={`sample-${sample.id}`}
                        className="font-medium flex items-center"
                      >
                        Writing Sample {sample.id}
                        {sample.isUploaded && (
                          <Check className="ml-2 h-4 w-4 text-green-500" />
                        )}
                      </Label>
                    </div>
                    <Textarea
                      id={`sample-${sample.id}`}
                      placeholder={`Enter sample text #${sample.id}...`}
                      className={`min-h-[100px] ${sample.isUploaded ? "border-green-500" : ""}`}
                      value={sample.text}
                      onChange={(e) =>
                        handleSampleTextChange(sample.id, e.target.value)
                      }
                    />
                    <div className="flex space-x-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className={`flex-1 ${sample.isUploaded && sample.text ? "border-green-500 text-green-600" : ""}`}
                        onClick={() => handleSubmitTextSample(sample.id)}
                        disabled={!sample.text.trim()}
                      >
                        {sample.isUploaded && sample.text ? (
                          <>
                            <Check className="mr-1 h-4 w-4" />
                            Saved
                          </>
                        ) : (
                          <>
                            <FileText className="mr-1 h-4 w-4" />
                            Save Text
                          </>
                        )}
                      </Button>
                      <div className="relative flex-1">
                        <Input
                          id={`file-${sample.id}`}
                          type="file"
                          accept=".txt,.doc,.docx,.pdf"
                          onChange={(e) => handleFileChange(sample.id, e)}
                          className="absolute inset-0 opacity-0 cursor-pointer"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className={`w-full ${sample.file ? "border-green-500 text-green-600" : ""}`}
                        >
                          {sample.file ? (
                            <>
                              <Check className="mr-1 h-4 w-4" />
                              Uploaded
                            </>
                          ) : (
                            <>
                              <Upload className="mr-1 h-4 w-4" />
                              Upload
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                    {sample.file && (
                      <p className="text-xs text-green-600 truncate">
                        File: {sample.file.name}
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {/* Add Writing Sample Button */}
              {visibleSamplesCount < 10 && (
                <div className="flex justify-center pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleAddWritingSample}
                    className="flex items-center space-x-2"
                  >
                    <Plus className="h-4 w-4" />
                    <span>Add Writing Sample</span>
                  </Button>
                </div>
              )}

              <div className="space-y-2">
                <Label>Feature Selection</Label>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="lexical"
                      checked={selectedFeatures.lexical}
                      onCheckedChange={() => handleFeatureChange("lexical")}
                    />
                    <Label htmlFor="lexical" className="cursor-pointer">
                      Lexical Features
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="syntactic"
                      checked={selectedFeatures.syntactic}
                      onCheckedChange={() => handleFeatureChange("syntactic")}
                    />
                    <Label htmlFor="syntactic" className="cursor-pointer">
                      Syntactic Patterns
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="structural"
                      checked={selectedFeatures.structural}
                      onCheckedChange={() => handleFeatureChange("structural")}
                    />
                    <Label htmlFor="structural" className="cursor-pointer">
                      Structural Elements
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="semantic"
                      checked={selectedFeatures.semantic}
                      onCheckedChange={() => handleFeatureChange("semantic")}
                    />
                    <Label htmlFor="semantic" className="cursor-pointer">
                      Semantic Characteristics
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="rhetorical"
                      checked={selectedFeatures.rhetorical}
                      onCheckedChange={() => handleFeatureChange("rhetorical")}
                    />
                    <Label htmlFor="rhetorical" className="cursor-pointer">
                      Rhetorical Devices
                    </Label>
                  </div>
                </div>
              </div>

              <Button
                onClick={handleAnalyze}
                className={`w-full ${hasAnySample
                  ? "bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                  : "bg-gray-300 text-gray-600 cursor-not-allowed"
                  }`}
                disabled={analysisStatus.isAnalyzing || !hasAnySample}
              >
                {analysisStatus.isAnalyzing ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Analyzing...
                  </>
                ) : (
                  <>
                    <BarChart className="mr-2 h-5 w-5" />
                    Analyze Features
                  </>
                )}
              </Button>

            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>

      <Card ref={configSectionRef}>
        <Collapsible open={isConfigOpen} onOpenChange={setIsConfigOpen}>
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer">
              <CardTitle className="flex items-center">
                <Brain className="mr-2 h-5 w-5" />
                Model Configuration
              </CardTitle>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="preset">Configuration Preset</Label>
                <Select
                  value={selectedPreset || ""}
                  onValueChange={handlePresetChange}
                >
                  <SelectTrigger id="preset">
                    <SelectValue placeholder="Select a preset or customize below" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="custom">Custom Configuration</SelectItem>
                    {MODEL_PRESETS.map((preset) => (
                      <SelectItem key={preset.name} value={preset.name}>
                        {preset.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Choose a preset or customize the settings below
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label htmlFor="sample-size">Sample Size</Label>
                  <span className="text-sm text-muted-foreground">
                    {modelConfig.sampleSize}%
                  </span>
                </div>
                <Slider
                  id="sample-size"
                  min={10}
                  max={100}
                  step={10}
                  value={[modelConfig.sampleSize]}
                  onValueChange={(value) =>
                    handleModelConfigChange("sampleSize", value[0])
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Percentage of input text to use for training (higher = more
                  accurate but slower)
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label htmlFor="feature-weight">Feature Weight</Label>
                  <span className="text-sm text-muted-foreground">
                    {modelConfig.featureWeight.toFixed(1)}
                  </span>
                </div>
                <Slider
                  id="feature-weight"
                  min={0.1}
                  max={1.0}
                  step={0.1}
                  value={[modelConfig.featureWeight]}
                  onValueChange={(value) =>
                    handleModelConfigChange("featureWeight", value[0])
                  }
                />
                <p className="text-xs text-muted-foreground">
                  How strongly to enforce author style (higher = more similar to
                  original)
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="complexity-level">Complexity Level</Label>
                <Select
                  value={modelConfig.complexityLevel}
                  onValueChange={(value) =>
                    handleModelConfigChange("complexityLevel", value)
                  }
                >
                  <SelectTrigger id="complexity-level">
                    <SelectValue placeholder="Select complexity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="simple">Simple</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="complex">Complex</SelectItem>
                    <SelectItem value="very-complex">Very Complex</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Determines sentence and paragraph complexity in generated text
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label htmlFor="creativity-level">Creativity Level</Label>
                  <span className="text-sm text-muted-foreground">
                    {modelConfig.creativityLevel.toFixed(1)}
                  </span>
                </div>
                <Slider
                  id="creativity-level"
                  min={0.1}
                  max={1.0}
                  step={0.1}
                  value={[modelConfig.creativityLevel]}
                  onValueChange={(value) =>
                    handleModelConfigChange("creativityLevel", value[0])
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Controls randomness in generation (higher = more creative but
                  less predictable)
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label htmlFor="max-tokens">Max Tokens</Label>
                  <span className="text-sm text-muted-foreground">
                    {modelConfig.maxTokens}
                  </span>
                </div>
                <Slider
                  id="max-tokens"
                  min={100}
                  max={2000}
                  step={100}
                  value={[modelConfig.maxTokens]}
                  onValueChange={(value) =>
                    handleModelConfigChange("maxTokens", value[0])
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Maximum length of generated text (approximately{" "}
                  {Math.round(modelConfig.maxTokens / 4)} words)
                </p>
              </div>

              <Button
                onClick={handleTrain}
                className="w-full bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                disabled={
                  trainingStatus.isTraining || !analysisStatus.isComplete
                }
              >
                {trainingStatus.isTraining ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Training...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-5 w-5" />
                    Train Model
                  </>
                )}
              </Button>

            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>

      <Card ref={resultsSectionRef}>
        <Collapsible open={isResultsOpen} onOpenChange={setIsResultsOpen}>
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer">
              <CardTitle className="flex items-center">
                <BarChart className="mr-2 h-5 w-5" />
                Analysis Results & Generated Text
              </CardTitle>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent className="space-y-6">
              {analysisStatus.isComplete && (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">Feature Analysis</h3>

                  <Tabs defaultValue="lexical">
                    <TabsList className="w-full">
                      <TabsTrigger
                        value="lexical"
                        disabled={!selectedFeatures.lexical}
                      >
                        Lexical
                      </TabsTrigger>
                      <TabsTrigger
                        value="syntactic"
                        disabled={!selectedFeatures.syntactic}
                      >
                        Syntactic
                      </TabsTrigger>
                      <TabsTrigger
                        value="structural"
                        disabled={!selectedFeatures.structural}
                      >
                        Structural
                      </TabsTrigger>
                      <TabsTrigger
                        value="semantic"
                        disabled={!selectedFeatures.semantic}
                      >
                        Semantic
                      </TabsTrigger>
                      <TabsTrigger
                        value="rhetorical"
                        disabled={!selectedFeatures.rhetorical}
                      >
                        Rhetorical
                      </TabsTrigger>
                    </TabsList>

                    <TabsContent value="lexical" className="pt-4">
                      <div className="space-y-4">
                        {featureResults.lexical.map((feature, index) => (
                          <div key={index} className="space-y-1">
                            <div className="flex justify-between">
                              <span className="font-medium">
                                {feature.name}
                              </span>
                              <span>{feature.value}</span>
                            </div>
                            <div className="relative h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                              <div
                                className="absolute top-0 left-0 h-full bg-[#3d545f]"
                                style={{ width: `${feature.percentile}%` }}
                              ></div>
                            </div>
                            <div className="flex justify-between text-xs text-gray-500">
                              <span>0%</span>
                              <span>Percentile: {feature.percentile}%</span>
                              <span>100%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </TabsContent>

                    <TabsContent value="syntactic" className="pt-4">
                      <div className="space-y-4">
                        {featureResults.syntactic.map((feature, index) => (
                          <div key={index} className="space-y-1">
                            <div className="flex justify-between">
                              <span className="font-medium">
                                {feature.name}
                              </span>
                              <span>{feature.value}</span>
                            </div>
                            <div className="relative h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                              <div
                                className="absolute top-0 left-0 h-full bg-[#3d545f]"
                                style={{ width: `${feature.percentile}%` }}
                              ></div>
                            </div>
                            <div className="flex justify-between text-xs text-gray-500">
                              <span>0%</span>
                              <span>Percentile: {feature.percentile}%</span>
                              <span>100%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </TabsContent>

                    <TabsContent value="structural" className="pt-4">
                      <div className="space-y-4">
                        {featureResults.structural.map((feature, index) => (
                          <div key={index} className="space-y-1">
                            <div className="flex justify-between">
                              <span className="font-medium">
                                {feature.name}
                              </span>
                              <span>{feature.value}</span>
                            </div>
                            <div className="relative h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                              <div
                                className="absolute top-0 left-0 h-full bg-[#3d545f]"
                                style={{ width: `${feature.percentile}%` }}
                              ></div>
                            </div>
                            <div className="flex justify-between text-xs text-gray-500">
                              <span>0%</span>
                              <span>Percentile: {feature.percentile}%</span>
                              <span>100%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </TabsContent>

                    <TabsContent value="semantic" className="pt-4">
                      <div className="space-y-4">
                        {featureResults.semantic.map((feature, index) => (
                          <div key={index} className="space-y-1">
                            <div className="flex justify-between">
                              <span className="font-medium">
                                {feature.name}
                              </span>
                              <span>{feature.value}</span>
                            </div>
                            <div className="relative h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                              <div
                                className="absolute top-0 left-0 h-full bg-[#3d545f]"
                                style={{ width: `${feature.percentile}%` }}
                              ></div>
                            </div>
                            <div className="flex justify-between text-xs text-gray-500">
                              <span>0%</span>
                              <span>Percentile: {feature.percentile}%</span>
                              <span>100%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </TabsContent>

                    <TabsContent value="rhetorical" className="pt-4">
                      <div className="space-y-4">
                        {featureResults.rhetorical.map((feature, index) => (
                          <div key={index} className="space-y-1">
                            <div className="flex justify-between">
                              <span className="font-medium">
                                {feature.name}
                              </span>
                              <span>{feature.value}</span>
                            </div>
                            <div className="relative h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                              <div
                                className="absolute top-0 left-0 h-full bg-[#3d545f]"
                                style={{ width: `${feature.percentile}%` }}
                              ></div>
                            </div>
                            <div className="flex justify-between text-xs text-gray-500">
                              <span>0%</span>
                              <span>Percentile: {feature.percentile}%</span>
                              <span>100%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </TabsContent>
                  </Tabs>
                </div>
              )}

              {trainingStatus.isComplete && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-medium">Generated Text</h3>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleGenerate}
                      disabled={generationStatus.isGenerating}
                    >
                      {generationStatus.isGenerating ? (
                        <svg
                          className="animate-spin h-4 w-4"
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          ></circle>
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          ></path>
                        </svg>
                      ) : (
                        <PenTool className="h-4 w-4" />
                      )}
                    </Button>
                  </div>

                  {generationStatus.isComplete ? (
                    <div className="space-y-4">
                      <div className="p-4 border rounded-md bg-gray-50">
                        <p className="whitespace-pre-line">{generatedText}</p>
                      </div>

                      <div className="flex space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleRegenerateText}
                          disabled={generationStatus.isGenerating}
                          className="flex-1"
                        >
                          {generationStatus.isGenerating ? (
                            <svg
                              className="animate-spin -ml-1 mr-2 h-4 w-4"
                              xmlns="http://www.w3.org/2000/svg"
                              fill="none"
                              viewBox="0 0 24 24"
                            >
                              <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                              ></circle>
                              <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              ></path>
                            </svg>
                          ) : (
                            <RefreshCw className="mr-2 h-4 w-4" />
                          )}
                          Regenerate
                        </Button>

                        <Button variant="outline" size="sm" className="flex-1">
                          <Save className="mr-2 h-4 w-4" />
                          Save to Content Queue
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-8 border rounded-md bg-gray-50 text-center text-gray-500">
                      <div className="flex flex-col items-center space-y-2">
                        <Wand2 className="h-8 w-8 text-gray-400" />
                        <p>
                          Click "Generate" to create text in the author's
                          style
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {analysisStatus.isComplete && (
                <div className="space-y-4 pt-4 border-t">
                  <h3 className="text-lg font-medium">Save Author Profile</h3>
                  <div className="flex space-x-2">
                    <Input
                      placeholder="Enter profile name"
                      value={newProfileName}
                      onChange={(e) => setNewProfileName(e.target.value)}
                      className="flex-1"
                    />
                    <Button
                      onClick={handleSaveProfile}
                      disabled={!newProfileName.trim()}
                      className="bg-[#3d545f] text-white hover:bg-[#3d545f]/90"
                    >
                      <Bookmark className="mr-2 h-4 w-4" />
                      Save Profile
                    </Button>
                  </div>
                </div>
              )}

              <div className="flex justify-between pt-4">
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsConfigOpen(true);
                    setTimeout(() => {
                      configSectionRef.current?.scrollIntoView({
                        behavior: "smooth",
                      });
                    }, 100);
                  }}
                  disabled={!analysisStatus.isComplete}
                >
                  <Layers className="mr-2 h-4 w-4" />
                  Adjust Model
                </Button>
              </div>
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>
      
      {/* Loading Modals */}
      <LoadingModal
        isOpen={analysisStatus.isAnalyzing}
        title="Analyzing text features"
        progress={analysisStatus.progress}
      />
      
      <LoadingModal
        isOpen={trainingStatus.isTraining}
        title="Training model"
        progress={trainingStatus.progress}
      />
      
      <LoadingModal
        isOpen={generationStatus.isGenerating}
        title="Generating text in author's style"
      />
      
      <PersonalityConfirmationModal
        isOpen={isConfirmModalOpen}
        onClose={() => setIsConfirmModalOpen(false)}
        onConfirm={handleConfirmSelection}
        personalityName={selectedPersonalityName}
      />
    </div>
  );
}
