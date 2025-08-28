import React from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "./ui/dialog";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "./ui/tabs";

// You may want to move these icons to a shared location
const UploadIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 16V4m0 0l-4 4m4-4l4 4M4 20h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

export interface RfpVersion {
  name: string;
  date: string;
  time: string;
}

export interface RfpModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode?: "new" | "update";
  initialName?: string;
  initialFile?: File | null;
  initialTab?: "upload" | "paste" | "url";
  onSubmit?: (data: { name: string; file?: File | null; text?: string; url?: string; inputTab: string }) => void;
  rfpVersions?: RfpVersion[];
  onFileChange?: (file: File) => void;
  onTextChange?: (text: string) => void;
  onUrlChange?: (url: string) => void;
  file?: File | null;
  text?: string;
  url?: string;
  loading?: boolean;
}

export default function RfpModal({
  open,
  onOpenChange,
  mode = "new", // "new" or "update"
  initialName = "",
  initialFile = null,
  initialTab = "upload",
  onSubmit,
  rfpVersions = [], // Array of {name, date, time}
  onFileChange,
  onTextChange,
  onUrlChange,
  file,
  text,
  url,
  loading,
}: RfpModalProps) {
  const [inputTab, setInputTab] = React.useState<"upload" | "paste" | "url">(initialTab);
  const [projectName, setProjectName] = React.useState(initialName);
  // Controlled file/text/url if provided, else local state
  const [localFile, setLocalFile] = React.useState<File | null>(initialFile);
  const [localText, setLocalText] = React.useState("");
  const [localUrl, setLocalUrl] = React.useState("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setLocalFile(e.target.files[0]);
      if (onFileChange) onFileChange(e.target.files[0]);
    }
  };
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalText(e.target.value);
    if (onTextChange) onTextChange(e.target.value);
  };
  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalUrl(e.target.value);
    if (onUrlChange) onUrlChange(e.target.value);
  };
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSubmit) {
      onSubmit({
        name: projectName,
        file: file ?? localFile,
        text: text ?? localText,
        url: url ?? localUrl,
        inputTab,
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl w-full">
        <DialogHeader>
          <DialogTitle>{mode === "update" ? "Update RFP" : "New Project"}</DialogTitle>
        </DialogHeader>
        <div className="w-full flex flex-col items-center px-0 pt-0 pb-0">
          <div className="w-full flex flex-col gap-6 items-center justify-center pt-6 px-6">
            <div className="w-full flex flex-col gap-1.5 items-start">
              <div className="flex flex-row gap-2.5 items-center">
                <span className="font-semibold text-[16px] text-zinc-950">{mode === "update" ? "Update RFP" : "Create a new RFP project"}</span>
              </div>
              <div className="flex flex-row gap-2.5 items-center w-full">
                <span className="text-[14px] text-zinc-500">Upload your RFP file here, paste it as text, or import from a URL.</span>
              </div>
            </div>
            <div className="bg-zinc-100 rounded-lg w-full">
              <Tabs value={inputTab} onValueChange={setInputTab as (value: string) => void} className="w-full">
                <TabsList className="flex flex-row gap-2 w-full p-2">
                  <TabsTrigger value="upload" className="flex-1">Upload PDF</TabsTrigger>
                  <TabsTrigger value="paste" className="flex-1">Paste Text</TabsTrigger>
                  <TabsTrigger value="url" className="flex-1">Import from URL</TabsTrigger>
                </TabsList>
                <TabsContent value="upload" className="w-full">
                  <div className="flex flex-row items-center w-full p-1 gap-2">
                    <label htmlFor="rfp-upload" className="bg-white flex flex-col gap-2.5 items-center justify-center px-2 py-1 rounded-md shadow font-medium text-[14px] text-zinc-950 border border-zinc-200 cursor-pointer w-full">
                      <div className="h-16 w-24 mb-2 flex items-center justify-center">
                        <UploadIcon />
                      </div>
                      <span className="text-zinc-500 text-[16px]">Click or drag file to upload</span>
                      <input
                        id="rfp-upload"
                        type="file"
                        onChange={handleFileChange}
                        className="hidden"
                        required={inputTab === "upload"}
                      />
                      {(file ?? localFile) && (file ?? localFile)?.name && (
                        <span className="mt-2 text-zinc-900 font-medium text-sm">{(file ?? localFile)?.name}</span>
                      )}
                    </label>
                  </div>
                </TabsContent>
                <TabsContent value="paste" className="w-full">
                  <textarea
                    className="w-full min-h-[120px] rounded-md border border-zinc-200 p-3 text-base shadow-sm bg-white text-zinc-950"
                    placeholder="Paste your RFP text here..."
                    value={text ?? localText}
                    onChange={handleTextChange}
                    required={inputTab === "paste"}
                  />
                </TabsContent>
                <TabsContent value="url" className="w-full">
                  <Input
                    className="w-full"
                    placeholder="Enter a URL to import RFP..."
                    value={url ?? localUrl}
                    onChange={handleUrlChange}
                    required={inputTab === "url"}
                  />
                </TabsContent>
              </Tabs>
            </div>
          </div>
          <div className="w-full flex flex-row gap-6 items-start justify-start p-6">
            {/* Left: Project Name */}
            <div className="flex-1 flex flex-col gap-6 min-w-[0]">
              <div className="flex flex-col gap-2.5 w-full">
                <span className="font-medium text-[14px] text-zinc-950">Project name</span>
                <Input
                  className="bg-white h-9 rounded-md w-full px-3 border border-zinc-200 shadow-sm text-[16px] text-zinc-950 font-normal"
                  placeholder="Enter project name"
                  value={projectName}
                  onChange={e => setProjectName(e.target.value)}
                  required
                />
              </div>
            </div>
            {/* Right: RFP Versions */}
            <div className="flex-1 flex flex-col gap-4 min-w-[0]">
              <div className="flex items-center justify-between">
                <span className="font-medium text-[14px] text-zinc-950">RFP Versions</span>
                <span className="text-xs text-zinc-500">{rfpVersions.length > 0 ? `${rfpVersions.length} versions` : "No versions yet"}</span>
              </div>
              <div className="flex flex-col gap-4 w-full max-h-[300px] overflow-y-auto pr-1 items-center justify-center text-zinc-400 text-sm">
                {rfpVersions.length > 0 ? (
                  rfpVersions.map((rfp, idx) => (
                    <div key={idx} className={`rounded-md w-full flex flex-col shadow-sm border bg-white border-zinc-200`}>
                      <div className="flex flex-row items-center justify-between px-2 py-1">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <span className="font-medium text-[14px] text-zinc-950 truncate">{rfp.name}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button type="button" size="sm" variant="outline">View</Button>
                        </div>
                      </div>
                      <div className="flex flex-row text-xs text-zinc-500 justify-between px-2 pb-1">
                        <span>{rfp.date}</span>
                        <span>{rfp.time}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <span>No RFP versions uploaded yet.</span>
                )}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" variant="default" className="bg-zinc-900 hover:bg-zinc-800 text-white" onClick={handleSubmit} disabled={loading}>{mode === "update" ? "Save changes" : "Create Project"}</Button>
            <DialogClose asChild>
              <Button type="button" variant="secondary">Cancel</Button>
            </DialogClose>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
} 